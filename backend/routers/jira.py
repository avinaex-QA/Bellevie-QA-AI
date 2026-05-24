"""
/api/jira endpoints — Jira ticket preview and validation.
"""
from fastapi import APIRouter, Depends, HTTPException
from backend.models.schemas import BugDraftRequest, BugDraftResponse, JiraBugCreateRequest, JiraBugCreateResponse, JiraTicket
from backend.services.ai_service import generate_bug_draft
from backend.services.integration_store import get_integration, require_integration
from backend.services.integration_runtime import require_runtime_integration
from backend.services.jira_service import JiraCredentials, create_jira_bug, fetch_jira_ticket
from backend.security.auth import get_current_user
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


def _jira_credentials(user_id: str) -> JiraCredentials:
    config = require_runtime_integration(user_id, "jira")
    return JiraCredentials(
        base_url=config.get("base_url") or config.get("site_url"),
        email=config.get("email"),
        api_token=config.get("api_token"),
        bug_project_key=config.get("bug_project_key"),
        access_token=config.get("access_token"),
        cloud_id=config.get("cloud_id") or config.get("provider_workspace_id"),
        site_url=config.get("site_url"),
    )


def _current_user_id(current_user) -> str | None:
    return current_user.get("id") if isinstance(current_user, dict) else None


@router.get("/fetch/{ticket_id}", response_model=JiraTicket)
async def get_jira_ticket(ticket_id: str, current_user=Depends(get_current_user)):
    """
    Fetch and preview a Jira ticket by ID.
    Used by the frontend to display ticket details before generating test cases.
    """
    try:
        user_id = _current_user_id(current_user)
        ticket = fetch_jira_ticket(ticket_id.strip().upper(), _jira_credentials(user_id) if user_id else None)
        return ticket
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Jira fetch failed for {ticket_id}: {e}")
        error_msg = str(e)
        if "401" in error_msg or "403" in error_msg:
            raise HTTPException(
                status_code=401,
                detail="Jira authentication failed. Check JIRA_EMAIL and JIRA_API_TOKEN in .env"
            )
        if "404" in error_msg:
            raise HTTPException(
                status_code=404,
                detail=f"Jira ticket '{ticket_id}' not found. Check the ticket ID."
            )
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch Jira ticket: {error_msg}"
        )


@router.get("/validate")
async def validate_jira_config(current_user=Depends(get_current_user)):
    """
    Check whether Jira credentials are configured (does not make an API call).
    """
    user_id = _current_user_id(current_user)
    config = get_integration(user_id, "jira") if user_id else {}
    configured = bool((config.get("base_url") and config.get("email") and config.get("api_token")) or (config.get("access_token") and config.get("cloud_id")))
    return {
        "configured": configured,
        "base_url": config.get("base_url") or config.get("site_url"),
        "email": config.get("email") or config.get("provider_account_email"),
    }


@router.post("/bug-draft", response_model=BugDraftResponse)
async def create_bug_draft(request: BugDraftRequest, current_user=Depends(get_current_user)):
    """Generate an editable Jira bug draft for a failed test case."""
    if request.test_case.jira_bug_id:
        raise HTTPException(status_code=409, detail="Bug already raised for this test case.")
    if request.test_case.status.lower() != "failed":
        raise HTTPException(status_code=400, detail="Bug can be raised only for failed test cases.")
    user_id = _current_user_id(current_user)
    return await generate_bug_draft(request, ai_config=get_integration(user_id, "ai") if user_id else None)


@router.post("/create-bug", response_model=JiraBugCreateResponse)
async def create_bug(request: JiraBugCreateRequest, current_user=Depends(get_current_user)):
    """Create a Jira Bug using backend Jira credentials only."""
    if not request.bug_summary.strip():
        raise HTTPException(status_code=400, detail="Bug Summary is required.")
    if not request.description.strip():
        raise HTTPException(status_code=400, detail="Description is required.")
    if not request.steps_to_reproduce:
        raise HTTPException(status_code=400, detail="Steps to Reproduce are required.")
    if not request.actual_result.strip():
        raise HTTPException(status_code=400, detail="Actual Result is required.")
    if not request.expected_result.strip():
        raise HTTPException(status_code=400, detail="Expected Result is required.")

    try:
        user_id = _current_user_id(current_user)
        return create_jira_bug(request, _jira_credentials(user_id) if user_id else None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Jira bug creation failed: {e}")
        error_msg = str(e)
        if "401" in error_msg or "403" in error_msg:
            raise HTTPException(status_code=401, detail="Jira authentication failed. Check Jira credentials.")
        if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
            raise HTTPException(status_code=504, detail="Jira request timed out. Please try again.")
        raise HTTPException(status_code=502, detail="Could not create Jira bug. Please check field mapping and Jira configuration.")
