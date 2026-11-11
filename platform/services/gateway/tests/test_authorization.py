"""Real OpenFGA/PostgreSQL qualification of bootstrap, projection and revocation ordering."""

import asyncio
import os
import secrets
import subprocess
import time
from collections.abc import AsyncGenerator
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID
from uuid import uuid4

import httpx
import pytest

from app.authorization.openfga import MODEL
from app.authorization.openfga import AuthorizationUnavailable
from app.authorization.openfga import FGASettings
from app.authorization.openfga import OpenFGA
from app.authorization.service import AccessDenied
from app.authorization.service import Authorization
from app.identity.issuer import ExternalIdentity
from app.storage.database import Database
from app.storage.repository import AuthorizationRecord
from app.storage.repository import BootstrapConsumed
from tests.test_storage import Postgres
from tests.test_storage import provision_postgres

pytestmark = pytest.mark.authorization
ISSUER = "https://identity.example.test/realms/ocai"
DEPLOY = Path(__file__).resolve().parents[3] / "deploy" / "openfga"


@dataclass(repr=False)
class FGAServer:
    endpoint: str
    token: str


@pytest.fixture(scope="module")
def fga_server() -> Iterator[FGAServer]:
    """Provision disposable FGA; even local APIs require an explicit credential."""
    name = "ocai-fga-test-" + uuid4().hex
    token = secrets.token_hex(32)
    env = dict(os.environ, OPENFGA_AUTHN_PRESHARED_KEYS=token)
    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--name",
                name,
                "--publish",
                "127.0.0.1::8080",
                "--env",
                "OPENFGA_AUTHN_PRESHARED_KEYS",
                "--env",
                "OPENFGA_AUTHN_METHOD=preshared",
                "--env",
                "OPENFGA_PLAYGROUND_ENABLED=false",
                "--env",
                "OPENFGA_LOG_LEVEL=error",
                (DEPLOY / "image.txt").read_text().strip(),
                "run",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert result.returncode == 0, "Isolated OpenFGA must start."
        port = (
            subprocess.run(
                ["docker", "port", name, "8080/tcp"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            .stdout.strip()
            .rsplit(":", 1)[1]
        )
        endpoint = "http://127.0.0.1:" + port
        with httpx.Client(timeout=2, trust_env=False) as client:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    if client.get(endpoint + "/healthz").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.2)
            else:
                pytest.fail("Isolated OpenFGA did not become ready.", pytrace=False)
        yield FGAServer(endpoint, token)
    finally:
        subprocess.run(
            ["docker", "rm", "--force", "--volumes", name],
            capture_output=True,
            timeout=30,
            check=False,
        )


@pytest.fixture
async def fga(fga_server: FGAServer) -> AsyncGenerator[OpenFGA]:
    async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
        headers = {"Authorization": "Bearer " + fga_server.token}
        store = await client.post(
            fga_server.endpoint + "/stores", json={"name": "qualification"}, headers=headers
        )
        assert store.status_code == 201
        store_id: str = store.json()["id"]
        model = await client.post(
            fga_server.endpoint + f"/stores/{store_id}/authorization-models",
            json=MODEL,
            headers=headers,
        )
        assert model.status_code == 201
        model_id: str = model.json()["authorization_model_id"]
        adapter = OpenFGA(
            FGASettings(fga_server.endpoint, store_id, model_id, fga_server.token, local=True),
            client,
        )
        await adapter.open()
        yield adapter


@pytest.fixture
def cluster() -> Iterator[Postgres]:
    """Each authority test owns installation bootstrap state; no reset of real deployment data."""
    yield from provision_postgres()


@pytest.fixture
async def database(cluster: Postgres) -> AsyncGenerator[Database]:
    db = Database(cluster.runtime)
    try:
        await db.open()
        yield db
    finally:
        await db.close()


def identity(subject: str) -> ExternalIdentity:
    return ExternalIdentity(ISSUER, subject, "ocai-console", int(time.time()) + 300)


async def bootstrap(database: Database, fga: OpenFGA, subject: str = "owner") -> UUID:
    async with database.transaction() as repository:
        state = await repository.installation()
        organization = await repository.bootstrap(
            state.installation_id,
            issuer=ISSUER,
            subject=subject,
            display_name="Example",
            store_id=fga.settings.store_id,
            model_id=fga.settings.model_id,
            request_id=uuid4(),
        )
        return organization.id


async def test_bootstrap_concurrency_replay_and_rollback(database: Database, fga: OpenFGA) -> None:
    with pytest.raises(RuntimeError, match="injected"):
        async with database.transaction() as repository:
            state = await repository.installation()
            await repository.bootstrap(
                state.installation_id,
                issuer=ISSUER,
                subject="rolled-back",
                display_name="No commit",
                store_id=fga.settings.store_id,
                model_id=fga.settings.model_id,
                request_id=uuid4(),
            )
            raise RuntimeError("injected")
    async with database.transaction() as repository:
        assert (await repository.installation()).organization_id is None
        assert await repository.resolve_identity(issuer=ISSUER, subject="rolled-back") is None
    results = await asyncio.gather(
        bootstrap(database, fga, "one"), bootstrap(database, fga, "two"), return_exceptions=True
    )
    assert sum(isinstance(result, UUID) for result in results) == 1
    assert sum(isinstance(result, BootstrapConsumed) for result in results) == 1
    with pytest.raises(BootstrapConsumed):
        await bootstrap(database, fga, "third")


async def test_permissions_current_state_and_isolation(database: Database, fga: OpenFGA) -> None:
    organization = await bootstrap(database, fga)
    service = Authorization(database, fga)
    with pytest.raises(AuthorizationUnavailable):
        async with service.transaction(identity("owner"), organization, "read"):
            pytest.fail("Unprojected authority must not permit access.")
    assert await service.reconcile(organization) == 1
    async with service.transaction(identity("owner"), organization, "update") as scope:
        viewer = await scope.repository.create_principal("user")
        await scope.repository.bind_identity(viewer, issuer=ISSUER, subject="viewer")
        await scope.repository.grant_membership(
            organization, viewer, role="viewer", actor_id=scope.actor_id, request_id=uuid4()
        )
    assert await service.reconcile(organization) == 1
    async with service.transaction(identity("viewer"), organization, "read"):
        pass
    denied: tuple[tuple[ExternalIdentity, UUID, Literal["read", "update"]], ...] = (
        (identity("viewer"), organization, "update"),
        (identity("unknown"), organization, "read"),
        (identity("owner"), uuid4(), "read"),
    )
    for credential, resource, action in denied:
        with pytest.raises(AccessDenied):
            async with service.transaction(credential, resource, action):
                pytest.fail("Unexpected permission.")
    async with service.transaction(identity("owner"), organization, "update") as scope:
        await scope.repository.revoke_membership(
            organization, viewer, actor_id=scope.actor_id, request_id=uuid4()
        )
    # FGA still grants read, but current platform state denies it immediately.
    assert await fga.check(organization, viewer, "read")
    with pytest.raises(AccessDenied):
        async with service.transaction(identity("viewer"), organization, "read"):
            pytest.fail("Revoked viewer must be denied before projection.")
    assert await service.reconcile(organization) == 1
    assert not await fga.check(organization, viewer, "read")


async def test_crash_after_tuple_write_retries_without_granting_early(
    database: Database,
    fga: OpenFGA,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organization = await bootstrap(database, fga)
    service = Authorization(database, fga)
    project = fga.project

    async def interrupted(change: AuthorizationRecord) -> None:
        await project(change)
        raise RuntimeError("crash before acknowledgement")

    with monkeypatch.context() as patch:
        patch.setattr(fga, "project", interrupted)
        with pytest.raises(RuntimeError, match="crash"):
            await service.reconcile(organization)
    async with database.transaction() as repository:
        row = await repository.organization(organization)
        assert row is not None and row.applied_revision == 0 and row.desired_revision == 1
        principal = await repository.resolve_identity(issuer=ISSUER, subject="owner")
        assert principal is not None
    assert await fga.check(organization, principal, "update")
    with pytest.raises(AuthorizationUnavailable):
        async with service.transaction(identity("owner"), organization, "update"):
            pytest.fail("An unacknowledged tuple must not authorize an action.")
    assert await service.reconcile(organization) == 1
    async with service.transaction(identity("owner"), organization, "update"):
        pass


async def test_ordered_concurrent_reconcilers_cannot_restore_revoked_grants(
    database: Database,
    fga: OpenFGA,
) -> None:
    organization = await bootstrap(database, fga)
    service = Authorization(database, fga)
    async with database.transaction() as repository:
        principal = await repository.resolve_identity(issuer=ISSUER, subject="owner")
        assert principal is not None
        await repository.revoke_membership(
            organization, principal, actor_id=principal, request_id=uuid4()
        )
    assert (
        sum(await asyncio.gather(service.reconcile(organization), service.reconcile(organization)))
        == 2
    )
    assert await service.reconcile(organization) == 0
    assert not await fga.check(organization, principal, "read")
    with pytest.raises(AccessDenied):
        async with service.transaction(identity("owner"), organization, "read"):
            pytest.fail("Revocation must win over the older grant.")


async def test_revocation_serializes_after_an_authorized_audited_mutation(
    database: Database,
    fga: OpenFGA,
) -> None:
    organization = await bootstrap(database, fga)
    service = Authorization(database, fga)
    await service.reconcile(organization)
    started = asyncio.Event()

    async def revoke(principal: UUID) -> None:
        async with database.transaction() as repository:
            started.set()
            await repository.revoke_membership(
                organization, principal, actor_id=principal, request_id=uuid4()
            )

    async with service.transaction(identity("owner"), organization, "update") as scope:
        task = asyncio.create_task(revoke(scope.actor_id))
        try:
            await started.wait()
            await asyncio.sleep(0.05)
            assert not task.done()
            await scope.repository.rename_organization(
                organization,
                "Committed first",
                version=1,
                actor_id=scope.actor_id,
                request_id=uuid4(),
            )
        except BaseException:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            raise
    await task
    async with database.transaction() as repository:
        row = await repository.organization(organization)
        assert row is not None and row.display_name == "Committed first"
        actions = [event.action for event in await repository.audit_events(organization)]
        assert "organization.renamed" in actions and "membership.revoked" in actions
    with pytest.raises(AccessDenied):
        async with service.transaction(identity("owner"), organization, "update"):
            pytest.fail("A mutation after revocation must be denied.")


async def test_fga_outage_and_suspended_principal_fail_closed(
    database: Database,
    fga: OpenFGA,
    cluster: Postgres,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organization = await bootstrap(database, fga)
    service = Authorization(database, fga)

    async def unavailable(change: AuthorizationRecord) -> None:
        raise AuthorizationUnavailable("Dependency unavailable.")

    with monkeypatch.context() as patch:
        patch.setattr(fga, "project", unavailable)
        with pytest.raises(AuthorizationUnavailable):
            await service.reconcile(organization)
    await service.reconcile(organization)

    async def cannot_check(
        organization_id: UUID, principal_id: UUID, action: Literal["read", "update"]
    ) -> bool:
        raise AuthorizationUnavailable("Dependency unavailable.")

    with monkeypatch.context() as patch:
        patch.setattr(fga, "check", cannot_check)
        with pytest.raises(AuthorizationUnavailable):
            async with service.transaction(identity("owner"), organization, "read"):
                pytest.fail("Unavailable authorization must never permit access.")
    async with database.transaction() as repository:
        principal = await repository.resolve_identity(issuer=ISSUER, subject="owner")
        assert principal is not None
    cluster.sql(f"UPDATE platform.principals SET active = false WHERE id = '{principal}'")
    assert await fga.check(organization, principal, "update")
    with pytest.raises(AccessDenied):
        async with service.transaction(identity("owner"), organization, "read"):
            pytest.fail("Suspension must be effective independently of token or tuple lifetime.")


async def test_bounded_worker_batch(database: Database, fga: OpenFGA) -> None:
    organization = await bootstrap(database, fga)
    service = Authorization(database, fga)
    assert await service.reconcile_pending() == 1
    assert await service.reconcile_pending() == 0
    async with service.transaction(identity("owner"), organization, "read"):
        pass


async def test_provision_preserves_pinned_identifiers(
    fga_server: FGAServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.authorization.provision import provision

    monkeypatch.setenv("OCAI_FGA_ENDPOINT", fga_server.endpoint)
    monkeypatch.setenv("OCAI_FGA_TOKEN", fga_server.token)
    monkeypatch.setenv("OCAI_FGA_STORE_ID", "")
    monkeypatch.setenv("OCAI_FGA_MODEL_ID", "")
    monkeypatch.setenv("OCAI_LOCAL_DEVELOPMENT", "1")
    first = await provision()
    for key, value in first.items():
        monkeypatch.setenv(key, value)
    assert await provision() == first
    monkeypatch.setenv("OCAI_FGA_MODEL_ID", "0" * 26)
    with pytest.raises(AuthorizationUnavailable):
        await provision()


async def test_unqualified_model_and_response_fail_closed(fga: OpenFGA) -> None:
    async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
        # Valid OpenFGA model, deliberately outside the reviewed permission contract.
        model = await client.post(
            fga.settings.endpoint + f"/stores/{fga.settings.store_id}/authorization-models",
            json={"schema_version": "1.1", "type_definitions": [{"type": "principal"}]},
            headers={"Authorization": "Bearer " + fga.settings.token},
        )
        assert model.status_code == 201
        candidate = OpenFGA(
            FGASettings(
                fga.settings.endpoint,
                fga.settings.store_id,
                model.json()["authorization_model_id"],
                fga.settings.token,
                local=True,
            ),
            client,
        )
        with pytest.raises(AuthorizationUnavailable):
            await candidate.open()

    def redirect(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith(fga.settings.endpoint)
        return httpx.Response(302, headers={"location": "https://untrusted.example.test"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(redirect)) as client:
        with pytest.raises(AuthorizationUnavailable):
            await OpenFGA(fga.settings, client).open()


@pytest.mark.parametrize(
    "endpoint,store,token",
    [
        ("http://remote.example.test", "0" * 26, "a" * 32),
        ("https://user:secret@example.test", "0" * 26, "a" * 32),
        ("https://example.test?query=1", "0" * 26, "a" * 32),
        ("https://example.test", "../stores", "a" * 32),
        ("https://example.test", "0" * 26, "\x00" * 32),
    ],
)
def test_invalid_fga_configuration(endpoint: str, store: str, token: str) -> None:
    with pytest.raises(ValueError, match="Invalid authorization configuration"):
        FGASettings(endpoint, store, "0" * 26, token)
