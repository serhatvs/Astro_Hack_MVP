"""FastAPI entrypoint for the Space Agriculture AI MVP."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.errors import (
    GENERIC_RETRY_MESSAGE,
    INVALID_INPUT_MESSAGE,
    normalize_http_error_detail,
)
from app.api.mission import router as mission_router
from app.api.recommend import router as recommend_router
from app.routes.demo_cases import router as demo_cases_router
from app.routes.health import router as health_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create the FastAPI application instance."""

    allowed_origins = ["*"]

    application = FastAPI(
        title="Adaptive Closed-Loop Space Agriculture AI",
        version="0.1.0",
        description=(
            "Mission-aware crop and growing-system recommendation engine for "
            "closed-loop space agriculture planning."
        ),
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:  # noqa: ARG001
        return JSONResponse(
            status_code=422,
            content={"detail": INVALID_INPUT_MESSAGE},
        )

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:  # noqa: ARG001
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": normalize_http_error_detail(exc.status_code, exc.detail)},
            headers=exc.headers,
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error on %s.", request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": GENERIC_RETRY_MESSAGE},
        )

    @application.get("/")
    def root() -> dict[str, object]:
        """Minimal root route for deployment health visibility."""

        return {
            "message": "Astro Hack MVP API is running",
            "status": "ok",
            "endpoints": [
                "/health",
                "/demo-cases",
                "/recommend",
                "/simulation/start",
                "/simulate",
                "/mission/step",
            ],
        }

    application.include_router(demo_cases_router)
    application.include_router(health_router)
    application.include_router(recommend_router)
    application.include_router(mission_router)
    return application


app = create_app()
