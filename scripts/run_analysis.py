"""Run the analysis pipeline on local files (debug helper, no server needed)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.pipeline.analysis import analyze_image  # noqa: E402
from backend.pipeline.validator import validate_upload  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--full", action="store_true", help="print the whole record as JSON")
    args = parser.parse_args()

    for path in args.paths:
        data = path.read_bytes()
        validated = validate_upload(data, path.name, None)
        record = analyze_image(data, validated, persist=False)
        if args.full:
            print(json.dumps(record, indent=2))
            continue
        print(
            f"{path.name:52s} evidence={record['manipulation_evidence']:5.1f} "
            f"coverage={record['data_coverage']:5.1f} band={record['risk_band']:35s} "
            f"cm={record['detectors']['copy_move']['status']:22s} "
            f"la={record['detectors']['local_anomaly']['status']:22s} "
            f"dice={record['spatial_agreement']['max_dice']:.2f}"
        )


if __name__ == "__main__":
    main()
