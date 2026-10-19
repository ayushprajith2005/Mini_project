"""Static SDG 9 methodology & alignment copy (Tab 4)."""
import streamlit as st


def render_sdg_info():
    st.markdown("### 🌱 Alignment with UN SDG 9: Industry, Innovation & Infrastructure")
    st.write("""
    **Target 9.1**: Develop quality, reliable, sustainable and resilient infrastructure, including regional and transborder infrastructure, to support economic development and human well-being.

    **Target 9.a**: Facilitate sustainable and resilient infrastructure development through enhanced technological innovation in developing countries.

    **How RainXplain Delivers on SDG 9:**
    1. **Transparent Early Warning**: Black-box machine learning models fail to gain trust during extreme weather contingencies. RainXplain provides glass-box SHAP attributions and LIME rules for every alert.
    2. **Disaster Mitigation for Transport & Urban Infrastructure**: Early identification of convective cloud bursts allows municipal authorities and transport operators to deploy storm drainage, reroute transit, and safeguard critical electrical/telecom infrastructure.
    3. **Zero-API Spatial Fallback**: Operates using pre-indexed BallTree spatial coordinates across India, functioning reliably even in constrained computing environments.
    """)
