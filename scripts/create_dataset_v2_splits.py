"""Create source-aware train/validation/test splits for Dataset V2.

This script creates reproducible, source-aware splits ensuring no source leakage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

ROOT = Path(__file__).resolve().parent.parent
DATASET_V2 = ROOT / "dataset_v2"
METADATA_DIR = DATASET_V2 / "metadata"
MANIFEST_FILE = METADATA_DIR / "manifest.jsonl"
SPLITS_DIR = DATASET_V2 / "splits"

RANDOM_SEED = 42


def load_manifest() -> List[Dict]:
    """Load manifest from JSONL."""
    rows = []
    with MANIFEST_FILE.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def create_source_aware_split(rows: List[Dict], train_ratio: float = 0.7, 
                               val_ratio: float = 0.15, test_ratio: float = 0.15,
                               seed: int = RANDOM_SEED) -> Dict[str, List[str]]:
    """Create source-aware train/validation/test split.
    
    Args:
        rows: List of metadata rows
        train_ratio: Proportion for training (default 0.7)
        val_ratio: Proportion for validation (default 0.15)
        test_ratio: Proportion for test (default 0.15)
        seed: Random seed for reproducibility
    
    Returns:
        Dictionary with 'train', 'validation', 'test' keys containing image_id lists
    """
    # Extract arrays for sklearn
    image_ids = np.array([r["image_id"] for r in rows])
    labels = np.array([r["label"] for r in rows])
    source_ids = np.array([r["source_id"] for r in rows])
    
    # Check we have enough sources
    unique_sources = set(source_ids)
    if len(unique_sources) < 3:
        raise ValueError(f"Need at least 3 sources for train/val/test split, got {len(unique_sources)}")
    
    # First split: train vs (val + test)
    splitter = GroupShuffleSplit(
        n_splits=1, 
        test_size=(val_ratio + test_ratio), 
        random_state=seed
    )
    train_idx, val_test_idx = next(splitter.split(
        np.zeros(len(rows)), labels, source_ids
    ))
    
    # Second split: validation vs test
    val_size = val_ratio / (val_ratio + test_ratio)
    inner_splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=val_size,
        random_state=seed + 1
    )
    val_rel_idx, test_rel_idx = next(inner_splitter.split(
        np.zeros(len(val_test_idx)), labels[val_test_idx], source_ids[val_test_idx]
    ))
    
    # Get final indices
    val_idx = val_test_idx[val_rel_idx]
    test_idx = val_test_idx[test_rel_idx]
    
    # Check for source leakage
    train_sources = set(source_ids[train_idx])
    val_sources = set(source_ids[val_idx])
    test_sources = set(source_ids[test_idx])
    
    overlap = (train_sources & val_sources) | (train_sources & test_sources) | (val_sources & test_sources)
    
    if overlap:
        raise ValueError(f"Source leakage detected: {overlap}")
    
    # Build result
    split = {
        "train": image_ids[train_idx].tolist(),
        "validation": image_ids[val_idx].tolist(),
        "test": image_ids[test_idx].tolist()
    }
    
    # Add metadata
    split["metadata"] = {
        "random_seed": seed,
        "train_ratio": train_ratio,
        "validation_ratio": val_ratio,
        "test_ratio": test_ratio,
        "total_images": len(rows),
        "train_images": len(train_idx),
        "validation_images": len(val_idx),
        "test_images": len(test_idx),
        "unique_sources": len(unique_sources),
        "train_sources": len(train_sources),
        "validation_sources": len(val_sources),
        "test_sources": len(test_sources),
        "leakage_check": "PASS",
        "split_method": "GroupShuffleSplit"
    }
    
    return split


def save_splits(split: Dict, output_dir: Path):
    """Save splits to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save each split
    for split_name in ["train", "validation", "test"]:
        split_file = output_dir / f"{split_name}.json"
        with split_file.open("w") as f:
            json.dump({"image_ids": split[split_name]}, f, indent=2)
        print(f"Saved {split_name} split to {split_file}")
    
    # Save combined split file
    combined_file = output_dir / "splits.json"
    with combined_file.open("w") as f:
        json.dump(split, f, indent=2)
    print(f"Saved combined splits to {combined_file}")


def main():
    """Main function."""
    print("Creating source-aware splits for Dataset V2...")
    
    # Load manifest
    rows = load_manifest()
    print(f"Loaded {len(rows)} images from manifest")
    
    # Create splits
    split = create_source_aware_split(rows)
    
    # Print summary
    metadata = split["metadata"]
    print(f"\nSplit Summary:")
    print(f"  Total images: {metadata['total_images']}")
    print(f"  Train: {metadata['train_images']} images ({metadata['train_images']/metadata['total_images']:.1%})")
    print(f"  Validation: {metadata['validation_images']} images ({metadata['validation_images']/metadata['total_images']:.1%})")
    print(f"  Test: {metadata['test_images']} images ({metadata['test_images']/metadata['total_images']:.1%})")
    print(f"  Unique sources: {metadata['unique_sources']}")
    print(f"  Train sources: {metadata['train_sources']}")
    print(f"  Validation sources: {metadata['validation_sources']}")
    print(f"  Test sources: {metadata['test_sources']}")
    print(f"  Leakage check: {metadata['leakage_check']}")
    
    # Save splits
    save_splits(split, SPLITS_DIR)
    
    print("\n✅ Splits created successfully")
    return 0


if __name__ == "__main__":
    exit(main())
