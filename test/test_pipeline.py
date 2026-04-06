import pandas as pd
import pytest
from pathlib import Path

import src.spatial_pipelines as spatial_pipelines


def test_spatial_pipeline_smoke(tmp_path, monkeypatch):
    # ============================================================
    # 1. Create minimal input observation CSV
    # ============================================================
    obs_df = pd.DataFrame({
        "Nombre señal": ["A", "B", "C", "D"],
        "Fecha": [
            "2026-01-01 00:00:00",
            "2026-01-01 00:00:00",
            "2026-01-01 00:00:00",
            "2026-01-01 00:00:00",
        ],
        "Valor": [10.0, 11.0, 10.5, 30.0],
        "Calidad": [1, 1, 1, 1],
    })

    obs_path = tmp_path / "obs.csv"
    obs_df.to_csv(obs_path, sep=";", index=False, encoding="latin-1", decimal=",")

    # ============================================================
    # 2. Create minimal coordinates CSV
    # ============================================================
    coords_df = pd.DataFrame({
        "Estacion": ["A", "B", "C", "D"],
        "X": [500000, 501000, 500500, 500700],
        "Y": [4700000, 4700000, 4701000, 4700500],
    })

    coords_path = tmp_path / "coords.csv"
    coords_df.to_csv(coords_path, sep=";", index=False, encoding="latin-1")

    # ============================================================
    # 3. Output and logs directories
    # ============================================================
    output_dir = tmp_path / "outputs"
    logs_dir = tmp_path / "logs"

    # ============================================================
    # 4. Patch pipeline settings
    # ============================================================
    monkeypatch.setattr(spatial_pipelines, "USE_DATABASE", False)
    monkeypatch.setattr(spatial_pipelines, "PLUVIO_TEST_FILE", str(obs_path))
    monkeypatch.setattr(spatial_pipelines, "COORDINATES_FILE", str(coords_path))
    monkeypatch.setattr(spatial_pipelines, "BASE_OUTPUT_DIR", output_dir)
    monkeypatch.setattr(spatial_pipelines, "LOGS_DIR", logs_dir)

    monkeypatch.setattr(spatial_pipelines, "ENABLE_LOGGING", False)
    monkeypatch.setattr(spatial_pipelines, "ENABLE_GIS_EXPORT", False)

    monkeypatch.setattr(
        spatial_pipelines,
        "SPATIAL_VALIDATION_CONFIG",
        {
            "min_neighbors": 2,
            "n_neighbors": 3,
            "abs_residual_threshold": 5.0,
            "expected_value_method": "median",
            "severity_thresholds": {"medium": 5.0, "high": 10.0},
        },
    )

    monkeypatch.setattr(spatial_pipelines, "VARIABLE_NAME", "temp")

    # ============================================================
    # 5. Run pipeline
    # ============================================================
    spatial_pipelines.run_spatial_pipeline()

    # ============================================================
    # 6. Assert key outputs exist
    # ============================================================
    assert output_dir.exists()
    output_files = {p.name for p in output_dir.iterdir()}

    assert any("summary" in name.lower() for name in output_files)
    assert any("report" in name.lower() for name in output_files)
    assert any("issues" in name.lower() for name in output_files)