"""
Request Logging Middleware - Structured logging with request context
"""
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with timing and context information."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Bind context for this request
        bound_logger = logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        bound_logger.info("Request started")

        # Add request ID to headers
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            process_time = round((time.time() - start_time) * 1000, 2)

            bound_logger.info(
                "Request completed",
                status_code=response.status_code,
                process_time_ms=process_time,
            )

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            return response

        except Exception as exc:
            process_time = round((time.time() - start_time) * 1000, 2)
            bound_logger.error(
                "Request failed",
                exc_info=exc,
                process_time_ms=process_time,
            )
            raise
