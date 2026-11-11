"""Explicit migration command; never invoked by HTTP startup or module import."""

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.util.exc import CommandError
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from app.storage.settings import DatabaseSettings


class MigrationError(Exception):
    """Sanitized migration failure for operator and automated callers."""


def upgrade(settings: DatabaseSettings) -> None:
    """Apply reviewed migrations using an explicitly supplied migration credential."""
    engine = create_engine(
        settings.url(),
        connect_args=settings.connection_options(),
        hide_parameters=True,
        poolclass=NullPool,
    )
    try:
        config = Config()
        config.set_main_option("script_location", str(Path(__file__).parents[2] / "migrations"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
    except (SQLAlchemyError, CommandError):
        raise MigrationError("Database migration failed.") from None
    finally:
        engine.dispose()


def main() -> int:
    """Run upgrade explicitly, reporting only safe operator-facing failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--local", action="store_true", help="Allow loopback development PostgreSQL"
    )
    args = parser.parse_args()
    try:
        upgrade(DatabaseSettings.from_env("OCAI_MIGRATION_DATABASE_URL", local=args.local))
    except (ValueError, MigrationError):
        print("Database migration failed; verify configuration, schema ownership and connectivity.")
        return 1
    print("Database migrations applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
