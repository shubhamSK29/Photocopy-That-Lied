"""Compression / resampling characteristics.

This detector is intentionally weak. Compression and resizing are ubiquitous in
legitimate smartphone, messaging and social-media pipelines, so its score is
capped and it is only ever used as supporting evidence (and as an input to the
data-coverage estimate).
"""
from __future__ import annotations

import io
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from backend.forensic.common import DetectorResult, blank_heatmap, normalize_map, regions_from_mask

MAX_SCORE = 0.35

# Standard JPEG luminance quantisation table (Annex K).
_STD_LUMA = np.array(
    [
        [16, 11, 10, 16, 24, 40, 51, 61],
        [12, 12, 14, 19, 26, 58, 60, 55],
        [14, 13, 16, 24, 40, 57, 69, 56],
        [14, 17, 22, 29, 51, 87, 80, 62],
        [18, 22, 37, 56, 68, 109, 103, 77],
        [24, 35, 55, 64, 81, 104, 113, 92],
        [49, 64, 78, 87, 103, 121, 120, 101],
        [72, 92, 95, 98, 112, 100, 103, 99],
    ],
    dtype=np.float64,
)


def estimate_jpeg_quality(data: bytes) -> Optional[float]:
    try:
        image = Image.open(io.BytesIO(data))
        tables = getattr(image, "quantization", None)
        if not tables:
            return None
        table = np.array(tables[0], dtype=np.float64)
        if table.size != 64:
            return None
        table = table.reshape(8, 8)
        ratios = table / _STD_LUMA
        scale = float(np.median(ratios)) * 100.0
        quality = (200.0 - scale) / 2.0 if scale > 100 else 100.0 - scale / 2.0
        return float(np.clip(quality, 1.0, 100.0))
    except Exception:
        return None


def _blockiness(gray: np.ndarray) -> tuple[float, np.ndarray]:
    """Compare gradient energy on the JPEG 8x8 grid with off-grid positions."""
    g = gray.astype(np.float32)
    dx = np.abs(np.diff(g, axis=1))
    dy = np.abs(np.diff(g, axis=0))
    cols = np.arange(dx.shape[1])
    rows = np.arange(dy.shape[0])
    on_x = dx[:, (cols % 8) == 7]
    off_x = dx[:, (cols % 8) != 7]
    on_y = dy[(rows % 8) == 7, :]
    off_y = dy[(rows % 8) != 7, :]
    on = float(on_x.mean() + on_y.mean()) / 2.0
    off = float(off_x.mean() + off_y.mean()) / 2.0 + 1e-6
    strength = max(0.0, on / off - 1.0)

    # Local blockiness map: grid-aligned gradient energy per 32x32 tile.
    h, w = gray.shape
    tile = 32
    grid = np.zeros(((h // tile) or 1, (w // tile) or 1), dtype=np.float32)
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            sub = dx[i * tile:(i + 1) * tile, j * tile:(j + 1) * tile]
            if sub.size == 0:
                continue
            sub_cols = np.arange(sub.shape[1])
            on_mask = (sub_cols + j * tile) % 8 == 7
            if on_mask.any() and (~on_mask).any():
                grid[i, j] = float(sub[:, on_mask].mean()) - float(sub[:, ~on_mask].mean())
    grid = np.clip(grid, 0, None)
    heat = cv2.resize(grid, (w, h), interpolation=cv2.INTER_CUBIC)
    return strength, normalize_map(cv2.GaussianBlur(heat, (0, 0), sigmaX=16))


def _resampling_score(gray: np.ndarray) -> float:
    """Periodic peaks in the spectrum of the second derivative hint at resampling."""
    g = gray.astype(np.float32) / 255.0
    lap = cv2.Laplacian(g, cv2.CV_32F)
    row = np.abs(lap).mean(axis=0)
    row = row - row.mean()
    if row.size < 64:
        return 0.0
    spectrum = np.abs(np.fft.rfft(row * np.hanning(row.size)))
    spectrum = spectrum[2:]
    if spectrum.size == 0:
        return 0.0
    peak = float(spectrum.max())
    med = float(np.median(spectrum)) + 1e-6
    return float(np.clip((peak / med - 6.0) / 24.0, 0.0, 1.0))


def detect(bgr: np.ndarray, original_bytes: bytes, image_format: str, original_size: tuple[int, int]) -> DetectorResult:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    quality = estimate_jpeg_quality(original_bytes) if image_format == "JPEG" else None
    blockiness, heat = _blockiness(gray)
    resampling = _resampling_score(gray)
    width, height = original_size

    metrics = {
        "format": image_format,
        "estimated_jpeg_quality": round(quality, 1) if quality is not None else None,
        "blockiness": round(float(blockiness), 4),
        "resampling_score": round(float(resampling), 4),
        "width": width,
        "height": height,
        "megapixels": round(width * height / 1e6, 3),
        "bytes_per_pixel": round(len(original_bytes) / float(width * height), 4),
        "non_standard_dimensions": bool(width % 8 or height % 8),
    }

    notes = []
    if quality is not None and quality < 75:
        notes.append(f"Estimated JPEG quality is low (~{quality:.0f}).")
    if blockiness > 0.25:
        notes.append("Visible 8x8 block structure suggests strong or repeated JPEG compression.")
    if resampling > 0.4:
        notes.append("Periodic interpolation traces suggest the image was resized.")
    if metrics["bytes_per_pixel"] < 0.15 and image_format == "JPEG":
        notes.append("Very low bytes-per-pixel ratio, typical of messaging-app recompression.")

    raw = 0.45 * min(1.0, blockiness / 0.6) + 0.35 * resampling
    if quality is not None:
        raw += 0.20 * float(np.clip((80.0 - quality) / 50.0, 0, 1))
    score = float(np.clip(raw, 0, 1) * MAX_SCORE)

    if image_format != "JPEG" and blockiness < 0.1 and resampling < 0.2:
        status = "not_detected"
    elif notes:
        status = "detected"
    else:
        status = "not_detected"

    explanation = (
        " ".join(notes) + " Compression and resizing are normal in smartphone and messaging "
        "pipelines and are treated only as supporting evidence."
        if notes
        else "No unusual compression or resampling characteristics were measured. "
        "Compression evidence is only ever supporting evidence."
    )

    mask = (heat > 0.75).astype(np.uint8)
    return DetectorResult(
        name="compression",
        status=status,
        score=score,
        heatmap=heat,
        regions=regions_from_mask(mask, min_area_fraction=0.01) if status == "detected" else [],
        explanation=explanation,
        metrics=metrics,
    )
