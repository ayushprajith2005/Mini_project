"""
Unit tests for data loader and region lookup table.
"""
import os
import sys
import pytest
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def test_region_lookup_exists_and_valid():
    lookup_parquet = os.path.join(BASE_DIR, "data", "processed", "region_lookup.parquet")
    lookup_json = os.path.join(BASE_DIR, "data", "processed", "region_lookup.json")
    
    assert os.path.exists(lookup_parquet) or os.path.exists(lookup_json), "Region lookup file must exist"
    
    if os.path.exists(lookup_parquet):
        df = pd.read_parquet(lookup_parquet)
    else:
        df = pd.read_json(lookup_json)
        
    assert len(df) >= 300, "Should have at least 300 weather stations in India"
    assert "station_name" in df.columns
    assert "latitude" in df.columns
    assert "longitude" in df.columns
    assert "avg_temp" in df.columns
    
    # Check Indian geographic bounding box
    assert df["latitude"].between(6.0, 38.0).all()
    assert df["longitude"].between(68.0, 98.0).all()

def test_cleaned_data_targets():
    clean_path = os.path.join(BASE_DIR, "data", "processed", "cleaned_weather_data.parquet")
    assert os.path.exists(clean_path), "Cleaned dataset should exist"
    df = pd.read_parquet(clean_path)
    
    assert "heavy_rain_event" in df.columns
    assert "risk_class" in df.columns
    assert set(df["heavy_rain_event"].unique()).issubset({0, 1})
    assert set(df["risk_class"].unique()).issubset({0, 1, 2})
