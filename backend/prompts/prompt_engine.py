"""
Builds the final prompt sent to the AI model.
Combines context, templates, and source-specific enrichment.
"""
from backend.prompts.templates import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    JIRA_ENRICHMENT_PROMPT,
    DIFF_ANALYSIS_PROMPT,
)
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class PromptEngine:
    """Assembles prompts for different input sources."""

    def build_generation_prompt(
        self,
        requirements: str,
        module: str,
        source_type: str,
    ) -> tuple[str, str]:
        """
        Returns (system_prompt, user_prompt) ready to send to the AI.
        """
        user_prompt = USER_PROMPT_TEMPLATE.format(
            requirements=requirements,
            module=module,
            source_type=source_type,
        )
        logger.debug(f"Built generation prompt for module={module}, source={source_type}")
        return SYSTEM_PROMPT, user_prompt

    def build_jira_enrichment_prompt(
        self,
        summary: str,
        description: str,
        acceptance_criteria: str,
        comments: list[str],
        status: str,
        issue_type: str,
    ) -> tuple[str, str]:
        """Returns prompts to convert a Jira ticket into a requirements document."""
        system = (
            "You are a Business Analyst extracting structured testing requirements "
            "from a Jira ticket. Be thorough and precise."
        )
        user = JIRA_ENRICHMENT_PROMPT.format(
            summary=summary,
            description=description or "Not provided",
            acceptance_criteria=acceptance_criteria or "Not provided",
            comments="\n".join(comments) if comments else "No comments",
            status=status,
            issue_type=issue_type,
        )
        return system, user

    def build_diff_analysis_prompt(
        self,
        diff: str,
        title: str,
        description: str,
    ) -> tuple[str, str]:
        """Returns prompts to convert a Git diff into a requirements document."""
        system = (
            "You are a Senior QA Engineer analyzing a code change to determine "
            "what needs to be tested. Focus on impact and risk."
        )
        # Truncate diff if too large (keep first 8000 chars)
        truncated_diff = diff[:8000] + "\n...[truncated]" if len(diff) > 8000 else diff
        user = DIFF_ANALYSIS_PROMPT.format(
            diff=truncated_diff,
            title=title,
            description=description or "Not provided",
        )
        return system, user


prompt_engine = PromptEngine()
