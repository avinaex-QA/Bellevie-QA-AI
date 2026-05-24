"""
Project context definitions used to guide AI test generation.
"""
from typing import Iterable


MAX_SELECTED_PROJECTS = 50
MAX_SELECTED_MODULES = 50


VALID_PROJECTS = (
    "Resident APP",
    "Society Dashboard",
    "VMS APP",
    "Society Admin APP",
    "Marketplace Brand Dashboard",
    "Marketplace Master Dashboard",
)

VALID_MODULES = (
    "Onboarding",
    "Ticket",
    "Notice",
    "Event",
    "Amenity",
    "Billing & Account",
    "VMS",
    "Documents",
    "Marketplace",
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

MODULE_CONTEXTS: dict[str, tuple[str, ...]] = {
    "Onboarding": (
        "signup",
        "login",
        "OTP",
        "social login",
        "forgot password",
        "email verification",
        "profile completion",
        "permissions",
        "first-time onboarding",
        "session handling",
        "edge validation",
    ),
    "Ticket": (
        "issue creation",
        "ticket lifecycle",
        "attachments",
        "comments",
        "escalation",
        "SLA",
        "assignment",
        "reopen",
        "closure",
        "search and filter behavior",
    ),
    "Notice": (
        "notice creation",
        "scheduling",
        "audience targeting",
        "push notifications",
        "read and unread states",
        "expiry",
        "attachments",
        "permissions",
    ),
    "Event": (
        "event creation",
        "RSVP",
        "attendee management",
        "reminders",
        "scheduling conflicts",
        "cancellations",
        "notifications",
    ),
    "Amenity": (
        "booking",
        "slot management",
        "approval",
        "payment",
        "cancellation",
        "conflict validation",
        "availability",
        "limits",
    ),
    "Billing & Account": (
        "invoices",
        "dues",
        "payment flows",
        "payment failures",
        "wallet",
        "refunds",
        "statement history",
        "account settings",
        "role permissions",
    ),
    "VMS": (
        "visitor registration",
        "OTP",
        "QR",
        "approvals",
        "gate entry",
        "exit",
        "delivery flow",
        "guard validation",
        "expired pass handling",
    ),
    "Documents": (
        "upload",
        "preview",
        "download",
        "access permissions",
        "versioning",
        "search",
        "delete",
        "file validation",
    ),
    "Marketplace": (
        "product listing",
        "orders",
        "cart",
        "checkout",
        "payment",
        "inventory",
        "coupons",
        "seller workflows",
        "buyer workflows",
        "order lifecycle",
    ),
}

BELLEVIE_CONTEXTS: dict[tuple[str, str], tuple[str, ...]] = {
    ("Resident APP", "Amenity"): (
        "resident apartment amenity booking",
        "slot availability",
        "booking approvals",
        "resident payments and cancellations",
    ),
    ("Resident APP", "Billing & Account"): (
        "resident maintenance payments",
        "dues visibility",
        "invoice history",
        "payment failure recovery",
    ),
    ("VMS APP", "VMS"): (
        "visitor management end-to-end",
        "security gate validation",
        "QR and OTP entry",
        "expired pass handling",
    ),
    ("Society Admin APP", "Ticket"): (
        "admin issue handling",
        "assignment and escalation",
        "resident communication",
        "ticket closure and reopen flows",
    ),
    ("Society Dashboard", "Notice"): (
        "web notice management",
        "audience targeting",
        "read visibility",
        "role-based publishing",
    ),
    ("Society Dashboard", "Event"): (
        "event dashboard management",
        "RSVP reporting",
        "attendee lists",
        "cancellation communication",
    ),
    ("Marketplace Brand Dashboard", "Marketplace"): (
        "seller catalog workflows",
        "order management",
        "inventory and payout visibility",
        "seller analytics",
    ),
    ("Marketplace Master Dashboard", "Marketplace"): (
        "super admin marketplace governance",
        "tenant and seller controls",
        "audit logs",
        "global marketplace reporting",
    ),
}


def normalize_selected_projects(projects: Iterable[str] | None) -> list[str]:
    """
    Trim, deduplicate, and preserve user-selected project names.
    Known Bellevie projects still receive enriched context; custom projects
    are accepted so user-managed frontend options can flow through generation.
    """
    raw_projects = _normalize_user_values(projects)
    if not raw_projects:
        raise ValueError("Please select at least one project.")
    if len(raw_projects) > MAX_SELECTED_PROJECTS:
        raise ValueError("Maximum 50 projects allowed.")
    return raw_projects


def normalize_selected_modules(modules: Iterable[str] | None) -> list[str]:
    """
    Trim, deduplicate, and preserve user-selected module names.
    Known Bellevie modules still receive enriched context; custom modules are
    accepted so user-managed frontend options can flow through generation.
    """
    raw_modules = _normalize_user_values(modules)
    if not raw_modules:
        raise ValueError("Please select at least one module.")
    if len(raw_modules) > MAX_SELECTED_MODULES:
        raise ValueError("Maximum 50 modules allowed.")
    return raw_modules


def _normalize_user_values(values: Iterable[str] | None) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = " ".join(str(value).strip().split())
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


def _merged_focus(selected: Iterable[str], context_map: dict[str, tuple[str, ...]]) -> tuple[list[str], list[str]]:
    focus_items: list[str] = []
    detail_lines: list[str] = []
    seen: set[str] = set()

    for item_name in selected:
        context_items = context_map.get(item_name)
        if not context_items:
            detail_lines.append(f"- {item_name}: user-defined context")
            continue
        detail_lines.append(f"- {item_name}: {', '.join(context_items)}")
        for context_item in context_items:
            key = context_item.lower()
            if key not in seen:
                seen.add(key)
                focus_items.append(context_item)

    return focus_items, detail_lines


def build_context_section(projects: Iterable[str], modules: Iterable[str]) -> str:
    selected_projects = normalize_selected_projects(projects)
    selected_modules = normalize_selected_modules(modules)

    project_focus, project_lines = _merged_focus(selected_projects, PROJECT_CONTEXTS)
    module_focus, module_lines = _merged_focus(selected_modules, MODULE_CONTEXTS)

    bellevie_focus: list[str] = []
    seen_bellevie: set[str] = set()
    for project in selected_projects:
        for module in selected_modules:
            for item in BELLEVIE_CONTEXTS.get((project, module), ()):
                key = item.lower()
                if key not in seen_bellevie:
                    seen_bellevie.add(key)
                    bellevie_focus.append(item)

    lines = [
        "===== BELLEVIE PRODUCT CONTEXT =====",
        f"Selected projects: {', '.join(selected_projects)}",
        f"Selected modules: {', '.join(selected_modules)}",
        "",
        "Product context:",
        *project_lines,
        "",
        "Module context:",
        *module_lines,
        "",
        "Merged product focus:",
        ", ".join(project_focus),
        "",
        "Merged module focus:",
        ", ".join(module_focus),
    ]

    if bellevie_focus:
        lines.extend([
            "",
            "Bellevie-specific scenario focus:",
            ", ".join(bellevie_focus),
        ])

    lines.extend([
        "",
        "Use the project context as the product layer and module context as the feature layer.",
        "Generate realistic Bellevie test coverage for roles, permissions, platform behavior,",
        "negative flows, edge validation, integrations, notifications, exports, and regression risk.",
        "Do not generate test cases from context alone; use it only to enrich supplied requirements.",
        "====================================",
    ])
    return "\n".join(lines)


def build_project_context_section(projects: Iterable[str]) -> str:
    """Backward-compatible project-only section for older call sites/tests."""
    selected_projects = normalize_selected_projects(projects)
    project_focus, project_lines = _merged_focus(selected_projects, PROJECT_CONTEXTS)
    return "\n".join([
        "===== PROJECT CONTEXT =====",
        f"Selected projects: {', '.join(selected_projects)}",
        "",
        "Apply these domain-specific testing priorities when designing coverage:",
        *project_lines,
        "",
        "Merged coverage focus:",
        ", ".join(project_focus),
        "",
        "Use this context to choose scenarios, tags, priorities, edge cases, permissions,",
        "platform-specific behavior, integrations, negative flows, and regression coverage.",
        "Do not generate test cases from project context alone; use it only to enrich the supplied requirements.",
        "===========================",
    ])
