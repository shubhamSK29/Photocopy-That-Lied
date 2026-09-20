"""Patch-based local image-processing inconsistency detector.

The module answers one narrow question: does some region behave differently from
the rest of the image, and from its own neighbourhood, in terms of noise,
high-frequency energy and chroma noise? It does not claim that a difference
proves splicing.
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy.ndimage import median_filter, uniform_filter

from backend.forensic.common import (
    DetectorResult,
    blank_heatmap,
    normalize_map,
    regions_from_mask,
)

PATCH = 64
STRIDE = 32
MIN_PATCHES = 24
ANOMALY_Z = 3.5
NEIGHBOURHOOD = 7


def _patch_features(patch_gray: np.ndarray, patch_bgr: np.ndarray) -> np.ndarray:
    """Content-normalised patch statistics.

    Raw noise or sharpness mostly measure what the scene contains. Ratios of noise
    and high-frequency energy to the local texture level describe how the pixels
    were processed, which is what this detector compares across the image.
    """
    g = patch_gray.astype(np.float32)
    residual = g - cv2.medianBlur(patch_gray, 3).astype(np.float32)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    texture = float(np.mean(np.abs(gx) + np.abs(gy)))
    noise_ratio = float(residual.std()) / (texture + 1.0)
    dct = cv2.dct(g / 255.0)
    total = float(np.abs(dct).sum()) + 1e-6
    high = float(np.abs(dct[patch_gray.shape[0] // 2:, patch_gray.shape[1] // 2:]).sum())
    lab = cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    chroma = lab[..., 1:]
    chroma_noise = float((chroma - cv2.GaussianBlur(chroma, (0, 0), 1.5)).std())
    # Content pasted from a differently compressed source carries a different 8x8
    # JPEG block signature than its surroundings.
    dh = np.abs(np.diff(g, axis=1))
    dv = np.abs(np.diff(g, axis=0))
    on = dh[:, 7::8].mean() + dv[7::8, :].mean()
    off = dh.mean() + dv.mean() + 1e-6
    blockiness = float(on / off)
    return np.array(
        [
            noise_ratio,
            high / total,
            chroma_noise / (texture + 1.0),
            blockiness,
            float(np.log1p(texture)),
        ],
        dtype=np.float32,
    )


N_FEATURES = 5


def _global_scale(flat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    median = np.median(flat, axis=0)
    mad = np.median(np.abs(flat - median), axis=0) * 1.4826
    # A floor keeps a near-zero spread in one statistic from producing enormous
    # z-scores for ordinary patches.
    scale = np.maximum(mad, 0.03 * np.abs(median) + 1e-6)
    return median, scale


def _neighbourhood_z(grid: np.ndarray, floor: np.ndarray) -> np.ndarray:
    """Robust z of every grid cell against its spatial neighbourhood.

    Scene structure (sky, horizon, shadow) varies smoothly, so comparing a patch
    with its neighbours suppresses differences that are merely scene layout.
    """
    out = np.zeros_like(grid)
    for k in range(grid.shape[2]):
        plane = grid[..., k]
        med = median_filter(plane, size=NEIGHBOURHOOD, mode="nearest")
        mad = median_filter(np.abs(plane - med), size=NEIGHBOURHOOD, mode="nearest") * 1.4826
        out[..., k] = (plane - med) / np.maximum(mad, floor[k])
    return out


def detect(bgr: np.ndarray) -> DetectorResult:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    heatmap = blank_heatmap((h, w))
    metrics: dict = {
        "patch_size": PATCH,
        "patch_count": 0,
        "anomalous_patch_fraction": 0.0,
        "max_anomaly": 0.0,
        "mean_anomaly": 0.0,
    }

    if h < PATCH * 2 or w < PATCH * 2:
        return DetectorResult(
            name="local_anomaly",
            status="insufficient_evidence",
            score=0.0,
            heatmap=heatmap,
            explanation="Image is too small for reliable patch-based comparison.",
            metrics=metrics,
        )

    ys = list(range(0, h - PATCH + 1, STRIDE))
    xs = list(range(0, w - PATCH + 1, STRIDE))
    feats = np.zeros((len(ys), len(xs), N_FEATURES), dtype=np.float32)
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            feats[iy, ix] = _patch_features(
                gray[y:y + PATCH, x:x + PATCH], bgr[y:y + PATCH, x:x + PATCH]
            )

    metrics["patch_count"] = int(feats.shape[0] * feats.shape[1])
    if metrics["patch_count"] < MIN_PATCHES or len(ys) < 3 or len(xs) < 3:
        return DetectorResult(
            name="local_anomaly",
            status="insufficient_evidence",
            score=0.0,
            heatmap=heatmap,
            explanation=(
                f"Only {metrics['patch_count']} analysable patches were available; at least "
                f"{MIN_PATCHES} are required for robust statistics."
            ),
            metrics=metrics,
        )

    flat = feats.reshape(-1, feats.shape[2])
    median, scale = _global_scale(flat)
    z_global = np.abs((feats - median) / scale)
    z_local = np.abs(_neighbourhood_z(feats, scale * 0.5))
    # A patch counts as anomalous only when it stands out from the whole image *and*
    # from its own surroundings, which removes most scene-structure false positives.
    z = np.minimum(z_global, z_local)
    # The texture level itself is scene content: it only qualifies the other signals.
    per_patch = z[..., : N_FEATURES - 1].max(axis=2)
    # Manipulated content covers a contiguous area, so an isolated outlier patch is
    # not evidence: average each patch with its immediate neighbours.
    patch_scores = uniform_filter(per_patch, size=3, mode="nearest")
    texture = feats[..., N_FEATURES - 1]
    patch_scores[texture < np.percentile(texture, 5)] *= 0.5

    accum = blank_heatmap((h, w))
    weight = blank_heatmap((h, w))
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            accum[y:y + PATCH, x:x + PATCH] += float(patch_scores[iy, ix])
            weight[y:y + PATCH, x:x + PATCH] += 1.0
    weight[weight == 0] = 1.0
    dense = accum / weight
    smooth = cv2.GaussianBlur(dense, (0, 0), sigmaX=max(4.0, PATCH / 8.0))

    anomalous = patch_scores >= ANOMALY_Z
    metrics.update(
        {
            "anomalous_patch_fraction": float(anomalous.mean()),
            "max_anomaly": float(patch_scores.max()),
            "mean_anomaly": float(patch_scores.mean()),
            "p95_anomaly": float(np.percentile(patch_scores, 95)),
            "anomalous_patch_count": int(anomalous.sum()),
        }
    )

    mask = (smooth >= ANOMALY_Z).astype(np.uint8)
    regions = regions_from_mask(mask)
    heatmap = normalize_map(np.clip(smooth / max(ANOMALY_Z * 1.5, 1e-6), 0, 1))

    fraction = metrics["anomalous_patch_fraction"]
    if metrics["max_anomaly"] < ANOMALY_Z:
        status = "not_detected"
        explanation = (
            "Local noise, high-frequency and colour statistics are consistent across the image."
        )
    elif fraction > 0.35:
        # Nearly everything flagged means the statistics are unstable, not localised.
        status = "insufficient_evidence"
        explanation = (
            "Patch statistics vary widely across the whole image, which typically indicates "
            "a globally noisy, heavily processed or low-quality photo rather than a localised "
            "inconsistency."
        )
    else:
        status = "detected"
        explanation = (
            f"{metrics['anomalous_patch_count']} of {metrics['patch_count']} patches "
            f"({fraction * 100:.1f}%) differ both from the image-wide distribution and from "
            f"their immediate neighbourhood (max robust z = {metrics['max_anomaly']:.1f}). "
            "Local processing differences can also be produced by selective smartphone "
            "enhancement."
        )

    score = float(
        np.clip(
            0.6 * np.clip((metrics["max_anomaly"] - ANOMALY_Z) / 6.0, 0, 1)
            + 0.4 * np.clip(fraction / 0.08, 0, 1),
            0,
            1,
        )
    )
    if status == "not_detected":
        score = 0.0

    return DetectorResult(
        name="local_anomaly",
        status=status,
        score=score,
        heatmap=heatmap,
        regions=regions if status == "detected" else [],
        explanation=explanation,
        metrics=metrics,
    )
