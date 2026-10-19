"""
FastAPI REST Service for RainXplain.
Exposes endpoints for prediction, explainability, spatial geocoding, and SQLite audit logs.
"""
import os
import sys
import json
import logging
import traceback
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger("rainxplain")
logging.basicConfig(level=logging.INFO)

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.predict import get_predictor
from src.geo_match import get_geo_matcher, match_coordinates
from src.impact import estimate_impact
from api.db import (
    log_prediction_event, get_recent_predictions, get_db_stats,
    create_subscription, get_all_subscriptions, get_recent_alerts, get_prediction_by_id
)
from api.alerts import start_alert_scheduler
from api.report import generate_pdf_report

app = FastAPI(
    title="RainXplain Explainable AI API",
    version="1.1.0",
    description="Explainable AI (XAI) System for Heavy Rain Prediction across India (SDG 9: Resilient Infrastructure)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    try:
        start_alert_scheduler(interval_minutes=60)
    except Exception as e:
        print(f"Warning: Failed to start alert scheduler: {e}")

# ----------------- Pydantic Models ----------------- #

class GeoQuery(BaseModel):
    latitude: float = Field(..., ge=6.0, le=38.0, description="Latitude inside India")
    longitude: float = Field(..., ge=68.0, le=98.0, description="Longitude inside India")

class RainPredictRequest(BaseModel):
    latitude: Optional[float] = Field(None, ge=5.0, le=40.0)
    longitude: Optional[float] = Field(None, ge=65.0, le=100.0)
    avg_temp: Optional[float] = Field(None, description="Average temperature in Celsius")
    min_temp: Optional[float] = Field(None, description="Minimum temperature in Celsius")
    max_temp: Optional[float] = Field(None, description="Maximum temperature in Celsius")
    air_pressure: Optional[float] = Field(None, description="Atmospheric surface pressure in hPa")
    wind_speed: Optional[float] = Field(None, description="Wind speed in km/h")
    elevation: Optional[float] = Field(None, description="Elevation above sea level in meters")
    rainfall_lag1: Optional[float] = Field(0.0, description="1-day lag rainfall (mm)")
    rainfall_lag2: Optional[float] = Field(0.0, description="2-day lag rainfall (mm)")
    rainfall_roll3_sum: Optional[float] = Field(None, description="3-day cumulative rainfall (mm)")
    rainfall_roll7_sum: Optional[float] = Field(None, description="7-day cumulative rainfall (mm)")
    month: Optional[int] = Field(7, ge=1, le=12, description="Month of prediction (1-12)")
    day_of_year: Optional[int] = Field(None, ge=1, le=366)

class SubscribeRequest(BaseModel):
    email: str = Field(..., description="Subscriber email address")
    region_or_latlon: str = Field(..., description="Target Indian station or region name")
    latitude: Optional[float] = Field(None)
    longitude: Optional[float] = Field(None)

# ----------------- Endpoints ----------------- #

@app.get("/", tags=["System"])
def root():
    return {
        "message": "Welcome to RainXplain XAI Engine API",
        "health": "/health",
        "docs": "/docs"
    }

@app.get("/health", tags=["System"])
def health_check():
    """System health check and diagnostic statistics."""
    stats = get_db_stats()
    return {
        "status": "healthy",
        "service": "RainXplain XAI Engine",
        "version": "1.1.0",
        "model": "XGBoost Heavy Rain Classifier (v1.0)",
        "frameworks": ["FastAPI", "XGBoost", "SHAP", "LIME", "ReportLab", "APScheduler"],
        "database_stats": stats
    }

@app.post("/match-geo", tags=["Geospatial"])
def match_geo(query: GeoQuery):
    """Finds nearest Indian weather station and retrieves baseline features."""
    try:
        match_res = match_coordinates(query.latitude, query.longitude)
        return match_res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stations", tags=["Geospatial"])
def get_all_stations():
    """Returns all 406 indexed weather stations across India for map visualization."""
    try:
        matcher = get_geo_matcher()
        stations = matcher.lookup_df.to_dict(orient="records")
        return {
            "total_stations": len(stations),
            "stations": stations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict", tags=["Inference"])
def predict_heavy_rain(req: RainPredictRequest):
    """
    Predicts heavy rain event probability given coordinates and/or weather parameters.
    Automatically logs query and confidence flags to SQLite.
    """
    try:
        predictor = get_predictor()
        input_data = req.model_dump(exclude_unset=True) if hasattr(req, 'model_dump') else req.dict(exclude_unset=True)
        res = predictor.predict(input_data)

        # Log prediction
        log_prediction_event(
            latitude=req.latitude,
            longitude=req.longitude,
            matched_region=res.get("matched_region"),
            distance_km=res.get("distance_km"),
            input_features=res.get("input_features"),
            prediction=res.get("prediction"),
            probability=res.get("probability"),
            risk_level=res.get("risk_level"),
            imd_category=res.get("imd_category"),
            top_shap_factors=[],
            plain_language_summary=""
        )
        return res
    except Exception as e:
        logger.error("Prediction failed for payload=%s\n%s", req.model_dump(exclude_unset=True), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@app.post("/explain", tags=["Explainability"])
def explain_heavy_rain(req: RainPredictRequest):
    """
    Runs full XGBoost inference with local SHAP, LIME, and impact estimation.
    Automatically logs query and top SHAP factors to SQLite.
    """
    try:
        predictor = get_predictor()
        input_data = req.model_dump(exclude_unset=True) if hasattr(req, 'model_dump') else req.dict(exclude_unset=True)
        res = predictor.predict_and_explain(input_data)

        # Attach Impact Estimation (Stretch Feature #7)
        geo_info = match_coordinates(req.latitude or 19.0760, req.longitude or 72.8777)
        state_name = geo_info.get("matched_state", "Maharashtra")
        impact_info = estimate_impact(state_name, res.get("risk_level"), res.get("probability"))
        res["impact_estimation"] = impact_info

        # Log prediction with explanation factors
        log_prediction_event(
            latitude=req.latitude,
            longitude=req.longitude,
            matched_region=res.get("matched_region"),
            distance_km=res.get("distance_km"),
            input_features=res.get("input_features"),
            prediction=res.get("prediction"),
            probability=res.get("probability"),
            risk_level=res.get("risk_level"),
            imd_category=res.get("imd_category"),
            top_shap_factors=res.get("top_contributing_factors", []),
            plain_language_summary=res.get("plain_language_summary", "")
        )
        return res
    except Exception as e:
        logger.error("Explanation failed for payload=%s\n%s", req.model_dump(exclude_unset=True), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Explanation error: {str(e)}")

@app.post("/forecast/multi-day", tags=["Inference"])
def multi_day_forecast(req: RainPredictRequest, days: int = Query(5, ge=3, le=7)):
    """Generates a 3-5 day recursive forward risk forecast for target location."""
    try:
        predictor = get_predictor()
        input_data = req.model_dump(exclude_unset=True) if hasattr(req, 'model_dump') else req.dict(exclude_unset=True)
        forecast_res = predictor.predict_multi_day_forecast(input_data, num_days=days)
        return forecast_res
    except Exception as e:
        logger.error("Forecast failed for payload=%s\n%s", req.model_dump(exclude_unset=True), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Forecast error: {str(e)}")

# ----------------- Subscription & Alerting Endpoints ----------------- #

@app.post("/subscribe", tags=["Alerts"])
def subscribe_alert(sub: SubscribeRequest):
    """Subscribes an email to automated heavy rain risk alerts for a target region."""
    try:
        sub_id = create_subscription(sub.email, sub.region_or_latlon, sub.latitude, sub.longitude)
        return {
            "status": "subscribed",
            "subscription_id": sub_id,
            "email": sub.email,
            "region": sub.region_or_latlon
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/subscriptions", tags=["Alerts"])
def list_subscriptions():
    """Lists all active region alert subscriptions."""
    try:
        return {"subscriptions": get_all_subscriptions()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alerts/recent", tags=["Alerts"])
def list_recent_alerts(limit: int = Query(50, ge=1, le=100)):
    """Retrieves recent triggered risk alerts."""
    try:
        alerts = get_recent_alerts(limit=limit)
        return {"count": len(alerts), "alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- PDF Report Endpoints ----------------- #

@app.get("/report/{prediction_id}", tags=["Reports"])
def get_prediction_report_pdf(prediction_id: int):
    """Generates and downloads a clean 1-page executive PDF report for a logged prediction ID."""
    pred_data = get_prediction_by_id(prediction_id)
    if not pred_data:
        raise HTTPException(status_code=404, detail=f"Prediction #{prediction_id} not found.")

    pdf_bytes = generate_pdf_report(pred_data)
    filename = f"RainXplain_Report_ID_{prediction_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/report/generate", tags=["Reports"])
def generate_pdf_from_payload(req: RainPredictRequest):
    """Generates PDF report on-the-fly for current prediction request payload."""
    try:
        predictor = get_predictor()
        input_data = req.model_dump(exclude_unset=True) if hasattr(req, 'model_dump') else req.dict(exclude_unset=True)
        res = predictor.predict_and_explain(input_data)
        pdf_bytes = generate_pdf_report(res)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=RainXplain_Executive_Report.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- Model Performance Metrics Endpoint ----------------- #

@app.get("/metrics/performance", tags=["Governance"])
def get_model_performance_artifacts():
    """Retrieves pre-computed test set ROC curve, confusion matrix, and global SHAP rankings."""
    metrics_dir = os.path.join(BASE_DIR, "models", "metrics")
    try:
        res = {}
        for fname in ["metrics.json", "roc_curve.json", "confusion_matrix.json", "global_shap.json"]:
            fpath = os.path.join(metrics_dir, fname)
            if os.path.exists(fpath):
                with open(fpath) as f:
                    res[fname.replace(".json", "")] = json.load(f)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/predictions/recent", tags=["Audit Log"])
def get_recent_logged_predictions(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """Retrieves recent logged predictions with full input parameters and explanations."""
    try:
        records = get_recent_predictions(limit=limit, offset=offset)
        return {
            "count": len(records),
            "limit": limit,
            "offset": offset,
            "predictions": records
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
