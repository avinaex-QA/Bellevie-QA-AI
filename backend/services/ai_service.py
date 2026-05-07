"""
AI service — Google Gemini (gemini-flash-latest).
Uses COVERAGE-DRIVEN generation: no hard limits, test count is derived
from requirement complexity.
"""
import asyncio
import json
import re
from typing import List

from google import genai
from google.genai import types

from backend.config.settings import settings
from backend.models.schemas import TestCase, TestSummary
from backend.utils.context_builder import build_context
from backend.utils.deduplicator import deduplicate, renumber_ids
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

# ── Gemini client ──────────────────────────────────────────────────────────
GEMINI_API_KEY = "AIzaSyD0D6MT7Xyl1O5C9wNsHPZx8is5OwOYPEA"
GEMINI_MODEL   = "gemini-flash-latest"
_client        = genai.Client(api_key=GEMINI_API_KEY)

# ── System instruction ─────────────────────────────────────────────────────
_SYSTEM = (
    "You are a Senior QA Engineer and Test Architect with 10+ years of production experience. "
    "You think in terms of COMPLETE COVERAGE — every user flow, every validation, every failure mode. "
    "You write test cases that catch real production bugs. "
    "You ALWAYS return only valid JSON with no markdown fences, no explanation text."
)

# ── Coverage-driven user prompt ────────────────────────────────────────────
_PROMPT_TEMPLATE = """Analyze the requirements below and generate test cases for COMPLETE COVERAGE.

===== REQUIREMENTS =====
{requirements}
========================
Module: {module}  |  Source: {source_type}
{extra}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — COMPLEXITY ANALYSIS (do this internally before generating)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Identify and count every testable dimension:
A. User flows / journeys      (each distinct path a user can take)
B. Input fields / validations  (every field with rules)
C. Business rules              (every conditional, constraint, calculation)
D. Integration points          (API calls, DB ops, 3rd-party services)
E. UI states                   (loading, empty, error, success, disabled, modal)
F. Error / exception paths     (network fail, timeout, invalid state, concurrency)
G. Security boundaries         (auth checks, permission levels, injection surfaces)
H. Data variations             (types, lengths, formats, languages, edge values)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — COVERAGE FORMULA (determines test count naturally)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For EACH item identified above, generate:
• User flow (happy path)    → 1 test per flow
• User flow (negative)      → 2-3 tests per flow (wrong input, missing step, unauthorized)
• Input validation          → 4-5 tests per field (valid, empty, too-long, special chars, boundary)
• Business rule             → 2-4 tests per rule (rule met, rule violated, boundary, ambiguous)
• Integration point         → 4-6 tests (success, failure, timeout, invalid response, retry)
• UI state                  → 1-3 tests per state
• Error path                → 2-3 tests per error scenario
• Security boundary         → 3-5 tests (valid auth, no auth, wrong role, injection, CSRF)
• Data variation            → 2-4 tests per data type concern

The total count EMERGES from complexity — never forced, never capped.
A feature with 10 flows + 12 validations + 3 integrations should yield 80-130 tests.
A simple feature with 2 flows + 3 validations should yield 20-35 tests.
{min_instruction}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — TEST CASE CATEGORIES (cover ALL of these)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Functional      — happy path, core journeys working end-to-end
2. Negative        — invalid inputs, wrong data types, missing required fields
3. Edge Case       — empty states, null, max length, special chars, unicode, whitespace-only
4. Boundary Value  — min-1, min, min+1, max-1, max, max+1 for numeric and length limits
5. UI/UX           — error messages, loading states, empty screens, tooltips, disabled states
6. API             — correct status codes, response schema, auth headers, rate limiting
7. Security        — XSS payloads, SQL injection, auth bypass, broken access control
8. Regression      — existing features that could be broken by this change
9. Error Handling  — network failures, server errors, partial responses, retries
10. Data Integrity — correct persistence, no data loss, correct calculations

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUALITY RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Every step must be a specific, atomic action — NO vague steps like "fill in the form"
• Expected results must be MEASURABLE — "Error message reads: 'Email is required'" not "error appears"
• NO duplicate or near-duplicate tests
• NO low-quality filler tests to reach a number
• Each test must test exactly ONE thing

Priority assignment:
  High   → blocks critical user flows, data loss risk, auth failure, payment, security
  Medium → important feature, degraded but workaround exists
  Low    → cosmetic, minor UX, non-blocking edge cases

Tag assignment (1-3 per test):
  Smoke      → 8-12 most critical tests (core functionality sanity check)
  Regression → verifies existing behaviour is not broken
  Sanity     → quick post-deployment verification
  API        → backend/API-specific tests
  Security   → security validation tests

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — return ONLY this JSON (no markdown, no extra text):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "complexity_analysis": {{
    "user_flows": 5,
    "input_validations": 8,
    "business_rules": 3,
    "integrations": 2,
    "ui_states": 6,
    "error_paths": 4,
    "security_boundaries": 3,
    "data_variations": 5
  }},
  "test_cases": [
    {{
      "id": "TC-001",
      "priority": "High",
      "title": "Verify successful login with valid email and password",
      "preconditions": "A registered user account exists. Application is accessible at the login URL.",
      "steps": [
        "Navigate to the application login page",
        "Enter a valid registered email address in the Email field",
        "Enter the correct password in the Password field",
        "Click the Login button"
      ],
      "expected_result": "User is authenticated and redirected to /dashboard. Welcome message 'Hello, [name]' is visible. Session cookie is set with HttpOnly flag.",
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
}}"""


def _build_min_instruction() -> str:
    if settings.enable_min_limit and settings.min_test_cases > 0:
        return (
            f"\nMINIMUM COVERAGE FLOOR: Ensure at least {settings.min_test_cases} test cases total. "
            f"If natural coverage yields fewer, expand with: additional data variations "
            f"(null, empty, unicode, very long strings), cross-field validation combinations, "
            f"session/state-based scenarios, and concurrent-user scenarios. "
            f"Quality over quantity — never add meaningless filler.\n"
        )
    return ""


# ── JSON / response parsing ────────────────────────────────────────────────
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


def _parse_response(raw: str) -> tuple[List[TestCase], TestSummary, dict]:
    cleaned = _strip_markdown(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            logger.error(f"Unparseable response (first 400 chars): {cleaned[:400]}")
            raise ValueError(
                "Gemini returned a non-JSON response. "
                "Try adding more specific requirements and retry."
            )
        data = json.loads(match.group())

    raw_cases = data.get("test_cases", [])
    if not raw_cases:
        raise ValueError(
            "No test cases were generated. "
            "The requirements may be too vague. Please add more detail."
        )

    test_cases: List[TestCase] = []
    for idx, tc in enumerate(raw_cases, start=1):
        steps = _normalize_steps(tc.get("steps", []))
        tags  = tc.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        try:
            test_cases.append(TestCase(
                id=tc.get("id", f"TC-{idx:03d}"),
                priority=tc.get("priority", "Medium"),
                title=tc.get("title", f"Test Case {idx}"),
                preconditions=tc.get("preconditions", ""),
                steps=steps,
                expected_result=tc.get("expected_result", ""),
                actual_result="",
                tags=tags,
                test_type=tc.get("test_type", "Functional"),
            ))
        except Exception as e:
            logger.warning(f"Skipping malformed test case #{idx}: {e}")

    test_cases = deduplicate(test_cases)
    test_cases = renumber_ids(test_cases)

    high   = sum(1 for t in test_cases if t.priority.lower() == "high")
    medium = sum(1 for t in test_cases if t.priority.lower() == "medium")
    low    = sum(1 for t in test_cases if t.priority.lower() == "low")

    summary = TestSummary(
        total=len(test_cases),
        high_priority=high,
        medium_priority=medium,
        low_priority=low,
        module_detected=data.get("module_detected", "General"),
    )
    complexity = data.get("complexity_analysis", {})
    return test_cases, summary, complexity


# ── Gemini call (sync, runs in thread pool) ────────────────────────────────
def _call_gemini_sync(prompt: str) -> str:
    logger.info(f"Calling Gemini: {GEMINI_MODEL}")
    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM,
            temperature=0.35,
            max_output_tokens=16384,  # allow large responses for complex requirements
        ),
    )
    return response.text


# ── Public API ─────────────────────────────────────────────────────────────
async def generate_test_cases(
    requirements: str,
    source_type: str = "text",
    additional_context: str = "",
    module: str | None = None,
) -> tuple[List[TestCase], TestSummary]:
    """
    Coverage-driven test case generation.
    Returns (test_cases, summary). Test count is derived from requirement complexity.
    """
    enriched_requirements, detected_module = build_context(
        requirements=requirements,
        source_type=source_type,
        module=module,
        additional_context=additional_context,
    )

    extra = f"Additional context: {additional_context}" if additional_context else ""
    prompt = _PROMPT_TEMPLATE.format(
        requirements=enriched_requirements,
        module=detected_module,
        source_type=source_type,
        extra=extra,
        min_instruction=_build_min_instruction(),
    )

    logger.info(
        f"Starting coverage-driven generation | "
        f"source={source_type} | module={detected_module} | "
        f"min_limit={'ON ≥'+str(settings.min_test_cases) if settings.enable_min_limit else 'OFF'}"
    )

    raw = await asyncio.to_thread(_call_gemini_sync, prompt)
    test_cases, summary, complexity = _parse_response(raw)

    if complexity:
        logger.info(
            f"Complexity analysis: flows={complexity.get('user_flows', '?')} "
            f"validations={complexity.get('input_validations', '?')} "
            f"integrations={complexity.get('integrations', '?')} "
            f"security={complexity.get('security_boundaries', '?')}"
        )

    logger.info(
        f"Generated {summary.total} test cases "
        f"({summary.high_priority}H / {summary.medium_priority}M / {summary.low_priority}L)"
    )
    return test_cases, summary


async def enrich_with_ai(system: str, user: str) -> str:
    """Generic AI call used by Jira/Git services for text pre-processing."""
    return await asyncio.to_thread(_call_gemini_sync, f"{system}\n\n{user}")
