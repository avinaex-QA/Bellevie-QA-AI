"""
OAuth provider token exchange, metadata lookup, and refresh helpers.
"""
from __future__ import annotations

from datetime import timedelta

import requests
from fastapi import HTTPException

from backend.config.settings import settings
from backend.security.auth import iso_now, utc_now


def _expiry(expires_in: int | None) -> str | None:
    if not expires_in:
        return None
    return (utc_now() + timedelta(seconds=int(expires_in))).isoformat()


def exchange_github_code(code: str) -> dict:
    response = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": settings.github_redirect_uri,
        },
        timeout=15,
    )
    if not response.ok or not response.json().get("access_token"):
        raise HTTPException(status_code=400, detail="GitHub OAuth failed.")
    token = response.json()["access_token"]
    user = requests.get("https://api.github.com/user", headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}, timeout=15).json()
    emails = requests.get("https://api.github.com/user/emails", headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}, timeout=15)
    primary_email = None
    if emails.ok:
        for item in emails.json():
            if item.get("primary"):
                primary_email = item.get("email")
                break
    return {
        "access_token": token,
        "provider_account_id": user.get("login") or str(user.get("id")),
        "provider_account_email": primary_email or user.get("email"),
    }


def exchange_clickup_code(code: str) -> dict:
    response = requests.post(
        "https://api.clickup.com/api/v2/oauth/token",
        json={"client_id": settings.clickup_client_id, "client_secret": settings.clickup_client_secret, "code": code},
        timeout=15,
    )
    if not response.ok or not response.json().get("access_token"):
        raise HTTPException(status_code=400, detail="ClickUp OAuth failed.")
    token = response.json()["access_token"]
    teams = requests.get("https://api.clickup.com/api/v2/team", headers={"Authorization": token}, timeout=15)
    workspace_id = workspace_name = None
    if teams.ok and teams.json().get("teams"):
        first = teams.json()["teams"][0]
        workspace_id = first.get("id")
        workspace_name = first.get("name")
    return {
        "access_token": token,
        "provider_workspace_id": workspace_id,
        "provider_workspace_name": workspace_name,
    }


def exchange_atlassian_code(code: str) -> dict:
    response = requests.post(
        "https://auth.atlassian.com/oauth/token",
        json={
            "grant_type": "authorization_code",
            "client_id": settings.atlassian_client_id,
            "client_secret": settings.atlassian_client_secret,
            "code": code,
            "redirect_uri": settings.atlassian_redirect_uri,
        },
        timeout=15,
    )
    if not response.ok or not response.json().get("access_token"):
        raise HTTPException(status_code=400, detail="Jira OAuth failed.")
    data = response.json()
    access_token = data["access_token"]
    resources = requests.get(
        "https://api.atlassian.com/oauth/token/accessible-resources",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=15,
    )
    if not resources.ok or not resources.json():
        raise HTTPException(status_code=400, detail="No Jira site found for this Atlassian account.")
    site = resources.json()[0]
    me = requests.get(
        f"https://api.atlassian.com/ex/jira/{site['id']}/rest/api/3/myself",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=15,
    )
    profile = me.json() if me.ok else {}
    return {
        "access_token": access_token,
        "refresh_token": data.get("refresh_token"),
        "expires_at": _expiry(data.get("expires_in")),
        "cloud_id": site["id"],
        "site_url": site.get("url"),
        "site_name": site.get("name") or site.get("url"),
        "provider_account_id": profile.get("accountId"),
        "provider_account_email": profile.get("emailAddress"),
    }


def refresh_atlassian_token(refresh_token: str) -> dict:
    response = requests.post(
        "https://auth.atlassian.com/oauth/token",
        json={
            "grant_type": "refresh_token",
            "client_id": settings.atlassian_client_id,
            "client_secret": settings.atlassian_client_secret,
            "refresh_token": refresh_token,
        },
        timeout=15,
    )
    if not response.ok:
        raise HTTPException(status_code=401, detail="Jira connection expired. Please reconnect.")
    data = response.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token") or refresh_token,
        "expires_at": _expiry(data.get("expires_in")),
    }
