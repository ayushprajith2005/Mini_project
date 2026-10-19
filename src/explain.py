"""
Explainability Engine (XAI) for RainXplain using SHAP and LIME.
Generates local SHAP waterfall/force values, global feature rankings,
LIME tabular cross-check explanations, and human-interpretable domain summaries.
"""
import os
import sys
import json
import numpy as np
import pandas as pd
import shap
import lime
import lime.lime_tabular
import xgboost as xgb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.features import FEATURE_COLUMNS

class RainExplainer:
    def __init__(self, models_dir: str = None):
        if models_dir is None:
            models_dir = os.path.join(BASE_DIR, "models")
        
        self.models_dir = models_dir
        self.model_path = os.path.join(models_dir, "xgboost_heavy_rain.json")
        self.background_path = os.path.join(models_dir, "shap_background.parquet")
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at {self.model_path}. Run train.py first.")
        
        # Load XGBoost model
        self.model = xgb.XGBClassifier()
        self.model.load_model(self.model_path)
        
        # Load background data for explainer calibration
        if os.path.exists(self.background_path):
            self.background_df = pd.read_parquet(self.background_path)[FEATURE_COLUMNS]
        else:
            # Fallback zero-filled baseline
            self.background_df = pd.DataFrame(np.zeros((50, len(FEATURE_COLUMNS))), columns=FEATURE_COLUMNS)

        # Initialize SHAP TreeExplainer
        self.shap_explainer = shap.TreeExplainer(self.model)
        ev = self.shap_explainer.expected_value
        if isinstance(ev, (list, np.ndarray)):
            self.expected_value = float(ev[1]) if len(ev) > 1 else float(ev[0])
        else:
            self.expected_value = float(ev)

        # Initialize LIME Tabular Explainer
        self.lime_explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=self.background_df.values,
            feature_names=FEATURE_COLUMNS,
            class_names=['Normal/Light Rain', 'Heavy Rain (>=64.5mm)'],
            mode='classification',
            random_state=42
        )

    def explain_instance(self, feature_df: pd.DataFrame) -> dict:
        """
        Computes SHAP and LIME explanations for a 1-row feature DataFrame.
        Returns a comprehensive, JSON-serializable dictionary.
        """
        if isinstance(feature_df, dict):
            feature_df = pd.DataFrame([feature_df])[FEATURE_COLUMNS]
        else:
            feature_df = feature_df[FEATURE_COLUMNS]

        feature_values = feature_df.iloc[0].to_dict()
        row_values_list = feature_df.iloc[0].values.tolist()

        # 1. SHAP Computation
        shap_values_raw = self.shap_explainer.shap_values(feature_df)
        if isinstance(shap_values_raw, list):
            shap_values = shap_values_raw[1][0] # Positive class SHAP
        elif len(shap_values_raw.shape) == 2:
            shap_values = shap_values_raw[0]
        else:
            shap_values = shap_values_raw

        shap_list = []
        for feat_name, feat_val, s_val in zip(FEATURE_COLUMNS, row_values_list, shap_values):
            shap_list.append({
                "feature": feat_name,
                "value": round(float(feat_val), 4),
                "shap_value": round(float(s_val), 4),
                "impact": "INCREASES_RISK" if s_val > 0 else "DECREASES_RISK",
                "abs_importance": round(abs(float(s_val)), 4)
            })

        # Sort by absolute SHAP impact
        shap_list_sorted = sorted(shap_list, key=lambda x: x['abs_importance'], reverse=True)
        top_risk_drivers = [item for item in shap_list_sorted if item['shap_value'] > 0][:5]
        top_risk_mitigators = [item for item in shap_list_sorted if item['shap_value'] < 0][:5]

        # 2. LIME Computation
        def predict_fn(x):
            preds = self.model.predict_proba(x)
            return preds

        lime_exp = self.lime_explainer.explain_instance(
            data_row=feature_df.iloc[0].values,
            predict_fn=predict_fn,
            num_features=6
        )
        lime_list = []
        for feat_rule, weight in lime_exp.as_list():
            lime_list.append({
                "rule": feat_rule,
                "weight": round(float(weight), 4),
                "impact": "INCREASES_RISK" if weight > 0 else "DECREASES_RISK"
            })

        # 3. SHAP vs LIME Comparison Synthesis
        comparison = self._compare_shap_lime(shap_list_sorted, lime_list)

        # 4. Plain Language Natural Summary
        summary_text = self._generate_plain_language_summary(top_risk_drivers, top_risk_mitigators, feature_values)

        return {
            "base_value": round(float(self.expected_value), 4),
            "shap_explanation": shap_list_sorted,
            "top_contributing_factors": top_risk_drivers,
            "top_mitigating_factors": top_risk_mitigators,
            "lime_explanation": lime_list,
            "shap_lime_comparison": comparison,
            "plain_language_summary": summary_text
        }

    def _compare_shap_lime(self, shap_sorted: list, lime_rules: list) -> dict:
        """Compares top SHAP feature attributions with LIME local rule weights."""
        top_shap_feats = [item['feature'] for item in shap_sorted[:3]]

        top_lime_feats = []
        for l in lime_rules[:4]:
            rule_str = l['rule']
            for feat in FEATURE_COLUMNS:
                if feat in rule_str and feat not in top_lime_feats:
                    top_lime_feats.append(feat)

        agreements = [f for f in top_shap_feats if f in top_lime_feats]
        shap_only = [f for f in top_shap_feats if f not in top_lime_feats]
        lime_only = [f for f in top_lime_feats if f not in top_shap_feats]

        if agreements:
            note = f"High Consensus: Both SHAP and LIME agree that {', '.join(agreements)} are key decision drivers."
            if shap_only or lime_only:
                note += f" SHAP emphasizes {', '.join(shap_only) if shap_only else 'no extra features'}, while LIME rules focus on {', '.join(lime_only) if lime_only else 'no extra features'}."
        else:
            note = f"Divergence: SHAP prioritizes {', '.join(top_shap_feats[:2])} whereas LIME rules focus on {', '.join(top_lime_feats[:2])}."

        return {
            "top_shap_features": top_shap_feats,
            "top_lime_features": top_lime_feats,
            "agreements": agreements,
            "shap_only": shap_only,
            "lime_only": lime_only,
            "comparison_note": note
        }

    def _generate_plain_language_summary(self, drivers: list, mitigators: list, feat_values: dict) -> str:
        """Translates top SHAP drivers into human meteorologist terms."""
        reasons = []
        
        feature_friendly_names = {
            'relative_humidity_est': 'High Atmospheric Humidity',
            'rainfall_roll7_sum': 'Sustained 7-Day Antecedent Rainfall',
            'rainfall_roll3_sum': '3-Day Moisture Accumulation',
            'rainfall_lag1': 'Heavy Precipitation Yesterday',
            'pressure_drop_3d': 'Barometric Pressure Drop (Low-Pressure Depression)',
            'air_pressure': 'Low Surface Air Pressure',
            'is_monsoon': 'Peak Southwest Monsoon Season',
            'wind_speed': 'High Wind Velocity',
            'temp_range': 'Narrow Diurnal Temperature Range (Dense Cloud Cover)',
            'vapor_pressure_deficit': 'Near-Zero Vapor Pressure Deficit (Saturated Air Column)',
            'elevation': 'Orograhic Lift Factor (Elevation)',
            'avg_temp': 'Elevated Convective Thermal Energy'
        }

        if drivers:
            top_factors = []
            for d in drivers[:3]:
                fname = feature_friendly_names.get(d['feature'], d['feature'])
                top_factors.append(f"{fname} (value: {d['value']})")
            reasons.append(f"Heavy rain risk is primarily driven by: {', '.join(top_factors)}.")
        else:
            reasons.append("Atmospheric indicators are within stable, dry thresholds.")

        if mitigators:
            top_mit = [feature_friendly_names.get(m['feature'], m['feature']) for m in mitigators[:2]]
            reasons.append(f"Risk is counteracted by favorable factors: {', '.join(top_mit)}.")

        return " ".join(reasons)

# Cached singleton instance
_explainer_instance = None

def get_explainer() -> RainExplainer:
    global _explainer_instance
    if _explainer_instance is None:
        _explainer_instance = RainExplainer()
    return _explainer_instance

if __name__ == "__main__":
    from src.features import extract_single_feature_vector
    explainer = RainExplainer()
    sample_input = {
        "avg_temp": 27.5,
        "min_temp": 25.0,
        "max_temp": 29.0,
        "air_pressure": 1002.0,
        "wind_speed": 22.0,
        "elevation": 15.0,
        "latitude": 19.07,
        "longitude": 72.87,
        "rainfall_lag1": 45.0,
        "rainfall_lag2": 30.0,
        "rainfall_roll3_sum": 75.0,
        "rainfall_roll7_sum": 160.0,
        "month": 7
    }
    vec = extract_single_feature_vector(sample_input)
    res = explainer.explain_instance(vec)
    print("\nSHAP Top Factors:")
    for f in res['top_contributing_factors']:
        print(f"  {f['feature']:<25}: SHAP={f['shap_value']:+.4f} (val={f['value']})")
    print("\nLIME Rules:")
    for l in res['lime_explanation']:
        print(f"  {l['rule']:<35}: Weight={l['weight']:+.4f}")
    print(f"\nPlain Language Summary:\n  {res['plain_language_summary']}")
