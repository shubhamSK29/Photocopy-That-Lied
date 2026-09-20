"""Natural smartphone-processing calibration.

The reference library holds forensic feature vectors measured on genuine images
and on legitimate variants of them (resize, JPEG recompression, screenshot,
sharpening, denoising, brightness/contrast/colour changes, messaging-style
recompression).

High similarity to the library does NOT mean "genuine". It only means the
observed forensic artifacts can plausibly be explained by ordinary image
processing, which reduces unexplained suspicion.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Optional

import numpy as np

from backend import config
from backend.features.feature_builder import BASE_FEATURE_NAMES

# Copy-move evidence is a manipulation signal, not a processing artifact; it is
# excluded from the natural-processing distance so that duplication evidence can
# never be "explained away" by compression-like similarity.
SIMILARITY_FEATURES = [
    name for name in BASE_FEATURE_NAMES if not name.startswith("copy_move") and not name.startswith("spatial")
]

K_NEIGHBOURS = 5


class NaturalProcessingLibrary:
    def __init__(self, payload: dict):
        self.version: str = payload.get("version", "natural-v1")
        self.feature_names: list[str] = payload.get("feature_names", SIMILARITY_FEATURES)
        self.entries: list[dict] = payload.get("entries", [])
        matrix = np.array([[e["features"].get(n, np.nan) for n in self.feature_names]
                           for e in self.entries], dtype=float)
        self.raw_matrix = matrix
        if matrix.size:
            self.center = np.nanmedian(matrix, axis=0)
            q75, q25 = np.nanpercentile(matrix, [75, 25], axis=0)
            scale = (q75 - q25)
            scale[~np.isfinite(scale) | (scale < 1e-6)] = 1.0
            self.scale = scale
            self.matrix = self._standardize(matrix)
        else:
            self.center = np.zeros(len(self.feature_names))
            self.scale = np.ones(len(self.feature_names))
            self.matrix = matrix

    def _standardize(self, matrix: np.ndarray) -> np.ndarray:
        std = (matrix - self.center) / self.scale
        return np.nan_to_num(std, nan=0.0, posinf=6.0, neginf=-6.0)

    @property
    def available(self) -> bool:
        return len(self.entries) >= K_NEIGHBOURS

    def compare(self, features: dict[str, float]) -> dict[str, Any]:
        if not self.available:
            return {
                "status": "unavailable",
                "natural_processing_similarity": 0.5,
                "matched_transformations": [],
                "matched_device_domain": None,
                "confidence": 0.0,
                "library_version": self.version,
                "library_size": len(self.entries),
                "interpretation": (
                    "No natural-processing reference library is loaded, so artifacts could not be "
                    "compared against known smartphone-processing patterns. A neutral value is used."
                ),
            }

        vector = np.array([features.get(n, np.nan) for n in self.feature_names], dtype=float)
        std_vector = self._standardize(vector.reshape(1, -1))[0]
        distances = np.linalg.norm(self.matrix - std_vector, axis=1) / np.sqrt(len(self.feature_names))
        order = np.argsort(distances)[:K_NEIGHBOURS]
        nearest = float(distances[order].mean())
        similarity = float(np.exp(-nearest / 1.25))

        transformations = Counter(self.entries[i].get("transformation", "unknown") for i in order)
        devices = Counter(self.entries[i].get("device_domain", "unknown") for i in order)
        spread = float(distances[order].std())
        confidence = float(np.clip(1.0 - spread, 0.0, 1.0))

        if similarity >= 0.6:
            interpretation = (
                "The measured artifacts closely resemble tested smartphone-processing patterns "
                "such as " + ", ".join(t for t, _ in transformations.most_common(2)) +
                ". They are therefore largely explainable by normal processing."
            )
        elif similarity >= 0.35:
            interpretation = (
                "The measured artifacts are only partially explained by tested "
                "smartphone-processing patterns."
            )
        else:
            interpretation = (
                "The measured artifacts are not well explained by any tested natural-processing "
                "condition. This does not by itself indicate manipulation; the image may simply be "
                "outside the tested conditions (see data coverage)."
            )

        return {
            "status": "available",
            "natural_processing_similarity": round(similarity, 4),
            "nearest_distance": round(nearest, 4),
            "matched_transformations": [t for t, _ in transformations.most_common(3)],
            "matched_device_domain": devices.most_common(1)[0][0] if devices else None,
            "confidence": round(confidence, 3),
            "library_version": self.version,
            "library_size": len(self.entries),
            "interpretation": interpretation,
        }

    def coverage_distance(self, features: dict[str, float]) -> Optional[float]:
        if not self.available:
            return None
        vector = np.array([features.get(n, np.nan) for n in self.feature_names], dtype=float)
        std_vector = self._standardize(vector.reshape(1, -1))[0]
        distances = np.linalg.norm(self.matrix - std_vector, axis=1) / np.sqrt(len(self.feature_names))
        return float(np.sort(distances)[:K_NEIGHBOURS].mean())


_CACHE: dict[str, NaturalProcessingLibrary] = {}


def load_library(path: Optional[Path] = None) -> NaturalProcessingLibrary:
    path = Path(path or config.NATURAL_LIBRARY_PATH)
    key = str(path)
    cached = _CACHE.get(key)
    mtime = path.stat().st_mtime if path.exists() else 0
    if cached is not None and getattr(cached, "_mtime", None) == mtime:
        return cached
    payload = json.loads(path.read_text()) if path.exists() else {"entries": []}
    library = NaturalProcessingLibrary(payload)
    library._mtime = mtime  # type: ignore[attr-defined]
    _CACHE[key] = library
    return library


def save_library(entries: list[dict], version: str, path: Optional[Path] = None) -> Path:
    path = Path(path or config.NATURAL_LIBRARY_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"version": version, "feature_names": SIMILARITY_FEATURES, "entries": entries},
            indent=2,
        )
    )
    _CACHE.pop(str(path), None)
    return path
