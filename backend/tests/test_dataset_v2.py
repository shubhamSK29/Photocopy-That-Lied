"""Tests for Dataset V2 pipeline validation.

These tests verify the Dataset V2 infrastructure and validation scripts.
"""

import json
import pytest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

DATASET_V2 = ROOT / "dataset_v2"
METADATA_DIR = DATASET_V2 / "metadata"
SCHEMA_FILE = METADATA_DIR / "schema.json"
MANIFEST_FILE = METADATA_DIR / "manifest.jsonl"


class TestDatasetV2Schema:
    """Test Dataset V2 metadata schema."""
    
    def test_schema_file_exists(self):
        """Schema file should exist."""
        assert SCHEMA_FILE.exists(), "Schema file not found"
    
    def test_schema_is_valid_json(self):
        """Schema should be valid JSON."""
        with SCHEMA_FILE.open() as f:
            data = json.load(f)
        assert isinstance(data, dict), "Schema should be a dictionary"
        assert "fields" in data, "Schema should have 'fields' key"
    
    def test_schema_has_required_fields(self):
        """Schema should define required fields."""
        with SCHEMA_FILE.open() as f:
            data = json.load(f)
        
        required_fields = ["image_id", "source_id", "label", "category", "width", "height", 
                          "format", "color_mode", "generation_method", "metadata_available", 
                          "dataset_version"]
        
        for field in required_fields:
            assert field in data["fields"], f"Schema missing required field: {field}"
            assert data["fields"][field].get("required", False), f"Field {field} should be required"


class TestDatasetV2Manifest:
    """Test Dataset V2 manifest file."""
    
    def test_manifest_file_exists(self):
        """Manifest file should exist."""
        assert MANIFEST_FILE.exists(), "Manifest file not found"
    
    def test_manifest_is_valid_jsonl(self):
        """Manifest should be valid JSONL format."""
        with MANIFEST_FILE.open() as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON on line {line_num}: {e}")


class TestDatasetV2DirectoryStructure:
    """Test Dataset V2 directory structure."""
    
    def test_dataset_v2_directory_exists(self):
        """Dataset V2 directory should exist."""
        assert DATASET_V2.exists(), "Dataset V2 directory not found"
    
    def test_required_subdirectories_exist(self):
        """Required subdirectories should exist."""
        required_dirs = [
            "genuine/original",
            "genuine/natural_processing",
            "manipulated/copy_move",
            "manipulated/splicing",
            "manipulated/object_removal",
            "manipulated/inpainting",
            "manipulated/resampling",
            "manipulated/timestamp",
            "manipulated/mixed",
            "hard_negatives",
            "masks",
            "sources",
            "metadata",
            "splits"
        ]
        
        for dir_path in required_dirs:
            full_path = DATASET_V2 / dir_path
            assert full_path.exists(), f"Required directory not found: {dir_path}"
            assert full_path.is_dir(), f"Path is not a directory: {dir_path}"


class TestDatasetV2Scripts:
    """Test Dataset V2 validation scripts can be imported."""
    
    def test_validate_dataset_v2_imports(self):
        """Validation script should be importable."""
        try:
            import importlib
            spec = importlib.util.spec_from_file_location(
                "validate_dataset_v2",
                ROOT / "scripts" / "validate_dataset_v2.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.fail(f"Failed to import validate_dataset_v2.py: {e}")
    
    def test_create_splits_imports(self):
        """Split creation script should be importable."""
        try:
            import importlib
            spec = importlib.util.spec_from_file_location(
                "create_dataset_v2_splits",
                ROOT / "scripts" / "create_dataset_v2_splits.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.fail(f"Failed to import create_dataset_v2_splits.py: {e}")
    
    def test_detect_duplicates_imports(self):
        """Duplicate detection script should be importable."""
        try:
            import importlib
            spec = importlib.util.spec_from_file_location(
                "detect_duplicates",
                ROOT / "scripts" / "detect_duplicates.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.fail(f"Failed to import detect_duplicates.py: {e}")
    
    def test_audit_leakage_imports(self):
        """Leakage audit script should be importable."""
        try:
            import importlib
            spec = importlib.util.spec_from_file_location(
                "audit_leakage",
                ROOT / "scripts" / "audit_leakage.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.fail(f"Failed to import audit_leakage.py: {e}")
    
    def test_validate_masks_imports(self):
        """Mask validation script should be importable."""
        try:
            import importlib
            spec = importlib.util.spec_from_file_location(
                "validate_masks",
                ROOT / "scripts" / "validate_masks.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.fail(f"Failed to import validate_masks.py: {e}")


class TestDatasetV2Preservation:
    """Test that Dataset V1 is preserved."""
    
    def test_dataset_v1_exists(self):
        """Original Dataset V1 should still exist."""
        dataset_v1 = ROOT / "dataset"
        assert dataset_v1.exists(), "Dataset V1 not found"
        assert dataset_v1.is_dir(), "Dataset V1 is not a directory"
    
    def test_dataset_v1_manifest_exists(self):
        """Dataset V1 manifest should still exist."""
        manifest_v1 = ROOT / "dataset" / "manifests" / "dataset.csv"
        assert manifest_v1.exists(), "Dataset V1 manifest not found"
    
    def test_dataset_v1_images_exist(self):
        """Dataset V1 images should still exist."""
        dataset_v1 = ROOT / "dataset"
        # Check for at least some images
        jpg_files = list(dataset_v1.rglob("*.jpg"))
        assert len(jpg_files) > 0, "Dataset V1 contains no images"


class TestMetadataSchemaValidation:
    """Test metadata schema validation logic."""
    
    def test_label_encoding(self):
        """Label encoding should be 0 or 1."""
        with SCHEMA_FILE.open() as f:
            schema = json.load(f)
        
        label_field = schema["fields"]["label"]
        assert label_field["type"] == "integer"
        assert set(label_field["allowed_values"]) == {0, 1}
    
    def test_category_encoding(self):
        """Category should have specific allowed values."""
        with SCHEMA_FILE.open() as f:
            schema = json.load(f)
        
        category_field = schema["fields"]["category"]
        assert "allowed_values" in category_field
        
        expected_categories = [
            "original", "natural_processing", "hard_negative",
            "copy_move", "splicing", "object_removal", 
            "inpainting", "resampling", "timestamp", "mixed"
        ]
        
        for cat in expected_categories:
            assert cat in category_field["allowed_values"], f"Category {cat} not in allowed values"
    
    def test_mask_encoding_documented(self):
        """Mask encoding should be documented in schema."""
        with SCHEMA_FILE.open() as f:
            schema = json.load(f)
        
        assert "mask_encoding" in schema
        assert "0" in schema["mask_encoding"]["values"]
        assert "1" in schema["mask_encoding"]["values"]


class TestNaturalProcessingLibrary:
    """Test natural processing library foundation."""
    
    def test_natural_processing_library_v2_exists(self):
        """Natural processing library V2 should exist."""
        library_v2 = ROOT / "models" / "natural_processing_library_v2.json"
        assert library_v2.exists(), "Natural processing library V2 not found"
    
    def test_natural_processing_library_v2_valid_json(self):
        """Natural processing library V2 should be valid JSON."""
        library_v2 = ROOT / "models" / "natural_processing_library_v2.json"
        with library_v2.open() as f:
            data = json.load(f)
        assert isinstance(data, dict), "Library should be a dictionary"
        assert "entries" in data, "Library should have 'entries' key"
        assert isinstance(data["entries"], list), "Entries should be a list"
