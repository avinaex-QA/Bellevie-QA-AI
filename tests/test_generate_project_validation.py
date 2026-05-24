import asyncio

import pytest
from fastapi import HTTPException

from backend.models.schemas import TestCase, TestSummary
from backend.routers import generate as generate_router
from backend.models.schemas import ClickUpTask


def test_generate_rejects_missing_project_selection():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(generate_router.generate(
            selected_projects=[],
            selected_modules=["Onboarding"],
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
            selected_modules=["Onboarding"],
            jira_id=None,
            text_input=None,
            github_pr_url=None,
            additional_context=None,
            file=None,
        ))

    assert exc.value.status_code == 400
    assert "requirement source" in exc.value.detail.lower()


def test_generate_rejects_missing_module_selection():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(generate_router.generate(
            selected_projects=["Resident APP"],
            selected_modules=[],
            jira_id=None,
            text_input="Generate login test cases.",
            github_pr_url=None,
            additional_context=None,
            file=None,
        ))

    assert exc.value.status_code == 400
    assert "select at least one module" in exc.value.detail.lower()


def test_generate_accepts_text_with_project_and_module(monkeypatch):
    async def fake_generate_test_cases(*, requirements, source_type, additional_context, selected_projects, selected_modules):
        assert "Generate login test cases." in requirements
        assert source_type == "text"
        assert selected_projects == ["Resident APP"]
        assert selected_modules == ["Onboarding"]
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
        selected_modules=["Onboarding"],
        jira_id=None,
        text_input="Generate login test cases.",
        github_pr_url=None,
        additional_context=None,
        file=None,
    ))

    assert response.success is True
    assert response.source_info["selected_projects"] == ["Resident APP"]
    assert response.source_info["selected_modules"] == ["Onboarding"]
    assert response.summary.total == 1


def test_generate_accepts_clickup_with_project_and_module(monkeypatch):
    def fake_fetch_clickup_task(task_id):
        assert task_id == "86abc123"
        return ClickUpTask(
            task_id="86abc123",
            title="Implement social login",
            description="Google and Apple social login for residents.",
            status="in progress",
            priority="high",
            assignee="QA User",
            tags=["auth", "mobile"],
            raw_text="ClickUp Task: 86abc123\nTitle: Implement social login",
        )

    async def fake_generate_test_cases(*, requirements, source_type, additional_context, selected_projects, selected_modules):
        assert "ClickUp Task: 86abc123" in requirements
        assert source_type == "clickup"
        assert selected_projects == ["Resident APP"]
        assert selected_modules == ["Onboarding"]
        return (
            [
                TestCase(
                    id="TC-001",
                    priority="High",
                    title="Verify social login",
                    preconditions="Resident app installed",
                    steps=["Open app", "Continue with Google"],
                    expected_result="Resident is authenticated",
                    tags=["Auth"],
                    test_type="Functional",
                )
            ],
            TestSummary(total=1, high_priority=1, medium_priority=0, low_priority=0, module_detected="Onboarding"),
        )

    monkeypatch.setattr(generate_router, "fetch_clickup_task", fake_fetch_clickup_task)
    monkeypatch.setattr(generate_router, "generate_test_cases", fake_generate_test_cases)

    response = asyncio.run(generate_router.generate(
        selected_projects=["Resident APP"],
        selected_modules=["Onboarding"],
        jira_id=None,
        clickup_task_id="86abc123",
        text_input=None,
        github_pr_url=None,
        additional_context=None,
        file=None,
    ))

    assert response.success is True
    assert response.source_info["clickup"]["task_id"] == "86abc123"
    assert response.source_info["clickup"]["title"] == "Implement social login"


def test_generate_rejects_clickup_without_project_and_module():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(generate_router.generate(
            selected_projects=[],
            selected_modules=[],
            jira_id=None,
            clickup_task_id="86abc123",
            text_input=None,
            github_pr_url=None,
            additional_context=None,
            file=None,
        ))

    assert exc.value.status_code == 400
    assert exc.value.detail == "Please select Project and Module along with ClickUp task."
