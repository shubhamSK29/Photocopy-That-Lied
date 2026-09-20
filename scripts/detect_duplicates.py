"""Detect duplicates and near-duplicates in Dataset V2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

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


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def compute_perceptual_hash(img: Image.Image, hash_size: int = 8) -> str:
    """Compute a simple perceptual hash using average hashing."""
    # Resize to hash_size x hash_size grayscale
    img = img.resize((hash_size, hash_size), Image.Resampling.LANCZOS).convert("L")
    
    # Compute average pixel value
    pixels = np.array(img)
    avg = pixels.mean()
    
    # Create hash based on whether each pixel is above/below average
    hash_bits = (pixels > avg).flatten()
    hash_str = "".join(["1" if bit else "0" for bit in hash_bits])
    
    return hash_str


def hamming_distance(hash1: str, hash2: str) -> int:
    """Compute Hamming distance between two hash strings."""
    return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))


def detect_duplicates(rows: List[Dict]) -> Dict:
    """Detect exact and near-duplicate images."""
    results = {
        "exact_duplicates": [],
        "near_duplicates": [],
        "sha256_map": {},
        "perceptual_hash_map": {},
        "summary": {}
    }
    
    sha256_map: Dict[str, List[str]] = {}
    perceptual_map: Dict[str, List[str]] = {}
    
    for row in rows:
        image_path = DATASET_V2 / row.get("image_path", "")
        if not image_path.exists():
            continue
        
        image_id = row["image_id"]
        
        # Compute SHA-256
        sha256 = compute_sha256(image_path)
        if sha256 not in sha256_map:
            sha256_map[sha256] = []
        sha256_map[sha256].append(image_id)
        results["sha256_map"][image_id] = sha256
        
        # Compute perceptual hash
        try:
            img = Image.open(image_path)
            p_hash = compute_perceptual_hash(img)
            if p_hash not in perceptual_map:
                perceptual_map[p_hash] = []
            perceptual_map[p_hash].append(image_id)
            results["perceptual_hash_map"][image_id] = p_hash
        except Exception as e:
            print(f"Warning: Could not compute perceptual hash for {image_id}: {e}")
    
    # Find exact duplicates (same SHA-256)
    for sha256, ids in sha256_map.items():
        if len(ids) > 1:
            results["exact_duplicates"].append({
                "sha256": sha256,
                "image_ids": ids,
                "count": len(ids)
            })
    
    # Find near-duplicates (similar perceptual hash)
    threshold = 5  # Hamming distance threshold
    checked_pairs: Set[Tuple[str, str]] = set()
    
    for hash1, ids1 in perceptual_map.items():
        for hash2, ids2 in perceptual_map.items():
            if hash1 >= hash2:  # Avoid checking same pair twice
                continue
            
            distance = hamming_distance(hash1, hash2)
            if distance <= threshold:
                for id1 in ids1:
                    for id2 in ids2:
                        if id1 != id2:
                            pair = tuple(sorted([id1, id2]))
                            if pair not in checked_pairs:
                                results["near_duplicates"].append({
                                    "image_id_1": id1,
                                    "image_id_2": id2,
                                    "hamming_distance": distance,
                                    "threshold": threshold
                                })
                                checked_pairs.add(pair)
    
    # Summary
    results["summary"] = {
        "total_images": len(rows),
        "exact_duplicate_groups": len(results["exact_duplicates"]),
        "total_exact_duplicates": sum(d["count"] for d in results["exact_duplicates"]),
        "near_duplicate_pairs": len(results["near_duplicates"]),
        "duplicate_threshold": threshold
    }
    
    return results


def print_report(results: Dict):
    """Print duplicate detection report."""
    print("=" * 80)
    print("DUPLICATE DETECTION REPORT")
    print("=" * 80)
    
    summary = results["summary"]
    print(f"\nTotal images: {summary['total_images']}")
    print(f"Exact duplicate groups: {summary['exact_duplicate_groups']}")
    print(f"Total exact duplicates: {summary['total_exact_duplicates']}")
    print(f"Near-duplicate pairs: {summary['near_duplicate_pairs']}")
    print(f"Near-duplicate threshold: {summary['duplicate_threshold']} Hamming distance")
    
    if results["exact_duplicates"]:
        print(f"\nExact Duplicates:")
        for dup in results["exact_duplicates"][:5]:
            print(f"  SHA256: {dup['sha256'][:16]}...")
            print(f"    Images: {dup['image_ids']}")
    
    if results["near_duplicates"]:
        print(f"\nNear-Duplicates (showing first 5):")
        for dup in results["near_duplicates"][:5]:
            print(f"  {dup['image_id_1']} <-> {dup['image_id_2']}")
            print(f"    Distance: {dup['hamming_distance']}/{dup['threshold']}")
    
    print("\n" + "=" * 80)


def main():
    """Main function."""
    print("Detecting duplicates in Dataset V2...")
    
    rows = load_manifest()
    print(f"Loaded {len(rows)} images from manifest")
    
    results = detect_duplicates(rows)
    
    print_report(results)
    
    # Save report
    report_file = ROOT / "reports" / "PHASE_2_DUPLICATE_AUDIT.json"
    report_file.parent.mkdir(exist_ok=True)
    with report_file.open("w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nReport saved to: {report_file}")
    
    return 0


if __name__ == "__main__":
    exit(main())
