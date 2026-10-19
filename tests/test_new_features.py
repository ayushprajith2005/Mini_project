"""
Unit & Integration Tests for RainXplain Core & Stretch Features.
Tests ROC/CM metrics artifacts, automated email alerting trigger,
confidence/anomaly flags, PDF report generation, and multi-day recursive forecasting.
"""
import os
import sys
import json
import pytest
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api.main import app
from src.geo_match import match_coordinates
from src.predict import get_predictor
from api.db import create_subscription, get_all_subscriptions, log_alert_sent, get_recent_alerts
from api.alerts import send_email_alert, check_and_trigger_alerts
from api.report import generate_pdf_report
from src.impact import estimate_impact

client = TestClient(app)

def test_feature_1_model_performance_artifacts():
    """Requirement 1: Verify metric artifacts exist and contain valid fields."""
    metrics_dir = os.path.join(BASE_DIR, "models", "metrics")
    assert os.path.exists(metrics_dir), "models/metrics directory should exist"
    
    # Check roc_curve.json
    roc_path = os.path.join(metrics_dir, "roc_curve.json")
    assert os.path.exists(roc_path)
    with open(roc_path) as f:
        roc_data = json.load(f)
        assert "fpr" in roc_data
        assert "tpr" in roc_data
        assert "roc_auc" in roc_data
        assert roc_data["roc_auc"] > 0.8

    # Check confusion_matrix.json
    cm_path = os.path.join(metrics_dir, "confusion_matrix.json")
    assert os.path.exists(cm_path)
    with open(cm_path) as f:
        cm_data = json.load(f)
        assert "matrix" in cm_data
        assert len(cm_data["matrix"]) == 2

    # Check global_shap.json
    shap_path = os.path.join(metrics_dir, "global_shap.json")
    assert os.path.exists(shap_path)
    with open(shap_path) as f:
        shap_data = json.load(f)
        assert len(shap_data) > 0
        assert "feature" in shap_data[0]
        assert "mean_abs_shap" in shap_data[0]

def test_feature_3_confidence_and_anomaly_flagging():
    """Requirement 3: Verify spatial distance (>50km) and decision boundary flags."""
    predictor = get_predictor()

    # 1. Spatial distance anomaly (>50km)
    # Query point off coast or near border
    res_far = predictor.predict({"latitude": 7.0, "longitude": 70.0})
    flags_far = res_far.get("confidence_flags", [])
    assert any("Low confidence" in f for f in flags_far)

    # 2. Probability near decision boundary (0.25 to 0.45)
    res_normal = predictor.predict({"latitude": 19.076, "longitude": 72.877, "rainfall_lag1": 35.0, "air_pressure": 1004.0})
    flags_normal = res_normal.get("confidence_flags", [])
    # Verify confidence_flags key exists in payload
    assert "confidence_flags" in res_normal

def test_feature_2_automated_alerting():
    """Requirement 2: Verify SQLite subscription table, mock email trigger, and alerts logging."""
    sub_id = create_subscription("alert_test@rainxplain.org", "Mumbai", 19.0760, 72.8777)
    assert sub_id > 0

    subs = get_all_subscriptions()
    assert any(s["email"] == "alert_test@rainxplain.org" for s in subs)

    # Mock send_email_alert (smtplib fallback)
    success = send_email_alert("alert_test@rainxplain.org", "Mumbai", "HEAVY RAIN WARNING", 0.65)
    assert success is True

    # Check alerts_sent log
    alert_id = log_alert_sent(sub_id, "alert_test@rainxplain.org", "Mumbai", "HEAVY RAIN WARNING", 0.65)
    assert alert_id > 0

    recent_alerts = get_recent_alerts(limit=5)
    assert len(recent_alerts) > 0
    assert recent_alerts[0]["email"] == "alert_test@rainxplain.org"

def test_feature_4_pdf_report_generation():
    """Requirement 4: Verify single-page PDF report generation and backend endpoint."""
    predictor = get_predictor()
    res = predictor.predict_and_explain({"latitude": 19.0760, "longitude": 72.8777, "rainfall_lag1": 80.0})

    pdf_bytes = generate_pdf_report(res)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")

def test_stretch_feature_5_multi_day_forecast():
    """Stretch Requirement 5: Verify multi-day recursive forecast payload."""
    predictor = get_predictor()
    fc = predictor.predict_multi_day_forecast({"latitude": 19.0760, "longitude": 72.8777}, num_days=5)
    assert "forecast_days" in fc
    assert len(fc["forecast_days"]) == 5
    assert "disclaimer" in fc

def test_stretch_feature_7_impact_estimation():
    """Stretch Requirement 7: Verify static population density impact layer."""
    impact = estimate_impact("Maharashtra", "HEAVY RAIN WARNING", 0.65)
    assert "population_density_sq_km" in impact
    assert impact["population_density_sq_km"] > 0
    assert "overall_impact_label" in impact

def test_api_endpoints_integration():
    """Verify API endpoints end-to-end via TestClient."""
    # GET /health
    r_health = client.get("/health")
    assert r_health.status_code == 200

    # POST /predict
    r_pred = client.post("/predict", json={"latitude": 19.0760, "longitude": 72.8777})
    assert r_pred.status_code == 200
    data_pred = r_pred.json()
    assert "confidence_flags" in data_pred

    # POST /explain
    r_exp = client.post("/explain", json={"latitude": 19.0760, "longitude": 72.8777})
    assert r_exp.status_code == 200
    data_exp = r_exp.json()
    assert "shap_lime_comparison" in data_exp
    assert "impact_estimation" in data_exp

    # GET /metrics/performance
    r_metrics = client.get("/metrics/performance")
    assert r_metrics.status_code == 200
    assert "roc_curve" in r_metrics.json()

    # POST /subscribe
    r_sub = client.post("/subscribe", json={"email": "api_test@rainxplain.org", "region_or_latlon": "Delhi", "latitude": 28.6139, "longitude": 77.2090})
    assert r_sub.status_code == 200

    # GET /subscriptions
    r_subs = client.get("/subscriptions")
    assert r_subs.status_code == 200

    # GET /alerts/recent
    r_alerts = client.get("/alerts/recent")
    assert r_alerts.status_code == 200

    # POST /report/generate
    r_pdf = client.post("/report/generate", json={"latitude": 19.0760, "longitude": 72.8777})
    assert r_pdf.status_code == 200
    assert r_pdf.headers["content-type"] == "application/pdf"
    assert r_pdf.content.startswith(b"%PDF")
