"""Internal persistence models; API contracts do not expose ORM objects."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

SCHEMA_REVISION = "0073_identity"
SCHEMA = "platform"


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA)


class Principal(Base):
    __tablename__ = "principals"
    __table_args__ = (CheckConstraint("kind IN ('user', 'service_account')"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))
    active: Mapped[bool] = mapped_column(default=True)


class IdentityBinding(Base):
    __tablename__ = "identity_bindings"
    __table_args__ = (UniqueConstraint("issuer", "subject"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    principal_id: Mapped[UUID] = mapped_column(ForeignKey("platform.principals.id"))
    issuer: Mapped[str] = mapped_column(String(512))
    subject: Mapped[str] = mapped_column(String(255))


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint("length(trim(display_name)) BETWEEN 1 AND 100"),
        CheckConstraint("version > 0"),
        CheckConstraint("applied_revision >= 0 AND desired_revision >= applied_revision"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(default=1)
    desired_revision: Mapped[int] = mapped_column(default=0)
    applied_revision: Mapped[int] = mapped_column(default=0)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (CheckConstraint("role IN ('owner', 'viewer')"),)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform.organizations.id"), primary_key=True
    )
    principal_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform.principals.id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(16))
    active: Mapped[bool] = mapped_column(default=True)


class AuthorizationChange(Base):
    __tablename__ = "authorization_outbox"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "principal_id"],
            ["platform.memberships.organization_id", "platform.memberships.principal_id"],
        ),
        CheckConstraint("revision > 0"),
        CheckConstraint("role IN ('owner', 'viewer')"),
        CheckConstraint("operation IN ('grant', 'revoke')"),
    )

    organization_id: Mapped[UUID] = mapped_column(primary_key=True)
    revision: Mapped[int] = mapped_column(primary_key=True)
    principal_id: Mapped[UUID]
    role: Mapped[str] = mapped_column(String(16))
    operation: Mapped[str] = mapped_column(String(16))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(
            "action IN ('organization.created', 'organization.renamed', 'membership.granted')"
        ),
        CheckConstraint("outcome = 'succeeded'"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform.organizations.id"), primary_key=True
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("platform.principals.id"))
    target_id: Mapped[UUID]
    request_id: Mapped[UUID]
    action: Mapped[str] = mapped_column(String(32))
    outcome: Mapped[str] = mapped_column(String(16), default="succeeded")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
