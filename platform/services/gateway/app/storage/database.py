"""Async unit-of-work lifecycle and runtime privilege/schema verification."""

from collections.abc import AsyncGenerator
from collections.abc import Sequence
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.storage.models import SCHEMA_REVISION
from app.storage.repository import Repository
from app.storage.settings import DatabaseSettings


class StorageError(Exception):
    """Safe storage failure; does not expose SQL, parameters or credentials."""


class StorageConflict(StorageError):
    """A database constraint prevented the requested transaction."""


class Database:
    def __init__(self, settings: DatabaseSettings) -> None:
        self._engine = create_async_engine(
            settings.url(),
            connect_args=settings.connection_options(),
            pool_size=5,
            max_overflow=0,
            pool_timeout=5,
            pool_pre_ping=True,
            hide_parameters=True,
            echo=False,
        )
        self._sessions = async_sessionmaker(self._engine, expire_on_commit=False)
        self._ready = False

    async def open(self) -> None:
        """Verify the migrated schema and least-privilege runtime role.

        Raises:
            StorageError: The database is unavailable, unmigrated or overprivileged.
        """
        self._ready = False
        try:
            async with self._engine.connect() as connection:
                revisions: Sequence[object] = (
                    (
                        await connection.execute(
                            text("SELECT version_num FROM platform.alembic_version")
                        )
                    )
                    .scalars()
                    .all()
                )
                safe = await connection.scalar(
                    text("""
                    SELECT NOT (rolsuper OR rolcreaterole OR rolcreatedb OR rolbypassrls)
                      AND NOT has_schema_privilege(current_user, 'platform', 'CREATE')
                      AND NOT has_database_privilege(current_user, current_database(), 'CREATE')
                      AND NOT pg_has_role(current_user,
                        (SELECT nspowner FROM pg_namespace WHERE nspname = 'platform'), 'MEMBER')
                      AND NOT has_table_privilege(current_user,
                        'platform.audit_events', 'UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                      AND has_table_privilege(current_user, 'platform.audit_events', 'INSERT')
                      AND has_table_privilege(current_user, 'platform.audit_events', 'SELECT')
                    FROM pg_roles WHERE rolname = current_user
                """)
                )
                if list(revisions) != [SCHEMA_REVISION] or safe is not True:
                    raise StorageError("Database schema or runtime privileges are invalid.")
        except SQLAlchemyError:
            raise StorageError("Database initialization failed.") from None
        self._ready = True

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[Repository]:
        """Commit all state and evidence together; roll back on any exception.

        Yields:
            A transaction-scoped repository; never retain it after this block.

        Raises:
            StorageConflict: A uniqueness, reference or value constraint failed.
            StorageError: Storage is unavailable or has not been verified.
        """
        if not self._ready:
            raise StorageError("Database has not been initialized.")
        try:
            async with self._sessions.begin() as session:
                yield Repository(session)
        except IntegrityError:
            raise StorageConflict("Storage constraint conflict.") from None
        except SQLAlchemyError:
            raise StorageError("Storage operation failed.") from None

    async def close(self) -> None:
        """Release pooled connections; no transaction can start until reopened."""
        self._ready = False
        await self._engine.dispose()
