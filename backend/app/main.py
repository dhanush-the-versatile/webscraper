"""FastAPI application factory and entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RateLimitMiddleware, RequestContextMiddleware

logger = get_logger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    logger.info("startup", environment=settings.ENVIRONMENT, project=settings.PROJECT_NAME)
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    configure_logging()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ---- Middleware (order matters: last added runs first) ----
    app.add_middleware(RateLimitMiddleware, limit=240, window_seconds=60)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["meta"], summary="Service metadata")
    async def root() -> dict:
        return {
            "name": settings.PROJECT_NAME,
            "version": "1.0.0",
            "docs": "/docs",
            "api": settings.API_V1_PREFIX,
        }

    return app


app = create_app()
