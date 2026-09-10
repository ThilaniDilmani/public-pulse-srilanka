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
from pathlib import Path
from typing import Generator

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

log = logging.getLogger(__name__)

# Guarantee environment loading before engine initialization (do not override explicit test env)
if "DATABASE_URL" not in os.environ:
    env_path = find_dotenv(usecwd=True)
    if env_path:
        load_dotenv(env_path)
    else:
        repo_env = Path(__file__).resolve().parents[3] / ".env"
        if repo_env.exists():
            load_dotenv(repo_env)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class DatabaseConfigurationError(RuntimeError):
    """Raised when DATABASE_URL is missing/invalid for a real (non-test) run.

    This project stores real research data (collected YouTube comments,
    ML predictions, etc.) in PostgreSQL/Supabase. Silently falling back to
    an empty in-memory SQLite database made the API/dashboard *look* like
    it worked while actually showing zero records. That fallback has been
    removed for normal application execution -- fail loudly instead.
    """


def _get_database_url() -> str:
    """Read DATABASE_URL from the environment.

    Raises DatabaseConfigurationError if it is missing, UNLESS
    PUBLIC_PULSE_ALLOW_SQLITE_FALLBACK=1 is explicitly set (e.g. for a
    throwaway local script). Test suites do not go through this function
    at all -- they build their own isolated SQLite engine directly in
    tests/conftest.py.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        if os.environ.get("PUBLIC_PULSE_ALLOW_SQLITE_FALLBACK") == "1":
            log.warning(
                "DATABASE_URL not set; PUBLIC_PULSE_ALLOW_SQLITE_FALLBACK=1 "
                "so falling back to sqlite:///:memory:. This DB is EMPTY -- "
                "never use this for real analytics/dashboard data."
            )
            return "sqlite:///:memory:"
        raise DatabaseConfigurationError(
            "DATABASE_URL is not set. Public Pulse requires a real "
            "PostgreSQL/Supabase connection string (see .env). Refusing to "
            "silently fall back to an empty in-memory SQLite database, "
            "since that would make the API/dashboard show zero records "
            "while looking like it succeeded. Set DATABASE_URL in your "
            ".env file, or set PUBLIC_PULSE_ALLOW_SQLITE_FALLBACK=1 if you "
            "really intend to run against a throwaway empty database."
        )
    # Suppress credentials from log output.
    safe_url = url.split("@")[-1] if "@" in url else "<url>"
    log.debug("Connecting to database host: %s", safe_url)
    return url


def _make_engine():
    url = _get_database_url()
    if "sqlite" in url:
        from sqlalchemy.pool import StaticPool
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
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