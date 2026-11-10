"""Real PostgreSQL qualification with isolated, automatically cleaned Docker storage."""

import asyncio
import os
import secrets
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError

from app.storage.database import Database
from app.storage.database import StorageConflict
from app.storage.database import StorageError
from app.storage.migrate import upgrade
from app.storage.repository import StaleWrite
from app.storage.settings import DatabaseSettings

pytestmark = pytest.mark.storage
DEPLOY = Path(__file__).resolve().parents[3] / "deploy" / "postgres"


def _docker(*args: str, input_text: str | None = None, env: dict[str, str] | None = None) -> str:
    try:
        result = subprocess.run(
            ["docker", *args],
            input=input_text,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pytest.fail("Storage integration requires an available Docker engine.", pytrace=False)
    if result.returncode:
        pytest.fail(f"Isolated PostgreSQL {args[0]} failed (details suppressed).", pytrace=False)
    return result.stdout.strip()


@dataclass(repr=False)
class Postgres:
    name: str
    runtime: DatabaseSettings
    migration: DatabaseSettings

    def sql(self, statement: str) -> str:
        return _docker(
            "exec",
            "-i",
            self.name,
            "psql",
            "-U",
            "postgres",
            "-d",
            "ocai",
            "-v",
            "ON_ERROR_STOP=1",
            "-At",
            input_text=statement,
        )

    def wait(self) -> None:
        for _ in range(60):
            ready = subprocess.run(
                [
                    "docker",
                    "exec",
                    self.name,
                    "pg_isready",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    "postgres",
                    "-d",
                    "ocai",
                ],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if ready.returncode == 0:
                return
            time.sleep(0.25)
        pytest.fail("Isolated PostgreSQL did not become ready.", pytrace=False)


@pytest.fixture(scope="session")
def postgres() -> Iterator[Postgres]:
    """Provision only disposable resources; never connect to a developer's database."""
    name = f"ocai-storage-test-{uuid4().hex}"
    migration_password = secrets.token_hex(32)
    runtime_password = secrets.token_hex(32)
    env = dict(os.environ)
    env.update(
        {
            "POSTGRES_PASSWORD": secrets.token_hex(32),
            "OCAI_MIGRATION_PASSWORD": migration_password,
            "OCAI_RUNTIME_PASSWORD": runtime_password,
        }
    )
    image = (DEPLOY / "image.txt").read_text().strip()
    try:
        _docker(
            "run",
            "--detach",
            "--rm",
            "--name",
            name,
            "--publish",
            "127.0.0.1::5432",
            "--env",
            "POSTGRES_PASSWORD",
            "--env",
            "POSTGRES_DB=ocai",
            image,
            env=env,
        )
        port = int(_docker("port", name, "5432/tcp").rsplit(":", 1)[1])

        def settings(user: str, password: str) -> DatabaseSettings:
            return DatabaseSettings(
                URL.create(
                    "postgresql+psycopg",
                    username=user,
                    password=password,
                    host="127.0.0.1",
                    port=port,
                    database="ocai",
                ).render_as_string(hide_password=False),
                local=True,
            )

        cluster = Postgres(
            name,
            settings("ocai_gateway", runtime_password),
            settings("ocai_migrator", migration_password),
        )
        cluster.wait()
        _docker(
            "exec",
            "-i",
            "--env",
            "OCAI_MIGRATION_PASSWORD",
            "--env",
            "OCAI_RUNTIME_PASSWORD",
            name,
            "psql",
            "-U",
            "postgres",
            "-d",
            "ocai",
            input_text=(DEPLOY / "bootstrap.sql").read_text(),
            env=env,
        )
        upgrade(cluster.migration)
        yield cluster
    finally:
        subprocess.run(
            ["docker", "rm", "--force", "--volumes", name],
            capture_output=True,
            timeout=30,
            check=False,
        )


async def _seed(database: Database) -> tuple[UUID, UUID]:
    async with database.transaction() as repository:
        actor = await repository.create_principal("user")
        organization = await repository.create_organization(
            "Storage qualification", actor_id=actor, request_id=uuid4()
        )
    return actor, organization.id


async def test_migration_persistence_restart_and_scoped_reads(postgres: Postgres) -> None:
    database = Database(postgres.runtime)
    await database.open()
    try:
        actor, organization_id = await _seed(database)
        other_actor, other_organization = await _seed(database)
        subject = uuid4().hex
        async with database.transaction() as repository:
            await repository.bind_identity(
                actor, issuer="https://identity.example/realm", subject=subject
            )
            await repository.grant_membership(
                organization_id, actor, role="owner", actor_id=actor, request_id=uuid4()
            )
            await repository.grant_membership(
                other_organization,
                other_actor,
                role="owner",
                actor_id=other_actor,
                request_id=uuid4(),
            )
    finally:
        await database.close()
    _docker("restart", postgres.name)
    port = int(_docker("port", postgres.name, "5432/tcp").rsplit(":", 1)[1])
    postgres.runtime = DatabaseSettings(
        postgres.runtime.url().set(port=port).render_as_string(hide_password=False), local=True
    )
    postgres.migration = DatabaseSettings(
        postgres.migration.url().set(port=port).render_as_string(hide_password=False), local=True
    )
    postgres.wait()
    upgrade(postgres.migration)  # Reapplying head must not reset data or grants.
    restored = Database(postgres.runtime)
    await restored.open()
    try:
        async with restored.transaction() as repository:
            organization = await repository.organization(organization_id)
            assert organization is not None
            assert (organization.desired_revision, organization.applied_revision) == (1, 0)
            assert (
                await repository.resolve_identity(
                    issuer="https://identity.example/realm", subject=subject
                )
                == actor
            )
            assert await repository.membership(other_organization, actor) is None
            member = await repository.membership(organization_id, actor)
            assert member is not None and member.role == "owner"
            events = await repository.audit_events(organization_id)
            assert {event.action for event in events} == {
                "organization.created",
                "membership.granted",
            }
            assert all(event.organization_id == organization_id for event in events)
            changes = await repository.authorization_changes(organization_id)
            assert len(changes) == 1 and changes[0].principal_id == actor
            assert await repository.audit_events(uuid4()) == ()
    finally:
        await restored.close()


async def test_audit_failure_rolls_back_state_and_projection(postgres: Postgres) -> None:
    database = Database(postgres.runtime)
    await database.open()
    try:
        actor, organization_id = await _seed(database)
        with pytest.raises(StorageConflict, match="Storage constraint conflict"):
            async with database.transaction() as repository:
                await repository.rename_organization(
                    organization_id,
                    "Must roll back",
                    version=1,
                    actor_id=uuid4(),
                    request_id=uuid4(),  # Audit actor FK fails at commit.
                )
        with pytest.raises(StorageConflict):
            async with database.transaction() as repository:
                await repository.grant_membership(
                    organization_id, actor, role="owner", actor_id=uuid4(), request_id=uuid4()
                )
        async with database.transaction() as repository:
            organization = await repository.organization(organization_id)
            assert organization is not None and organization.display_name == "Storage qualification"
            assert organization.version == 1 and organization.desired_revision == 0
            assert await repository.membership(organization_id, actor) is None
            assert await repository.authorization_changes(organization_id) == ()
            assert len(await repository.audit_events(organization_id)) == 1
    finally:
        await database.close()


async def test_identity_conflict_is_atomic_and_sanitized(postgres: Postgres) -> None:
    database = Database(postgres.runtime)
    await database.open()
    marker = f"private-subject-{uuid4().hex}"
    try:
        async with database.transaction() as repository:
            actor = await repository.create_principal("user")
            await repository.bind_identity(actor, issuer="https://identity.example", subject=marker)
        duplicate: UUID | None = None
        with pytest.raises(StorageConflict) as error:
            async with database.transaction() as repository:
                duplicate = await repository.create_principal("user")
                await repository.bind_identity(
                    duplicate, issuer="https://identity.example", subject=marker
                )
        assert marker not in str(error.value)
        assert error.value.__suppress_context__
        async with database.transaction() as repository:
            assert (
                await repository.resolve_identity(issuer="https://identity.example", subject=marker)
                == actor
            )
        assert duplicate is not None
        assert (
            postgres.sql(f"SELECT count(*) FROM platform.principals WHERE id = '{duplicate}'")
            == "0"
        )
    finally:
        await database.close()


async def test_concurrent_grants_and_versioned_mutations(postgres: Postgres) -> None:
    database = Database(postgres.runtime)
    await database.open()
    try:
        actor, organization_id = await _seed(database)

        async def grant() -> None:
            async with database.transaction() as repository:
                member = await repository.create_principal("user")
                await repository.grant_membership(
                    organization_id, member, role="viewer", actor_id=actor, request_id=uuid4()
                )

        await asyncio.gather(*(grant() for _ in range(5)))
        async with database.transaction() as repository:
            revisions = await repository.authorization_changes(organization_id)
            assert [change.revision for change in revisions] == [1, 2, 3, 4, 5]
            changed = await repository.rename_organization(
                organization_id, "Renamed", version=1, actor_id=actor, request_id=uuid4()
            )
            assert changed is not None and changed.version == 2
        with pytest.raises(StaleWrite):
            async with database.transaction() as repository:
                await repository.rename_organization(
                    organization_id, "Stale", version=1, actor_id=actor, request_id=uuid4()
                )
        async with database.transaction() as repository:
            assert len(await repository.audit_events(organization_id)) == 7
    finally:
        await database.close()


async def test_cancellation_rolls_back_and_releases_pool(postgres: Postgres) -> None:
    database = Database(postgres.runtime)
    await database.open()
    actor, _ = await _seed(database)
    cancelled_id: UUID | None = None
    try:
        with pytest.raises(asyncio.CancelledError):
            async with database.transaction() as repository:
                organization = await repository.create_organization(
                    "Cancelled", actor_id=actor, request_id=uuid4()
                )
                cancelled_id = organization.id
                raise asyncio.CancelledError
        assert cancelled_id is not None
        async with database.transaction() as repository:
            assert await repository.organization(cancelled_id) is None
            assert await repository.audit_events(cancelled_id) == ()
    finally:
        await database.close()


async def test_privilege_and_schema_checks_fail_closed(postgres: Postgres) -> None:
    migration_connection = Database(postgres.migration)
    try:
        with pytest.raises(StorageError):
            await migration_connection.open()
    finally:
        await migration_connection.close()
    postgres.sql("GRANT UPDATE ON platform.audit_events TO ocai_gateway")
    runtime = Database(postgres.runtime)
    try:
        with pytest.raises(StorageError):
            await runtime.open()
    finally:
        postgres.sql("REVOKE UPDATE ON platform.audit_events FROM ocai_gateway")
        await runtime.close()
    postgres.sql("REVOKE INSERT ON platform.memberships FROM ocai_gateway")
    try:
        with pytest.raises(StorageError):
            await runtime.open()
    finally:
        postgres.sql("GRANT INSERT ON platform.memberships TO ocai_gateway")
        await runtime.close()
    postgres.sql("UPDATE platform.alembic_version SET version_num = 'future'")
    try:
        with pytest.raises(StorageError):
            await runtime.open()
    finally:
        postgres.sql("UPDATE platform.alembic_version SET version_num = '0073_identity'")
        await runtime.close()


def test_runtime_cannot_tamper_or_cross_membership_foreign_key(postgres: Postgres) -> None:
    engine = create_engine(postgres.runtime.url(), hide_parameters=True)
    try:
        for statement in (
            "DELETE FROM platform.audit_events",
            "UPDATE platform.audit_events SET outcome='failed'",
            "TRUNCATE platform.audit_events",
            "ALTER TABLE platform.audit_events ADD COLUMN leak TEXT",
            "UPDATE platform.alembic_version SET version_num='forged'",
        ):
            with pytest.raises(DBAPIError), engine.begin() as connection:
                connection.execute(text(statement))
        # A principal in A cannot be referenced as a member of B by an outbox row.
        with pytest.raises(DBAPIError), engine.begin() as connection:
            actor, org_a, org_b = uuid4(), uuid4(), uuid4()
            connection.execute(
                text("INSERT INTO platform.principals VALUES (:id, 'user', true)"), {"id": actor}
            )
            for identifier in (org_a, org_b):
                connection.execute(
                    text("INSERT INTO platform.organizations VALUES (:id, 'Org', 1, 0, 0)"),
                    {"id": identifier},
                )
            connection.execute(
                text("INSERT INTO platform.memberships VALUES (:org, :actor, 'owner', true)"),
                {"org": org_a, "actor": actor},
            )
            connection.execute(
                text(
                    "INSERT INTO platform.authorization_outbox "
                    "VALUES (:org, 1, :actor, 'owner', 'grant')"
                ),
                {"org": org_b, "actor": actor},
            )
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "dsn, local",
    [
        ("not-a-url-with-private-marker", False),
        ("postgresql+psycopg://user:private-marker@remote/db", False),
        ("postgresql+psycopg://user:private-marker@remote/db", True),
        ("postgresql+psycopg://user:private-marker@localhost/db?options=unsafe", True),
    ],
)
def test_invalid_settings_do_not_expose_credentials(dsn: str, local: bool) -> None:
    with pytest.raises(ValueError) as error:
        DatabaseSettings(dsn, local=local)
    assert "private-marker" not in str(error.value)


def test_configuration_repr_redacts_and_has_no_ambient_discovery() -> None:
    settings = DatabaseSettings("postgresql+psycopg://u:private-marker@localhost/db", local=True)
    assert "private-marker" not in repr(settings)
    with pytest.raises(ValueError, match="required"):
        DatabaseSettings.from_env(f"ABSENT_{uuid4().hex}")
