"""Generate contact sheets for visual inspection of Dataset V2.

This script creates sample grids showing representative images from each category.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATASET_V2 = ROOT / "dataset_v2"
METADATA_DIR = DATASET_V2 / "metadata"
MANIFEST_FILE = METADATA_DIR / "manifest.jsonl"
OUTPUT_DIR = ROOT / "reports" / "contact_sheets"


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


def create_contact_sheet(image_paths: List[Path], title: str, 
                         grid_size: Tuple[int, int] = (4, 4),
                         thumbnail_size: Tuple[int, int] = (256, 256)) -> Image.Image:
    """Create a contact sheet from a list of images."""
    cols, rows = grid_size
    cell_width, cell_height = thumbnail_size
    
    # Create canvas
    canvas_width = cols * cell_width + (cols - 1) * 10
    canvas_height = rows * cell_height + (rows - 1) * 10 + 60  # Extra space for title
    canvas = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    # Add title
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    draw.text((10, 10), title, fill=(0, 0, 0), font=font)
    
    # Add images to grid
    for idx, img_path in enumerate(image_paths[:cols * rows]):
        if not img_path.exists():
            continue
        
        col = idx % cols
        row = idx // cols
        
        x = col * (cell_width + 10)
        y = row * (cell_height + 10) + 60
        
        try:
            img = Image.open(img_path)
            img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            
            # Center image in cell
            paste_x = x + (cell_width - img.width) // 2
            paste_y = y + (cell_height - img.height) // 2
            canvas.paste(img, (paste_x, paste_y))
            
            # Add filename below image
            filename = img_path.stem[:20]  # Truncate long names
            draw.text((x, y + cell_height + 2), filename, fill=(100, 100, 100), font=font)
            
        except Exception as e:
            # Draw placeholder for failed images
            draw.rectangle([x, y, x + cell_width, y + cell_height], fill=(240, 240, 240))
            draw.text((x + 10, y + cell_height // 2), "ERROR", fill=(255, 0, 0), font=font)
    
    return canvas


def generate_category_contact_sheets(rows: List[Dict], max_per_category: int = 16):
    """Generate contact sheets for each category."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Group images by category
    categories = {}
    for row in rows:
        category = row.get("category", "unknown")
        if category not in categories:
            categories[category] = []
        image_path = DATASET_V2 / row.get("image_path", "")
        categories[category].append((image_path, row.get("image_id")))
    
    # Generate contact sheet for each category
    for category, items in categories.items():
        if not items:
            continue
        
        image_paths = [item[0] for item in items[:max_per_category]]
        title = f"{category.upper()} ({len(items)} images)"
        
        # Calculate grid size
        grid_cols = 4
        grid_rows = (len(image_paths) + grid_cols - 1) // grid_cols
        
        contact_sheet = create_contact_sheet(
            image_paths, 
            title, 
            grid_size=(grid_cols, grid_rows)
        )
        
        output_file = OUTPUT_DIR / f"{category}_contact_sheet.png"
        contact_sheet.save(output_file)
        print(f"Saved contact sheet: {output_file}")
    
    # Generate overall summary
    all_categories = list(categories.keys())
    if all_categories:
        summary_title = f"DATASET V2 OVERVIEW ({len(rows)} total images)"
        sample_paths = []
        for category in all_categories:
            if categories[category]:
                sample_paths.append(categories[category][0][0])
        
        if sample_paths:
            summary_sheet = create_contact_sheet(
                sample_paths[:16],
                summary_title,
                grid_size=(4, 4)
            )
            summary_file = OUTPUT_DIR / "overview_contact_sheet.png"
            summary_sheet.save(summary_file)
            print(f"Saved overview contact sheet: {summary_file}")


def main():
    """Main function."""
    print("Generating contact sheets for Dataset V2 visual inspection...")
    
    rows = load_manifest()
    print(f"Loaded {len(rows)} images from manifest")
    
    if not rows:
        print("Dataset is empty - no contact sheets to generate")
        return 0
    
    generate_category_contact_sheets(rows)
    
    print(f"\nContact sheets saved to: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    exit(main())
