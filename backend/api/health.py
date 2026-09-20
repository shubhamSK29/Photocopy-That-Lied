"""Health and system status."""
from __future__ import annotations

from fastapi import APIRouter

from backend import config
from backend.calibration import natural_processing
from backend.forensic.timestamp import OCR_AVAILABLE
from backend.fusion.predict import get_model

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health() -> dict:
    model = get_model()
    library = natural_processing.load_library()
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "mode": "trained_model" if model else "demo_fallback",
        "model_version": model.model_version if model else config.MODEL_VERSION_FALLBACK,
        "dataset_version": model.dataset_version if model else config.DATASET_VERSION_FALLBACK,
        "feature_version": config.FEATURE_VERSION,
        "pipeline_version": config.PIPELINE_VERSION,
        "ocr_available": OCR_AVAILABLE,
        "natural_library": {
            "available": library.available,
            "version": library.version,
            "size": len(library.entries),
        },
    }
