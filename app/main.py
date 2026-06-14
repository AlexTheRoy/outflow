"""Outflow backend — production-hardened FastAPI app.

Local dev:
    cd backend
    pip install -r requirements.txt
    export DATABASE_URL="sqlite:///./dev.db"   # zero-setup option
    alembic upgrade head
    uvicorn app.main:app --reload

Docker (api + postgres + redis):
    docker compose up --build

Open http://localhost:8000/docs and try POST /analyze with {"url": "https://stripe.com"}.
Step 1 is fully functional; steps 2-4 return mock/simulated data until you add keys.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud
from .config import settings
from .db import get_db
from .errors import register_exception_handlers
from .observability import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    configure_logging,
)
from .routers import analyze, content, dialer, leads, outreach

logger = logging.getLogger("outflow")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    problems = settings.validate_for_production()
    if problems:
        # Fail fast: don't boot a misconfigured production instance.
        raise RuntimeError("Unsafe production config: " + "; ".join(problems))
    logger.info(
        "starting outflow env=%s auth=%s llm=%s",
        settings.environment,
        settings.auth_enabled,
        settings.llm_enabled,
    )
    yield
    logger.info("shutting down")


app = FastAPI(
    title="Outflow API",
    version="1.0.0",
    description="Paste-your-URL outbound engine.",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    lifespan=lifespan,
)

# Order matters: rate limit -> request context -> CORS (outermost runs last added).
app.add_middleware(CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)

register_exception_handlers(app)

app.include_router(analyze.router)
app.include_router(leads.router)
app.include_router(outreach.router)
app.include_router(content.router)
app.include_router(dialer.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness — process is up."""
    return {"status": "ok", "environment": settings.environment}


@app.get("/ready", tags=["meta"])
def ready(db: Session = Depends(get_db)) -> dict:
    """Readiness — dependencies reachable."""
    db_ok = crud.db_healthy(db)
    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "llm_enabled": settings.llm_enabled,
        "llm_provider": settings.llm_provider,
        "providers": {
            "apollo": bool(settings.apollo_api_key),
            "email": bool(settings.instantly_api_key or settings.smartlead_api_key),
            "twilio": bool(settings.twilio_account_sid),
        },
    }
