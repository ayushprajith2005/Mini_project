"""
Feature Engineering Module for RainXplain.
Computes meteorological proxies, convective stability indicators, rolling lags,
and seasonal cyclic signals for heavy rain event prediction.
"""
import os
import json
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    'avg_temp',
    'min_temp',
    'max_temp',
    'temp_range',
    'relative_humidity_est',
    'vapor_pressure_deficit',
    'air_pressure',
    'pressure_drop_3d',
    'wind_speed',
    'wind_convective_proxy',
    'elevation',
    'latitude',
    'longitude',
    'rainfall_lag1',
    'rainfall_lag2',
    'rainfall_roll3_sum',
    'rainfall_roll7_sum',
    'temp_roll3_mean',
    'day_of_year_sin',
    'day_of_year_cos',
    'month',
    'is_monsoon',
    'is_post_monsoon'
]

def tetens_saturation_vapor_pressure(temp_c):
    """Calculates saturation vapor pressure (hPa) using Tetens equation."""
    temp_c = np.clip(temp_c, -40.0, 60.0)
    return 6.1078 * np.exp((17.27 * temp_c) / (temp_c + 237.3))

def estimate_relative_humidity(t_avg, t_min):
    """
    Estimates relative humidity (%) using daily avg temp and daily min temp as dew point proxy.
    """
    es_avg = tetens_saturation_vapor_pressure(t_avg)
    es_min = tetens_saturation_vapor_pressure(t_min)
    rh = (es_min / np.maximum(es_avg, 1e-4)) * 100.0
    return np.clip(rh, 5.0, 100.0)

def estimate_vapor_pressure_deficit(t_avg, t_min):
    """Calculates vapor pressure deficit (hPa). Low VPD indicates near-saturated atmosphere."""
    es_avg = tetens_saturation_vapor_pressure(t_avg)
    es_min = tetens_saturation_vapor_pressure(t_min)
    vpd = np.maximum(0.0, es_avg - es_min)
    return vpd

def engineer_batch_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies feature engineering across the full multi-station dataset with time lags.
    """
    df = df.copy()
    df['date_of_record'] = pd.to_datetime(df['date_of_record'])
    df = df.sort_values(by=['station_name', 'date_of_record']).reset_index(drop=True)

    # 1. Convective & Thermodynamic Features
    df['temp_range'] = np.maximum(0.0, df['max_temp'] - df['min_temp'])
    df['relative_humidity_est'] = estimate_relative_humidity(df['avg_temp'], df['min_temp'])
    df['vapor_pressure_deficit'] = estimate_vapor_pressure_deficit(df['avg_temp'], df['min_temp'])
    df['wind_convective_proxy'] = df['wind_speed'] * (df['temp_range'] / 10.0)

    # 2. Cyclic & Seasonal Features
    day_of_year = df['date_of_record'].dt.dayofyear
    df['day_of_year_sin'] = np.sin(2 * np.pi * day_of_year / 365.25)
    df['day_of_year_cos'] = np.cos(2 * np.pi * day_of_year / 365.25)
    df['month'] = df['date_of_record'].dt.month
    df['is_monsoon'] = df['month'].isin([6, 7, 8, 9]).astype(int)
    df['is_post_monsoon'] = df['month'].isin([10, 11]).astype(int)

    # 3. Time Lags & Rolling Features (grouped by station)
    grouped = df.groupby('station_name')

    df['rainfall_lag1'] = grouped['rainfall'].shift(1).fillna(0.0)
    df['rainfall_lag2'] = grouped['rainfall'].shift(2).fillna(0.0)
    df['rainfall_roll3_sum'] = grouped['rainfall'].transform(lambda x: x.shift(1).rolling(3, min_periods=1).sum()).fillna(0.0)
    df['rainfall_roll7_sum'] = grouped['rainfall'].transform(lambda x: x.shift(1).rolling(7, min_periods=1).sum()).fillna(0.0)

    df['temp_roll3_mean'] = grouped['avg_temp'].transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean()).fillna(df['avg_temp'])
    df['pressure_roll3_mean'] = grouped['air_pressure'].transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean()).fillna(df['air_pressure'])
    
    # Barometric pressure drop indicator (drop > 2-4 hPa signals monsoon depressions/cyclones)
    df['pressure_drop_3d'] = df['pressure_roll3_mean'] - df['air_pressure']

    return df

def extract_single_feature_vector(input_dict: dict) -> pd.DataFrame:
    """
    Transforms a single input dictionary (from API or dashboard) into a 1-row DataFrame
    aligned with model feature columns.
    """
    avg_temp = float(input_dict.get('avg_temp', 28.0))
    min_temp = float(input_dict.get('min_temp', avg_temp - 5.0))
    max_temp = float(input_dict.get('max_temp', avg_temp + 5.0))
    air_pressure = float(input_dict.get('air_pressure', 1008.0))
    wind_speed = float(input_dict.get('wind_speed', 10.0))
    elevation = float(input_dict.get('elevation', 150.0))
    latitude = float(input_dict.get('latitude', 20.0))
    longitude = float(input_dict.get('longitude', 78.0))

    rainfall_lag1 = float(input_dict.get('rainfall_lag1', 0.0))
    rainfall_lag2 = float(input_dict.get('rainfall_lag2', 0.0))
    rainfall_roll3_sum = float(input_dict.get('rainfall_roll3_sum', rainfall_lag1 + rainfall_lag2))
    rainfall_roll7_sum = float(input_dict.get('rainfall_roll7_sum', rainfall_roll3_sum * 1.5))
    temp_roll3_mean = float(input_dict.get('temp_roll3_mean', avg_temp))
    pressure_roll3_mean = float(input_dict.get('pressure_roll3_mean', air_pressure))
    
    month = int(input_dict.get('month', 7)) # Default July (Monsoon)
    day_of_year = int(input_dict.get('day_of_year', month * 30))

    temp_range = max(0.0, max_temp - min_temp)
    relative_humidity_est = float(input_dict.get('relative_humidity_est', estimate_relative_humidity(avg_temp, min_temp)))
    vapor_pressure_deficit = estimate_vapor_pressure_deficit(avg_temp, min_temp)
    wind_convective_proxy = wind_speed * (temp_range / 10.0)
    pressure_drop_3d = pressure_roll3_mean - air_pressure

    day_of_year_sin = np.sin(2 * np.pi * day_of_year / 365.25)
    day_of_year_cos = np.cos(2 * np.pi * day_of_year / 365.25)
    is_monsoon = 1 if month in [6, 7, 8, 9] else 0
    is_post_monsoon = 1 if month in [10, 11] else 0

    row_data = {
        'avg_temp': avg_temp,
        'min_temp': min_temp,
        'max_temp': max_temp,
        'temp_range': temp_range,
        'relative_humidity_est': relative_humidity_est,
        'vapor_pressure_deficit': vapor_pressure_deficit,
        'air_pressure': air_pressure,
        'pressure_drop_3d': pressure_drop_3d,
        'wind_speed': wind_speed,
        'wind_convective_proxy': wind_convective_proxy,
        'elevation': elevation,
        'latitude': latitude,
        'longitude': longitude,
        'rainfall_lag1': rainfall_lag1,
        'rainfall_lag2': rainfall_lag2,
        'rainfall_roll3_sum': rainfall_roll3_sum,
        'rainfall_roll7_sum': rainfall_roll7_sum,
        'temp_roll3_mean': temp_roll3_mean,
        'day_of_year_sin': day_of_year_sin,
        'day_of_year_cos': day_of_year_cos,
        'month': month,
        'is_monsoon': is_monsoon,
        'is_post_monsoon': is_post_monsoon
    }

    df_single = pd.DataFrame([row_data])[FEATURE_COLUMNS]
    return df_single

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    clean_path = os.path.join(base_dir, "data", "processed", "cleaned_weather_data.parquet")
    if os.path.exists(clean_path):
        print(f"Reading {clean_path}...")
        df = pd.read_parquet(clean_path)
        print(f"Engineering features for {len(df):,} records...")
        df_feat = engineer_batch_features(df)
        feat_path = os.path.join(base_dir, "data", "processed", "featured_weather_data.parquet")
        df_feat.to_parquet(feat_path, index=False)
        print(f"Engineered dataset saved to {feat_path} with {len(FEATURE_COLUMNS)} features!")
