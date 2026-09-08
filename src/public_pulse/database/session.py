"""SQLAlchemy engine, session factory, and FastAPI dependency for Public Pulse.

DATABASE_URL is read from the environment — never hard-coded.
Load it from .env locally (python-dotenv) or from platform secrets in
production (GitHub Actions, Hugging Face Spaces).

Usage:
    from public_pulse.database.session import get_db, engine

    # As a FastAPI dependency:
    @app.get("/comments")
    def list_comments(db: Session = Depends(get_db)):
        ...

    # As a plain context manager (scripts, pipeline):
    with SessionLocal() as db:
        ...
"""

import logging
import os
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def _get_database_url() -> str:
    """Read DATABASE_URL from environment, defaulting to in-memory SQLite if absent."""
    url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    # Suppress credentials from log output.
    safe_url = url.split("@")[-1] if "@" in url else "<url>"
    log.debug("Connecting to database host: %s", safe_url)
    return url



def _make_engine():
    url = _get_database_url()
    if "sqlite" in url:
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )



engine = _make_engine()

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=True,
)

# ---------------------------------------------------------------------------
# FastAPI / dependency-injection helper
# ---------------------------------------------------------------------------


def get_db() -> Generator[Session, None, None]:
    """Yield a database session; always close on exit.

    Intended for use as a FastAPI Depends() dependency.  Can also be used
    directly in scripts via contextlib.contextmanager semantics:

        from contextlib import closing
        with closing(next(get_db())) as db:
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Health-check helper (used by api/main.py /health route)
# ---------------------------------------------------------------------------


def check_db_connection() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("Database health check failed: %s", exc)
        return False
