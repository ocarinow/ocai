"""Transactional authority checks and recoverable ordered relationship projection."""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.authorization.openfga import AuthorizationUnavailable
from app.authorization.openfga import OpenFGA
from app.identity.issuer import ExternalIdentity
from app.storage.database import Database
from app.storage.database import StorageError
from app.storage.repository import Repository


class AccessDenied(Exception):
    """Identity, organization and permission failures share one outward category."""


@dataclass(frozen=True)
class AuthorizedScope:
    actor_id: UUID
    organization_id: UUID
    repository: Repository


class Authorization:
    """Hold the organization and principal locks through the authorized transaction."""

    def __init__(self, database: Database, fga: OpenFGA) -> None:
        self._database = database
        self._fga = fga

    async def _binding(self, repository: Repository) -> None:
        state = await repository.installation()
        if (
            state.organization_id is None
            or state.store_id != self._fga.settings.store_id
            or state.model_id != self._fga.settings.model_id
        ):
            raise AuthorizationUnavailable("Authorization deployment is not synchronized.")

    @asynccontextmanager
    async def transaction(
        self,
        identity: ExternalIdentity,
        organization_id: UUID,
        action: Literal["read", "update"],
    ) -> AsyncGenerator[AuthorizedScope]:
        """Authorize short management work; never hold this context across inference or tools.

        Yields:
            Authorized repository and stable actor within this transaction only.

        Raises:
            AccessDenied: The identity or permission is not active for this organization.
            AuthorizationUnavailable: Projection, storage or OpenFGA cannot establish authority.
        """
        try:
            async with self._database.transaction() as repository:
                organization = await repository.lock_organization(organization_id)
                principal = await repository.lock_identity(
                    issuer=identity.issuer, subject=identity.subject
                )
                if (
                    organization is None
                    or principal is None
                    or time.time() >= identity.expires_at + 30
                ):
                    raise AccessDenied("Resource access denied.")
                membership = await repository.membership(organization_id, principal)
                if membership is None or not membership.active:
                    raise AccessDenied("Resource access denied.")
                await self._binding(repository)
                if organization.desired_revision != organization.applied_revision:
                    raise AuthorizationUnavailable("Authorization changes are pending.")
                if not await self._fga.check(organization_id, principal, action):
                    raise AccessDenied("Resource access denied.")
                yield AuthorizedScope(principal, organization_id, repository)
        except StorageError:
            raise AuthorizationUnavailable("Authorization storage is unavailable.") from None

    async def reconcile_pending(self) -> int:
        """Drain a bounded maintenance batch; each organization retains its own lock/order."""
        try:
            async with self._database.transaction() as repository:
                pending = await repository.pending_authorization()
        except StorageError:
            raise AuthorizationUnavailable("Authorization storage is unavailable.") from None
        applied = 0
        for organization_id in pending:
            applied += await self.reconcile(organization_id, limit=10)
        return applied

    async def reconcile(self, organization_id: UUID, *, limit: int = 100) -> int:
        """Apply bounded ordered changes; a crash after a write safely retries the same tuple.

        Returns:
            The number of revisions durably acknowledged by this invocation.
        """
        if not 1 <= limit <= 100:
            raise ValueError("Projection batch must contain 1 to 100 changes.")
        applied = 0
        for _ in range(limit):
            try:
                async with self._database.transaction() as repository:
                    organization = await repository.lock_organization(organization_id)
                    if organization is None:
                        raise AccessDenied("Resource access denied.")
                    await self._binding(repository)
                    if organization.desired_revision == organization.applied_revision:
                        return applied
                    changes = await repository.authorization_changes(organization_id)
                    if not changes or changes[0].revision != organization.applied_revision + 1:
                        raise AuthorizationUnavailable("Authorization outbox is inconsistent.")
                    await self._fga.project(changes[0])
                    await repository.acknowledge(organization_id, changes[0].revision)
                applied += 1
            except StorageError:
                raise AuthorizationUnavailable("Authorization storage is unavailable.") from None
        return applied
