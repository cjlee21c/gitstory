import hmac

from fastapi import Header, HTTPException, Request

from app import config

# Paths served without the access code. /health is Render's health check;
# /docs, /openapi.json, /redoc stay open so the API docs remain browsable.
_OPEN_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


def require_access_code(
    request: Request,
    x_access_code: str | None = Header(default=None),
) -> None:
    """App-wide gate. Applied once in main.py so every route is protected; the
    handful of _OPEN_PATHS (health check, docs) pass through. Compared in
    constant time so the code can't be guessed by timing."""
    if request.url.path in _OPEN_PATHS:
        return
    if x_access_code is None or not hmac.compare_digest(x_access_code, config.ACCESS_CODE):
        raise HTTPException(status_code=401, detail="Invalid or missing access code")
