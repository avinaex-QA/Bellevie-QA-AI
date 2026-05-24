"""
Jira REST API integration.
Fetches ticket summary, description, acceptance criteria, and comments.
"""
import re
from dataclasses import dataclass
import requests
from requests.auth import HTTPBasicAuth

from backend.config.jira_bug_fields import get_bug_field_map
from backend.config.settings import settings
from backend.models.schemas import JiraBugCreateRequest, JiraBugCreateResponse, JiraTicket
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class JiraCredentials:
    base_url: str | None = None
    email: str | None = None
    api_token: str | None = None
    bug_project_key: str | None = None
    access_token: str | None = None
    cloud_id: str | None = None
    site_url: str | None = None

# Common Jira custom field names for Acceptance Criteria
AC_FIELDS = [
    "customfield_10016",  # Most common in Jira Cloud
    "customfield_10014",
    "customfield_10021",
    "customfield_10028",
    "customfield_10034",
    "customfield_10100",
]


def _is_oauth(credentials: JiraCredentials | None = None) -> bool:
    return bool(credentials and credentials.access_token and credentials.cloud_id)


def _get_auth(credentials: JiraCredentials | None = None) -> HTTPBasicAuth | None:
    if _is_oauth(credentials):
        return None
    email = credentials.email if credentials else settings.jira_email
    api_token = credentials.api_token if credentials else settings.jira_api_token
    if not email or not api_token:
        raise ValueError(
            "JIRA_EMAIL and JIRA_API_TOKEN must be set in .env to use Jira integration."
        )
    return HTTPBasicAuth(email, api_token)


def _get_base_url(credentials: JiraCredentials | None = None) -> str:
    if _is_oauth(credentials):
        return f"https://api.atlassian.com/ex/jira/{credentials.cloud_id}"
    base_url = credentials.base_url if credentials else settings.jira_base_url
    if not base_url:
        raise ValueError("JIRA_BASE_URL must be set in .env (e.g. https://company.atlassian.net)")
    return base_url.rstrip("/")


def _headers(credentials: JiraCredentials | None = None, content_type: bool = False) -> dict:
    headers = {"Accept": "application/json"}
    if content_type:
        headers["Content-Type"] = "application/json"
    if _is_oauth(credentials):
        headers["Authorization"] = f"Bearer {credentials.access_token}"
    return headers


def _browse_base_url(credentials: JiraCredentials | None = None) -> str:
    if credentials and credentials.site_url:
        return credentials.site_url.rstrip("/")
    return _get_base_url(credentials)


def _strip_jira_markup(text: str) -> str:
    """Remove Jira wiki markup and Atlassian Document Format (ADF) noise."""
    if not text:
        return ""
    # Remove {color:...} tags
    text = re.sub(r"\{color[^}]*\}", "", text)
    text = re.sub(r"\{/color\}", "", text)
    # Remove {panel}, {quote}, etc.
    text = re.sub(r"\{[a-zA-Z][^}]*\}", "", text)
    # Normalize whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_acceptance_criteria(fields: dict) -> str:
    """Try multiple custom field locations to find acceptance criteria."""
    for field_name in AC_FIELDS:
        value = fields.get(field_name)
        if value and isinstance(value, str):
            return _strip_jira_markup(value)
        if value and isinstance(value, dict):
            # ADF format — extract plain text
            return _extract_adf_text(value)
    return ""


def _extract_adf_text(adf: dict) -> str:
    """Recursively extract plain text from Atlassian Document Format JSON."""
    if not isinstance(adf, dict):
        return str(adf)
    text_parts = []
    if adf.get("type") == "text":
        text_parts.append(adf.get("text", ""))
    for child in adf.get("content", []):
        text_parts.append(_extract_adf_text(child))
    return " ".join(filter(None, text_parts)).strip()


def _text_to_adf(text: str) -> dict:
    paragraphs = []
    for line in (text or "").splitlines():
        clean = line.strip()
        if not clean:
            continue
        paragraphs.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": clean}],
        })
    if not paragraphs:
        paragraphs.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": "No description provided."}],
        })
    return {
        "type": "doc",
        "version": 1,
        "content": paragraphs,
    }


def _jira_field_value(value: str):
    clean = str(value or "").strip()
    if not clean:
        return None
    return {"value": clean}


def _infer_project_key(source_issue_key: str | None = None, credentials: JiraCredentials | None = None) -> str:
    configured_project = credentials.bug_project_key if credentials else settings.jira_bug_project_key
    if configured_project:
        return configured_project.strip().upper()
    if source_issue_key and "-" in source_issue_key:
        return source_issue_key.split("-", 1)[0].strip().upper()
    raise ValueError("JIRA_BUG_PROJECT_KEY must be set to create Jira bugs.")


def _build_bug_description(request: JiraBugCreateRequest) -> str:
    steps = "\n".join(f"{idx}. {step}" for idx, step in enumerate(request.steps_to_reproduce, 1))
    sections = [
        f"Description:\n{request.description}",
        f"Steps to Reproduce:\n{steps or 'Not provided'}",
        f"Actual Result:\n{request.actual_result}",
        f"Expected Result:\n{request.expected_result}",
        f"Environment: {request.environment}",
        f"Severity: {request.severity}",
        f"Project Context: {request.project}",
        f"Module Context: {request.module}",
        f"Classification: {request.classification}",
        f"Type: {request.type}",
        f"Device Type: {request.device_type}",
    ]
    optional = [
        ("Impacted Areas", request.impacted_areas),
        ("App Version", request.app_version),
        ("Vertical", request.vertical),
        ("Reviewer", request.reviewer),
        ("Sprint", request.sprint),
        ("Likely Root Cause", request.likely_root_cause),
        ("Additional Notes", request.additional_notes),
    ]
    for label, value in optional:
        if value:
            sections.append(f"{label}: {value}")
    return "\n\n".join(sections)


def create_jira_bug(request: JiraBugCreateRequest, credentials: JiraCredentials | None = None) -> JiraBugCreateResponse:
    """
    Create a Jira Bug from a failed test case using backend-only credentials.
    Custom field IDs are supplied by backend/config/jira_bug_fields.py or env.
    """
    base_url = _get_base_url(credentials)
    auth = _get_auth(credentials)
    project_key = _infer_project_key(request.source_issue_key, credentials)
    field_map = get_bug_field_map()

    fields: dict = {
        "project": {"key": project_key},
        "issuetype": {"name": "Bug"},
        "summary": request.bug_summary.strip(),
        "description": _text_to_adf(_build_bug_description(request)),
    }

    custom_values = {
        "severity": request.severity,
        "module": request.module,
        "classification": request.classification,
        "environment": request.environment,
        "device_type": request.device_type,
        "impacted_areas": request.impacted_areas,
        "app_version": request.app_version,
        "vertical": request.vertical,
        "reviewer": request.reviewer,
        "sprint": request.sprint,
    }
    for key, value in custom_values.items():
        jira_field = field_map.get(key)
        jira_value = _jira_field_value(value)
        if jira_field and jira_value:
            fields[jira_field] = jira_value

    response = requests.post(
        f"{base_url}/rest/api/3/issue",
        auth=auth,
        headers=_headers(credentials, content_type=True),
        json={"fields": fields},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    issue_key = data["key"]
    issue_url = f"{_browse_base_url(credentials)}/browse/{issue_key}"
    return JiraBugCreateResponse(
        success=True,
        issue_key=issue_key,
        issue_url=issue_url,
        message=f"Bug created successfully: {issue_key}",
    )


def _build_raw_text(ticket: JiraTicket) -> str:
    """Combine all ticket fields into a single requirements string for AI processing."""
    parts = [
        f"Jira Ticket: {ticket.ticket_id}",
        f"Issue Type: {ticket.issue_type}",
        f"Summary: {ticket.summary}",
        "",
        "Description:",
        ticket.description or "Not provided",
    ]
    if ticket.acceptance_criteria:
        parts += ["", "Acceptance Criteria:", ticket.acceptance_criteria]
    if ticket.comments:
        parts += ["", "Comments / Discussion:"]
        parts += [f"- {c}" for c in ticket.comments[:10]]  # cap at 10 comments
    return "\n".join(parts)


def fetch_jira_ticket(ticket_id: str, credentials: JiraCredentials | None = None) -> JiraTicket:
    """
    Fetches a Jira issue by ID and returns a structured JiraTicket.
    Raises ValueError on auth errors or missing configuration.
    Raises requests.HTTPError on API errors.
    """
    base_url = _get_base_url(credentials)
    auth = _get_auth(credentials)

    # Fetch main issue
    issue_url = f"{base_url}/rest/api/3/issue/{ticket_id}"
    logger.info(f"Fetching Jira ticket: {ticket_id}")

    resp = requests.get(
        issue_url,
        auth=auth,
        headers=_headers(credentials),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    fields = data.get("fields", {})

    # Description may be ADF (dict) or plain text (str)
    raw_desc = fields.get("description", "")
    if isinstance(raw_desc, dict):
        description = _extract_adf_text(raw_desc)
    else:
        description = _strip_jira_markup(raw_desc or "")

    acceptance_criteria = _extract_acceptance_criteria(fields)

    # Priority
    priority_obj = fields.get("priority") or {}
    priority = priority_obj.get("name", "") if isinstance(priority_obj, dict) else ""

    # Labels
    labels = fields.get("labels", []) or []

    # Issue type
    issuetype = fields.get("issuetype") or {}
    issue_type = issuetype.get("name", "") if isinstance(issuetype, dict) else ""

    # Status
    status_obj = fields.get("status") or {}
    status = status_obj.get("name", "") if isinstance(status_obj, dict) else ""

    # Fetch comments
    comments = _fetch_comments(base_url, auth, ticket_id, fields, credentials)

    ticket = JiraTicket(
        ticket_id=ticket_id.upper(),
        summary=fields.get("summary", ""),
        description=description,
        acceptance_criteria=acceptance_criteria,
        comments=comments,
        status=status,
        priority=priority,
        issue_type=issue_type,
        labels=labels,
    )
    ticket.raw_text = _build_raw_text(ticket)
    return ticket


def _fetch_comments(base_url: str, auth: HTTPBasicAuth | None, ticket_id: str, fields: dict, credentials: JiraCredentials | None = None) -> list[str]:
    """Extract comments from embedded fields or fetch from comments API."""
    comments_data = fields.get("comment", {})

    if isinstance(comments_data, dict):
        raw_comments = comments_data.get("comments", [])
    else:
        # Fallback: call comments endpoint
        try:
            url = f"{base_url}/rest/api/3/issue/{ticket_id}/comment"
            resp = requests.get(url, auth=auth, headers=_headers(credentials), timeout=10)
            resp.raise_for_status()
            raw_comments = resp.json().get("comments", [])
        except Exception as e:
            logger.warning(f"Could not fetch comments for {ticket_id}: {e}")
            return []

    result = []
    for comment in raw_comments:
        body = comment.get("body", "")
        if isinstance(body, dict):
            text = _extract_adf_text(body)
        else:
            text = _strip_jira_markup(str(body))
        if text:
            result.append(text)

    return result
