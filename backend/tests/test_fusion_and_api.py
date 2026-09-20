from io import BytesIO
import tempfile
from pathlib import Path

import numpy as np
import cv2
from fastapi.testclient import TestClient
from PIL import Image

from backend.features.feature_builder import FEATURE_NAMES, build_base_features, build_context, to_ordered_list
from backend.forensic.metadata import extract_metadata
from backend.forensic.copy_move import detect as detect_copy_move
from backend.forensic.local_anomaly import detect as detect_local_anomaly
from backend.forensic.compression import detect as detect_compression
from backend.fusion.model import TrainedModel, build_calibrated, save_model
from backend.fusion.predict import predict_evidence, _fallback_probability
from backend.main import app
from backend.pipeline.validator import ValidationError, validate_upload


def jpeg_bytes(size=(80, 80), color=(30, 120, 60)) -> bytes:
    image = Image.new("RGB", size, color)
    result = BytesIO(); image.save(result, format="JPEG"); return result.getvalue()


def png_bytes(size=(80, 80), color=(30, 120, 60)) -> bytes:
    image = Image.new("RGB", size, color)
    result = BytesIO(); image.save(result, format="PNG"); return result.getvalue()


def corrupt_jpeg_bytes() -> bytes:
    return b"\xff\xd8\xff" + b"\x00" * 100 + b"\xff\xd9"


# Upload validation tests
def test_upload_validation_accepts_jpeg_and_rejects_bad_extension():
    valid = validate_upload(jpeg_bytes(), "field.jpg", "image/jpeg")
    assert valid.format == "JPEG"
    try:
        validate_upload(jpeg_bytes(), "field.txt", "image/jpeg")
    except ValidationError as error:
        assert error.code == "invalid_extension"
    else:
        raise AssertionError("invalid extension was accepted")


def test_upload_validation_accepts_png():
    valid = validate_upload(png_bytes(), "field.png", "image/png")
    assert valid.format == "PNG"


def test_upload_validation_rejects_mime_mismatch():
    try:
        validate_upload(jpeg_bytes(), "field.jpg", "application/octet-stream")
    except ValidationError as error:
        assert error.code == "unsupported_mime"
    else:
        raise AssertionError("MIME mismatch was accepted")


def test_upload_validation_rejects_corrupt_image():
    try:
        validate_upload(corrupt_jpeg_bytes(), "field.jpg", "image/jpeg")
    except ValidationError as error:
        assert error.code == "corrupted_image"
    else:
        raise AssertionError("corrupt image was accepted")


def test_upload_validation_rejects_oversized_image():
    large_bytes = b"\x00" * (30 * 1024 * 1024)  # 30MB
    try:
        validate_upload(large_bytes, "field.jpg", "image/jpeg")
    except ValidationError as error:
        assert error.code == "file_too_large"
    else:
        raise AssertionError("oversized image was accepted")


def test_upload_validation_rejects_excessive_pixels():
    # Create a small JPEG header that claims excessive dimensions
    large_image = Image.new("RGB", (10000, 10000), (30, 120, 60))
    result = BytesIO()
    large_image.save(result, format="JPEG")
    try:
        validate_upload(result.getvalue(), "field.jpg", "image/jpeg")
    except ValidationError as error:
        assert error.code in ("too_many_pixels", "corrupted_image")
    else:
        raise AssertionError("excessive pixel image was accepted")


def test_upload_validation_rejects_empty_file():
    try:
        validate_upload(b"", "field.jpg", "image/jpeg")
    except ValidationError as error:
        assert error.code == "empty_file"
    else:
        raise AssertionError("empty file was accepted")


# Metadata tests
def test_metadata_extraction_with_exif():
    image = Image.new("RGB", (100, 100), (30, 120, 60))
    from PIL.ExifTags import TAGS
    exif = image.getexif()
    # Use the correct EXIF tag numbers
    exif[271] = "Test Camera"  # Make
    exif[272] = "Test Model"  # Model
    exif[305] = "Test Software"  # Software
    
    result = BytesIO()
    image.save(result, format="JPEG", exif=exif)
    
    metadata = extract_metadata(result.getvalue())
    assert metadata["status"] == "available"
    assert metadata["exif_present"] == True
    assert metadata["camera_make"] == "Test Camera"
    assert metadata["camera_model"] == "Test Model"
    assert metadata["software"] == "Test Software"


def test_metadata_extraction_without_exif():
    image = Image.new("RGB", (100, 100), (30, 120, 60))
    result = BytesIO()
    image.save(result, format="PNG")  # PNG typically has no EXIF
    
    metadata = extract_metadata(result.getvalue())
    assert metadata["status"] == "unavailable"
    assert metadata["exif_present"] == False
    assert "No EXIF metadata present" in "".join(metadata["notes"])


def test_metadata_extraction_handles_malformed():
    # Create a minimal JPEG with no EXIF
    minimal_jpeg = jpeg_bytes()
    metadata = extract_metadata(minimal_jpeg)
    assert metadata["status"] in ("unavailable", "available")
    # Should not crash


# Copy-move tests
def test_copy_move_normal_image():
    image = Image.new("RGB", (200, 200), (30, 120, 60))
    # Add some texture
    pixels = np.array(image)
    noise = np.random.randint(0, 50, (200, 200, 3), dtype=np.uint8)
    pixels = np.clip(pixels.astype(int) + noise, 0, 255).astype(np.uint8)
    image = Image.fromarray(pixels)
    
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    result = detect_copy_move(gray)
    
    assert result.name == "copy_move"
    assert result.status in ("not_detected", "insufficient_evidence")
    assert result.score == 0.0


def test_copy_move_low_keypoint_image():
    # Very smooth image with few keypoints
    image = Image.new("RGB", (200, 200), (128, 128, 128))
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    result = detect_copy_move(gray)
    
    assert result.status == "insufficient_evidence"
    assert "Too few reliable keypoints" in result.explanation


def test_copy_move_repetitive_pattern_hard_negative():
    # Create a repetitive pattern (hard negative)
    pattern = np.tile(np.random.randint(0, 255, (20, 20, 3), dtype=np.uint8), (10, 10, 1))
    image = Image.fromarray(pattern)
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    result = detect_copy_move(gray)
    
    # Should either be not_detected or handle as repetitive texture
    assert result.status in ("not_detected", "insufficient_evidence")
    assert result.score == 0.0


# Local anomaly tests
def test_local_anomaly_normal_image():
    image = Image.new("RGB", (200, 200), (30, 120, 60))
    pixels = np.array(image)
    noise = np.random.randint(0, 30, (200, 200, 3), dtype=np.uint8)
    pixels = np.clip(pixels.astype(int) + noise, 0, 255).astype(np.uint8)
    image = Image.fromarray(pixels)
    
    bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    result = detect_local_anomaly(bgr)
    
    assert result.name == "local_anomaly"
    assert result.status in ("not_detected", "insufficient_evidence")
    assert result.score >= 0.0


def test_local_anomaly_small_image():
    image = Image.new("RGB", (50, 50), (30, 120, 60))
    bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    result = detect_local_anomaly(bgr)
    
    assert result.status == "insufficient_evidence"
    assert "too small" in result.explanation.lower()


# Compression tests
def test_compression_detection():
    image = Image.new("RGB", (200, 200), (30, 120, 60))
    result = BytesIO()
    image.save(result, format="JPEG", quality=85)
    jpeg_bytes = result.getvalue()
    
    bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    result = detect_compression(bgr, jpeg_bytes, "JPEG", (200, 200))
    
    assert result.name == "compression"
    assert result.status in ("detected", "not_detected")
    assert result.score >= 0.0
    assert result.metrics["format"] == "JPEG"


# Feature builder tests
def test_feature_builder_ordering():
    from backend.forensic.common import DetectorResult
    
    detectors = {
        "copy_move": DetectorResult(
            name="copy_move", status="not_detected", score=0.0,
            heatmap=np.zeros((100, 100)), explanation="test",
            metrics={"verified_match_count": 0, "inlier_ratio": 0.0, "region_area_fraction": 0.0}
        ),
        "local_anomaly": DetectorResult(
            name="local_anomaly", status="not_detected", score=0.0,
            heatmap=np.zeros((100, 100)), explanation="test",
            metrics={"max_anomaly": 0.0, "mean_anomaly": 0.0, "anomalous_patch_fraction": 0.0}
        ),
        "compression": DetectorResult(
            name="compression", status="not_detected", score=0.0,
            heatmap=np.zeros((100, 100)), explanation="test",
            metrics={"resampling_score": 0.0, "blockiness": 0.0}
        )
    }
    
    spatial = {"max_iou": 0.0, "max_dice": 0.0}
    image_info = {"megapixels": 0.01, "bytes_per_pixel": 0.5}
    
    features = build_base_features(detectors, spatial, image_info)
    ordered = to_ordered_list(features)
    
    assert len(ordered) == len(FEATURE_NAMES)
    assert all(isinstance(v, (int, float)) for v in ordered)


def test_feature_builder_missing_values():
    from backend.forensic.common import DetectorResult
    
    detectors = {
        "copy_move": None,
        "local_anomaly": None,
        "compression": None
    }
    
    spatial = {"max_iou": 0.0, "max_dice": 0.0}
    image_info = {"megapixels": 0.01, "bytes_per_pixel": 0.5}
    
    features = build_base_features(detectors, spatial, image_info)
    
    # Should handle None detectors gracefully
    assert features["copy_move_verified_matches"] == 0.0
    assert features["copy_move_inlier_ratio"] == 0.0


def test_context_builder():
    from backend.forensic.common import DetectorResult
    
    detectors = {
        "copy_move": DetectorResult(
            name="copy_move", status="detected", score=0.5,
            heatmap=np.zeros((100, 100)), explanation="test",
            metrics={}
        ),
        "local_anomaly": DetectorResult(
            name="local_anomaly", status="not_detected", score=0.0,
            heatmap=np.zeros((100, 100)), explanation="test",
            metrics={}
        ),
        "compression": DetectorResult(
            name="compression", status="not_detected", score=0.0,
            heatmap=np.zeros((100, 100)), explanation="test",
            metrics={}
        )
    }
    
    metadata = {"exif_present": True}
    context = build_context(detectors, metadata)
    
    assert context["metadata_available"] == True
    assert context["copy_move_status"] == "detected"
    assert context["local_anomaly_status"] == "not_detected"


# Fusion model tests
def test_trained_model_prediction_and_schema_mismatch(tmp_path):
    x = np.array([[0.] * len(FEATURE_NAMES), [1.] * len(FEATURE_NAMES), [.1] * len(FEATURE_NAMES), [.9] * len(FEATURE_NAMES)])
    estimator = build_calibrated(cv=2); estimator.fit(x, [0, 1, 0, 1])
    model_path = tmp_path / "model.joblib"
    save_model(TrainedModel(estimator, FEATURE_NAMES, "test", "test-data", "features-v1", "calibrated_logistic_regression", {}), model_path)
    output = predict_evidence(dict(zip(FEATURE_NAMES, x[1])), model_path)
    assert output["mode"] == "trained_model"
    try:
        predict_evidence({}, model_path)
    except ValueError as error:
        assert "schema mismatch" in str(error).lower()
    else:
        raise AssertionError("schema mismatch was accepted")


def test_fusion_fallback_mode():
    import tempfile
    from pathlib import Path
    from backend import config
    
    features = {name: 0.0 for name in FEATURE_NAMES}
    features["copy_move_inlier_ratio"] = 0.5
    features["copy_move_verified_matches"] = 30
    features["patch_max_anomaly"] = 5.0
    features["patch_anomaly_fraction"] = 0.1
    features["spatial_dice"] = 0.6
    features["compression_score"] = 0.4
    features["natural_processing_similarity"] = 0.3
    
    # Test fallback with no model path (should use demo fallback)
    # Use a non-existent path to force fallback mode
    nonexistent_path = Path(tempfile.gettempdir()) / "nonexistent_model.joblib"
    output = predict_evidence(features, nonexistent_path)
    assert output["mode"] == "demo_fallback"
    assert output["demo_mode"] == True
    assert "DEMO MODE" in output["note"]
    assert 0 <= output["manipulation_evidence"] <= 100


def test_fusion_fallback_probability_calculation():
    features = {name: 0.0 for name in FEATURE_NAMES}
    features["copy_move_inlier_ratio"] = 0.8
    features["copy_move_verified_matches"] = 50
    features["patch_max_anomaly"] = 8.0
    features["patch_anomaly_fraction"] = 0.2
    features["spatial_dice"] = 0.7
    features["compression_score"] = 0.5
    features["natural_processing_similarity"] = 0.2
    
    prob = _fallback_probability(features)
    assert 0.0 <= prob <= 1.0
    # High evidence should give higher probability
    assert prob > 0.5


# API integration tests
def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_endpoint():
    client = TestClient(app)
    response = client.post(
        "/api/analyze",
        files={"file": ("test.jpg", jpeg_bytes(), "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert "manipulation_evidence" in data
    assert "data_coverage" in data
    assert "risk_band" in data


def test_get_analysis_endpoint():
    client = TestClient(app)
    # First create an analysis
    create_response = client.post(
        "/api/analyze",
        files={"file": ("test.jpg", jpeg_bytes(), "image/jpeg")}
    )
    analysis_id = create_response.json()["analysis_id"]
    
    # Then retrieve it
    response = client.get(f"/api/analysis/{analysis_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["analysis_id"] == analysis_id


def test_get_analysis_not_found():
    client = TestClient(app)
    response = client.get("/api/analysis/nonexistent")
    assert response.status_code == 404


def test_get_report_endpoint():
    client = TestClient(app)
    # First create an analysis
    create_response = client.post(
        "/api/analyze",
        files={"file": ("test.jpg", jpeg_bytes(), "image/jpeg")}
    )
    analysis_id = create_response.json()["analysis_id"]
    
    # Get JSON report
    response = client.get(f"/api/report/{analysis_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["analysis_id"] == analysis_id
    
    # Get HTML report
    response = client.get(f"/api/report/{analysis_id}?format=html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_report_not_found():
    client = TestClient(app)
    response = client.get("/api/report/nonexistent")
    assert response.status_code == 404


def test_get_report_pdf_format():
    client = TestClient(app)
    # First create an analysis
    create_response = client.post(
        "/api/analyze",
        files={"file": ("test.jpg", jpeg_bytes(), "image/jpeg")}
    )
    analysis_id = create_response.json()["analysis_id"]
    
    # Try to get PDF report (may fail if weasyprint not installed)
    pdf_response = client.get(f"/api/report/{analysis_id}?format=pdf")
    # Should either succeed with PDF or fail gracefully with 501
    assert pdf_response.status_code in (200, 501)
    if pdf_response.status_code == 200:
        assert "application/pdf" in pdf_response.headers["content-type"]


def test_analyze_invalid_upload():
    client = TestClient(app)
    response = client.post(
        "/api/analyze",
        files={"file": ("test.txt", b"not an image", "text/plain")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "code" in data["detail"]


# End-to-end test
def test_end_to_end_analysis_flow():
    client = TestClient(app)
    
    # Step 1: Upload and analyze
    upload_response = client.post(
        "/api/analyze",
        files={"file": ("test.jpg", jpeg_bytes(), "image/jpeg")}
    )
    assert upload_response.status_code == 200
    analysis_data = upload_response.json()
    analysis_id = analysis_data["analysis_id"]
    
    # Step 2: Retrieve analysis
    analysis_response = client.get(f"/api/analysis/{analysis_id}")
    assert analysis_response.status_code == 200
    retrieved_data = analysis_response.json()
    assert retrieved_data["analysis_id"] == analysis_id
    
    # Step 3: Get report
    report_response = client.get(f"/api/report/{analysis_id}")
    assert report_response.status_code == 200
    report_data = report_response.json()
    assert report_data["analysis_id"] == analysis_id
    assert "detectors" in report_data
    assert "warnings" in report_data
    assert "limitations" in report_data
    
    # Step 4: Verify structure
    assert all(key in analysis_data for key in [
        "manipulation_evidence", "data_coverage", "risk_band",
        "detectors", "metadata", "fusion", "versions"
    ])
    
    # Step 5: Check fusion mode (either trained model or demo fallback)
    assert analysis_data["fusion"]["mode"] in ("demo_fallback", "trained_model")
    # If it's demo mode, it should be labelled
    if analysis_data["fusion"]["mode"] == "demo_fallback":
        assert analysis_data["fusion"]["demo_mode"] == True
