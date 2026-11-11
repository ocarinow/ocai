"""Scoped persistence operations; authentication/authorization belong above this layer."""

from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models import AuditEvent
from app.storage.models import AuthorizationChange
from app.storage.models import IdentityBinding
from app.storage.models import Installation
from app.storage.models import Membership
from app.storage.models import Organization
from app.storage.models import Principal


@dataclass(frozen=True)
class OrganizationRecord:
    id: UUID
    display_name: str
    version: int
    desired_revision: int
    applied_revision: int


@dataclass(frozen=True)
class MembershipRecord:
    organization_id: UUID
    principal_id: UUID
    role: str
    active: bool


@dataclass(frozen=True)
class AuditRecord:
    id: UUID
    organization_id: UUID
    actor_id: UUID
    target_id: UUID
    request_id: UUID
    action: str


@dataclass(frozen=True)
class AuthorizationRecord:
    organization_id: UUID
    revision: int
    principal_id: UUID
    role: str
    operation: str


@dataclass(frozen=True)
class InstallationRecord:
    installation_id: UUID
    organization_id: UUID | None
    store_id: str | None
    model_id: str | None


class BootstrapConsumed(Exception):
    """Bootstrap state is absent, mismatched or consumed; never claim a second owner."""


class StaleWrite(Exception):
    """Resource version changed before the requested write."""


def _name(value: str) -> str:
    result = value.strip()
    if not 1 <= len(result) <= 100:
        raise ValueError("Display name must contain 1 to 100 characters.")
    return result


def _organization(row: Organization) -> OrganizationRecord:
    return OrganizationRecord(
        row.id, row.display_name, row.version, row.desired_revision, row.applied_revision
    )


class Repository:
    """Internal unit-of-work repository; callers must supply authorized scope."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def pending_authorization(self) -> tuple[UUID, ...]:
        """Maintenance-only discovery of at most ten organization IDs; not a tenant query."""
        identifiers = await self._session.scalars(
            select(Organization.id)
            .where(Organization.desired_revision > Organization.applied_revision)
            .order_by(Organization.id)
            .limit(10)
        )
        return tuple(identifiers)

    async def installation(self) -> InstallationRecord:
        """Read immutable installation identity and pinned authorization deployment."""
        row = await self._session.get(Installation, 1)
        if row is None:
            raise ValueError("Installation state is absent.")
        return InstallationRecord(
            row.installation_id, row.organization_id, row.store_id, row.model_id
        )

    async def lock_organization(self, organization_id: UUID) -> OrganizationRecord | None:
        """Serialize permission-sensitive operations with membership/projection changes."""
        row = await self._session.scalar(
            select(Organization).where(Organization.id == organization_id).with_for_update()
        )
        return None if row is None else _organization(row)

    async def lock_identity(self, *, issuer: str, subject: str) -> UUID | None:
        """Keep the active-principal decision stable through the caller's transaction."""
        return await self._session.scalar(
            select(Principal.id)
            .join(IdentityBinding, IdentityBinding.principal_id == Principal.id)
            .where(
                IdentityBinding.issuer == issuer,
                IdentityBinding.subject == subject,
                Principal.active.is_(True),
            )
            .with_for_update(of=Principal)
        )

    async def acknowledge(self, organization_id: UUID, revision: int) -> None:
        """Advance exactly one confirmed revision under the organization's lock."""
        row = await self._session.scalar(
            select(Organization).where(Organization.id == organization_id).with_for_update()
        )
        if row is None or row.applied_revision + 1 != revision or revision > row.desired_revision:
            raise ValueError("Authorization revision is out of order.")
        row.applied_revision = revision
        await self._session.flush()

    async def bootstrap(
        self,
        installation_id: UUID,
        *,
        issuer: str,
        subject: str,
        display_name: str,
        store_id: str,
        model_id: str,
        request_id: UUID,
    ) -> OrganizationRecord:
        """Consume operator-selected installation state and create the first owner atomically."""
        state = await self._session.scalar(
            select(Installation).where(Installation.singleton == 1).with_for_update()
        )
        if (
            state is None
            or state.installation_id != installation_id
            or state.organization_id is not None
        ):
            raise BootstrapConsumed("Installation bootstrap is unavailable or already consumed.")
        principal = await self.create_principal("user")
        await self.bind_identity(principal, issuer=issuer, subject=subject)
        organization = await self.create_organization(
            display_name, actor_id=principal, request_id=request_id
        )
        await self.grant_membership(
            organization.id, principal, role="owner", actor_id=principal, request_id=request_id
        )
        state.organization_id = organization.id
        state.store_id, state.model_id = store_id, model_id
        self._audit(
            organization.id, principal, organization.id, request_id, "installation.bootstrapped"
        )
        await self._session.flush()
        result = await self.organization(organization.id)
        assert result is not None
        return result

    async def revoke_membership(
        self,
        organization_id: UUID,
        principal_id: UUID,
        *,
        actor_id: UUID,
        request_id: UUID,
    ) -> None:
        """Make revocation effective in PostgreSQL immediately and queue ordered tuple deletion."""
        row = await self._session.scalar(
            select(Organization).where(Organization.id == organization_id).with_for_update()
        )
        member = await self._session.get(Membership, (organization_id, principal_id))
        if row is None or member is None:
            raise ValueError("Membership does not exist.")
        if not member.active:
            return
        member.active = False
        row.desired_revision += 1
        self._session.add(
            AuthorizationChange(
                organization_id=organization_id,
                revision=row.desired_revision,
                principal_id=principal_id,
                role=member.role,
                operation="revoke",
            )
        )
        self._audit(organization_id, actor_id, principal_id, request_id, "membership.revoked")
        await self._session.flush()

    async def create_principal(self, kind: Literal["user", "service_account"]) -> UUID:
        """Create a principal without granting organization access."""
        identifier = uuid4()
        self._session.add(Principal(id=identifier, kind=kind, active=True))
        await self._session.flush()
        return identifier

    async def bind_identity(self, principal_id: UUID, *, issuer: str, subject: str) -> UUID:
        """Bind exact issuer/subject values; never normalize or merge by email."""
        try:
            parsed = urlsplit(issuer)
            valid = (
                issuer.isascii()
                and 1 <= len(issuer) <= 512
                and parsed.scheme in {"http", "https"}
                and bool(parsed.hostname)
                and not (parsed.username or parsed.password or parsed.query or parsed.fragment)
                and 1 <= len(subject) <= 255
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("Invalid external identity binding.")
        identifier = uuid4()
        self._session.add(
            IdentityBinding(
                id=identifier, principal_id=principal_id, issuer=issuer, subject=subject
            )
        )
        await self._session.flush()
        return identifier

    async def resolve_identity(self, *, issuer: str, subject: str) -> UUID | None:
        """Resolve an exact binding only while its platform principal is active."""
        return await self._session.scalar(
            select(IdentityBinding.principal_id)
            .join(Principal, Principal.id == IdentityBinding.principal_id)
            .where(
                IdentityBinding.issuer == issuer,
                IdentityBinding.subject == subject,
                Principal.active.is_(True),
            )
        )

    async def create_organization(
        self, display_name: str, *, actor_id: UUID, request_id: UUID
    ) -> OrganizationRecord:
        """Persist an organization and its creation evidence in the same transaction."""
        row = Organization(
            id=uuid4(),
            display_name=_name(display_name),
            version=1,
            desired_revision=0,
            applied_revision=0,
        )
        self._session.add(row)
        await self._session.flush()
        self._audit(row.id, actor_id, row.id, request_id, "organization.created")
        return _organization(row)

    async def organization(self, organization_id: UUID) -> OrganizationRecord | None:
        """Read one explicitly scoped organization without exposing mutable ORM state."""
        row = await self._session.get(Organization, organization_id)
        return None if row is None else _organization(row)

    async def rename_organization(
        self,
        organization_id: UUID,
        display_name: str,
        *,
        version: int,
        actor_id: UUID,
        request_id: UUID,
    ) -> OrganizationRecord | None:
        """Serialize a versioned rename and persist its audit event atomically."""
        row = await self._session.scalar(
            select(Organization).where(Organization.id == organization_id).with_for_update()
        )
        if row is None:
            return None
        if row.version != version:
            raise StaleWrite("Organization version changed.")
        row.display_name = _name(display_name)
        row.version += 1
        self._audit(row.id, actor_id, row.id, request_id, "organization.renamed")
        return _organization(row)

    async def grant_membership(
        self,
        organization_id: UUID,
        principal_id: UUID,
        *,
        role: Literal["owner", "viewer"],
        actor_id: UUID,
        request_id: UUID,
    ) -> None:
        """Add a new membership with ordered projection intent and durable evidence.

        Raises:
            ValueError: The scoped organization does not exist.
        """
        row = await self._session.scalar(
            select(Organization).where(Organization.id == organization_id).with_for_update()
        )
        if row is None:
            raise ValueError("Organization does not exist.")
        self._session.add(
            Membership(
                organization_id=organization_id, principal_id=principal_id, role=role, active=True
            )
        )
        await self._session.flush()
        row.desired_revision += 1
        self._session.add(
            AuthorizationChange(
                organization_id=organization_id,
                revision=row.desired_revision,
                principal_id=principal_id,
                role=role,
                operation="grant",
            )
        )
        self._audit(organization_id, actor_id, principal_id, request_id, "membership.granted")

    async def membership(
        self, organization_id: UUID, principal_id: UUID
    ) -> MembershipRecord | None:
        """Read a member only inside the supplied organization."""
        row = await self._session.get(Membership, (organization_id, principal_id))
        return (
            None
            if row is None
            else MembershipRecord(row.organization_id, row.principal_id, row.role, row.active)
        )

    async def audit_events(self, organization_id: UUID) -> tuple[AuditRecord, ...]:
        """Read only this organization's evidence, bounded to the latest 100 events."""
        rows = await self._session.scalars(
            select(AuditEvent)
            .where(AuditEvent.organization_id == organization_id)
            .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id)
            .limit(100)
        )
        return tuple(
            AuditRecord(
                row.id, row.organization_id, row.actor_id, row.target_id, row.request_id, row.action
            )
            for row in rows
        )

    async def authorization_changes(self, organization_id: UUID) -> tuple[AuthorizationRecord, ...]:
        """Read the next bounded batch of unprojected changes in revision order."""
        rows = await self._session.scalars(
            select(AuthorizationChange)
            .join(Organization, Organization.id == AuthorizationChange.organization_id)
            .where(
                AuthorizationChange.organization_id == organization_id,
                AuthorizationChange.revision > Organization.applied_revision,
            )
            .order_by(AuthorizationChange.revision)
            .limit(100)
        )
        return tuple(
            AuthorizationRecord(
                row.organization_id, row.revision, row.principal_id, row.role, row.operation
            )
            for row in rows
        )

    def _audit(
        self,
        organization_id: UUID,
        actor_id: UUID,
        target_id: UUID,
        request_id: UUID,
        action: Literal[
            "organization.created",
            "organization.renamed",
            "membership.granted",
            "membership.revoked",
            "installation.bootstrapped",
        ],
    ) -> None:
        self._session.add(
            AuditEvent(
                organization_id=organization_id,
                id=uuid4(),
                actor_id=actor_id,
                target_id=target_id,
                request_id=request_id,
                action=action,
                outcome="succeeded",
            )
        )
