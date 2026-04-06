from __future__ import annotations

import logging
import uuid
from pathlib import Path

import pandas as pd


# ============================================================
# STEP 0. LOGGING AND EXECUTION CONTEXT
# ============================================================

def generate_execution_id() -> str:
    """
    Generate a short unique execution ID for the current pipeline run.
    """
    return str(uuid.uuid4())[:8]


def setup_logger(
    log_dir: Path,
    execution_id: str,
    run_datetime: pd.Timestamp,
    log_prefix: str = "spatial_pipeline",
) -> Path:
    """
    Configure logging to both console and file.

    Parameters
    ----------
    log_dir : Path
        Directory where log file will be stored.
    execution_id : str
        Short execution identifier.
    run_datetime : pd.Timestamp
        Execution timestamp.
    log_prefix : str
        Prefix used in log filename.

    Returns
    -------
    Path
        Path to generated log file.
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = pd.to_datetime(run_datetime).strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{log_prefix}_{timestamp_str}_{execution_id}.log"

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return log_file