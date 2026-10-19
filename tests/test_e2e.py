"""
End-to-End System Test for RainXplain.
Tests the full pipeline from coordinate query to geo-matching, inference,
SHAP/LIME explanation, and SQLite audit logging.
"""
import os
import sys
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api.main import app
from api.db import get_recent_predictions, get_db_stats

def test_full_pipeline():
    client = TestClient(app)

    print("=== 1. Testing GET /health ===")
    res_health = client.get("/health").json()
    print("Health:", res_health)
    assert res_health["status"] == "healthy"

    print("\n=== 2. Testing Multiple Indian Locations End-to-End ===")
    test_locations = [
        {"name": "Mumbai Monsoon Storm", "lat": 19.0760, "lon": 72.8777, "lag1": 85.0, "pressure": 998.0, "wind": 35.0, "month": 7},
        {"name": "Delhi Winter Dry", "lat": 28.6139, "lon": 77.2090, "lag1": 0.0, "pressure": 1015.0, "wind": 5.0, "month": 1},
        {"name": "Cherrapunji Cloudburst", "lat": 25.2986, "lon": 91.5822, "lag1": 190.0, "pressure": 990.0, "wind": 25.0, "month": 6},
        {"name": "Bengaluru Moderate Shower", "lat": 12.9716, "lon": 77.5946, "lag1": 20.0, "pressure": 1009.0, "wind": 12.0, "month": 8},
        {"name": "Chennai Post-Monsoon", "lat": 13.0827, "lon": 80.2707, "lag1": 75.0, "pressure": 1001.0, "wind": 28.0, "month": 11}
    ]

    for loc in test_locations:
        payload = {
            "latitude": loc["lat"],
            "longitude": loc["lon"],
            "rainfall_lag1": loc["lag1"],
            "air_pressure": loc["pressure"],
            "wind_speed": loc["wind"],
            "month": loc["month"]
        }
        r = client.post("/explain", json=payload)
        assert r.status_code == 200
        data = r.json()
        print(f"\n[{loc['name']}] -> Matched: {data['matched_region']} ({data['distance_km']} km)")
        print(f"  Risk Level : {data['risk_level']} ({data['probability_pct']})")
        print(f"  Top SHAP   : {[f['feature'] + ': ' + str(f['shap_value']) for f in data['top_contributing_factors'][:2]]}")
        print(f"  Summary    : {data['plain_language_summary']}")

    print("\n=== 3. Verifying SQLite Database Audit Log ===")
    stats = get_db_stats()
    print(f"Total logged in SQLite: {stats['total_predictions_logged']}")
    assert stats["total_predictions_logged"] >= 5

    recent = get_recent_predictions(limit=5)
    print("Recent logs retrieved from DB:")
    for item in recent:
        print(f"  Log #{item['id']}: {item['timestamp']} | Lat: {item['latitude']:.2f}, Lon: {item['longitude']:.2f} | {item['matched_region']} | {item['risk_level']} ({item['probability']})")

    print("\n=== ALL END-TO-END FLOW CHECKS PASSED PERFECTLY! ===")

if __name__ == "__main__":
    test_full_pipeline()
