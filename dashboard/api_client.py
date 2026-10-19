"""
Backend access layer for the RainXplain dashboard.
Every function here calls the FastAPI service over HTTP first, falling back to
calling the local src/api modules directly if the service is unreachable.
"""
import os
import sys
import json

import requests
import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")


@st.cache_data(ttl=600)
def fetch_stations():
    try:
        r = requests.get(f"{API_URL}/stations", timeout=4)
        if r.status_code == 200:
            return r.json().get("stations", [])
    except Exception:
        lookup_path = os.path.join(BASE_DIR, "data", "processed", "region_lookup.parquet")
        if os.path.exists(lookup_path):
            df = pd.read_parquet(lookup_path)
            return df.to_dict(orient="records")
    return []


def call_geo_match(lat, lon):
    try:
        r = requests.post(f"{API_URL}/match-geo", json={"latitude": lat, "longitude": lon}, timeout=4)
        if r.status_code == 200:
            return r.json()
    except Exception:
        from src.geo_match import match_coordinates
        return match_coordinates(lat, lon)
    return None


def call_explain_api(payload):
    try:
        r = requests.post(f"{API_URL}/explain", json=payload, timeout=8)
        if r.status_code == 200:
            return r.json()
        else:
            st.error(f"API Error ({r.status_code}): {r.text}")
    except Exception:
        from src.predict import predict_and_explain
        from src.geo_match import match_coordinates
        from src.impact import estimate_impact
        res = predict_and_explain(payload)
        geo_info = match_coordinates(payload.get("latitude", 19.076), payload.get("longitude", 72.877))
        state_name = geo_info.get("matched_state", "Maharashtra")
        res["impact_estimation"] = estimate_impact(state_name, res.get("risk_level"), res.get("probability"))
        return res
    return None


def call_multi_day_forecast(payload):
    try:
        r = requests.post(f"{API_URL}/forecast/multi-day?days=5", json=payload, timeout=6)
        if r.status_code == 200:
            return r.json()
    except Exception:
        from src.predict import get_predictor
        return get_predictor().predict_multi_day_forecast(payload, num_days=5)
    return None


def fetch_performance_metrics():
    metrics_dir = os.path.join(BASE_DIR, "models", "metrics")
    res = {}
    for fname in ["metrics.json", "roc_curve.json", "confusion_matrix.json", "global_shap.json"]:
        fpath = os.path.join(metrics_dir, fname)
        if os.path.exists(fpath):
            with open(fpath) as f:
                res[fname.replace(".json", "")] = json.load(f)
    return res


def subscribe_alert(email, region, lat, lon):
    try:
        r = requests.post(f"{API_URL}/subscribe", json={
            "email": email,
            "region_or_latlon": region,
            "latitude": lat,
            "longitude": lon
        }, timeout=4)
        if r.status_code == 200:
            return True, f"Subscribed {email} to alerts for {region}!"
        return False, f"Subscription failed: {r.text}"
    except Exception:
        from api.db import create_subscription
        create_subscription(email, region, lat, lon)
        return True, f"Subscribed {email} to alerts for {region}!"


def fetch_recent_predictions(limit=50):
    try:
        r = requests.get(f"{API_URL}/predictions/recent?limit={limit}", timeout=4)
        if r.status_code == 200:
            return r.json().get("predictions", [])
        from api.db import get_recent_predictions
        return get_recent_predictions(limit=limit)
    except Exception:
        from api.db import get_recent_predictions
        return get_recent_predictions(limit=limit)


def fetch_admin_governance_data():
    try:
        from api.db import get_db_stats, get_recent_predictions, get_recent_alerts
        stats = get_db_stats()
        recent_logs = get_recent_predictions(limit=100)
        alerts_sent = get_recent_alerts(limit=50)
        return stats, recent_logs, alerts_sent, None
    except Exception as e:
        return {}, [], [], str(e)
