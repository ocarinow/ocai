"""One-use installation bootstrap and membership revocation evidence."""

from alembic import op

revision: str = "0075_bootstrap"
down_revision: str | None = "0073_identity"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Seed exactly one installation state; migrations never re-arm an existing bootstrap."""
    for statement in (
        """CREATE TABLE platform.installation (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            installation_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
            organization_id UUID REFERENCES platform.organizations(id),
            store_id VARCHAR(26), model_id VARCHAR(26),
            CHECK ((organization_id IS NULL AND store_id IS NULL AND model_id IS NULL)
                OR (organization_id IS NOT NULL AND store_id IS NOT NULL AND model_id IS NOT NULL))
        )""",
        "INSERT INTO platform.installation(singleton) VALUES (1)",
        "GRANT SELECT, UPDATE ON platform.installation TO ocai_gateway",
        "ALTER TABLE platform.audit_events DROP CONSTRAINT audit_events_action_check",
        """ALTER TABLE platform.audit_events ADD CONSTRAINT audit_events_action_check
            CHECK (action IN ('organization.created', 'organization.renamed',
                'membership.granted', 'membership.revoked', 'installation.bootstrapped'))""",
    ):
        op.execute(statement)


def downgrade() -> None:
    """Never reset consumed installation state by automatic downgrade."""
    raise RuntimeError("Destructive schema downgrade is not supported; restore a reviewed backup.")
