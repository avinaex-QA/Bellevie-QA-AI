import asyncio

import pytest
from fastapi import HTTPException

from backend.models.schemas import TestCase, TestSummary
from backend.routers import generate as generate_router


def test_generate_rejects_missing_project_selection():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(generate_router.generate(
            selected_projects=[],
            jira_id=None,
            text_input="Generate login test cases.",
            github_pr_url=None,
            additional_context=None,
            file=None,
        ))

    assert exc.value.status_code == 400
    assert "select at least one project" in exc.value.detail.lower()


def test_generate_rejects_project_without_requirement_source():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(generate_router.generate(
            selected_projects=["Resident APP"],
            jira_id=None,
            text_input=None,
            github_pr_url=None,
            additional_context=None,
            file=None,
        ))

    assert exc.value.status_code == 400
    assert "requirement source" in exc.value.detail.lower()


def test_generate_accepts_text_with_project(monkeypatch):
    async def fake_generate_test_cases(*, requirements, source_type, additional_context, selected_projects):
        assert "Generate login test cases." in requirements
        assert source_type == "text"
        assert selected_projects == ["Resident APP"]
        return (
            [
                TestCase(
                    id="TC-001",
                    priority="High",
                    title="Verify login",
                    preconditions="User exists",
                    steps=["Open app", "Log in"],
                    expected_result="User logs in",
                    tags=["Smoke"],
                    test_type="Functional",
                )
            ],
            TestSummary(total=1, high_priority=1, medium_priority=0, low_priority=0, module_detected="Login"),
        )

    monkeypatch.setattr(generate_router, "generate_test_cases", fake_generate_test_cases)

    response = asyncio.run(generate_router.generate(
        selected_projects=["Resident APP"],
        jira_id=None,
        text_input="Generate login test cases.",
        github_pr_url=None,
        additional_context=None,
        file=None,
    ))

    assert response.success is True
    assert response.source_info["selected_projects"] == ["Resident APP"]
    assert response.summary.total == 1
