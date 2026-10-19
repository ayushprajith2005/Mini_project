# 🌧️ RainXplain: Explainable AI (XAI) System for Heavy Rain Event Prediction

> **SDG 9: Industry, Innovation & Infrastructure** — Building climate-resilient early warning systems with glass-box Explainable AI (SHAP + LIME) for extreme rainfall and urban flood risk mitigation.

---

## 📌 Project Overview
**RainXplain** is a production-grade Explainable AI (XAI) meteorological forecasting system designed to predict high-impact heavy rainfall events across India according to official **India Meteorological Department (IMD)** thresholds:
- **Heavy Rain**: $\ge 64.5 \text{ mm / 24 hr}$ (Orange Alert)
- **Very Heavy Rain**: $\ge 115.6 \text{ mm / 24 hr}$ (Red Alert)
- **Extremely Heavy Rain**: $\ge 204.5 \text{ mm / 24 hr}$ (Extreme Contingency)

Traditional weather forecasting often relies on complex numerical weather prediction (NWP) simulations or opaque deep learning models that fail to explain *why* an extreme alert was triggered. RainXplain bridges this gap by combining **gradient boosted decision trees (XGBoost)** with **Shapley Additive Explanations (SHAP)** and **Local Interpretable Model-agnostic Explanations (LIME)**, presented through a web app built with Vite + React and an India-only map.

---

## 🌟 Upgraded System Features

### Core Required Features
1. **Model Trust / Performance Panel**:
   - Live interactive ROC curve and confusion matrix computed from time-aware test set (2024-2025).
   - Global SHAP feature importance rankings across test samples.
   - Key evaluation metric cards (Precision, Recall, F1, ROC-AUC, Accuracy).
   - Pre-computed saved artifacts in `models/metrics/` loaded dynamically without retraining.
2. **Automated Risk Alerting**:
   - `smtplib`-based email notification engine with graceful console/DB fallback logging.
   - SQLite subscription registry (`subscriptions` table) and an email-alert sign-up on the Predict screen for any Indian region.
   - Background APScheduler task re-evaluating active region subscriptions every hour.
   - Audited alert history logged to `alerts_sent` table and exposed via `GET /alerts/recent`.
3. **Prediction Confidence & Anomaly Flagging**:
   - Spatial distance anomaly warning when clicked coordinates are $> 50 \text{ km}$ from known met stations.
   - Model probability decision boundary uncertainty flag (when probability is within margin $[0.25, 0.45]$ of $0.35$ threshold).
   - Prominently rendered warning badges in UI and returned in API responses as `confidence_flags`.
4. **Downloadable PDF Executive Report**:
   - Single-page ReportLab PDF generation containing target location, risk tier, confidence flags, SHAP feature attribution table, and plain-language meteorological insight.
   - "Download PDF" button on the result panel, backed by `POST /report/from-result` and `GET /report/{prediction_id}`.

### Stretch Features Status
5. **Multi-Day Rolling Forecast (Completed)**:
   - 5-day forward recursive risk trend estimation using lag-feature statistical updating.
   - 5-day outlook chart in the web app labeled as recursive statistical estimate.
6. **SHAP vs LIME Comparison View (Completed)**:
   - Side-by-side comparison matrix showing top SHAP drivers vs LIME decision rules.
   - Automated synthesis note detailing feature consensus vs divergence.
7. **Impact Estimation Layer (Completed)**:
   - Static Indian state population density dataset join (`src/impact.py`).
   - Evaluates urban flood vulnerability and displays localized infrastructure risk recommendations.
8. **Admin Analytics & Governance Screen (Completed)**:
   - Login is checked by the API (`POST /admin/login`), which issues a token for `GET /admin/overview`. Credentials never ship in the browser bundle.
   - Shows total predictions logged, risk level distribution, a map of queried regions, and the alert history log.

---

## ⚙️ Environment Variables & Configuration

Configure the following environment variables (or set them in `.env`) for customized alerting and administration:

| Environment Variable | Default | Purpose |
|---|---|---|
| `SMTP_HOST` | *(None)* | SMTP server hostname for live email alerts (e.g. `smtp.gmail.com`). |
| `SMTP_PORT` | `587` | SMTP server port. |
| `SMTP_USER` | *(None)* | SMTP login username. |
| `SMTP_PASS` | *(None)* | SMTP password / App Password. |
| `ALERT_FROM_EMAIL` | `alerts@rainxplain.org` | Sender address for email alerts. |
| `ADMIN_USER` | `admin` | Username for the Admin screen login (checked by the API). |
| `ADMIN_PASSWORD` | `rainxplain123` | Password for the Admin screen login (checked by the API). |

*Note: If no SMTP credentials are provided, alerting operates in log-based fallback mode without breaking.*

---

## 🏗️ Architecture & Interaction Flow

```
+-------------------------------------------------------------------------------+
|                    Vite + React Frontend (frontend/)                          |
|  - India-Restricted Leaflet Map (Lat 6-38N, Lon 68-98E)                       |
|  - Click-to-Autofill Station Baseline (Haversine BallTree)                    |
|  - Parameter Simulation & Scenario Presets (Mumbai, Cherrapunji, Delhi, etc.) |
|  - SHAP Key-Factor Chart, SHAP vs LIME Comparison, 5-Day Outlook              |
+-------------------------------------------------------------------------------+
                                      │
                                      ▼ HTTP REST
+-------------------------------------------------------------------------------+
|                             FastAPI Backend Service                           |
|  - POST /predict    : Fast inference & risk classification                    |
|  - POST /explain    : Full inference + SHAP TreeExplainer + LIME surrogate    |
|  - POST /match-geo  : O(log N) nearest-station coordinate resolution          |
|  - POST /forecast/multi-day : 5-day recursive risk outlook                     |
|  - GET  /predictions/recent : Paginated audit trail retrieval                 |
|  - GET  /metrics/performance : ROC, confusion matrix, global SHAP             |
|  - POST /report/from-result : PDF for a result the client already holds       |
|  - POST /admin/login, GET /admin/overview : Admin screen (token protected)    |
+-------------------------------------------------------------------------------+
         │                                               │
         ▼ (Inference & Attribution)                     ▼ (Audit Persistence)
+------------------------------------+          +-------------------------------+
|       Core ML / XAI Engine         |          |       SQLite Audit Log        |
|  - XGBoost Heavy-Rain Classifier   |          |  - Location, Features, Probs  |
|  - SHAP TreeExplainer              |          |  - Top SHAP Risk Drivers      |
|  - LIME Tabular Explainer          |          |  - Plain-Language Summaries   |
|  - Spatial BallTree Index (406 Stn)|          |    (data/predictions.db)      |
+------------------------------------+          +-------------------------------+
```

---

## 📊 Data Strategy & Audit Justification

The system processes 6 raw meteorological and satellite datasets:

| Dataset | Records | Role in RainXplain | Strategy Justification |
|---|---|---|---|
| **India Weather & Rainfall (2015-2025)** | **970,339** | **Primary Training Dataset** | 10-year daily resolution across 406 distinct IMD weather stations in all 32 Indian States with exact Latitude/Longitude, pressure, temp, wind, and rainfall ground truth. |
| **Indian Climate Dataset (2024-2025)** | 7,310 | Atmospheric Enrichment | Daily Relative Humidity, Cloud Cover %, AQI, and Pressure across 10 Indian Metros. |
| **Rainfall in India (1901-2015)** | 4,116 | Historical Climatology | 115-year historical monthly subdivision normals used for baseline climatological anomaly calculation. |
| **District-Wise Rainfall Normal** | 641 | Geographic Reference | Normal rainfall baselines across 637 districts in 35 States/UTs. |
| **Sub-Division IMD 2017** | 4,188 | Validation Benchmark | IMD subdivision seasonal rainfall indices (JF, MAM, JJAS, OND). |
| **RainCast Telemetry (train.parquet)** | 420,000 | Complementary Track C | Satellite Earth-Space communication telemetry (10-30 GHz carrier SNR, rain attenuation `excess_attenuation_db`). Documented as Track C satellite link degradation analysis. |

### Geocoding & Spatial Nearest-Neighbor Strategy
- All 406 weather stations across India were aggregated with exact coordinates:
  $$\text{Latitude: } 8.3^\circ\text{N to } 34.5^\circ\text{N}, \quad \text{Longitude: } 69.0^\circ\text{E to } 95.5^\circ\text{E}$$
- An exact **BallTree spatial index with Haversine metric** is pre-computed and stored in `data/processed/region_lookup.parquet`.
- Any user click on the interactive map performs an $O(\log N)$ spatial lookup returning the station name, distance in kilometers, and climatological baseline parameters.

---

## 🤖 Model Performance & Evaluation

The classification engine uses a **time-aware chronological split** to prevent data leakage:
- **Training Set (2015–2022)**: 398,697 samples (6,018 heavy rain events)
- **Validation Set (2023)**: 149,786 samples (911 heavy rain events)
- **Test Set (2024–2025)**: 164,302 samples (1,133 heavy rain events)

### Key Metrics on Unseen 2024-2025 Test Set:
- **Test ROC-AUC**: `0.9688`
- **Heavy Rain Recall (Tuned @ 0.35 threshold)**: `77.41%` (Catches 877 of 1,133 severe events)
- **Overall Accuracy**: `97.82%`
- **Class Imbalance Handling**: Applied `scale_pos_weight = 32.63` within XGBoost to penalize missed extreme events far more severely than false alarms.

---

## 🔍 Explainability Engine (XAI)

Every prediction is paired with two distinct levels of interpretation:
1. **SHAP (Shapley Additive Explanations)**:
   - Evaluates exact game-theoretic marginal contributions of each meteorological variable (e.g., 7-day antecedent rainfall, pressure drop, relative humidity proxy, elevation).
   - Generates local waterfall plots and directional risk attributions.
2. **LIME (Local Interpretable Model-agnostic Explanations)**:
   - Builds local sparse linear surrogate models around the query point to cross-validate feature thresholds.
3. **Plain-Language Synthesis**:
   - Converts numeric attribution vectors into human-interpretable domain summaries (e.g., *"Heavy rain risk is primarily driven by: High Antecedent Moisture Accumulation (160mm) and Barometric Depression Drop (-6.2 hPa)."*)

---

## 🖥️ Web App

The frontend lives in `frontend/` (Vite + React, plain JavaScript, Leaflet for the map). It is a single-page app with a side navigation:

| Screen | What it does |
|---|---|
| **Predict** | Pick a location on the India map, set the weather conditions (or start from a scenario like *Mumbai storm*), and run a prediction. The result shows the probability against the 35% alert threshold, the estimated impact, and a "Why the model says this" panel with **Key factors** (SHAP), **SHAP vs LIME**, and a **5-day outlook**. Results can be downloaded as a PDF. |
| **Prediction log** | Every prediction saved by the API, with search by station and a risk-level filter. |
| **Model performance** | Plain-language summary of the test results, ROC curve, confusion matrix, and global feature importance. |
| **About** | What the system does, why explanations matter, and how locations are matched. |
| **Admin** | Login-protected usage stats, risk distribution, map of queried regions, and sent alerts. |

**How it talks to the API:** the browser calls `/api/*`. In development, Vite forwards that to the FastAPI service (`API_URL`, default `http://127.0.0.1:8000`). In Docker, nginx does the same forwarding. To call a differently hosted API directly, build with `VITE_API_URL` set.

**Map tiles:** Esri Light Gray Canvas (free, no API key). Change them in `frontend/src/tiles.js`.

**Build for production:**
```bash
cd frontend
npm run build        # outputs frontend/dist
```

---

## 🚀 Quickstart Guide

### Method A: Running with Pip / Local Environment

1. **Clone & Setup Environment**:
   ```bash
   git clone <repo_url>
   cd Mini_project
   pip install -r requirements.txt
   ```

2. **Step Zero Data Audit & Preprocessing** (Already generated):
   ```bash
   python src/data_audit.py
   python src/data_loader.py
   python src/features.py
   ```

3. **Train XGBoost Models & Log to MLflow**:
   ```bash
   python src/train.py
   ```

4. **Launch the FastAPI Backend Service**:
   ```bash
   uvicorn api.main:app --host 127.0.0.1 --port 8000
   ```

5. **Launch the Web App (Vite + React)**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Requires Node 18 or newer. Open your browser at `http://localhost:5173`. The dev server forwards `/api/*` to the FastAPI
   service on port 8000 (set `API_URL` to point it elsewhere).

6. **Run Unit & Integration Tests**:
   ```bash
   python -m pytest -v
   ```

---

### Method B: Running with Docker & Docker-Compose

To launch the FastAPI service and the web app (nginx serving the Vite build) in isolated network containers:
```bash
docker-compose up --build
```
- **Web app**: `http://localhost:8080`
- **FastAPI Documentation / Swagger**: `http://localhost:8000/docs`

---

## 🛰️ Integration Guide: Real Satellite & Live Weather APIs

To connect RainXplain with live Earth Observation satellite streams or real-time NWP feeds:

### 1. ISRO MOSDAC / INSAT-3D / 3DR Imager
- **Variables**: Cloud Top Brightness Temperature (TBB), Hydro-Estimator Precipitation (HEM), Quantitative Precipitation Estimation (QPE).
- **Integration**: In `src/features.py`, ingest MOSDAC HDF5/NetCDF files and map the INSAT pixel grid to station coordinates via `scipy.spatial.cKDTree`.

### 2. NASA GPM-IMERG (Global Precipitation Measurement)
- **Variables**: Multi-satellite precipitation calibrated with gauge analysis (Early / Late Run).
- **Integration**: Query the NASA Earthdata API (`https://gpm1.gesdisc.eosdis.nasa.gov/opendap/`) for real-time 30-minute rain rates and feed as `rainfall_lag1` and `rainfall_roll3_sum`.

### 3. ECMWF ERA5 Reanalysis / Open-Meteo API
- **Variables**: Mean Sea Level Pressure (MSLP), 2m Dewpoint Temperature, Convective Available Potential Energy (CAPE).
- **Integration**: In `api/main.py`, substitute the static `region_lookup` fallback with an HTTP request to `https://api.open-meteo.com/v1/forecast` using the clicked `(lat, lon)`.

---

## 📁 Repository Structure
```
Mini_project/
├── api/
│   ├── main.py                # FastAPI REST API endpoints
│   ├── db.py                  # SQLite logging and audit query helper
│   ├── alerts.py              # Email alert scheduler
│   └── report.py              # PDF report generation
├── frontend/                  # Vite + React web app
│   ├── src/pages/             # Predict, Prediction log, Model performance, About, Admin
│   ├── src/components/        # Map, conditions form, result panel, shared UI
│   ├── src/api.js             # All calls to the FastAPI service
│   ├── src/index.css          # Design tokens and layout
│   ├── vite.config.js         # Dev server and /api proxy
│   └── nginx.conf             # Serves the build and proxies /api to FastAPI
├── data/
│   ├── raw/                   # Original 6 CSVs/Parquet datasets
│   └── processed/             # Cleaned Parquet data & region_lookup table
├── models/
│   ├── xgboost_heavy_rain.json# Trained XGBoost binary model
│   ├── xgboost_multiclass.json# Trained multi-class risk model
│   ├── feature_metadata.json  # Feature schema and test evaluation metrics
│   └── shap_background.parquet# Calibration samples for SHAP/LIME
├── src/
│   ├── data_audit.py          # Step Zero: deep dataset audit script
│   ├── data_loader.py         # Data loading, target engineering, lookup builder
│   ├── features.py            # Meteorological proxy formulas & lag engineering
│   ├── geo_match.py           # Spatial BallTree nearest-neighbor indexer
│   ├── train.py               # Time-aware split, XGBoost training, MLflow logging
│   ├── explain.py             # SHAP & LIME explanation generators
│   └── predict.py             # Predict & explain orchestration pipeline
├── tests/
│   ├── test_data_loader.py    # Tests for dataset schemas & targets
│   ├── test_geo_match.py      # Tests for spatial coordinate matching
│   ├── test_train.py          # Smoke tests for model artifacts & outputs
│   └── test_predict.py        # Unit tests for predict_and_explain API
├── Dockerfile.api             # Container definition for FastAPI service
├── Dockerfile.frontend        # Container definition for the Vite web app
├── docker-compose.yml         # Multi-container orchestration
├── requirements.txt           # Pinned Python package dependencies
└── README.md                  # System documentation & technical spec
```

---

## 📄 License & SDG Attribution
This project is developed under **UN Sustainable Development Goal 9 (Industry, Innovation & Infrastructure)** to foster open-source disaster resilience technologies.
