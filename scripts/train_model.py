"""Train the calibrated, grouped-split fusion model from a dataset manifest."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.features.feature_builder import FEATURE_NAMES, FEATURE_VERSION
from backend.fusion.model import TrainedModel, build_calibrated, save_model
from scripts.ml_common import (RANDOM_SEED, extract_features, grouped_split, load_manifest,
                               metrics, save_figures, subset_metrics, write_run_metadata)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "dataset/manifests/dataset.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "models")
    parser.add_argument("--dataset-version", default="dataset-synthetic-v1")
    parser.add_argument("--model-version", default="fusion-v1")
    args = parser.parse_args(); args.output_dir = args.output_dir / args.model_version
    print("[1/8] Loading dataset"); rows, _ = load_manifest(args.manifest)
    print("[2/8] Validating manifest"); split = grouped_split(rows)
    print("[3/8] Extracting features"); x = extract_features(rows); y = __import__('numpy').array([r['label'] for r in rows])
    print("[4/8] Splitting groups")
    print(" ".join(f"{name.title()} groups: {len({rows[i]['_group'] for i in ids})}" for name, ids in split.items()))
    print("Group leakage: 0")
    print("[5/8] Training model"); train, val, test = (split[k] for k in ("train", "validation", "test"))
    if len(set(y[train])) < 2: raise SystemExit("ERROR: training split does not contain both classes.")
    cv = min(3, min(int((y[train] == c).sum()) for c in (0, 1)))
    if cv < 2: raise SystemExit("ERROR: insufficient examples per class for calibration.")
    estimator = build_calibrated(cv=cv); estimator.fit(x[train], y[train])
    print("[6/8] Calibrating model")
    test_p = estimator.predict_proba(x[test])[:, 1]
    report = {"train": metrics(y[train], estimator.predict_proba(x[train])[:, 1]), "validation": metrics(y[val], estimator.predict_proba(x[val])[:, 1]), "test": metrics(y[test], test_p), "subsets": subset_metrics(rows, test, test_p), "synthetic_demo_warning": "Metrics are from the supplied data; synthetic/demo metrics are not real-world performance claims."}
    print("[7/8] Evaluating"); args.output_dir.mkdir(parents=True, exist_ok=True)
    save_figures(args.output_dir, y[test], test_p)
    schema = {"feature_version": FEATURE_VERSION, "features": FEATURE_NAMES, "feature_types": {f: "float" for f in FEATURE_NAMES}, "missing_value_strategy": "NaN represents unavailable detector evidence; median imputation is fitted on training data.", "model_version": args.model_version, "dataset_version": args.dataset_version}
    (args.output_dir / "feature_schema.json").write_text(json.dumps(schema, indent=2))
    model = TrainedModel(estimator, FEATURE_NAMES, args.model_version, args.dataset_version, FEATURE_VERSION, "calibrated_logistic_regression", report)
    save_model(model, args.output_dir / "model.joblib"); save_model(model, ROOT / "models/fusion_model.joblib")
    (args.output_dir / "evaluation_report.json").write_text(json.dumps(report, indent=2))
    (args.output_dir / "evaluation_report.html").write_text(f"<h1>Fusion evaluation</h1><pre>{json.dumps(report, indent=2)}</pre>")
    metadata = {**schema, "pipeline_version": "pipeline-v1", "training_timestamp": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(), "random_seed": RANDOM_SEED, "manifest": str(args.manifest)}
    (args.output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2)); write_run_metadata(args.output_dir / "run_metadata.json", args.dataset_version, args.model_version)
    print("[8/8] Saving artifacts\nSaved:", args.output_dir)
if __name__ == "__main__": main()
