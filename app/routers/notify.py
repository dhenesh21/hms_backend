"""
Notification Service — Email (SMTP) + SMS (configurable)

Configuration via environment variables or database settings:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
  SMS_API_URL, SMS_API_KEY, SMS_SENDER_ID

For local testing, set SMTP_HOST=localhost with a local mail catcher like MailHog.
For production, use Gmail / SendGrid / AWS SES for email, and Fast2SMS / Twilio for SMS.
"""

import asyncio
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import date, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.doctor import DoctorProfile
import httpx
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Notifications"])

# ── Config ────────────────────────────────────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@hospital.com")
HOSPITAL_NAME = os.getenv("HOSPITAL_NAME", "HMS Hospital")

SMS_API_URL = os.getenv("SMS_API_URL", "")   # e.g. Fast2SMS API URL
SMS_API_KEY = os.getenv("SMS_API_KEY", "")
SMS_SENDER_ID = os.getenv("SMS_SENDER_ID", "HMSAPP")


# ── Email ─────────────────────────────────────────────────────────────────────
def send_email_sync(to: str, subject: str, html_body: str) -> bool:
    if not SMTP_HOST or not SMTP_USER:
        logger.warning("SMTP not configured — email skipped")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{HOSPITAL_NAME} <{SMTP_FROM}>"
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to, msg.as_string())
        logger.info(f"Email sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Email failed to {to}: {e}")
        return False


async def send_email(to: str, subject: str, html_body: str) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, send_email_sync, to, subject, html_body)


# ── SMS ───────────────────────────────────────────────────────────────────────
async def send_sms(phone: str, message: str) -> bool:
    if not SMS_API_URL or not SMS_API_KEY:
        logger.warning("SMS not configured — SMS skipped")
        return False
    try:
        # Generic webhook format — works with Fast2SMS, MSG91, etc.
        async with httpx.AsyncClient() as client:
            resp = await client.post(SMS_API_URL, json={
                "authorization": SMS_API_KEY,
                "sender_id": SMS_SENDER_ID,
                "message": message,
                "language": "english",
                "route": "p",
                "numbers": phone.replace("+91", "").replace(" ", ""),
            }, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"SMS failed to {phone}: {e}")
        return False


# ── Templates ─────────────────────────────────────────────────────────────────
def appointment_email_html(patient_name: str, doctor_name: str, appt_date: str, appt_time: str, token: int) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;background:#fff;border:1px solid #EDE9FE;border-radius:12px;overflow:hidden">
      <div style="background:linear-gradient(135deg,#7C3AED,#4F46E5);padding:24px;text-align:center">
        <h1 style="color:#fff;margin:0;font-size:20px">{HOSPITAL_NAME}</h1>
        <p style="color:#DDD6FE;margin:4px 0 0;font-size:13px">Appointment Confirmation</p>
      </div>
      <div style="padding:24px">
        <p style="font-size:15px;color:#1E1B4B">Dear <strong>{patient_name}</strong>,</p>
        <p style="color:#4B5563;font-size:13px">Your appointment has been confirmed. Please find the details below:</p>
        <div style="background:#F5F3FF;border-radius:8px;padding:16px;margin:16px 0">
          <table style="width:100%;font-size:13px">
            <tr><td style="color:#7C3AED;font-weight:600;padding:4px 0">Doctor</td><td style="color:#1E1B4B">Dr. {doctor_name}</td></tr>
            <tr><td style="color:#7C3AED;font-weight:600;padding:4px 0">Date</td><td style="color:#1E1B4B">{appt_date}</td></tr>
            <tr><td style="color:#7C3AED;font-weight:600;padding:4px 0">Time</td><td style="color:#1E1B4B">{appt_time}</td></tr>
            <tr><td style="color:#7C3AED;font-weight:600;padding:4px 0">Token No.</td><td style="color:#1E1B4B;font-weight:700;font-size:16px">#{token}</td></tr>
          </table>
        </div>
        <p style="color:#6B7280;font-size:12px">Please arrive 10 minutes early. Carry your ID proof and previous medical records if any.</p>
        <p style="color:#6B7280;font-size:12px;margin-top:16px">— {HOSPITAL_NAME} Team</p>
      </div>
    </div>"""

def appointment_sms(patient_name: str, doctor_name: str, appt_date: str, token: int) -> str:
    return f"Dear {patient_name}, your appointment with Dr. {doctor_name} on {appt_date} is confirmed. Token No: {token}. Please arrive 10 mins early. - {HOSPITAL_NAME}"

def lab_result_email_html(patient_name: str, order_number: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;background:#fff;border:1px solid #EDE9FE;border-radius:12px;overflow:hidden">
      <div style="background:linear-gradient(135deg,#7C3AED,#4F46E5);padding:24px;text-align:center">
        <h1 style="color:#fff;margin:0;font-size:20px">{HOSPITAL_NAME}</h1>
      </div>
      <div style="padding:24px">
        <p style="font-size:15px;color:#1E1B4B">Dear <strong>{patient_name}</strong>,</p>
        <p style="color:#4B5563;font-size:13px">Your lab results for order <strong>{order_number}</strong> are now ready.</p>
        <p style="color:#4B5563;font-size:13px">Please visit the hospital or contact us to collect your reports.</p>
        <p style="color:#6B7280;font-size:12px;margin-top:16px">— {HOSPITAL_NAME} Lab Team</p>
      </div>
    </div>"""


# ── API Endpoints ─────────────────────────────────────────────────────────────
@router.post("/notify/appointment/{appointment_id}")
async def notify_appointment(
    appointment_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send appointment confirmation to patient via email + SMS"""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        return {"error": "Appointment not found"}

    patient = db.query(Patient).filter(Patient.id == appt.patient_id).first()
    dp = db.query(DoctorProfile).filter(DoctorProfile.id == appt.doctor_id).first()
    doc_user = db.query(User).filter(User.id == dp.user_id).first() if dp else None

    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Patient"
    doctor_name = doc_user.full_name if doc_user else "Doctor"
    appt_date = appt.appointment_date.strftime("%d %b %Y") if appt.appointment_date else "—"
    appt_time = str(appt.appointment_time) if appt.appointment_time else "—"
    token = appt.token_number or 0

    results = {"email": False, "sms": False}

    if patient and patient.email:
        html = appointment_email_html(patient_name, doctor_name, appt_date, appt_time, token)
        results["email"] = await send_email(patient.email, f"Appointment Confirmed — {HOSPITAL_NAME}", html)

    if patient and patient.phone:
        sms = appointment_sms(patient_name, doctor_name, appt_date, token)
        results["sms"] = await send_sms(patient.phone, sms)

    return {"message": "Notifications sent", "results": results, "patient": patient_name}


@router.post("/notify/lab-result/{order_id}")
async def notify_lab_result(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Notify patient when lab results are ready"""
    from app.models.lab import LabOrder
    order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
    if not order:
        return {"error": "Order not found"}

    patient = db.query(Patient).filter(Patient.id == order.patient_id).first()
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Patient"

    results = {"email": False, "sms": False}

    if patient and patient.email:
        html = lab_result_email_html(patient_name, order.order_number or str(order_id))
        results["email"] = await send_email(patient.email, f"Lab Results Ready — {HOSPITAL_NAME}", html)

    if patient and patient.phone:
        sms = f"Dear {patient_name}, your lab results are ready. Order: {order.order_number}. Please visit {HOSPITAL_NAME} to collect. Thank you."
        results["sms"] = await send_sms(patient.phone, sms)

    return {"message": "Notifications sent", "results": results}


@router.post("/notify/custom")
async def send_custom_notification(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send custom message to a patient"""
    patient_id = data.get("patient_id")
    message = data.get("message", "")
    subject = data.get("subject", f"Message from {HOSPITAL_NAME}")

    patient = db.query(Patient).filter(Patient.id == patient_id).first() if patient_id else None
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Patient"

    results = {"email": False, "sms": False}

    if patient and patient.email and data.get("send_email"):
        html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px">
          <h2 style="color:#7C3AED">{HOSPITAL_NAME}</h2>
          <p>Dear {patient_name},</p>
          <p style="line-height:1.7">{message}</p>
          <p style="color:#6B7280;font-size:12px;margin-top:16px">— {HOSPITAL_NAME} Team</p>
        </div>"""
        results["email"] = await send_email(patient.email, subject, html)

    if patient and patient.phone and data.get("send_sms"):
        results["sms"] = await send_sms(patient.phone, message)

    return {"message": "Done", "results": results}


@router.get("/notify/config")
async def get_notification_config(current_user: User = Depends(get_current_user)):
    """Check notification configuration status"""
    return {
        "email_configured": bool(SMTP_HOST and SMTP_USER),
        "sms_configured": bool(SMS_API_URL and SMS_API_KEY),
        "smtp_host": SMTP_HOST or "Not configured",
        "sms_provider": SMS_API_URL.split('/')[2] if SMS_API_URL else "Not configured",
    }
