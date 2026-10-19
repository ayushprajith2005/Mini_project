"""
Spatial Indexing and Nearest-Region Matching Module for RainXplain.
Uses BallTree with Haversine metric to find the nearest Indian weather station / district
given any user-clicked (lat, lon) on the map.
"""
import os
import json
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

EARTH_RADIUS_KM = 6371.0088

class IndiaGeoMatcher:
    def __init__(self, lookup_path: str = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if lookup_path is None:
            lookup_path = os.path.join(base_dir, "data", "processed", "region_lookup.parquet")
            if not os.path.exists(lookup_path):
                lookup_path = os.path.join(base_dir, "data", "processed", "region_lookup.json")

        self.lookup_df = self._load_lookup(lookup_path)
        self._build_spatial_index()

    def _load_lookup(self, path: str) -> pd.DataFrame:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Lookup file not found at {path}. Run data_loader.py first.")
        if path.endswith(".parquet"):
            df = pd.read_parquet(path)
        else:
            df = pd.read_json(path)
        return df

    def _build_spatial_index(self):
        # Extract lat/lon in radians for Haversine
        coords_rad = np.radians(self.lookup_df[['latitude', 'longitude']].values)
        self.ball_tree = BallTree(coords_rad, metric='haversine')

    def find_nearest_region(self, lat: float, lon: float, distance_threshold_km: float = 50.0) -> dict:
        """
        Finds the nearest weather station/region to (lat, lon) using Haversine BallTree.
        Returns station metadata, distance in km, and baseline weather features.
        """
        # Validate latitude/longitude bounds for India (~6-38 N, ~68-98 E)
        lat = float(lat)
        lon = float(lon)

        query_rad = np.radians([[lat, lon]])
        dist_rad, indices = self.ball_tree.query(query_rad, k=1)
        
        nearest_idx = indices[0][0]
        distance_km = float(dist_rad[0][0] * EARTH_RADIUS_KM)
        matched_row = self.lookup_df.iloc[nearest_idx].to_dict()

        dist_rounded = round(distance_km, 2)
        spatial_flag = None
        if dist_rounded > distance_threshold_km:
            spatial_flag = f"Low confidence: nearest known region is {dist_rounded}km away."

        # Format clean return payload
        return {
            "query_lat": lat,
            "query_lon": lon,
            "matched_station": matched_row.get("station_name", "Unknown"),
            "matched_state": matched_row.get("state", "Unknown"),
            "matched_district": matched_row.get("district", "Unknown"),
            "station_latitude": float(matched_row.get("latitude", lat)),
            "station_longitude": float(matched_row.get("longitude", lon)),
            "distance_km": dist_rounded,
            "spatial_warning": spatial_flag,
            "elevation": float(matched_row.get("elevation", 100)),
            "avg_temp": float(matched_row.get("avg_temp", 28.0)),
            "min_temp": float(matched_row.get("min_temp", 23.0)),
            "max_temp": float(matched_row.get("max_temp", 33.0)),
            "air_pressure": float(matched_row.get("air_pressure", 1008.0)),
            "wind_speed": float(matched_row.get("wind_speed", 9.0)),
            "historical_mean_rainfall": float(matched_row.get("rainfall", 5.0))
        }

# Global cached matcher instance
_geo_matcher_instance = None

def get_geo_matcher() -> IndiaGeoMatcher:
    global _geo_matcher_instance
    if _geo_matcher_instance is None:
        _geo_matcher_instance = IndiaGeoMatcher()
    return _geo_matcher_instance

def match_coordinates(lat: float, lon: float) -> dict:
    matcher = get_geo_matcher()
    return matcher.find_nearest_region(lat, lon)

if __name__ == "__main__":
    matcher = IndiaGeoMatcher()
    # Test with major city coordinates
    test_cities = [
        ("Mumbai", 19.0760, 72.8777),
        ("Delhi", 28.6139, 77.2090),
        ("Bengaluru", 12.9716, 77.5946),
        ("Kolkata", 22.5726, 88.3639),
        ("Cherrapunji", 25.2986, 91.5822),
        ("Chennai", 13.0827, 80.2707)
    ]
    print(f"{'City':<15} | {'Queried (Lat, Lon)':<22} | {'Matched Station':<20} | {'Dist (km)':<10} | {'State'}")
    print("-" * 85)
    for name, lat, lon in test_cities:
        res = matcher.find_nearest_region(lat, lon)
        print(f"{name:<15} | {lat:.4f}, {lon:.4f}{'':<8} | {res['matched_station']:<20} | {res['distance_km']:<10.1f} | {res['matched_state']}")
