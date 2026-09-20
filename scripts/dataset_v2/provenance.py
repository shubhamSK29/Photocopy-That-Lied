"""Provenance record building for Dataset V2 variants."""

import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image
import numpy as np


def compute_sha256(image_path: Path) -> str:
    """Compute SHA-256 hash of an image file."""
    sha256_hash = hashlib.sha256()
    with image_path.open('rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def compute_manipulation_area_ratio(mask_path: Path) -> float:
    """
    Compute the ratio of manipulated pixels to total pixels in a mask.
    
    Args:
        mask_path: Path to the mask file
        
    Returns:
        Ratio of manipulated pixels (0.0 to 1.0)
    """
    try:
        mask = Image.open(mask_path)
        mask_array = np.array(mask)
        
        # Count non-zero pixels
        manipulated_pixels = np.count_nonzero(mask_array)
        total_pixels = mask_array.size
        
        if total_pixels == 0:
            return 0.0
        
        return manipulated_pixels / total_pixels
    except Exception as e:
        print(f"Error computing manipulation area ratio for {mask_path}: {e}")
        return 0.0


def get_image_properties(image_path: Path) -> Dict[str, Any]:
    """Extract image properties."""
    with Image.open(image_path) as img:
        return {
            'width': img.width,
            'height': img.height,
            'format': img.format if img.format else 'JPEG',
            'color_mode': img.mode,
        }


def build_provenance_record(
    image_id: str,
    source_id: str,
    parent_image_id: str,
    parent_source_id: str,
    variant_id: str,
    category: str,
    label: int,
    generation_method: str,
    processing_operations: list,
    image_path: str,
    mask_path: Optional[str] = None,
    mask_id: Optional[str] = None,
    manipulation_type: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None,
    dataset_version: str = "dataset-real-v1",
    metadata_available: bool = False,
    provenance: Optional[Dict[str, Any]] = None,
    root_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Build a complete provenance record for a generated variant.

    Args:
        image_id: Unique image identifier
        source_id: Source identifier
        parent_image_id: Parent image ID
        parent_source_id: Parent source ID
        variant_id: Variant identifier
        category: Category (original, natural_processing, manipulated, hard_negative)
        label: Label (0 or 1)
        generation_method: How the image was generated
        processing_operations: List of operations applied
        image_path: Relative path to the image file
        mask_path: Relative path to mask (if applicable)
        mask_id: Mask identifier (if applicable)
        manipulation_type: Type of manipulation (if applicable)
        parameters: Generation parameters
        seed: Random seed used
        dataset_version: Dataset version
        metadata_available: Whether EXIF metadata is available
        provenance: Additional provenance information
        root_path: Root path for resolving relative paths

    Returns:
        Complete provenance record dictionary
    """
    # Resolve image path
    if root_path:
        image_full_path = root_path / image_path
    else:
        image_full_path = Path(image_path)
    
    # Compute image properties and hash
    props = get_image_properties(image_full_path)
    sha256 = compute_sha256(image_full_path)

    record = {
        'image_id': image_id,
        'source_id': source_id,
        'parent_image_id': parent_image_id,
        'parent_source_id': parent_source_id,
        'variant_id': variant_id,
        'label': label,
        'category': category,
        'width': props['width'],
        'height': props['height'],
        'format': props['format'],
        'color_mode': props['color_mode'],
        'generation_method': generation_method,
        'processing_operations': processing_operations,
        'image_path': image_path,
        'sha256': sha256,
        'dataset_version': dataset_version,
        'metadata_available': metadata_available,
    }

    # Optional fields
    if mask_path:
        record['mask_path'] = mask_path
        # Compute manipulation area ratio if mask exists
        if root_path:
            mask_full_path = root_path / mask_path
            area_ratio = compute_manipulation_area_ratio(mask_full_path)
            if parameters is None:
                parameters = {}
            parameters['manipulation_area_ratio'] = area_ratio
    if mask_id:
        record['mask_id'] = mask_id
    if manipulation_type:
        record['manipulation_type'] = manipulation_type
    if parameters:
        record['parameters'] = parameters
    if seed is not None:
        record['seed'] = seed
    if provenance:
        record['provenance'] = provenance

    return record
