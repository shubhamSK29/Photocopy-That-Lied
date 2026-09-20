"""Visible (burned-in) timestamp detection.

A timestamp rendered into the pixels is reported as an observation only. The
module never claims the timestamp is genuine, and never claims it is forged.
"""
from __future__ import annotations

import re
from typing import Optional

import cv2
import numpy as np

from backend.forensic.common import DetectorResult, blank_heatmap, normalize_map

try:  # OCR is optional; the module degrades gracefully without it.
    import pytesseract

    pytesseract.get_tesseract_version()
    OCR_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    pytesseract = None
    OCR_AVAILABLE = False

_DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b"),
    re.compile(r"\b(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})\b"),
    re.compile(r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{2,4})\b", re.I),
]
_TIME_PATTERN = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?\b")


def _corner_rois(shape: tuple[int, int]) -> dict[str, tuple[int, int, int, int]]:
    h, w = shape
    bh, bw = max(40, int(h * 0.18)), max(80, int(w * 0.55))
    return {
        "bottom-right": (w - bw, h - bh, bw, bh),
        "bottom-left": (0, h - bh, bw, bh),
        "top-right": (w - bw, 0, bw, bh),
        "top-left": (0, 0, bw, bh),
        "bottom-center": (max(0, (w - bw) // 2), h - bh, bw, bh),
    }


def _ocr(image: np.ndarray) -> list[dict]:
    if not OCR_AVAILABLE:
        return []
    config = "--psm 7"
    data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
    words = []
    for i, text in enumerate(data["text"]):
        text = (text or "").strip()
        conf = float(data["conf"][i]) if data["conf"][i] not in ("-1", -1) else -1.0
        if text and conf >= 0:
            words.append(
                {
                    "text": text,
                    "conf": conf / 100.0,
                    "box": (data["left"][i], data["top"][i], data["width"][i], data["height"][i]),
                }
            )
    return words


def _match_datetime(text: str) -> Optional[str]:
    for pattern in _DATE_PATTERNS:
        m = pattern.search(text)
        if m:
            time_match = _TIME_PATTERN.search(text)
            return f"{m.group(0)} {time_match.group(0)}" if time_match else m.group(0)
    return None


def detect(bgr: np.ndarray) -> DetectorResult:
    h, w = bgr.shape[:2]
    heatmap = blank_heatmap((h, w))
    metrics: dict = {"ocr_available": OCR_AVAILABLE, "regions_scanned": 0}

    if not OCR_AVAILABLE:
        return DetectorResult(
            name="visible_timestamp",
            status="not_applicable",
            score=0.0,
            heatmap=heatmap,
            explanation="OCR support is not installed, so burned-in timestamps cannot be read.",
            metrics=metrics,
        )

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    best: Optional[dict] = None
    for location, (x, y, rw, rh) in _corner_rois((h, w)).items():
        roi = gray[y:y + rh, x:x + rw]
        if roi.size == 0:
            continue
        metrics["regions_scanned"] += 1
        scaled = cv2.resize(roi, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        for variant in (scaled, cv2.bitwise_not(scaled)):
            try:
                words = _ocr(variant)
            except Exception as exc:  # pragma: no cover - OCR runtime failure
                return DetectorResult(
                    name="visible_timestamp",
                    status="insufficient_evidence",
                    score=0.0,
                    heatmap=heatmap,
                    explanation=f"OCR failed on this image ({exc}).",
                    metrics=metrics,
                    error=str(exc),
                )
            if not words:
                continue
            line = " ".join(word["text"] for word in words)
            matched = _match_datetime(line)
            if not matched:
                continue
            confidence = float(np.mean([word["conf"] for word in words]))
            candidate = {
                "text": matched[:60],
                "raw_line": line[:120],
                "location": location,
                "confidence": round(confidence, 3),
                "bounding_box": {"x": int(x), "y": int(y), "width": int(rw), "height": int(rh)},
            }
            if best is None or candidate["confidence"] > best["confidence"]:
                best = candidate

    if best is None:
        return DetectorResult(
            name="visible_timestamp",
            status="not_detected",
            score=0.0,
            heatmap=heatmap,
            explanation="No date-like text was found rendered into the image pixels.",
            metrics=metrics,
        )

    box = best["bounding_box"]
    heat = blank_heatmap((h, w))
    heat[box["y"]:box["y"] + box["height"], box["x"]:box["x"] + box["width"]] = 1.0
    heat = normalize_map(cv2.GaussianBlur(heat, (0, 0), sigmaX=12))

    metrics.update(best)
    return DetectorResult(
        name="visible_timestamp",
        status="detected",
        score=0.0,  # presence of a visible timestamp is not manipulation evidence
        heatmap=heat,
        regions=[{**box, "point_count": 0, "area_fraction": round(box["width"] * box["height"] / float(w * h), 5)}],
        explanation=(
            f"A visible timestamp '{best['text']}' was read in the {best['location']} of the image "
            f"(OCR confidence {best['confidence']:.2f}). Burned-in text can be added by a camera app "
            "or by an editor; its authenticity cannot be established from the pixels alone."
        ),
        metrics=metrics,
    )


def timestamp_integrity(metadata: dict, visible: DetectorResult) -> dict:
    """Combine EXIF and visible-timestamp observations without over-claiming."""
    exif_time = metadata.get("capture_datetime")
    visible_detected = visible.status == "detected"
    visible_text = visible.metrics.get("text") if visible_detected else None

    if exif_time:
        exif_status = "available"
        exif_note = f"EXIF capture timestamp: {exif_time}."
    else:
        exif_status = "unavailable"
        exif_note = (
            "No EXIF capture timestamp is present. Metadata is routinely stripped by messaging "
            "apps, social platforms and screenshots; its absence is not evidence of manipulation."
        )

    if exif_time and visible_detected:
        verification = "partial"
        summary = (
            "Both an EXIF timestamp and a burned-in timestamp are present. They can be compared "
            "manually by the reviewer, but neither can be authenticated from the image alone."
        )
    elif exif_time:
        verification = "metadata_only"
        summary = (
            "Only an EXIF timestamp is available. EXIF fields can be edited, so this is an "
            "unverified claim about capture time."
        )
    elif visible_detected:
        verification = "pixel_text_only"
        summary = (
            "Only a burned-in timestamp is available. Rendered text can be produced by a camera "
            "app or added afterwards, so it cannot be authenticated."
        )
    else:
        verification = "not_possible"
        summary = (
            "Timestamp verification is not possible from the available image evidence. If metadata "
            "was removed after an edit, no recoverable trace of the original timestamp remains in "
            "the pixels. The system does not attempt to recover it."
        )

    return {
        "exif_timestamp": exif_time,
        "exif_status": exif_status,
        "exif_note": exif_note,
        "visible_timestamp_detected": visible_detected,
        "visible_timestamp_text": visible_text,
        "visible_timestamp_location": visible.metrics.get("location") if visible_detected else None,
        "visible_timestamp_confidence": visible.metrics.get("confidence") if visible_detected else None,
        "visible_timestamp_status": visible.status,
        "verification": verification,
        "summary": summary,
    }
