import pytest
from fastapi import HTTPException

from backend import db as db_module
from backend.db import get_db
from backend.config.settings import settings
from backend.routers import auth as auth_router
from backend.security.auth import verify_password
from backend.services import otp_service
from backend.services.email_service import EmailDeliveryNotConfigured, send_verification_email
from backend.services.integration_store import get_integration, save_connected_integration
from backend.services.oauth_state_service import consume_oauth_state, create_oauth_state


def _init_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "saas.db")
    db_module.init_db()


def test_signup_otp_creates_user_only_after_verification(tmp_path, monkeypatch):
    _init_tmp_db(tmp_path, monkeypatch)
    sent = {}
    monkeypatch.setattr(otp_service, "send_verification_email", lambda email, name, otp: sent.update({"email": email, "name": name, "otp": otp}))

    result = otp_service.start_email_verification(
        "Avinash",
        "avinash@example.com",
        "Strong@123",
        "Strong@123",
    )

    assert result["message"] == "Verification code sent"
    with get_db() as db:
        assert db.execute("SELECT id FROM users WHERE email = ?", ("avinash@example.com",)).fetchone() is None
        verification = db.execute("SELECT * FROM email_verifications WHERE email = ?", ("avinash@example.com",)).fetchone()

    assert verification["otp_hash"] != sent["otp"]
    assert verify_password(sent["otp"], verification["otp_hash"])

    verified = otp_service.verify_signup_otp("avinash@example.com", sent["otp"])
    assert verified["success"] is True
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", ("avinash@example.com",)).fetchone()
    assert user is not None
    assert user["email_verified"] == 1


def test_email_delivery_requires_provider_unless_dev_mode(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", None)
    monkeypatch.setattr(settings, "smtp_host", None)
    monkeypatch.setattr(settings, "email_dev_mode", False)

    with pytest.raises(EmailDeliveryNotConfigured):
        send_verification_email("avi@example.com", "Avi", "123456")


def test_google_start_does_not_return_placeholder_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", None)
    monkeypatch.setattr(settings, "google_client_secret", None)

    response = __import__("asyncio").run(auth_router.google_start())

    assert response.configured is False
    assert response.authorization_url == ""
    assert "Google sign-in is not configured" in response.message


def test_signup_password_policy_rejects_weak_password(tmp_path, monkeypatch):
    _init_tmp_db(tmp_path, monkeypatch)

    with pytest.raises(HTTPException) as exc:
        otp_service.start_email_verification("Avi", "avi@example.com", "password", "password")

    assert exc.value.detail == "Password must contain uppercase, lowercase, number, and special character."


def test_oauth_state_is_one_time_and_user_scoped(tmp_path, monkeypatch):
    _init_tmp_db(tmp_path, monkeypatch)
    with get_db() as db:
        db.execute(
            "INSERT INTO users (id, name, email, hashed_password, auth_provider, created_at, is_active, email_verified) VALUES (?, ?, ?, ?, ?, ?, 1, 1)",
            ("user-a", "User A", "a@example.com", None, "google", "2026-05-24T00:00:00+00:00"),
        )

    state = create_oauth_state("github", "connect", user_id="user-a")
    consumed = consume_oauth_state(state, "github", "connect")

    assert consumed["user_id"] == "user-a"
    with pytest.raises(HTTPException):
        consume_oauth_state(state, "github", "connect")


def test_oauth_tokens_are_encrypted_and_status_metadata_is_visible(tmp_path, monkeypatch):
    _init_tmp_db(tmp_path, monkeypatch)
    with get_db() as db:
        db.execute(
            "INSERT INTO users (id, name, email, hashed_password, auth_provider, created_at, is_active, email_verified) VALUES (?, ?, ?, ?, ?, ?, 1, 1)",
            ("user-a", "User A", "a@example.com", None, "google", "2026-05-24T00:00:00+00:00"),
        )

    save_connected_integration(
        "user-a",
        "github",
        config={"access_token": "gh-secret"},
        auth_type="oauth",
        access_token="gh-secret",
        provider_account_id="avinash",
        provider_account_email="a@example.com",
    )

    with get_db() as db:
        row = db.execute("SELECT * FROM user_integrations WHERE user_id = ? AND provider = 'github'", ("user-a",)).fetchone()
    assert "gh-secret" not in row["access_token_encrypted"]
    assert get_integration("user-a", "github")["access_token"] == "gh-secret"
