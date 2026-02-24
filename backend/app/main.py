"""
FastAPI Main Application Entry Point
CodeMix NLP - Misinformation & Sarcasm Detection Platform
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import analyze, analytics, models
from app.core.config import settings
from app.core.database import engine, create_tables
from app.services.ml_service import ml_service
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import RequestLoggingMiddleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan - startup and shutdown events."""
    # Startup
    logger.info("Starting CodeMix NLP Platform", version="1.0.0", environment=settings.ENVIRONMENT)
    
    # Create database tables
    await create_tables()
    logger.info("Database tables initialized")
    
    # Load ML model
    await ml_service.load_model()
    logger.info("ML model loaded successfully", model=settings.MODEL_NAME)
    
    yield
    
    # Shutdown
    logger.info("Shutting down CodeMix NLP Platform")
    await ml_service.cleanup()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-grade NLP platform for detecting misinformation and sarcasm in Indian code-mixed text",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # =========================================================================
    # Middleware (order matters - outermost first)
    # =========================================================================
    
    # Security headers
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.DEBUG else [settings.FRONTEND_URL.replace("https://", "").replace("http://", "")]
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_URL] if not settings.DEBUG else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )
    
    # Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Rate limiting
    app.add_middleware(RateLimitMiddleware)
    
    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # =========================================================================
    # Exception Handlers
    # =========================================================================
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "type": "HTTPException",
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": 422,
                    "message": "Validation error",
                    "type": "ValidationError",
                    "details": exc.errors(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception", exc_info=exc, path=str(request.url))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": 500,
                    "message": "Internal server error",
                    "type": "InternalServerError",
                }
            },
        )

    # =========================================================================
    # Routes
    # =========================================================================
    app.include_router(analyze.router, prefix="/api/v1/analyze", tags=["Analysis"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
    app.include_router(models.router, prefix="/api/v1/models", tags=["Models"])

    # =========================================================================
    # Health Check
    # =========================================================================
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "model_loaded": ml_service.is_loaded,
        }

    @app.get("/", tags=["Root"])
    async def root() -> dict:
        """Root endpoint."""
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_application()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
