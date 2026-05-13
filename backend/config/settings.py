"""
Application configuration loaded from environment variables / .env file.
"""
import os
from typing import Optional

from pydantic_settings import BaseSettings


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
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    debug: bool = True
    log_level: str = "INFO"

    def model_post_init(self, __context: object) -> None:
        render_port = os.getenv("PORT")
        if render_port:
            self.app_host = "0.0.0.0"
            if not os.getenv("APP_PORT"):
                self.app_port = int(render_port)

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
