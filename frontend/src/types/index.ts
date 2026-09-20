export interface AnalysisResult {
  analysis_id: string;
  created_at: string;
  duration_ms: number;
  image: {
    filename: string;
    sha256: string;
    file_size: number;
    format: string;
    mime: string;
    width: number;
    height: number;
    megapixels: number;
    analysis_width: number;
    analysis_height: number;
    analysis_scale: number;
  };
  manipulation_evidence: number;
  data_coverage: number;
  risk_band: string;
  bands: {
    low_threshold: number;
    high_threshold: number;
    note: string;
  };
  detectors: {
    copy_move: DetectorResult;
    local_anomaly: DetectorResult;
    compression: DetectorResult;
    visible_timestamp: DetectorResult;
  };
  spatial_agreement: {
    combined_dice: number;
    combined_iou: number;
    consensus_regions: Region[];
  };
  natural_processing: {
    natural_processing_similarity: number;
    matched_transformations: string[];
    matched_device_domain: string | null;
    confidence: number;
  };
  coverage: {
    score: number;
    resolution_similarity: number;
    forensic_feature_similarity: number;
    device_coverage: number;
    quality_score: number;
  };
  metadata: {
    available: boolean;
    camera_make: string | null;
    camera_model: string | null;
    capture_date: string | null;
    software: string | null;
    orientation: number | null;
  };
  timestamp_integrity: {
    exif_timestamp: string | null;
    visible_timestamp: string | null;
    visible_timestamp_location: string | null;
    visible_timestamp_confidence: number | null;
    verification_status: string;
  };
  features: Record<string, number>;
  fusion: {
    manipulation_evidence: number;
    probability: number;
    mode: string;
    demo_mode: boolean;
    model_version: string;
    dataset_version: string;
    model_kind: string;
    note: string;
  };
  explanation: {
    primary_evidence: string[];
    supporting_evidence: string[];
    weak_evidence: string[];
    unavailable_evidence: string[];
    natural_processing_note: string;
    metadata_note: string;
  };
  warnings: string[];
  limitations: string[];
  artifacts: {
    analysis_image: string;
    heatmap: string;
    overlay: string;
    note: string;
  };
  regions: Region[];
  versions: {
    model_version: string;
    dataset_version: string;
    feature_version: string;
    pipeline_version: string;
  };
  disclaimer: string;
}

export interface DetectorResult {
  name: string;
  status: 'detected' | 'not_detected' | 'insufficient_evidence' | 'not_applicable';
  score: number;
  explanation: string;
  metrics: Record<string, any>;
  regions?: Region[];
}

export interface Region {
  x: number;
  y: number;
  width: number;
  height: number;
  area_fraction?: number;
}

export interface UploadConfig {
  max_file_size_mb: number;
  allowed_formats: string[];
  review_bands: {
    low_threshold: number;
    high_threshold: number;
  };
  limitations: string[];
  disclaimer: string;
}
