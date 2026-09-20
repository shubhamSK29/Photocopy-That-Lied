"""Upload validation: never trust the filename or the declared MIME type."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, asdict
from typing import Optional

from PIL import Image, UnidentifiedImageError

from backend import config

Image.MAX_IMAGE_PIXELS = config.MAX_PIXELS

_SIGNATURES = {
    b"\xff\xd8\xff": "JPEG",
    b"\x89PNG\r\n\x1a\n": "PNG",
}

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_EXTENSIONS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}


class ValidationError(Exception):
    def __init__(self, message: str, code: str = "invalid_image"):
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass
class ValidatedImage:
    format: str
    mime: str
    width: int
    height: int
    size_bytes: int
    mode: str
    safe_filename: str

    def to_dict(self) -> dict:
        return asdict(self)


def safe_filename(name: Optional[str]) -> str:
    name = (name or "upload").strip().replace("\x00", "")
    name = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    name = _SAFE_NAME.sub("_", name)
    name = name.lstrip(".") or "upload"
    return name[:120]


def sniff_format(data: bytes) -> Optional[str]:
    for sig, fmt in _SIGNATURES.items():
        if data.startswith(sig):
            return fmt
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    return None


def validate_upload(data: bytes, filename: Optional[str], declared_mime: Optional[str] = None) -> ValidatedImage:
    if not data:
        raise ValidationError("Uploaded file is empty.", "empty_file")
    if len(data) > config.MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            f"File exceeds the maximum size of {config.MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
            "file_too_large",
        )

    # The filename is only one signal, but reject unsupported or misleading
    # extensions explicitly so upload validation has a clear user-facing error.
    if filename:
        extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if extension not in _EXTENSIONS:
            raise ValidationError("Filename extension must be .jpg, .jpeg, .png, or .webp.", "invalid_extension")

    sniffed = sniff_format(data)
    if sniffed is None:
        raise ValidationError(
            "File signature is not a supported image type (JPEG, PNG, WebP).",
            "unsupported_format",
        )

    if declared_mime and declared_mime.lower() not in config.ALLOWED_MIME:
        raise ValidationError(
            f"Declared content type '{declared_mime}' is not supported.", "unsupported_mime"
        )

    try:
        probe = Image.open(io.BytesIO(data))
        probe.verify()
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError(f"Image could not be decoded: {exc}", "corrupted_image") from exc

    fmt = (image.format or sniffed).upper()
    if fmt == "MPO":  # multi-picture JPEG produced by some phones
        fmt = "JPEG"
    if fmt not in config.ALLOWED_FORMATS:
        raise ValidationError(f"Image format '{fmt}' is not supported.", "unsupported_format")
    if fmt != sniffed:
        raise ValidationError(
            f"File signature ({sniffed}) does not match decoded format ({fmt}).",
            "format_mismatch",
        )
    if filename and _EXTENSIONS[extension] != fmt:
        raise ValidationError("Filename extension does not match the decoded image format.", "extension_mismatch")

    width, height = image.size
    if width < config.MIN_DIMENSION or height < config.MIN_DIMENSION:
        raise ValidationError(
            f"Image is too small for forensic analysis (minimum {config.MIN_DIMENSION}px per side).",
            "image_too_small",
        )
    if width * height > config.MAX_PIXELS:
        raise ValidationError("Image exceeds the maximum allowed pixel count.", "too_many_pixels")

    mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[fmt]
    return ValidatedImage(
        format=fmt,
        mime=mime,
        width=width,
        height=height,
        size_bytes=len(data),
        mode=image.mode,
        safe_filename=safe_filename(filename),
    )
