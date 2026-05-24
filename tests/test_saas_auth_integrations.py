from pathlib import Path

from backend import db as db_module
from backend.security.auth import create_session, hash_password, verify_password, verify_session_token
from backend.security.encryption import decrypt_json, encrypt_json
from backend.services.integration_store import get_integration, list_status, save_integration


def test_credentials_are_encrypted_round_trip():
    payload = {"api_token": "secret-token", "base_url": "https://example.atlassian.net"}

    encrypted = encrypt_json(payload)

    assert "secret-token" not in encrypted
    assert decrypt_json(encrypted) == payload


def test_password_hash_and_session_token_are_verifiable(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "saas.db")
    db_module.init_db()

    password_hash = hash_password("strong-password")
    assert password_hash != "strong-password"
    assert verify_password("strong-password", password_hash)
    assert not verify_password("wrong-password", password_hash)

    with db_module.get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, name, email, hashed_password, auth_provider, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, 1)",
            ("user-a", "User A", "a@example.com", password_hash, "email", "2026-05-23T00:00:00+00:00"),
        )

    token, _ = create_session("user-a")
    assert verify_session_token(token)


def test_integrations_are_user_scoped_and_status_hides_secrets(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "saas.db")
    db_module.init_db()

    with db_module.get_db() as conn:
        for user_id, email in (("user-a", "a@example.com"), ("user-b", "b@example.com")):
            conn.execute(
                "INSERT INTO users (id, name, email, hashed_password, auth_provider, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, 1)",
                (user_id, user_id, email, None, "google", "2026-05-23T00:00:00+00:00"),
            )

    save_integration("user-a", "jira", {"base_url": "https://a.atlassian.net", "email": "a@example.com", "api_token": "token-a"})
    save_integration("user-b", "jira", {"base_url": "https://b.atlassian.net", "email": "b@example.com", "api_token": "token-b"})

    assert get_integration("user-a", "jira")["api_token"] == "token-a"
    assert get_integration("user-b", "jira")["api_token"] == "token-b"

    statuses = list_status("user-a")
    jira_status = next(item for item in statuses if item["provider"] == "jira")
    assert jira_status["connected"] is True
    assert jira_status["display"]["base_url"] == "https://a.atlassian.net"
    assert "token-a" not in str(jira_status)
