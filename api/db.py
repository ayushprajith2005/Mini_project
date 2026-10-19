"""
SQLite Persistence and Audit Logging Helper for RainXplain.
Logs every prediction and explanation query with timestamp, coordinates,
matched station, input features, probabilities, and top SHAP drivers.
"""
import os
import json
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "predictions.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        matched_region TEXT,
        distance_km REAL,
        input_features TEXT,
        prediction INTEGER NOT NULL,
        probability REAL NOT NULL,
        risk_level TEXT NOT NULL,
        imd_category TEXT NOT NULL,
        top_shap_factors TEXT,
        plain_language_summary TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        region_or_latlon TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts_sent (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        subscription_id INTEGER,
        email TEXT NOT NULL,
        region TEXT,
        risk_level TEXT NOT NULL,
        probability REAL NOT NULL
    )
    """)
    conn.commit()
    conn.close()

def log_prediction_event(
    latitude: float,
    longitude: float,
    matched_region: str,
    distance_km: float,
    input_features: dict,
    prediction: int,
    probability: float,
    risk_level: str,
    imd_category: str,
    top_shap_factors: list = None,
    plain_language_summary: str = None
) -> int:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    input_json = json.dumps(input_features or {})
    shap_json = json.dumps(top_shap_factors or [])

    cursor.execute("""
    INSERT INTO predictions_log (
        timestamp, latitude, longitude, matched_region, distance_km,
        input_features, prediction, probability, risk_level, imd_category,
        top_shap_factors, plain_language_summary
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp, latitude, longitude, matched_region, distance_km,
        input_json, int(prediction), float(probability), risk_level, imd_category,
        shap_json, plain_language_summary or ""
    ))
    
    logged_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return logged_id

def get_recent_predictions(limit: int = 50, offset: int = 0) -> list:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT * FROM predictions_log
    ORDER BY id DESC
    LIMIT ? OFFSET ?
    """, (limit, offset))
    
    rows = cursor.fetchall()
    results = []
    for r in rows:
        item = dict(r)
        try:
            item["input_features"] = json.loads(item["input_features"])
        except:
            pass
        try:
            item["top_shap_factors"] = json.loads(item["top_shap_factors"])
        except:
            pass
        results.append(item)
        
    conn.close()
    return results

def get_prediction_by_id(pred_id: int) -> dict:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM predictions_log WHERE id = ?", (pred_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    item = dict(row)
    try:
        item["input_features"] = json.loads(item["input_features"])
    except:
        pass
    try:
        item["top_shap_factors"] = json.loads(item["top_shap_factors"])
    except:
        pass
    return item

def create_subscription(email: str, region_or_latlon: str, latitude: float = None, longitude: float = None) -> int:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.utcnow().isoformat() + "Z"
    cursor.execute("""
    INSERT INTO subscriptions (email, region_or_latlon, latitude, longitude, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (email, region_or_latlon, latitude, longitude, created_at))
    sub_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return sub_id

def get_all_subscriptions() -> list:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscriptions ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def log_alert_sent(subscription_id: int, email: str, region: str, risk_level: str, probability: float) -> int:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    timestamp = datetime.utcnow().isoformat() + "Z"
    cursor.execute("""
    INSERT INTO alerts_sent (timestamp, subscription_id, email, region, risk_level, probability)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, subscription_id, email, region, risk_level, float(probability)))
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id

def get_recent_alerts(limit: int = 50) -> list:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts_sent ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_db_stats() -> dict:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM predictions_log")
    total = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as heavy FROM predictions_log WHERE prediction = 1")
    heavy = cursor.fetchone()["heavy"]

    cursor.execute("SELECT COUNT(*) as subs FROM subscriptions")
    subs = cursor.fetchone()["subs"]

    cursor.execute("SELECT COUNT(*) as alerts FROM alerts_sent")
    alerts = cursor.fetchone()["alerts"]
    
    conn.close()
    return {
        "total_predictions_logged": total,
        "heavy_rain_events_logged": heavy,
        "active_subscriptions": subs,
        "alerts_sent_count": alerts
    }

if __name__ == "__main__":
    init_db()
    print(f"Initialized SQLite database at {DB_PATH}")
    stats = get_db_stats()
    print("Database stats:", stats)
