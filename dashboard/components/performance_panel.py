"""Model Performance & Validation panel: ROC curve, confusion matrix, global SHAP (Tab 3)."""
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from api_client import fetch_performance_metrics


def render_performance_panel():
    st.markdown("### 🎯 Model Performance & Validation Panel")
    st.caption("Comprehensive test set validation metrics, ROC curve, confusion matrix, and global SHAP feature importance computed from time-aware train/test split (2024-2025).")

    perf_artifacts = fetch_performance_metrics()
    metrics_data = perf_artifacts.get("metrics", {})

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Test ROC-AUC", f"{metrics_data.get('test_roc_auc', 0.9688):.4f}", "Time-Aware 2024-2025")
    with m2:
        st.metric("Tuned Recall (0.35)", f"{metrics_data.get('test_recall_tuned_0.35', 0.7741)*100:.1f}%", "Prioritized Recall")
    with m3:
        st.metric("Test Accuracy", f"{metrics_data.get('test_accuracy', 0.9782)*100:.1f}%", "164,302 Test Records")
    with m4:
        st.metric("Test PR-AUC", f"{metrics_data.get('test_pr_auc', 0.3434):.4f}", "Imbalanced PR")
    with m5:
        st.metric("Covered Stations", "406", "All 32 States of India")

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    pcol1, pcol2 = st.columns(2, gap="large")

    with pcol1:
        st.markdown("#### 📈 Receiver Operating Characteristic (ROC) Curve")
        roc_info = perf_artifacts.get("roc_curve")
        if roc_info:
            fig_roc = go.Figure()
            fig_roc.add_trace(go.Scatter(
                x=roc_info.get("fpr", []),
                y=roc_info.get("tpr", []),
                mode='lines',
                name=f"XGBoost Model (AUC = {roc_info.get('roc_auc', 0.9688)})",
                line=dict(color="#0EA5E9", width=3)
            ))
            fig_roc.add_trace(go.Scatter(
                x=[0, 1], y=[0, 1],
                mode='lines',
                name="Random Baseline",
                line=dict(color="#64748B", dash="dash")
            ))
            fig_roc.update_layout(
                xaxis_title="False Positive Rate (1 - Specificity)",
                yaxis_title="True Positive Rate (Recall)",
                template="plotly_dark",
                height=350,
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig_roc, width='stretch')
        else:
            st.info("ROC Curve artifact loading...")

    with pcol2:
        st.markdown("#### 🔲 Confusion Matrix (Test Set @ 0.5 Threshold)")
        cm_info = perf_artifacts.get("confusion_matrix")
        if cm_info:
            matrix = np.array(cm_info.get("matrix", [[159945, 3224], [356, 777]]))
            labels = cm_info.get("labels", ["Normal/Light", "Heavy Rain"])

            fig_cm = px.imshow(
                matrix,
                x=labels,
                y=labels,
                color_continuous_scale="Blues",
                text_auto=True,
                aspect="auto",
                labels=dict(x="Predicted Class", y="Actual Class", color="Count"),
                template="plotly_dark"
            )
            fig_cm.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_cm, width='stretch')
        else:
            st.info("Confusion Matrix artifact loading...")

    st.markdown("#### 🌐 Global SHAP Feature Importance (Overall Model Driver Ranking)")
    global_shap = perf_artifacts.get("global_shap")
    if global_shap:
        df_gshap = pd.DataFrame(global_shap[:12])
        df_gshap = df_gshap.sort_values(by="mean_abs_shap", ascending=True)
        fig_gshap = px.bar(
            df_gshap,
            x="mean_abs_shap",
            y="feature",
            orientation="h",
            title="Global Mean Absolute SHAP Values across Test Set",
            labels={"mean_abs_shap": "Mean |SHAP Value| (Global Feature Importance)", "feature": "Meteorological Feature"},
            color="mean_abs_shap",
            color_continuous_scale="Tealgrn",
            template="plotly_dark",
            height=380
        )
        fig_gshap.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_gshap, width='stretch')
    else:
        st.info("Global SHAP artifact loading...")
