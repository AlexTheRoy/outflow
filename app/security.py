"""API-key authentication.

Clients authenticate with either:
    Authorization: Bearer <key>
    X-API-Key: <key>

Behavior:
  * development with no API_KEYS set -> auth disabled (handy for local work)
  * production, or any env with API_KEYS set -> key required and verified in
    constant time to avoid timing attacks.
"""
from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from .config import settings


def _matches_any(candidate: str) -> bool:
    return any(hmac.compare_digest(candidate, k) for k in settings.api_key_set)


async def require_api_key(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> str:
    """FastAPI dependency. Returns the validated key (or "anonymous" in dev)."""
    if not settings.auth_enabled:
        return "anonymous"

    key = ""
    if authorization and authorization.lower().startswith("bearer "):
        key = authorization[7:].strip()
    elif x_api_key:
        key = x_api_key.strip()

    if not key or not _matches_any(key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return key
