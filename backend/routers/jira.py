"""
/api/jira endpoints — Jira ticket preview and validation.
"""
from fastapi import APIRouter, HTTPException
from backend.models.schemas import BugDraftRequest, BugDraftResponse, JiraBugCreateRequest, JiraBugCreateResponse, JiraTicket
from backend.services.ai_service import generate_bug_draft
from backend.services.jira_service import create_jira_bug, fetch_jira_ticket
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


@router.get("/fetch/{ticket_id}", response_model=JiraTicket)
async def get_jira_ticket(ticket_id: str):
    """
    Fetch and preview a Jira ticket by ID.
    Used by the frontend to display ticket details before generating test cases.
    """
    try:
        ticket = fetch_jira_ticket(ticket_id.strip().upper())
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
async def validate_jira_config():
    """
    Check whether Jira credentials are configured (does not make an API call).
    """
    from backend.config.settings import settings
    configured = bool(
        settings.jira_base_url
        and settings.jira_email
        and settings.jira_api_token
    )
    return {
        "configured": configured,
        "base_url": settings.jira_base_url or None,
        "email": settings.jira_email or None,
    }


@router.post("/bug-draft", response_model=BugDraftResponse)
async def create_bug_draft(request: BugDraftRequest):
    """Generate an editable Jira bug draft for a failed test case."""
    if request.test_case.jira_bug_id:
        raise HTTPException(status_code=409, detail="Bug already raised for this test case.")
    if request.test_case.status.lower() != "failed":
        raise HTTPException(status_code=400, detail="Bug can be raised only for failed test cases.")
    return await generate_bug_draft(request)


@router.post("/create-bug", response_model=JiraBugCreateResponse)
async def create_bug(request: JiraBugCreateRequest):
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
        return create_jira_bug(request)
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
