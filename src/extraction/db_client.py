from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import pandas as pd
import pyodbc


# ============================================================
# STEP 0. DEFINE QUERY TEMPLATE
# ============================================================

def build_cons_dia_query() -> str:
    """
    Build SQL query for station data extraction from CONS_DIA table.

    Returns
    -------
    str
        Parameterized SQL query.
    """
    query = """
        SELECT
            s.LS_TAG_TXT AS [Nombre señal],
            s.LS_DESCRIPCION AS [Descripción],
            t.CC_FECHA AS [Fecha],
            t.CC_VALOR AS [Valor],
            t.CC_CALIDAD AS [Calidad],
            s.LS_UNID_ING AS [Unidades]
        FROM [SAIHMS_HIST].[dbo].[CONS_DIA] t
        LEFT OUTER JOIN [SAIHMS_HIST].[dbo].[LISTA_SENALES] s
            ON t.CC_IDSENAL = s.LS_TAG
        WHERE t.CC_FECHA BETWEEN ? AND ?
          AND s.LS_TAG_TXT = ?
        ORDER BY t.CC_FECHA DESC
    """
    return query


# ============================================================
# STEP 1. LOAD DATABASE CONFIGURATION
# ============================================================

def load_db_config() -> dict:
    """
    Load database connection settings from environment variables.

    Expected environment variables
    ------------------------------
    DB_DRIVER
    DB_SERVER
    DB_DATABASE
    DB_USER
    DB_PASSWORD

    Returns
    -------
    dict
        Database configuration dictionary.
    """
    config = {
        "driver": os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server"),
        "server": os.getenv("DB_SERVER"),
        "database": os.getenv("DB_DATABASE"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }

    missing = [key for key, value in config.items() if value is None]
    if missing:
        raise ValueError(
            f"Missing database environment variables for: {missing}"
        )

    return config


# ============================================================
# STEP 2. BUILD CONNECTION STRING
# ============================================================

def build_connection_string(config: dict) -> str:
    """
    Build pyodbc connection string.

    Parameters
    ----------
    config : dict
        Database configuration dictionary.

    Returns
    -------
    str
        ODBC connection string.
    """
    conn_str = (
        f"DRIVER={{{config['driver']}}};"
        f"SERVER={config['server']};"
        f"DATABASE={config['database']};"
        f"UID={config['user']};"
        f"PWD={config['password']};"
        "ApplicationIntent=ReadOnly;"
    )
    return conn_str


# ============================================================
# STEP 3. CREATE DATABASE CONNECTION
# ============================================================

def create_connection(
    connection_string: str,
    connect_timeout: int = 5,
) -> pyodbc.Connection:
    """
    Create database connection.

    Parameters
    ----------
    connection_string : str
        ODBC connection string.
    connect_timeout : int
        Connection timeout in seconds.

    Returns
    -------
    pyodbc.Connection
    """
    return pyodbc.connect(connection_string, timeout=connect_timeout)


# ============================================================
# STEP 4. VALIDATE DATE RANGE
# ============================================================

def validate_date_range(
    start_date: str,
    end_date: str,
    fmt: str = "%Y%m%d",
    max_days: int = 93,
) -> tuple[datetime, datetime]:
    """
    Validate query date range.

    Parameters
    ----------
    start_date : str
        Start date in YYYYMMDD format.
    end_date : str
        End date in YYYYMMDD format.
    fmt : str
        Date format.
    max_days : int
        Maximum allowed range in days.

    Returns
    -------
    tuple[datetime, datetime]
        Parsed start and end datetimes.
    """
    try:
        dt0 = datetime.strptime(start_date, fmt)
        dt1 = datetime.strptime(end_date, fmt)
    except ValueError as exc:
        raise ValueError(
            "Invalid date format. Expected 'YYYYMMDD'."
        ) from exc

    delta_days = (dt1 - dt0).days

    if delta_days < 0:
        raise ValueError("Start date cannot be later than end date.")

    if delta_days > max_days:
        raise ValueError(
            f"Date range cannot exceed {max_days} days "
            f"(requested: {delta_days})."
        )

    return dt0, dt1


# ============================================================
# STEP 5. EXECUTE QUERY
# ============================================================

def execute_query(
    query: str,
    start_date: str,
    end_date: str,
    tag: str,
    query_timeout: int = 30,
) -> pd.DataFrame:
    """
    Execute parameterized query and return results as DataFrame.

    Parameters
    ----------
    query : str
        SQL query.
    start_date : str
        Start date in YYYYMMDD format.
    end_date : str
        End date in YYYYMMDD format.
    tag : str
        Station tag / signal identifier.
    query_timeout : int
        SQL execution timeout in seconds.

    Returns
    -------
    DataFrame
        Query result as pandas DataFrame.
    """
    config = load_db_config()
    connection_string = build_connection_string(config)

    con = create_connection(connection_string)
    try:
        con.timeout = query_timeout
        cursor = con.cursor()
        cursor.execute(query, start_date, end_date, tag)

        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

        df = pd.DataFrame.from_records(rows, columns=columns)
        return df

    finally:
        con.close()


# ============================================================
# STEP 6. FETCH DATA FOR A SINGLE STATION
# ============================================================

def fetch_station_data(
    start_date: str,
    end_date: str,
    tag: str,
) -> pd.DataFrame:
    """
    Fetch data for a single station tag.

    Parameters
    ----------
    start_date : str
        Start date in YYYYMMDD format.
    end_date : str
        End date in YYYYMMDD format.
    tag : str
        Station tag / signal identifier.

    Returns
    -------
    DataFrame
        Station data.
    """
    validate_date_range(start_date, end_date)

    query = build_cons_dia_query()
    df = execute_query(
        query=query,
        start_date=start_date,
        end_date=end_date,
        tag=tag,
    )

    return df