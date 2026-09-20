"""Controlled local storage for uploads and generated forensic artifacts."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from backend import config

_EXT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def upload_dir(analysis_id: str) -> Path:
    d = config.UPLOAD_DIR / analysis_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def artifact_dir(analysis_id: str) -> Path:
    d = config.ARTIFACT_DIR / analysis_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def store_original(analysis_id: str, data: bytes, image_format: str) -> Path:
    """Write the original bytes untouched. Never overwrite an existing original."""
    path = upload_dir(analysis_id) / f"original{_EXT.get(image_format, '.bin')}"
    if path.exists():
        raise FileExistsError(f"Original for analysis {analysis_id} already exists")
    path.write_bytes(data)
    return path


def save_image(analysis_id: str, name: str, image: np.ndarray | Image.Image) -> Path:
    path = artifact_dir(analysis_id) / name
    if isinstance(image, np.ndarray):
        arr = image
        if arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)
        Image.fromarray(arr).save(path)
    else:
        image.save(path)
    return path


def relative_artifact(path: Optional[Path]) -> Optional[str]:
    """Return an artifact path relative to the artifact root (never absolute)."""
    if path is None:
        return None
    try:
        return str(Path(path).resolve().relative_to(config.ARTIFACT_DIR.resolve()))
    except ValueError:
        return None


def resolve_artifact(analysis_id: str, rel_name: str) -> Path:
    """Resolve an artifact request safely inside the analysis artifact directory."""
    root = (config.ARTIFACT_DIR / analysis_id).resolve()
    target = (root / rel_name).resolve()
    if root not in target.parents and target != root:
        raise ValueError("Artifact path escapes the artifact directory")
    if not target.is_file():
        raise FileNotFoundError(rel_name)
    return target
