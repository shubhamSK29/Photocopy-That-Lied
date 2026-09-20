"""Stable variant ID generation for Dataset V2."""

import hashlib
import json
from typing import Dict, Any


def generate_variant_id(
    parent_image_id: str,
    category: str,
    operation: str,
    parameters: Dict[str, Any],
    seed: int = None
) -> str:
    """
    Generate a deterministic variant ID.

    The ID depends on stable information only:
    - parent_image_id
    - category
    - operation
    - parameters
    - seed (if provided)

    The same inputs always produce the same ID.
    Order of operations or iteration does not affect the ID.

    Args:
        parent_image_id: ID of the parent image
        category: Variant category (natural_processing, manipulated, hard_negative)
        operation: Specific operation (e.g., jpeg_recompression, copy_move)
        parameters: Operation parameters
        seed: Random seed (if applicable)

    Returns:
        Stable variant ID
    """
    # Create deterministic input string
    input_data = {
        'parent': parent_image_id,
        'category': category,
        'operation': operation,
        'parameters': parameters,
    }
    if seed is not None:
        input_data['seed'] = seed

    # Sort keys for consistent string representation
    input_str = json.dumps(input_data, sort_keys=True)

    # Generate SHA-256 hash
    hash_hex = hashlib.sha256(input_str.encode()).hexdigest()

    # Create readable ID prefix based on category
    category_prefixes = {
        'natural_processing': 'NP',
        'manipulated': 'M',
        'hard_negative': 'HN',
    }
    prefix = category_prefixes.get(category, 'VAR')

    # Use first 16 characters of hash for compact ID
    return f"{parent_image_id}_{prefix}_{operation.upper()}_{hash_hex[:16]}"
