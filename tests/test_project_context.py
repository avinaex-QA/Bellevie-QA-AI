import asyncio
import json

import pytest

from backend.config.project_context import (
    build_context_section,
    build_project_context_section,
    normalize_selected_modules,
    normalize_selected_projects,
)
from backend.services import ai_service


def test_normalize_selected_projects_validates_and_orders_projects():
    assert normalize_selected_projects(["VMS APP", "Resident APP", "VMS APP"]) == [
        "Resident APP",
        "VMS APP",
    ]


def test_normalize_selected_projects_rejects_invalid_values():
    with pytest.raises(ValueError, match="Invalid project selection"):
        normalize_selected_projects(["Resident APP", "Unknown Project"])


def test_normalize_selected_modules_validates_and_orders_modules():
    assert normalize_selected_modules(["VMS", "Ticket", "Ticket"]) == ["Ticket", "VMS"]


def test_normalize_selected_modules_rejects_invalid_values():
    with pytest.raises(ValueError, match="Invalid module selection"):
        normalize_selected_modules(["Ticket", "Unknown Module"])


def test_build_project_context_section_merges_multi_project_context():
    context = build_project_context_section(["Resident APP", "VMS APP"])

    assert "Selected projects: Resident APP, VMS APP" in context
    assert "mobile app workflows" in context
    assert "visitor management" in context
    assert "Do not generate test cases from project context alone" in context


def test_build_context_section_merges_project_module_and_bellevie_context():
    context = build_context_section(["Resident APP", "Society Admin APP"], ["Ticket", "Notice"])

    assert "Selected projects: Resident APP, Society Admin APP" in context
    assert "Selected modules: Ticket, Notice" in context
    assert "mobile app workflows" in context
    assert "issue creation" in context
    assert "notice creation" in context
    assert "admin issue handling" in context


def test_generate_test_cases_injects_project_and_module_context(monkeypatch):
    captured = {}

    def fake_call(prompt):
        captured["prompt"] = prompt
        return json.dumps({
            "test_cases": [{
                "id": "TC-001",
                "priority": "High",
                "title": "Verify visitor OTP approval",
                "preconditions": "User is logged in",
                "steps": ["Open visitor request", "Approve with OTP"],
                "expected_result": "Visitor is approved",
                "tags": ["Regression"],
                "test_type": "Functional",
            }],
            "module_detected": "Visitor Management",
            "summary": {"total": 1, "high_priority": 1, "medium_priority": 0, "low_priority": 0},
        })

    monkeypatch.setattr(ai_service, "_call_ai_sync", fake_call)

    test_cases, summary = asyncio.run(ai_service.generate_test_cases(
        requirements="Visitor approval must support OTP.",
        source_type="text",
        selected_projects=["Resident APP", "VMS APP"],
        selected_modules=["VMS"],
    ))

    assert summary.total == 1
    assert test_cases[0].title == "Verify visitor OTP approval"
    assert "Selected projects: Resident APP, VMS APP" in captured["prompt"]
    assert "Selected modules: VMS" in captured["prompt"]
    assert "mobile app workflows" in captured["prompt"]
    assert "visitor management" in captured["prompt"]
