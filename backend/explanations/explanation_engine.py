"""Rule-based explanation layer written for a non-technical reviewer."""
from __future__ import annotations

from typing import Any

from backend import config
from backend.forensic.common import DetectorResult

STRENGTH_ORDER = {"strong": 3, "moderate": 2, "weak": 1, "none": 0, "unavailable": -1}


def _copy_move_strength(det: DetectorResult) -> str:
    if det.status in ("insufficient_evidence", "not_applicable"):
        return "unavailable"
    if det.status == "not_detected":
        return "none"
    matches = float(det.metrics.get("verified_match_count", 0))
    ratio = float(det.metrics.get("inlier_ratio", 0.0))
    if matches >= 20 and ratio >= 0.2:
        return "strong"
    if matches >= 10:
        return "moderate"
    return "weak"


def _local_strength(det: DetectorResult) -> str:
    if det.status in ("insufficient_evidence", "not_applicable"):
        return "unavailable"
    if det.status == "not_detected":
        return "none"
    z = float(det.metrics.get("max_anomaly", 0.0))
    if z >= 8:
        return "strong"
    if z >= 5:
        return "moderate"
    return "weak"


def _compression_strength(det: DetectorResult) -> str:
    if det.status in ("insufficient_evidence", "not_applicable"):
        return "unavailable"
    # Compression is capped at "weak" by design.
    return "weak" if det.status == "detected" else "none"


def _spatial_strength(spatial: dict) -> str:
    level = spatial.get("agreement_level", "none")
    return {"strong": "strong", "moderate": "moderate", "weak": "weak", "none": "none"}[level]


def _natural_strength(natural: dict) -> str:
    if natural.get("status") != "available":
        return "unavailable"
    similarity = float(natural.get("natural_processing_similarity", 0.0))
    if similarity >= 0.6:
        return "strong"
    if similarity >= 0.35:
        return "moderate"
    return "weak"


def build_explanation(
    detectors: dict[str, DetectorResult],
    spatial: dict,
    natural: dict,
    timestamp_integrity: dict,
    metadata: dict,
    evidence_score: float,
    coverage: dict,
) -> dict[str, Any]:
    copy_move = detectors["copy_move"]
    local = detectors["local_anomaly"]
    compression = detectors["compression"]

    summary_rows = [
        {"detector": "Copy-Move", "status": copy_move.status, "strength": _copy_move_strength(copy_move)},
        {"detector": "Local Anomaly", "status": local.status, "strength": _local_strength(local)},
        {"detector": "Compression", "status": compression.status, "strength": _compression_strength(compression)},
        {"detector": "Natural Match", "status": natural.get("status", "unavailable"), "strength": _natural_strength(natural)},
        {"detector": "Spatial Agreement", "status": "detected" if spatial.get("max_dice", 0) > 0 else "not_detected",
         "strength": _spatial_strength(spatial)},
    ]

    strong: list[str] = []
    moderate: list[str] = []
    weak: list[str] = []
    unavailable: list[str] = []

    if _copy_move_strength(copy_move) in ("strong", "moderate"):
        strong.append(
            f"Verified duplicated-region (copy-move) evidence: "
            f"{int(copy_move.metrics.get('verified_match_count', 0))} geometrically consistent matches."
        )
    elif copy_move.status == "detected":
        moderate.append("Weak duplicated-region evidence was verified but involves few matches.")
    elif copy_move.status in ("insufficient_evidence", "not_applicable"):
        unavailable.append(f"Copy-move analysis: {copy_move.explanation}")

    if spatial.get("agreement_level") == "strong":
        strong.append(
            "Independent detectors highlight the same localised area "
            f"(Dice {spatial.get('max_dice', 0):.2f})."
        )
    elif spatial.get("agreement_level") == "moderate":
        moderate.append(
            f"Partial spatial agreement between detectors (Dice {spatial.get('max_dice', 0):.2f})."
        )

    if local.status == "detected":
        target = moderate if _local_strength(local) != "strong" else strong
        target.append(
            "Localised image-processing inconsistency: "
            f"{local.metrics.get('anomalous_patch_count', 0)} patches deviate from the image-wide "
            f"distribution (max robust z = {local.metrics.get('max_anomaly', 0):.1f})."
        )
    elif local.status in ("insufficient_evidence", "not_applicable"):
        unavailable.append(f"Local anomaly analysis: {local.explanation}")

    if compression.status == "detected":
        weak.append(compression.explanation)
    elif compression.status in ("insufficient_evidence", "not_applicable"):
        unavailable.append(f"Compression analysis: {compression.explanation}")

    if metadata.get("editor_software_hint"):
        weak.append(
            f"Metadata names editing software ({metadata.get('software')}). Weak contextual evidence only."
        )
    if not metadata.get("exif_present"):
        unavailable.append(
            "Metadata: unavailable. Missing EXIF is common and is not evidence of manipulation."
        )

    if natural.get("status") == "available":
        natural_line = natural.get("interpretation", "")
    else:
        natural_line = natural.get("interpretation", "Natural-processing comparison unavailable.")
        unavailable.append("Natural-processing reference comparison unavailable.")

    if strong:
        primary = strong[0]
    elif moderate:
        primary = moderate[0]
    elif weak:
        primary = weak[0]
    else:
        primary = "No forensic detector produced positive manipulation evidence."

    supporting = [line for line in (strong[1:] + moderate) if line != primary]

    narrative_parts = [
        f"Primary evidence:\n{primary}",
        "Supporting evidence:\n" + ("\n".join(f"- {s}" for s in supporting) if supporting else "None."),
        "Weak / contextual signals:\n" + ("\n".join(f"- {w}" for w in weak) if weak else "None."),
        f"Natural-processing check:\n{natural_line}",
        f"Metadata:\n{'Available.' if metadata.get('exif_present') else 'Unavailable.'}",
        f"Timestamp:\n{timestamp_integrity.get('summary', '')}",
        f"Data coverage:\n{coverage.get('score')} / 100 ({coverage.get('level')}).",
        f"Reviewer action:\n{config.risk_band(evidence_score)}.",
    ]

    return {
        "summary_rows": summary_rows,
        "primary_evidence": primary,
        "strong_evidence": strong,
        "moderate_evidence": moderate,
        "weak_evidence": weak,
        "unavailable_evidence": unavailable,
        "natural_processing_note": natural_line,
        "narrative": "\n\n".join(narrative_parts),
        "disclaimer": config.DISCLAIMER,
    }


def build_warnings(
    detectors: dict[str, DetectorResult],
    coverage: dict,
    natural: dict,
    metadata: dict,
    fusion: dict,
    evidence_score: float,
) -> list[str]:
    warnings: list[str] = []
    if fusion.get("demo_mode"):
        warnings.append(
            "DEMO MODE: no trained fusion model is loaded; scores come from a deterministic "
            "fallback rule, not a calibrated ML model."
        )
    if coverage.get("level") == "low":
        warnings.append(
            f"Low data coverage ({coverage.get('score')}/100): this image is outside the system's "
            "well-tested conditions, so the evidence score is less reliable."
        )
    elif coverage.get("level") == "moderate" and evidence_score >= config.REVIEW_BAND_LOW:
        warnings.append(
            f"Moderate data coverage ({coverage.get('score')}/100): interpret the evidence score with care."
        )
    for det in detectors.values():
        if det.status == "insufficient_evidence":
            warnings.append(f"{det.name}: insufficient evidence (this is not the same as a score of zero).")
        if det.status == "not_applicable":
            warnings.append(f"{det.name}: detector not applicable to this image.")
        if det.error:
            warnings.append(f"{det.name}: detector error - {det.error}")
    if not metadata.get("exif_present"):
        warnings.append("EXIF metadata is unavailable; timestamp and device claims cannot be checked.")
    if natural.get("status") != "available":
        warnings.append("Natural-processing reference library unavailable; artifacts could not be calibrated.")
    warnings.append(config.DISCLAIMER)
    return warnings
