"""
ReportLab PDF Report Generator for RainXplain.
Generates a clean, single-page executive PDF report for a given prediction payload.
"""
import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

def generate_pdf_report(pred_data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A")
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor("#0284C7")
    )
    
    section_heading = ParagraphStyle(
        'SectionHead',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=8,
        spaceAfter=4
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )
    
    warning_style = ParagraphStyle(
        'WarningBox',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#991B1B")
    )

    elements = []

    # Title & Header Block
    elements.append(Paragraph("🌧️ RainXplain | Heavy Rain Prediction & XAI Report", title_style))
    elements.append(Paragraph("Explainable AI Early Warning System for Resilient Infrastructure (UN SDG 9)", subtitle_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0EA5E9"), spaceAfter=12))

    # Metadata & Key Metrics
    timestamp = pred_data.get("timestamp") or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    region = pred_data.get("matched_region") or "Unknown"
    distance = pred_data.get("distance_km") or 0.0
    lat = pred_data.get("latitude") or pred_data.get("input_features", {}).get("latitude", 0.0)
    lon = pred_data.get("longitude") or pred_data.get("input_features", {}).get("longitude", 0.0)
    prob_pct = pred_data.get("probability_pct") or f"{float(pred_data.get('probability', 0.0))*100:.1f}%"
    risk_lvl = pred_data.get("risk_level") or "LOW"
    imd_cat = pred_data.get("imd_category") or ""

    summary_table_data = [
        [
            Paragraph("<b>Target Location:</b>", body_style),
            Paragraph(f"{region} ({lat:.4f}, {lon:.4f})", body_style),
            Paragraph("<b>Report Generated:</b>", body_style),
            Paragraph(str(timestamp), body_style)
        ],
        [
            Paragraph("<b>Nearest Station Dist:</b>", body_style),
            Paragraph(f"{distance} km", body_style),
            Paragraph("<b>Rain Probability:</b>", body_style),
            Paragraph(f"<b>{prob_pct}</b>", body_style)
        ],
        [
            Paragraph("<b>Risk Classification:</b>", body_style),
            Paragraph(f"<b>{risk_lvl}</b>", body_style),
            Paragraph("<b>IMD Category:</b>", body_style),
            Paragraph(imd_cat, body_style)
        ]
    ]

    t_summary = Table(summary_table_data, colWidths=[120, 160, 120, 140])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 10))

    # Confidence & Anomaly Flags Section
    flags = pred_data.get("confidence_flags") or []
    if isinstance(flags, str):
        try:
            import json
            flags = json.loads(flags)
        except:
            flags = [flags] if flags else []

    if flags:
        elements.append(Paragraph("⚠️ Confidence & Anomaly Flags", section_heading))
        flag_data = []
        for f in flags:
            flag_data.append([Paragraph(f"• {f}", warning_style)])
        t_flags = Table(flag_data, colWidths=[540])
        t_flags.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FEF2F2")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#FCA5A5")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t_flags)
        elements.append(Spacer(1, 10))

    # Plain Language Summary Box
    summary_text = pred_data.get("plain_language_summary") or ""
    if summary_text:
        elements.append(Paragraph("💡 Plain-Language Meteorological Insight", section_heading))
        t_insight = Table([[Paragraph(summary_text, body_style)]], colWidths=[540])
        t_insight.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0F9FF")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#BAE6FD")),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(t_insight)
        elements.append(Spacer(1, 10))

    # SHAP Key Features Table
    elements.append(Paragraph("🔍 Key Feature Attributions (SHAP Local Drivers)", section_heading))
    shap_factors = pred_data.get("top_contributing_factors") or pred_data.get("top_shap_factors") or []
    if isinstance(shap_factors, str):
        try:
            import json
            shap_factors = json.loads(shap_factors)
        except:
            shap_factors = []

    shap_rows = [
        [Paragraph("<b>Feature</b>", body_style), Paragraph("<b>Value</b>", body_style), Paragraph("<b>SHAP Contribution</b>", body_style), Paragraph("<b>Impact Direction</b>", body_style)]
    ]
    
    for item in shap_factors[:5]:
        feat = item.get("feature", "N/A")
        val = str(item.get("value", "N/A"))
        shap_v = item.get("shap_value", 0.0)
        shap_str = f"+{shap_v:.4f}" if shap_v > 0 else f"{shap_v:.4f}"
        impact = item.get("impact", "INCREASES_RISK")
        shap_rows.append([
            Paragraph(feat, body_style),
            Paragraph(val, body_style),
            Paragraph(shap_str, body_style),
            Paragraph(impact, body_style)
        ])

    if len(shap_rows) == 1:
        shap_rows.append([Paragraph("No detailed SHAP factors available.", body_style), Paragraph("", body_style), Paragraph("", body_style), Paragraph("", body_style)])

    t_shap = Table(shap_rows, colWidths=[160, 100, 140, 140])
    t_shap.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_shap)

    # Footer
    elements.append(Spacer(1, 15))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=6))
    elements.append(Paragraph("<font color='#64748B' size='8'>RainXplain Engine (v1.0) — XGBoost + SHAP/LIME — Automated PDF Report for Disaster Governance</font>", body_style))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
