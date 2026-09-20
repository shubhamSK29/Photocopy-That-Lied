"""Shared, reproducible training and evaluation helpers for the fusion model."""
from __future__ import annotations

import csv
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
from sklearn.metrics import (accuracy_score, brier_score_loss, confusion_matrix,
                             f1_score, precision_score, recall_score, roc_auc_score,
                             roc_curve)
from sklearn.model_selection import GroupShuffleSplit

from backend import config
from backend.features.feature_builder import FEATURE_NAMES
from backend.pipeline.analysis import analyze_image
from backend.pipeline.validator import validate_upload

RANDOM_SEED = 42


class ManifestError(ValueError):
    pass


def load_manifest(path: Path) -> tuple[list[dict], Path]:
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ManifestError("Manifest contains no rows.")
    required = {"label", "source_id"}
    missing = required - set(rows[0])
    if missing:
        raise ManifestError(f"Manifest missing required columns: {', '.join(sorted(missing))}")
    image_column = "image_path" if "image_path" in rows[0] else "path"
    if image_column not in rows[0]:
        raise ManifestError("Manifest requires image_path (or legacy path).")
    for row in rows:
        if str(row.get("label")) not in {"0", "1", "genuine", "manipulated"}:
            raise ManifestError(f"Invalid label for {row.get(image_column)}: {row.get('label')}")
        row["label"] = 1 if str(row["label"]) in {"1", "manipulated"} else 0
        row["_image"] = (path.parent.parent / row[image_column]).resolve()
        row["_group"] = row.get("parent_id") or row.get("source_id") or row.get("session_id")
        if not row["_group"]:
            raise ManifestError("Every row requires parent_id, source_id, or session_id for grouped splitting.")
        if not row["_image"].exists():
            raise ManifestError(f"Manifest image not found: {row['_image']}")
    return rows, path


def grouped_split(rows: list[dict], seed: int = RANDOM_SEED) -> dict[str, list[int]]:
    labels = np.array([r["label"] for r in rows])
    groups = np.array([r["_group"] for r in rows])
    if len(set(groups)) < 3:
        raise ManifestError("At least three source/parent groups are required for train/validation/test splitting.")
    
    # Try to use stratified group splitting for better class balance
    try:
        from sklearn.model_selection import StratifiedGroupShuffleSplit
        splitter = StratifiedGroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
        train_val, test = next(splitter.split(np.zeros(len(rows)), labels, groups))
        inner = StratifiedGroupShuffleSplit(n_splits=1, test_size=0.125, random_state=seed + 1)
        train_rel, val_rel = next(inner.split(np.zeros(len(train_val)), labels[train_val], groups[train_val]))
    except (ImportError, TypeError):
        # Fall back to regular GroupShuffleSplit if stratified version not available
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
        train_val, test = next(splitter.split(np.zeros(len(rows)), labels, groups))
        inner = GroupShuffleSplit(n_splits=1, test_size=0.125, random_state=seed + 1)
        train_rel, val_rel = next(inner.split(np.zeros(len(train_val)), labels[train_val], groups[train_val]))
    
    split = {"train": train_val[train_rel].tolist(), "validation": train_val[val_rel].tolist(), "test": test.tolist()}
    memberships = {name: {groups[i] for i in ids} for name, ids in split.items()}
    overlap = (memberships["train"] & memberships["validation"]) | (memberships["train"] & memberships["test"]) | (memberships["validation"] & memberships["test"])
    if overlap:
        raise ManifestError(f"Parent-group leakage detected: {sorted(overlap)[:5]}")
    
    # Check class distribution in each split
    for split_name, ids in split.items():
        split_labels = labels[ids]
        unique_classes = len(np.unique(split_labels))
        if unique_classes < 2:
            print(f"WARNING: {split_name} split contains only {unique_classes} class(es). Some metrics may be unavailable.")
    
    return split


def extract_features(rows: Iterable[dict]) -> np.ndarray:
    vectors = []
    for index, row in enumerate(rows, 1):
        data = row["_image"].read_bytes()
        validated = validate_upload(data, row["_image"].name, None)
        record = analyze_image(data, validated, persist=False)
        vectors.append([record["features"].get(name, np.nan) for name in FEATURE_NAMES])
        print(f"  extracted {index}: {row['_image'].name}")
    return np.asarray(vectors, dtype=float)


def metrics(y_true: np.ndarray, probability: np.ndarray, threshold: float = 0.6) -> dict:
    predicted = (probability >= 0.5).astype(int)
    cm = confusion_matrix(y_true, predicted, labels=[0, 1])
    negatives = int(cm[0].sum())
    high = probability >= threshold
    result = {
        "count": int(len(y_true)), "accuracy": float(accuracy_score(y_true, predicted)),
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "false_positive_rate": float(cm[0, 1] / negatives) if negatives else None,
        "confusion_matrix": cm.tolist(),
        "high_priority_review_precision": float(precision_score(y_true[high], np.ones(high.sum()), zero_division=0)) if high.any() else None,
        "brier_score": float(brier_score_loss(y_true, probability)),
    }
    result["roc_auc"] = float(roc_auc_score(y_true, probability)) if len(np.unique(y_true)) == 2 else None
    
    # Add calibration metrics if sample size is sufficient and both classes present
    if len(y_true) >= 30 and len(np.unique(y_true)) == 2:
        result["calibration"] = calibration_metrics(y_true, probability)
    
    return result


def calibration_metrics(y_true: np.ndarray, probability: np.ndarray, n_bins: int = 10) -> dict:
    """Compute calibration metrics including Expected Calibration Error (ECE)."""
    if len(y_true) < n_bins:
        return {"note": f"Insufficient samples ({len(y_true)}) for reliable calibration analysis."}
    
    try:
        from sklearn.calibration import calibration_curve
        prob_true, prob_pred = calibration_curve(y_true, probability, n_bins=n_bins, strategy='uniform')
        
        # Compute Expected Calibration Error (ECE)
        bin_edges = np.linspace(0, 1, n_bins + 1)
        bin_width = 1.0 / n_bins
        ece = 0.0
        bin_counts = []
        
        for i in range(n_bins):
            mask = (probability > bin_edges[i]) & (probability <= bin_edges[i + 1])
            if i == n_bins - 1:  # Include the right edge for the last bin
                mask = (probability >= bin_edges[i]) & (probability <= bin_edges[i + 1])
            
            bin_count = mask.sum()
            bin_counts.append(int(bin_count))
            
            if bin_count > 0:
                ece += bin_count * abs(prob_true[i] - prob_pred[i])
        
        ece = ece / len(y_true)
        
        return {
            "expected_calibration_error": float(ece),
            "n_bins": n_bins,
            "bin_counts": bin_counts,
            "prob_true": prob_true.tolist(),
            "prob_pred": prob_pred.tolist(),
            "note": "Calibration analysis requires sufficient sample size for reliable estimates."
        }
    except Exception as e:
        return {"note": f"Calibration analysis failed: {str(e)}"}


def subset_metrics(rows: list[dict], ids: list[int], probabilities: np.ndarray) -> dict:
    result = {}
    for name, predicate in {
        "genuine_low_end_phone": lambda r: r["label"] == 0 and r.get("device_tier") == "low",
        "hard_negatives": lambda r: r["label"] == 0 and r.get("category") == "hard_cases",
        "natural_processing": lambda r: r["label"] == 0 and r.get("category") == "natural_variants",
    }.items():
        selected = [pos for pos, original in enumerate(ids) if predicate(rows[original])]
        if selected:
            y = np.array([rows[ids[pos]]["label"] for pos in selected])
            p = probabilities[selected]
            
            # Only compute full metrics if sample size is sufficient
            if len(selected) >= 10:
                # Single-class subsets deliberately omit ROC-AUC and recall is still honest.
                subset_result = {**metrics(y, p), "average_evidence_score": float(np.mean(p) * 100)}
                subset_result["note"] = f"Subset contains {len(selected)} examples."
                result[name] = subset_result
            else:
                # For small subsets, provide basic statistics only
                subset_result = {
                    "count": len(selected),
                    "average_evidence_score": float(np.mean(p) * 100),
                    "note": f"Insufficient sample size ({len(selected)} < 10) for reliable metrics. Only basic statistics provided."
                }
                result[name] = subset_result
        else:
            result[name] = {
                "count": 0,
                "note": "No matching evaluation examples in this subset."
            }
    return result


def write_run_metadata(path: Path, dataset_version: str, model_version: str) -> None:
    import sklearn
    path.write_text(json.dumps({
        "dataset_version": dataset_version, "model_version": model_version,
        "feature_version": config.FEATURE_VERSION, "pipeline_version": config.PIPELINE_VERSION,
        "random_seed": RANDOM_SEED, "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version, "platform": platform.platform(),
        "dependencies": {"numpy": np.__version__, "scikit_learn": sklearn.__version__},
        "warning": "Evaluation is synthetic/demo data unless the supplied manifest states otherwise.",
    }, indent=2), encoding="utf-8")


def save_figures(output: Path, y: np.ndarray, p: np.ndarray) -> None:
    """Save simple, dependency-light evaluation figures using Pillow."""
    from PIL import Image, ImageDraw
    output.mkdir(parents=True, exist_ok=True)
    cm = confusion_matrix(y, (p >= .5).astype(int), labels=[0, 1])
    im = Image.new("RGB", (500, 380), "white"); draw = ImageDraw.Draw(im)
    draw.text((20, 15), "Confusion matrix (rows: actual, columns: predicted)", fill="black")
    for r in range(2):
        for c in range(2):
            x, yy = 110 + c * 140, 100 + r * 100
            draw.rectangle((x, yy, x + 100, yy + 70), outline="black")
            draw.text((x + 35, yy + 25), str(int(cm[r, c])), fill="black")
    im.save(output / "confusion_matrix.png")
    if len(np.unique(y)) == 2:
        fpr, tpr, _ = roc_curve(y, p)
        im = Image.new("RGB", (500, 400), "white"); draw = ImageDraw.Draw(im)
        draw.line((60, 340, 440, 40), fill="gray", width=1)
        points = [(60 + int(x * 380), 340 - int(z * 300)) for x, z in zip(fpr, tpr)]
        if len(points) > 1: draw.line(points, fill="blue", width=3)
        draw.rectangle((60, 40, 440, 340), outline="black"); draw.text((190, 12), "ROC curve", fill="black")
        im.save(output / "roc_curve.png")
