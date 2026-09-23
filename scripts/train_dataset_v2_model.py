"""Train a Dataset V2 forensic classifier."""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import cv2
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix
)
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import joblib

from backend import config
from backend.data.dataset_v2_loader import create_loader, DatasetV2Sample
from backend.features.feature_builder import FEATURE_NAMES
from backend.fusion.model import TrainedModel, save_model


def to_ordered_list(features: dict[str, float], names: list[str]) -> list[float]:
    """Convert feature dict to ordered list."""
    return [float(features.get(name, float("nan"))) for name in names]


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatasetV2Trainer:
    """Train forensic classifiers on Dataset V2."""
    
    def __init__(self):
        self.loader = create_loader()
        self.model_dir = config.MODEL_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_features(self, samples: List[DatasetV2Sample]) -> np.ndarray:
        """Extract forensic features from samples using simplified approach for prototype."""
        import cv2
        from PIL import Image
        import io
        
        features_list = []
        
        for sample in samples:
            try:
                # Load image
                with open(sample.image_path, "rb") as f:
                    image_bytes = f.read()
                image = Image.open(io.BytesIO(image_bytes))
                image = image.convert("RGB")
                rgb = np.array(image)
                
                # Extract basic forensic features (simplified for prototype)
                features = {
                    "copy_move_verified_matches": 0.0,  # Placeholder
                    "copy_move_inlier_ratio": 0.0,  # Placeholder
                    "copy_move_region_count": 0.0,  # Placeholder
                    "copy_move_region_area": 0.0,  # Placeholder
                    "patch_max_anomaly": 0.0,  # Placeholder
                    "patch_mean_anomaly": 0.0,  # Placeholder
                    "patch_anomaly_fraction": 0.0,  # Placeholder
                    "compression_score": 0.0,  # Placeholder
                    "resampling_score": 0.0,  # Placeholder
                    "blockiness": 0.0,  # Placeholder
                    "jpeg_quality": 85.0,  # Default
                    "image_megapixels": (sample.width * sample.height) / 1_000_000,
                    "bytes_per_pixel": len(image_bytes) / (sample.width * sample.height * 3),
                    "spatial_iou": 0.0,  # Placeholder
                    "spatial_dice": 0.0,  # Placeholder
                    "natural_processing_similarity": 0.5,  # Default
                }
                
                # Add basic image statistics as features
                # Color statistics
                features["image_megapixels"] = (sample.width * sample.height) / 1_000_000
                features["bytes_per_pixel"] = len(image_bytes) / (sample.width * sample.height * 3)
                
                # Add some basic variance as a weak anomaly signal
                gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
                features["patch_mean_anomaly"] = float(np.std(gray)) / 255.0
                features["patch_max_anomaly"] = float(np.max(gray)) / 255.0
                
                features_list.append(features)
                
            except Exception as e:
                logger.warning(f"Failed to extract features for {sample.image_id}: {e}")
                # Add NaN features for failed samples
                features_list.append({name: np.nan for name in FEATURE_NAMES})
        
        # Convert to numpy array
        feature_matrix = np.array([[f.get(name, np.nan) for name in FEATURE_NAMES] for f in features_list])
        return feature_matrix
    
    def build_estimator(self, kind: str = "logistic_regression"):
        """Build a scikit-learn estimator pipeline."""
        if kind == "random_forest":
            base = RandomForestClassifier(
                n_estimators=300,
                min_samples_leaf=3,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1
            )
        else:
            # Use stronger class weight for imbalanced dataset
            base = LogisticRegression(
                max_iter=2000,
                class_weight={0: 1, 1: 12},  # Manual weighting for 12:1 imbalance
                C=1.0,
                random_state=42,
                solver="liblinear"
            )
        
        return Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("clf", base),
        ])
    
    def train_logistic_regression(self):
        """Train logistic regression on Dataset V2."""
        logger.info("Training Logistic Regression on Dataset V2...")
        
        # Load data
        train_samples = self.loader.load_split("train")
        val_samples = self.loader.load_split("validation")
        test_samples = self.loader.load_split("test")
        
        logger.info(f"Train samples: {len(train_samples)}")
        logger.info(f"Validation samples: {len(val_samples)}")
        logger.info(f"Test samples: {len(test_samples)}")
        
        # Extract features
        logger.info("Extracting features...")
        X_train = self.extract_features(train_samples)
        X_val = self.extract_features(val_samples)
        X_test = self.extract_features(test_samples)
        
        y_train = np.array([s.label for s in train_samples])
        y_val = np.array([s.label for s in val_samples])
        y_test = np.array([s.label for s in test_samples])
        
        # Build and train model
        logger.info("Training model...")
        estimator = self.build_estimator("logistic_regression")
        
        # Calibrate using validation data
        calibrated = CalibratedClassifierCV(estimator, cv="prefit", method="sigmoid")
        estimator.fit(X_train, y_train)
        calibrated.fit(X_val, y_val)
        
        # Evaluate
        logger.info("Evaluating on test set...")
        y_pred = calibrated.predict(X_test)
        y_proba = calibrated.predict_proba(X_test)[:, 1]
        
        metrics = self.calculate_metrics(y_test, y_pred, y_proba)
        
        # Create trained model object
        model = TrainedModel(
            estimator=calibrated,
            feature_names=FEATURE_NAMES,
            model_version="dataset-v2-logistic-v1",
            dataset_version="dataset-real-v1",
            feature_version="features-v1",
            kind="logistic_regression",
            metrics=metrics
        )
        
        # Save model
        model_path = self.model_dir / "dataset_v2_model.joblib"
        save_model(model, model_path)
        logger.info(f"Model saved to {model_path}")
        
        # Save training metadata
        metadata = {
            "training_timestamp": datetime.now().isoformat(),
            "dataset_version": "dataset-real-v1",
            "model_version": "dataset-v2-logistic-v1",
            "feature_version": "features-v1",
            "train_samples": len(train_samples),
            "val_samples": len(val_samples),
            "test_samples": len(test_samples),
            "feature_names": FEATURE_NAMES,
            "metrics": metrics,
        }
        
        metadata_path = self.model_dir / "dataset_v2_training_metadata.json"
        with metadata_path.open("w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Training metadata saved to {metadata_path}")
        
        return model, metrics
    
    def train_random_forest(self):
        """Train random forest on Dataset V2."""
        logger.info("Training Random Forest on Dataset V2...")
        
        # Load data
        train_samples = self.loader.load_split("train")
        val_samples = self.loader.load_split("validation")
        test_samples = self.loader.load_split("test")
        
        logger.info(f"Train samples: {len(train_samples)}")
        logger.info(f"Validation samples: {len(val_samples)}")
        logger.info(f"Test samples: {len(test_samples)}")
        
        # Extract features
        logger.info("Extracting features...")
        X_train = self.extract_features(train_samples)
        X_val = self.extract_features(val_samples)
        X_test = self.extract_features(test_samples)
        
        y_train = np.array([s.label for s in train_samples])
        y_val = np.array([s.label for s in val_samples])
        y_test = np.array([s.label for s in test_samples])
        
        # Build and train model
        logger.info("Training model...")
        estimator = self.build_estimator("random_forest")
        
        # Calibrate using validation data
        calibrated = CalibratedClassifierCV(estimator, cv="prefit", method="sigmoid")
        estimator.fit(X_train, y_train)
        calibrated.fit(X_val, y_val)
        
        # Evaluate
        logger.info("Evaluating on test set...")
        y_pred = calibrated.predict(X_test)
        y_proba = calibrated.predict_proba(X_test)[:, 1]
        
        metrics = self.calculate_metrics(y_test, y_pred, y_proba)
        
        # Create trained model object
        model = TrainedModel(
            estimator=calibrated,
            feature_names=FEATURE_NAMES,
            model_version="dataset-v2-randomforest-v1",
            dataset_version="dataset-real-v1",
            feature_version="features-v1",
            kind="random_forest",
            metrics=metrics
        )
        
        # Save model
        model_path = self.model_dir / "dataset_v2_randomforest_model.joblib"
        save_model(model, model_path)
        logger.info(f"Model saved to {model_path}")
        
        # Save training metadata
        metadata = {
            "training_timestamp": datetime.now().isoformat(),
            "dataset_version": "dataset-real-v1",
            "model_version": "dataset-v2-randomforest-v1",
            "feature_version": "features-v1",
            "train_samples": len(train_samples),
            "val_samples": len(val_samples),
            "test_samples": len(test_samples),
            "feature_names": FEATURE_NAMES,
            "metrics": metrics,
        }
        
        metadata_path = self.model_dir / "dataset_v2_randomforest_metadata.json"
        with metadata_path.open("w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Training metadata saved to {metadata_path}")
        
        return model, metrics
    
    def calculate_metrics(self, y_true, y_pred, y_proba) -> Dict[str, Any]:
        """Calculate comprehensive evaluation metrics."""
        metrics = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_true, y_proba) if len(set(y_true)) > 1 else 0.5),
            "pr_auc": float(average_precision_score(y_true, y_proba) if len(set(y_true)) > 1 else 0.5),
            "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
        }
        
        # Calculate FPR and FNR
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        metrics["fpr"] = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
        metrics["fnr"] = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
        metrics["specificity"] = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
        
        return metrics


def main():
    """Main training entry point."""
    trainer = DatasetV2Trainer()
    
    # Train logistic regression (primary model)
    logger.info("=" * 80)
    logger.info("PHASE 3: Dataset V2 Classifier Training")
    logger.info("=" * 80)
    
    model, metrics = trainer.train_logistic_regression()
    
    logger.info("\n" + "=" * 80)
    logger.info("Training Complete - Metrics:")
    logger.info("=" * 80)
    logger.info(f"Accuracy: {metrics['accuracy']:.4f}")
    logger.info(f"Precision: {metrics['precision']:.4f}")
    logger.info(f"Recall: {metrics['recall']:.4f}")
    logger.info(f"F1: {metrics['f1']:.4f}")
    logger.info(f"ROC-AUC: {metrics['roc_auc']:.4f}")
    logger.info(f"PR-AUC: {metrics['pr_auc']:.4f}")
    logger.info(f"FPR: {metrics['fpr']:.4f}")
    logger.info(f"FNR: {metrics['fnr']:.4f}")
    logger.info(f"Specificity: {metrics['specificity']:.4f}")
    logger.info("=" * 80)
    
    # Optionally train random forest if time permits
    # model_rf, metrics_rf = trainer.train_random_forest()


if __name__ == "__main__":
    main()
