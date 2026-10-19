"""Prediction results: stat cards, impact estimate, SHAP/LIME/forecast sub-tabs, PDF download (Tab 1, full width)."""
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from api_client import call_multi_day_forecast
from api.report import generate_pdf_report


def _render_stat_cards(res):
    r1, r2, r3, r4 = st.columns([1.2, 1, 1, 1])

    prob_val = res.get("probability", 0.0)
    risk_lvl = res.get("risk_level", "LOW")
    color_code = res.get("color_code", "#16A34A")

    with r1:
        badge_class = "badge-heavy" if prob_val >= 0.35 else "badge-safe"
        st.markdown(f"""
        <div class="card" style="border-left: 6px solid {color_code};">
            <span class="stat-label">IMD Risk Classification</span>
            <div style="margin: 8px 0;"><span class="{badge_class}">{risk_lvl}</span></div>
            <small style="color: #CBD5E1;">{res.get('imd_category', '')}</small>
        </div>
        """, unsafe_allow_html=True)

    with r2:
        st.markdown(f"""
        <div class="card">
            <span class="stat-label">Heavy Rain Probability</span>
            <div class="stat-value" style="color: {color_code};">{prob_val*100:.1f}%</div>
            <small style="color: #94A3B8;">IMD Threshold &ge; 64.5 mm/24h</small>
        </div>
        """, unsafe_allow_html=True)

    with r3:
        st.markdown(f"""
        <div class="card">
            <span class="stat-label">Matched Region</span>
            <div class="stat-value" style="font-size: 1.15rem; color: #38BDF8;">{res.get('matched_region', 'N/A')}</div>
            <small style="color: #94A3B8;">Distance: {res.get('distance_km', 0)} km</small>
        </div>
        """, unsafe_allow_html=True)

    with r4:
        st.markdown(f"""
        <div class="card">
            <span class="stat-label">Model Engine</span>
            <div class="stat-value" style="font-size: 1.15rem; color: #A78BFA;">XGBoost + SHAP</div>
            <small style="color: #94A3B8;">Tuned for Recall (F1: 0.30, AUC: 0.97)</small>
        </div>
        """, unsafe_allow_html=True)


def _render_impact_card(res):
    impact_info = res.get("impact_estimation")
    if not impact_info:
        return
    st.markdown(f"""
    <div class="card" style="border-left: 6px solid {impact_info.get('impact_color', '#0EA5E9')};">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span class="stat-label">Potential Infrastructure & Population Impact Layer</span>
                <h4 style="margin: 4px 0 0 0; color: #F8FAFC;">{impact_info.get('overall_impact_label')}</h4>
                <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.95rem;">
                    <strong>State:</strong> {impact_info.get('state')} &nbsp;|&nbsp;
                    <strong>Density:</strong> {impact_info.get('population_density_sq_km')} people/km² ({impact_info.get('density_category')})
                </p>
                <small style="color: #94A3B8; display: block; margin-top: 4px;">💡 <strong>Action Recommendation:</strong> {impact_info.get('recommendation')}</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_shap_tab(res):
    shap_data = res.get("shap_explanation", [])
    if not shap_data:
        return
    df_shap = pd.DataFrame(shap_data[:10])
    df_shap['Direction'] = df_shap['shap_value'].apply(lambda x: 'Increases Heavy Rain Risk' if x > 0 else 'Decreases Heavy Rain Risk')
    df_shap['AbsImpact'] = df_shap['shap_value'].abs()
    df_shap = df_shap.sort_values(by='AbsImpact', ascending=True)

    fig_shap = px.bar(
        df_shap,
        x='shap_value',
        y='feature',
        orientation='h',
        color='Direction',
        color_discrete_map={
            'Increases Heavy Rain Risk': '#EF4444',
            'Decreases Heavy Rain Risk': '#10B981'
        },
        title="Top 10 Feature Contributions to Prediction (SHAP Values)",
        labels={'shap_value': 'SHAP Contribution (Log-Odds Impact)', 'feature': 'Meteorological Feature'},
        template="plotly_dark",
        height=380
    )
    fig_shap.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif")
    )
    st.plotly_chart(fig_shap, width='stretch')


def _render_shap_lime_comparison_tab(res):
    c_col1, c_col2 = st.columns(2, gap="medium")
    with c_col1:
        st.markdown("#### SHAP Top Risk Drivers")
        shap_list = res.get("shap_explanation", [])
        if shap_list:
            st.dataframe(pd.DataFrame(shap_list[:6])[['feature', 'value', 'shap_value', 'impact']], width='stretch', hide_index=True)
    with c_col2:
        st.markdown("#### LIME Local Decision Rules")
        lime_list = res.get("lime_explanation", [])
        if lime_list:
            st.dataframe(pd.DataFrame(lime_list[:6])[['rule', 'weight', 'impact']], width='stretch', hide_index=True)

    comparison = res.get("shap_lime_comparison")
    if comparison:
        st.info(f"**🤖 SHAP vs LIME Consensus Synthesis:** {comparison.get('comparison_note')}")


def _render_forecast_tab(res):
    st.caption("Recursive forward risk trend using lag-feature statistical updating. *Note: Simple recursive statistical estimate; not a physical Numerical Weather Prediction model.*")
    forecast_data = call_multi_day_forecast({
        "latitude": st.session_state.selected_lat,
        "longitude": st.session_state.selected_lon,
        "matched_station": res.get("matched_region"),
        "rainfall_lag1": res.get("input_features", {}).get("rainfall_lag1", 10.0),
        "rainfall_lag2": res.get("input_features", {}).get("rainfall_lag2", 5.0)
    })
    if forecast_data and "forecast_days" in forecast_data:
        df_fc = pd.DataFrame(forecast_data["forecast_days"])
        fig_fc = px.line(
            df_fc,
            x="day_label",
            y="probability",
            markers=True,
            title=f"5-Day Forward Risk Trend for {res.get('matched_region')}",
            labels={"probability": "Heavy Rain Probability", "day_label": "Forecast Horizon"},
            template="plotly_dark",
            height=320
        )
        fig_fc.add_hline(y=0.35, line_dash="dash", line_color="#EA580C", annotation_text="Heavy Rain Alert Threshold (0.35)")
        fig_fc.update_traces(line_color="#38BDF8", line_width=3, marker_size=8)
        st.plotly_chart(fig_fc, width='stretch')


def render_results_panel():
    if not st.session_state.prediction_result:
        return

    res = st.session_state.prediction_result
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # Download PDF Report Button & Action Header (Required Feature #4)
    pdf_col1, pdf_col2 = st.columns([0.75, 0.25])
    with pdf_col1:
        st.markdown("## 📊 Explainable Prediction & Risk Assessment")
    with pdf_col2:
        try:
            pdf_bytes = generate_pdf_report(res)
            st.download_button(
                label="📄 Download PDF Report",
                data=pdf_bytes,
                file_name=f"RainXplain_Report_{res.get('matched_region','Region').replace(' ','_')}.pdf",
                mime="application/pdf",
                width='stretch'
            )
        except Exception as e:
            st.error(f"PDF error: {e}")

    # Confidence & Anomaly Flagging Banner (Required Feature #3)
    flags = res.get("confidence_flags", [])
    for f in flags:
        st.markdown(f"""
        <div class="warning-callout">
            <strong>⚠️ Confidence / Anomaly Alert:</strong> {f}
        </div>
        """, unsafe_allow_html=True)

    _render_stat_cards(res)
    _render_impact_card(res)

    summary = res.get("plain_language_summary", "")
    if summary:
        color_code = res.get("color_code", "#16A34A")
        st.markdown(f"""
        <div class="info-callout" style="background: rgba(30, 41, 59, 0.8); border-left: 4px solid {color_code};">
            <h4 style="margin: 0 0 6px 0; color: #F8FAFC;">💡 Plain-Language Meteorological Insight</h4>
            <p style="margin: 0; font-size: 1.05rem; line-height: 1.5; color: #E2E8F0;">{summary}</p>
        </div>
        """, unsafe_allow_html=True)

    ex_tabs = st.tabs(["🔍 SHAP Feature Attribution", "⚖️ SHAP vs LIME Comparison", "📈 5-Day Recursive Risk Forecast"])
    with ex_tabs[0]:
        _render_shap_tab(res)
    with ex_tabs[1]:
        _render_shap_lime_comparison_tab(res)
    with ex_tabs[2]:
        _render_forecast_tab(res)
