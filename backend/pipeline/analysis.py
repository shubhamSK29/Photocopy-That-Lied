"""End-to-end analysis orchestration.

A failure inside one detector degrades that detector only; the analysis
continues with the remaining evidence.
"""
from __future__ import annotations

import io
import logging
import time
from pathlib import Path
from typing import Any, Callable, Optional

import cv2
import numpy as np
from PIL import Image, ImageOps

from backend import config
from backend.calibration import natural_processing
from backend.calibration.coverage import compute_coverage
from backend.explanations.explanation_engine import build_explanation, build_warnings
from backend.features import feature_builder
from backend.forensic import compression as compression_mod
from backend.forensic import copy_move as copy_move_mod
from backend.forensic import local_anomaly as local_mod
from backend.forensic import metadata as metadata_mod
from backend.forensic import spatial as spatial_mod
from backend.forensic import timestamp as timestamp_mod
from backend.forensic.common import DetectorResult, blank_heatmap
from backend.fusion.predict import predict_evidence
from backend.pipeline import provenance
from backend.pipeline.validator import ValidatedImage
from backend.storage import artifacts

logger = logging.getLogger("ptl.analysis")


def normalize_image(data: bytes) -> tuple[np.ndarray, dict]:
    """Orientation-corrected RGB analysis image at a bounded resolution."""
    image = Image.open(io.BytesIO(data))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    original_w, original_h = image.size
    scale = 1.0
    max_dim = max(image.size)
    if max_dim > config.ANALYSIS_MAX_DIM:
        scale = config.ANALYSIS_MAX_DIM / float(max_dim)
        image = image.resize(
            (max(1, int(original_w * scale)), max(1, int(original_h * scale))),
            Image.LANCZOS,
        )
    rgb = np.array(image)
    info = {
        "analysis_width": rgb.shape[1],
        "analysis_height": rgb.shape[0],
        "analysis_scale": round(scale, 5),
        "orientation_corrected": True,
        "max_analysis_dimension": config.ANALYSIS_MAX_DIM,
    }
    return rgb, info


def _run(name: str, fn: Callable[[], DetectorResult], log: list[dict]) -> DetectorResult:
    start = time.time()
    entry: dict[str, Any] = {"module": name, "start_time": start}
    try:
        result = fn()
        entry.update({"status": result.status, "error": None})
    except Exception as exc:  # detector failure must not break the analysis
        logger.exception("detector %s failed", name)
        result = DetectorResult(
            name=name,
            status="not_applicable",
            score=0.0,
            explanation=f"Detector failed and was skipped: {exc}",
            error=str(exc),
        )
        entry.update({"status": "error", "error": str(exc)})
    entry["duration_ms"] = round((time.time() - start) * 1000, 1)
    log.append(entry)
    return result


def _render_artifacts(analysis_id: str, rgb: np.ndarray, combined: np.ndarray, regions: list[dict]) -> dict:
    artifacts.save_image(analysis_id, "analysis.png", rgb)
    heat_u8 = np.clip(combined * 255.0, 0, 255).astype(np.uint8)
    colored = cv2.applyColorMap(heat_u8, cv2.COLORMAP_JET)
    colored_rgb = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
    artifacts.save_image(analysis_id, "heatmap.png", colored_rgb)

    alpha = np.clip(combined, 0, 1)[..., None] * 0.6
    overlay = (rgb.astype(np.float32) * (1 - alpha) + colored_rgb.astype(np.float32) * alpha)
    overlay = overlay.astype(np.uint8)
    boxed = overlay.copy()
    for region in regions[:6]:
        cv2.rectangle(
            boxed,
            (int(region["x"]), int(region["y"])),
            (int(region["x"] + region["width"]), int(region["y"] + region["height"])),
            (255, 255, 255),
            2,
        )
    artifacts.save_image(analysis_id, "overlay.png", boxed)
    return {
        "analysis_image": "analysis.png",
        "heatmap": "heatmap.png",
        "overlay": "overlay.png",
        "note": "Approximate forensic signal - not pixel-perfect proof of manipulation.",
    }


def analyze_image(
    data: bytes,
    validated: ValidatedImage,
    analysis_id: Optional[str] = None,
    persist: bool = True,
) -> dict:
    analysis_id = analysis_id or provenance.new_analysis_id()
    started = time.time()
    module_log: list[dict] = []

    sha256 = provenance.sha256_bytes(data)
    if persist:
        artifacts.store_original(analysis_id, data, validated.format)

    rgb, norm_info = normalize_image(data)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    shape = gray.shape[:2]

    meta = metadata_mod.extract_metadata(data)

    detectors: dict[str, DetectorResult] = {
        "copy_move": _run("copy_move", lambda: copy_move_mod.detect(gray), module_log),
        "local_anomaly": _run("local_anomaly", lambda: local_mod.detect(bgr), module_log),
        "compression": _run(
            "compression",
            lambda: compression_mod.detect(
                bgr, data, validated.format, (validated.width, validated.height)
            ),
            module_log,
        ),
        "visible_timestamp": _run("visible_timestamp", lambda: timestamp_mod.detect(bgr), module_log),
    }
    for det in detectors.values():
        if det.heatmap is None:
            det.heatmap = blank_heatmap(shape)

    spatial_inputs = {k: v for k, v in detectors.items() if k != "visible_timestamp"}
    combined, spatial_summary = spatial_mod.combine(spatial_inputs, shape)

    image_info = {
        "megapixels": validated.width * validated.height / 1e6,
        "bytes_per_pixel": validated.size_bytes / float(validated.width * validated.height),
    }
    base_features = feature_builder.build_base_features(detectors, spatial_summary, image_info)

    library = natural_processing.load_library()
    natural = library.compare(base_features)
    features = feature_builder.build_feature_vector(
        base_features, natural["natural_processing_similarity"]
    )
    context = feature_builder.build_context(detectors, meta)

    fusion = predict_evidence(features)
    evidence_score = float(fusion["manipulation_evidence"])
    coverage = compute_coverage(
        library, base_features, detectors, image_info, model_trained=not fusion["demo_mode"]
    )
    band = config.risk_band(evidence_score)

    ts_integrity = timestamp_mod.timestamp_integrity(meta, detectors["visible_timestamp"])
    explanation = build_explanation(
        detectors, spatial_summary, natural, ts_integrity, meta, evidence_score, coverage
    )
    warnings = build_warnings(detectors, coverage, natural, meta, fusion, evidence_score)

    all_regions = (
        spatial_summary.get("consensus_regions")
        or detectors["copy_move"].regions
        or detectors["local_anomaly"].regions
    )
    artifact_paths = _render_artifacts(analysis_id, rgb, combined, all_regions) if persist else {}

    record = {
        "analysis_id": analysis_id,
        "created_at": provenance.utc_now_iso(),
        "duration_ms": round((time.time() - started) * 1000, 1),
        "image": {
            "filename": validated.safe_filename,
            "sha256": sha256,
            "file_size": validated.size_bytes,
            "format": validated.format,
            "mime": validated.mime,
            "width": validated.width,
            "height": validated.height,
            "megapixels": round(image_info["megapixels"], 3),
            **norm_info,
        },
        "manipulation_evidence": round(evidence_score, 1),
        "data_coverage": coverage["score"],
        "risk_band": band,
        "bands": {
            "low_threshold": config.REVIEW_BAND_LOW,
            "high_threshold": config.REVIEW_BAND_HIGH,
            "note": "Thresholds are configurable engineering defaults, not universal constants.",
        },
        "detectors": {name: det.to_dict() for name, det in detectors.items()},
        "spatial_agreement": spatial_summary,
        "natural_processing": natural,
        "coverage": coverage,
        "metadata": meta,
        "timestamp_integrity": ts_integrity,
        "features": {k: (None if v != v else round(float(v), 6)) for k, v in features.items()},
        "feature_context": context,
        "fusion": fusion,
        "explanation": explanation,
        "warnings": warnings,
        "limitations": config.SYSTEM_LIMITATIONS,
        "artifacts": artifact_paths,
        "regions": all_regions,
        "versions": provenance.version_block(fusion["model_version"], fusion["dataset_version"]),
        "module_log": module_log,
        "disclaimer": config.DISCLAIMER,
    }
    return record


def to_db_record(record: dict) -> dict:
    image = record["image"]
    return {
        "analysis_id": record["analysis_id"],
        "created_at": record["created_at"],
        "filename": image["filename"],
        "sha256": image["sha256"],
        "file_size": image["file_size"],
        "format": image["format"],
        "width": image["width"],
        "height": image["height"],
        "metadata": record["metadata"],
        "manipulation_score": record["manipulation_evidence"],
        "coverage_score": record["data_coverage"],
        "risk_band": record["risk_band"],
        "copy_move_result": record["detectors"]["copy_move"],
        "local_anomaly_result": record["detectors"]["local_anomaly"],
        "compression_result": record["detectors"]["compression"],
        "timestamp_result": record["timestamp_integrity"],
        "natural_processing_result": record["natural_processing"],
        "spatial_agreement": record["spatial_agreement"],
        "heatmap_path": record["artifacts"].get("heatmap"),
        "report_path": record.get("report_path"),
        "model_version": record["versions"]["model_version"],
        "dataset_version": record["versions"]["dataset_version"],
        "warnings": record["warnings"],
        "payload": record,
    }
