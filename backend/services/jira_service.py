"""
Jira REST API integration.
Fetches ticket summary, description, acceptance criteria, and comments.
"""
import re
import requests
from requests.auth import HTTPBasicAuth

from backend.config.settings import settings
from backend.models.schemas import JiraTicket
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

# Common Jira custom field names for Acceptance Criteria
AC_FIELDS = [
    "customfield_10016",  # Most common in Jira Cloud
    "customfield_10014",
    "customfield_10021",
    "customfield_10028",
    "customfield_10034",
    "customfield_10100",
]


def _get_auth() -> HTTPBasicAuth:
    if not settings.jira_email or not settings.jira_api_token:
        raise ValueError(
            "JIRA_EMAIL and JIRA_API_TOKEN must be set in .env to use Jira integration."
        )
    return HTTPBasicAuth(settings.jira_email, settings.jira_api_token)


def _get_base_url() -> str:
    if not settings.jira_base_url:
        raise ValueError("JIRA_BASE_URL must be set in .env (e.g. https://company.atlassian.net)")
    return settings.jira_base_url.rstrip("/")


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


def fetch_jira_ticket(ticket_id: str) -> JiraTicket:
    """
    Fetches a Jira issue by ID and returns a structured JiraTicket.
    Raises ValueError on auth errors or missing configuration.
    Raises requests.HTTPError on API errors.
    """
    base_url = _get_base_url()
    auth = _get_auth()

    # Fetch main issue
    issue_url = f"{base_url}/rest/api/3/issue/{ticket_id}"
    logger.info(f"Fetching Jira ticket: {ticket_id}")

    resp = requests.get(
        issue_url,
        auth=auth,
        headers={"Accept": "application/json"},
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
    comments = _fetch_comments(base_url, auth, ticket_id, fields)

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


def _fetch_comments(base_url: str, auth: HTTPBasicAuth, ticket_id: str, fields: dict) -> list[str]:
    """Extract comments from embedded fields or fetch from comments API."""
    comments_data = fields.get("comment", {})

    if isinstance(comments_data, dict):
        raw_comments = comments_data.get("comments", [])
    else:
        # Fallback: call comments endpoint
        try:
            url = f"{base_url}/rest/api/3/issue/{ticket_id}/comment"
            resp = requests.get(url, auth=auth, headers={"Accept": "application/json"}, timeout=10)
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
