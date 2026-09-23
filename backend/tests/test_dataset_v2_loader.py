"""Test Dataset V2 loader."""

import pytest
import numpy as np
from pathlib import Path

from backend.data.dataset_v2_loader import create_loader, DatasetV2Sample


def test_loader_creation():
    """Test that loader can be created."""
    loader = create_loader()
    assert loader is not None
    assert loader.manifest_path.exists()
    assert loader.split_file.exists()


def test_loader_statistics():
    """Test that loader returns correct statistics."""
    loader = create_loader()
    stats = loader.get_statistics()
    
    assert stats["total"] == 3895
    assert stats["by_split"]["train"] > 0
    assert stats["by_split"]["validation"] > 0
    assert stats["by_split"]["test"] > 0
    assert "original" in stats["by_category"]
    assert "manipulated" in stats["by_category"]
    assert "copy_move" in stats["by_manipulation_type"]


def test_split_loading():
    """Test that splits can be loaded with isolation."""
    loader = create_loader()
    
    train = loader.load_split("train")
    validation = loader.load_split("validation")
    test = loader.load_split("test")
    
    assert len(train) > 0
    assert len(validation) > 0
    assert len(test) > 0
    
    # Verify no overlap in source_ids
    train_sources = {s.source_id for s in train}
    val_sources = {s.source_id for s in validation}
    test_sources = {s.source_id for s in test}
    
    assert len(train_sources & val_sources) == 0
    assert len(train_sources & test_sources) == 0
    assert len(val_sources & test_sources) == 0


def test_image_loading():
    """Test that images can be loaded."""
    loader = create_loader()
    train = loader.load_split("train")
    
    if train:
        sample = train[0]
        image = loader.load_image(sample)
        
        assert image.shape[2] == 3  # RGB
        assert image.dtype == np.uint8
        assert image.shape[0] == sample.height
        assert image.shape[1] == sample.width


def test_mask_loading():
    """Test that masks can be loaded for manipulated images."""
    loader = create_loader()
    train = loader.load_split("train")
    
    # Find a manipulated sample
    manipulated = [s for s in train if s.category == "manipulated"]
    
    if manipulated:
        sample = manipulated[0]
        mask = loader.load_mask(sample)
        
        assert mask is not None
        assert mask.shape[0] == sample.height
        assert mask.shape[1] == sample.width
        assert mask.dtype == np.uint8
        # Check binary
        assert mask.max() <= 1


def test_metadata_preservation():
    """Test that metadata is preserved."""
    loader = create_loader()
    train = loader.load_split("train")
    
    if train:
        sample = train[0]
        
        assert sample.image_id is not None
        assert sample.source_id is not None
        assert sample.label in [0, 1]
        assert sample.category in ["original", "natural_processing", "hard_negative", "manipulated"]
        assert sample.split in ["train", "validation", "test"]
        assert sample.width > 0
        assert sample.height > 0


def test_missing_file_handling():
    """Test that missing files are handled gracefully."""
    loader = create_loader()
    
    # Create a fake sample with non-existent path
    fake_sample = DatasetV2Sample(
        image_id="fake",
        source_id="fake",
        label=0,
        category="original",
        manipulation_type=None,
        split="train",
        image_path=Path("/nonexistent/path.jpg"),
        mask_path=None,
        mask_id=None,
        variant_id=None,
        parameters={},
        manipulation_area_ratio=None,
        width=256,
        height=256,
        format="JPEG",
        color_mode="RGB",
    )
    
    with pytest.raises(FileNotFoundError):
        loader.load_image(fake_sample)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
