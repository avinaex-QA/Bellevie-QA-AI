"""
Encrypted per-user integration storage.
"""
from __future__ import annotations

import secrets
from typing import Any

from backend.db import get_db
from backend.security.auth import iso_now
from backend.security.encryption import decrypt_json, encrypt_json


PROVIDERS = ("jira", "clickup", "github", "ai")


def save_integration(user_id: str, provider: str, config: dict[str, Any], auth_type: str = "manual") -> None:
    save_connected_integration(user_id, provider, config=config, auth_type=auth_type)


def save_connected_integration(
    user_id: str,
    provider: str,
    *,
    config: dict[str, Any],
    auth_type: str = "manual",
    access_token: str | None = None,
    refresh_token: str | None = None,
    expires_at: str | None = None,
    provider_account_id: str | None = None,
    provider_account_email: str | None = None,
    provider_workspace_id: str | None = None,
    provider_workspace_name: str | None = None,
) -> None:
    provider = provider.lower()
    encrypted = encrypt_json(config)
    encrypted_access = encrypt_json({"token": access_token}) if access_token else None
    encrypted_refresh = encrypt_json({"token": refresh_token}) if refresh_token else None
    now = iso_now()
    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM user_integrations WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        ).fetchone()
        if existing:
            db.execute(
                """
                UPDATE user_integrations
                SET encrypted_config = ?, auth_type = ?, access_token_encrypted = ?, refresh_token_encrypted = ?,
                    expires_at = ?, provider_account_id = ?, provider_account_email = ?,
                    provider_workspace_id = ?, provider_workspace_name = ?, is_connected = 1, updated_at = ?
                WHERE user_id = ? AND provider = ?
                """,
                (
                    encrypted,
                    auth_type,
                    encrypted_access,
                    encrypted_refresh,
                    expires_at,
                    provider_account_id,
                    provider_account_email,
                    provider_workspace_id,
                    provider_workspace_name,
                    now,
                    user_id,
                    provider,
                ),
            )
        else:
            db.execute(
                """
                INSERT INTO user_integrations
                (id, user_id, provider, encrypted_config, auth_type, access_token_encrypted, refresh_token_encrypted,
                 expires_at, provider_account_id, provider_account_email, provider_workspace_id, provider_workspace_name,
                 is_connected, connected_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    secrets.token_urlsafe(16),
                    user_id,
                    provider,
                    encrypted,
                    auth_type,
                    encrypted_access,
                    encrypted_refresh,
                    expires_at,
                    provider_account_id,
                    provider_account_email,
                    provider_workspace_id,
                    provider_workspace_name,
                    now,
                    now,
                ),
            )


def get_integration(user_id: str, provider: str) -> dict[str, Any] | None:
    with get_db() as db:
        row = db.execute(
            """
            SELECT encrypted_config, access_token_encrypted, refresh_token_encrypted, expires_at,
                   provider_account_id, provider_account_email, provider_workspace_id, provider_workspace_name,
                   auth_type, is_connected
            FROM user_integrations WHERE user_id = ? AND provider = ? AND is_connected = 1
            """,
            (user_id, provider.lower()),
        ).fetchone()
    if not row:
        return None
    config = decrypt_json(row["encrypted_config"])
    if row["access_token_encrypted"]:
        config["access_token"] = decrypt_json(row["access_token_encrypted"]).get("token")
    if row["refresh_token_encrypted"]:
        config["refresh_token"] = decrypt_json(row["refresh_token_encrypted"]).get("token")
    config.update({
        "expires_at": row["expires_at"],
        "provider_account_id": row["provider_account_id"],
        "provider_account_email": row["provider_account_email"],
        "provider_workspace_id": row["provider_workspace_id"],
        "provider_workspace_name": row["provider_workspace_name"],
        "auth_type": row["auth_type"],
    })
    return config


def delete_integration(user_id: str, provider: str) -> None:
    with get_db() as db:
        db.execute(
            "UPDATE user_integrations SET is_connected = 0, updated_at = ? WHERE user_id = ? AND provider = ?",
            (iso_now(), user_id, provider.lower()),
        )


def list_status(user_id: str) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT provider, auth_type, encrypted_config, updated_at, provider_account_email,
                   provider_workspace_id, provider_workspace_name, is_connected
            FROM user_integrations WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()

    by_provider = {row["provider"]: row for row in rows}
    statuses = []
    for provider in PROVIDERS:
        row = by_provider.get(provider)
        display = {}
        if row and row["is_connected"]:
            config = decrypt_json(row["encrypted_config"])
            if provider == "jira":
                display = {
                    "base_url": config.get("base_url") or config.get("site_url"),
                    "email": row["provider_account_email"] or config.get("email"),
                    "workspace": row["provider_workspace_name"] or config.get("base_url"),
                    "workspace_id": row["provider_workspace_id"],
                    "bug_project_key": config.get("bug_project_key"),
                }
            elif provider == "clickup":
                display = {
                    "email": row["provider_account_email"],
                    "workspace": row["provider_workspace_name"],
                    "workspace_id": row["provider_workspace_id"],
                    "api_base": config.get("api_base"),
                }
            elif provider == "github":
                display = {
                    "email": row["provider_account_email"],
                    "username": row["provider_account_id"],
                    "token_configured": True,
                }
            elif provider == "ai":
                display = {"provider": config.get("provider")}
        statuses.append({
            "provider": provider,
            "connected": bool(row and row["is_connected"]),
            "auth_type": row["auth_type"] if row else "",
            "display": display,
            "updated_at": row["updated_at"] if row else None,
        })
    return statuses


def require_integration(user_id: str, provider: str) -> dict[str, Any]:
    config = get_integration(user_id, provider)
    if not config:
        raise ValueError(f"Please connect {provider.title()} in Settings before using this feature.")
    return config


def update_oauth_tokens(
    user_id: str,
    provider: str,
    *,
    access_token: str,
    refresh_token: str | None = None,
    expires_at: str | None = None,
) -> None:
    encrypted_access = encrypt_json({"token": access_token})
    encrypted_refresh = encrypt_json({"token": refresh_token}) if refresh_token else None
    with get_db() as db:
        if encrypted_refresh:
            db.execute(
                """
                UPDATE user_integrations
                SET access_token_encrypted = ?, refresh_token_encrypted = ?, expires_at = ?, updated_at = ?
                WHERE user_id = ? AND provider = ?
                """,
                (encrypted_access, encrypted_refresh, expires_at, iso_now(), user_id, provider.lower()),
            )
        else:
            db.execute(
                """
                UPDATE user_integrations
                SET access_token_encrypted = ?, expires_at = ?, updated_at = ?
                WHERE user_id = ? AND provider = ?
                """,
                (encrypted_access, expires_at, iso_now(), user_id, provider.lower()),
            )


def mark_disconnected(user_id: str, provider: str) -> None:
    delete_integration(user_id, provider)
