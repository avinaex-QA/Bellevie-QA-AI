"""
Detects the software module/domain from requirement text and builds
enriched context for the AI prompt.
"""
import re
from typing import Tuple

MODULE_KEYWORDS: dict[str, list[str]] = {
    "Authentication": [
        "login", "logout", "sign in", "sign out", "authenticate", "password",
        "forgot password", "reset password", "2fa", "two-factor", "sso",
        "oauth", "session", "token", "jwt", "register", "signup", "sign up",
    ],
    "Payment": [
        "payment", "checkout", "billing", "invoice", "credit card", "debit card",
        "paypal", "stripe", "refund", "transaction", "subscription", "pricing",
        "cart", "purchase", "buy", "order", "wallet", "bank",
    ],
    "Dashboard": [
        "dashboard", "overview", "analytics", "metrics", "kpi", "report",
        "chart", "graph", "widget", "summary", "statistics", "insights",
    ],
    "User Management": [
        "user", "profile", "account", "settings", "preferences", "roles",
        "permissions", "admin", "manage users", "user list", "deactivate",
    ],
    "Search": [
        "search", "filter", "sort", "query", "find", "results", "pagination",
        "autocomplete", "suggestions", "browse",
    ],
    "Notifications": [
        "notification", "alert", "email", "sms", "push notification",
        "reminder", "subscribe", "unsubscribe", "digest",
    ],
    "File Management": [
        "upload", "download", "file", "document", "attachment", "export",
        "import", "pdf", "csv", "excel",
    ],
    "API": [
        "api", "endpoint", "rest", "graphql", "webhook", "integration",
        "request", "response", "payload", "json", "xml",
    ],
    "Onboarding": [
        "onboarding", "wizard", "setup", "welcome", "tutorial", "guide",
        "first time", "getting started",
    ],
    "E-Commerce": [
        "product", "catalog", "inventory", "stock", "shipping", "delivery",
        "tracking", "returns", "wishlist", "review", "rating",
    ],
}


def detect_module(text: str) -> str:
    """Returns the best-matching module name for the given requirement text."""
    if not text:
        return "General"

    text_lower = text.lower()
    scores: dict[str, int] = {}

    for module, keywords in MODULE_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            scores[module] = count

    if not scores:
        return "General"

    return max(scores, key=lambda k: scores[k])


def build_context(
    requirements: str,
    source_type: str,
    module: str | None = None,
    additional_context: str = "",
) -> Tuple[str, str]:
    """
    Returns (enriched_requirements, detected_module).
    Prepends source metadata and cleans whitespace.
    """
    detected_module = module or detect_module(requirements)
    clean_text = re.sub(r"\n{3,}", "\n\n", requirements.strip())

    meta = f"[Source: {source_type.upper()} | Module: {detected_module}]\n\n"
    if additional_context:
        meta += f"Additional Context: {additional_context}\n\n"

    return meta + clean_text, detected_module
