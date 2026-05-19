"""
Project context definitions used to guide AI test generation.
"""
from typing import Iterable


VALID_PROJECTS = (
    "Resident APP",
    "Society Dashboard",
    "VMS APP",
    "Society Admin APP",
    "Marketplace Brand Dashboard",
    "Marketplace Master Dashboard",
)

PROJECT_CONTEXTS: dict[str, tuple[str, ...]] = {
    "Resident APP": (
        "mobile app workflows",
        "resident onboarding",
        "visitor flow",
        "delivery management",
        "SOS",
        "gate pass",
        "profile management",
        "notifications",
        "payments",
        "session handling",
        "mobile permissions",
        "push notifications",
    ),
    "Society Dashboard": (
        "web dashboard workflows",
        "admin controls",
        "reports",
        "analytics",
        "ticket management",
        "search and filter behavior",
        "exports",
        "access control",
        "dashboard widgets",
        "role permissions",
    ),
    "VMS APP": (
        "visitor management",
        "QR flow",
        "approvals",
        "entry and exit",
        "OTP verification",
        "security workflows",
        "gate validation",
        "delivery entries",
    ),
    "Society Admin APP": (
        "admin mobile workflows",
        "approvals",
        "ticket handling",
        "visitor approvals",
        "resident management",
        "announcements",
        "issue management",
    ),
    "Marketplace Brand Dashboard": (
        "seller workflows",
        "order management",
        "catalog management",
        "inventory",
        "payouts",
        "analytics",
        "reporting",
        "role access",
    ),
    "Marketplace Master Dashboard": (
        "super admin workflows",
        "tenant management",
        "global configs",
        "audit logs",
        "access control",
        "marketplace-wide reporting",
        "permissions",
        "integrations",
    ),
}


def normalize_selected_projects(projects: Iterable[str] | None) -> list[str]:
    """
    Trim, validate, deduplicate, and preserve configured project order.
    Raises ValueError with a friendly message for invalid input.
    """
    raw_projects = [str(project).strip() for project in (projects or []) if str(project).strip()]
    if not raw_projects:
        raise ValueError("Please select at least one project.")

    invalid = sorted({project for project in raw_projects if project not in VALID_PROJECTS})
    if invalid:
        raise ValueError(f"Invalid project selection: {', '.join(invalid)}.")

    selected = set(raw_projects)
    return [project for project in VALID_PROJECTS if project in selected]


def build_project_context_section(projects: Iterable[str]) -> str:
    selected_projects = normalize_selected_projects(projects)
    focus_items: list[str] = []
    seen: set[str] = set()

    lines = [
        "===== PROJECT CONTEXT =====",
        f"Selected projects: {', '.join(selected_projects)}",
        "",
        "Apply these domain-specific testing priorities when designing coverage:",
    ]

    for project in selected_projects:
        context_items = PROJECT_CONTEXTS[project]
        lines.append(f"- {project}: {', '.join(context_items)}")
        for item in context_items:
            key = item.lower()
            if key not in seen:
                seen.add(key)
                focus_items.append(item)

    lines.extend([
        "",
        "Merged coverage focus:",
        ", ".join(focus_items),
        "",
        "Use this context to choose scenarios, tags, priorities, edge cases, permissions,",
        "platform-specific behavior, integrations, negative flows, and regression coverage.",
        "Do not generate test cases from project context alone; use it only to enrich the supplied requirements.",
        "===========================",
    ])
    return "\n".join(lines)
