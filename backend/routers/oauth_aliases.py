"""
Local-friendly OAuth callback aliases without the /api prefix.
"""
from __future__ import annotations

from fastapi import APIRouter, Response

from backend.routers.auth import google_callback
from backend.routers.integrations import clickup_oauth_callback, github_oauth_callback, jira_oauth_callback

router = APIRouter()


@router.get("/auth/google/callback")
async def google_callback_alias(response: Response, code: str | None = None, state: str | None = None, error: str | None = None):
    return await google_callback(response=response, code=code, state=state, error=error)


@router.get("/oauth/github/callback")
async def github_callback_alias(code: str | None = None, state: str | None = None, error: str | None = None):
    return await github_oauth_callback(code=code, state=state, error=error)


@router.get("/oauth/clickup/callback")
async def clickup_callback_alias(code: str | None = None, state: str | None = None, error: str | None = None):
    return await clickup_oauth_callback(code=code, state=state, error=error)


@router.get("/oauth/jira/callback")
async def jira_callback_alias(code: str | None = None, state: str | None = None, error: str | None = None):
    return await jira_oauth_callback(code=code, state=state, error=error)
