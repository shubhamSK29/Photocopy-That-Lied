"""Evaluate a saved fusion model against a manifest using its persisted schema."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from backend.fusion.model import load_model
from scripts.ml_common import extract_features, grouped_split, load_manifest, metrics, save_figures, subset_metrics, write_run_metadata

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--manifest", type=Path, default=ROOT / "dataset/manifests/dataset.csv"); parser.add_argument("--model", type=Path, default=ROOT / "models/fusion_model.joblib"); parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/evaluations"); args = parser.parse_args()
    rows, _ = load_manifest(args.manifest); model = load_model(args.model)
    if model is None: raise SystemExit(f"ERROR: no readable model at {args.model}")
    from backend.features.feature_builder import FEATURE_NAMES
    if model.feature_names != FEATURE_NAMES: raise SystemExit("ERROR: saved feature schema does not match the current feature builder.")
    split = grouped_split(rows); x = extract_features(rows); import numpy as np; y = np.array([r['label'] for r in rows]); ids = split['test']; p = model.predict_proba(x[ids])
    report = {"model_version": model.model_version, "dataset_version": model.dataset_version, "test": metrics(y[ids], p), "subsets": subset_metrics(rows, ids, p), "limitation": "Synthetic/demo evaluation must not be interpreted as real-world performance."}
    args.output_dir.mkdir(parents=True, exist_ok=True); (args.output_dir / "evaluation_report.json").write_text(json.dumps(report, indent=2)); (args.output_dir / "evaluation_report.html").write_text(f"<h1>Evaluation</h1><pre>{json.dumps(report, indent=2)}</pre>"); save_figures(args.output_dir, y[ids], p); write_run_metadata(args.output_dir / "run_metadata.json", model.dataset_version, model.model_version)
    print(json.dumps(report['test'], indent=2))
if __name__ == "__main__": main()
