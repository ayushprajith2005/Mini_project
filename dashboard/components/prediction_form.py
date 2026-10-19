"""Preset scenario buttons + weather parameter form (Tab 1, right column)."""
import streamlit as st

from api_client import call_geo_match, call_explain_api

PRESETS = [
    {
        "label": "🌧️ Mumbai Storm",
        "lat": 19.0760, "lon": 72.8777,
        "lag1": 95.0, "pressure": 998.0, "wind": 32.0, "month": 7,
    },
    {
        "label": "🌊 Cherrapunji",
        "lat": 25.2986, "lon": 91.5822,
        "lag1": 180.0, "pressure": 992.0, "wind": 25.0, "month": 6,
    },
    {
        "label": "☀️ Delhi Dry",
        "lat": 28.6139, "lon": 77.2090,
        "lag1": 0.0, "pressure": 1014.0, "wind": 6.0, "month": 1,
    },
    {
        "label": "🌀 Chennai OND",
        "lat": 13.0827, "lon": 80.2707,
        "lag1": 70.0, "pressure": 1001.0, "wind": 28.0, "month": 11,
    },
]


def _apply_preset(preset):
    st.session_state.selected_lat = preset["lat"]
    st.session_state.selected_lon = preset["lon"]
    st.session_state.matched_data = call_geo_match(preset["lat"], preset["lon"])
    st.session_state.override_lag1 = preset["lag1"]
    st.session_state.override_pressure = preset["pressure"]
    st.session_state.override_wind = preset["wind"]
    st.session_state.override_month = preset["month"]
    st.rerun()


def render_prediction_form():
    st.markdown("### ⚙️ Weather Parameters & Simulation")

    matched = st.session_state.matched_data or {}

    st.markdown("**Quick Preset Scenarios:**")
    preset_cols = st.columns(4)
    for col, preset in zip(preset_cols, PRESETS):
        if col.button(preset["label"], width='stretch'):
            _apply_preset(preset)

    with st.form("prediction_form"):
        c1, c2 = st.columns(2)
        with c1:
            avg_temp = st.number_input("Average Temp (°C)", value=float(matched.get("avg_temp", 28.0)), step=0.5)
            min_temp = st.number_input("Min Temp (°C)", value=float(matched.get("min_temp", 23.5)), step=0.5)
            max_temp = st.number_input("Max Temp (°C)", value=float(matched.get("max_temp", 33.0)), step=0.5)
            air_pressure = st.number_input("Surface Pressure (hPa)", value=float(st.session_state.get("override_pressure", matched.get("air_pressure", 1008.0))), step=1.0)
        with c2:
            wind_speed = st.number_input("Wind Speed (km/h)", value=float(st.session_state.get("override_wind", matched.get("wind_speed", 10.0))), step=1.0)
            rainfall_lag1 = st.number_input("Rainfall Yesterday (mm)", value=float(st.session_state.get("override_lag1", 5.0)), step=5.0)
            rainfall_roll7 = st.number_input("7-Day Antecedent Rain (mm)", value=float(rainfall_lag1 * 2.5), step=10.0)
            month = st.selectbox("Month of Event", options=list(range(1, 13)), index=int(st.session_state.get("override_month", 7)) - 1, format_func=lambda m: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m-1])

        with st.expander("🛠️ Advanced Meteorological & Terrain Overrides"):
            elevation = st.number_input("Elevation (m)", value=float(matched.get("elevation", 100.0)), step=10.0)
            rainfall_lag2 = st.number_input("Rainfall 2-Days Ago (mm)", value=float(rainfall_lag1 * 0.5), step=5.0)
            rainfall_roll3 = st.number_input("3-Day Antecedent Rain (mm)", value=float(rainfall_lag1 + rainfall_lag2), step=5.0)

        submit_predict = st.form_submit_button("⚡ Run Explainable Prediction (SHAP + LIME)", width='stretch', type="primary")

    if submit_predict:
        payload = {
            "latitude": st.session_state.selected_lat,
            "longitude": st.session_state.selected_lon,
            "avg_temp": avg_temp,
            "min_temp": min_temp,
            "max_temp": max_temp,
            "air_pressure": air_pressure,
            "wind_speed": wind_speed,
            "elevation": elevation,
            "rainfall_lag1": rainfall_lag1,
            "rainfall_lag2": rainfall_lag2,
            "rainfall_roll3_sum": rainfall_roll3,
            "rainfall_roll7_sum": rainfall_roll7,
            "month": month
        }
        with st.spinner("Executing XGBoost Inference & Generating SHAP/LIME Explanations..."):
            res = call_explain_api(payload)
            st.session_state.prediction_result = res
