"""
Per-user integration configuration, OAuth connectors, disconnect, and test.
"""
from __future__ import annotations

from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from backend.config.settings import settings
from backend.models.schemas import (
    AiIntegrationConfig,
    ClickUpIntegrationConfig,
    GitHubIntegrationConfig,
    IntegrationSaveResponse,
    IntegrationStatusResponse,
    JiraIntegrationConfig,
    OAuthStartResponse,
)
from backend.security.auth import get_current_user
from backend.services.integration_store import (
    delete_integration,
    get_integration,
    list_status,
    save_connected_integration,
    save_integration,
)
from backend.services.oauth_provider_service import exchange_atlassian_code, exchange_clickup_code, exchange_github_code
from backend.services.oauth_state_service import consume_oauth_state, create_oauth_state

router = APIRouter()


@router.get("", response_model=IntegrationStatusResponse)
async def get_integrations(current_user=Depends(get_current_user)):
    return IntegrationStatusResponse(integrations=list_status(current_user["id"]))


@router.post("/jira", response_model=IntegrationSaveResponse)
async def save_jira(config: JiraIntegrationConfig, current_user=Depends(get_current_user)):
    if not config.base_url.startswith("http"):
        raise HTTPException(status_code=400, detail="Jira base URL must start with http or https.")
    save_integration(current_user["id"], "jira", config.model_dump(), "manual")
    return IntegrationSaveResponse(provider="jira", message="Jira connected successfully.")


@router.post("/clickup", response_model=IntegrationSaveResponse)
async def save_clickup(config: ClickUpIntegrationConfig, current_user=Depends(get_current_user)):
    save_integration(current_user["id"], "clickup", config.model_dump(), "manual")
    return IntegrationSaveResponse(provider="clickup", message="ClickUp connected successfully.")


@router.post("/github", response_model=IntegrationSaveResponse)
async def save_github(config: GitHubIntegrationConfig, current_user=Depends(get_current_user)):
    save_integration(current_user["id"], "github", config.model_dump(), "manual")
    return IntegrationSaveResponse(provider="github", message="GitHub connected successfully.")


@router.post("/ai", response_model=IntegrationSaveResponse)
async def save_ai(config: AiIntegrationConfig, current_user=Depends(get_current_user)):
    provider = config.provider.lower().strip()
    if provider not in {"groq", "openai", "gemini", "claude", "deepseek"}:
        raise HTTPException(status_code=400, detail="Unsupported AI provider.")
    save_integration(current_user["id"], "ai", {"provider": provider, "api_key": config.api_key}, "manual")
    return IntegrationSaveResponse(provider="ai", message=f"{provider.title()} AI provider saved.")


@router.delete("/{provider}")
async def disconnect(provider: str, current_user=Depends(get_current_user)):
    provider = provider.lower()
    if provider not in {"jira", "clickup", "github", "ai"}:
        raise HTTPException(status_code=404, detail="Unknown integration.")
    delete_integration(current_user["id"], provider)
    return {"success": True, "message": f"{provider.title()} disconnected."}


@router.post("/{provider}/test")
async def test_connection(provider: str, current_user=Depends(get_current_user)):
    provider = provider.lower()
    config = get_integration(current_user["id"], provider)
    if not config:
        raise HTTPException(status_code=400, detail=f"{provider.title()} is not connected.")
    try:
        if provider == "github":
            token = config.get("access_token") or config.get("token")
            resp = requests.get("https://api.github.com/user", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        elif provider == "clickup":
            token = config.get("access_token") or config.get("api_token")
            resp = requests.get("https://api.clickup.com/api/v2/team", headers={"Authorization": token}, timeout=10)
        elif provider == "jira":
            if config.get("access_token") and config.get("cloud_id"):
                resp = requests.get(
                    f"https://api.atlassian.com/ex/jira/{config['cloud_id']}/rest/api/3/myself",
                    headers={"Authorization": f"Bearer {config['access_token']}", "Accept": "application/json"},
                    timeout=10,
                )
            else:
                from requests.auth import HTTPBasicAuth

                resp = requests.get(
                    f"{config['base_url'].rstrip('/')}/rest/api/3/myself",
                    auth=HTTPBasicAuth(config["email"], config["api_token"]),
                    headers={"Accept": "application/json"},
                    timeout=10,
                )
        else:
            return {"success": True, "message": "AI provider saved."}
    except requests.RequestException:
        raise HTTPException(status_code=502, detail=f"Unable to test {provider.title()} connection.")
    if not resp.ok:
        raise HTTPException(status_code=400, detail=f"{provider.title()} connection test failed.")
    return {"success": True, "message": f"{provider.title()} connection works."}


@router.get("/oauth/{provider}/start", response_model=OAuthStartResponse)
async def oauth_start(provider: str, current_user=Depends(get_current_user)):
    provider = provider.lower()
    state = create_oauth_state(provider, "connect", user_id=current_user["id"], redirect_after=settings.frontend_base_url)

    if provider == "github":
        configured = bool(settings.github_client_id and settings.github_client_secret)
        params = urlencode({
            "client_id": settings.github_client_id or "local-placeholder",
            "redirect_uri": settings.github_redirect_uri,
            "scope": "repo read:user user:email",
            "state": state,
        })
        return OAuthStartResponse(provider="github", authorization_url=f"https://github.com/login/oauth/authorize?{params}", state=state, configured=configured)

    if provider == "clickup":
        configured = bool(settings.clickup_client_id and settings.clickup_client_secret)
        params = urlencode({
            "client_id": settings.clickup_client_id or "local-placeholder",
            "redirect_uri": settings.clickup_redirect_uri,
            "state": state,
        })
        return OAuthStartResponse(provider="clickup", authorization_url=f"https://app.clickup.com/api?{params}", state=state, configured=configured)

    if provider == "jira":
        configured = bool(settings.atlassian_client_id and settings.atlassian_client_secret)
        params = urlencode({
            "audience": "api.atlassian.com",
            "client_id": settings.atlassian_client_id or "local-placeholder",
            "scope": "read:jira-work read:jira-user write:jira-work offline_access",
            "redirect_uri": settings.atlassian_redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
        })
        return OAuthStartResponse(provider="jira", authorization_url=f"https://auth.atlassian.com/authorize?{params}", state=state, configured=configured)

    raise HTTPException(status_code=404, detail="OAuth provider is not supported.")


@router.get("/oauth/github/callback")
async def github_oauth_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error or not code:
        raise HTTPException(status_code=400, detail="GitHub OAuth failed.")
    state_row = consume_oauth_state(state, "github", "connect")
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=400, detail="GitHub OAuth is not configured locally.")
    data = exchange_github_code(code)
    save_connected_integration(
        state_row["user_id"],
        "github",
        config={"access_token": data["access_token"]},
        auth_type="oauth",
        access_token=data["access_token"],
        provider_account_id=data.get("provider_account_id"),
        provider_account_email=data.get("provider_account_email"),
    )
    return RedirectResponse(settings.frontend_base_url)


@router.get("/oauth/clickup/callback")
async def clickup_oauth_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error or not code:
        raise HTTPException(status_code=400, detail="ClickUp OAuth failed.")
    state_row = consume_oauth_state(state, "clickup", "connect")
    if not settings.clickup_client_id or not settings.clickup_client_secret:
        raise HTTPException(status_code=400, detail="ClickUp OAuth is not configured locally.")
    data = exchange_clickup_code(code)
    save_connected_integration(
        state_row["user_id"],
        "clickup",
        config={"api_token": data["access_token"], "api_base": "https://api.clickup.com/api/v2"},
        auth_type="oauth",
        access_token=data["access_token"],
        provider_workspace_id=data.get("provider_workspace_id"),
        provider_workspace_name=data.get("provider_workspace_name"),
    )
    return RedirectResponse(settings.frontend_base_url)


@router.get("/oauth/jira/callback")
async def jira_oauth_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error or not code:
        raise HTTPException(status_code=400, detail="Jira OAuth failed.")
    state_row = consume_oauth_state(state, "jira", "connect")
    if not settings.atlassian_client_id or not settings.atlassian_client_secret:
        raise HTTPException(status_code=400, detail="Jira OAuth is not configured locally.")
    data = exchange_atlassian_code(code)
    save_connected_integration(
        state_row["user_id"],
        "jira",
        config={
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "cloud_id": data["cloud_id"],
            "site_url": data.get("site_url"),
        },
        auth_type="oauth",
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_at=data.get("expires_at"),
        provider_account_id=data.get("provider_account_id"),
        provider_account_email=data.get("provider_account_email"),
        provider_workspace_id=data.get("cloud_id"),
        provider_workspace_name=data.get("site_name") or data.get("site_url"),
    )
    return RedirectResponse(settings.frontend_base_url)
