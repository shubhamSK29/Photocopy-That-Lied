"""Data Coverage: how well does this image fit the system's tested conditions?

Coverage is deliberately independent of manipulation evidence. A high evidence
score with low coverage must be read as "evidence found, but outside the tested
operating conditions".
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np

from backend.calibration.natural_processing import NaturalProcessingLibrary
from backend.forensic.common import DetectorResult


def compute_coverage(
    library: NaturalProcessingLibrary,
    base_features: dict[str, float],
    detectors: dict[str, DetectorResult],
    image_info: dict,
    model_trained: bool,
) -> dict[str, Any]:
    components: dict[str, float] = {}
    notes: list[str] = []

    # 1. Similarity of the forensic feature profile to tested data.
    distance = library.coverage_distance(base_features)
    if distance is None:
        components["reference_library"] = 0.25
        notes.append("No natural-processing reference library is available.")
    else:
        components["reference_library"] = float(np.clip(np.exp(-distance / 2.0), 0.0, 1.0))
        if components["reference_library"] < 0.4:
            notes.append(
                "The forensic profile of this image is far from the tested reference conditions."
            )

    # 2. Resolution similarity to the tested range.
    mp = float(image_info.get("megapixels", 0.0))
    if mp <= 0:
        components["resolution"] = 0.3
    elif 0.3 <= mp <= 16.0:
        components["resolution"] = 1.0
    elif mp < 0.3:
        components["resolution"] = float(np.clip(mp / 0.3, 0.1, 1.0))
        notes.append("Image resolution is below the tested range.")
    else:
        components["resolution"] = float(np.clip(1.0 - (mp - 16.0) / 40.0, 0.2, 1.0))
        notes.append("Image resolution is above the tested range.")

    # 3. Compression similarity.
    quality = base_features.get("jpeg_quality")
    if quality is None or not np.isfinite(quality):
        components["compression"] = 0.6
        notes.append("JPEG quality could not be estimated for this format.")
    else:
        components["compression"] = float(np.clip((quality - 25.0) / 55.0, 0.15, 1.0))
        if quality < 45:
            notes.append("Very heavy compression reduces the reliability of pixel statistics.")

    # 4. Detector availability.
    usable = [d for d in detectors.values() if d.status in ("detected", "not_detected")]
    scored = len(usable) / max(1, len(detectors))
    components["detector_availability"] = float(scored)
    unavailable = [d.name for d in detectors.values() if d.status in ("insufficient_evidence", "not_applicable")]
    if unavailable:
        notes.append("Detectors without usable output: " + ", ".join(unavailable) + ".")

    # 5. Image quality proxy (texture available for analysis).
    local = detectors.get("local_anomaly")
    patch_count = float(local.metrics.get("patch_count", 0)) if local else 0.0
    components["image_quality"] = float(np.clip(patch_count / 200.0, 0.2, 1.0))

    # 6. Model provenance.
    components["model_trained"] = 1.0 if model_trained else 0.4
    if not model_trained:
        notes.append("No trained fusion model is loaded; the deterministic fallback is in use.")

    weights = {
        "reference_library": 0.3,
        "resolution": 0.15,
        "compression": 0.15,
        "detector_availability": 0.2,
        "image_quality": 0.1,
        "model_trained": 0.1,
    }
    score = sum(components[k] * w for k, w in weights.items()) * 100.0
    score = float(np.clip(score, 0.0, 100.0))

    level = "high" if score >= 70 else "moderate" if score >= 45 else "low"
    if level == "low":
        notes.append(
            "Data coverage is low: this image lies outside the system's well-tested operating "
            "conditions, so the evidence score should be interpreted with extra caution."
        )

    return {
        "score": round(score, 1),
        "level": level,
        "components": {k: round(v, 3) for k, v in components.items()},
        "weights": weights,
        "notes": notes,
    }
