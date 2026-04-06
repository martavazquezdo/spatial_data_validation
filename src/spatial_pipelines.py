"""
Spatial validation pipeline orchestration.

This module coordinates the full validation workflow:
- data extraction from database (optional)
- preprocessing and spatial enrichment
- spatial consistency validation
- reporting and output generation

The pipeline is designed to be reproducible, modular,
and scalable to multiple stations and time windows.
"""

from __future__ import annotations

import logging
import pandas as pd

from config.settings import (
    USE_DATABASE,
    PLUVIO_TEST_FILE,
    COORDINATES_FILE,
    VARIABLE_NAME,
    SPATIAL_VALIDATION_CONFIG,
    SPATIAL_ISSUE_RULES,
    BASE_OUTPUT_DIR,
    LOGS_DIR,
    ENABLE_LOGGING,
    LOG_FILE_PREFIX,
    LOG_LEVEL,
    ENABLE_GIS_EXPORT
)

from src.utils.logging_utils import (
    generate_execution_id,
    setup_logger,
)
if USE_DATABASE:
    from src.extraction.extract_stations import run_extraction_pipeline
from src.preprocessing.spatial_preprocessing import run_preprocessing_pipeline
from src.validation.spatial_validation import run_spatial_validation
from src.validation.spatial_layers import generate_spatial_outputs
from src.reporting.reporting import (
    enrich_spatial_issues,
    build_execution_summary,
    build_station_overview,
    generate_execution_report_text,
    save_reporting_outputs,
)


# ============================================================
# MAIN PIPELINE FUNCTION
# ============================================================

def run_spatial_pipeline() -> None:
    """
    Execute full spatial validation pipeline.
    """

    # ========================================================
    # STEP 0. LOGGING AND EXECUTION CONTEXT
    # ========================================================

    run_datetime = pd.Timestamp.now()
    execution_id = generate_execution_id()
    log_file_path = None

    if ENABLE_LOGGING:
        log_file_path = setup_logger(
            log_dir=LOGS_DIR,
            execution_id=execution_id,
            run_datetime=run_datetime,
            log_prefix=LOG_FILE_PREFIX,
        )

    logging.info("Spatial validation pipeline started.")
    logging.info(f"Execution ID: {execution_id}")

    try:
        # ====================================================
        # STEP 1. DATA INPUT (DB OR CSV)
        # ====================================================

        logging.info("STEP 1 - Data input started.")
        
        obs_df = None
        extraction_summary_df = None
        
        if USE_DATABASE:
            logging.info("Running extraction pipeline from database.")
            obs_df, extraction_summary_df = run_extraction_pipeline()
            logging.info("Database extraction finished successfully.")
        else:
            logging.info(f"Loading CSV input from: {PLUVIO_TEST_FILE}")
            obs_df = pd.read_csv(
                PLUVIO_TEST_FILE,
                sep=";",
                encoding="latin-1",
                decimal=",",
            )
            extraction_summary_df = None
            logging.info("CSV input loaded successfully.")

        logging.info(f"Raw records loaded: {len(obs_df)}")

        # ====================================================
        # STEP 2. PREPROCESSING
        # ====================================================

        logging.info("STEP 2 - Running preprocessing pipeline.")

        merged_df, spatial_input_df, preprocessing_summary_df = (
            run_preprocessing_pipeline(
                obs_df=obs_df,
                coords_filepath=COORDINATES_FILE,
            )
        )

        logging.info(f"Merged records: {len(merged_df)}")
        logging.info(f"Records ready for spatial validation: {len(spatial_input_df)}")

        if "Estacion" in spatial_input_df.columns:
            logging.info(
                f"Unique stations ready for validation: "
                f"{spatial_input_df['Estacion'].nunique()}"
            )

        # ====================================================
        # STEP 3. SPATIAL VALIDATION
        # ====================================================

        logging.info("STEP 3 - Running spatial validation.")

        raw_issues_df, validated_df = run_spatial_validation(
            df=spatial_input_df,
            variable=VARIABLE_NAME,
            config=SPATIAL_VALIDATION_CONFIG,
        )

        logging.info(f"Validated records: {len(validated_df)}")
        logging.info(f"Spatial issues detected: {len(raw_issues_df)}")

        # ====================================================
        # STEP 4. REPORTING
        # ====================================================

        logging.info("STEP 4 - Building reporting outputs.")

        enriched_issues_df = enrich_spatial_issues(
            issues_df=raw_issues_df,
            issue_rules=SPATIAL_ISSUE_RULES,
        )

        execution_summary_df = build_execution_summary(
            validated_df=validated_df,
            issues_df=enriched_issues_df,
            preprocessing_summary_df=preprocessing_summary_df,
            extraction_summary_df=extraction_summary_df,
        )

        station_overview_df = build_station_overview(
            validated_df=validated_df,
            issues_df=enriched_issues_df,
        )

        report_text = generate_execution_report_text(
            execution_id=execution_id,
            reference_date=run_datetime,
            execution_summary_df=execution_summary_df,
            station_overview_df=station_overview_df,
        )

        if not execution_summary_df.empty and "status" in execution_summary_df.columns:
           logging.info(
                f"Execution status: {execution_summary_df.iloc[0]['status']}"
            )

        # ====================================================
        # STEP 5. SAVE OUTPUTS
        # ====================================================

        output_dir = BASE_OUTPUT_DIR

        logging.info(f"STEP 5 - Saving outputs to: {output_dir}")

        save_reporting_outputs(
            issues_df=enriched_issues_df,
           execution_summary_df=execution_summary_df,
            station_overview_df=station_overview_df,
            report_text=report_text,
            output_dir=output_dir,
        )

        logging.info("Outputs saved successfully.")
        logging.info("Spatial validation pipeline finished successfully.")

        if log_file_path is not None:
            logging.info(f"Log file written to: {log_file_path}")
            
        # ============================================================
        # STEP 6 - GIS EXPORT (OPTIONAL)
        # ============================================================
        if ENABLE_GIS_EXPORT:
            logging.info("STEP 6 - Generating GIS outputs.")

            generate_spatial_outputs(
                validated_df=validated_df,
                issues_df=enriched_issues_df,
             output_dir=output_dir,
            )

            logging.info("GIS outputs generated successfully.")

    except Exception:
        logging.exception("Pipeline execution failed.")
        raise
    
    
if __name__ == "__main__":
    print("Launching spatial validation pipeline...")
    run_spatial_pipeline()
    