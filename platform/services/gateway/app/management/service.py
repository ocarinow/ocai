"""Compose current identity, authorization, scoped state and durable evidence."""

from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from app.authorization.openfga import AuthorizationUnavailable
from app.authorization.service import AccessDenied
from app.authorization.service import Authorization
from app.identity.issuer import ExternalIdentity
from app.storage.database import Database
from app.storage.repository import OrganizationRecord


class OrganizationView(BaseModel):
    id: UUID
    display_name: str
    version: int
    can_update: bool


class IdentityView(BaseModel):
    principal_id: UUID
    organizations: list[OrganizationView]


class OrganizationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    display_name: str = Field(min_length=1, max_length=100)
    version: int = Field(gt=0, le=2147483647)

    @field_validator("display_name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        """Reject blank display names after the bounded input has been normalized."""
        result = value.strip()
        if not result:
            raise ValueError("Display name is blank.")
        return result


class UnboundPrincipal(AccessDenied):
    """The verified external identity has no active platform binding."""


def view(record: OrganizationRecord, *, can_update: bool) -> OrganizationView:
    """Expose only the management contract, excluding internal projection state."""
    return OrganizationView(
        id=record.id,
        display_name=record.display_name,
        version=record.version,
        can_update=can_update,
    )


class Management:
    """Short management transactions never share locks with provider execution."""

    def __init__(self, database: Database, authorization: Authorization) -> None:
        self.database = database
        self.authorization = authorization

    async def read(self, identity: ExternalIdentity, organization_id: UUID) -> OrganizationView:
        """Read a resource only after the live authorization gate succeeds."""
        async with self.authorization.transaction(identity, organization_id, "read") as scope:
            organization = await scope.repository.organization(organization_id)
            membership = await scope.repository.membership(organization_id, scope.actor_id)
            if organization is None or membership is None:
                raise AccessDenied("Resource access denied.")
            # The pinned owner/viewer model grants update only to owners. This is
            # presentation metadata; every mutation still performs its own FGA check.
            return view(organization, can_update=membership.role == "owner")

    async def update(
        self,
        identity: ExternalIdentity,
        organization_id: UUID,
        patch: OrganizationPatch,
        request_id: UUID,
    ) -> OrganizationView:
        """Commit a versioned rename and its correlated audit evidence atomically."""
        async with self.authorization.transaction(identity, organization_id, "update") as scope:
            organization = await scope.repository.rename_organization(
                organization_id,
                patch.display_name,
                version=patch.version,
                actor_id=scope.actor_id,
                request_id=request_id,
            )
            if organization is None:
                raise AccessDenied("Resource access denied.")
            return view(organization, can_update=True)

    async def me(self, identity: ExternalIdentity) -> IdentityView:
        """Resolve an active principal and individually authorize its candidate organizations."""
        async with self.database.transaction() as repository:
            principal = await repository.resolve_identity(
                issuer=identity.issuer, subject=identity.subject
            )
            if principal is None:
                raise UnboundPrincipal("No active platform binding.")
            try:
                candidates = await repository.identity_organizations(principal)
            except ValueError:
                raise AuthorizationUnavailable("Organization discovery is unavailable.") from None
        organizations: list[OrganizationView] = []
        for identifier in candidates:
            try:
                organizations.append(await self.read(identity, identifier))
            except AccessDenied:
                # A concurrent revocation removes visibility, never exposes stale names.
                continue
        return IdentityView(principal_id=principal, organizations=organizations)
