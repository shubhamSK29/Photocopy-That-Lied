"""Spatial evidence fusion: do independent detectors point at the same place?"""
from __future__ import annotations

from itertools import combinations
from typing import Optional

import cv2
import numpy as np

from backend.forensic.common import DetectorResult, blank_heatmap, normalize_map, regions_from_mask

THRESHOLD = 0.5
# Compression is a weak signal, so it contributes little to the combined map.
COMBINE_WEIGHTS = {"copy_move": 0.5, "local_anomaly": 0.35, "compression": 0.15}


def _mask(heatmap: Optional[np.ndarray], shape: tuple[int, int]) -> np.ndarray:
    if heatmap is None or heatmap.size == 0:
        return np.zeros(shape, dtype=bool)
    if heatmap.shape[:2] != shape:
        heatmap = cv2.resize(heatmap, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)
    return heatmap >= THRESHOLD


def _iou_dice(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    inter = float(np.logical_and(a, b).sum())
    union = float(np.logical_or(a, b).sum())
    total = float(a.sum() + b.sum())
    iou = inter / union if union > 0 else 0.0
    dice = 2 * inter / total if total > 0 else 0.0
    return iou, dice


def combine(detectors: dict[str, DetectorResult], shape: tuple[int, int]) -> tuple[np.ndarray, dict]:
    active = {
        name: det for name, det in detectors.items()
        if det.status == "detected" and det.heatmap is not None and float(det.heatmap.max()) > 0
    }
    combined = blank_heatmap(shape)
    for name, det in active.items():
        heat = det.heatmap
        if heat.shape[:2] != shape:
            heat = cv2.resize(heat, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)
        combined += COMBINE_WEIGHTS.get(name, 0.2) * heat
    combined = normalize_map(combined)

    masks = {name: _mask(det.heatmap, shape) for name, det in active.items()}
    pairs = {}
    best_iou = best_dice = 0.0
    for (n1, m1), (n2, m2) in combinations(masks.items(), 2):
        if n1 == "visible_timestamp" or n2 == "visible_timestamp":
            continue
        iou, dice = _iou_dice(m1, m2)
        pairs[f"{n1}|{n2}"] = {"iou": round(iou, 4), "dice": round(dice, 4)}
        best_iou = max(best_iou, iou)
        best_dice = max(best_dice, dice)

    strong_pairs = [k for k, v in pairs.items() if v["dice"] >= 0.3]
    agreement_level = (
        "strong" if best_dice >= 0.5 else "moderate" if best_dice >= 0.2 else
        "weak" if best_dice > 0 else "none"
    )

    consensus_mask = np.zeros(shape, dtype=np.uint8)
    if len(masks) >= 2:
        stack = np.stack([m.astype(np.uint8) for m in masks.values()])
        consensus_mask = (stack.sum(axis=0) >= 2).astype(np.uint8)

    summary = {
        "detectors_with_regions": sorted(active.keys()),
        "pairs": pairs,
        "max_iou": round(best_iou, 4),
        "max_dice": round(best_dice, 4),
        "agreement_level": agreement_level,
        "agreeing_pairs": strong_pairs,
        "consensus_regions": regions_from_mask(consensus_mask, min_area_fraction=0.003),
        "note": (
            "Spatial agreement means several independent detectors highlight a similar area. "
            "It strengthens the evidence but is not proof of manipulation."
        ),
    }
    return combined, summary
