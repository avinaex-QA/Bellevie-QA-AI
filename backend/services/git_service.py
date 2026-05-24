"""
GitHub PR integration service.
Fetches PR metadata and diff, then asks the AI to summarize it as requirements.
"""
import re
import httpx
from backend.config.settings import settings
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


def _parse_github_pr_url(url: str) -> tuple[str, str, str]:
    """
    Parses a GitHub PR URL into (owner, repo, pr_number).
    Supports:
      https://github.com/owner/repo/pull/123
      github.com/owner/repo/pull/123
    """
    pattern = r"(?:https?://)?github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pattern, url.strip())
    if not match:
        raise ValueError(
            f"Invalid GitHub PR URL: '{url}'. "
            "Expected format: https://github.com/owner/repo/pull/123"
        )
    return match.group(1), match.group(2), match.group(3)


def _get_headers(token: str | None = None) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    configured_token = token or settings.github_token
    if configured_token:
        headers["Authorization"] = f"Bearer {configured_token}"
    return headers


async def fetch_pr_diff(pr_url: str, token: str | None = None) -> dict:
    """
    Fetches PR metadata and diff from GitHub.
    Returns dict with keys: title, description, diff, files_changed, additions, deletions.
    """
    owner, repo, pr_number = _parse_github_pr_url(pr_url)
    logger.info(f"Fetching GitHub PR: {owner}/{repo}#{pr_number}")

    headers = _get_headers(token)

    async with httpx.AsyncClient(timeout=20.0) as client:
        # Fetch PR metadata
        meta_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        meta_resp = await client.get(meta_url, headers=headers)
        meta_resp.raise_for_status()
        meta = meta_resp.json()

        # Fetch PR diff
        diff_headers = {**headers, "Accept": "application/vnd.github.diff"}
        diff_resp = await client.get(meta_url, headers=diff_headers)
        diff_resp.raise_for_status()
        diff_text = diff_resp.text

        # Fetch changed files list
        files_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        files_resp = await client.get(files_url, headers=headers)
        files_resp.raise_for_status()
        files_data = files_resp.json()

    files_changed = [f["filename"] for f in files_data]
    additions = meta.get("additions", 0)
    deletions = meta.get("deletions", 0)

    return {
        "title": meta.get("title", ""),
        "description": meta.get("body", "") or "",
        "diff": diff_text,
        "files_changed": files_changed,
        "additions": additions,
        "deletions": deletions,
        "pr_number": pr_number,
        "repo": f"{owner}/{repo}",
    }


async def summarize_pr_as_requirements(pr_url: str, token: str | None = None, ai_config: dict | None = None) -> str:
    """
    High-level function: fetches a PR and returns a plain-text requirements
    summary ready for test case generation.
    """
    from backend.prompts.prompt_engine import prompt_engine
    from backend.services.ai_service import enrich_with_ai

    pr_data = await fetch_pr_diff(pr_url, token)

    system_prompt, user_prompt = prompt_engine.build_diff_analysis_prompt(
        diff=pr_data["diff"],
        title=pr_data["title"],
        description=pr_data["description"],
    )

    files_section = "\n".join(f"  - {f}" for f in pr_data["files_changed"][:20])
    user_prompt += (
        f"\n\nFiles changed (+{pr_data['additions']} -{pr_data['deletions']}):\n{files_section}"
    )

    requirements_text = await enrich_with_ai(system_prompt, user_prompt, ai_config=ai_config)

    # Prefix with PR metadata
    header = (
        f"GitHub PR #{pr_data['pr_number']} | {pr_data['repo']}\n"
        f"Title: {pr_data['title']}\n"
        f"Files Changed: {len(pr_data['files_changed'])} "
        f"(+{pr_data['additions']} -{pr_data['deletions']} lines)\n\n"
    )
    return header + requirements_text
