"""Analysis endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend import config
from backend.pipeline import analysis as analysis_pipeline
from backend.pipeline.validator import ValidationError, validate_upload
from backend.storage import artifacts, database

router = APIRouter(prefix="/api", tags=["analysis"])
logger = logging.getLogger("ptl.api")


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)) -> dict:
    data = await file.read()
    try:
        validated = validate_upload(data, file.filename, file.content_type)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})

    try:
        record = analysis_pipeline.analyze_image(data, validated)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("analysis failed")
        raise HTTPException(
            status_code=500,
            detail={"code": "analysis_failed", "message": f"Analysis failed: {exc}"},
        )

    database.save_analysis(analysis_pipeline.to_db_record(record))
    return record


@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str) -> dict:
    record = database.get_analysis(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Unknown analysis id"})
    return record


@router.get("/analyses")
async def list_analyses(limit: int = 25) -> dict:
    return {"items": database.list_analyses(limit=min(max(limit, 1), 100))}


@router.get("/artifacts/{analysis_id}/{name}")
async def get_artifact(analysis_id: str, name: str) -> FileResponse:
    try:
        path = artifacts.resolve_artifact(analysis_id, name)
    except (ValueError, FileNotFoundError):
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Unknown artifact"})
    return FileResponse(path)


@router.get("/config")
async def get_config() -> dict:
    return {
        "max_file_size_mb": config.MAX_FILE_SIZE_BYTES // (1024 * 1024),
        "allowed_formats": sorted(config.ALLOWED_FORMATS),
        "review_bands": {
            "low_threshold": config.REVIEW_BAND_LOW,
            "high_threshold": config.REVIEW_BAND_HIGH,
        },
        "limitations": config.SYSTEM_LIMITATIONS,
        "disclaimer": config.DISCLAIMER,
    }
