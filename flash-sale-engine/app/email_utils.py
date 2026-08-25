import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "TatkalEngine <onboarding@resend.dev>")

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def build_verification_html(code: str) -> str:
    return f"""
    <html>
      <body style="font-family: sans-serif;">
        <h2>Verify Your Account</h2>
        <p>Your verification code is:</p>
        <h1 style="letter-spacing: 4px;">{code}</h1>
        <p>This code expires in 10 minutes.</p>
      </body>
    </html>
    """


def send_with_resend(to_email: str, subject: str, html: str) -> bool:
    if not RESEND_API_KEY:
        return False

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": RESEND_FROM_EMAIL,
                "to": [to_email],
                "subject": subject,
                "html": html,
            },
            timeout=10,
        )
        if response.ok:
            return True
        print(f"[EMAIL ERROR] Resend failed for {to_email}: {response.status_code} {response.text}")
        return False
    except Exception as e:
        print(f"[EMAIL ERROR] Resend request failed for {to_email}: {e}")
        return False


def send_with_smtp(to_email: str, subject: str, html: str) -> bool:
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] SMTP failed for {to_email}: {e}")
        return False


def send_verification_email(to_email: str, code: str) -> bool:
    subject = "TatkalEngine - Verify Your Email"
    html = build_verification_html(code)

    if send_with_resend(to_email, subject, html):
        return True

    return send_with_smtp(to_email, subject, html)
