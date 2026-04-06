from pathlib import Path
import pandas as pd

from pathlib import Path


from src.preprocessing.spatial_preprocessing import run_preprocessing_pipeline
from src.validation.spatial_validation import run_spatial_validation
from src.reporting.reporting import (
    enrich_spatial_issues,
    build_execution_summary,
    build_station_overview,
    generate_execution_report_text,
    save_reporting_outputs,
)


# ============================================================
# STEP 0. CONFIGURATION
# ============================================================


# Resolve project root dynamically (assuming this file is in src/config/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

PLUVIO_FILE = PROJECT_ROOT /"data/raw/PLUVIOS.csv"
COORDS_FILE = PROJECT_ROOT /"data/raw/coordenadas_estaciones.csv"
OUTPUT_DIR = PROJECT_ROOT /"data/outputs/test_run"

VARIABLE_NAME = "precipitation"


SPATIAL_VALIDATION_CONFIG = {
    "min_neighbors": 3,
    "n_neighbors": 5,
    "max_distance": 50000,
    "expected_value_method": "median",
    "abs_residual_threshold": 10.0,
    "severity_thresholds": {
        "medium": 10.0,
        "high": 20.0,
    },
}

ISSUE_RULES = {
    "spatial_residual_exceeded": {
        "severity": "MEDIUM",
        "recommended_action": "review_station_value_against_neighbors",
    },
    "insufficient_spatial_context": {
        "severity": "LOW",
        "recommended_action": "check_station_density",
    },
}


# ============================================================
# STEP 1. LOAD CSV DATA
# ============================================================

print("Loading CSV data...")

df = pd.read_csv(
    PLUVIO_FILE,
    sep=";",
    encoding="latin-1",
    decimal=",",
)

print(f"Loaded {len(df)} records")


# ============================================================
# STEP 2. PREPROCESSING
# ============================================================

print("Running preprocessing...")

merged_df, spatial_input_df, preprocessing_summary_df = (
    run_preprocessing_pipeline(
        obs_df=df,
        coords_filepath=COORDS_FILE,
    )
)

print(f"Records ready for validation: {len(spatial_input_df)}")


# ============================================================
# STEP 3. SPATIAL VALIDATION
# ============================================================

print("Running spatial validation...")
print("Number of rows:", len(spatial_input_df))
print("Unique stations:", spatial_input_df["Estacion"].nunique())
print(spatial_input_df[["Estacion", "X", "Y"]].head(20))

raw_issues_df, validated_df = run_spatial_validation(
    df=spatial_input_df,
    variable=VARIABLE_NAME,
    config=SPATIAL_VALIDATION_CONFIG,
)

print(f"Detected {len(raw_issues_df)} issues")


# ============================================================
# STEP 4. REPORTING
# ============================================================

print("Building reporting...")

enriched_issues_df = enrich_spatial_issues(
    issues_df=raw_issues_df,
    issue_rules=ISSUE_RULES,
)

execution_summary_df = build_execution_summary(
    validated_df=validated_df,
    issues_df=enriched_issues_df,
    preprocessing_summary_df=preprocessing_summary_df,
)

station_overview_df = build_station_overview(
    validated_df=validated_df,
    issues_df=enriched_issues_df,
)

report_text = generate_execution_report_text(
    execution_id="test_run",
    reference_date=pd.Timestamp.now(),
    execution_summary_df=execution_summary_df,
    station_overview_df=station_overview_df,
)

print("\n=== REPORT ===")
print(report_text)


# ============================================================
# STEP 5. SAVE OUTPUTS
# ============================================================

print("Saving outputs...")

save_reporting_outputs(
    issues_df=enriched_issues_df,
    execution_summary_df=execution_summary_df,
    station_overview_df=station_overview_df,
    report_text=report_text,
    output_dir=Path(OUTPUT_DIR),
)

print(f"Outputs saved to: {OUTPUT_DIR}")

