"""Initial platform identity storage and least-privilege runtime grants."""

from alembic import op

revision: str = "0073_identity"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create the frozen initial schema without importing evolving ORM metadata."""
    statements = (
        """CREATE TABLE platform.principals (
            id UUID PRIMARY KEY,
            kind VARCHAR(32) NOT NULL CHECK (kind IN ('user', 'service_account')),
            active BOOLEAN NOT NULL
        )""",
        """CREATE TABLE platform.identity_bindings (
            id UUID PRIMARY KEY,
            principal_id UUID NOT NULL REFERENCES platform.principals(id),
            issuer VARCHAR(512) NOT NULL CHECK (length(issuer) > 0),
            subject VARCHAR(255) NOT NULL CHECK (length(subject) > 0),
            UNIQUE (issuer, subject)
        )""",
        """CREATE TABLE platform.organizations (
            id UUID PRIMARY KEY,
            display_name VARCHAR(100) NOT NULL
                CHECK (length(trim(display_name)) BETWEEN 1 AND 100),
            version INTEGER NOT NULL CHECK (version > 0),
            desired_revision INTEGER NOT NULL,
            applied_revision INTEGER NOT NULL,
            CHECK (applied_revision >= 0 AND desired_revision >= applied_revision)
        )""",
        """CREATE TABLE platform.memberships (
            organization_id UUID NOT NULL REFERENCES platform.organizations(id),
            principal_id UUID NOT NULL REFERENCES platform.principals(id),
            role VARCHAR(16) NOT NULL CHECK (role IN ('owner', 'viewer')),
            active BOOLEAN NOT NULL,
            PRIMARY KEY (organization_id, principal_id)
        )""",
        """CREATE TABLE platform.authorization_outbox (
            organization_id UUID NOT NULL,
            revision INTEGER NOT NULL CHECK (revision > 0),
            principal_id UUID NOT NULL,
            role VARCHAR(16) NOT NULL CHECK (role IN ('owner', 'viewer')),
            operation VARCHAR(16) NOT NULL CHECK (operation IN ('grant', 'revoke')),
            PRIMARY KEY (organization_id, revision),
            FOREIGN KEY (organization_id, principal_id)
                REFERENCES platform.memberships(organization_id, principal_id)
        )""",
        """CREATE TABLE platform.audit_events (
            organization_id UUID NOT NULL REFERENCES platform.organizations(id),
            id UUID NOT NULL,
            actor_id UUID NOT NULL REFERENCES platform.principals(id),
            target_id UUID NOT NULL,
            request_id UUID NOT NULL,
            action VARCHAR(32) NOT NULL CHECK (
                action IN ('organization.created', 'organization.renamed', 'membership.granted')
            ),
            outcome VARCHAR(16) NOT NULL CHECK (outcome = 'succeeded'),
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (organization_id, id)
        )""",
        "CREATE INDEX audit_recent ON platform.audit_events (organization_id, occurred_at DESC)",
        "GRANT USAGE ON SCHEMA platform TO ocai_gateway",
        """GRANT SELECT, INSERT, UPDATE ON
            platform.principals, platform.identity_bindings, platform.organizations,
            platform.memberships, platform.authorization_outbox TO ocai_gateway""",
        "GRANT SELECT, INSERT ON platform.audit_events TO ocai_gateway",
        "GRANT SELECT ON platform.alembic_version TO ocai_gateway",
    )
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    """Reject automatic destructive rollback; restoration needs an operator procedure."""
    raise RuntimeError("Destructive schema downgrade is not supported; restore a reviewed backup.")
