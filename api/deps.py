"""API dependencies for database session and security validation (Phase 11)."""

import os
from typing import Generator
from fastapi import Header, HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Environment-driven database connection string (defaults to SQLite memory for testing safety)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
pool_kwargs = {"poolclass": StaticPool} if "sqlite" in DATABASE_URL or DATABASE_URL == "sqlite:///:memory:" else {"pool_pre_ping": True}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **pool_kwargs
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

if "sqlite" in DATABASE_URL or DATABASE_URL == "sqlite:///:memory:":
    from public_pulse.database.models import Base
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency producing a SQLAlchemy Session per HTTP request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
