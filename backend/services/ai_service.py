"""
AI service — Multi Provider (Groq + OpenAI + Gemini + DeepSeek)
Coverage-driven AI test case generation.
"""

import asyncio
import json
import re
import os
from typing import List

from dotenv import load_dotenv
from openai import OpenAI
from google import genai
from google.genai import types

from backend.models.schemas import TestCase, TestSummary
from backend.utils.context_builder import build_context
from backend.utils.deduplicator import deduplicate, renumber_ids
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

# ── ENV LOAD ──────────────────────────────────────────────────────────────
load_dotenv()

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
def _call_ai_sync(prompt: str) -> str:
    logger.info(f"Using AI Provider: {AI_PROVIDER}")

    # GROQ
    if AI_PROVIDER == "groq":
        if not groq_client:
            raise ValueError("GROQ_API_KEY not configured")

        response = groq_client.chat.completions.create(
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
    elif AI_PROVIDER == "openai":
        if not openai_client:
            raise ValueError("OPENAI_API_KEY not configured")

        response = openai_client.chat.completions.create(
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
    elif AI_PROVIDER == "deepseek":
        if not deepseek_client:
            raise ValueError("DEEPSEEK_API_KEY not configured")

        response = deepseek_client.chat.completions.create(
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
    elif AI_PROVIDER == "gemini":
        if not gemini_client:
            raise ValueError("GEMINI_API_KEY not configured")

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM,
                temperature=0.35,
                max_output_tokens=8192,
            ),
        )

        return response.text

    else:
        raise ValueError(f"Unsupported AI provider: {AI_PROVIDER}")


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


# ── Public API ──────────────────────────────────────────────────────────
async def generate_test_cases(
    requirements: str,
    source_type: str = "text",
    additional_context: str = "",
    module: str | None = None,
):
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
    )

    logger.info(
        f"Generating test cases | provider={AI_PROVIDER} | module={detected_module}"
    )

    raw = await asyncio.to_thread(_call_ai_sync, prompt)
    test_cases, summary = _parse_response(raw)

    logger.info(f"Generated {summary.total} test cases")

    return test_cases, summary


# ── Generic AI helper ───────────────────────────────────────────────────
async def enrich_with_ai(system: str, user: str) -> str:
    prompt = f"{system}\n\n{user}"
    return await asyncio.to_thread(_call_ai_sync, prompt)