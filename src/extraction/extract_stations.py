from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from db_client import fetch_station_data


# ============================================================
# STEP 0. LOAD TAG LIST
# ============================================================

def load_tags(filepath: str) -> list[str]:
    """
    Load station tags from text file.

    Empty lines and commented lines are ignored.

    Parameters
    ----------
    filepath : str
        Path to tag list file.

    Returns
    -------
    list[str]
        List of station tags.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        tags = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]
    return tags


# ============================================================
# STEP 1. RESOLVE EXTRACTION DATE RANGE
# ============================================================

def resolve_daily_date_range(reference_date: datetime | None = None) -> tuple[str, str]:
    """
    Resolve default extraction window as previous full day.

    Parameters
    ----------
    reference_date : datetime | None
        Optional reference datetime.

    Returns
    -------
    tuple[str, str]
        Start and end date in YYYYMMDD format.
    """
    if reference_date is None:
        reference_date = datetime.now()

    target_day = reference_date - timedelta(days=1)

    start_date = target_day.strftime("%Y%m%d")
    end_date = target_day.strftime("%Y%m%d")

    return start_date, end_date


# ============================================================
# STEP 2. EXTRACT DATA FOR MULTIPLE TAGS
# ============================================================

def fetch_multiple_stations(
    tags: list[str],
    start_date: str,
    end_date: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extract data for multiple station tags.

    Parameters
    ----------
    tags : list[str]
        List of station tags.
    start_date : str
        Start date in YYYYMMDD format.
    end_date : str
        End date in YYYYMMDD format.

    Returns
    -------
    all_data_df : DataFrame
        Combined DataFrame with all station data.
    extraction_summary_df : DataFrame
        Per-tag extraction summary.
    """
    all_data = []
    summary_rows = []

    for tag in tags:
        try:
            df = fetch_station_data(
                start_date=start_date,
                end_date=end_date,
                tag=tag,
            )

            n_records = len(df)
            has_data = not df.empty

            summary_rows.append(
                {
                    "tag": tag,
                    "status": "success",
                    "n_records": n_records,
                    "error_message": None,
                }
            )

            if has_data:
                all_data.append(df)

        except Exception as exc:
            summary_rows.append(
                {
                    "tag": tag,
                    "status": "error",
                    "n_records": 0,
                    "error_message": str(exc),
                }
            )

    if all_data:
        all_data_df = pd.concat(all_data, ignore_index=True)
    else:
        all_data_df = pd.DataFrame()

    extraction_summary_df = pd.DataFrame(summary_rows)

    return all_data_df, extraction_summary_df


# ============================================================
# STEP 3. BUILD EXTRACTION SUMMARY
# ============================================================

def build_global_extraction_summary(
    all_data_df: pd.DataFrame,
    extraction_summary_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build global extraction summary.

    Parameters
    ----------
    all_data_df : DataFrame
    extraction_summary_df : DataFrame

    Returns
    -------
    DataFrame
    """
    summary = {
        "n_tags_requested": int(len(extraction_summary_df)),
        "n_tags_success": int((extraction_summary_df["status"] == "success").sum()),
        "n_tags_error": int((extraction_summary_df["status"] == "error").sum()),
        "n_total_records": int(len(all_data_df)),
    }

    return pd.DataFrame([summary])


# ============================================================
# STEP 4. EXPORT EXTRACTION OUTPUTS
# ============================================================

def export_extraction_outputs(
    all_data_df: pd.DataFrame,
    extraction_summary_df: pd.DataFrame,
    global_summary_df: pd.DataFrame,
    output_dir: str,
) -> None:
    """
    Export extraction outputs to CSV files.

    Parameters
    ----------
    all_data_df : DataFrame
    extraction_summary_df : DataFrame
    global_summary_df : DataFrame
    output_dir : str
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    all_data_df.to_csv(output_path / "station_observations.csv", index=False)
    extraction_summary_df.to_csv(output_path / "extraction_summary.csv", index=False)
    global_summary_df.to_csv(output_path / "extraction_global_summary.csv", index=False)


# ============================================================
# STEP 5. FULL EXTRACTION PIPELINE
# ============================================================

def run_extraction_pipeline(
    tags_filepath: str,
    output_dir: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Run full multi-station extraction pipeline.

    Steps:
    1. Load tags
    2. Resolve date range if not provided
    3. Fetch data for all tags
    4. Build summaries
    5. Optionally export outputs

    Returns
    -------
    all_data_df : DataFrame
    extraction_summary_df : DataFrame
    global_summary_df : DataFrame
    """
    # 1. Load tag list
    tags = load_tags(tags_filepath)

    # 2. Resolve default date range
    if start_date is None or end_date is None:
        start_date, end_date = resolve_daily_date_range()

    # 3. Fetch data for multiple stations
    all_data_df, extraction_summary_df = fetch_multiple_stations(
        tags=tags,
        start_date=start_date,
        end_date=end_date,
    )

    # 4. Build global summary
    global_summary_df = build_global_extraction_summary(
        all_data_df=all_data_df,
        extraction_summary_df=extraction_summary_df,
    )

    # 5. Export outputs if requested
    if output_dir is not None:
        export_extraction_outputs(
            all_data_df=all_data_df,
            extraction_summary_df=extraction_summary_df,
            global_summary_df=global_summary_df,
            output_dir=output_dir,
        )

    return all_data_df, extraction_summary_df, global_summary_df