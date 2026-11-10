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
the desired authorization revision and append an ordered outbox entry. OpenFGA
projection is not implemented yet; an unapplied grant does not establish access.

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
