import asyncio

from backend.models.schemas import BugDraftRequest, JiraBugCreateRequest, TestCase
from backend.services import ai_service, jira_service


def _failed_test_case() -> TestCase:
    return TestCase(
        id="TC-001",
        priority="High",
        title="Verify resident can approve visitor",
        preconditions="Resident is logged in",
        steps=["Open Resident App", "Open visitor request", "Tap Approve"],
        expected_result="Visitor request is approved",
        actual_result="Approve button disabled",
        tags=["Regression"],
        test_type="Functional",
        status="Failed",
        execution_notes="Approval button disabled",
    )


def test_bug_draft_falls_back_when_ai_is_unavailable(monkeypatch):
    def fail_ai(prompt):
        raise RuntimeError("AI unavailable")

    monkeypatch.setattr(ai_service, "_call_ai_sync", fail_ai)

    draft = asyncio.run(ai_service.generate_bug_draft(BugDraftRequest(
        test_case=_failed_test_case(),
        selected_projects=["Resident APP"],
        selected_modules=["VMS"],
        execution_notes="Approval button disabled",
    )))

    assert "Verify resident can approve visitor" in draft.bug_summary
    assert draft.actual_result == "Approval button disabled"
    assert draft.project == "Resident APP"
    assert draft.module == "VMS"
    assert draft.environment == "QA"


def test_create_jira_bug_uses_configured_project_and_custom_field_mapping(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"key": "APP-5926"}

    def fake_post(url, auth, headers, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr(jira_service.settings, "jira_base_url", "https://example.atlassian.net")
    monkeypatch.setattr(jira_service.settings, "jira_email", "qa@example.com")
    monkeypatch.setattr(jira_service.settings, "jira_api_token", "token")
    monkeypatch.setattr(jira_service.settings, "jira_bug_project_key", "APP")
    monkeypatch.setattr(jira_service, "get_bug_field_map", lambda: {"severity": "customfield_1", "module": "customfield_2"})
    monkeypatch.setattr(jira_service.requests, "post", fake_post)

    response = jira_service.create_jira_bug(JiraBugCreateRequest(
        test_case_id="TC-001",
        bug_summary="Resident unable to approve visitor",
        description="Approval is blocked.",
        steps_to_reproduce=["Open app", "Tap Approve"],
        actual_result="Button disabled",
        expected_result="Visitor approved",
        severity="High",
        environment="QA",
        project="Resident APP",
        module="VMS",
        classification="Functionality",
        type="Mobile",
        device_type="Mobile",
    ))

    assert response.issue_key == "APP-5926"
    fields = captured["json"]["fields"]
    assert fields["project"]["key"] == "APP"
    assert fields["issuetype"]["name"] == "Bug"
    assert fields["customfield_1"]["value"] == "High"
    assert fields["customfield_2"]["value"] == "VMS"
