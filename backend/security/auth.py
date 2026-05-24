"""
Password hashing and signed cookie session helpers.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, HTTPException, Request

from backend.config.settings import settings
from backend.db import get_db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 150_000)
    return f"pbkdf2_sha256${salt}${base64.b64encode(digest).decode('utf-8')}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, salt, digest = stored_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 150_000)
        return hmac.compare_digest(base64.b64encode(candidate).decode("utf-8"), digest)
    except ValueError:
        return False


def _sign(value: str) -> str:
    return hmac.new(settings.app_secret_key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def signed_session_token(session_id: str) -> str:
    return f"{session_id}.{_sign(session_id)}"


def verify_session_token(token: str | None) -> str | None:
    if not token or "." not in token:
        return None
    session_id, signature = token.rsplit(".", 1)
    if hmac.compare_digest(_sign(session_id), signature):
        return session_id
    return None


def create_session(user_id: str) -> tuple[str, str]:
    session_id = secrets.token_urlsafe(32)
    now = utc_now()
    expires = now + timedelta(hours=settings.session_expire_hours)
    with get_db() as db:
        db.execute(
            "INSERT INTO sessions (id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (session_id, user_id, now.isoformat(), expires.isoformat()),
        )
    return signed_session_token(session_id), expires.isoformat()


def revoke_session(token: str | None) -> None:
    session_id = verify_session_token(token)
    if not session_id:
        return
    with get_db() as db:
        db.execute("UPDATE sessions SET revoked_at = ? WHERE id = ?", (iso_now(), session_id))


def get_current_user(request: Request, session_cookie: str | None = Cookie(default=None, alias=settings.session_cookie_name)):
    token = session_cookie or request.cookies.get(settings.session_cookie_name)
    session_id = verify_session_token(token)
    if not session_id:
        raise HTTPException(status_code=401, detail="Please log in to continue.")

    with get_db() as db:
        row = db.execute(
            """
            SELECT users.* FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.id = ?
              AND sessions.revoked_at IS NULL
              AND sessions.expires_at > ?
              AND users.is_active = 1
            """,
            (session_id, iso_now()),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    return dict(row)
