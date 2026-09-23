"""Create demo dataset for UI testing."""

import shutil
from pathlib import Path

# Demo images based on QC samples
demo_images = {
    "original.jpg": "dataset_v2/sources/deepweeds_raw/images/20171109-193756-1.jpg",
    "natural_processing.jpg": "dataset_v2/variants/natural_processing/SRC_DW_D4C6276E8DC7CA74_NP_GAMMA_72f2695e95d7f3f5.jpg",
    "hard_negative.jpg": "dataset_v2/variants/hard_negative/SRC_DW_03E50FF738AA1B03_HN_JPEG_RECOMPRESSION_1d41219b05c78836.jpg",
    "copy_move.jpg": "dataset_v2/variants/manipulated/SRC_DW_AFB187CC4AA4C45C_M_COPY_MOVE_ab439a585d7f3df1.jpg",
    "object_removal.jpg": "dataset_v2/variants/manipulated/SRC_DW_6C1F002ABF308E01_M_OBJECT_REMOVAL_d2a6018ec3c5c27c.jpg",
    "object_insertion.jpg": "dataset_v2/variants/manipulated/SRC_DW_D35996DEA6907BC8_M_OBJECT_INSERTION_03cea4b426335115.jpg",
    "splicing.jpg": "dataset_v2/variants/manipulated/SRC_DW_8287B54F129B68F1_M_SPLICING_2a0effabd2c0e652.jpg",
}

demo_dir = Path("demo")
demo_dir.mkdir(exist_ok=True)

for dest_name, src_path in demo_images.items():
    src = Path(src_path)
    dest = demo_dir / dest_name
    
    if src.exists():
        shutil.copy(src, dest)
        print(f"Copied {dest_name}")
    else:
        print(f"WARNING: {src} not found")

print(f"\nDemo dataset created in {demo_dir}")
print(f"Total images: {len(demo_images)}")
