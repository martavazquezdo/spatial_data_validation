# Spatial Data Validation Pipeline

## Overview

This project implements a modular pipeline for **data validation of meteorological observations**, with a strong focus on **spatial consistency analysis**.

It is designed to:

* detect inconsistencies in environmental data
* structure issues in a reproducible way
* provide both analytical and spatial outputs
* support visual inspection using GIS tools (e.g. QGIS)

---

## Objectives

The project prioritizes:

* clear and reproducible validation logic
* structured issue reporting
* integration with geospatial workflows
* practical usability over excessive complexity

---

## Pipeline Structure

The pipeline is organized into the following steps:

1. **Input & preprocessing**
2. **Spatial validation**
3. **Issue generation**
4. **Reporting**
5. **Optional GIS export**

---

## Spatial Validation

The core of the project is a spatial validation module that:

* estimates expected values from neighboring stations
* computes residuals (observed vs expected)
* detects anomalies based on configurable thresholds
* classifies severity levels

It supports different estimation methods:

* median (default)
* mean
* inverse distance weighting (IDW)

---

## Outputs

### 1. Structured issues

* anomalies detected
* metadata (station, timestamp, residual, severity)
* number of neighbors used

---

### 2. Reporting

* execution summary
* station-level overview
* human-readable report

---

### 3. GIS outputs (optional)

Generated files:

* `stations.geojson` → observation points
* `spatial_issues.geojson` → detected anomalies
* `interpolated_surface.tif` → interpolated spatial surface

These can be directly loaded into GIS software for visual inspection.

---

## Key Insight

During development, a **boundary-related bias** was identified:

Stations located near the edges of the spatial domain may show artificially high residuals due to reduced neighbor support.

This behavior is:

* expected from the interpolation method
* documented
* considered for future improvements

---

## How to Run

```bash
python spatial_pipelines.py
```

Make sure configuration paths and flags are correctly set.

---

## Tests

The project includes:

* unit tests for spatial validation logic
* smoke test for pipeline execution

Run tests with:

```bash
pytest
```

---

## Project Structure

```
src/
    validation/
        spatial_validation.py
        spatial_layers.py

tests/
    test_spatial_validation.py
    test_spatial_pipeline_smoke.py
```

---

## Future Improvements

* boundary-aware validation rules
* improved interpolation strategies
* spatial support metrics
* enhanced GIS visualization

---

## Author

Developed as part of a data validation portfolio focused on environmental and geospatial data.
