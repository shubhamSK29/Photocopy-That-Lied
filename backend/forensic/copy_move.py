"""Copy-move detection via keypoint self-matching with geometric verification.

The detector looks for groups of matched keypoints inside the *same* image whose
displacement is geometrically consistent, which is the signature of a region that
was duplicated. Descriptor similarity alone is never treated as proof: matches must
survive a ratio test, a spatial-separation filter, shift-vector clustering and a
RANSAC affine verification.
"""
from __future__ import annotations

from typing import Any, Optional

import cv2
import numpy as np

from backend.forensic.common import (
    DetectorResult,
    blank_heatmap,
    boxes_from_points,
    gaussian_blobs,
)

MIN_KEYPOINTS = 40
RATIO_TEST = 0.65
MIN_SPATIAL_SEPARATION_FRACTION = 0.05
SHIFT_CLUSTER_TOLERANCE = 12.0
MIN_CLUSTER_SIZE = 4
MIN_INLIERS = 8
# A duplicated region is spatially compact; naturally repeated texture matches
# spread over most of the frame.
MAX_CLUSTER_SPREAD_FRACTION = 0.35


def _detector() -> tuple[Any, str]:
    if hasattr(cv2, "SIFT_create"):
        try:
            # A low contrast threshold keeps enough keypoints in smooth crop scenes.
            return cv2.SIFT_create(nfeatures=6000, contrastThreshold=0.006, edgeThreshold=12), "SIFT"
        except cv2.error:  # pragma: no cover - build dependent
            pass
    return cv2.ORB_create(nfeatures=6000), "ORB"


def _cluster_by_shift(pairs: np.ndarray) -> list[np.ndarray]:
    """Greedy clustering of match pairs by their displacement vector."""
    shifts = pairs[:, 2:4] - pairs[:, 0:2]
    order = np.argsort(np.linalg.norm(shifts, axis=1))
    clusters: list[list[int]] = []
    centers: list[np.ndarray] = []
    for idx in order:
        shift = shifts[idx]
        placed = False
        for c_i, center in enumerate(centers):
            if np.linalg.norm(shift - center) <= SHIFT_CLUSTER_TOLERANCE:
                clusters[c_i].append(int(idx))
                n = len(clusters[c_i])
                centers[c_i] = center + (shift - center) / n
                placed = True
                break
        if not placed:
            clusters.append([int(idx)])
            centers.append(shift.astype(float))
    return [pairs[np.array(c)] for c in clusters if len(c) >= MIN_CLUSTER_SIZE]


def detect(gray: np.ndarray) -> DetectorResult:
    h, w = gray.shape[:2]
    heatmap = blank_heatmap(gray.shape[:2])
    detector, algo = _detector()

    try:
        keypoints, descriptors = detector.detectAndCompute(gray, None)
    except cv2.error as exc:  # pragma: no cover - defensive
        return DetectorResult(
            name="copy_move",
            status="not_applicable",
            score=0.0,
            heatmap=heatmap,
            explanation=f"Keypoint extraction failed ({exc}).",
            metrics={"algorithm": algo},
        )

    metrics: dict[str, Any] = {
        "algorithm": algo,
        "keypoint_count": 0 if descriptors is None else len(keypoints),
        "candidate_match_count": 0,
        "verified_match_count": 0,
        "inlier_ratio": 0.0,
        "cluster_count": 0,
        "region_area_fraction": 0.0,
        "region_separation_px": 0.0,
    }

    if descriptors is None or len(keypoints) < MIN_KEYPOINTS:
        return DetectorResult(
            name="copy_move",
            status="insufficient_evidence",
            score=0.0,
            heatmap=heatmap,
            explanation=(
                "Too few reliable keypoints were found for copy-move analysis "
                f"({metrics['keypoint_count']} found, {MIN_KEYPOINTS} required). "
                "This often happens with blurred, very smooth or low-resolution images."
            ),
            metrics=metrics,
        )

    desc = descriptors.astype(np.float32)
    coords = np.array([kp.pt for kp in keypoints], dtype=np.float32)
    min_sep = MIN_SPATIAL_SEPARATION_FRACTION * float(np.hypot(w, h))

    index = cv2.BFMatcher(cv2.NORM_L2)
    knn = index.knnMatch(desc, desc, k=min(10, len(desc)))

    pairs: list[tuple[float, float, float, float]] = []
    for matches in knn:
        filtered = [
            m for m in matches
            if m.trainIdx != m.queryIdx
            and np.linalg.norm(coords[m.queryIdx] - coords[m.trainIdx]) > min_sep
        ]
        if len(filtered) < 2:
            continue
        best, second = filtered[0], filtered[1]
        if second.distance <= 1e-6 or best.distance / second.distance > RATIO_TEST:
            continue
        p, q = coords[best.queryIdx], coords[best.trainIdx]
        pairs.append((float(p[0]), float(p[1]), float(q[0]), float(q[1])))

    metrics["candidate_match_count"] = len(pairs)
    if len(pairs) < MIN_CLUSTER_SIZE:
        return DetectorResult(
            name="copy_move",
            status="not_detected",
            score=0.0,
            heatmap=heatmap,
            explanation="No duplicated-region candidates survived descriptor ratio filtering.",
            metrics=metrics,
        )

    pair_array = np.array(pairs, dtype=np.float32)
    clusters = _cluster_by_shift(pair_array)
    metrics["cluster_count"] = len(clusters)
    if not clusters:
        return DetectorResult(
            name="copy_move",
            status="not_detected",
            score=0.0,
            heatmap=heatmap,
            explanation=(
                "Candidate matches were scattered with inconsistent displacements, which is "
                "typical of naturally repeated texture rather than a duplicated region."
            ),
            metrics=metrics,
        )

    verified_points: list[np.ndarray] = []
    verified_regions: list[dict] = []
    total_inliers = 0
    rejected_spread = 0
    separations: list[float] = []

    for cluster in clusters:
        src = np.ascontiguousarray(cluster[:, 0:2], dtype=np.float32)
        dst = np.ascontiguousarray(cluster[:, 2:4], dtype=np.float32)
        if len(cluster) < MIN_CLUSTER_SIZE:
            continue
        model, inliers = cv2.estimateAffinePartial2D(
            src.reshape(-1, 1, 2), dst.reshape(-1, 1, 2),
            method=cv2.RANSAC, ransacReprojThreshold=4.0, maxIters=3000,
        )
        if model is None or inliers is None:
            continue
        mask = inliers.ravel().astype(bool)
        if int(mask.sum()) < MIN_INLIERS:
            continue
        src_in, dst_in = src[mask], dst[mask]
        diag = float(np.hypot(w, h))
        spread = max(
            float(np.hypot(*(src_in.max(axis=0) - src_in.min(axis=0)))),
            float(np.hypot(*(dst_in.max(axis=0) - dst_in.min(axis=0)))),
        ) / diag
        if spread > MAX_CLUSTER_SPREAD_FRACTION:
            rejected_spread += 1
            continue
        total_inliers += int(mask.sum())
        verified_points.append(np.vstack([src_in, dst_in]))
        separations.append(float(np.median(np.linalg.norm(dst_in - src_in, axis=1))))

    metrics["verified_match_count"] = total_inliers
    metrics["clusters_rejected_as_repeated_texture"] = rejected_spread
    metrics["inlier_ratio"] = (
        total_inliers / float(len(pair_array)) if len(pair_array) else 0.0
    )
    metrics["region_separation_px"] = float(np.mean(separations)) if separations else 0.0

    if total_inliers < MIN_INLIERS:
        return DetectorResult(
            name="copy_move",
            status="not_detected",
            score=0.0,
            heatmap=heatmap,
            explanation=(
                "Candidate matches failed geometric verification or were spread across the "
                "whole frame, which is the signature of naturally repeated texture rather than "
                "a duplicated region."
                if rejected_spread
                else "Candidate matches failed geometric verification, so no duplicated region "
                "is supported by the evidence."
            ),
            metrics=metrics,
        )

    points = np.vstack(verified_points)
    heatmap = gaussian_blobs(gray.shape[:2], points, sigma=max(8.0, min(h, w) * 0.02))
    verified_regions = boxes_from_points(points, gray.shape[:2])
    region_area = sum(r["area_fraction"] for r in verified_regions)
    metrics["region_area_fraction"] = float(min(1.0, region_area))
    metrics["region_count"] = len(verified_regions)

    # Score grows with verified evidence but saturates; it is never a fraud verdict.
    score = float(
        np.clip(
            0.45 * np.tanh(total_inliers / 25.0)
            + 0.35 * np.clip(metrics["inlier_ratio"] / 0.5, 0, 1)
            + 0.20 * np.clip(metrics["region_area_fraction"] / 0.15, 0, 1),
            0,
            1,
        )
    )
    return DetectorResult(
        name="copy_move",
        status="detected",
        score=score,
        heatmap=heatmap,
        regions=verified_regions,
        explanation=(
            f"{total_inliers} geometrically consistent duplicate-region matches were verified "
            f"across {len(verified_regions)} region(s). Duplicated content can also occur in "
            "naturally repetitive scenes, so the location should be inspected visually."
        ),
        metrics=metrics,
    )
