"""
Model Training and Evaluation Pipeline for RainXplain.
Uses time-aware train/val/test splitting, XGBoost with class-imbalance weighting,
comprehensive classification metrics (emphasizing recall for heavy rain), MLflow logging,
and model artifact serialization.
"""
import os
import sys
import json
import numpy as np
import pandas as pd

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import joblib
import xgboost as xgb
import mlflow
import mlflow.xgboost
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, classification_report, confusion_matrix, roc_curve
)
import shap
from src.features import FEATURE_COLUMNS

def load_featured_data(base_dir: str) -> pd.DataFrame:
    data_path = os.path.join(base_dir, "data", "processed", "featured_weather_data.parquet")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"{data_path} not found. Run features.py first.")
    df = pd.read_parquet(data_path)
    df['date_of_record'] = pd.to_datetime(df['date_of_record'])
    return df

def time_aware_split(df: pd.DataFrame):
    """
    Time-aware train/val/test split:
      - Train: records before 2023 (< 2023-01-01)
      - Validation: 2023 (2023-01-01 to 2023-12-31)
      - Test: 2024 to 2025 (>= 2024-01-01)
    """
    train_mask = df['date_of_record'] < '2023-01-01'
    val_mask = (df['date_of_record'] >= '2023-01-01') & (df['date_of_record'] < '2024-01-01')
    test_mask = df['date_of_record'] >= '2024-01-01'

    X_train = df.loc[train_mask, FEATURE_COLUMNS]
    y_train = df.loc[train_mask, 'heavy_rain_event']
    y_train_multi = df.loc[train_mask, 'risk_class']

    X_val = df.loc[val_mask, FEATURE_COLUMNS]
    y_val = df.loc[val_mask, 'heavy_rain_event']
    y_val_multi = df.loc[val_mask, 'risk_class']

    X_test = df.loc[test_mask, FEATURE_COLUMNS]
    y_test = df.loc[test_mask, 'heavy_rain_event']
    y_test_multi = df.loc[test_mask, 'risk_class']

    print(f"Time-aware Split Summary:")
    print(f"  Train (2015-2022): {len(X_train):,} samples, {y_train.sum():,} heavy rain ({y_train.mean()*100:.2f}%)")
    print(f"  Val   (2023):      {len(X_val):,} samples, {y_val.sum():,} heavy rain ({y_val.mean()*100:.2f}%)")
    print(f"  Test  (2024-2025): {len(X_test):,} samples, {y_test.sum():,} heavy rain ({y_test.mean()*100:.2f}%)")

    return (X_train, y_train, y_train_multi), (X_val, y_val, y_val_multi), (X_test, y_test, y_test_multi)

def train_and_evaluate(experiment_name: str = "RainXplain_HeavyRain_Prediction"):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(base_dir, "models")
    os.makedirs(models_dir, exist_ok=True)

    df = load_featured_data(base_dir)
    (X_train, y_train, y_train_multi), (X_val, y_val, y_val_multi), (X_test, y_test, y_test_multi) = time_aware_split(df)

    # Calculate scale_pos_weight to prioritize heavy-rain recall
    pos_count = y_train.sum()
    neg_count = len(y_train) - pos_count
    # Set effective scale_pos_weight with balance to avoid excessive false positives
    scale_pos_weight = float(neg_count / max(pos_count, 1)) * 0.5
    print(f"Computed scale_pos_weight: {scale_pos_weight:.2f}")

    # Set up MLflow with SQLite backend
    db_path = os.path.join(base_dir, "mlflow.db").replace(os.sep, "/")
    mlflow.set_tracking_uri(f"sqlite:///{db_path}")
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name="XGBoost_HeavyRain_Classifier"):
        # Model Hyperparameters
        params = {
            'n_estimators': 300,
            'max_depth': 6,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'scale_pos_weight': scale_pos_weight,
            'random_state': 42,
            'eval_metric': 'logloss',
            'tree_method': 'hist',
            'early_stopping_rounds': 30
        }
        mlflow.log_params(params)

        print("\nTraining XGBoost Binary Heavy-Rain Model...")
        model = xgb.XGBClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=50
        )

        # Predictions on Test Set
        y_test_pred_prob = model.predict_proba(X_test)[:, 1]
        
        # Test evaluation with standard 0.5 threshold and recall-tuned 0.35 threshold
        y_test_pred = (y_test_pred_prob >= 0.5).astype(int)
        y_test_pred_tuned = (y_test_pred_prob >= 0.35).astype(int)

        acc = accuracy_score(y_test, y_test_pred)
        prec = precision_score(y_test, y_test_pred, zero_division=0)
        rec = recall_score(y_test, y_test_pred, zero_division=0)
        f1 = f1_score(y_test, y_test_pred, zero_division=0)
        roc_auc = roc_auc_score(y_test, y_test_pred_prob)
        pr_auc = average_precision_score(y_test, y_test_pred_prob)

        rec_tuned = recall_score(y_test, y_test_pred_tuned, zero_division=0)
        f1_tuned = f1_score(y_test, y_test_pred_tuned, zero_division=0)

        metrics = {
            'test_accuracy': float(acc),
            'test_precision': float(prec),
            'test_recall': float(rec),
            'test_f1': float(f1),
            'test_roc_auc': float(roc_auc),
            'test_pr_auc': float(pr_auc),
            'test_recall_tuned_0.35': float(rec_tuned),
            'test_f1_tuned_0.35': float(f1_tuned)
        }
        mlflow.log_metrics(metrics)

        print("\n" + "=" * 60)
        print("TEST SET EVALUATION RESULTS (XGBoost Heavy Rain)")
        print("=" * 60)
        for k, v in metrics.items():
            print(f"  {k:<25}: {v:.4f}")

        print("\nConfusion Matrix (Threshold 0.5):")
        cm = confusion_matrix(y_test, y_test_pred)
        print(cm)
        print("\nClassification Report:")
        print(classification_report(y_test, y_test_pred, target_names=['Normal/Light', 'Heavy Rain (>=64.5mm)']))

        # Train Multi-class Model for risk tier estimation (0: None, 1: Heavy, 2: Very Heavy)
        print("\nTraining Multi-Class Risk Tier Model...")
        multi_params = {
            'n_estimators': 200,
            'max_depth': 5,
            'learning_rate': 0.05,
            'objective': 'multi:softprob',
            'num_class': 3,
            'random_state': 42,
            'tree_method': 'hist'
        }
        model_multi = xgb.XGBClassifier(**multi_params)
        model_multi.fit(X_train, y_train_multi)

        # Save model artifacts
        model_path_json = os.path.join(models_dir, "xgboost_heavy_rain.json")
        model_multi_path_json = os.path.join(models_dir, "xgboost_multiclass.json")
        meta_path = os.path.join(models_dir, "feature_metadata.json")

        model.save_model(model_path_json)
        model_multi.save_model(model_multi_path_json)

        # Save feature metadata & sample background data for SHAP
        metadata = {
            "feature_columns": FEATURE_COLUMNS,
            "threshold_heavy_mm": 64.5,
            "threshold_very_heavy_mm": 115.6,
            "metrics": metrics,
            "scale_pos_weight": scale_pos_weight
        }
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Save small background dataset sample (100 samples) for SHAP TreeExplainer initialization
        background_sample = X_train.sample(n=min(200, len(X_train)), random_state=42)
        background_path = os.path.join(models_dir, "shap_background.parquet")
        background_sample.to_parquet(background_path, index=False)

        # Save detailed performance metrics artifacts
        metrics_dir = os.path.join(models_dir, "metrics")
        os.makedirs(metrics_dir, exist_ok=True)

        # ROC Curve
        fpr, tpr, roc_thresholds = roc_curve(y_test, y_test_pred_prob)
        # Subsample ROC curve points to keep JSON lightweight
        step = max(1, len(fpr) // 100)
        roc_data = {
            "fpr": [round(float(val), 5) for val in fpr[::step]],
            "tpr": [round(float(val), 5) for val in tpr[::step]],
            "roc_auc": round(float(roc_auc), 4)
        }
        with open(os.path.join(metrics_dir, "roc_curve.json"), "w") as f:
            json.dump(roc_data, f, indent=2)

        # Confusion Matrix
        cm_data = {
            "matrix": cm.tolist(),
            "labels": ["Normal/Light", "Heavy Rain (>=64.5mm)"],
            "threshold": 0.5
        }
        with open(os.path.join(metrics_dir, "confusion_matrix.json"), "w") as f:
            json.dump(cm_data, f, indent=2)

        # Global SHAP feature importance
        print("\nComputing Global SHAP Feature Importance across test sample...")
        explainer_shap = shap.TreeExplainer(model)
        test_sample = X_test.sample(n=min(300, len(X_test)), random_state=42)
        shap_vals_raw = explainer_shap.shap_values(test_sample)
        if isinstance(shap_vals_raw, list):
            shap_vals = shap_vals_raw[1]
        else:
            shap_vals = shap_vals_raw
        
        mean_abs_shap = np.abs(shap_vals).mean(axis=0)
        global_shap_data = []
        for feat_name, mean_val in zip(FEATURE_COLUMNS, mean_abs_shap):
            global_shap_data.append({
                "feature": feat_name,
                "mean_abs_shap": round(float(mean_val), 4)
            })
        global_shap_data = sorted(global_shap_data, key=lambda x: x['mean_abs_shap'], reverse=True)
        with open(os.path.join(metrics_dir, "global_shap.json"), "w") as f:
            json.dump(global_shap_data, f, indent=2)

        # Metrics summary
        with open(os.path.join(metrics_dir, "metrics.json"), "w") as f:
            json.dump(metrics, f, indent=2)

        print(f"\nSaved models and metadata to {models_dir}/ and {metrics_dir}/")
        print(f"  Binary model: {model_path_json}")
        print(f"  Multi-class model: {model_multi_path_json}")
        print(f"  Metadata: {meta_path}")

    return metrics

if __name__ == "__main__":
    train_and_evaluate()
