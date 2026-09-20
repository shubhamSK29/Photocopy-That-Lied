"""EXIF / metadata extraction.

Missing metadata is reported as `unavailable`. It is never treated as evidence of
manipulation.
"""
from __future__ import annotations

import io
from typing import Any, Optional

from PIL import Image, ExifTags

_TAGS = {v: k for k, v in ExifTags.TAGS.items()}
_GPS_TAGS = ExifTags.GPSTAGS

_EDITOR_HINTS = (
    "photoshop", "gimp", "paint.net", "pixlr", "snapseed", "lightroom",
    "picsart", "affinity", "imagemagick", "inkscape", "krita", "canva",
)


def _clean(value: Any, limit: int = 200) -> Any:
    """EXIF strings are attacker controlled; never trust or render them raw."""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        value = "".join(ch for ch in value if ch.isprintable())
        return value.strip()[:limit]
    if isinstance(value, (int, float)):
        return value
    return str(value)[:limit]


def _rational(value: Any) -> Optional[float]:
    try:
        if isinstance(value, tuple) and len(value) == 2:
            return float(value[0]) / float(value[1] or 1)
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _gps(exif: dict) -> Optional[dict]:
    raw = exif.get(_TAGS.get("GPSInfo"))
    if not isinstance(raw, dict):
        return None
    parsed = {}
    for key, value in raw.items():
        name = _GPS_TAGS.get(key, str(key))
        if name in ("GPSLatitude", "GPSLongitude"):
            parts = [_rational(v) for v in value] if isinstance(value, tuple) else []
            if len(parts) == 3 and all(p is not None for p in parts):
                parsed[name] = parts[0] + parts[1] / 60 + parts[2] / 3600
        elif name in ("GPSLatitudeRef", "GPSLongitudeRef"):
            parsed[name] = _clean(value, 4)
    if "GPSLatitude" in parsed and parsed.get("GPSLatitudeRef") == "S":
        parsed["GPSLatitude"] = -parsed["GPSLatitude"]
    if "GPSLongitude" in parsed and parsed.get("GPSLongitudeRef") == "W":
        parsed["GPSLongitude"] = -parsed["GPSLongitude"]
    return parsed or None


def extract_metadata(data: bytes) -> dict:
    result: dict[str, Any] = {
        "status": "unavailable",
        "exif_present": False,
        "camera_make": None,
        "camera_model": None,
        "capture_datetime": None,
        "software": None,
        "orientation": None,
        "gps": None,
        "width": None,
        "height": None,
        "jpeg_info": {},
        "editor_software_hint": False,
        "field_count": 0,
        "notes": [],
    }
    try:
        image = Image.open(io.BytesIO(data))
        result["width"], result["height"] = image.size
        result["jpeg_info"] = {
            "format": image.format,
            "mode": image.mode,
            "quantization_tables": len(getattr(image, "quantization", {}) or {}),
            "progressive": bool(image.info.get("progressive")),
            "icc_profile": bool(image.info.get("icc_profile")),
        }
        exif = image.getexif()
    except Exception as exc:  # pragma: no cover - defensive
        result["notes"].append(f"Metadata parsing failed: {exc}")
        result["status"] = "error"
        return result

    if not exif:
        result["notes"].append(
            "No EXIF metadata present. This is common for screenshots, messaging apps "
            "and social media downloads, and is not evidence of manipulation."
        )
        return result

    merged = dict(exif)
    try:
        merged.update(dict(exif.get_ifd(0x8769)))  # ExifIFD
    except Exception:
        pass
    try:
        gps_ifd = exif.get_ifd(0x8825)
        if gps_ifd:
            merged[_TAGS.get("GPSInfo")] = dict(gps_ifd)
    except Exception:
        pass

    result["exif_present"] = True
    result["status"] = "available"
    result["field_count"] = len(merged)
    result["camera_make"] = _clean(merged.get(_TAGS.get("Make"))) or None
    result["camera_model"] = _clean(merged.get(_TAGS.get("Model"))) or None
    result["software"] = _clean(merged.get(_TAGS.get("Software"))) or None
    result["orientation"] = merged.get(_TAGS.get("Orientation"))
    for tag in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
        value = merged.get(_TAGS.get(tag))
        if value:
            result["capture_datetime"] = _clean(value, 40)
            result["capture_datetime_tag"] = tag
            break
    result["gps"] = _gps(merged)

    software = (result["software"] or "").lower()
    if software and any(hint in software for hint in _EDITOR_HINTS):
        result["editor_software_hint"] = True
        result["notes"].append(
            "Metadata names image-editing software. This is weak contextual evidence "
            "only; editors are also used for legitimate cropping and resizing."
        )
    if not result["capture_datetime"]:
        result["notes"].append("EXIF present but no capture timestamp field was found.")
    return result
