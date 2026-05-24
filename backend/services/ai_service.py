"""
AI service — Multi Provider (Groq + OpenAI + Gemini + DeepSeek)
Coverage-driven AI test case generation.
"""

import asyncio
import json
import re
import os
from typing import List

import requests
from openai import OpenAI
from google import genai
from google.genai import types

from backend.config.env_loader import load_env_file
from backend.config.project_context import build_context_section, build_project_context_section
from backend.models.schemas import BugDraftRequest, BugDraftResponse, TestCase, TestSummary
from backend.utils.context_builder import build_context
from backend.utils.deduplicator import deduplicate, renumber_ids
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

# ── ENV LOAD ──────────────────────────────────────────────────────────────
load_env_file()

# ── AI Provider Selection ────────────────────────────────────────────────
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq").lower()

# ── GROQ Configuration ───────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = None

if GROQ_API_KEY:
    groq_client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )

# ── OpenAI Configuration ────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = None

if OPENAI_API_KEY:
    openai_client = OpenAI(
        api_key=OPENAI_API_KEY
    )

# ── DeepSeek Configuration ──────────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
deepseek_client = None

if DEEPSEEK_API_KEY:
    deepseek_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )

# ── Gemini Configuration ────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash"
gemini_client = None

if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ── System Instruction ──────────────────────────────────────────────────
_SYSTEM = (
    "You are a Senior QA Engineer and Test Architect with 10+ years of production experience. "
    "You think in terms of COMPLETE COVERAGE — every user flow, every validation, every failure mode. "
    "You write test cases that catch real production bugs. "
    "Return ONLY valid JSON. No markdown. No explanations."
)

# ── Prompt Template ─────────────────────────────────────────────────────
_PROMPT_TEMPLATE = """
Analyze the requirements below and generate COMPLETE QA test coverage.

===== REQUIREMENTS =====
{requirements}
========================

Module: {module}
Source: {source_type}

{extra}

Generate:
1. Functional tests
2. Negative tests
3. Boundary tests
4. Edge cases
5. API tests
6. Security tests
7. Regression tests
8. UI/UX validation tests

Return ONLY JSON:

{{
  "test_cases": [
    {{
      "id": "TC-001",
      "priority": "High",
      "title": "Verify login with valid credentials",
      "preconditions": "User account exists",
      "steps": ["Step 1", "Step 2"],
      "expected_result": "User logs in successfully",
      "actual_result": "",
      "tags": ["Smoke", "Regression"],
      "test_type": "Functional"
    }}
  ],
  "module_detected": "{module}",
  "summary": {{
    "total": 0,
    "high_priority": 0,
    "medium_priority": 0,
    "low_priority": 0
  }}
}}
"""

# ── Helpers ─────────────────────────────────────────────────────────────
def _strip_markdown(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _normalize_steps(steps_raw) -> List[str]:
    if isinstance(steps_raw, list):
        return [str(s).strip() for s in steps_raw if str(s).strip()]

    if isinstance(steps_raw, str):
        parts = re.split(r"\n|\r\n|\d+\.\s+", steps_raw)
        return [p.strip() for p in parts if p.strip()]

    return [str(steps_raw)]


# ── AI CALL ──────────────────────────────────────────────────────────────
def _call_ai_sync(prompt: str, ai_config: dict | None = None) -> str:
    provider = (ai_config or {}).get("provider", AI_PROVIDER).lower()
    api_key = (ai_config or {}).get("api_key")
    logger.info(f"Using AI Provider: {provider}")

    # GROQ
    if provider == "groq":
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1") if api_key else groq_client
        if not client:
            raise ValueError("GROQ_API_KEY not configured")

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4000,
        )

        return response.choices[0].message.content

    # OPENAI
    elif provider == "openai":
        client = OpenAI(api_key=api_key) if api_key else openai_client
        if not client:
            raise ValueError("OPENAI_API_KEY not configured")

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4000,
        )

        return response.choices[0].message.content

    # DEEPSEEK
    elif provider == "deepseek":
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com") if api_key else deepseek_client
        if not client:
            raise ValueError("DEEPSEEK_API_KEY not configured")

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4000,
        )

        return response.choices[0].message.content

    # GEMINI
    elif provider == "gemini":
        client = genai.Client(api_key=api_key) if api_key else gemini_client
        if not client:
            raise ValueError("GEMINI_API_KEY not configured")

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM,
                temperature=0.35,
                max_output_tokens=8192,
            ),
        )

        return response.text

    elif provider == "claude":
        anthropic_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-3-5-sonnet-latest",
                "system": _SYSTEM,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4000,
            },
            timeout=60,
        )
        response.raise_for_status()
        content = response.json().get("content", [])
        return "".join(part.get("text", "") for part in content if part.get("type") == "text")

    else:
        raise ValueError(f"Unsupported AI provider: {provider}")


# ── Response Parser ─────────────────────────────────────────────────────
def _parse_response(raw: str):
    cleaned = _strip_markdown(raw)

    try:
        data = json.loads(cleaned)

    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)

        if not match:
            logger.error(f"Invalid AI response: {cleaned[:500]}")
            raise ValueError("AI returned invalid JSON response")

        data = json.loads(match.group())

    raw_cases = data.get("test_cases", [])

    if not raw_cases:
        raise ValueError("No test cases generated")

    test_cases: List[TestCase] = []

    for idx, tc in enumerate(raw_cases, start=1):
        steps = _normalize_steps(tc.get("steps", []))
        tags = tc.get("tags", [])

        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        test_cases.append(
            TestCase(
                id=tc.get("id", f"TC-{idx:03d}"),
                priority=tc.get("priority", "Medium"),
                title=tc.get("title", f"Test Case {idx}"),
                preconditions=tc.get("preconditions", ""),
                steps=steps,
                expected_result=tc.get("expected_result", ""),
                actual_result="",
                tags=tags,
                test_type=tc.get("test_type", "Functional"),
            )
        )

    test_cases = deduplicate(test_cases)
    test_cases = renumber_ids(test_cases)

    high = sum(1 for t in test_cases if t.priority.lower() == "high")
    medium = sum(1 for t in test_cases if t.priority.lower() == "medium")
    low = sum(1 for t in test_cases if t.priority.lower() == "low")

    summary = TestSummary(
        total=len(test_cases),
        high_priority=high,
        medium_priority=medium,
        low_priority=low,
        module_detected=data.get("module_detected", "General"),
    )

    return test_cases, summary


def _infer_bug_type(test_case: TestCase, projects: list[str], modules: list[str]) -> str:
    haystack = " ".join([test_case.title, test_case.test_type, *test_case.tags, *projects, *modules]).lower()
    if "api" in haystack or "backend" in haystack:
        return "API" if "api" in haystack else "Backend"
    if "mobile" in haystack or "app" in haystack or "resident app" in haystack or "vms app" in haystack:
        return "Mobile"
    return "Frontend"


def _infer_device_type(projects: list[str]) -> str:
    joined = " ".join(projects).lower()
    if "app" in joined:
        return "Mobile"
    return "Web"


def _infer_vertical(projects: list[str]) -> str:
    joined = " ".join(projects).lower()
    if "marketplace" in joined:
        return "Marketplace"
    return "Residential"


def _fallback_bug_draft(request: BugDraftRequest) -> BugDraftResponse:
    test_case = request.test_case
    projects = request.selected_projects
    modules = request.selected_modules
    module_text = ", ".join(modules)
    project_text = ", ".join(projects)
    notes = request.execution_notes or request.tester_notes or test_case.actual_result or "Observed behavior did not match expected result."

    return BugDraftResponse(
        bug_summary=f"{project_text}: {test_case.title}",
        description=(
            f"Failure observed while executing test case {test_case.id}: {test_case.title}.\n"
            f"Project Context: {project_text}\nModule Context: {module_text}"
        ),
        steps_to_reproduce=test_case.steps,
        actual_result=notes,
        expected_result=test_case.expected_result,
        severity="Medium",
        environment="QA",
        project=project_text,
        module=module_text,
        classification="Functionality",
        type=_infer_bug_type(test_case, projects, modules),
        device_type=_infer_device_type(projects),
        impacted_areas=module_text,
        vertical=_infer_vertical(projects),
        additional_notes=request.tester_notes,
    )


def _parse_bug_draft(raw: str, fallback: BugDraftResponse) -> BugDraftResponse:
    cleaned = _strip_markdown(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return fallback
        data = json.loads(match.group())

    merged = fallback.model_dump()
    for key, value in data.items():
        if key in merged and value not in (None, ""):
            merged[key] = value
    if isinstance(merged.get("steps_to_reproduce"), str):
        merged["steps_to_reproduce"] = _normalize_steps(merged["steps_to_reproduce"])
    return BugDraftResponse(**merged)


async def generate_bug_draft(request: BugDraftRequest, ai_config: dict | None = None) -> BugDraftResponse:
    fallback = _fallback_bug_draft(request)
    context = build_context_section(request.selected_projects, request.selected_modules)
    test_case = request.test_case

    prompt = f"""
Create a concise Jira Bug draft for Bellevie QA from this failed test case.
Return ONLY valid JSON with these keys:
bug_summary, description, steps_to_reproduce, actual_result, expected_result,
severity, environment, project, module, classification, type, device_type,
impacted_areas, app_version, vertical, reviewer, sprint, additional_notes,
likely_root_cause.

{context}

Test Case:
ID: {test_case.id}
Title: {test_case.title}
Type: {test_case.test_type}
Priority: {test_case.priority}
Preconditions: {test_case.preconditions}
Steps: {json.dumps(test_case.steps)}
Expected Result: {test_case.expected_result}

Failure Notes:
Execution notes: {request.execution_notes or test_case.execution_notes}
Tester notes: {request.tester_notes or test_case.tester_comments}
Source context: {json.dumps(request.source_info)[:1200]}
"""
    try:
        raw = await asyncio.to_thread(_call_ai_sync, prompt, ai_config) if ai_config else await asyncio.to_thread(_call_ai_sync, prompt)
        return _parse_bug_draft(raw, fallback)
    except Exception as e:
        logger.warning(f"AI bug draft fallback used: {e}")
        return fallback


# ── Public API ──────────────────────────────────────────────────────────
async def generate_test_cases(
    requirements: str,
    source_type: str = "text",
    additional_context: str = "",
    module: str | None = None,
    selected_projects: list[str] | None = None,
    selected_modules: list[str] | None = None,
    ai_config: dict | None = None,
):
    enriched_requirements, detected_module = build_context(
        requirements=requirements,
        source_type=source_type,
        module=module,
        additional_context=additional_context,
    )

    if selected_modules:
        extra_parts = [build_context_section(selected_projects or [], selected_modules)]
    else:
        extra_parts = [build_project_context_section(selected_projects or [])]
    if additional_context:
        extra_parts.append(f"Additional context: {additional_context}")
    extra = "\n\n".join(extra_parts)

    prompt = _PROMPT_TEMPLATE.format(
        requirements=enriched_requirements,
        module=detected_module,
        source_type=source_type,
        extra=extra,
    )

    logger.info(
        f"Generating test cases | provider={(ai_config or {}).get('provider', AI_PROVIDER)} | module={detected_module}"
    )

    raw = await asyncio.to_thread(_call_ai_sync, prompt, ai_config) if ai_config else await asyncio.to_thread(_call_ai_sync, prompt)
    test_cases, summary = _parse_response(raw)

    logger.info(f"Generated {summary.total} test cases")

    return test_cases, summary


# ── Generic AI helper ───────────────────────────────────────────────────
async def enrich_with_ai(system: str, user: str, ai_config: dict | None = None) -> str:
    prompt = f"{system}\n\n{user}"
    return await asyncio.to_thread(_call_ai_sync, prompt, ai_config) if ai_config else await asyncio.to_thread(_call_ai_sync, prompt)
