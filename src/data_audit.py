"""
Step Zero: Data Audit Script for RainXplain
Inspects all 6 raw/processed datasets, generates schema and quality reports, and defines data strategy.
"""
import os
import pandas as pd
import numpy as np

def run_data_audit():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, "data", "raw")
    proc_dir = os.path.join(base_dir, "data", "processed")

    print("=" * 80)
    print("RAINXPLAIN - STEP ZERO: COMPREHENSIVE DATA AUDIT REPORT")
    print("=" * 80)

    dataset_configs = [
        {
            "name": "1. Indian Climate Dataset (2024-2025)",
            "file": os.path.join(raw_dir, "Indian_Climate_Dataset_2024_2025.csv"),
            "type": "csv",
            "role": "Atmospheric Features (Humidity, Cloud Cover, AQI, Temp, Pressure) across 10 Metros"
        },
        {
            "name": "2. India Weather & Rainfall Data (2015-2025)",
            "file": os.path.join(proc_dir, "india_weather_rainfall_data.parquet") if os.path.exists(os.path.join(proc_dir, "india_weather_rainfall_data.parquet")) else os.path.join(raw_dir, "india_weather_rainfall_data.xlsx"),
            "type": "parquet" if os.path.exists(os.path.join(proc_dir, "india_weather_rainfall_data.parquet")) else "excel",
            "role": "PRIMARY TRAINING DATASET (970k daily records, 406 stations, exact lat/lon, 10-year span)"
        },
        {
            "name": "3. Rainfall in India (1901-2015) Subdivision-Wise",
            "file": os.path.join(raw_dir, "rainfall in india 1901-2015.csv"),
            "type": "csv",
            "role": "Long-running Subdivision Historical Climatology (115 years, 36 IMD subdivisions)"
        },
        {
            "name": "3b. District-Wise Rainfall Normal",
            "file": os.path.join(raw_dir, "district wise rainfall normal.csv"),
            "type": "csv",
            "role": "District-level Rainfall Normals (637 districts across 35 states/UTs)"
        },
        {
            "name": "4. Sub-Division IMD 2017",
            "file": os.path.join(raw_dir, "Sub_Division_IMD_2017.csv"),
            "type": "csv",
            "role": "IMD 36 Subdivisions Rainfall Data (1901-2017, monthly/seasonal totals)"
        },
        {
            "name": "5. Rainfall Time Series",
            "file": os.path.join(raw_dir, "Rainfall_data.csv"),
            "type": "csv",
            "role": "Time Series (2000-2020) humidity, temp, precipitation"
        },
        {
            "name": "6. RainCast Earth-Space Satellite Telemetry",
            "file": os.path.join(raw_dir, "train.parquet"),
            "type": "parquet",
            "role": "Satellite-Communication Rain Attenuation Telemetry (Track C)"
        }
    ]

    report = []

    for cfg in dataset_configs:
        path = cfg["file"]
        print(f"\n[{cfg['name']}]")
        print(f"  Path: {os.path.relpath(path, base_dir)}")
        print(f"  Role: {cfg['role']}")

        if not os.path.exists(path):
            print(f"  [ERROR] File missing: {path}")
            continue

        if cfg["type"] == "csv":
            df = pd.read_csv(path)
        elif cfg["type"] == "parquet":
            df = pd.read_parquet(path)
        elif cfg["type"] == "excel":
            df = pd.read_excel(path, nrows=5000)

        print(f"  Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
        print(f"  Columns: {list(df.columns)}")
        null_counts = df.isnull().sum()
        max_null_col = null_counts.idxmax()
        max_null_pct = (null_counts.max() / len(df)) * 100
        print(f"  Missing values: Max in '{max_null_col}' ({max_null_pct:.1f}%)")

        report.append({
            "name": cfg["name"],
            "rows": df.shape[0],
            "cols": df.shape[1],
            "columns": list(df.columns),
            "max_null": f"{max_null_col} ({max_null_pct:.1f}%)",
            "role": cfg["role"]
        })

    print("\n" + "=" * 80)
    print("DATA STRATEGY & JUSTIFICATION")
    print("=" * 80)
    print("""
1. PRIMARY DATASET: India Weather & Rainfall Data (2015-2025)
   - Reason: 970,339 rows across 406 distinct IMD weather stations spanning all 32 Indian States.
   - Contains exact geospatial coordinates (Latitude, Longitude, Elevation), air pressure, wind speed,
     min/avg/max temperature, daily rainfall (0 to 485.9 mm).
   - Contains 8,062 heavy rain events (>=64.5mm), 1,862 very heavy (>=115.6mm), 264 extremely heavy (>=204.5mm).
   - Provides a comprehensive ground truth for spatial nearest-neighbor search on the India map.

2. FEATURE ENRICHMENT & METEOROLOGICAL DERIVATIONS:
   - Relative humidity proxy and vapor pressure calculation (Tetens formulation).
   - Diurnal temperature range (DTR = max_temp - min_temp), atmospheric lapse and barometric indicators.
   - Rolling rainfall aggregations per station (1-day, 3-day, 7-day cumulative rainfall).
   - Cyclic seasonal encoding (day of year sine/cosine, month features, JJAS monsoon flag).
   - District normal baseline enrichment from Dataset 3b.

3. HISTORICAL NORMAL BASELINES (Datasets 3, 3b, 4):
   - Generates historical normal rainfall lookup tables per district and subdivision.

4. SATELLITE TELEMETRY (RainCast - Dataset 6):
   - Evaluated as specialized Track C satellite-communication rain attenuation analysis.

5. GEOCODING & SPATIAL LOOKUP TABLE:
   - Pre-build spatial BallTree/cKDTree from all 406 unique weather stations across India.
   - Exact station lat/lon coverage: Latitude ~8.3°N to 34.5°N, Longitude ~69.0°E to 95.5°E.
""")
    return report

if __name__ == "__main__":
    run_data_audit()
