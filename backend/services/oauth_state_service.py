"""
OAuth state persistence and validation.
"""
from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import HTTPException

from backend.db import get_db
from backend.security.auth import iso_now, utc_now


def create_oauth_state(provider: str, purpose: str, user_id: str | None = None, redirect_after: str | None = None) -> str:
    state = secrets.token_urlsafe(32)
    expires = (utc_now() + timedelta(minutes=10)).isoformat()
    with get_db() as db:
        db.execute(
            """
            INSERT INTO oauth_states (state, user_id, provider, purpose, redirect_after, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (state, user_id, provider, purpose, redirect_after, iso_now(), expires),
        )
    return state


def consume_oauth_state(state: str | None, provider: str, purpose: str) -> dict:
    if not state:
        raise HTTPException(status_code=400, detail="Invalid OAuth callback.")
    with get_db() as db:
        row = db.execute(
            """
            SELECT * FROM oauth_states
            WHERE state = ? AND provider = ? AND purpose = ? AND used_at IS NULL AND expires_at > ?
            """,
            (state, provider, purpose, iso_now()),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="Invalid OAuth callback.")
        db.execute("UPDATE oauth_states SET used_at = ? WHERE state = ?", (iso_now(), state))
    return dict(row)
