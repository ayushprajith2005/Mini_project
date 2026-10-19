"""
Automated Risk Alerting Service for RainXplain.
Sends email notifications via smtplib (or logs them gracefully if no SMTP server configured)
whenever a subscribed region crosses heavy-rain thresholds.
"""
import os
import sys
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api.db import get_all_subscriptions, log_alert_sent
from src.predict import get_predictor

logger = logging.getLogger("rainxplain.alerts")
logging.basicConfig(level=logging.INFO)

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
ALERT_FROM_EMAIL = os.environ.get("ALERT_FROM_EMAIL", "alerts@rainxplain.org")

def send_email_alert(to_email: str, region: str, risk_level: str, probability: float, details: dict = None) -> bool:
    """
    Sends email alert to subscriber. If no live SMTP credentials provided,
    degrades gracefully by logging the notification.
    """
    subject = f"🚨 RainXplain Heavy Rain Alert for {region}: {risk_level}"
    body = (
        f"RainXplain Early Warning System Alert\n"
        f"=========================================\n"
        f"Region / Location : {region}\n"
        f"Risk Classification: {risk_level}\n"
        f"Heavy Rain Probability: {probability * 100:.1f}%\n"
        f"IMD Threshold     : >= 64.5 mm / 24 hours\n\n"
        f"Please take necessary precautions for resilient infrastructure and safety.\n"
        f"-- RainXplain SDG 9 Early Warning System"
    )

    if SMTP_HOST and SMTP_USER and SMTP_PASS:
        try:
            msg = MIMEMultipart()
            msg['From'] = ALERT_FROM_EMAIL
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(ALERT_FROM_EMAIL, to_email, msg.as_string())
            server.quit()
            logger.info(f"[SMTP Alert Sent] Email successfully delivered to {to_email} for region {region}")
            return True
        except Exception as e:
            logger.error(f"[SMTP Error] Failed to send email to {to_email}: {e}")

    # Graceful fallback logging
    logger.info(f"[LOG-BASED ALERT] Mock email sent to {to_email} | Region: {region} | Risk: {risk_level} ({probability*100:.1f}%)")
    return True

def check_and_trigger_alerts() -> int:
    """
    Periodic job that re-evaluates all active subscriptions.
    Triggers alert if predicted risk is 'HEAVY' or higher (probability >= 0.35).
    """
    subscriptions = get_all_subscriptions()
    if not subscriptions:
        logger.info("No active subscriptions found for alert check.")
        return 0

    predictor = get_predictor()
    alerts_triggered = 0

    for sub in subscriptions:
        lat = sub.get("latitude")
        lon = sub.get("longitude")
        region = sub.get("region_or_latlon", "Unknown")

        if lat is not None and lon is not None:
            pred_input = {"latitude": float(lat), "longitude": float(lon)}
        else:
            pred_input = {"matched_station": region}

        res = predictor.predict(pred_input)
        prob = res.get("probability", 0.0)
        risk_level = res.get("risk_level", "LOW")

        # Trigger alert if Heavy Rain Warning or higher
        if prob >= 0.35 or "HEAVY" in risk_level.upper():
            send_email_alert(
                to_email=sub["email"],
                region=res.get("matched_region") or region,
                risk_level=risk_level,
                probability=prob,
                details=res
            )
            log_alert_sent(
                subscription_id=sub["id"],
                email=sub["email"],
                region=res.get("matched_region") or region,
                risk_level=risk_level,
                probability=prob
            )
            alerts_triggered += 1

    logger.info(f"Completed subscription check: {alerts_triggered} alerts triggered.")
    return alerts_triggered

_scheduler = None

def start_alert_scheduler(interval_minutes: int = 60):
    global _scheduler
    if _scheduler is None or not _scheduler.running:
        _scheduler = BackgroundScheduler()
        _scheduler.add_job(check_and_trigger_alerts, 'interval', minutes=interval_minutes, id='rainxplain_alert_job')
        _scheduler.start()
        logger.info(f"Started Background Alert Scheduler running every {interval_minutes} minutes.")

if __name__ == "__main__":
    count = check_and_trigger_alerts()
    print(f"Triggered {count} alerts in manual run.")
