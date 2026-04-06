from __future__ import annotations

from pathlib import Path


# ============================================================
# STEP 0. PROJECT ROOT PATH
# ============================================================

# Resolve project root dynamically (assuming this file is in src/config/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ============================================================
# STEP 1. DATA PATHS
# ============================================================

DATA_DIR = PROJECT_ROOT / "data"

RAW_DATA_DIR = DATA_DIR / "raw"
OUTPUTS_DIR = DATA_DIR / "outputs"


# Input files (adjust as needed)
PLUVIO_TEST_FILE = RAW_DATA_DIR / "PLUVIOS.csv"
COORDINATES_FILE = RAW_DATA_DIR / "coordenadas_estaciones.csv"

# Tags file (for DB extraction mode)
TAGS_FILE = PROJECT_ROOT / "config" / "tags_contraste_pluvios.txt"


# ============================================================
# STEP 2. EXECUTION CONFIGURATION
# ============================================================

VARIABLE_NAME = "precipitation"

# Default execution mode
USE_DATABASE = False  # True → extraction pipeline, False → CSV mode


# ============================================================
# STEP 3. DATA QUALITY SETTINGS
# ============================================================

# Quality codes considered invalid (set value to NaN)
INVALID_QUALITY_CODES = (3, 8)


# ============================================================
# STEP 4. SPATIAL VALIDATION CONFIGURATION
# ============================================================

SPATIAL_VALIDATION_CONFIG = {
    "min_neighbors": 3,
    "n_neighbors": 5,
    "max_distance": 50000,  # meters
    "expected_value_method": "median",  # "median", "mean", "idw_neighbors"
    "abs_residual_threshold": 10.0,
    "severity_thresholds": {
        "medium": 10.0,
        "high": 20.0,
    },
}


# ============================================================
# STEP 5. REPORTING RULES
# ============================================================

SPATIAL_ISSUE_RULES = {
    "spatial_residual_exceeded": {
        "severity": "MEDIUM",
        "recommended_action": "review_station_value_against_neighboring_stations",
    },
    "insufficient_spatial_context": {
        "severity": "LOW",
        "recommended_action": "check_station_density_or_missing_neighbor_data",
    },
}


# ============================================================
# STEP 6. OUTPUT SETTINGS
# ============================================================

# Base output directory
BASE_OUTPUT_DIR = OUTPUTS_DIR / "spatial_validation"

# Whether to save intermediate files
SAVE_INTERMEDIATE_OUTPUTS = True

# Whether to save final reporting outputs
SAVE_REPORTING_OUTPUTS = True

ENABLE_GIS_EXPORT = True


# ============================================================
# STEP 7. LOGGING SETTINGS (optional)
# ============================================================

LOGS_DIR = PROJECT_ROOT / "logs"
ENABLE_LOGGING = True
LOG_FILE_PREFIX = "spatial_pipeline"
LOG_LEVEL = "INFO"


