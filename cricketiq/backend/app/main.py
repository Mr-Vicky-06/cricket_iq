"""FastAPI Application entrypoint for CricketIQ — ICC & MCC Rules Intelligence Assistant."""

import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cricketiq.backend.app.api.routes.health import router as health_router

try:
    from cricketiq.backend.app.api.routes.rules import router as rules_router
except ImportError:
    rules_router = None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="CricketIQ — ICC & MCC Rules Intelligence API",
        description=(
            "Evidence-grounded cricket rules assistant with format-aware "
            "precedence resolution, deterministic citation verification, and strict abstention."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID and timing middleware
    @app.middleware("http")
    async def add_process_time_and_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        start_time = time.perf_counter()

        response = await call_next(request)

        process_time_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"
        return response

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "request_id": request_id,
            },
        )

    # Include routers
    app.include_router(health_router)
    if rules_router is not None:
        app.include_router(rules_router)

    return app


app = create_app()
