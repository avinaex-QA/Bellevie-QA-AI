"""
Application configuration loaded from environment variables / .env file.
"""
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings  # type: ignore


class Settings(BaseSettings):
    # AI Provider
    ai_provider: str = "gemini"
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    max_tokens: int = 8192

    # Jira
    jira_base_url: Optional[str] = None
    jira_email: Optional[str] = None
    jira_api_token: Optional[str] = None

    # GitHub
    github_token: Optional[str] = None

    # Coverage-driven test generation
    min_test_cases: int = 20        # only enforced when enable_min_limit=True
    enable_min_limit: bool = False  # set to true to enforce minimum

    # Excel auto-open (Windows only via os.startfile)
    auto_open_excel: bool = False

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
