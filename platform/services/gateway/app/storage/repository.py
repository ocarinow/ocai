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
        action: Literal["organization.created", "organization.renamed", "membership.granted"],
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
