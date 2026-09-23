"""Test Dataset V2 loader."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.data.dataset_v2_loader import create_loader, DatasetV2Sample


def test_loader():
    """Test the Dataset V2 loader."""
    print("Testing Dataset V2 Loader...")
    
    # Create loader
    loader = create_loader()
    
    # Get statistics
    stats = loader.get_statistics()
    print(f"\nDataset Statistics:")
    print(f"  Total: {stats['total']}")
    print(f"  Train: {stats['by_split']['train']}")
    print(f"  Validation: {stats['by_split']['validation']}")
    print(f"  Test: {stats['by_split']['test']}")
    print(f"  By category: {stats['by_category']}")
    print(f"  By manipulation type: {stats['by_manipulation_type']}")
    
    # Test loading from each split
    print("\nTesting split loading...")
    
    train_samples = loader.load_split("train")
    print(f"  Train samples: {len(train_samples)}")
    
    val_samples = loader.load_split("validation")
    print(f"  Validation samples: {len(val_samples)}")
    
    test_samples = loader.load_split("test")
    print(f"  Test samples: {len(test_samples)}")
    
    # Test image loading
    print("\nTesting image loading...")
    if train_samples:
        sample = train_samples[0]
        print(f"  Sample: {sample.image_id}")
        print(f"  Image path: {sample.image_path}")
        print(f"  Image exists: {sample.image_path.exists()}")
        
        try:
            image = loader.load_image(sample)
            print(f"  Image shape: {image.shape}")
            print(f"  Image dtype: {image.dtype}")
        except Exception as e:
            print(f"  ERROR loading image: {e}")
    
    # Test mask loading
    print("\nTesting mask loading...")
    # Find a manipulated sample
    manipulated_samples = [s for s in train_samples if s.category == "manipulated"]
    if manipulated_samples:
        sample = manipulated_samples[0]
        print(f"  Sample: {sample.image_id}")
        print(f"  Mask path: {sample.mask_path}")
        print(f"  Mask exists: {sample.mask_path.exists()}")
        
        try:
            mask = loader.load_mask(sample)
            print(f"  Mask shape: {mask.shape}")
            print(f"  Mask dtype: {mask.dtype}")
            print(f"  Mask non-zero pixels: {mask.sum()}")
        except Exception as e:
            print(f"  ERROR loading mask: {e}")
    
    # Test split isolation
    print("\nTesting split isolation...")
    try:
        # Try to load a train sample from validation split (should fail)
        train_source = train_samples[0].source_id
        val_records = loader._by_split["validation"]
        for record in val_records:
            if record["source_id"] == train_source:
                print(f"  ERROR: Split isolation violation detected!")
                break
        else:
            print(f"  Split isolation: PASS")
    except Exception as e:
        print(f"  ERROR testing split isolation: {e}")
    
    print("\nLoader test complete.")


if __name__ == "__main__":
    test_loader()
