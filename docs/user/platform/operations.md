# Operating the foundation preview

The reference development environment uses Python 3.13+, uv, the pinned Node
version, Docker, PostgreSQL, Keycloak and OpenFGA. It is a local qualification
profile, not a certified high-availability or production deployment.

From a repository checkout:

```bash
uv sync
npm ci --prefix platform
task serve:setup
task serve:all
```

`serve:setup` explicitly provisions local infrastructure, migrations and private
settings. Re-running it preserves established state. `serve:all` starts the apps
and authorization projector; it does not grant users access automatically.
`task serve:status` reports managed services; `task serve:stop` preserves their data.
Do not publish generated local environment settings or credential files.

## Identity and bootstrap

Keycloak verifies identities; PostgreSQL holds principals/memberships, and OpenFGA
evaluates the pinned organization relationship model. Inspect installation state
with `task serve:operator -- status`. Bootstrap requires the installation UUID and
the intended user's verified issuer subject; see the exact
[operator procedure](https://github.com/ocarinow/ocai/blob/main/platform/README.md#organization-bootstrap-and-openfga-authorization-wu-75).
Do not infer identity from an email or grant access merely because login succeeds.

The initial internal model has organization owners and viewers. Team, project and
attribute policies are planned extensions. Run the authorization worker to apply
outbox revisions; a pending revision or unavailable authorization never grants
access. Use the explicit reconciliation procedure after interrupted projection,
not a reset of bootstrap state.

Production deployment, model migration, cross-database recovery, enterprise SSO
profiles and replicated operation require further qualification. The
[platform development guide](https://github.com/ocarinow/ocai/blob/main/platform/README.md)
contains the maintained configuration and operational commands.
