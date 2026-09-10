"""FastAPI application entrypoint for Public Pulse (Phase 11).

Analytical REST API for Sri Lankan TV news YouTube comment discourse.
Reads pre-scored data from PostgreSQL (batch-scored by pipeline/inference).
Does NOT trigger live classifier inference per HTTP request.
"""

import os
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import (
    health,
    channels,
    programs,
    analytics,
    evidence,
    insights,
    verification,
    jobs,
    sentiment,
    topics,
    comments,
    collection,
)

app = FastAPI(
    title="Public Pulse API",
    description=(
        "Multilingual civic discourse analytics platform for Sri Lankan TV news YouTube comments. "
        "Surfaces server-side aggregated topic distributions, stance trends, grounded insights, "
        "and faithfulness verification metrics."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS Configuration — allow dashboard origins
allowed_origins_env = os.getenv(
    "DASHBOARD_ORIGIN",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8501,http://127.0.0.1:8501"
)
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation Error", "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal Server Error", "detail": str(exc)},
    )


# Include API v1 Routers
PREFIX = "/api/v1"
app.include_router(health.router, prefix=PREFIX)
app.include_router(channels.router, prefix=PREFIX)
app.include_router(programs.router, prefix=PREFIX)
app.include_router(analytics.router, prefix=PREFIX)
app.include_router(evidence.router, prefix=PREFIX)
app.include_router(insights.router, prefix=PREFIX)
app.include_router(verification.router, prefix=PREFIX)
app.include_router(jobs.router, prefix=PREFIX)
app.include_router(collection.router, prefix=PREFIX)

# Backwards compatibility / convenience top-level endpoints
app.include_router(sentiment.router, prefix=PREFIX)
app.include_router(topics.router, prefix=PREFIX)
app.include_router(comments.router, prefix=PREFIX)


@app.get("/health")
def root_health():
    """Top-level health check."""
    return {"status": "ok", "version": "1.0.0"}
