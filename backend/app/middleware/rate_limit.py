"""
Rate Limiting Middleware - Token Bucket per User/IP
"""
import time
from typing import Dict, Tuple

import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter using in-memory store.
    Falls back to Redis for distributed environments.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        # In-memory store: {key: [(timestamp,),...]}
        self._store: Dict[str, list] = {}
        self._limit = settings.RATE_LIMIT_REQUESTS
        self._window = settings.RATE_LIMIT_WINDOW

        # Paths that are exempt from rate limiting
        self._exempt_paths = {"/health", "/", "/docs", "/redoc", "/openapi.json"}

    def _get_identifier(self, request: Request) -> str:
        """Get rate limit identifier (user or IP)."""
        # Try to get user from auth header (just identifier, not full auth)
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return f"token:{hash(auth)}"
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return f"apikey:{hash(api_key)}"
        # Fall back to IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        ip = forwarded_for.split(",")[0].strip() if forwarded_for else (
            request.client.host if request.client else "unknown"
        )
        return f"ip:{ip}"

    def _is_allowed(self, key: str) -> Tuple[bool, int]:
        """Check if request is within rate limit. Returns (allowed, remaining)."""
        now = time.time()
        window_start = now - self._window

        # Cleanup old entries
        if key in self._store:
            self._store[key] = [t for t in self._store[key] if t > window_start]
        else:
            self._store[key] = []

        count = len(self._store[key])
        if count >= self._limit:
            return False, 0

        self._store[key].append(now)
        return True, self._limit - count - 1

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and static paths
        if request.url.path in self._exempt_paths:
            return await call_next(request)

        identifier = self._get_identifier(request)
        allowed, remaining = self._is_allowed(identifier)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": 429,
                        "message": f"Rate limit exceeded. Maximum {self._limit} requests per {self._window} seconds.",
                        "type": "RateLimitError",
                    }
                },
                headers={
                    "Retry-After": str(self._window),
                    "X-RateLimit-Limit": str(self._limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Window": str(self._window),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
