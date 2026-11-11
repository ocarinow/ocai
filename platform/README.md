# Platform development

Implemented: the console-to-API foundation (WU-35) and internal PostgreSQL
identity storage with transactional audit/outbox writes (WU-73). Storage has no
protected HTTP surface yet. Organization access, OpenFGA enforcement, provider
connections, inference and accounting remain subsequent slices. The HTTP service
still exposes only public, non-sensitive health and system-status operations.

## Layout

```text
apps/console/                   Nuxt app and product pages
services/gateway/
  app/main.py                   FastAPI composition and entry point
  app/middleware/               reusable request/error infrastructure
  app/storage/                  scoped PostgreSQL unit of work and operator migration command
  migrations/                   reviewed Alembic revisions; no automatic startup migration
  tests/                        service and middleware qualification
  pyproject.toml, uv.lock        isolated application environment; no wheel
packages/
  nuxt-ui/                      owned UI components and theme
  nuxt-platform/                reusable shell with navigation slot
  management-client/            plain TypeScript client and generated API types
spec/management.openapi.json    provisional management API contract
tests/                         client/layer boundary and browser integration tests
deploy/postgres/                operator role bootstrap and pinned PostgreSQL test image
```

The gateway is an application, not a published Python distribution. Reuse its
middleware modules within the service; extract a backend package only when another
service demonstrates the need. Frontend packages are private npm workspaces.
The UI button follows the shadcn-vue composition approach using Reka UI, CVA, and
Tailwind; its source and Ocarinow theme are owned here. Additional components and
TanStack Table enter when a product workflow uses them.

## Install and run

Requires Python 3.13+, uv, and Node 24.15+ (or a Node version accepted by
`package.json`). Use the same Node version in development and CI. From the
repository root:

```bash
uv sync --project platform/services/gateway --frozen
npm ci --prefix platform
```

In separate terminals:

```bash
uv run --directory platform/services/gateway python -m app.main
npm run dev --prefix platform
```

Open the console at `http://localhost:3000`. The gateway binds only to
`127.0.0.1:8000`. The console's server calls a fixed status operation on the
private `NUXT_GATEWAY_BASE_URL` setting (default `http://127.0.0.1:8000`). It does
not forward browser cookies, authorization, arbitrary headers, or query parameters.
Redirects and automatic retries are disabled. This narrow status proxy is not a
general authenticated BFF; add session forwarding only with its identity WU.

`/health/live` indicates the process can serve HTTP. `/health/ready` deliberately
returns 503 until later work qualifies inference readiness. Console status never
turns this into a successful model-access claim. `/management/v1/status` reveals
only service identity, foundation stage, and false inference readiness.

## Verification

Install the test browser once and start Docker, then run the repository gate:

```bash
cd platform
npx playwright install chromium
cd ..
uv run python scripts/check.py
```

`scripts/check_platform.py` runs platform lint, strict Python and TypeScript
checks, OpenAPI/type drift checks, HTTP/client/boundary tests, a production Nuxt
build, real PostgreSQL storage tests, and Playwright against the built console and
real FastAPI service. Storage tests provision an isolated PostgreSQL 16.15 container
using `deploy/postgres/image.txt` (immutable multi-platform digest), generated
disposable credentials and a random loopback port, then remove that container and
its anonymous volume. They never reuse or reset a developer database. Docker or
image startup failure fails the gate instead of skipping the tests. Ports
8000 and 3100 must be free; tests never silently reuse a developer's server.
The deployment-source test imports a copy of `app/` outside the repository with
the service dependencies. It does not claim a container deployment was tested.

After intentionally changing the API contract, export and regenerate it:

```bash
uv run --directory platform/services/gateway python -c 'import json; from pathlib import Path; from app.main import create_app; Path("../../spec/management.openapi.json").write_text(json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n")'
npm run generate:client --prefix platform
```

Request middleware generates a server request ID and forwards ASGI messages
without body accumulation. Error bodies exclude exception/input details.
Completion records contain only ID, normalized method, route template, status,
outcome, and elapsed time. They are passive diagnostics, not audit durability.
The entry point disables Uvicorn access logs and forwarded-header trust; any
deployment proxy must have an equally deliberate logging/trust policy.

## PostgreSQL storage (WU-73)

The storage layer persists principals, exact issuer/subject bindings,
organizations, scoped memberships, pending authorization changes and allowlisted
audit events. Organization creation/rename and membership grant methods write
their audit evidence within the same transaction. Membership grants also increase
the desired authorization revision and append an ordered outbox entry. WU-75 implements OpenFGA
projection as described below; an unapplied grant does not establish access.

Repository methods require explicit organization scope. They are internal storage
operations, not an authorization boundary; a later application service must
authenticate and authorize callers before using them. There is no RLS claim.
Audit fields are identifiers, fixed action/outcome codes and timestamps; display
names, credentials and arbitrary request metadata are excluded. The runtime role
can read/append audit records but cannot edit, delete, truncate or alter them.
Database administrators retain control; this is not certified immutable storage.

For a **new dedicated database**, an operator with role/schema privileges runs
`deploy/postgres/bootstrap.sql` through `psql`. Supply `OCAI_MIGRATION_PASSWORD`
and `OCAI_RUNTIME_PASSWORD` explicitly from the deployment secret manager to that
process environment; the script reads them without putting passwords in command
arguments. Use ordinary explicit `psql` connection options for the administrative
connection. No application command discovers administrative credentials. The script
creates `ocai_migrator`, `ocai_gateway` and the `platform` schema, revokes public
database privileges/public-schema creation, and grants only the required connect
rights. Run it once; it refuses an existing role/schema instead of resetting data.
Do not run it against a shared application database. Managed databases requiring
operator-specific role provisioning must reproduce these grants and pass the same
runtime checks; they are not qualified automatically.

Set `OCAI_MIGRATION_DATABASE_URL` explicitly to the migration-role URL and run:

```bash
uv run --directory platform/services/gateway python -m app.storage.migrate
```

URLs use `postgresql+psycopg`, an explicit username/password/host/database and
`sslmode=verify-full` in production (plus `sslrootcert` when needed). Never paste a
real DSN into logs, issue reports or command arguments. The optional `--local`
profile permits loopback-only development connections without production TLS.
The application does not automatically read that setting or execute migrations.
There is no destructive reset/downgrade command; restore backups through an
operator-reviewed recovery procedure. WU-73 tests restart persistence, not a full
backup/restore deployment.

Backend callers construct `Database(DatabaseSettings(dsn))` explicitly, call
`await database.open()` to verify schema and runtime privileges, use
`async with database.transaction() as repository`, and close the database during
shutdown. Use the **runtime** DSN, not the migration DSN. Transactions are isolated
per async task; no global session or connection is shared. Pool capacity is five,
with five-second connection/pool/statement bounds, two-second lock waits and a
ten-second idle-transaction timeout. Storage exceptions expose safe categories,
not SQL/connection details. Do not enable SQLAlchemy/driver parameter logging.

Focused storage qualification (still requires Docker):

```bash
uv run --directory platform/services/gateway pytest -m storage
```

`pytest -m 'not storage'` is useful for HTTP-only iteration; it is not the full gate.

## Local services and reference identity (WU-74)

From the repository root, install Task, Docker, uv and the Node version specified
above, then run:

```bash
task serve:setup    # install dependencies, start PostgreSQL/Keycloak, apply migrations
task serve:all      # gateway + console; infrastructure/package dependencies run first
task serve:status   # inspect this checkout's development containers
task serve:stop     # stop infrastructure, preserve the PostgreSQL volume
```

Individual commands are `serve:gateway`, `serve:console`, `serve:postgres` and
`serve:keycloak`. Stop foreground gateway/console processes with Ctrl+C. Console
runs at `http://localhost:3000`, gateway at `http://127.0.0.1:8000`, Keycloak at
`http://localhost:18080` and PostgreSQL on loopback port 15432. The console still
shows foundation status; the user-facing login and session flow arrive in WU-76.
A fresh database needs the explicit `serve:setup` migration step. Ordinary service
startup does not silently migrate schemas. Docker images are pinned by digest in
`deploy/{postgres,keycloak}/image.txt`; the same versions run in required tests.

The helper creates `.local/platform/settings.json` with private permissions and
random credentials, plus an imported realm. The directory is gitignored. Local
Keycloak has username `developer` and a separate `ocai-admin` operator; their
passwords are respectively `OCAI_DEV_USER_PASSWORD` and
`OCAI_KEYCLOAK_ADMIN_PASSWORD` in that private settings file. Read them locally
when needed; do not print, paste or commit the file. The development user has no
platform membership. This profile uses local HTTP and Keycloak `start-dev`;
it is unsuitable for an exposed or production deployment.

The named Compose project belongs to this checkout. `stop` retains its data and
credentials; subsequent setup is idempotent. Keep settings and volumes together:
regenerating settings against an existing volume does not rotate database or
Keycloak credentials. Change development ports in the private settings before
first initialization. There is deliberately no automatic destructive reset.
These tasks select their own local profile explicitly; they do not load or replace
an active root `.env` or any `.envs/` environment.

Production service startup reads `OCAI_IDENTITY_ISSUER`,
`OCAI_IDENTITY_AUDIENCE` and `OCAI_CONSOLE_CLIENT_ID` explicitly. Use an HTTPS issuer
and the qualified Keycloak profile: confidential console client, Authorization
Code with S256 PKCE, exact callback URI, five-minute access tokens and an
`ocai-management` audience mapper applied to access tokens only. Use
`included.custom.audience` for this API audience, as specified in the
[Keycloak mapper reference](https://www.keycloak.org/admin-api/protocol-mappers). Password grant,
implicit flow and console service-account access are disabled. Select
`OCAI_LOCAL_DEVELOPMENT=1` only for the loopback HTTP profile. Direct external OIDC,
SAML federation and machine-token qualification are not implemented by this WU.

The reusable FastAPI identity dependency verifies one Authorization bearer token
through `joserfc` (RS256 allowlist). It validates issuer/audience, expiry/issued-at,
subject, Bearer token type and authorized console client. It rejects ID tokens,
forged identity headers, caller-selected key URLs and invalid credentials (401).
Discovery/JWKS requests have five-second bounds, a 64 KiB document limit, no
redirects/ambient proxies and at most 32 keys. Fresh keys are cached for at most
five minutes; refresh is single-flight with a five-second retry interval. An
outage can use fresh known keys but cannot extend their freshness; unavailable
verification returns sanitized 503. Token revocation at the IdP is not immediate
offline JWT revocation; platform membership enforcement is described in WU-75 below.

Focused identity qualification:

```bash
uv run --directory platform/services/gateway pytest tests/test_identity.py tests/test_keycloak.py
```

The real Keycloak test runs Authorization Code + PKCE and token exchange with
disposable accounts, then verifies access-token acceptance and ID-token rejection.
It uses ephemeral H2 storage for protocol qualification; the development Compose
service uses a separate PostgreSQL database/role. Missing Docker fails the gate.
For unit-only iteration, use `pytest -m 'not storage and not identity and not authorization'`; this is not
full verification. No live user or provider credentials are required.


## Organization bootstrap and OpenFGA authorization (WU-75)

OpenFGA runs separately from the gateway. Keycloak verifies identity; the platform
owns principals, memberships and grants in PostgreSQL; OpenFGA evaluates a reviewed
relationship model. The gateway combines all three. End users never call OpenFGA
or obtain its service credential. Future access-management screens will operate
through our management API; this WU provides internal services and operator
commands, not a role-editor UI.

The first model gives organization owners read/update and viewers read only.
Relationships identify stable platform principal UUIDs, not email addresses or
provider usernames. The adapter verifies the exact reviewed model at startup and
pins every request to its immutable model ID. `HIGHER_CONSISTENCY` checks do not
replace the platform's transactional synchronization checks. There is no positive
permission cache. Future team/resource relationships and conditional policies
require versioned model changes and their own qualification.

`task serve:setup` now provisions a separate OpenFGA PostgreSQL role/database,
runs its migrations explicitly, starts authenticated OpenFGA on loopback port
18081, and creates/verifies one pinned store/model. Their IDs and generated service
credentials stay in the private local settings. Rerunning setup preserves them.
Ordinary `serve:openfga` startup assumes this setup has already run. PostgreSQL-backed
state persists across stops/restarts. The tests use disposable in-memory OpenFGA
storage for protocol/race tests; local smoke verification also exercises PostgreSQL.

`task serve:all` starts gateway, console and the authorization projector.
`task serve:authorization` runs the projector by itself. It discovers a bounded
batch of pending organizations, applies changes in revision order, and records
acknowledgement only after OpenFGA confirms the tuple write. Multiple instances
serialize on organization locks. Structured logs report projected revision counts
or retrying dependency failures; no tokens, DSNs or raw tuples are logged.

For a new local installation, inspect its one-use state:

```bash
task serve:operator -- status
```

Inspect the intended user's exact subject in the trusted Keycloak realm. Then
explicitly consume the installation identity returned above:

```bash
task serve:operator -- bootstrap --installation INSTALLATION_UUID --subject TRUSTED_SUBJECT --name 'Example organization'
```

The configured issuer and that subject bind to a new platform principal. Initial
organization, owner membership, audit events and projection intent commit atomically.
Concurrent or repeated bootstrap is rejected. A rollback leaves bootstrap available;
a successful bootstrap followed by projection failure remains consumed, with pending
work safely recoverable. Do not reset installation state to recover projection.
The local developer account receives no authority until this command is run.

Start the worker or explicitly reconcile one organization:

```bash
task serve:operator -- reconcile --organization ORGANIZATION_UUID
```

The explicit command applies at most 100 revisions per invocation; repeat until
no pending work remains. The worker handles up to ten organizations and ten
revisions each per pass, then sleeps two seconds. A crash after a tuple write but
before acknowledgement replays that revision with OpenFGA's duplicate/missing
ignore semantics. Older grants cannot be replayed after later acknowledged
revocations. A dependency outage never becomes an implicit permission grant.

Production operators supply `OCAI_DATABASE_URL` with the gateway runtime role,
`OCAI_FGA_ENDPOINT` (HTTPS), `OCAI_FGA_STORE_ID`, `OCAI_FGA_MODEL_ID` and
`OCAI_FGA_TOKEN` explicitly. The OpenFGA API must be private and access-controlled;
the initial adapter uses a service bearer credential, not the user's login token.
Provision OpenFGA storage and migrate it separately with the pinned server version,
then use `python -m app.authorization.provision` to create/qualify a model and print
its non-secret IDs. Preserve these IDs in deployment configuration. Partial failed
provisioning may leave an unreferenced store; inspect it before operator cleanup.
No application startup creates stores or chooses a latest model implicitly.

Run `python -m app.authorization.operator status|bootstrap|reconcile|worker` from
the gateway environment; production omits `--local`. Bootstrap additionally requires
the explicit issuer/audience/console-client configuration from WU-74. A changed
store/model cannot reuse an old deployment's acknowledged revisions: the database
binding check fails closed. Model upgrades and coordinated multi-database restore
need a separately reviewed migration/reprojection procedure; automatic production
upgrade/restore is not claimed by this WU.

Backend handlers use `Authorization.transaction(identity, organization_id, action)`
for short management operations. It checks the current active principal and
membership, pinned deployment, matching desired/applied revisions and OpenFGA
permission. The yielded scope supplies actor/resource IDs and a transaction-bound
repository; changes and their audit commit before locks are released. Missing or
inaccessible resources raise the same `AccessDenied` category. Pending/unavailable
authorization raises `AuthorizationUnavailable`. HTTP error mapping and the first
protected console operation arrive in WU-77. Never keep this transaction open across
model generation, agent runs or arbitrary tool execution.

Revocation becomes effective in platform state immediately, independently of token
or tuple lifetime. A concurrent administrative mutation either commits under its
existing authorization before revocation or observes revocation and is denied.
Repository CRUD alone is not an authorization boundary; request handlers must use
the authorized scope. Maintenance bootstrap/projection paths are explicitly separate.

Focused qualification:

```bash
uv run --directory platform/services/gateway pytest tests/test_authorization.py
```

The suite exercises real OpenFGA and PostgreSQL, concurrent/replayed bootstrap,
rollback, owner/viewer isolation, current principal suspension, bounded projection,
crashes around tuple acknowledgement, concurrent reconcilers and revocation races.
No live user/provider credentials are required. Missing Docker fails verification.
