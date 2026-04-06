import pandas as pd
from src.validation.spatial_validation import run_spatial_validation
import pytest


def test_spatial_validation_detects_outlier():
    df = pd.DataFrame({
        "Estacion": ["A", "B", "C", "D", "E"],
        "Fecha": pd.to_datetime(["2026-01-01"] * 5),
        "Valor": [10, 10, 10, 10, 30],  # E es outlier
        "X": [0, 1, 0, 1, 0.5],
        "Y": [0, 0, 1, 1, 0.5],
    })

    config = {
        "min_neighbors": 3,
        "n_neighbors": 4,
        "abs_residual_threshold": 5.0,
    }

    issues_df, validated_df = run_spatial_validation(
        df=df,
        variable="temp",
        config=config,
    )

    assert len(issues_df) >= 1
    assert "spatial_residual_exceeded" in issues_df["issue_type"].values
    assert "E" in issues_df["station_name"].values
    
def test_spatial_validation_no_anomalies():
    df = pd.DataFrame({
        "Estacion": ["A", "B", "C", "D"],
        "Fecha": pd.to_datetime(["2026-01-01"] * 4),
        "Valor": [10, 11, 10, 11],
        "X": [0, 1, 0, 1],
        "Y": [0, 0, 1, 1],
    })

    config = {
        "min_neighbors": 2,
        "n_neighbors": 3,
        "abs_residual_threshold": 10.0,
    }

    issues_df, validated_df = run_spatial_validation(
        df=df,
        variable="temp",
        config=config,
    )

    assert issues_df.empty
    assert len(validated_df) == 4
    
def test_spatial_validation_insufficient_neighbors():
    df = pd.DataFrame({
        "Estacion": ["A", "B"],
        "Fecha": pd.to_datetime(["2026-01-01"] * 2),
        "Valor": [10, 20],
        "X": [0, 10],
        "Y": [0, 10],
    })

    config = {
        "min_neighbors": 3,  # imposible con 2 puntos
        "n_neighbors": 2,
    }

    issues_df, validated_df = run_spatial_validation(
        df=df,
        variable="temp",
        config=config,
    )

    assert len(issues_df) == 2
    assert all(issues_df["issue_type"] == "insufficient_spatial_context")
    assert validated_df.empty


def test_missing_required_columns():
    df = pd.DataFrame({
        "Estacion": ["A"],
        "Valor": [10],
        # falta X, Y, Fecha
    })

    config = {}

    with pytest.raises(ValueError):
        run_spatial_validation(
            df=df,
            variable="temp",
            config=config,
        )