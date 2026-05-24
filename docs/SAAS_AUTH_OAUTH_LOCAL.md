# SaaS Auth + OAuth Local Setup

Local-only implementation notes for authentication hardening, OTP verification, and OAuth integrations.

## Database Migration

The local app initializes and migrates the SQLite database automatically on startup.

Default DB:

```env
DATABASE_URL=sqlite:///./local_saas.db
```

New tables:

- `email_verifications`
- `oauth_states`

Updated tables:

- `users`: `email_verified`, `google_id`
- `user_integrations`: encrypted OAuth token columns, provider account metadata, workspace metadata, connection state

## Required Security Env

```env
APP_SECRET_KEY=change-this-long-random-secret
ENCRYPTION_KEY=
SESSION_EXPIRE_HOURS=168
APP_BASE_URL=http://localhost:8000
FRONTEND_BASE_URL=http://localhost:8000
```

`ENCRYPTION_KEY` is optional locally. If set, it must be a Fernet key.

## Email Setup

SMTP:

```env
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-user
SMTP_PASSWORD=your-password
SMTP_FROM="AI QA Copilot <no-reply@example.com>"
```

Resend:

```env
RESEND_API_KEY=your-resend-key
SMTP_FROM="AI QA Copilot <no-reply@example.com>"
```

If neither is configured, signup returns:

```text
Email service is not configured. Add SMTP settings or RESEND_API_KEY in .env.
```

For local log-only OTP testing, explicitly enable:

```env
EMAIL_DEV_MODE=true
```

## OAuth Callback URLs

Google:

```text
http://localhost:8000/auth/google/callback
```

GitHub:

```text
http://localhost:8000/oauth/github/callback
```

ClickUp:

```text
http://localhost:8000/oauth/clickup/callback
```

Atlassian/Jira:

```text
http://localhost:8000/oauth/jira/callback
```

Equivalent `/api/...` callbacks are also supported by the backend.

## OAuth Env

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=http://localhost:8000/oauth/github/callback

CLICKUP_CLIENT_ID=
CLICKUP_CLIENT_SECRET=
CLICKUP_REDIRECT_URI=http://localhost:8000/oauth/clickup/callback

ATLASSIAN_CLIENT_ID=
ATLASSIAN_CLIENT_SECRET=
ATLASSIAN_REDIRECT_URI=http://localhost:8000/oauth/jira/callback
```

## Atlassian Scopes

```text
read:jira-work read:jira-user write:jira-work offline_access
```

## Testing Checklist

Run:

```bash
python3 -m pytest tests
python3 -m compileall backend
node --check frontend/js/app.js
```

Manual smoke:

1. Open `http://localhost:8000`.
2. Try signup with weak password and confirm inline validation.
3. Signup with strong password and confirm OTP screen appears.
4. Check local logs for OTP if SMTP/Resend is not configured.
5. Verify OTP and confirm auto-login.
6. Open Settings and confirm Jira, ClickUp, GitHub cards show Connect/Reconnect/Test/Disconnect.
7. Connect OAuth providers after adding client IDs/secrets.

## Notes

- OAuth tokens are encrypted at rest.
- OAuth state is one-time use and expires.
- Jira OAuth is preferred; manual Jira API token fallback remains available.
- GitHub PR analysis, ClickUp task fetch, Jira issue fetch, and Jira bug creation use the logged-in user's connected integration.
