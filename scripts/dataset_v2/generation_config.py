"""Configuration for Dataset V2 variant generation."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Tuple


@dataclass
class GenerationConfig:
    """Configuration for variant generation."""

    # Dataset paths
    variants_dir: str = "dataset_v2/variants"
    natural_processing_dir: str = "natural_processing"
    manipulated_dir: str = "manipulated"
    hard_negative_dir: str = "hard_negative"
    masks_dir: str = "masks"

    # Source paths
    sources_dir: str = "dataset_v2/sources/deepweeds_raw/images"

    # Metadata paths
    manifest_path: str = "dataset_v2/metadata/manifest.jsonl"
    splits_dir: str = "dataset_v2/splits"

    # Generation parameters
    random_seed: int = 42

    # Natural processing parameter ranges (exclude no-op values)
    jpeg_quality_range: List[int] = field(default_factory=lambda: [70, 75, 80, 85, 90, 95])
    resize_scale_range: List[float] = field(default_factory=lambda: [0.5, 0.75, 0.9, 1.1, 1.25, 1.5])
    sharpen_strength_range: List[float] = field(default_factory=lambda: [0.5, 1.5, 2.0])  # Exclude 1.0 (no-op)
    brightness_range: List[float] = field(default_factory=lambda: [-30, -15, 15, 30])  # Exclude 0 (no-op)
    contrast_range: List[float] = field(default_factory=lambda: [0.7, 0.85, 1.15, 1.3])  # Exclude 1.0 (no-op)

    # Hard negative parameter ranges (more aggressive, non-overlapping with natural processing)
    hn_jpeg_quality_range: List[int] = field(default_factory=lambda: [50, 55, 60, 65])  # Lower quality than natural
    hn_resize_scale_range: List[float] = field(default_factory=lambda: [0.3, 0.4, 0.6, 0.8])  # Different from natural (no 0.5, 0.75, 0.9)
    hn_sharpen_strength_range: List[float] = field(default_factory=lambda: [2.5, 3.0, 3.5])  # Stronger than natural

    # Manipulation parameter ranges
    manipulation_area_ratio_range: List[float] = field(default_factory=lambda: [0.05, 0.1, 0.15, 0.2, 0.25, 0.3])
    copy_move_rotation_range: List[int] = field(default_factory=lambda: [0, 15, 30, 45, 90, 180, 270])
    copy_move_scale_range: List[float] = field(default_factory=lambda: [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3])
    
    # Object removal parameter ranges
    removal_region_configs: List[Tuple[str, float]] = field(default_factory=lambda: [
        ("center", 0.15), ("center", 0.20), ("center", 0.25),
        ("top_left", 0.15), ("top_right", 0.15), ("bottom_left", 0.15), ("bottom_right", 0.15)
    ])
    removal_inpainting_methods: List[str] = field(default_factory=lambda: ["telea", "ns"])
    removal_inpaint_radius: List[int] = field(default_factory=lambda: [3, 5, 7])
    
    # Object insertion parameter ranges
    insertion_region_configs: List[Tuple[str, float]] = field(default_factory=lambda: [
        ("center", 0.15), ("center", 0.20), ("top_left", 0.15), ("top_right", 0.15), ("bottom_left", 0.15), ("bottom_right", 0.15)
    ])
    insertion_rotation_range: List[int] = field(default_factory=lambda: [0, 15, 30, 45, 90])
    insertion_scale_range: List[float] = field(default_factory=lambda: [0.8, 0.9, 1.0, 1.1, 1.2])
    
    # Splicing parameter ranges
    splicing_region_configs: List[Tuple[str, float]] = field(default_factory=lambda: [
        ("center", 0.15), ("center", 0.20), ("top_left", 0.15), ("top_right", 0.15), ("bottom_left", 0.15), ("bottom_right", 0.15)
    ])
    splicing_rotation_range: List[int] = field(default_factory=lambda: [0, 15, 30, 45, 90])
    splicing_scale_range: List[float] = field(default_factory=lambda: [0.8, 0.9, 1.0, 1.1, 1.2])

    # Output format
    output_format: str = "JPEG"
    output_quality: int = 95

    # Pilot configuration
    pilot_source_count: int = 20
    pilot_natural_count: int = 20
    pilot_hard_negative_count: int = 20
    pilot_manipulated_count: int = 25  # Updated to match sum below

    # Distribution of manipulation types in pilot
    pilot_copy_move_count: int = 10  # Increased for diversity
    pilot_removal_count: int = 5
    pilot_insertion_count: int = 5
    pilot_splicing_count: int = 5

    # Dataset version
    dataset_version: str = "dataset-real-v1"

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Validate ranges are not empty
        assert self.jpeg_quality_range, "JPEG quality range cannot be empty"
        assert self.resize_scale_range, "Resize scale range cannot be empty"
        assert self.manipulation_area_ratio_range, "Manipulation area ratio range cannot be empty"

        # Validate pilot counts sum correctly
        total_manipulated = (
            self.pilot_copy_move_count +
            self.pilot_removal_count +
            self.pilot_insertion_count +
            self.pilot_splicing_count
        )
        # Auto-correct pilot_manipulated_count if it doesn't match
        if total_manipulated != self.pilot_manipulated_count:
            self.pilot_manipulated_count = total_manipulated
