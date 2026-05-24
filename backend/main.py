"""
FastAPI application entry point.
Mounts routers and serves the frontend SPA.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config.settings import settings
from backend.db import init_db
from backend.routers import auth, clickup, generate, integrations, jira, export, oauth_aliases
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(
    title="AI Test Case Generator",
    description="Generate comprehensive, real-world test cases from Jira tickets, "
                "documents, raw text, and GitHub PRs using Claude AI.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ───────────────────────────────────────────────────────────────
app.include_router(auth.router,     prefix="/api/auth", tags=["Auth"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])
app.include_router(oauth_aliases.router, tags=["OAuth Aliases"])
app.include_router(generate.router, prefix="/api", tags=["Generate"])
app.include_router(jira.router,     prefix="/api/jira", tags=["Jira"])
app.include_router(clickup.router,  prefix="/api/clickup", tags=["ClickUp"])
app.include_router(export.router,   prefix="/api/export", tags=["Export"])

# ── Static Files (frontend) ───────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR)),
        name="static",
    )
    logger.info(f"Serving frontend from: {FRONTEND_DIR}")


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "AI Test Case Generator API", "docs": "/docs"}


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "ai_provider": settings.ai_provider,
        "jira_configured": bool(settings.jira_base_url and settings.jira_api_token),
        "clickup_configured": bool(settings.clickup_api_token),
        "github_configured": bool(settings.github_token),
        "database": "local-sqlite" if settings.database_url.startswith("sqlite") else "external",
    }


@app.on_event("startup")
async def startup():
    init_db()
    logger.info("AI Test Case Generator started")
    logger.info(f"AI Provider: {settings.ai_provider.upper()}")
    logger.info(f"Docs available at: http://localhost:{settings.app_port}/docs")
