"""
Smoke tests for model artifacts and training outputs.
"""
import os
import sys
import json
import pytest
import xgboost as xgb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.features import FEATURE_COLUMNS

def test_model_artifacts_exist():
    models_dir = os.path.join(BASE_DIR, "models")
    model_path = os.path.join(models_dir, "xgboost_heavy_rain.json")
    meta_path = os.path.join(models_dir, "feature_metadata.json")
    
    assert os.path.exists(model_path), "Model JSON file must exist"
    assert os.path.exists(meta_path), "Feature metadata must exist"
    
    with open(meta_path, "r") as f:
        meta = json.load(f)
        
    assert "metrics" in meta
    assert meta["metrics"]["test_roc_auc"] > 0.85
    assert len(meta["feature_columns"]) == len(FEATURE_COLUMNS)

def test_model_inference_smoke():
    model_path = os.path.join(BASE_DIR, "models", "xgboost_heavy_rain.json")
    model = xgb.XGBClassifier()
    model.load_model(model_path)
    
    import numpy as np
    dummy_x = np.ones((2, len(FEATURE_COLUMNS)))
    preds = model.predict_proba(dummy_x)
    
    assert preds.shape == (2, 2)
    assert (preds >= 0.0).all() and (preds <= 1.0).all()
