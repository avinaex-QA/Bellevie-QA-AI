"""
Runtime integration credential resolution, including OAuth refresh.
"""
from __future__ import annotations

from fastapi import HTTPException

from backend.security.auth import iso_now
from backend.services.integration_store import mark_disconnected, require_integration, update_oauth_tokens
from backend.services.oauth_provider_service import refresh_atlassian_token


def require_runtime_integration(user_id: str, provider: str) -> dict:
    config = require_integration(user_id, provider)
    if provider == "jira" and config.get("auth_type") == "oauth" and config.get("expires_at") and config["expires_at"] <= iso_now():
        if not config.get("refresh_token"):
            mark_disconnected(user_id, "jira")
            raise HTTPException(status_code=401, detail="Jira connection expired. Please reconnect.")
        try:
            refreshed = refresh_atlassian_token(config["refresh_token"])
        except Exception:
            mark_disconnected(user_id, "jira")
            raise HTTPException(status_code=401, detail="Jira connection expired. Please reconnect.")
        update_oauth_tokens(
            user_id,
            "jira",
            access_token=refreshed["access_token"],
            refresh_token=refreshed.get("refresh_token"),
            expires_at=refreshed.get("expires_at"),
        )
        config["access_token"] = refreshed["access_token"]
        config["refresh_token"] = refreshed.get("refresh_token") or config.get("refresh_token")
        config["expires_at"] = refreshed.get("expires_at")
    return config
