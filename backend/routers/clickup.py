"""
ClickUp API routes.
"""
from fastapi import APIRouter, Depends, HTTPException

from backend.models.schemas import ClickUpTask
from backend.services.clickup_service import ClickUpCredentials, fetch_clickup_task
from backend.security.auth import get_current_user
from backend.services.integration_runtime import require_runtime_integration
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


@router.get("/task/{task_id}", response_model=ClickUpTask)
async def get_clickup_task(task_id: str, current_user=Depends(get_current_user)):
    try:
        config = require_runtime_integration(current_user["id"], "clickup")
        return fetch_clickup_task(task_id, ClickUpCredentials(
            api_token=config.get("access_token") or config.get("api_token"),
            api_base=config.get("api_base", "https://api.clickup.com/api/v2"),
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"ClickUp task fetch failed: {exc}")
        raise HTTPException(status_code=502, detail="Unable to fetch ClickUp task.")
