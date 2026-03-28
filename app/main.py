"""FastAPI entrypoint for the Space Agriculture AI MVP."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.demo_cases import router as demo_cases_router
from app.routes.health import router as health_router
from app.routes.recommend import router as recommend_router
from app.routes.simulate import router as simulate_router


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
                "/simulate",
            ],
        }

    application.include_router(demo_cases_router)
    application.include_router(health_router)
    application.include_router(recommend_router)
    application.include_router(simulate_router)
    return application


app = create_app()
