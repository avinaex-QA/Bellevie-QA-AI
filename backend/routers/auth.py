"""
Authentication routes: email/password, Google OAuth start/callback placeholder,
current user, logout.
"""
from __future__ import annotations

from datetime import timedelta
import secrets
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from backend.config.settings import settings
from backend.db import get_db
from backend.models.schemas import AuthResponse, LoginRequest, OAuthStartResponse, OtpResendRequest, OtpStartResponse, OtpVerifyRequest, SignupRequest, UserPublic
from backend.security.auth import create_session, get_current_user, iso_now, revoke_session, verify_password
from backend.security.rate_limiter import check_rate_limit
from backend.services.oauth_state_service import consume_oauth_state, create_oauth_state
from backend.services.otp_service import resend_otp, start_email_verification, validate_email, verify_signup_otp

router = APIRouter()


def _public_user(row: dict) -> UserPublic:
    return UserPublic(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        auth_provider=row["auth_provider"],
        avatar_url=row.get("avatar_url"),
        created_at=row["created_at"],
        last_login=row.get("last_login"),
        is_active=bool(row["is_active"]),
        email_verified=bool(row.get("email_verified", 0)),
    )


def _set_session_cookie(response: Response, user_id: str) -> None:
    token, _ = create_session(user_id)
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=settings.session_expire_hours * 3600,
    )


@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest, response: Response):
    result = start_email_verification(request.name, request.email, request.password, request.confirm_password)
    raise HTTPException(status_code=202, detail=result["message"])


@router.post("/signup/start", response_model=OtpStartResponse)
async def signup_start(request: SignupRequest, http_request: Request):
    check_rate_limit(f"signup:{http_request.client.host}:{request.email.lower()}", limit=5, window_seconds=3600, message="Too many signup attempts. Please try again later.")
    return OtpStartResponse(**start_email_verification(request.name, request.email, request.password, request.confirm_password))


@router.post("/signup/resend", response_model=OtpStartResponse)
async def signup_resend(request: OtpResendRequest, http_request: Request):
    check_rate_limit(f"otp-resend:{http_request.client.host}:{request.email.lower()}", limit=4, window_seconds=3600, message="Too many OTP resend requests.")
    result = resend_otp(request.email)
    return OtpStartResponse(email=request.email.strip().lower(), **result)


@router.post("/signup/verify", response_model=AuthResponse)
async def signup_verify(request: OtpVerifyRequest, response: Response, http_request: Request):
    check_rate_limit(f"otp-verify:{http_request.client.host}:{request.email.lower()}", limit=8, window_seconds=900, message="Too many attempts")
    result = verify_signup_otp(request.email, request.otp)
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE id = ?", (result["user_id"],)).fetchone()
    _set_session_cookie(response, result["user_id"])
    return AuthResponse(user=_public_user(dict(row)))


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, response: Response, http_request: Request):
    email = validate_email(request.email)
    if not request.password:
        raise HTTPException(status_code=400, detail="Password is required.")
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must meet minimum requirements.")
    check_rate_limit(f"login:{http_request.client.host}:{email}", limit=8, window_seconds=900, message="Too many login attempts. Please try again later.")
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Account not found.")
    if not row["hashed_password"] or not verify_password(request.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect password.")
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="Your account is inactive.")
    if not row["email_verified"]:
        raise HTTPException(status_code=403, detail="Please verify your email before logging in.")

    with get_db() as db:
        db.execute("UPDATE users SET last_login = ? WHERE id = ?", (iso_now(), row["id"]))
        row = db.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()

    _set_session_cookie(response, row["id"])
    return AuthResponse(user=_public_user(dict(row)))


@router.post("/logout")
async def logout(request: Request, response: Response, current_user=Depends(get_current_user)):
    revoke_session(request.cookies.get(settings.session_cookie_name))
    response.delete_cookie(settings.session_cookie_name)
    return {"success": True, "message": "Logged out successfully."}


@router.get("/me", response_model=UserPublic)
async def me(current_user=Depends(get_current_user)):
    return _public_user(current_user)


@router.get("/google/start", response_model=OAuthStartResponse)
async def google_start():
    configured = bool(settings.google_client_id and settings.google_client_secret)
    if not configured:
        return OAuthStartResponse(
            provider="google",
            authorization_url="",
            state="",
            configured=False,
            message="Google sign-in is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.",
        )
    state = create_oauth_state("google", "login", redirect_after=settings.frontend_base_url)
    params = urlencode({
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
        "prompt": "select_account",
    })
    return OAuthStartResponse(
        provider="google",
        authorization_url=f"https://accounts.google.com/o/oauth2/v2/auth?{params}",
        state=state,
        configured=configured,
    )


@router.get("/google/callback")
async def google_callback(response: Response, code: str | None = None, state: str | None = None, error: str | None = None):
    if error or not code or not state:
        raise HTTPException(status_code=400, detail="Google sign-in failed. Please try again.")
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=400, detail="Google OAuth is not configured locally.")

    try:
        consume_oauth_state(state, "google", "login")
    except HTTPException:
        raise HTTPException(status_code=400, detail="Google sign-in failed. Please try again.")

    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    if not token_resp.ok:
        raise HTTPException(status_code=400, detail="Google sign-in failed. Please try again.")
    access_token = token_resp.json().get("access_token")
    profile_resp = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if not profile_resp.ok:
        raise HTTPException(status_code=400, detail="Google sign-in failed. Please try again.")
    profile = profile_resp.json()
    email = (profile.get("email") or "").lower()
    if not email:
        raise HTTPException(status_code=400, detail="Google sign-in failed. Please try again.")

    now = iso_now()
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            provider = row["auth_provider"] if "google" in row["auth_provider"] else f"{row['auth_provider']}_google"
            db.execute(
                "UPDATE users SET last_login = ?, avatar_url = ?, google_id = ?, auth_provider = ?, email_verified = 1 WHERE id = ?",
                (now, profile.get("picture"), profile.get("sub"), provider, row["id"]),
            )
            user_id = row["id"]
        else:
            user_id = secrets.token_urlsafe(16)
            db.execute(
                """
                INSERT INTO users (id, name, email, hashed_password, auth_provider, avatar_url, created_at, last_login, is_active, email_verified, google_id)
                VALUES (?, ?, ?, NULL, 'google', ?, ?, ?, 1, 1, ?)
                """,
                (user_id, profile.get("name") or email, email, profile.get("picture"), now, now, profile.get("sub")),
            )
    redirect = RedirectResponse(settings.frontend_base_url)
    _set_session_cookie(redirect, user_id)
    return redirect
