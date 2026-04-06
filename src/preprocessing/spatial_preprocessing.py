from __future__ import annotations

from datetime import datetime
from typing import Iterable

import pandas as pd
import numpy as np


# ============================================================
# STEP 0. VALIDATE REQUIRED COLUMNS
# ============================================================

REQUIRED_OBS_COLUMNS = ["Nombre señal", "Valor", "Calidad"]
REQUIRED_COORD_COLUMNS = ["Estacion", "X", "Y"]


def validate_required_columns(
    df: pd.DataFrame,
    required_columns: Iterable[str],
    df_name: str,
) -> None:
    """
    Validate that a DataFrame contains all required columns.

    Parameters
    ----------
    df : DataFrame
        Input DataFrame to validate.
    required_columns : Iterable[str]
        List of required column names.
    df_name : str
        Name of the DataFrame (used for error messages).
    """
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns in {df_name}: {missing}"
        )


# ============================================================
# STEP 1. LOAD STATION COORDINATES
# ============================================================

def load_station_coordinates(
    filepath: str,
    delimiter: str = ";",
    encoding: str = "latin-1",
) -> pd.DataFrame:
    """
    Load station coordinates from CSV file.

    Expected columns: Estacion, X, Y

    Parameters
    ----------
    filepath : str
        Path to coordinates CSV file.

    Returns
    -------
    DataFrame
        Coordinates DataFrame.
    """
    coords_df = pd.read_csv(
        filepath,
        delimiter=delimiter,
        encoding=encoding,
        usecols=REQUIRED_COORD_COLUMNS,
    )

    validate_required_columns(coords_df, REQUIRED_COORD_COLUMNS, "coords_df")

    return coords_df


# ============================================================
# STEP 2. STANDARDIZE OBSERVATION DATAFRAME
# ============================================================

def standardize_observations_df(obs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a defensive copy and validate required observation columns.

    Parameters
    ----------
    obs_df : DataFrame
        Raw observations DataFrame.

    Returns
    -------
    DataFrame
        Clean copy of observations DataFrame.
    """
    df = obs_df.copy()

    validate_required_columns(df, REQUIRED_OBS_COLUMNS, "obs_df")

    return df


# ============================================================
# STEP 3. EXTRACT STATION CODE FROM TAG
# ============================================================

def extract_station_code(
    obs_df: pd.DataFrame,
    source_col: str = "Nombre señal",
    target_col: str = "Estacion",
    n_chars: int = 5,
) -> pd.DataFrame:
    """
    Extract station identifier from signal name.

    Based on original logic:
    'Estacion' = first 5 characters of 'Nombre señal'

    Parameters
    ----------
    obs_df : DataFrame
    source_col : str
    target_col : str
    n_chars : int

    Returns
    -------
    DataFrame
    """
    df = obs_df.copy()

    df[target_col] = df[source_col].astype(str).str[:n_chars]

    return df


# ============================================================
# STEP 4. APPLY QUALITY FILTER
# ============================================================

def apply_quality_filter(
    obs_df: pd.DataFrame,
    quality_col: str = "Calidad",
    value_col: str = "Valor",
    invalid_quality_codes: tuple[int, ...] = (3, 8),
) -> pd.DataFrame:
    """
    Invalidate values based on quality flags.

    Values with invalid quality codes are set to NaN.

    Parameters
    ----------
    obs_df : DataFrame
    invalid_quality_codes : tuple

    Returns
    -------
    DataFrame
    """
    df = obs_df.copy()

    df.loc[df[quality_col].isin(invalid_quality_codes), value_col] = np.nan

    return df


# ============================================================
# STEP 5. NORMALIZE DATA TYPES
# ============================================================

def normalize_observation_types(
    obs_df: pd.DataFrame,
    value_col: str = "Valor",
    date_col: str = "Fecha",
) -> pd.DataFrame:
    """
    Normalize numeric and datetime columns.

    Parameters
    ----------
    obs_df : DataFrame

    Returns
    -------
    DataFrame
    """
    df = obs_df.copy()

    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    return df


# ============================================================
# STEP 6. MERGE OBSERVATIONS WITH COORDINATES
# ============================================================

def merge_observations_with_coordinates(
    obs_df: pd.DataFrame,
    coords_df: pd.DataFrame,
    station_col: str = "Estacion",
    how: str = "left",
) -> pd.DataFrame:
    """
    Merge observation data with station coordinates.

    Parameters
    ----------
    obs_df : DataFrame
    coords_df : DataFrame

    Returns
    -------
    DataFrame
    """
    validate_required_columns(obs_df, [station_col], "obs_df")
    validate_required_columns(coords_df, REQUIRED_COORD_COLUMNS, "coords_df")

    merged_df = pd.merge(obs_df, coords_df, on=station_col, how=how)

    return merged_df


# ============================================================
# STEP 7. ADD PREPROCESSING FLAGS
# ============================================================

def add_preprocessing_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add boolean flags useful for QA and reporting.

    Returns
    -------
    DataFrame
    """
    out = df.copy()

    out["has_valid_value"] = out["Valor"].notna()
    out["has_valid_coordinates"] = out["X"].notna() & out["Y"].notna()
    out["is_ready_for_spatial_validation"] = (
        out["has_valid_value"] & out["has_valid_coordinates"]
    )

    return out


# ============================================================
# STEP 8. PREPARE FINAL DATASET FOR SPATIAL VALIDATION
# ============================================================

def prepare_spatial_validation_input(
    df: pd.DataFrame,
    drop_duplicates: bool = True,
) -> pd.DataFrame:
    """
    Generate final clean dataset for spatial validation.
    """
    out = df.copy()

    out = out.dropna(subset=["Valor", "X", "Y"])

    if drop_duplicates:
        # Only remove duplicates if both station and timestamp are available
        if "Estacion" in out.columns and "Fecha" in out.columns:
            out = out.drop_duplicates(subset=["Estacion", "Fecha"])

    out = out.reset_index(drop=True)

    return out


# ============================================================
# STEP 9. BUILD PREPROCESSING SUMMARY
# ============================================================

def build_preprocessing_summary(
    df_raw: pd.DataFrame,
    df_merged: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build summary statistics of preprocessing stage.

    Returns
    -------
    DataFrame
    """
    summary = {
        "n_raw_records": len(df_raw),
        "n_merged_records": len(df_merged),
        "n_missing_values": int(df_merged["Valor"].isna().sum())
        if "Valor" in df_merged.columns else np.nan,
        "n_missing_coordinates": int(
            df_merged[["X", "Y"]].isna().any(axis=1).sum()
        ) if {"X", "Y"}.issubset(df_merged.columns) else np.nan,
        "n_ready_for_spatial_validation": int(
            df_merged["is_ready_for_spatial_validation"].sum()
        ) if "is_ready_for_spatial_validation" in df_merged.columns else np.nan,
    }

    return pd.DataFrame([summary])


# ============================================================
# STEP 10. FULL PREPROCESSING PIPELINE
# ============================================================

def run_preprocessing_pipeline(
    obs_df: pd.DataFrame,
    coords_filepath: str,
    invalid_quality_codes: tuple[int, ...] = (3, 8),
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Execute full preprocessing pipeline.

    Steps:
    1. Load coordinates
    2. Standardize observations
    3. Extract station code
    4. Apply quality filtering
    5. Normalize types
    6. Merge with coordinates
    7. Add QA flags
    8. Prepare spatial validation input
    9. Build summary

    Returns
    -------
    merged_df : DataFrame
        Full dataset with coordinates and flags.
    spatial_input_df : DataFrame
        Clean dataset ready for spatial validation.
    summary_df : DataFrame
        Preprocessing summary.
    """

    # 1. Load coordinates
    coords_df = load_station_coordinates(coords_filepath)

    # 2. Standardize observations
    df = standardize_observations_df(obs_df)

    # 3. Extract station codes
    df = extract_station_code(df)

    # 4. Apply quality filtering
    df = apply_quality_filter(df, invalid_quality_codes=invalid_quality_codes)

    # 5. Normalize data types
    df = normalize_observation_types(df)

    # 6. Merge with coordinates
    merged_df = merge_observations_with_coordinates(df, coords_df)

    # 7. Add QA flags
    merged_df = add_preprocessing_flags(merged_df)

    # 8. Prepare spatial validation input
    spatial_input_df = prepare_spatial_validation_input(merged_df)

    # 9. Build summary
    summary_df = build_preprocessing_summary(
        df_raw=obs_df,
        df_merged=merged_df,
    )

    return merged_df, spatial_input_df, summary_df