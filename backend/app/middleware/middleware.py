from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

API_KEY_HEADER = "X-API-Key"
DEFAULT_RATE_LIMIT = "60/minute"
PUBLIC_PATHS = {"/", "/docs", "/redoc"}
PUBLIC_PATH_SUFFIXES = ("/openapi.json",)
API_KEY = os.getenv("API_KEY", "").strip()


try:
    from slowapi import Limiter
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address
    SLOWAPI_AVAILABLE = True
except ImportError:
    Limiter = None
    RateLimitExceeded = None
    SlowAPIMiddleware = None
    SLOWAPI_AVAILABLE = False

    def get_remote_address(request: Request) -> str:
        if request.client is None:
            return "unknown"
        return request.client.host or "unknown"


@dataclass(frozen=True)
class ErrorPayload:
    code: str
    message: str


class _NoOpLimiter:
    def __init__(self, *args, **kwargs):
        self.enabled = False

    def init_app(self, app):
        return None

    def limit(self, *_args, **_kwargs):
        def decorator(func):
            return func

        return decorator


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[DEFAULT_RATE_LIMIT],
) if SLOWAPI_AVAILABLE else _NoOpLimiter()


def is_public_path(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True

    return any(path.endswith(suffix) for suffix in PUBLIC_PATH_SUFFIXES)


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or is_public_path(request.url.path):
            return await call_next(request)

        if not API_KEY:
            return await call_next(request)

        provided_key = request.headers.get(API_KEY_HEADER, "").strip()
        if provided_key != API_KEY:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Missing or invalid API key.",
                    },
                },
            )

        return await call_next(request)


async def rate_limit_exceeded_handler(request: Request, exc):
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
            },
        },
    )


def configure_rate_limiting(app) -> None:
    if not SLOWAPI_AVAILABLE:
        app.state.limiter = limiter
        return

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
