"""Server-side prediction audit trail (Tab 2)."""
import pandas as pd
import streamlit as st

from api_client import fetch_recent_predictions


def render_audit_log():
    st.markdown("### 📋 Server-Side SQLite Prediction Audit Trail")
    st.caption("Every prediction and explainability request is permanently logged for disaster accountability and reproducible model governance.")

    logs = fetch_recent_predictions(limit=50)

    if not logs:
        st.info("No predictions logged yet. Run a prediction from the map tab to create audit log records.")
        return

    df_logs = pd.DataFrame(logs)
    cols = [c for c in ['id', 'timestamp', 'latitude', 'longitude', 'matched_region', 'prediction', 'probability', 'risk_level', 'plain_language_summary'] if c in df_logs.columns]
    df_display = df_logs[cols].copy()
    df_display['prediction'] = df_display['prediction'].apply(lambda p: "🌧️ Heavy Rain" if p == 1 else "☀️ Normal/Light")
    df_display['probability'] = df_display['probability'].apply(lambda pr: f"{pr*100:.1f}%")

    st.dataframe(
        df_display,
        column_config={
            "id": "Log ID",
            "timestamp": "UTC Timestamp",
            "latitude": st.column_config.NumberColumn("Lat", format="%.3f"),
            "longitude": st.column_config.NumberColumn("Lon", format="%.3f"),
            "matched_region": "Nearest Station",
            "prediction": "Prediction",
            "probability": "Risk Prob",
            "risk_level": "Risk Level",
            "plain_language_summary": "Explanation Summary"
        },
        width='stretch',
        hide_index=True
    )
