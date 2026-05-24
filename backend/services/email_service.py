"""
Email delivery abstraction for OTP verification.
Supports SMTP, Resend, and local dev fallback.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

import requests

from backend.config.settings import settings
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class EmailDeliveryNotConfigured(RuntimeError):
    pass


class EmailDeliveryFailed(RuntimeError):
    pass


def _verification_body(name: str, otp: str) -> str:
    return (
        f"Hello {name},\n\n"
        "Your verification code is:\n\n"
        f"{otp}\n\n"
        "This code expires in 10 minutes.\n\n"
        "If you did not request this, please ignore this email.\n"
    )


def send_verification_email(email: str, name: str, otp: str) -> None:
    subject = "Verify your AI QA Copilot account"
    body = _verification_body(name, otp)

    # RESEND EMAIL DELIVERY
    if settings.resend_api_key and settings.email_from:
        try:
            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.email_from,
                    "to": [email],
                    "subject": subject,
                    "text": body,
                },
                timeout=15,
            )

            if response.status_code >= 400:
                logger.error("Resend API Error: %s", response.text)

            response.raise_for_status()

            logger.info("Verification email sent successfully to %s via Resend", email)
            return

        except requests.RequestException as exc:
            logger.exception("Resend email sending failed")
            raise EmailDeliveryFailed(
                f"Could not send verification email via Resend: {str(exc)}"
            ) from exc

    # SMTP FALLBACK
    if settings.smtp_host:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.smtp_from or settings.email_from
        message["To"] = email
        message.set_content(body)

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                server.starttls()

                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)

                server.send_message(message)

            logger.info("Verification email sent successfully to %s via SMTP", email)
            return

        except (OSError, smtplib.SMTPException) as exc:
            logger.exception("SMTP email sending failed")
            raise EmailDeliveryFailed(
                f"Could not send verification email via SMTP: {str(exc)}"
            ) from exc

    # LOCAL DEV FALLBACK
    if getattr(settings, "email_dev_mode", False):
        logger.warning("EMAIL_DEV_MODE enabled. OTP for %s is %s", email, otp)
        return

    raise EmailDeliveryNotConfigured(
        "Email service is not configured. Add RESEND_API_KEY + EMAIL_FROM or SMTP settings in .env."
    )