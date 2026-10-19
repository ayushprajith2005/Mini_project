"""
RainXplain Interactive Streamlit Dashboard.
Features an interactive India-restricted Folium map, click-to-autofill spatial matching,
real-time Explainable AI (SHAP + LIME), Model Performance Panel (ROC/CM/Global SHAP),
Automated Risk Alerting, Confidence Flags, downloadable PDF reports, and Admin Analytics.
"""
import os
import sys

import streamlit as st

# Ensure project root and this dashboard/ directory are both on sys.path, so
# `api.*` / `src.*` imports resolve and sibling modules (styles, api_client,
# components.*) are importable regardless of how the script is launched.
DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(DASHBOARD_DIR)
for _p in (BASE_DIR, DASHBOARD_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from styles import inject_css, render_header
from components.map_panel import render_map_panel
from components.prediction_form import render_prediction_form
from components.results_panel import render_results_panel
from components.audit_log import render_audit_log
from components.performance_panel import render_performance_panel
from components.sdg_info import render_sdg_info
from components.admin_panel import render_admin_panel

st.set_page_config(
    page_title="RainXplain | Explainable AI Heavy Rain Prediction",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_css()
render_header()

tabs = st.tabs([
    "🗺️ Interactive Map & Explainable Predictor",
    "📊 Recent Predictions Log",
    "🎯 Model Performance & Metrics",
    "🌱 SDG 9 & XAI Methodology",
    "🔒 Admin Analytics & Governance"
])

with tabs[0]:
    if "selected_lat" not in st.session_state:
        st.session_state.selected_lat = 19.0760
        st.session_state.selected_lon = 72.8777
        st.session_state.matched_data = None
        st.session_state.prediction_result = None

    col_map, col_results = st.columns([1.1, 0.9], gap="large")
    with col_map:
        render_map_panel()
    with col_results:
        render_prediction_form()

    render_results_panel()

with tabs[1]:
    render_audit_log()

with tabs[2]:
    render_performance_panel()

with tabs[3]:
    render_sdg_info()

with tabs[4]:
    render_admin_panel()
