"""
/api/export endpoints:
  POST   /excel                    — generate + download + save + log history
  GET    /history                  — list all past exports
  GET    /download/{filename}      — re-download a saved file
  DELETE /{filename}               — delete a saved file and its history entry
"""
import io
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

from backend.config.project_context import normalize_selected_modules, normalize_selected_projects
from backend.models.schemas import ExportRequest, TestCase
from backend.services.excel_service import (
    EXPORTS_DIR,
    generate_excel,
    load_history,
    remove_history_entry,
)
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


# ── POST /excel ────────────────────────────────────────────────────────────
@router.post("/excel")
async def export_to_excel(request: ExportRequest):
    """
    Generate a formatted Excel file, save it to /exports/, update history,
    and stream it as a download response.
    """
    if not request.test_cases:
        raise HTTPException(status_code=400, detail="No test cases provided for export.")

    try:
        selected_projects = normalize_selected_projects(request.selected_projects)
        selected_modules = normalize_selected_modules(request.selected_modules)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        excel_bytes, file_name = generate_excel(
            test_cases=request.test_cases,
            selected_projects=selected_projects,
            selected_modules=selected_modules,
            project_name=request.project_name,
            sheet_title=request.sheet_title,
            source_type=getattr(request, "source_type", "text"),
            module_detected=getattr(request, "module_detected", "General"),
        )
    except Exception as e:
        logger.error(f"Excel generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Excel export failed: {str(e)}")

    logger.info(f"Streaming download: {file_name} ({len(request.test_cases)} test cases)")

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={file_name}"},
    )


# ── GET /history ───────────────────────────────────────────────────────────
@router.get("/history")
async def get_export_history():
    """Return the full list of past Excel exports (newest first)."""
    history = load_history()
    return history


# ── GET /download/{filename} ───────────────────────────────────────────────
@router.get("/download/{filename}")
async def download_saved_export(filename: str):
    """Re-download a previously saved Excel file by name."""
    # Sanitize: strip any path separators to prevent directory traversal
    safe_name = Path(filename).name
    file_path = EXPORTS_DIR / safe_name

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Export file '{safe_name}' not found. It may have been deleted."
        )

    return FileResponse(
        path=str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={safe_name}"},
    )


# ── DELETE /{filename} ─────────────────────────────────────────────────────
@router.delete("/{filename}")
async def delete_export(filename: str):
    """Delete a saved Excel file and remove its entry from history."""
    safe_name = Path(filename).name
    file_path = EXPORTS_DIR / safe_name

    deleted_file = False
    if file_path.exists():
        file_path.unlink()
        deleted_file = True
        logger.info(f"Deleted export file: {safe_name}")
    else:
        logger.warning(f"Delete requested for non-existent file: {safe_name}")

    remove_history_entry(safe_name)
    logger.info(f"Removed '{safe_name}' from history")

    return {
        "success": True,
        "file_deleted": deleted_file,
        "message": f"'{safe_name}' removed from exports and history.",
    }
