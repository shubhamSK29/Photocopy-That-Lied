"""Central configuration for the Photocopy That Lied prototype."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).resolve() if value else default


UPLOAD_DIR = _env_path("PTL_UPLOAD_DIR", BASE_DIR / "uploads")
ARTIFACT_DIR = _env_path("PTL_ARTIFACT_DIR", BASE_DIR / "artifacts")
REPORT_DIR = _env_path("PTL_REPORT_DIR", BASE_DIR / "reports")
MODEL_DIR = _env_path("PTL_MODEL_DIR", BASE_DIR / "models")
DATASET_DIR = _env_path("PTL_DATASET_DIR", BASE_DIR / "dataset")
DB_PATH = _env_path("PTL_DB_PATH", BASE_DIR / "analysis.db")

for _d in (UPLOAD_DIR, ARTIFACT_DIR, REPORT_DIR, MODEL_DIR):
    _d.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE_BYTES = int(os.environ.get("PTL_MAX_FILE_SIZE_MB", "25")) * 1024 * 1024
MAX_PIXELS = int(os.environ.get("PTL_MAX_PIXELS", str(50_000_000)))
MIN_DIMENSION = int(os.environ.get("PTL_MIN_DIMENSION", "64"))
ANALYSIS_MAX_DIM = int(os.environ.get("PTL_ANALYSIS_MAX_DIM", "1600"))

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}

# Review bands are engineering defaults and are configurable.
REVIEW_BAND_LOW = float(os.environ.get("PTL_BAND_LOW", "30"))
REVIEW_BAND_HIGH = float(os.environ.get("PTL_BAND_HIGH", "60"))

MODEL_VERSION_FALLBACK = "fusion-demo-fallback"
DATASET_VERSION_FALLBACK = "dataset-unavailable"
FEATURE_VERSION = "features-v1"
PIPELINE_VERSION = "pipeline-v1"

MODEL_PATH = MODEL_DIR / "fusion_model.joblib"
NATURAL_LIBRARY_PATH = MODEL_DIR / "natural_processing_library.json"

CORS_ORIGINS = os.environ.get(
    "PTL_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")


def risk_band(score: float) -> str:
    if score < REVIEW_BAND_LOW:
        return "No significant manipulation evidence"
    if score < REVIEW_BAND_HIGH:
        return "Review required"
    return "High-priority forensic review"


SYSTEM_LIMITATIONS = [
    "Missing EXIF metadata does not prove manipulation.",
    "Compression artifacts do not prove manipulation.",
    "Resizing does not prove manipulation.",
    "Normal smartphone processing (sharpening, denoising, HDR) can create forensic artifacts.",
    "Timestamp recovery is impossible when no evidence remains in the submitted image.",
    "Heatmaps are approximate forensic signals, not pixel-perfect proof of manipulation.",
    "Low data coverage means the image is outside well-tested operating conditions and reduces confidence.",
    "This system assists human reviewers; it does not determine fraud.",
    "This system must not be used to automatically reject an insurance claim.",
]

DISCLAIMER = (
    "This system provides forensic screening evidence to support human review. "
    "It does not determine fraud or automatically reject insurance claims."
)
