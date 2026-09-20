"""Provenance helpers: hashing, ids and version stamps."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from backend import config


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def new_analysis_id() -> str:
    return uuid.uuid4().hex


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def version_block(model_version: str, dataset_version: str) -> dict:
    return {
        "model_version": model_version,
        "dataset_version": dataset_version,
        "feature_version": config.FEATURE_VERSION,
        "pipeline_version": config.PIPELINE_VERSION,
    }
