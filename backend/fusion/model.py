"""Fusion model definition and persistence."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend import config
from backend.features.feature_builder import FEATURE_NAMES, FEATURE_VERSION

MODEL_VERSION = "fusion-v1"


def build_estimator(kind: str = "logistic_regression"):
    if kind == "random_forest":
        base = RandomForestClassifier(
            n_estimators=300, min_samples_leaf=3, class_weight="balanced", random_state=7
        )
    else:
        base = LogisticRegression(max_iter=2000, class_weight="balanced", C=0.5)
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("clf", base),
        ]
    )


def build_calibrated(kind: str = "logistic_regression", cv: int = 3, method: str = "sigmoid"):
    return CalibratedClassifierCV(build_estimator(kind), cv=cv, method=method)


@dataclass
class TrainedModel:
    estimator: Any
    feature_names: list[str]
    model_version: str
    dataset_version: str
    feature_version: str
    kind: str
    metrics: dict

    def predict_proba(self, rows) -> Any:
        return self.estimator.predict_proba(rows)[:, 1]


def save_model(model: TrainedModel, path: Optional[Path] = None) -> Path:
    path = Path(path or config.MODEL_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "estimator": model.estimator,
            "feature_names": model.feature_names,
            "model_version": model.model_version,
            "dataset_version": model.dataset_version,
            "feature_version": model.feature_version,
            "kind": model.kind,
            "metrics": model.metrics,
        },
        path,
    )
    return path


def load_model(path: Optional[Path] = None) -> Optional[TrainedModel]:
    path = Path(path or config.MODEL_PATH)
    if not path.exists():
        return None
    try:
        payload = joblib.load(path)
        return TrainedModel(
            estimator=payload["estimator"],
            feature_names=payload.get("feature_names", FEATURE_NAMES),
            model_version=payload.get("model_version", MODEL_VERSION),
            dataset_version=payload.get("dataset_version", "unknown"),
            feature_version=payload.get("feature_version", FEATURE_VERSION),
            kind=payload.get("kind", "logistic_regression"),
            metrics=payload.get("metrics", {}),
        )
    except Exception:
        return None
