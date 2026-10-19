"""Shared CSS theme for the RainXplain Streamlit dashboard."""
import streamlit as st

CSS_STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Inter:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3, h4, .brand-title {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    .main-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0369A1 100%);
        padding: 24px 32px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .section-divider {
        margin: 28px 0;
        border: none;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    .badge-heavy {
        background: linear-gradient(135deg, #DC2626, #991B1B);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 700;
        display: inline-block;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4);
    }

    .badge-mod {
        background: linear-gradient(135deg, #EA580C, #C2410C);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 700;
        display: inline-block;
        box-shadow: 0 4px 12px rgba(234, 88, 12, 0.4);
    }

    .badge-safe {
        background: linear-gradient(135deg, #16A34A, #15803D);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 700;
        display: inline-block;
        box-shadow: 0 4px 12px rgba(22, 163, 74, 0.4);
    }

    .card {
        background: #1E293B;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        margin-bottom: 16px;
    }

    .stat-label {
        font-size: 0.85rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .stat-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #F8FAFC;
    }

    .info-callout {
        background: rgba(14, 165, 233, 0.1);
        border-left: 4px solid #0EA5E9;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin: 12px 0;
        color: #E2E8F0;
    }

    .warning-callout {
        background: rgba(220, 38, 38, 0.15);
        border-left: 5px solid #EF4444;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin: 12px 0;
        color: #FECACA;
    }
</style>
"""


def inject_css():
    st.markdown(CSS_STYLES, unsafe_allow_html=True)


def render_header():
    st.markdown("""
    <div class="main-header">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 style="margin: 0; font-size: 2.2rem; display: flex; align-items: center; gap: 12px;">
                    🌧️ RainXplain
                    <span style="font-size: 0.9rem; background: rgba(56, 189, 248, 0.2); border: 1px solid #38BDF8; color: #38BDF8; padding: 4px 10px; border-radius: 12px; font-weight: 500;">
                        SDG 9: Resilient Infrastructure
                    </span>
                </h1>
                <p style="margin: 6px 0 0 0; color: #CBD5E1; font-size: 1.05rem;">
                    Explainable AI (XAI) System for Predicting High-Impact Heavy Rain Events across India
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
