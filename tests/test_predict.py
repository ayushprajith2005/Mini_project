"""
Unit tests for predict_and_explain orchestration and API schema.
"""
import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.predict import predict_and_explain

def test_predict_and_explain_structure():
    sample_input = {
        "latitude": 19.0760,
        "longitude": 72.8777,
        "avg_temp": 28.0,
        "min_temp": 24.0,
        "max_temp": 32.0,
        "air_pressure": 1004.0,
        "wind_speed": 18.0,
        "rainfall_lag1": 40.0,
        "month": 7
    }
    
    result = predict_and_explain(sample_input)
    
    assert "prediction" in result
    assert result["prediction"] in [0, 1]
    assert "probability" in result
    assert 0.0 <= result["probability"] <= 1.0
    assert "risk_level" in result
    assert "shap_explanation" in result
    assert len(result["shap_explanation"]) > 0
    assert "lime_explanation" in result
    assert "plain_language_summary" in result
    assert len(result["plain_language_summary"]) > 10
