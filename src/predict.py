"""
Prediction and Explanation Orchestration Service for RainXplain.
Exposes `predict_and_explain(input_dict)` which performs feature extraction,
XGBoost inference, risk classification, and SHAP/LIME explanation generation.
"""
import os
import sys
import json
import numpy as np
import pandas as pd
import xgboost as xgb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.features import extract_single_feature_vector, FEATURE_COLUMNS
from src.geo_match import match_coordinates
from src.explain import get_explainer

class RainPredictor:
    def __init__(self, models_dir: str = None):
        if models_dir is None:
            models_dir = os.path.join(BASE_DIR, "models")
        
        self.models_dir = models_dir
        self.binary_model_path = os.path.join(models_dir, "xgboost_heavy_rain.json")
        self.multi_model_path = os.path.join(models_dir, "xgboost_multiclass.json")
        
        # Load binary model
        self.binary_model = xgb.XGBClassifier()
        self.binary_model.load_model(self.binary_model_path)

        # Load multi-class model if available
        self.multi_model = None
        if os.path.exists(self.multi_model_path):
            self.multi_model = xgb.XGBClassifier()
            self.multi_model.load_model(self.multi_model_path)

        self.explainer = get_explainer()

    def predict(self, input_dict: dict) -> dict:
        """
        Runs model prediction without full SHAP/LIME overhead (fast prediction).
        """
        # If lat/lon provided without full features, autofill from nearest region first
        enriched_input = self._enrich_input_with_geo(input_dict)
        feature_df = extract_single_feature_vector(enriched_input)

        prob_heavy = float(self.binary_model.predict_proba(feature_df)[0][1])
        prediction_binary = int(prob_heavy >= 0.35) # Tuned optimal recall threshold

        # Multi-class probabilities if model loaded
        multi_probs = [0.0, 0.0, 0.0]
        risk_tier = 0
        if self.multi_model:
            multi_probs_raw = self.multi_model.predict_proba(feature_df)[0]
            multi_probs = [float(p) for p in multi_probs_raw]
            risk_tier = int(np.argmax(multi_probs_raw))

        risk_level, imd_category, color_code = self._determine_risk_level(prob_heavy, risk_tier)

        # Confidence and Anomaly Flagging
        confidence_flags = []
        
        # 1. Spatial distance anomaly flag
        distance_km = enriched_input.get("distance_km")
        if distance_km is not None and distance_km > 50.0:
            confidence_flags.append(f"Low confidence: nearest known region is {distance_km}km away.")
        
        # 2. Probability decision boundary uncertainty flag
        if 0.25 <= prob_heavy <= 0.45:
            confidence_flags.append(f"Uncertain prediction: probability ({prob_heavy*100:.1f}%) is near decision boundary.")

        return {
            "prediction": prediction_binary,
            "prediction_label": "Heavy Rain Event (>=64.5mm)" if prediction_binary == 1 else "Normal / Moderate Rain (<64.5mm)",
            "probability": round(prob_heavy, 4),
            "probability_pct": f"{prob_heavy * 100:.1f}%",
            "risk_level": risk_level,
            "imd_category": imd_category,
            "color_code": color_code,
            "confidence_flags": confidence_flags,
            "multi_class_probabilities": {
                "normal_or_light": round(multi_probs[0], 4) if len(multi_probs) > 0 else None,
                "heavy_rain_64_115mm": round(multi_probs[1], 4) if len(multi_probs) > 1 else None,
                "very_heavy_rain_gt_115mm": round(multi_probs[2], 4) if len(multi_probs) > 2 else None
            },
            "matched_region": enriched_input.get("matched_station"),
            "distance_km": enriched_input.get("distance_km"),
            "input_features": feature_df.iloc[0].to_dict()
        }

    def predict_and_explain(self, input_dict: dict) -> dict:
        """
        Runs model prediction AND generates SHAP + LIME explainability payloads.
        """
        base_result = self.predict(input_dict)
        feature_df = pd.DataFrame([base_result["input_features"]])[FEATURE_COLUMNS]

        explanation = self.explainer.explain_instance(feature_df)

        full_payload = {
            **base_result,
            "shap_explanation": explanation["shap_explanation"],
            "top_contributing_factors": explanation["top_contributing_factors"],
            "top_mitigating_factors": explanation["top_mitigating_factors"],
            "lime_explanation": explanation["lime_explanation"],
            "shap_lime_comparison": explanation.get("shap_lime_comparison"),
            "plain_language_summary": explanation["plain_language_summary"]
        }
        return full_payload

    def predict_multi_day_forecast(self, input_dict: dict, num_days: int = 5) -> dict:
        """
        Generates a 3-5 day forward recursive risk trend using lag-feature updating.
        Clearly labeled as a simple recursive statistical estimate.
        """
        forecast = []
        current_inputs = dict(input_dict)
        
        # Baseline rainfall estimate from input or station average
        last_rainfall = float(current_inputs.get("rainfall_lag1", 10.0))
        lag1 = last_rainfall
        lag2 = float(current_inputs.get("rainfall_lag2", 5.0))
        roll3 = float(current_inputs.get("rainfall_roll3_sum", lag1 + lag2))
        roll7 = float(current_inputs.get("rainfall_roll7_sum", roll3 * 2.0))

        for day in range(1, num_days + 1):
            step_input = dict(current_inputs)
            step_input["rainfall_lag1"] = lag1
            step_input["rainfall_lag2"] = lag2
            step_input["rainfall_roll3_sum"] = roll3
            step_input["rainfall_roll7_sum"] = roll7

            pred_res = self.predict(step_input)
            prob = pred_res["probability"]

            # Estimate expected rainfall mm recursively based on predicted risk tier
            if prob >= 0.70:
                est_rain = 120.0
            elif prob >= 0.35:
                est_rain = 70.0
            elif prob >= 0.15:
                est_rain = 25.0
            else:
                est_rain = 5.0

            forecast.append({
                "day": day,
                "day_label": f"Day +{day}",
                "probability": prob,
                "probability_pct": f"{prob*100:.1f}%",
                "risk_level": pred_res["risk_level"],
                "color_code": pred_res["color_code"],
                "estimated_rainfall_mm": est_rain
            })

            # Update lag features recursively for next step
            lag2 = lag1
            lag1 = est_rain
            roll3 = lag1 + lag2 + (roll3 / 3.0)
            roll7 = roll7 * 0.85 + est_rain

        return {
            "matched_region": current_inputs.get("matched_station"),
            "forecast_days": forecast,
            "disclaimer": "Recursive statistical estimate based on lag features; not a physical Numerical Weather Prediction model."
        }

    def _enrich_input_with_geo(self, input_dict: dict) -> dict:
        enriched = dict(input_dict)
        lat = input_dict.get('latitude')
        lon = input_dict.get('longitude')
        
        if lat is not None and lon is not None:
            # Match nearest region
            geo_info = match_coordinates(float(lat), float(lon))
            enriched["matched_station"] = geo_info["matched_station"]
            enriched["matched_state"] = geo_info["matched_state"]
            enriched["matched_district"] = geo_info["matched_district"]
            enriched["distance_km"] = geo_info["distance_km"]

            # Autofill features if missing in input
            for key in ["avg_temp", "min_temp", "max_temp", "air_pressure", "wind_speed", "elevation"]:
                if key not in enriched or enriched[key] is None:
                    enriched[key] = geo_info.get(key)

        return enriched

    def _determine_risk_level(self, prob: float, risk_tier: int):
        if prob >= 0.70 or risk_tier == 2:
            return "VERY HEAVY / EXTREME RISK", ">= 115.6 mm / 24hr (Red Alert)", "#DC2626"
        elif prob >= 0.35 or risk_tier == 1:
            return "HEAVY RAIN WARNING", "64.5 - 115.5 mm / 24hr (Orange Alert)", "#EA580C"
        elif prob >= 0.15:
            return "MODERATE RISK", "15.6 - 64.4 mm / 24hr (Yellow Watch)", "#EAB308"
        else:
            return "LOW / NO RISK", "< 15.5 mm / 24hr (Green / Safe)", "#16A34A"

# Global singleton
_predictor_instance = None

def get_predictor() -> RainPredictor:
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = RainPredictor()
    return _predictor_instance

def predict_and_explain(input_dict: dict) -> dict:
    predictor = get_predictor()
    return predictor.predict_and_explain(input_dict)

if __name__ == "__main__":
    predictor = RainPredictor()
    # Test high rain case (Mumbai monsoon storm)
    high_rain_query = {
        "latitude": 19.0760,
        "longitude": 72.8777,
        "avg_temp": 26.5,
        "min_temp": 24.8,
        "max_temp": 28.2,
        "air_pressure": 998.5, # low pressure cyclone depression
        "wind_speed": 35.0,
        "rainfall_lag1": 80.0,
        "rainfall_lag2": 45.0,
        "rainfall_roll3_sum": 125.0,
        "rainfall_roll7_sum": 290.0,
        "month": 7
    }
    result = predictor.predict_and_explain(high_rain_query)
    print("=== HIGH RAIN PREDICTION TEST ===")
    print(f"Matched Station: {result['matched_region']} ({result['distance_km']} km away)")
    print(f"Probability: {result['probability_pct']}")
    print(f"Risk Level: {result['risk_level']} ({result['imd_category']})")
    print(f"Summary: {result['plain_language_summary']}")
