import logging
from pathlib import Path

import numpy as np
import geopandas as gpd
from scipy.interpolate import griddata
import rasterio
from rasterio.transform import from_origin


def generate_spatial_outputs(
    validated_df,
    issues_df,
    variable_name: str,
    output_dir: Path,
    resolution: int = 100,
):
    """
    Generate GIS-ready outputs:
    - interpolated raster (GeoTIFF)
    - stations layer (GeoJSON)
    - spatial issues layer (GeoJSON)
    """

    logging.info("Generating spatial GIS outputs.")

    output_dir.mkdir(parents=True, exist_ok=True)

    # ==========================================================
    # 1. CHECK REQUIRED COLUMNS
    # ==========================================================
    required_cols = ["lat", "lon", variable_name]

    for col in required_cols:
        if col not in validated_df.columns:
            raise ValueError(f"Missing required column in validated_df: {col}")

    if not issues_df.empty:
        for col in ["lat", "lon"]:
            if col not in issues_df.columns:
                raise ValueError(f"Missing required column in issues_df: {col}")

    # ==========================================================
    # 2. CREATE STATIONS LAYER
    # ==========================================================
    logging.info("Creating stations GeoJSON.")

    stations_gdf = gpd.GeoDataFrame(
        validated_df.copy(),
        geometry=gpd.points_from_xy(
            validated_df["lon"],
            validated_df["lat"],
        ),
        crs="EPSG:4326",
    )

    stations_path = output_dir / "stations.geojson"
    stations_gdf.to_file(stations_path, driver="GeoJSON")

    logging.info(f"Stations layer saved to: {stations_path}")

    # ==========================================================
    # 3. CREATE ISSUES LAYER
    # ==========================================================
    if not issues_df.empty:
        logging.info("Creating spatial issues GeoJSON.")

        issues_gdf = gpd.GeoDataFrame(
            issues_df.copy(),
            geometry=gpd.points_from_xy(
                issues_df["lon"],
                issues_df["lat"],
            ),
            crs="EPSG:4326",
        )

        issues_path = output_dir / "spatial_issues.geojson"
        issues_gdf.to_file(issues_path, driver="GeoJSON")

        logging.info(f"Issues layer saved to: {issues_path}")
    else:
        logging.info("No spatial issues detected. Skipping issues layer.")

    # ==========================================================
    # 4. GENERATE INTERPOLATED RASTER
    # ==========================================================
    logging.info("Generating interpolated raster.")

    df = validated_df.dropna(subset=["lon", "lat", variable_name])

    if len(df) < 3:
        logging.warning("Not enough points for interpolation. Skipping raster.")
        return

    # Grid definition
    grid_x, grid_y = np.meshgrid(
        np.linspace(df["lon"].min(), df["lon"].max(), resolution),
        np.linspace(df["lat"].min(), df["lat"].max(), resolution),
    )

    # Interpolation
    grid_z = griddata(
        (df["lon"], df["lat"]),
        df[variable_name],
        (grid_x, grid_y),
        method="linear",
    )

    # Fill NaNs (optional but recommended)
    if np.isnan(grid_z).all():
        logging.warning("Interpolation failed (all NaNs). Skipping raster.")
        return

    grid_z = np.nan_to_num(grid_z, nan=np.nanmean(grid_z))

    # ==========================================================
    # 5. SAVE RASTER
    # ==========================================================
    transform = from_origin(
        west=df["lon"].min(),
        north=df["lat"].max(),
        xsize=(df["lon"].max() - df["lon"].min()) / resolution,
        ysize=(df["lat"].max() - df["lat"].min()) / resolution,
    )

    raster_path = output_dir / "interpolated_surface.tif"

    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        height=grid_z.shape[0],
        width=grid_z.shape[1],
        count=1,
        dtype=grid_z.dtype,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(grid_z, 1)

    logging.info(f"Raster saved to: {raster_path}")

    logging.info("Spatial GIS outputs generated successfully.")