"""
Unit tests for spatial nearest-station matching with BallTree and Haversine distance.
"""
import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.geo_match import get_geo_matcher

def test_mumbai_match():
    matcher = get_geo_matcher()
    # Coordinates for Mumbai (19.0760, 72.8777)
    res = matcher.find_nearest_region(19.0760, 72.8777)
    
    assert res["matched_state"] in ["MH", "Maharashtra", "Mumbai"]
    assert "Bombay" in res["matched_station"] or "Santacruz" in res["matched_station"] or "Colaba" in res["matched_station"]
    assert res["distance_km"] < 25.0, f"Distance should be close to Mumbai, got {res['distance_km']} km"

def test_delhi_match():
    matcher = get_geo_matcher()
    # Coordinates for Delhi (28.6139, 77.2090)
    res = matcher.find_nearest_region(28.6139, 77.2090)
    
    assert res["matched_state"] in ["DL", "Delhi", "HR", "UP"]
    assert "Delhi" in res["matched_station"] or "Safdarjung" in res["matched_station"] or "Palam" in res["matched_station"]
    assert res["distance_km"] < 25.0

def test_bengaluru_match():
    matcher = get_geo_matcher()
    # Coordinates for Bengaluru (12.9716, 77.5946)
    res = matcher.find_nearest_region(12.9716, 77.5946)
    
    assert res["matched_state"] in ["KA", "Karnataka"]
    assert "Bangalore" in res["matched_station"] or "Bengaluru" in res["matched_station"]
    assert res["distance_km"] < 20.0
