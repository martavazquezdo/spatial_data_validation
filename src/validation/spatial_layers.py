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
    required_cols = ["X", "Y", 'Valor']

    for col in required_cols:
        if col not in validated_df.columns:
            raise ValueError(f"Missing required column in validated_df: {col}")

    
    issues_df = issues_df.merge(
        validated_df[["Estacion", "X", "Y"]],
        left_on="station_name",
        right_on="Estacion",
        how="left"
    )
    
    if not issues_df.empty:
        for col in ["X", "Y"]:
            if col not in issues_df.columns:
                raise ValueError(f"Missing required column in issues_df: {col}")

    # ==========================================================
    # 2. CREATE STATIONS LAYER
    # ==========================================================
    logging.info("Creating stations GeoJSON.")

    stations_gdf = gpd.GeoDataFrame(
        validated_df.copy(),
        geometry=gpd.points_from_xy(
            validated_df["X"],
            validated_df["Y"],
        ),
        crs="EPSG:25829",
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
            issues_df["X"],
            issues_df["Y"],
        ),
        crs="EPSG:25829",
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

    df = validated_df.dropna(subset=["X", "Y", "Valor"]).copy()
    df = df.drop_duplicates(subset=["X", "Y"])

    if len(df) < 3:
        logging.warning("Not enough unique points for interpolation. Skipping raster.")
        return

    if df["X"].nunique() < 2 or df["Y"].nunique() < 2:
        raise ValueError(
            "Invalid spatial coordinates: insufficient variation in X or Y."
        )

    grid_x, grid_y = np.meshgrid(
        np.linspace(df["X"].min(), df["X"].max(), resolution),
        np.linspace(df["Y"].max(), df["Y"].min(), resolution),
    )

    points = df[["X", "Y"]].to_numpy()
    values = df["Valor"].to_numpy()

    try:
        grid_z = griddata(
            points,
            values,
            (grid_x, grid_y),
            method="linear",
        )
    except Exception as e:
        logging.warning(f"Linear interpolation failed ({e}). Falling back to nearest.")
        grid_z = griddata(
            points,
            values,
            (grid_x, grid_y),
            method="nearest",
        )

    if np.isnan(grid_z).all():
        logging.warning("Interpolation failed (all NaNs). Skipping raster.")
        return

    nodata_value = -9999.0
    grid_z_out = np.where(np.isnan(grid_z), nodata_value, grid_z).astype("float32")

    transform = from_origin(
        west=df["X"].min(),
        north=df["Y"].max(),
        xsize=(df["X"].max() - df["X"].min()) / resolution,
        ysize=(df["Y"].max() - df["Y"].min()) / resolution,
    )

    raster_path = output_dir / "interpolated_surface.tif"

    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        height=grid_z_out.shape[0],
        width=grid_z_out.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:25829",
        transform=transform,
        nodata=nodata_value,
    ) as dst:
        dst.write(grid_z_out, 1)

    # ==========================================================
    # 5. SAVE RASTER
    # ==========================================================
    transform = from_origin(
        west=df["X"].min(),
        north=df["Y"].max(),
        xsize=(df["X"].max() - df["X"].min()) / resolution,
        ysize=(df["Y"].max() - df["Y"].min()) / resolution,
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
        crs="EPSG:25829",
        transform=transform,
    ) as dst:
        dst.write(grid_z, 1)

    logging.info(f"Raster saved to: {raster_path}")

    logging.info("Spatial GIS outputs generated successfully.")