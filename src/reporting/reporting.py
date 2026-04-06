from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# STEP 0. Issue enrichment utilities
# ============================================================

def enrich_spatial_issues(
    issues_df: pd.DataFrame,
    issue_rules: dict[str, dict[str, str]],
) -> pd.DataFrame:
    """
    Enrich spatial issues with severity and recommended action.

    Parameters
    ----------
    issues_df : DataFrame
        Raw spatial issues dataframe.
    issue_rules : dict
        Mapping of issue_type to severity and recommended action.

    Returns
    -------
    DataFrame
        Enriched issues dataframe.
    """
    if issues_df.empty:
        enriched_df = issues_df.copy()
        enriched_df["severity"] = pd.Series(dtype="object")
        enriched_df["recommended_action"] = pd.Series(dtype="object")
        return enriched_df

    enriched_df = issues_df.copy()

    enriched_df["severity"] = enriched_df["issue_type"].map(
        lambda x: issue_rules.get(x, {}).get("severity", "UNKNOWN")
    )
    enriched_df["recommended_action"] = enriched_df["issue_type"].map(
        lambda x: issue_rules.get(x, {}).get("recommended_action", "review_required")
    )

    return enriched_df


# ============================================================
# STEP 1. Execution-level reporting
# ============================================================

def build_execution_summary(
    validated_df: pd.DataFrame,
    issues_df: pd.DataFrame,
    preprocessing_summary_df: pd.DataFrame | None = None,
    extraction_summary_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Build one-row execution summary for the spatial validation pipeline.

    Parameters
    ----------
    validated_df : DataFrame
        Full validation results dataframe.
    issues_df : DataFrame
        Enriched issues dataframe.
    preprocessing_summary_df : DataFrame | None
        Optional preprocessing summary dataframe.
    extraction_summary_df : DataFrame | None
        Optional extraction summary dataframe.

    Returns
    -------
    DataFrame
        Execution summary dataframe.
    """
    n_validated_records = len(validated_df)
    stations_processed = (
        validated_df["Estacion"].nunique()
        if "Estacion" in validated_df.columns and not validated_df.empty
        else 0
    )

    spatial_anomaly_count = (
        int(validated_df["is_spatial_anomaly"].sum())
        if "is_spatial_anomaly" in validated_df.columns and not validated_df.empty
        else 0
    )

    insufficient_context_count = (
        int((issues_df["issue_type"] == "insufficient_spatial_context").sum())
        if not issues_df.empty and "issue_type" in issues_df.columns
        else 0
    )

    high_count = int((issues_df["severity"] == "HIGH").sum()) if not issues_df.empty else 0
    medium_count = int((issues_df["severity"] == "MEDIUM").sum()) if not issues_df.empty else 0
    low_count = int((issues_df["severity"] == "LOW").sum()) if not issues_df.empty else 0

    mean_abs_residual = (
        float(validated_df["abs_residual"].mean())
        if "abs_residual" in validated_df.columns and not validated_df.empty
        else np.nan
    )

    max_abs_residual = (
        float(validated_df["abs_residual"].max())
        if "abs_residual" in validated_df.columns and not validated_df.empty
        else np.nan
    )

    n_raw_records = np.nan
    n_ready_for_spatial_validation = np.nan
    if preprocessing_summary_df is not None and not preprocessing_summary_df.empty:
        row = preprocessing_summary_df.iloc[0]
        n_raw_records = row.get("n_raw_records", np.nan)
        n_ready_for_spatial_validation = row.get("n_ready_for_spatial_validation", np.nan)

    n_tags_requested = np.nan
    n_tags_error = np.nan
    if extraction_summary_df is not None and not extraction_summary_df.empty:
        row = extraction_summary_df.iloc[0]
        n_tags_requested = row.get("n_tags_requested", np.nan)
        n_tags_error = row.get("n_tags_error", np.nan)

    if high_count > 0:
        status = "CRITICAL"
    elif medium_count > 0 or low_count > 0:
        status = "WARNING"
    else:
        status = "OK"

    summary = {
        "n_tags_requested": n_tags_requested,
        "n_tags_error": n_tags_error,
        "n_raw_records": n_raw_records,
        "n_ready_for_spatial_validation": n_ready_for_spatial_validation,
        "stations_processed": stations_processed,
        "n_validated_records": n_validated_records,
        "spatial_anomaly_count": spatial_anomaly_count,
        "insufficient_context_count": insufficient_context_count,
        "total_issues": len(issues_df),
        "high_severity_count": high_count,
        "medium_severity_count": medium_count,
        "low_severity_count": low_count,
        "mean_abs_residual": mean_abs_residual,
        "max_abs_residual": max_abs_residual,
        "status": status,
    }

    return pd.DataFrame([summary])


# ============================================================
# STEP 2. Station-level reporting
# ============================================================

def build_station_overview(
    validated_df: pd.DataFrame,
    issues_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build station-level overview combining validation results and issues.

    Parameters
    ----------
    validated_df : DataFrame
        Full validation results dataframe.
    issues_df : DataFrame
        Enriched issues dataframe.

    Returns
    -------
    DataFrame
        Station-level overview dataframe.
    """
    if validated_df.empty:
        return pd.DataFrame(
            columns=[
                "station_name",
                "n_records",
                "n_spatial_anomalies",
                "mean_abs_residual",
                "max_abs_residual",
                "high_severity_count",
                "medium_severity_count",
                "low_severity_count",
                "status",
            ]
        )

    validation_grouped = (
        validated_df.groupby("Estacion", dropna=False)
        .agg(
            n_records=("Estacion", "size"),
            n_spatial_anomalies=("is_spatial_anomaly", "sum"),
            mean_abs_residual=("abs_residual", "mean"),
            max_abs_residual=("abs_residual", "max"),
        )
        .reset_index()
        .rename(columns={"Estacion": "station_name"})
    )

    if issues_df.empty:
        validation_grouped["high_severity_count"] = 0
        validation_grouped["medium_severity_count"] = 0
        validation_grouped["low_severity_count"] = 0
    else:
        issue_grouped = (
            issues_df.groupby("station_name", dropna=False)
            .agg(
                high_severity_count=("severity", lambda s: int((s == "HIGH").sum())),
                medium_severity_count=("severity", lambda s: int((s == "MEDIUM").sum())),
                low_severity_count=("severity", lambda s: int((s == "LOW").sum())),
            )
            .reset_index()
        )

        validation_grouped = validation_grouped.merge(
            issue_grouped,
            on="station_name",
            how="left",
        )

        validation_grouped[
            ["high_severity_count", "medium_severity_count", "low_severity_count"]
        ] = validation_grouped[
            ["high_severity_count", "medium_severity_count", "low_severity_count"]
        ].fillna(0).astype(int)

    def assign_status(row: pd.Series) -> str:
        if row["high_severity_count"] > 0:
            return "CRITICAL"
        if row["medium_severity_count"] > 0 or row["low_severity_count"] > 0:
            return "WARNING"
        return "OK"

    validation_grouped["status"] = validation_grouped.apply(assign_status, axis=1)

    return validation_grouped.sort_values(
        by=[
            "high_severity_count",
            "medium_severity_count",
            "n_spatial_anomalies",
            "max_abs_residual",
        ],
        ascending=False,
    ).reset_index(drop=True)


# ============================================================
# STEP 3. Human-readable report generation
# ============================================================

def generate_execution_report_text(
    execution_id: str,
    reference_date: pd.Timestamp,
    execution_summary_df: pd.DataFrame,
    station_overview_df: pd.DataFrame,
) -> str:
    """
    Generate human-readable execution report text.

    Parameters
    ----------
    execution_id : str
    reference_date : Timestamp
    execution_summary_df : DataFrame
    station_overview_df : DataFrame

    Returns
    -------
    str
        Plain text report.
    """
    summary = execution_summary_df.iloc[0]

    lines = []
    lines.append("SPATIAL VALIDATION EXECUTION REPORT")
    lines.append(f"Execution ID: {execution_id}")
    lines.append(f"Reference date: {pd.to_datetime(reference_date).date()}")
    lines.append("")

    lines.append("GLOBAL SUMMARY")
    if pd.notna(summary["n_tags_requested"]):
        lines.append(f"- Tags requested: {summary['n_tags_requested']}")
        lines.append(f"- Tags with extraction errors: {summary['n_tags_error']}")
    else:
        lines.append("- Data source: local file input (database extraction skipped)")

    lines.append(f"- Raw records: {summary['n_raw_records']}")
    lines.append(
        f"- Records ready for spatial validation: "
        f"{summary['n_ready_for_spatial_validation']}"
    )
    lines.append(f"- Stations processed: {summary['stations_processed']}")
    lines.append(f"- Validated records: {summary['n_validated_records']}")
    lines.append(f"- Spatial anomalies detected: {summary['spatial_anomaly_count']}")
    lines.append(f"- Insufficient spatial context issues: {summary['insufficient_context_count']}")
    lines.append(f"- Total issues: {summary['total_issues']}")
    lines.append(f"- High severity issues: {summary['high_severity_count']}")
    lines.append(f"- Medium severity issues: {summary['medium_severity_count']}")
    lines.append(f"- Low severity issues: {summary['low_severity_count']}")
    lines.append(f"- Mean absolute residual: {summary['mean_abs_residual']}")
    lines.append(f"- Maximum absolute residual: {summary['max_abs_residual']}")
    lines.append(f"- Overall status: {summary['status']}")
    lines.append("")

    lines.append("STATION OVERVIEW")
    if station_overview_df.empty:
        lines.append("- No stations available for reporting.")
    else:
        for _, row in station_overview_df.iterrows():
            lines.append(
                f"- {row['station_name']}: "
                f"status={row['status']}, "
                f"records={row['n_records']}, "
                f"anomalies={row['n_spatial_anomalies']}, "
                f"mean_abs_residual={row['mean_abs_residual']:.2f}, "
                f"max_abs_residual={row['max_abs_residual']:.2f}, "
                f"HIGH={row['high_severity_count']}, "
                f"MEDIUM={row['medium_severity_count']}, "
                f"LOW={row['low_severity_count']}"
            )

    return "\n".join(lines)


# ============================================================
# STEP 4. Persist reporting outputs
# ============================================================

def save_text_report(report_text: str, output_path: Path) -> None:
    """
    Save plain text report to disk.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")


def save_reporting_outputs(
    issues_df: pd.DataFrame,
    execution_summary_df: pd.DataFrame,
    station_overview_df: pd.DataFrame,
    report_text: str,
    output_dir: str | Path,
) -> None:
    """
    Save all reporting outputs to disk.

    Parameters
    ----------
    issues_df : DataFrame
    execution_summary_df : DataFrame
    station_overview_df : DataFrame
    report_text : str
    output_dir : str | Path
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    issues_df.to_csv(output_dir / "spatial_issues_enriched.csv", index=False)
    execution_summary_df.to_csv(output_dir / "execution_summary.csv", index=False)
    station_overview_df.to_csv(output_dir / "station_overview.csv", index=False)
    save_text_report(report_text, output_dir / "execution_report.txt")