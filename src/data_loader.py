"""
Data Loader and Region Centroid Builder for RainXplain.
Loads the primary weather dataset, cleans features, builds the regional geospatial lookup table,
and constructs target variables (IMD heavy rain thresholds).
"""
import os
import json
import numpy as np
import pandas as pd

# IMD Rainfall Thresholds (mm/24hr)
IMD_HEAVY_THRESHOLD = 64.5       # Heavy rain: 64.5 - 115.5 mm
IMD_VERY_HEAVY_THRESHOLD = 115.6 # Very heavy rain: 115.6 - 204.4 mm
IMD_EXTREME_THRESHOLD = 204.5    # Extremely heavy rain: >= 204.5 mm

def get_paths():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, "data", "raw")
    proc_dir = os.path.join(base_dir, "data", "processed")
    os.makedirs(proc_dir, exist_ok=True)
    return base_dir, raw_dir, proc_dir

def build_region_lookup(df: pd.DataFrame, proc_dir: str) -> pd.DataFrame:
    """
    Builds a unique station/region coordinate lookup table with baseline climatology.
    """
    stations = df.groupby('station_name').agg({
        'latitude': 'first',
        'longitude': 'first',
        'elevation': 'first',
        'state': 'first',
        'district': 'first',
        'avg_temp': 'mean',
        'min_temp': 'mean',
        'max_temp': 'mean',
        'wind_speed': 'mean',
        'air_pressure': 'mean',
        'rainfall': 'mean'
    }).reset_index()

    # Fill any null means with dataset-wide medians
    stations['wind_speed'] = stations['wind_speed'].fillna(df['wind_speed'].median())
    stations['air_pressure'] = stations['air_pressure'].fillna(df['air_pressure'].median())
    stations['min_temp'] = stations['min_temp'].fillna(df['min_temp'].median())
    stations['max_temp'] = stations['max_temp'].fillna(df['max_temp'].median())
    stations['rainfall'] = stations['rainfall'].fillna(0.0)

    # Save to JSON and Parquet for fast querying
    lookup_path_json = os.path.join(proc_dir, "region_lookup.json")
    lookup_path_parquet = os.path.join(proc_dir, "region_lookup.parquet")
    
    stations.to_json(lookup_path_json, orient='records', indent=2)
    stations.to_parquet(lookup_path_parquet, index=False)
    print(f"Region lookup built with {len(stations)} stations across India saved to {lookup_path_json}")
    return stations

def load_and_preprocess_primary_data(sample_limit: int = None) -> pd.DataFrame:
    """
    Loads the primary weather dataset, handles missing values, cleans columns,
    and creates IMD target classification labels.
    """
    base_dir, raw_dir, proc_dir = get_paths()
    parquet_path = os.path.join(proc_dir, "india_weather_rainfall_data.parquet")
    excel_path = os.path.join(raw_dir, "india_weather_rainfall_data.xlsx")

    if os.path.exists(parquet_path):
        print(f"Loading primary dataset from Parquet: {parquet_path}")
        df = pd.read_parquet(parquet_path)
    elif os.path.exists(excel_path):
        print(f"Loading primary dataset from Excel: {excel_path}")
        df = pd.read_excel(excel_path)
        df.to_parquet(parquet_path, index=False)
    else:
        raise FileNotFoundError(f"Neither {parquet_path} nor {excel_path} found.")

    if sample_limit and len(df) > sample_limit:
        df = df.iloc[:sample_limit].copy()

    # Ensure correct datetime type and sort for time-series features
    df['date_of_record'] = pd.to_datetime(df['date_of_record'])
    df = df.sort_values(by=['station_name', 'date_of_record']).reset_index(drop=True)

    # Drop records where rainfall ground-truth is missing
    initial_len = len(df)
    df = df.dropna(subset=['rainfall']).copy()
    dropped_target_nulls = initial_len - len(df)
    print(f"Dropped {dropped_target_nulls} rows with null rainfall labels. Remaining rows: {len(df):,}")

    # Build region lookup from valid station data
    build_region_lookup(df, proc_dir)

    # Missing value imputation per station or global median
    df['avg_temp'] = df['avg_temp'].fillna(df.groupby('station_name')['avg_temp'].transform('median'))
    df['min_temp'] = df['min_temp'].fillna(df['avg_temp'] - 5.0)
    df['max_temp'] = df['max_temp'].fillna(df['avg_temp'] + 5.0)
    
    global_pressure = df['air_pressure'].median() if not df['air_pressure'].isnull().all() else 1010.0
    global_wind = df['wind_speed'].median() if not df['wind_speed'].isnull().all() else 8.5

    df['air_pressure'] = df['air_pressure'].fillna(df.groupby('station_name')['air_pressure'].transform('median')).fillna(global_pressure)
    df['wind_speed'] = df['wind_speed'].fillna(df.groupby('station_name')['wind_speed'].transform('median')).fillna(global_wind)

    # Target Engineering (IMD Criteria)
    # Binary target: 1 if Heavy Rain (>= 64.5 mm/24h), else 0
    df['heavy_rain_event'] = (df['rainfall'] >= IMD_HEAVY_THRESHOLD).astype(int)
    
    # Multi-class target: 0: Normal/Light (<64.5mm), 1: Heavy (64.5-115.5mm), 2: Very Heavy/Extreme (>=115.6mm)
    conditions = [
        (df['rainfall'] < IMD_HEAVY_THRESHOLD),
        (df['rainfall'] >= IMD_HEAVY_THRESHOLD) & (df['rainfall'] < IMD_VERY_HEAVY_THRESHOLD),
        (df['rainfall'] >= IMD_VERY_HEAVY_THRESHOLD)
    ]
    choices = [0, 1, 2] # 0: None/Light, 1: Heavy, 2: Very Heavy
    df['risk_class'] = np.select(conditions, choices, default=0)

    heavy_count = df['heavy_rain_event'].sum()
    very_heavy_count = (df['risk_class'] == 2).sum()
    total = len(df)
    print(f"Target stats: Total={total:,}, Heavy={heavy_count:,} ({heavy_count/total*100:.2f}%), Very Heavy={very_heavy_count:,} ({very_heavy_count/total*100:.2f}%)")

    # Save cleaned preprocessed base
    clean_path = os.path.join(proc_dir, "cleaned_weather_data.parquet")
    df.to_parquet(clean_path, index=False)
    print(f"Cleaned dataset saved to {clean_path}")

    return df

if __name__ == "__main__":
    load_and_preprocess_primary_data()
