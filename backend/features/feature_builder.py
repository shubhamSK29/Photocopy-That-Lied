"""Forensic feature vector construction.

Metadata availability is carried for coverage/status reporting only: absence of
EXIF must never increase manipulation evidence, so `metadata_available` is not
part of the model feature list.
"""
from __future__ import annotations

from typing import Any, Optional

from backend.forensic.common import DetectorResult

FEATURE_VERSION = "features-v1"

# Features consumed by the fusion model, in a fixed order.
BASE_FEATURE_NAMES = [
    "copy_move_verified_matches",
    "copy_move_inlier_ratio",
    "copy_move_region_count",
    "copy_move_region_area",
    "patch_max_anomaly",
    "patch_mean_anomaly",
    "patch_anomaly_fraction",
    "compression_score",
    "resampling_score",
    "blockiness",
    "jpeg_quality",
    "image_megapixels",
    "bytes_per_pixel",
    "spatial_iou",
    "spatial_dice",
]

FEATURE_NAMES = BASE_FEATURE_NAMES + ["natural_processing_similarity"]

# Reported alongside the model input but never used to increase evidence.
CONTEXT_FIELDS = [
    "metadata_available",
    "visible_timestamp_detected",
    "copy_move_status",
    "local_anomaly_status",
    "compression_status",
]


def _m(det: Optional[DetectorResult], key: str, default: float = 0.0) -> float:
    if det is None:
        return default
    value = det.metrics.get(key, default)
    return float(value) if isinstance(value, (int, float)) else default


def build_base_features(
    detectors: dict[str, DetectorResult],
    spatial: dict,
    image_info: dict,
) -> dict[str, float]:
    copy_move = detectors.get("copy_move")
    local = detectors.get("local_anomaly")
    comp = detectors.get("compression")

    quality = _m(comp, "estimated_jpeg_quality", default=float("nan"))
    features = {
        "copy_move_verified_matches": _m(copy_move, "verified_match_count"),
        "copy_move_inlier_ratio": _m(copy_move, "inlier_ratio"),
        "copy_move_region_count": float(len(copy_move.regions) if copy_move else 0),
        "copy_move_region_area": _m(copy_move, "region_area_fraction"),
        "patch_max_anomaly": _m(local, "max_anomaly"),
        "patch_mean_anomaly": _m(local, "mean_anomaly"),
        "patch_anomaly_fraction": _m(local, "anomalous_patch_fraction"),
        "compression_score": float(comp.score) if comp is not None else 0.0,
        "resampling_score": _m(comp, "resampling_score"),
        "blockiness": _m(comp, "blockiness"),
        "jpeg_quality": quality,
        "image_megapixels": float(image_info.get("megapixels", 0.0)),
        "bytes_per_pixel": float(image_info.get("bytes_per_pixel", 0.0)),
        "spatial_iou": float(spatial.get("max_iou", 0.0)),
        "spatial_dice": float(spatial.get("max_dice", 0.0)),
    }
    return features


def build_feature_vector(
    base_features: dict[str, float],
    natural_similarity: float,
) -> dict[str, float]:
    features = dict(base_features)
    features["natural_processing_similarity"] = float(natural_similarity)
    return features


def build_context(detectors: dict[str, DetectorResult], metadata: dict) -> dict[str, Any]:
    timestamp = detectors.get("visible_timestamp")
    return {
        "metadata_available": bool(metadata.get("exif_present")),
        "visible_timestamp_detected": bool(timestamp and timestamp.status == "detected"),
        "copy_move_status": detectors["copy_move"].status if "copy_move" in detectors else "not_applicable",
        "local_anomaly_status": detectors["local_anomaly"].status if "local_anomaly" in detectors else "not_applicable",
        "compression_status": detectors["compression"].status if "compression" in detectors else "not_applicable",
    }


def to_ordered_list(features: dict[str, float], names: Optional[list[str]] = None) -> list[float]:
    names = names or FEATURE_NAMES
    return [float(features.get(name, float("nan"))) for name in names]
