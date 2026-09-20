"""Evidence fusion at inference time.

If no trained model is available the system runs a clearly labelled deterministic
fallback (DEMO MODE). The fallback is never presented as a trained model.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np

from backend import config
from backend.features.feature_builder import FEATURE_NAMES, to_ordered_list
from backend.fusion.model import TrainedModel, load_model

_CACHE: dict[str, Any] = {"path": None, "mtime": None, "model": None}


def get_model(path: Optional[Path] = None) -> Optional[TrainedModel]:
    path = Path(path or config.MODEL_PATH)
    mtime = path.stat().st_mtime if path.exists() else None
    if _CACHE["path"] == str(path) and _CACHE["mtime"] == mtime:
        return _CACHE["model"]
    model = load_model(path)
    _CACHE.update({"path": str(path), "mtime": mtime, "model": model})
    return model


def _fallback_probability(features: dict[str, float]) -> float:
    """Deterministic weighted fusion used only in DEMO MODE."""
    copy_move = float(np.clip(features.get("copy_move_inlier_ratio", 0.0) / 0.4, 0, 1))
    matches = float(np.tanh(features.get("copy_move_verified_matches", 0.0) / 25.0))
    patch = float(np.clip((features.get("patch_max_anomaly", 0.0) - 3.5) / 6.0, 0, 1))
    fraction = float(np.clip(features.get("patch_anomaly_fraction", 0.0) / 0.15, 0, 1))
    spatial = float(np.clip(features.get("spatial_dice", 0.0) / 0.5, 0, 1))
    compression = float(np.clip(features.get("compression_score", 0.0) / 0.35, 0, 1))
    natural = float(np.clip(features.get("natural_processing_similarity", 0.5), 0, 1))

    evidence = (
        0.34 * max(copy_move, matches)
        + 0.24 * patch
        + 0.12 * fraction
        + 0.20 * spatial
        + 0.10 * compression  # supporting evidence only
    )
    # A good natural-processing explanation reduces unexplained suspicion, but it
    # can never fully cancel strong duplication evidence.
    damping = 1.0 - 0.35 * natural
    strong_duplication = max(copy_move, matches) > 0.5
    if strong_duplication:
        damping = max(damping, 0.85)
    return float(np.clip(evidence * damping, 0.0, 1.0))


def predict_evidence(features: dict[str, float], model_path: Optional[Path] = None) -> dict:
    model = get_model(model_path)
    if model is None:
        probability = _fallback_probability(features)
        return {
            "manipulation_evidence": round(probability * 100.0, 1),
            "probability": round(probability, 4),
            "mode": "demo_fallback",
            "demo_mode": True,
            "model_version": config.MODEL_VERSION_FALLBACK,
            "dataset_version": config.DATASET_VERSION_FALLBACK,
            "model_kind": "deterministic_rule_fusion",
            "note": (
                "DEMO MODE: no trained fusion model is loaded. Scores come from a deterministic "
                "weighted rule, not from a calibrated machine-learning model."
            ),
        }

    expected, received = set(model.feature_names), set(features)
    missing = sorted(expected - received)
    unexpected = sorted(received - expected)
    if missing or unexpected:
        detail = []
        if missing:
            detail.append(f"missing features: {', '.join(missing)}")
        if unexpected:
            detail.append(f"unexpected features: {', '.join(unexpected)}")
        raise ValueError("Feature schema mismatch for trained fusion model (" + "; ".join(detail) + ").")
    row = np.array([to_ordered_list(features, model.feature_names)], dtype=float)
    probability = float(model.predict_proba(row)[0])
    return {
        "manipulation_evidence": round(probability * 100.0, 1),
        "probability": round(probability, 4),
        "mode": "trained_model",
        "demo_mode": False,
        "model_version": model.model_version,
        "dataset_version": model.dataset_version,
        "model_kind": model.kind,
        "note": (
            "Calibrated fusion model output. The score represents the amount of detected "
            "manipulation evidence under the system's validation conditions."
        ),
        "validation_metrics": model.metrics.get("test", {}),
    }


def feature_order(model_path: Optional[Path] = None) -> list[str]:
    model = get_model(model_path)
    return model.feature_names if model else FEATURE_NAMES
