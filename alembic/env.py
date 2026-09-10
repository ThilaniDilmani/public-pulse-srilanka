"""Alembic migration environment for Public Pulse.

DATABASE_URL is read from the environment — never from alembic.ini.
The src/ directory is prepended to sys.path by alembic.ini so that
``public_pulse`` imports work during migration execution.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path
from dotenv import load_dotenv

from alembic import context
from sqlalchemy import engine_from_config, pool

load_dotenv()

# Ensure src/ is on the path (alembic.ini sets prepend_sys_path = src,
# but be explicit here in case env.py is run directly).
_src = Path(__file__).resolve().parents[2] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

# Import Base so Alembic can inspect the ORM metadata for autogenerate.
from public_pulse.database.models import Base  # noqa: E402

# Alembic Config object (gives access to alembic.ini values)
config = context.config

# Set up Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Provide the ORM metadata for autogenerate support
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Resolve DATABASE_URL from environment
# ---------------------------------------------------------------------------


def _get_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Run: export DATABASE_URL=postgresql://user:pass@host:5432/public_pulse"
        )
    return url


# ---------------------------------------------------------------------------
# Offline migrations (generate SQL without a live DB connection)
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations (connect to the live DB)
# ---------------------------------------------------------------------------


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _get_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
