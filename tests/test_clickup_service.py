import pytest

from backend.config.settings import settings
from backend.services import clickup_service


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload


def test_fetch_clickup_task_normalizes_response(monkeypatch):
    monkeypatch.setattr(settings, "clickup_api_token", "token")
    monkeypatch.setattr(settings, "clickup_api_base", "https://api.clickup.com/api/v2")

    def fake_get(url, headers, timeout):
        assert headers["Authorization"] == "token"
        if url.endswith("/comment"):
            return FakeResponse(payload={
                "comments": [
                    {"comment_text": "Please cover Apple login failure.", "user": {"username": "Avinash"}}
                ]
            })
        return FakeResponse(payload={
            "id": "86abc123",
            "name": "Implement social login",
            "text_content": "Google and Apple login support.",
            "status": {"status": "in progress"},
            "priority": {"priority": "high"},
            "assignees": [{"username": "QA User"}],
            "tags": [{"name": "auth"}, {"name": "mobile"}],
            "checklists": [{"name": "QA", "items": [{"name": "Add regression cases", "resolved": False}]}],
            "custom_fields": [{"name": "Module", "value": "Onboarding"}],
            "dependencies": [{"task_id": "86dep456"}],
            "date_created": "1714521600000",
            "due_date": "1715126400000",
        })

    monkeypatch.setattr(clickup_service.requests, "get", fake_get)

    task = clickup_service.fetch_clickup_task("86abc123")

    assert task.task_id == "86abc123"
    assert task.title == "Implement social login"
    assert task.status == "in progress"
    assert task.priority == "high"
    assert task.assignee == "QA User"
    assert task.tags == ["auth", "mobile"]
    assert task.checklists == ["QA: Add regression cases (open)"]
    assert task.custom_fields == {"Module": "Onboarding"}
    assert task.dependencies == ["86dep456"]
    assert "ClickUp Task: 86abc123" in task.raw_text
    assert "Please cover Apple login failure." in task.raw_text


def test_fetch_clickup_task_requires_token(monkeypatch):
    monkeypatch.setattr(settings, "clickup_api_token", None)

    with pytest.raises(ValueError) as exc:
        clickup_service.fetch_clickup_task("86abc123")

    assert "CLICKUP_API_TOKEN" in str(exc.value)


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (401, "Invalid ClickUp credentials."),
        (403, "Invalid ClickUp credentials."),
        (404, "ClickUp task not found."),
        (429, "ClickUp rate limit reached."),
    ],
)
def test_fetch_clickup_task_friendly_api_errors(monkeypatch, status_code, expected):
    monkeypatch.setattr(settings, "clickup_api_token", "token")

    def fake_get(url, headers, timeout):
        return FakeResponse(status_code=status_code)

    monkeypatch.setattr(clickup_service.requests, "get", fake_get)

    with pytest.raises(ValueError) as exc:
        clickup_service.fetch_clickup_task("86abc123")

    assert expected in str(exc.value)
