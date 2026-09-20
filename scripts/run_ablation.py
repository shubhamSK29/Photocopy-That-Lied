"""Run reproducible grouped-split fusion ablations on the supplied manifest."""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
import numpy as np
from backend.features.feature_builder import FEATURE_NAMES
from backend.fusion.model import build_calibrated
from scripts.ml_common import extract_features, grouped_split, load_manifest, metrics, write_run_metadata

EXPERIMENTS = {
 "copy_move_only": ["copy_move_"], "local_anomaly_only": ["patch_"],
 "all_forensic_signals": ["copy_move_", "patch_", "compression", "resampling", "blockiness", "jpeg_quality"],
 "without_natural_processing": ["!natural_processing_similarity"],
 "without_spatial_agreement": ["!spatial_iou", "!spatial_dice"], "full_system": [""]}
def selected(patterns):
    return [i for i, name in enumerate(FEATURE_NAMES) if any((p == "" or (p.startswith("!") and not name.startswith(p[1:])) or (not p.startswith("!") and name.startswith(p))) for p in patterns)]
def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--manifest", type=Path, default=ROOT/"dataset/manifests/dataset.csv"); parser.add_argument("--output-dir", type=Path, default=ROOT/"reports/ablations"); args=parser.parse_args()
    rows,_=load_manifest(args.manifest); split=grouped_split(rows); x=extract_features(rows); y=np.array([r['label'] for r in rows]); results=[]
    for name, patterns in EXPERIMENTS.items():
        cols=selected(patterns); train,test=split['train'],split['test']; cv=min(3,min(int((y[train]==c).sum()) for c in (0,1))); est=build_calibrated(cv=cv); est.fit(x[train][:,cols],y[train]); value=metrics(y[test],est.predict_proba(x[test][:,cols])[:,1]); results.append({"experiment":name,"features":[FEATURE_NAMES[i] for i in cols],**value})
    args.output_dir.mkdir(parents=True,exist_ok=True); (args.output_dir/"ablation_report.json").write_text(json.dumps(results,indent=2));
    with (args.output_dir/"ablation_results.csv").open("w",newline="") as fh: csv.DictWriter(fh,fieldnames=["experiment","accuracy","precision","recall","f1","false_positive_rate","roc_auc","high_priority_review_precision"]).writeheader(); csv.DictWriter(fh,fieldnames=["experiment","accuracy","precision","recall","f1","false_positive_rate","roc_auc","high_priority_review_precision"]).writerows([{k:r.get(k) for k in ["experiment","accuracy","precision","recall","f1","false_positive_rate","roc_auc","high_priority_review_precision"]} for r in results])
    write_run_metadata(args.output_dir/"run_metadata.json", rows[0].get("dataset_version","unknown"), "ablation")
    print(f"Saved {len(results)} experiments to {args.output_dir}")
if __name__=="__main__": main()
