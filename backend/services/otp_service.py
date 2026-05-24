"""
OTP generation and verification for email signup.
"""
from __future__ import annotations

import re
import secrets
from datetime import timedelta

from fastapi import HTTPException

from backend.config.settings import settings
from backend.db import get_db
from backend.security.auth import hash_password, iso_now, utc_now, verify_password
from backend.services.email_service import EmailDeliveryFailed, EmailDeliveryNotConfigured, send_verification_email


PASSWORD_POLICY_MESSAGE = "Password must contain uppercase, lowercase, number, and special character."


def validate_email(email: str) -> str:
    clean = (email or "").strip().lower()
    if not clean:
        raise HTTPException(status_code=400, detail="Email is required.")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    return clean


def validate_password(password: str, confirm_password: str | None = None) -> None:
    if not password:
        raise HTTPException(status_code=400, detail="Password is required.")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must meet minimum requirements.")
    checks = [
        re.search(r"[A-Z]", password),
        re.search(r"[a-z]", password),
        re.search(r"\d", password),
        re.search(r"[^A-Za-z0-9]", password),
    ]
    if not all(checks):
        raise HTTPException(status_code=400, detail=PASSWORD_POLICY_MESSAGE)
    if confirm_password is not None and password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")


def _otp_hash(otp: str) -> str:
    return hash_password(otp)


def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def start_email_verification(name: str, email: str, password: str, confirm_password: str) -> dict:
    email = validate_email(email)
    if not (name or "").strip():
        raise HTTPException(status_code=400, detail="Name is required.")
    validate_password(password, confirm_password)

    with get_db() as db:
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="An account already exists for this email.")

    otp = _generate_otp()
    now = utc_now()
    expires = now + timedelta(minutes=settings.otp_expire_minutes)
    verification_id = secrets.token_urlsafe(16)
    with get_db() as db:
        db.execute("DELETE FROM email_verifications WHERE email = ? AND is_verified = 0", (email,))
        db.execute(
            """
            INSERT INTO email_verifications
            (id, name, email, otp_hash, password_hash, expires_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (verification_id, name.strip(), email, _otp_hash(otp), hash_password(password), expires.isoformat(), now.isoformat(), now.isoformat()),
        )
    try:
        send_verification_email(email, name.strip(), otp)
    except (EmailDeliveryNotConfigured, EmailDeliveryFailed) as exc:
        with get_db() as db:
            db.execute("DELETE FROM email_verifications WHERE id = ?", (verification_id,))
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"success": True, "message": "Verification code sent", "email": email, "expires_in_seconds": settings.otp_expire_minutes * 60}


def resend_otp(email: str) -> dict:
    email = validate_email(email)
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM email_verifications WHERE email = ? AND is_verified = 0 ORDER BY created_at DESC LIMIT 1",
            (email,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No pending verification found.")
        if row["resend_count"] >= settings.otp_max_resends:
            raise HTTPException(status_code=429, detail="Too many OTP resend requests.")
        otp = _generate_otp()
        expires = utc_now() + timedelta(minutes=settings.otp_expire_minutes)
        db.execute(
            "UPDATE email_verifications SET otp_hash = ?, expires_at = ?, resend_count = resend_count + 1, updated_at = ? WHERE id = ?",
            (_otp_hash(otp), expires.isoformat(), iso_now(), row["id"]),
        )
    try:
        send_verification_email(email, row["name"], otp)
    except (EmailDeliveryNotConfigured, EmailDeliveryFailed) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"success": True, "message": "OTP resent", "expires_in_seconds": settings.otp_expire_minutes * 60}


def verify_signup_otp(email: str, otp: str) -> dict:
    email = validate_email(email)
    clean_otp = (otp or "").strip()
    if not re.fullmatch(r"\d{6}", clean_otp):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    with get_db() as db:
        row = db.execute(
            "SELECT * FROM email_verifications WHERE email = ? AND is_verified = 0 ORDER BY created_at DESC LIMIT 1",
            (email,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No pending verification found.")
        if row["attempt_count"] >= settings.otp_max_attempts:
            raise HTTPException(status_code=429, detail="Too many attempts")
        if row["expires_at"] <= iso_now():
            raise HTTPException(status_code=400, detail="OTP expired")
        db.execute("UPDATE email_verifications SET attempt_count = attempt_count + 1, updated_at = ? WHERE id = ?", (iso_now(), row["id"]))
        if not verify_password(clean_otp, row["otp_hash"]):
            raise HTTPException(status_code=400, detail="Invalid OTP")

        user_id = secrets.token_urlsafe(16)
        now = iso_now()
        db.execute(
            """
            INSERT INTO users (id, name, email, hashed_password, auth_provider, created_at, last_login, is_active, email_verified)
            VALUES (?, ?, ?, ?, 'email', ?, ?, 1, 1)
            """,
            (user_id, row["name"], email, row["password_hash"], now, now),
        )
        db.execute("UPDATE email_verifications SET is_verified = 1, updated_at = ? WHERE id = ?", (now, row["id"]))
    return {"success": True, "message": "Email verified", "user_id": user_id}
