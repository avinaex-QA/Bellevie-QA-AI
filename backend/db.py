"""
Lightweight local database layer.

The repository can run locally without installing extra packages. The schema is
kept relational and PostgreSQL-ready so it can later move behind SQLAlchemy /
Alembic without changing API contracts.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from backend.config.settings import settings


def _sqlite_path() -> Path:
    url = settings.database_url
    if url.startswith("sqlite:///"):
        return Path(url.replace("sqlite:///", "", 1)).resolve()
    if url.startswith("sqlite://"):
        parsed = urlparse(url)
        return Path(parsed.path).resolve()
    return Path("local_saas.db").resolve()


DB_PATH = _sqlite_path()


@contextmanager
def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              email TEXT NOT NULL UNIQUE,
              hashed_password TEXT,
              auth_provider TEXT NOT NULL DEFAULT 'email',
              avatar_url TEXT,
              created_at TEXT NOT NULL,
              last_login TEXT,
              is_active INTEGER NOT NULL DEFAULT 1,
              email_verified INTEGER NOT NULL DEFAULT 0,
              google_id TEXT
            );

            CREATE TABLE IF NOT EXISTS user_integrations (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              provider TEXT NOT NULL,
              encrypted_config TEXT NOT NULL,
              auth_type TEXT NOT NULL DEFAULT 'manual',
              access_token_encrypted TEXT,
              refresh_token_encrypted TEXT,
              expires_at TEXT,
              provider_account_id TEXT,
              provider_account_email TEXT,
              provider_workspace_id TEXT,
              provider_workspace_name TEXT,
              is_connected INTEGER NOT NULL DEFAULT 1,
              connected_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(user_id, provider),
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS generation_history (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              source_type TEXT,
              selected_projects TEXT,
              selected_modules TEXT,
              source_info TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS execution_history (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              test_case_id TEXT NOT NULL,
              status TEXT NOT NULL,
              notes TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS linked_bugs (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              test_case_id TEXT NOT NULL,
              provider TEXT NOT NULL,
              external_id TEXT NOT NULL,
              external_url TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              revoked_at TEXT,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS email_verifications (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              email TEXT NOT NULL,
              otp_hash TEXT NOT NULL,
              password_hash TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              attempt_count INTEGER NOT NULL DEFAULT 0,
              resend_count INTEGER NOT NULL DEFAULT 0,
              is_verified INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS oauth_states (
              state TEXT PRIMARY KEY,
              user_id TEXT,
              provider TEXT NOT NULL,
              purpose TEXT NOT NULL,
              redirect_after TEXT,
              created_at TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              used_at TEXT,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        _ensure_columns(db, "users", {
            "email_verified": "INTEGER NOT NULL DEFAULT 0",
            "google_id": "TEXT",
        })
        _ensure_columns(db, "user_integrations", {
            "access_token_encrypted": "TEXT",
            "refresh_token_encrypted": "TEXT",
            "expires_at": "TEXT",
            "provider_account_id": "TEXT",
            "provider_account_email": "TEXT",
            "provider_workspace_id": "TEXT",
            "provider_workspace_name": "TEXT",
            "is_connected": "INTEGER NOT NULL DEFAULT 1",
        })


def _ensure_columns(db: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, definition in columns.items():
        if name not in existing:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
