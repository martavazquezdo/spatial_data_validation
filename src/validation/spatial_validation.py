from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ["Estacion", "Fecha", "Valor", "X", "Y"]


def validate_required_columns(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas para validación espacial: {missing}")


def prepare_validation_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df_valid = df.copy()

    df_valid = df_valid.dropna(subset=["Valor", "X", "Y"]).reset_index(drop=True)

    if df_valid.empty:
        raise ValueError("No hay datos válidos para la validación espacial.")

    return df_valid


def compute_distances(x0: float, y0: float, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.sqrt((x - x0) ** 2 + (y - y0) ** 2)


def get_neighbor_subset(
    df: pd.DataFrame,
    row_idx: int,
    n_neighbors: int,
    max_distance: float | None = None,
) -> pd.DataFrame:
    row = df.iloc[row_idx]

    distances = compute_distances(
        row["X"],
        row["Y"],
        df["X"].to_numpy(),
        df["Y"].to_numpy(),
    )

    neighbors = df.copy()
    neighbors["distance"] = distances
    neighbors = neighbors[neighbors.index != row_idx]

    if max_distance is not None:
        neighbors = neighbors[neighbors["distance"] <= max_distance]

    neighbors = neighbors.sort_values("distance").head(n_neighbors)

    return neighbors


def estimate_expected_value(
    neighbors_df: pd.DataFrame,
    method: str = "median",
    epsilon: float = 1e-6,
) -> float:
    if neighbors_df.empty:
        return np.nan

    values = neighbors_df["Valor"].to_numpy(dtype=float)

    if method == "median":
        return float(np.median(values))

    if method == "mean":
        return float(np.mean(values))

    if method == "idw_neighbors":
        distances = neighbors_df["distance"].to_numpy(dtype=float)
        weights = 1.0 / (distances + epsilon)
        return float(np.sum(weights * values) / np.sum(weights))

    raise ValueError(f"Método de estimación no soportado: {method}")


def classify_severity(abs_residual: float, severity_thresholds: dict) -> str:
    high = severity_thresholds.get("high", np.inf)
    medium = severity_thresholds.get("medium", np.inf)

    if abs_residual >= high:
        return "high"
    if abs_residual >= medium:
        return "medium"
    return "low"


def build_spatial_issue(
    row: pd.Series,
    issue_type: str,
    variable: str,
    observed_value: float | None = None,
    expected_value: float | None = None,
    residual: float | None = None,
    abs_residual: float | None = None,
    n_neighbors_used: int | None = None,
    max_neighbor_distance: float | None = None,
    severity: str | None = None,
    details: str | None = None,
) -> dict:
    return {
        "station_name": row.get("Estacion"),
        "timestamp": row.get("Fecha"),
        "check_dimension": "spatial",
        "issue_type": issue_type,
        "variable": variable,
        "observed_value": observed_value,
        "expected_value": expected_value,
        "residual": residual,
        "abs_residual": abs_residual,
        "n_neighbors_used": n_neighbors_used,
        "max_neighbor_distance": max_neighbor_distance,
        "severity": severity,
        "details": details,
    }


def run_spatial_validation(
    df: pd.DataFrame,
    variable: str,
    config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    validate_required_columns(df)
    df_valid = prepare_validation_dataframe(df)

    min_neighbors = config.get("min_neighbors", 3)
    n_neighbors = config.get("n_neighbors", 5)
    max_distance = config.get("max_distance")
    expected_method = config.get("expected_value_method", "median")
    abs_threshold = config.get("abs_residual_threshold", 10.0)
    severity_thresholds = config.get(
        "severity_thresholds",
        {"medium": 10.0, "high": 20.0},
    )

    issues = []
    validation_rows = []

    for idx in range(len(df_valid)):
        row = df_valid.iloc[idx]
        neighbors = get_neighbor_subset(
            df_valid,
            row_idx=idx,
            n_neighbors=n_neighbors,
            max_distance=max_distance,
        )

        n_used = len(neighbors)

        if n_used < min_neighbors:
            issues.append(
                build_spatial_issue(
                    row=row,
                    issue_type="insufficient_spatial_context",
                    variable=variable,
                    observed_value=row["Valor"],
                    n_neighbors_used=n_used,
                    max_neighbor_distance=neighbors["distance"].max() if n_used > 0 else np.nan,
                    severity="low",
                    details=f"Solo se encontraron {n_used} vecinas válidas; mínimo requerido: {min_neighbors}",
                )
            )
            continue

        expected_value = estimate_expected_value(
            neighbors_df=neighbors,
            method=expected_method,
        )

        residual = float(row["Valor"] - expected_value)
        abs_residual = abs(residual)
        severity = classify_severity(abs_residual, severity_thresholds)

        validation_rows.append(
            {
                "Estacion": row["Estacion"],
                "Fecha": row["Fecha"],
                "Valor": row["Valor"],
                "X": row["X"],
                "Y": row["Y"],
                "expected_value": expected_value,
                "residual": residual,
                "abs_residual": abs_residual,
                "n_neighbors_used": n_used,
                "max_neighbor_distance": neighbors["distance"].max(),
                "is_spatial_anomaly": abs_residual > abs_threshold,
                "severity": severity,
            }
        )

        if abs_residual > abs_threshold:
            issues.append(
                build_spatial_issue(
                    row=row,
                    issue_type="spatial_residual_exceeded",
                    variable=variable,
                    observed_value=row["Valor"],
                    expected_value=expected_value,
                    residual=residual,
                    abs_residual=abs_residual,
                    n_neighbors_used=n_used,
                    max_neighbor_distance=neighbors["distance"].max(),
                    severity=severity,
                    details=(
                        f"Residual espacial absoluto {abs_residual:.2f} "
                        f"superior al umbral {abs_threshold:.2f}"
                    ),
                )
            )

    issues_df = pd.DataFrame(issues)
    validated_df = pd.DataFrame(validation_rows)

    return issues_df, validated_df