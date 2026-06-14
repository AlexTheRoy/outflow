"""Global exception handlers — consistent JSON error envelopes, and no internal
stack traces leaked to clients in production."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings

logger = logging.getLogger("outflow")


def _envelope(error: str, detail, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": error, "detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exc(_: Request, exc: StarletteHTTPException):
        return _envelope("http_error", exc.detail, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exc(_: Request, exc: RequestValidationError):
        return _envelope("validation_error", exc.errors(), 422)

    @app.exception_handler(Exception)
    async def unhandled_exc(_: Request, exc: Exception):
        logger.exception("unhandled exception: %s", exc)
        detail = "Internal server error." if settings.is_production else str(exc)
        return _envelope("internal_error", detail, 500)
