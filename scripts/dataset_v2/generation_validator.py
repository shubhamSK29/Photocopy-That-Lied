"""Validation for generated Dataset V2 variants."""

import json
from pathlib import Path
from typing import Dict, List, Any, Set
from PIL import Image
import numpy as np


class GenerationValidator:
    """Validates generated variants against taxonomy rules."""

    def __init__(self, manifest_path: Path, splits_dir: Path):
        """
        Initialize validator.

        Args:
            manifest_path: Path to manifest.jsonl
            splits_dir: Path to splits directory
        """
        self.manifest_path = manifest_path
        self.splits_dir = splits_dir
        self.existing_records: List[Dict[str, Any]] = []
        self.existing_image_ids: Set[str] = set()
        self.existing_variant_ids: Set[str] = set()
        self.existing_hashes: Set[str] = set()
        self._load_manifest()

    def _load_manifest(self):
        """Load existing manifest records."""
        if not self.manifest_path.exists():
            return

        with self.manifest_path.open() as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    self.existing_records.append(record)
                    self.existing_image_ids.add(record.get('image_id', ''))
                    self.existing_variant_ids.add(record.get('variant_id', ''))
                    self.existing_hashes.add(record.get('sha256', ''))

    def validate_batch(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a batch of generated records.

        Args:
            records: List of generated records to validate

        Returns:
            Validation results with errors and warnings
        """
        results = {
            'total': len(records),
            'errors': [],
            'warnings': [],
            'valid': True
        }

        for record in records:
            self._validate_record(record, results)

        results['valid'] = len(results['errors']) == 0
        return results

    def _validate_record(self, record: Dict[str, Any], results: Dict[str, Any]):
        """Validate a single record."""
        image_id = record.get('image_id', 'unknown')

        # Check required fields
        required_fields = [
            'image_id', 'source_id', 'label', 'category',
            'width', 'height', 'format', 'color_mode',
            'generation_method', 'dataset_version'
        ]
        for field in required_fields:
            if field not in record:
                results['errors'].append(f"{image_id}: Missing required field '{field}'")

        # Check for duplicate image IDs
        if record.get('image_id') in self.existing_image_ids:
            results['errors'].append(f"{image_id}: Duplicate image ID")

        # Check for duplicate variant IDs
        if record.get('variant_id') in self.existing_variant_ids:
            results['errors'].append(f"{image_id}: Duplicate variant ID")

        # Check for duplicate hashes
        if record.get('sha256') in self.existing_hashes:
            results['errors'].append(f"{image_id}: Duplicate SHA-256 hash")

        # Validate category and label consistency
        category = record.get('category')
        label = record.get('label')

        if category == 'original':
            if label != 0:
                results['errors'].append(f"{image_id}: Original must have label=0")
            if record.get('manipulation_type'):
                results['errors'].append(f"{image_id}: Original cannot have manipulation_type")
            if record.get('mask_path'):
                results['errors'].append(f"{image_id}: Original cannot have mask")

        elif category == 'natural_processing':
            if label != 0:
                results['errors'].append(f"{image_id}: Natural processing must have label=0")
            if record.get('manipulation_type'):
                results['errors'].append(f"{image_id}: Natural processing cannot have manipulation_type")
            if not record.get('processing_operations'):
                results['errors'].append(f"{image_id}: Natural processing must have processing_operations")

        elif category == 'hard_negative':
            if label != 0:
                results['errors'].append(f"{image_id}: Hard negative must have label=0")
            if record.get('manipulation_type'):
                results['errors'].append(f"{image_id}: Hard negative cannot have manipulation_type")

        elif category == 'manipulated':
            if label != 1:
                results['errors'].append(f"{image_id}: Manipulated must have label=1")
            if not record.get('manipulation_type'):
                results['errors'].append(f"{image_id}: Manipulated must have manipulation_type")
            if not record.get('mask_path'):
                results['errors'].append(f"{image_id}: Manipulated must have mask_path")

        # Validate file existence
        image_path = record.get('image_path')
        if image_path:
            full_path = Path(image_path)
            if not full_path.exists():
                results['errors'].append(f"{image_id}: Image file does not exist: {image_path}")
            else:
                # Validate image is readable
                try:
                    with Image.open(full_path) as img:
                        if img.width != record.get('width'):
                            results['errors'].append(f"{image_id}: Width mismatch")
                        if img.height != record.get('height'):
                            results['errors'].append(f"{image_id}: Height mismatch")
                except Exception as e:
                    results['errors'].append(f"{image_id}: Image unreadable: {e}")

        # Validate mask if present
        mask_path = record.get('mask_path')
        if mask_path:
            full_mask_path = Path(mask_path)
            if not full_mask_path.exists():
                results['errors'].append(f"{image_id}: Mask file does not exist: {mask_path}")
            else:
                try:
                    with Image.open(full_mask_path) as mask:
                        # Check dimensions match image
                        if (mask.width, mask.height) != (record.get('width'), record.get('height')):
                            results['errors'].append(f"{image_id}: Mask dimensions do not match image")

                        # Check mask is not empty
                        mask_array = np.array(mask)
                        if np.sum(mask_array) == 0:
                            results['errors'].append(f"{image_id}: Mask is empty (no manipulated pixels)")
                except Exception as e:
                    results['errors'].append(f"{image_id}: Mask unreadable: {e}")

    def check_split_leakage(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check for source leakage across splits.

        Args:
            records: List of records to check

        Returns:
            Leakage check results
        """
        # Load splits
        splits_file = self.splits_dir / 'splits.json'
        with splits_file.open() as f:
            splits = json.load(f)

        # Build source to split mapping
        source_to_split = {}
        for split_name in ['train', 'validation', 'test']:
            for source_id in splits.get(split_name, []):
                source_to_split[source_id] = split_name

        # Check each record
        sources_in_splits = {'train': set(), 'validation': set(), 'test': set()}
        for record in records:
            source_id = record.get('source_id')
            if source_id in source_to_split:
                split = source_to_split[source_id]
                sources_in_splits[split].add(source_id)

        # Check for overlap
        train_val_overlap = sources_in_splits['train'] & sources_in_splits['validation']
        train_test_overlap = sources_in_splits['train'] & sources_in_splits['test']
        val_test_overlap = sources_in_splits['validation'] & sources_in_splits['test']

        return {
            'train_val_overlap': len(train_val_overlap),
            'train_test_overlap': len(train_test_overlap),
            'val_test_overlap': len(val_test_overlap),
            'has_leakage': bool(train_val_overlap or train_test_overlap or val_test_overlap)
        }
