"""Pytest fixtures for Public Pulse database tests.

Uses an SQLite in-memory database via SQLAlchemy's generic types.
A fresh in-memory database is created for each test function so tests
are fully isolated.

PostgreSQL-specific constraints tested here:
  - Enum validation at the SQLAlchemy / Python layer (works in SQLite)
  - UNIQUE constraints (enforced by SQLite)
  - FK constraints (enforced by SQLite with PRAGMA foreign_keys=ON)

Constraints NOT testable in SQLite (noted explicitly in test_database.py):
  - Partial unique index: UNIQUE(layer) WHERE is_active = TRUE
    (enforced by the Alembic migration against a live PostgreSQL DB only)
  - Native JSONB operators / GIN indexes
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from public_pulse.database.models import Base


@pytest.fixture(scope="function")
def engine():
    """Fresh SQLite in-memory engine per test."""
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable FK enforcement in SQLite (off by default)
    @event.listens_for(_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(_engine)
    yield _engine
    Base.metadata.drop_all(_engine)
    _engine.dispose()


@pytest.fixture(scope="function")
def db(engine):
    """Database session for one test; rolls back after the test."""
    with Session(engine) as session:
        yield session
        session.rollback()
