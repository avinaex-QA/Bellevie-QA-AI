"""
Application configuration loaded from environment variables / .env file.
"""
import os
from typing import Optional

from backend.config.env_loader import load_env_file

load_env_file()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return int(value)

class Settings:
    def __init__(self) -> None:
        # Database / security
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./local_saas.db")
        self.app_secret_key: str = os.getenv("APP_SECRET_KEY", "local-dev-change-me")
        self.encryption_key: Optional[str] = os.getenv("ENCRYPTION_KEY")
        self.session_cookie_name: str = os.getenv("SESSION_COOKIE_NAME", "qa_copilot_session")
        self.session_expire_hours: int = _get_int("SESSION_EXPIRE_HOURS", 168)
        self.app_base_url: str = os.getenv("APP_BASE_URL", "http://localhost:8000").rstrip("/")
        self.frontend_base_url: str = os.getenv("FRONTEND_BASE_URL", self.app_base_url).rstrip("/")

        # OTP
        self.otp_expire_minutes: int = _get_int("OTP_EXPIRE_MINUTES", 10)
        self.otp_max_attempts: int = _get_int("OTP_MAX_ATTEMPTS", 5)
        self.otp_max_resends: int = _get_int("OTP_MAX_RESENDS", 3)

        # Email delivery
        self.resend_api_key: Optional[str] = os.getenv("RESEND_API_KEY")
        self.email_from: str = os.getenv("EMAIL_FROM", "onboarding@resend.dev")

        self.smtp_host: Optional[str] = os.getenv("SMTP_HOST")
        self.smtp_port: int = _get_int("SMTP_PORT", 587)
        self.smtp_username: Optional[str] = os.getenv("SMTP_USERNAME")
        self.smtp_password: Optional[str] = os.getenv("SMTP_PASSWORD")
        self.smtp_from: str = os.getenv("SMTP_FROM", self.email_from)

        self.email_dev_mode: bool = _get_bool("EMAIL_DEV_MODE", False)

        # AI Provider
        self.ai_provider: str = os.getenv("AI_PROVIDER", "gemini")
        self.anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.max_tokens: int = _get_int("MAX_TOKENS", 8192)

        # Jira
        self.jira_base_url: Optional[str] = os.getenv("JIRA_BASE_URL")
        self.jira_email: Optional[str] = os.getenv("JIRA_EMAIL")
        self.jira_api_token: Optional[str] = os.getenv("JIRA_API_TOKEN")
        self.jira_bug_project_key: Optional[str] = (
            os.getenv("JIRA_BUG_PROJECT_KEY")
            or os.getenv("JIRA_DEFAULT_PROJECT_KEY")
        )

        # ClickUp
        self.clickup_api_token: Optional[str] = os.getenv("CLICKUP_API_TOKEN")
        self.clickup_api_base: str = os.getenv(
            "CLICKUP_API_BASE",
            "https://api.clickup.com/api/v2",
        ).rstrip("/")

        # GitHub
        self.github_token: Optional[str] = os.getenv("GITHUB_TOKEN")

        # OAuth
        self.google_client_id: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
        self.google_redirect_uri: str = os.getenv(
            "GOOGLE_REDIRECT_URI",
            f"{self.app_base_url}/auth/google/callback",
        )

        self.github_client_id: Optional[str] = os.getenv("GITHUB_CLIENT_ID")
        self.github_client_secret: Optional[str] = os.getenv("GITHUB_CLIENT_SECRET")
        self.github_redirect_uri: str = os.getenv(
            "GITHUB_REDIRECT_URI",
            f"{self.app_base_url}/oauth/github/callback",
        )

        self.atlassian_client_id: Optional[str] = os.getenv("ATLASSIAN_CLIENT_ID")
        self.atlassian_client_secret: Optional[str] = os.getenv("ATLASSIAN_CLIENT_SECRET")
        self.atlassian_redirect_uri: str = os.getenv(
            "ATLASSIAN_REDIRECT_URI",
            f"{self.app_base_url}/oauth/jira/callback",
        )

        self.clickup_client_id: Optional[str] = os.getenv("CLICKUP_CLIENT_ID")
        self.clickup_client_secret: Optional[str] = os.getenv("CLICKUP_CLIENT_SECRET")
        self.clickup_redirect_uri: str = os.getenv(
            "CLICKUP_REDIRECT_URI",
            f"{self.app_base_url}/oauth/clickup/callback",
        )

        # Coverage
        self.min_test_cases: int = _get_int("MIN_TEST_CASES", 20)
        self.enable_min_limit: bool = _get_bool("ENABLE_MIN_LIMIT", False)

        # Excel
        self.auto_open_excel: bool = _get_bool("AUTO_OPEN_EXCEL", False)

        # App
        render_port = os.getenv("PORT")
        self.app_host: str = "0.0.0.0" if render_port else os.getenv("APP_HOST", "127.0.0.1")
        self.app_port: int = int(render_port) if render_port else _get_int("APP_PORT", 8000)
        self.debug: bool = _get_bool("DEBUG", True)
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()