"""
ClickUp REST API integration.
Fetches task details and normalizes them into requirement text for AI generation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from backend.config.settings import settings
from backend.models.schemas import ClickUpTask
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class ClickUpCredentials:
    api_token: str
    api_base: str = "https://api.clickup.com/api/v2"


def _get_base_url(credentials: ClickUpCredentials | None = None) -> str:
    return (credentials.api_base if credentials else settings.clickup_api_base).rstrip("/")


def _get_headers(credentials: ClickUpCredentials | None = None) -> dict[str, str]:
    token = credentials.api_token if credentials else settings.clickup_api_token
    if not token:
        raise ValueError("CLICKUP_API_TOKEN must be set in .env to use ClickUp integration.")
    return {
        "Authorization": token,
        "Accept": "application/json",
    }


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("name", "username", "email", "value", "label"):
            if value.get(key):
                return _clean_text(value[key])
        return ", ".join(f"{k}: {_stringify_value(v)}" for k, v in value.items() if v)
    if isinstance(value, list):
        return ", ".join(filter(None, (_stringify_value(item) for item in value)))
    return _clean_text(value)


def _format_timestamp(value: Any) -> str:
    if not value:
        return ""
    try:
        timestamp = int(value) / 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return _clean_text(value)


def _extract_status(data: dict[str, Any]) -> str:
    status = data.get("status")
    if isinstance(status, dict):
        return _clean_text(status.get("status") or status.get("type"))
    return _clean_text(status)


def _extract_priority(data: dict[str, Any]) -> str:
    priority = data.get("priority")
    if isinstance(priority, dict):
        return _clean_text(priority.get("priority") or priority.get("color") or priority.get("id"))
    return _clean_text(priority)


def _extract_assignee(data: dict[str, Any]) -> str:
    assignees = data.get("assignees") or []
    if not isinstance(assignees, list):
        return _stringify_value(assignees)
    names = []
    for assignee in assignees:
        if isinstance(assignee, dict):
            names.append(_clean_text(assignee.get("username") or assignee.get("email") or assignee.get("id")))
    return ", ".join(filter(None, names))


def _extract_tags(data: dict[str, Any]) -> list[str]:
    tags = data.get("tags") or []
    if not isinstance(tags, list):
        return []
    names = []
    for tag in tags:
        if isinstance(tag, dict):
            names.append(_clean_text(tag.get("name")))
        else:
            names.append(_clean_text(tag))
    return [name for name in names if name]


def _extract_checklists(data: dict[str, Any]) -> list[str]:
    checklists = data.get("checklists") or []
    if not isinstance(checklists, list):
        return []

    items: list[str] = []
    for checklist in checklists:
        if not isinstance(checklist, dict):
            continue
        checklist_name = _clean_text(checklist.get("name")) or "Checklist"
        for item in checklist.get("items") or []:
            if not isinstance(item, dict):
                continue
            item_name = _clean_text(item.get("name") or item.get("title"))
            if not item_name:
                continue
            status = "resolved" if item.get("resolved") else "open"
            items.append(f"{checklist_name}: {item_name} ({status})")
    return items


def _extract_custom_fields(data: dict[str, Any]) -> dict[str, str]:
    fields = data.get("custom_fields") or []
    if not isinstance(fields, list):
        return {}

    normalized: dict[str, str] = {}
    for field in fields:
        if not isinstance(field, dict):
            continue
        name = _clean_text(field.get("name") or field.get("id"))
        value = _stringify_value(field.get("value"))
        if name and value:
            normalized[name] = value
    return normalized


def _extract_dependencies(data: dict[str, Any]) -> list[str]:
    candidates = []
    for key in ("dependencies", "linked_tasks"):
        value = data.get(key)
        if isinstance(value, list):
            candidates.extend(value)

    dependencies: list[str] = []
    for item in candidates:
        if isinstance(item, dict):
            dep_id = _clean_text(item.get("task_id") or item.get("id") or item.get("links_to"))
        else:
            dep_id = _clean_text(item)
        if dep_id:
            dependencies.append(dep_id)
    return list(dict.fromkeys(dependencies))


def _fetch_comments(task_id: str, headers: dict[str, str], credentials: ClickUpCredentials | None = None) -> list[str]:
    try:
        response = requests.get(
            f"{_get_base_url(credentials)}/task/{task_id}/comment",
            headers=headers,
            timeout=10,
        )
        if not response.ok:
            return []
        data = response.json()
    except (requests.RequestException, ValueError):
        return []

    comments = data.get("comments") or []
    normalized: list[str] = []
    if not isinstance(comments, list):
        return normalized

    for comment in comments[:10]:
        if not isinstance(comment, dict):
            continue
        text = _clean_text(comment.get("comment_text") or comment.get("comment"))
        user = comment.get("user") or {}
        author = _clean_text(user.get("username") if isinstance(user, dict) else "")
        if text and author:
            normalized.append(f"{author}: {text}")
        elif text:
            normalized.append(text)
    return normalized


def _build_raw_text(task: ClickUpTask) -> str:
    parts = [
        f"ClickUp Task: {task.task_id}",
        f"Title: {task.title}",
        f"Status: {task.status or 'Unknown'}",
        f"Priority: {task.priority or 'Unset'}",
        f"Assignee: {task.assignee or 'Unassigned'}",
    ]
    if task.created_date:
        parts.append(f"Created Date: {task.created_date}")
    if task.due_date:
        parts.append(f"Due Date: {task.due_date}")
    if task.tags:
        parts.append(f"Tags: {', '.join(task.tags)}")
    parts += ["", "Description:", task.description or "Not provided"]
    if task.checklists:
        parts += ["", "Checklist Items:", *[f"- {item}" for item in task.checklists]]
    if task.custom_fields:
        parts += ["", "Custom Fields:", *[f"- {key}: {value}" for key, value in task.custom_fields.items()]]
    if task.comments:
        parts += ["", "Comments:", *[f"- {comment}" for comment in task.comments[:10]]]
    if task.dependencies:
        parts += ["", f"Dependencies: {', '.join(task.dependencies)}"]
    return "\n".join(parts)


def _raise_friendly_http_error(response: requests.Response, task_id: str) -> None:
    if response.status_code in {401, 403}:
        raise ValueError("Invalid ClickUp credentials.")
    if response.status_code == 404:
        raise ValueError("ClickUp task not found.")
    if response.status_code == 429:
        raise ValueError("ClickUp rate limit reached. Please try again shortly.")
    raise ValueError(f"Unable to fetch ClickUp task '{task_id}'.")


def fetch_clickup_task(task_id: str, credentials: ClickUpCredentials | None = None) -> ClickUpTask:
    clean_task_id = _clean_text(task_id)
    if not clean_task_id:
        raise ValueError("ClickUp task ID is required.")

    headers = _get_headers(credentials)
    logger.info(f"Fetching ClickUp task: {clean_task_id}")

    try:
        response = requests.get(
            f"{_get_base_url(credentials)}/task/{clean_task_id}",
            headers=headers,
            timeout=15,
        )
    except requests.Timeout as exc:
        raise ValueError("Unable to fetch ClickUp task. ClickUp request timed out.") from exc
    except requests.RequestException as exc:
        raise ValueError("Unable to fetch ClickUp task.") from exc

    if not response.ok:
        _raise_friendly_http_error(response, clean_task_id)

    try:
        data = response.json()
    except ValueError as exc:
        raise ValueError("Malformed ClickUp response.") from exc

    task = ClickUpTask(
        task_id=_clean_text(data.get("id") or clean_task_id),
        title=_clean_text(data.get("name") or "Untitled ClickUp task"),
        description=_clean_text(data.get("text_content") or data.get("description")),
        status=_extract_status(data),
        priority=_extract_priority(data),
        assignee=_extract_assignee(data),
        tags=_extract_tags(data),
        checklists=_extract_checklists(data),
        comments=_fetch_comments(clean_task_id, headers, credentials),
        custom_fields=_extract_custom_fields(data),
        dependencies=_extract_dependencies(data),
        due_date=_format_timestamp(data.get("due_date")),
        created_date=_format_timestamp(data.get("date_created")),
    )
    task.raw_text = _build_raw_text(task)

    has_requirement_content = any([task.title, task.description, task.checklists, task.custom_fields])
    if not has_requirement_content:
        raise ValueError("ClickUp task has no usable requirement content.")

    return task
