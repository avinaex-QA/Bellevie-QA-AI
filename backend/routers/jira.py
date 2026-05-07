"""
/api/jira endpoints — Jira ticket preview and validation.
"""
from fastapi import APIRouter, HTTPException
from backend.models.schemas import JiraTicket
from backend.services.jira_service import fetch_jira_ticket
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
