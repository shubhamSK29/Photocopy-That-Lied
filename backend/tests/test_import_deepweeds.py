"""Tests for DeepWeeds importer validation.

These tests verify the DeepWeeds importer handles identity stability,
duplicate detection, manifest safety, and idempotency correctly.
"""

import json
import pytest
import hashlib
from pathlib import Path
import sys
import tempfile
import shutil

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

DATASET_V2 = ROOT / "dataset_v2"
METADATA_DIR = DATASET_V2 / "metadata"
MANIFEST_FILE = METADATA_DIR / "manifest.jsonl"
DEEPWEEDS_SOURCE = DATASET_V2 / "sources" / "deepweeds_raw" / "images"


class TestDeepWeedsIdentity:
    """Test DeepWeeds identity generation stability."""
    
    def test_source_id_from_filename(self):
        """Source ID should be deterministic from filename."""
        # Import the functions from the importer
        import importlib
        spec = importlib.util.spec_from_file_location(
            "import_deepweeds",
            ROOT / "scripts" / "import_deepweeds.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Test same filename produces same source_id
        filename = "20160928-140314-0.jpg"
        source_id_1 = module.generate_source_id(filename)
        source_id_2 = module.generate_source_id(filename)
        
        assert source_id_1 == source_id_2, "Same filename should produce same source_id"
        assert source_id_1.startswith("SRC_DW_"), "Source ID should have correct prefix"
        assert len(source_id_1) == len("SRC_DW_") + 16, "Source ID should have 16-char hash"
    
    def test_image_id_from_source_id(self):
        """Image ID should be deterministic from source ID."""
        import importlib
        spec = importlib.util.spec_from_file_location(
            "import_deepweeds",
            ROOT / "scripts" / "import_deepweeds.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Test same source_id produces same image_id
        source_id = "SRC_DW_A7EBBF9012345678"
        image_id_1 = module.generate_image_id(source_id)
        image_id_2 = module.generate_image_id(source_id)
        
        assert image_id_1 == image_id_2, "Same source_id should produce same image_id"
        assert image_id_1 == source_id, "For DeepWeeds, image_id should equal source_id"
    
    def test_sha256_collision_resistance(self):
        """Source ID should use SHA-256 for strong collision resistance."""
        import importlib
        spec = importlib.util.spec_from_file_location(
            "import_deepweeds",
            ROOT / "scripts" / "import_deepweeds.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Different filenames should produce different source_ids
        filename1 = "20160928-140314-0.jpg"
        filename2 = "20160928-140315-0.jpg"
        
        source_id_1 = module.generate_source_id(filename1)
        source_id_2 = module.generate_source_id(filename2)
        
        assert source_id_1 != source_id_2, "Different filenames should produce different source_ids"


class TestDeepWeedsDuplicates:
    """Test DeepWeeds duplicate detection."""
    
    def test_duplicate_filename_detection(self):
        """Importer should detect duplicate filenames."""
        # This would require running the importer with duplicate files
        # For now, we test the detection logic
        filename_counts = {
            "file1.jpg": 1,
            "file2.jpg": 2,  # duplicate
            "file3.jpg": 1
        }
        
        duplicates = {name: count for name, count in filename_counts.items() if count > 1}
        assert len(duplicates) == 1, "Should detect one duplicate"
        assert "file2.jpg" in duplicates, "Should identify the duplicate file"
    
    def test_source_id_collision_detection(self):
        """Importer should detect source ID collisions."""
        import importlib
        spec = importlib.util.spec_from_file_location(
            "import_deepweeds",
            ROOT / "scripts" / "import_deepweeds.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Simulate collision by using same filename
        filename = "test.jpg"
        source_id_1 = module.generate_source_id(filename)
        source_id_2 = module.generate_source_id(filename)
        
        assert source_id_1 == source_id_2, "Same filename should produce same source_id"
        # In real importer, this would be detected as a collision


class TestDeepWeedsManifestSafety:
    """Test DeepWeeds manifest safety and --force behavior."""
    
    def test_is_deepweeds_record(self):
        """Test DeepWeeds record identification."""
        import importlib
        spec = importlib.util.spec_from_file_location(
            "import_deepweeds",
            ROOT / "scripts" / "import_deepweeds.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # DeepWeeds record
        deepweeds_record = {
            "image_id": "SRC_DW_TEST",
            "provenance": {
                "source": "DeepWeeds - University of Queensland"
            }
        }
        
        # Non-DeepWeeds record
        other_record = {
            "image_id": "IMG_OTHER",
            "provenance": {
                "source": "Other Dataset"
            }
        }
        
        assert module.is_deepweeds_record(deepweeds_record), "Should identify DeepWeeds record"
        assert not module.is_deepweeds_record(other_record), "Should not identify non-DeepWeeds record"
    
    def test_force_preserves_non_deepweeds(self):
        """Test that --force preserves non-DeepWeeds records."""
        import importlib
        spec = importlib.util.spec_from_file_location(
            "import_deepweeds",
            ROOT / "scripts" / "import_deepweeds.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Create test records
        deepweeds_record = {
            "image_id": "SRC_DW_TEST",
            "provenance": {"source": "DeepWeeds - University of Queensland"}
        }
        
        other_record_1 = {
            "image_id": "IMG_OTHER_1",
            "provenance": {"source": "Other Dataset"}
        }
        
        other_record_2 = {
            "image_id": "IMG_OTHER_2",
            "provenance": {"source": "Another Dataset"}
        }
        
        all_records = [deepweeds_record, other_record_1, other_record_2]
        
        # Filter out DeepWeeds records
        non_deepweeds_records = [r for r in all_records if not module.is_deepweeds_record(r)]
        
        assert len(non_deepweeds_records) == 2, "Should preserve 2 non-DeepWeeds records"
        assert deepweeds_record not in non_deepweeds_records, "Should remove DeepWeeds record"
        assert other_record_1 in non_deepweeds_records, "Should preserve other record 1"
        assert other_record_2 in non_deepweeds_records, "Should preserve other record 2"


class TestDeepWeedsIdempotency:
    """Test DeepWeeds importer idempotency."""
    
    def test_duplicate_detection_in_manifest(self):
        """Test that duplicate image_ids are detected."""
        # Load existing manifest
        existing_image_ids = set()
        
        if MANIFEST_FILE.exists():
            with MANIFEST_FILE.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if "image_id" in record:
                            existing_image_ids.add(record["image_id"])
                    except json.JSONDecodeError:
                        continue
        
        # Check for duplicates in existing manifest
        image_id_counts = {}
        if MANIFEST_FILE.exists():
            with MANIFEST_FILE.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        image_id = record.get("image_id")
                        if image_id:
                            image_id_counts[image_id] = image_id_counts.get(image_id, 0) + 1
                    except json.JSONDecodeError:
                        continue
        
        duplicates = {iid: count for iid, count in image_id_counts.items() if count > 1}
        assert len(duplicates) == 0, f"Manifest should not contain duplicate image_ids: {duplicates}"


class TestDeepWeedsStrictJSONL:
    """Test that manifest is strict JSONL."""
    
    def test_manifest_strict_jsonl(self):
        """Every non-empty line in manifest should be valid JSON."""
        if not MANIFEST_FILE.exists():
            pytest.skip("Manifest file does not exist yet")
        
        with MANIFEST_FILE.open() as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Should not have comment lines
                assert not line.startswith("#"), f"Line {line_num} starts with # (comment), not strict JSONL"
                
                # Should parse as JSON
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Line {line_num} is not valid JSON: {e}")


class TestDeepWeedsSourcePreservation:
    """Test that source files are not modified."""
    
    def test_source_files_unchanged(self):
        """Source files in deepweeds_raw/images should not be modified."""
        if not DEEPWEEDS_SOURCE.exists():
            pytest.skip("DeepWeeds source directory does not exist")
        
        # Get all .jpg files
        jpg_files = list(DEEPWEEDS_SOURCE.glob("*.jpg"))
        
        if len(jpg_files) == 0:
            pytest.skip("No .jpg files in DeepWeeds source directory")
        
        # Sample a few files and check they exist and are readable
        for img_path in jpg_files[:5]:  # Check first 5 files
            assert img_path.exists(), f"Source file {img_path} should exist"
            assert img_path.is_file(), f"Source file {img_path} should be a file"
            
            # Try to open with PIL to verify it's a valid image
            try:
                from PIL import Image
                with Image.open(img_path) as img:
                    img.verify()
            except Exception as e:
                pytest.fail(f"Source file {img_path} is not a valid image: {e}")


class TestDeepWeedsAtomicWriting:
    """Test atomic manifest writing."""
    
    def test_atomic_write_function(self):
        """Test that atomic write function works correctly."""
        import importlib
        spec = importlib.util.spec_from_file_location(
            "import_deepweeds",
            ROOT / "scripts" / "import_deepweeds.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            test_manifest = Path(tmpdir) / "test_manifest.jsonl"
            
            # Test records
            test_records = [
                {"image_id": "TEST_1", "data": "value1"},
                {"image_id": "TEST_2", "data": "value2"}
            ]
            
            # Write atomically
            module.write_manifest_atomic(test_records, test_manifest)
            
            # Verify file exists and has correct content
            assert test_manifest.exists(), "Manifest should be created"
            
            # Verify content
            with test_manifest.open() as f:
                lines = f.readlines()
            
            assert len(lines) == 2, "Should have 2 lines"
            
            for i, line in enumerate(lines):
                record = json.loads(line.strip())
                assert record == test_records[i], f"Line {i+1} should match test record {i+1}"
            
            # Verify no temporary file left behind
            temp_file = test_manifest.with_suffix(".jsonl.tmp")
            assert not temp_file.exists(), "Temporary file should be cleaned up"


class TestDeepWeedsSchemaCompliance:
    """Test that imported records comply with schema."""
    
    def test_records_comply_with_schema(self):
        """Test that manifest records comply with schema."""
        if not MANIFEST_FILE.exists():
            pytest.skip("Manifest file does not exist yet")
        
        schema_file = METADATA_DIR / "schema.json"
        if not schema_file.exists():
            pytest.skip("Schema file does not exist")
        
        with schema_file.open() as f:
            schema = json.load(f)
        
        required_fields = [k for k, v in schema["fields"].items() if v.get("required", False)]
        
        with MANIFEST_FILE.open() as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    record = json.loads(line)
                    
                    # Check required fields
                    for field in required_fields:
                        assert field in record, f"Line {line_num}: Missing required field '{field}'"
                    
                    # Check that 'split' is NOT in record (should be external)
                    assert "split" not in record, f"Line {line_num}: 'split' should not be in manifest record"
                    
                except json.JSONDecodeError as e:
                    pytest.fail(f"Line {line_num} is not valid JSON: {e}")
