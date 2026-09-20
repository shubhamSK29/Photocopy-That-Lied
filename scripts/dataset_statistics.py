"""Generate dataset statistics for Dataset V2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DATASET_V2 = ROOT / "dataset_v2"
METADATA_DIR = DATASET_V2 / "metadata"
MANIFEST_FILE = METADATA_DIR / "manifest.jsonl"


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


def compute_statistics(rows: List[Dict]) -> Dict:
    """Compute comprehensive dataset statistics."""
    stats = {
        "total_images": len(rows),
        "genuine": 0,
        "manipulated": 0,
        "natural_processing": 0,
        "hard_negatives": 0,
        "manipulation_types": {},
        "unique_sources": 0,
        "images_per_source": {},
        "resolution_distribution": {},
        "format_distribution": {},
        "color_mode_distribution": {},
        "mask_coverage": 0,
        "device_distribution": {},
        "generation_method_distribution": {}
    }
    
    for row in rows:
        # Labels
        if row.get("label") == 0:
            stats["genuine"] += 1
        else:
            stats["manipulated"] += 1
        
        # Categories
        category = row.get("category", "unknown")
        if category == "natural_processing":
            stats["natural_processing"] += 1
        elif category == "hard_negative":
            stats["hard_negatives"] += 1
        
        # Manipulation types
        if row.get("label") == 1:
            manipulation_type = row.get("manipulation_type", "unknown")
            stats["manipulation_types"][manipulation_type] = stats["manipulation_types"].get(manipulation_type, 0) + 1
        
        # Sources
        source_id = row.get("source_id")
        if source_id:
            stats["images_per_source"][source_id] = stats["images_per_source"].get(source_id, 0) + 1
        
        # Image properties
        image_path = DATASET_V2 / row.get("image_path", "")
        if image_path.exists():
            try:
                img = Image.open(image_path)
                resolution = f"{img.width}x{img.height}"
                stats["resolution_distribution"][resolution] = stats["resolution_distribution"].get(resolution, 0) + 1
                stats["format_distribution"][img.format] = stats["format_distribution"].get(img.format, 0) + 1
                stats["color_mode_distribution"][img.mode] = stats["color_mode_distribution"].get(img.mode, 0) + 1
            except:
                pass
        
        # Device distribution
        device_id = row.get("device_id")
        if device_id:
            stats["device_distribution"][device_id] = stats["device_distribution"].get(device_id, 0) + 1
        
        # Generation method
        gen_method = row.get("generation_method")
        if gen_method:
            stats["generation_method_distribution"][gen_method] = stats["generation_method_distribution"].get(gen_method, 0) + 1
    
    stats["unique_sources"] = len(stats["images_per_source"])
    
    # Mask coverage
    manipulated_images = [r for r in rows if r.get("label") == 1]
    if manipulated_images:
        with_masks = sum(1 for r in manipulated_images if r.get("mask_path"))
        stats["mask_coverage"] = with_masks / len(manipulated_images)
    
    return stats


def print_report(stats: Dict):
    """Print statistics report."""
    print("=" * 80)
    print("DATASET V2 STATISTICS")
    print("=" * 80)
    
    print(f"\n[OVERALL]")
    print(f"Total images: {stats['total_images']}")
    print(f"Genuine: {stats['genuine']} ({stats['genuine']/stats['total_images']:.1%})")
    print(f"Manipulated: {stats['manipulated']} ({stats['manipulated']/stats['total_images']:.1%})")
    print(f"Natural processing: {stats['natural_processing']}")
    print(f"Hard negatives: {stats['hard_negatives']}")
    
    print(f"\n[SOURCE DIVERSITY]")
    print(f"Unique sources: {stats['unique_sources']}")
    print(f"Images per source (min/max/avg):")
    if stats['images_per_source']:
        counts = list(stats['images_per_source'].values())
        print(f"  Min: {min(counts)}")
        print(f"  Max: {max(counts)}")
        print(f"  Avg: {np.mean(counts):.1f}")
    
    print(f"\n[MANIPULATION TYPES]")
    for mtype, count in stats['manipulation_types'].items():
        print(f"  {mtype}: {count}")
    
    print(f"\n[RESOLUTION DISTRIBUTION]")
    for res, count in sorted(stats['resolution_distribution'].items()):
        print(f"  {res}: {count}")
    
    print(f"\n[FORMAT DISTRIBUTION]")
    for fmt, count in stats['format_distribution'].items():
        print(f"  {fmt}: {count}")
    
    print(f"\n[COLOR MODE DISTRIBUTION]")
    for mode, count in stats['color_mode_distribution'].items():
        print(f"  {mode}: {count}")
    
    print(f"\n[MASK COVERAGE]")
    print(f"Manipulated images with masks: {stats['mask_coverage']:.1%}")
    
    print(f"\n[DEVICE DISTRIBUTION]")
    for device, count in stats['device_distribution'].items():
        print(f"  {device}: {count}")
    
    print(f"\n[GENERATION METHOD]")
    for method, count in stats['generation_method_distribution'].items():
        print(f"  {method}: {count}")
    
    print("\n" + "=" * 80)


def main():
    """Main function."""
    print("Generating Dataset V2 statistics...")
    
    rows = load_manifest()
    print(f"Loaded {len(rows)} images from manifest")
    
    stats = compute_statistics(rows)
    
    print_report(stats)
    
    # Save report
    report_file = ROOT / "reports" / "PHASE_2_DATASET_STATISTICS.json"
    report_file.parent.mkdir(exist_ok=True)
    with report_file.open("w") as f:
        json.dump(stats, f, indent=2)
    
    print(f"\nStatistics saved to: {report_file}")
    
    return 0


if __name__ == "__main__":
    exit(main())
