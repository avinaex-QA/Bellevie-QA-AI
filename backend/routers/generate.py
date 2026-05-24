"""
/api/generate endpoint — core test case generation from all input sources.
Accepts: Jira ID, file upload, raw text, GitHub PR URL (or any combination).
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.config.project_context import normalize_selected_modules, normalize_selected_projects
from backend.models.schemas import GenerateResponse, TestSummary
from backend.services.ai_service import generate_test_cases
from backend.services.clickup_service import fetch_clickup_task
from backend.services.document_service import extract_text_from_upload
from backend.services.jira_service import fetch_jira_ticket
from backend.services.git_service import summarize_pr_as_requirements
from backend.services.integration_store import get_integration, require_integration
from backend.services.integration_runtime import require_runtime_integration
from backend.services.jira_service import JiraCredentials
from backend.services.clickup_service import ClickUpCredentials
from backend.security.auth import get_current_user
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


def _friendly_ai_error(error: Exception) -> str:
    raw = str(error)
    lowered = raw.lower()

    if "invalid_api_key" in lowered or "invalid api key" in lowered or "401" in lowered:
        return (
            "AI provider authentication failed. Please verify the configured API key "
            "for the selected AI provider and restart the server."
        )

    if "api_key not configured" in lowered:
        return (
            "AI provider API key is not configured. Please add the required key in "
            "your environment settings and restart the server."
        )

    return f"AI test case generation failed: {raw}"


def _clean_optional_form_value(value: Optional[str]) -> str:
    return value.strip() if isinstance(value, str) else ""


def _current_user_id(current_user) -> str | None:
    return current_user.get("id") if isinstance(current_user, dict) else None


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    selected_projects: list[str] = Form(default=[]),
    selected_modules: list[str] = Form(default=[]),
    jira_id: Optional[str] = Form(None),
    clickup_task_id: Optional[str] = Form(None),
    text_input: Optional[str] = Form(None),
    github_pr_url: Optional[str] = Form(None),
    additional_context: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user=Depends(get_current_user),
):
    """
    Generate test cases from one or more input sources.
    Sources are merged together and sent to the AI in a single enriched prompt.
    """
    requirement_parts: list[str] = []
    source_info: dict = {}
    source_types: list[str] = []
    clean_clickup_task_id = _clean_optional_form_value(clickup_task_id)
    raw_has_clickup_task = bool(clean_clickup_task_id)
    user_id = _current_user_id(current_user)

    if raw_has_clickup_task and (not selected_projects or not selected_modules):
        raise HTTPException(
            status_code=400,
            detail="Please select Project and Module along with ClickUp task.",
        )

    try:
        selected_projects = normalize_selected_projects(selected_projects)
        selected_modules = normalize_selected_modules(selected_modules)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ── 1. Jira ticket ─────────────────────────────────────────────────────
    if jira_id and jira_id.strip():
        try:
            logger.info(f"Fetching Jira ticket: {jira_id.strip()}")
            credentials = None
            if user_id:
                jira_config = require_runtime_integration(user_id, "jira")
                credentials = JiraCredentials(
                    base_url=jira_config.get("base_url") or jira_config.get("site_url"),
                    email=jira_config.get("email"),
                    api_token=jira_config.get("api_token"),
                    bug_project_key=jira_config.get("bug_project_key"),
                    access_token=jira_config.get("access_token"),
                    cloud_id=jira_config.get("cloud_id") or jira_config.get("provider_workspace_id"),
                    site_url=jira_config.get("site_url"),
                )
            ticket = fetch_jira_ticket(jira_id.strip().upper(), credentials)
            requirement_parts.append(ticket.raw_text)
            source_types.append("jira")
            source_info["jira"] = {
                "ticket_id": ticket.ticket_id,
                "summary": ticket.summary,
                "status": ticket.status,
                "issue_type": ticket.issue_type,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Jira fetch error: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Could not fetch Jira ticket '{jira_id}': {str(e)}"
            )

    # ── 2. ClickUp task ────────────────────────────────────────────────────
    if clean_clickup_task_id:
        try:
            logger.info(f"Fetching ClickUp task: {clean_clickup_task_id}")
            credentials = None
            if user_id:
                clickup_config = require_runtime_integration(user_id, "clickup")
                credentials = ClickUpCredentials(
                    api_token=clickup_config.get("access_token") or clickup_config.get("api_token"),
                    api_base=clickup_config.get("api_base", "https://api.clickup.com/api/v2"),
                )
            task = fetch_clickup_task(clean_clickup_task_id, credentials) if credentials else fetch_clickup_task(clean_clickup_task_id)
            requirement_parts.append(task.raw_text)
            source_types.append("clickup")
            source_info["clickup"] = {
                "task_id": task.task_id,
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "assignee": task.assignee,
                "tags": task.tags,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"ClickUp fetch error: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Could not fetch ClickUp task '{clean_clickup_task_id}': {str(e)}"
            )

    # ── 3. Document upload ─────────────────────────────────────────────────
    if file and file.filename:
        try:
            logger.info(f"Processing uploaded file: {file.filename}")
            doc_text = await extract_text_from_upload(file)
            requirement_parts.append(f"--- Document: {file.filename} ---\n{doc_text}")
            source_types.append("document")
            source_info["document"] = {"filename": file.filename, "chars": len(doc_text)}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Document processing error: {e}")
            raise HTTPException(status_code=422, detail=f"Document processing failed: {str(e)}")

    # ── 4. Raw text input ─────────────────────────────────────────────────
    if text_input and text_input.strip():
        requirement_parts.append(f"--- Requirements Text ---\n{text_input.strip()}")
        source_types.append("text")
        source_info["text"] = {"chars": len(text_input.strip())}

    # ── 5. GitHub PR ──────────────────────────────────────────────────────
    if github_pr_url and github_pr_url.strip():
        try:
            logger.info(f"Fetching GitHub PR: {github_pr_url.strip()}")
            github_config = require_runtime_integration(user_id, "github") if user_id else {}
            ai_config = get_integration(user_id, "ai") if user_id else None
            pr_requirements = await summarize_pr_as_requirements(
                github_pr_url.strip(),
                token=github_config.get("token") or github_config.get("access_token"),
                ai_config=ai_config,
            )
            requirement_parts.append(f"--- GitHub PR Analysis ---\n{pr_requirements}")
            source_types.append("github_pr")
            source_info["github_pr"] = {"url": github_pr_url.strip()}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"GitHub PR fetch error: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Could not fetch GitHub PR: {str(e)}"
            )

    # ── Validate at least one source provided ─────────────────────────────
    if not requirement_parts:
        raise HTTPException(
            status_code=400,
            detail="Please select Project, Module, and at least one requirement source (Jira, ClickUp, Text, Document, or GitHub PR)."
        )

    # ── Combine all sources and generate ─────────────────────────────────
    combined_requirements = "\n\n".join(requirement_parts)
    source_type = "_".join(source_types) if source_types else "text"

    try:
        generation_kwargs = {
            "requirements": combined_requirements,
            "source_type": source_type,
            "additional_context": additional_context or "",
            "selected_projects": selected_projects,
            "selected_modules": selected_modules,
        }
        ai_config = get_integration(user_id, "ai") if user_id else None
        if ai_config:
            generation_kwargs["ai_config"] = ai_config
        test_cases, summary = await generate_test_cases(**generation_kwargs)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"AI generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=_friendly_ai_error(e)
        )

    return GenerateResponse(
        success=True,
        test_cases=test_cases,
        summary=summary,
        source_info={
            **source_info,
            "selected_projects": selected_projects,
            "selected_modules": selected_modules,
        },
        message=f"Successfully generated {summary.total} test cases from {', '.join(source_types)}.",
    )
