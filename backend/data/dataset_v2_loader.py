"""Dataset V2 data loader for prototype model training and inference.

This loader provides:
- Manifest.jsonl loading
- Portable image path resolution
- Mask loading for manipulated images
- Split isolation enforcement
- Metadata preservation
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np
from PIL import Image

from backend import config


@dataclass
class DatasetV2Sample:
    """A single sample from Dataset V2."""
    image_id: str
    source_id: str
    label: int  # 0 = genuine, 1 = manipulated
    category: str  # original, natural_processing, hard_negative, manipulated
    manipulation_type: Optional[str]  # copy_move, object_removal, object_insertion, splicing
    split: str  # train, validation, test
    image_path: Path
    mask_path: Optional[Path]
    mask_id: Optional[str]
    variant_id: Optional[str]
    parameters: Dict[str, Any]
    manipulation_area_ratio: Optional[float]
    width: int
    height: int
    format: str
    color_mode: str


class DatasetV2Loader:
    """Loader for Dataset V2 with split isolation and portable paths."""

    def __init__(self, dataset_root: Optional[Path] = None):
        self.dataset_root = Path(dataset_root or config.DATASET_DIR)
        self.project_root = self.dataset_root.parent  # Project root is parent of dataset_v2
        self.manifest_path = self.dataset_root / "metadata" / "manifest.jsonl"
        self.split_file = self.dataset_root / "splits" / "splits.json"
        
        # Cache manifest records first
        self.records = self._load_manifest()
        
        # Load splits
        self.splits = self._load_splits()
        
        # Build source_id to filename mapping (for original images)
        self.source_id_to_path = self._build_source_mapping()
        
        # Group by split
        self._by_split = self._group_by_split()

    def _load_splits(self) -> Dict[str, List[str]]:
        """Load split definitions."""
        if not self.split_file.exists():
            raise FileNotFoundError(f"Split file not found: {self.split_file}")
        
        with self.split_file.open() as f:
            return json.load(f)

    def _build_source_mapping(self) -> Dict[str, Path]:
        """Build mapping from source_id to actual DeepWeeds filename using SHA256."""
        source_dir = self.dataset_root / "sources" / "deepweeds_raw" / "images"
        if not source_dir.exists():
            return {}
        
        # Build SHA256 lookup
        sha256_to_path = {}
        for image_file in source_dir.glob("*.jpg"):
            try:
                file_sha256 = hashlib.sha256(image_file.read_bytes()).hexdigest()
                sha256_to_path[file_sha256] = image_file
            except Exception:
                continue
        
        # Map source_id to path using SHA256 from manifest
        source_id_to_path = {}
        for record in self.records:
            if record["category"] == "original":
                source_id = record["source_id"]
                sha256_hash = record.get("sha256", "")
                if sha256_hash and sha256_hash in sha256_to_path:
                    source_id_to_path[source_id] = sha256_to_path[sha256_hash]
        
        return source_id_to_path

    def _load_manifest(self) -> List[Dict[str, Any]]:
        """Load manifest.jsonl."""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")
        
        records = []
        with self.manifest_path.open() as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records

    def _group_by_split(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group records by split."""
        by_split = {"train": [], "validation": [], "test": []}
        
        for record in self.records:
            source_id = record["source_id"]
            if source_id in self.splits["train"]:
                by_split["train"].append(record)
            elif source_id in self.splits["validation"]:
                by_split["validation"].append(record)
            elif source_id in self.splits["test"]:
                by_split["test"].append(record)
        
        return by_split

    def _resolve_image_path(self, record: Dict[str, Any]) -> Path:
        """Resolve portable image path to actual file location."""
        if record["category"] == "original":
            # Use SHA256 mapping for original images
            source_id = record["source_id"]
            if source_id in self.source_id_to_path:
                return self.source_id_to_path[source_id]
            # Fallback to direct path
            return self.dataset_root / "sources" / "deepweeds_raw" / "images" / f"{source_id}.jpg"
        else:
            # Variants have relative paths in manifest
            image_path_str = record.get("image_path", "")
            if image_path_str.startswith("dataset_v2/"):
                # Path is relative to project root
                return self.project_root / image_path_str
            else:
                # Path is relative to dataset_v2
                return self.dataset_root / image_path_str

    def _resolve_mask_path(self, record: Dict[str, Any]) -> Optional[Path]:
        """Resolve mask path for manipulated images."""
        mask_path_str = record.get("mask_path", "")
        if not mask_path_str:
            return None
        
        if mask_path_str.startswith("dataset_v2/"):
            return self.project_root / mask_path_str
        else:
            return self.dataset_root / mask_path_str

    def _record_to_sample(self, record: Dict[str, Any]) -> DatasetV2Sample:
        """Convert manifest record to DatasetV2Sample."""
        image_path = self._resolve_image_path(record)
        mask_path = self._resolve_mask_path(record)
        
        # Get manipulation_area_ratio from parameters
        params = record.get("parameters", {})
        area_ratio = params.get("manipulation_area_ratio")
        
        return DatasetV2Sample(
            image_id=record["image_id"],
            source_id=record["source_id"],
            label=record["label"],
            category=record["category"],
            manipulation_type=record.get("manipulation_type"),
            split=self._get_split_for_source(record["source_id"]),
            image_path=image_path,
            mask_path=mask_path,
            mask_id=record.get("mask_id"),
            variant_id=record.get("variant_id"),
            parameters=params,
            manipulation_area_ratio=area_ratio,
            width=record["width"],
            height=record["height"],
            format=record["format"],
            color_mode=record["color_mode"],
        )

    def _get_split_for_source(self, source_id: str) -> str:
        """Get split assignment for a source_id."""
        if source_id in self.splits["train"]:
            return "train"
        elif source_id in self.splits["validation"]:
            return "validation"
        elif source_id in self.splits["test"]:
            return "test"
        else:
            raise ValueError(f"Source {source_id} not found in any split")

    def load_split(self, split: str) -> List[DatasetV2Sample]:
        """Load all samples from a specific split with isolation enforcement."""
        if split not in ["train", "validation", "test"]:
            raise ValueError(f"Invalid split: {split}")
        
        records = self._by_split[split]
        samples = []
        
        for record in records:
            # Verify split isolation
            actual_split = self._get_split_for_source(record["source_id"])
            if actual_split != split:
                raise ValueError(f"Split isolation violation: {record['source_id']} in {actual_split} but requested {split}")
            
            sample = self._record_to_sample(record)
            samples.append(sample)
        
        return samples

    def load_image(self, sample: DatasetV2Sample) -> np.ndarray:
        """Load image as numpy array (RGB)."""
        if not sample.image_path.exists():
            raise FileNotFoundError(f"Image not found: {sample.image_path}")
        
        image = Image.open(sample.image_path)
        image = image.convert("RGB")
        return np.array(image)

    def load_mask(self, sample: DatasetV2Sample) -> Optional[np.ndarray]:
        """Load mask as numpy array (binary)."""
        if sample.mask_path is None:
            return None
        
        if not sample.mask_path.exists():
            raise FileNotFoundError(f"Mask not found: {sample.mask_path}")
        
        mask = Image.open(sample.mask_path)
        mask_array = np.array(mask)
        
        # Ensure binary (0 or 1)
        if mask_array.max() > 1:
            mask_array = (mask_array > 127).astype(np.uint8)
        
        return mask_array

    def iter_train(self) -> Iterator[DatasetV2Sample]:
        """Iterate over training split."""
        for sample in self.load_split("train"):
            yield sample

    def iter_validation(self) -> Iterator[DatasetV2Sample]:
        """Iterate over validation split."""
        for sample in self.load_split("validation"):
            yield sample

    def iter_test(self) -> Iterator[DatasetV2Sample]:
        """Iterate over test split."""
        for sample in self.load_split("test"):
            yield sample

    def get_statistics(self) -> Dict[str, Any]:
        """Get dataset statistics."""
        stats = {
            "total": len(self.records),
            "by_split": {
                "train": len(self._by_split["train"]),
                "validation": len(self._by_split["validation"]),
                "test": len(self._by_split["test"]),
            },
            "by_category": {},
            "by_manipulation_type": {},
        }
        
        # Count by category
        for record in self.records:
            cat = record["category"]
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
        
        # Count by manipulation type
        for record in self.records:
            if record["category"] == "manipulated":
                manip_type = record.get("manipulation_type", "unknown")
                stats["by_manipulation_type"][manip_type] = stats["by_manipulation_type"].get(manip_type, 0) + 1
        
        return stats


def create_loader(dataset_root: Optional[Path] = None) -> DatasetV2Loader:
    """Factory function to create a DatasetV2Loader."""
    return DatasetV2Loader(dataset_root)
