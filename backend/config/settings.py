"""
Application configuration loaded from environment variables / .env file.
"""
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


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
        # AI Provider
        self.ai_provider: str = os.getenv("AI_PROVIDER", "gemini")
        self.anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.max_tokens: int = _get_int("MAX_TOKENS", 8192)

        # Jira
        self.jira_base_url: Optional[str] = os.getenv("JIRA_BASE_URL")
        self.jira_email: Optional[str] = os.getenv("JIRA_EMAIL")
        self.jira_api_token: Optional[str] = os.getenv("JIRA_API_TOKEN")

        # GitHub
        self.github_token: Optional[str] = os.getenv("GITHUB_TOKEN")

        # Coverage-driven test generation
        self.min_test_cases: int = _get_int("MIN_TEST_CASES", 20)
        self.enable_min_limit: bool = _get_bool("ENABLE_MIN_LIMIT", False)

        # Excel auto-open (Windows only via os.startfile)
        self.auto_open_excel: bool = _get_bool("AUTO_OPEN_EXCEL", False)

        # Application
        render_port = os.getenv("PORT")
        self.app_host: str = "0.0.0.0" if render_port else os.getenv("APP_HOST", "127.0.0.1")
        self.app_port: int = int(render_port) if render_port else _get_int("APP_PORT", 8000)
        self.debug: bool = _get_bool("DEBUG", True)
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
