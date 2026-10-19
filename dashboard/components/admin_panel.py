"""Admin login + governance analytics (Tab 5)."""
import os

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px

from api_client import fetch_admin_governance_data
from components.map_panel import DARK_TILES_URL, DARK_TILES_ATTR

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "rainxplain123")


def _render_login_form():
    st.caption("Restricted access for disaster management officers and system administrators.")
    with st.form("admin_login_form"):
        user = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login to Admin Console", width='stretch')

        if login_btn:
            if user == ADMIN_USER and password == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.success("Authentication successful!")
                st.rerun()
            else:
                st.error("Invalid credentials. Check ADMIN_USER / ADMIN_PASSWORD environment variables.")


def _render_governance_dashboard():
    st.sidebar.button("Logout Admin", on_click=lambda: st.session_state.update({"admin_logged_in": False}))
    st.success("Authenticated as Disaster Governance Admin")

    stats, recent_logs, alerts_sent, error = fetch_admin_governance_data()
    if error:
        st.error(f"Failed to load DB stats: {error}")

    a1, a2, a3, a4 = st.columns(4)
    with a1:
        st.metric("Total Predictions Made", stats.get("total_predictions_logged", 0))
    with a2:
        st.metric("Heavy Rain Events Logged", stats.get("heavy_rain_events_logged", 0))
    with a3:
        st.metric("Active Subscriptions", stats.get("active_subscriptions", 0))
    with a4:
        st.metric("Total Alerts Sent", stats.get("alerts_sent_count", 0))

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    if recent_logs:
        df_admin = pd.DataFrame(recent_logs)
        acol1, acol2 = st.columns(2)

        with acol1:
            st.markdown("#### Risk Level Distribution")
            if "risk_level" in df_admin.columns:
                risk_counts = df_admin["risk_level"].value_counts().reset_index()
                risk_counts.columns = ["Risk Level", "Count"]
                fig_risk = px.bar(risk_counts, x="Risk Level", y="Count", color="Risk Level", template="plotly_dark")
                st.plotly_chart(fig_risk, width='stretch')

        with acol2:
            st.markdown("#### Most Queried Regions Map")
            if "latitude" in df_admin.columns and "longitude" in df_admin.columns:
                m_admin = folium.Map(
                    location=[20.5937, 78.9629],
                    zoom_start=4,
                    tiles=DARK_TILES_URL,
                    attr=DARK_TILES_ATTR
                )
                for _, row in df_admin.dropna(subset=['latitude', 'longitude']).iterrows():
                    folium.CircleMarker(
                        location=[row['latitude'], row['longitude']],
                        radius=5,
                        color="#EF4444" if row.get("prediction") == 1 else "#38BDF8",
                        fill=True,
                        tooltip=f"{row.get('matched_region')}: {row.get('risk_level')}"
                    ).add_to(m_admin)
                st_folium(m_admin, width="100%", height=300, key="admin_map")

    if alerts_sent:
        st.markdown("#### 🚨 Sent Alerts Audit Log")
        st.dataframe(pd.DataFrame(alerts_sent), width='stretch', hide_index=True)


def render_admin_panel():
    st.markdown("### 🔒 Admin Analytics & System Governance")

    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        _render_login_form()
    else:
        _render_governance_dashboard()
