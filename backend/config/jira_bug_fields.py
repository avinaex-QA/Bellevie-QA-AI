"""
Config-driven Jira bug field mapping.

Core Jira fields (project, issuetype, summary, description) are always handled
by the Jira service. Custom Bellevie fields can be mapped through the
JIRA_BUG_FIELD_MAP environment variable as JSON, for example:

{
  "severity": "customfield_10071",
  "module": "customfield_10072",
  "classification": "customfield_10073",
  "environment": "customfield_10074",
  "device_type": "customfield_10075"
}
"""
import json
import os


DEFAULT_BUG_FIELD_MAP: dict[str, str] = {
    "severity": "",
    "module": "",
    "classification": "",
    "environment": "",
    "device_type": "",
    "impacted_areas": "",
    "app_version": "",
    "vertical": "",
    "reviewer": "",
    "sprint": "",
}


def get_bug_field_map() -> dict[str, str]:
    raw = os.getenv("JIRA_BUG_FIELD_MAP", "").strip()
    if not raw:
        return DEFAULT_BUG_FIELD_MAP.copy()

    try:
        configured = json.loads(raw)
    except json.JSONDecodeError:
        return DEFAULT_BUG_FIELD_MAP.copy()

    if not isinstance(configured, dict):
        return DEFAULT_BUG_FIELD_MAP.copy()

    mapping = DEFAULT_BUG_FIELD_MAP.copy()
    for key, value in configured.items():
        if key in mapping and isinstance(value, str):
            mapping[key] = value.strip()
    return mapping
