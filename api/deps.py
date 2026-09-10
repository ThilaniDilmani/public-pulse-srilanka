"""API dependencies for database session and security validation (Phase 11).

IMPORTANT: This module delegates the database engine to
`public_pulse.database.session` which guarantees .env is loaded before the
engine is created. Do NOT create a second engine here — that causes a silent
SQLite fallback when DATABASE_URL is not yet in os.environ.
"""

import os
from typing import Generator
from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

# Re-export the canonical session factory and get_db from session.py.
# session.py loads .env via find_dotenv() before creating the engine, so
# DATABASE_URL is always resolved to the real PostgreSQL URL at startup.
from public_pulse.database.session import engine, SessionLocal, get_db  # noqa: F401


def verify_api_key(x_api_key: str = Header(default=None)) -> str:
    """Validate API key header if API_KEY environment variable is configured."""
    expected_key = os.getenv("API_KEY")
    if expected_key:
        if not x_api_key or x_api_key != expected_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing X-API-Key header",
            )
    return x_api_key or "public"
