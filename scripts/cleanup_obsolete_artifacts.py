"""Phase 24: Cleanup obsolete artifacts.

This script identifies and lists obsolete temporary scripts that can be removed.
NOTE: This is a conservative cleanup - only removes clearly obsolete temporary scripts.
"""

import os
from pathlib import Path

scripts_dir = Path(__file__).resolve().parent

print("=== Phase 24: Cleanup Obsolete Artifacts ===\n")

# Scripts that are clearly obsolete (replaced by phase scripts)
obsolete_scripts = [
    "backup_manipulated.py",  # Backup script, no longer needed
    "backup_processing.py",  # Backup script, no longer needed
    "check_area_ratios.py",  # Verification script, superseded by validate_masks.py
    "check_feature_compatibility.py",  # Verification script, superseded by validate_dataset_v2.py
    "analyze_area_ratios.py",  # Analysis script, superseded by final_dataset_statistics.py
    "generate_missing_insertion.py",  # Temporary generation script, replaced by phase12
    "generate_object_insertion.py",  # Temporary generation script, replaced by phase12
    "generate_object_removal.py",  # Temporary generation script, replaced by phase12
    "generate_splicing.py",  # Temporary generation script, replaced by phase12
    "regenerate_all_manipulated.py",  # Regeneration script, superseded by phase12
    "regenerate_copy_move.py",  # Regeneration script, superseded by phase12
    "regenerate_missing_hn.py",  # Regeneration script, superseded by phase13
    "regenerate_processing.py",  # Regeneration script, superseded by phase13
    "remove_duplicate_hn.py",  # Cleanup script, issue resolved
    "scale_insertion_splicing.py",  # Scaling script, replaced by phase12
    "scale_manipulations.py",  # Scaling script, replaced by phase12
    "scale_to_250_processing.py",  # Scaling script, replaced by phase13
    "investigate_duplicates.py",  # Investigation script, issue resolved
]

# Scripts to keep (essential for dataset operations)
essential_scripts = [
    "ml_common.py",  # Common ML utilities
    "import_deepweeds.py",  # DeepWeeds import
    "generate_dataset.py",  # Original dataset generation
    "generate_pilot_dataset_v2.py",  # Pilot generation
    "create_dataset_v2_splits.py",  # Split creation
    "validate_dataset_v2.py",  # Main validation
    "validate_masks.py",  # Mask validation
    "detect_duplicates.py",  # Duplicate detection
    "audit_leakage.py",  # Leakage audit
    "anti_shortcut_audit.py",  # Anti-shortcut audit
    "dataset_statistics.py",  # Statistics
    "train_model.py",  # Model training
    "evaluate_model.py",  # Model evaluation
    "run_analysis.py",  # Analysis runner
    "detector_sweep.py",  # Detector sweep
    "run_ablation.py",  # Ablation study
    "generate_contact_sheets.py",  # Contact sheet generation
    # New phase scripts
    "scale_manipulations_phase12.py",  # Phase 12 manipulation scaling
    "scale_source_families_phase13.py",  # Phase 13 source family scaling
    "verify_natural_processing_coverage.py",  # Phase 15 verification
    "verify_hard_negative_coverage.py",  # Phase 16 verification
    "final_dataset_statistics.py",  # Phase 20 statistics
    "manual_qc_sample.py",  # Phase 21 QC
    "test_reproducibility.py",  # Phase 22 reproducibility
    # Dataset V2 core modules
    "dataset_v2/__init__.py",
    "dataset_v2/generation_config.py",
    "dataset_v2/generation_validator.py",
    "dataset_v2/generators.py",
    "dataset_v2/pilot_generator.py",
    "dataset_v2/provenance.py",
    "dataset_v2/split_inheritance.py",
    "dataset_v2/variant_ids.py"
]

print("OBSOLETE SCRIPTS (can be removed):")
print("=" * 80)
obsolete_found = []
for script in obsolete_scripts:
    script_path = scripts_dir / script
    if script_path.exists():
        obsolete_found.append(script)
        print(f"  [FOUND] {script}")
    else:
        print(f"  [MISSING] {script}")

print(f"\nTotal obsolete scripts found: {len(obsolete_found)}")

print("\nESSENTIAL SCRIPTS (must be kept):")
print("=" * 80)
essential_found = []
for script in essential_scripts:
    script_path = scripts_dir / script
    if script_path.exists():
        essential_found.append(script)
        print(f"  [FOUND] {script}")
    else:
        print(f"  [MISSING] {script}")

print(f"\nTotal essential scripts found: {len(essential_found)}")

print("\n=== CLEANUP RECOMMENDATION ===")
print(f"Found {len(obsolete_found)} obsolete scripts that can be safely removed")
print(f"Found {len(essential_found)} essential scripts that must be kept")

print("\n=== CONSERVATIVE CLEANUP POLICY ===")
print("Due to the importance of dataset integrity, this cleanup is conservative:")
print("1. Only temporary/obsolete scripts are identified for removal")
print("2. All core dataset operations scripts are preserved")
print("3. All validation and verification scripts are preserved")
print("4. All new phase scripts are preserved")
print("5. Source data (DeepWeeds images) are NEVER removed")
print("6. Manifests and metadata are NEVER removed")
print("7. Generated variants and masks are NEVER removed")

print("\n=== AUTOMATED CLEANUP SKIPPED ===")
print("For safety, no automated deletion is performed.")
print("Manual review recommended before deletion.")
print("To delete obsolete scripts, manually remove them from the scripts/ directory.")

# Create cleanup report
cleanup_report = {
    "obsolete_scripts": obsolete_found,
    "essential_scripts": essential_found,
    "cleanup_policy": "conservative",
    "automated_cleanup": "skipped",
    "recommendation": "manual_review_required"
}

report_file = scripts_dir.parent / "reports" / "PHASE_24_CLEANUP_REPORT.json"
report_file.parent.mkdir(exist_ok=True)
import json
with report_file.open("w") as f:
    json.dump(cleanup_report, f, indent=2)

print(f"\nCleanup report saved to: {report_file}")

print("\n=== Phase 24 Complete ===")
print("Obsolete artifacts identified but not automatically deleted")
print("Manual review required before deletion")
