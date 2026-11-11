"""Bounded access-denial evidence independent of successful organization mutations."""

from alembic import op

revision: str = "0077_security_events"
down_revision: str | None = "0075_bootstrap"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Keep denied attempts append-only and free of request bodies or credentials."""
    op.execute("""CREATE TABLE platform.security_events (
        id UUID PRIMARY KEY,
        request_id UUID NOT NULL,
        target_id UUID,
        action VARCHAR(32) NOT NULL CHECK (action IN
            ('organization.read', 'organization.update', 'identity.read')),
        outcome VARCHAR(16) NOT NULL CHECK (outcome IN ('unauthenticated', 'denied')),
        occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")
    op.execute("GRANT SELECT, INSERT ON platform.security_events TO ocai_gateway")


def downgrade() -> None:
    """Reject destructive evidence removal through automatic downgrade."""
    raise RuntimeError("Destructive schema downgrade is not supported; restore a reviewed backup.")
