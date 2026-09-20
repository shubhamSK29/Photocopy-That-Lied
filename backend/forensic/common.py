"""Shared structures and helpers for the forensic detectors."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import cv2
import numpy as np

STATUSES = ("detected", "not_detected", "insufficient_evidence", "not_applicable")


@dataclass
class DetectorResult:
    name: str
    status: str
    score: float
    heatmap: Optional[np.ndarray] = None
    regions: list[dict] = field(default_factory=list)
    explanation: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"invalid detector status: {self.status}")

    @property
    def score_available(self) -> bool:
        """`insufficient_evidence` is not the same thing as a score of zero."""
        return self.status in ("detected", "not_detected")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "score": round(float(self.score), 4) if self.score_available else None,
            "score_available": self.score_available,
            "regions": self.regions,
            "explanation": self.explanation,
            "metrics": _jsonable(self.metrics),
            "error": self.error,
        }


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return round(float(value), 6)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    return value


def blank_heatmap(shape: tuple[int, int]) -> np.ndarray:
    return np.zeros(shape, dtype=np.float32)


def normalize_map(heatmap: np.ndarray) -> np.ndarray:
    peak = float(heatmap.max()) if heatmap.size else 0.0
    if peak <= 1e-8:
        return np.zeros_like(heatmap, dtype=np.float32)
    return (heatmap / peak).astype(np.float32)


def gaussian_blobs(shape: tuple[int, int], points: np.ndarray, sigma: float = 12.0) -> np.ndarray:
    heat = blank_heatmap(shape)
    h, w = shape
    for x, y in np.asarray(points, dtype=np.float32):
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < w and 0 <= yi < h:
            heat[yi, xi] += 1.0
    ksize = int(max(3, sigma * 4) // 2 * 2 + 1)
    heat = cv2.GaussianBlur(heat, (ksize, ksize), sigma)
    return normalize_map(heat)


def boxes_from_points(points: np.ndarray, shape: tuple[int, int], pad: int = 8) -> list[dict]:
    """Cluster points spatially and return padded bounding boxes."""
    pts = np.asarray(points, dtype=np.float32)
    if len(pts) == 0:
        return []
    h, w = shape
    eps = max(20.0, 0.05 * float(np.hypot(w, h)))
    labels: list[int] = [-1] * len(pts)
    current = 0
    for i in range(len(pts)):
        if labels[i] != -1:
            continue
        stack = [i]
        labels[i] = current
        while stack:
            j = stack.pop()
            dists = np.linalg.norm(pts - pts[j], axis=1)
            for k in np.where(dists <= eps)[0]:
                if labels[k] == -1:
                    labels[k] = current
                    stack.append(int(k))
        current += 1

    regions = []
    for label in range(current):
        group = pts[np.array(labels) == label]
        if len(group) < 3:
            continue
        x0 = max(0, int(group[:, 0].min()) - pad)
        y0 = max(0, int(group[:, 1].min()) - pad)
        x1 = min(w - 1, int(group[:, 0].max()) + pad)
        y1 = min(h - 1, int(group[:, 1].max()) + pad)
        area = max(1, (x1 - x0) * (y1 - y0))
        regions.append(
            {
                "x": x0,
                "y": y0,
                "width": x1 - x0,
                "height": y1 - y0,
                "point_count": int(len(group)),
                "area_fraction": round(area / float(w * h), 5),
            }
        )
    regions.sort(key=lambda r: r["point_count"], reverse=True)
    return regions[:6]


def regions_from_mask(mask: np.ndarray, min_area_fraction: float = 0.002) -> list[dict]:
    binary = (mask > 0).astype(np.uint8)
    num, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    h, w = mask.shape[:2]
    regions = []
    for i in range(1, num):
        x, y, bw, bh, area = stats[i]
        if area / float(w * h) < min_area_fraction:
            continue
        regions.append(
            {
                "x": int(x),
                "y": int(y),
                "width": int(bw),
                "height": int(bh),
                "point_count": int(area),
                "area_fraction": round(float(area) / float(w * h), 5),
            }
        )
    regions.sort(key=lambda r: r["area_fraction"], reverse=True)
    return regions[:6]
