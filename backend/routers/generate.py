"""
/api/generate endpoint — core test case generation from all input sources.
Accepts: Jira ID, file upload, raw text, GitHub PR URL (or any combination).
"""
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.models.schemas import GenerateResponse, TestSummary
from backend.services.ai_service import generate_test_cases
from backend.services.document_service import extract_text_from_upload
from backend.services.jira_service import fetch_jira_ticket
from backend.services.git_service import summarize_pr_as_requirements
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    jira_id: Optional[str] = Form(None),
    text_input: Optional[str] = Form(None),
    github_pr_url: Optional[str] = Form(None),
    additional_context: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """
    Generate test cases from one or more input sources.
    Sources are merged together and sent to the AI in a single enriched prompt.
    """
    requirement_parts: list[str] = []
    source_info: dict = {}
    source_types: list[str] = []

    # ── 1. Jira ticket ─────────────────────────────────────────────────────
    if jira_id and jira_id.strip():
        try:
            logger.info(f"Fetching Jira ticket: {jira_id.strip()}")
            ticket = fetch_jira_ticket(jira_id.strip().upper())
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

    # ── 2. Document upload ─────────────────────────────────────────────────
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

    # ── 3. Raw text input ─────────────────────────────────────────────────
    if text_input and text_input.strip():
        requirement_parts.append(f"--- Requirements Text ---\n{text_input.strip()}")
        source_types.append("text")
        source_info["text"] = {"chars": len(text_input.strip())}

    # ── 4. GitHub PR ──────────────────────────────────────────────────────
    if github_pr_url and github_pr_url.strip():
        try:
            logger.info(f"Fetching GitHub PR: {github_pr_url.strip()}")
            pr_requirements = await summarize_pr_as_requirements(github_pr_url.strip())
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
            detail="Please provide at least one input: Jira ID, document, text, or GitHub PR URL."
        )

    # ── Combine all sources and generate ─────────────────────────────────
    combined_requirements = "\n\n".join(requirement_parts)
    source_type = "_".join(source_types) if source_types else "text"

    try:
        test_cases, summary = await generate_test_cases(
            requirements=combined_requirements,
            source_type=source_type,
            additional_context=additional_context or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"AI generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI test case generation failed: {str(e)}"
        )

    return GenerateResponse(
        success=True,
        test_cases=test_cases,
        summary=summary,
        source_info=source_info,
        message=f"Successfully generated {summary.total} test cases from {', '.join(source_types)}.",
    )
