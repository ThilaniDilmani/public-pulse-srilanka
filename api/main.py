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

# CORS Configuration
allowed_origins = os.getenv("DASHBOARD_ORIGIN", "http://localhost:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
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

# Backwards compatibility / convenience top-level endpoints
app.include_router(sentiment.router, prefix=PREFIX)
app.include_router(topics.router, prefix=PREFIX)
app.include_router(comments.router, prefix=PREFIX)


@app.get("/health")
def root_health():
    """Top-level health check."""
    return {"status": "ok", "version": "1.0.0"}
