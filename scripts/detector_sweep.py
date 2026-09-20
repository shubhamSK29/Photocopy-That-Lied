"""Quick detector behaviour sweep over the synthetic demo dataset.

Reports, per dataset category, how often each detector fires. Synthetic data only:
this is a development aid, not a validation result.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from collections import defaultdict

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.forensic import copy_move, local_anomaly  # noqa: E402

CATEGORIES = [
    "authentic",
    "natural_variants",
    "hard_cases",
    "copy_move",
    "splicing",
    "manipulated_recompressed",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=24)
    args = parser.parse_args()

    stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for category in CATEGORIES:
        for path in sorted(glob.glob(f"dataset/{category}/*"))[: args.limit]:
            bgr = cv2.imread(path)
            if bgr is None:
                continue
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            stats[category]["n"] += 1
            stats[category][f"cm_{copy_move.detect(gray).status}"] += 1
            stats[category][f"la_{local_anomaly.detect(bgr).status}"] += 1

    for category in CATEGORIES:
        row = stats[category]
        n = row.get("n", 0)
        if not n:
            continue
        print(f"{category:26s} n={n:3d} "
              f"cm_detected={row.get('cm_detected', 0):3d} "
              f"la_detected={row.get('la_detected', 0):3d} "
              f"la_insufficient={row.get('la_insufficient_evidence', 0):3d}")


if __name__ == "__main__":
    main()
