# Platform development

Implemented: the first console-to-API foundation (WU-35). Organization access,
PostgreSQL state, OpenFGA authorization, provider connections, inference, durable
audit, and accounting are subsequent slices, not enabled features. The service
exposes only public, non-sensitive health and system-status operations.

## Layout

```text
apps/console/                   Nuxt app and product pages
services/gateway/
  app/main.py                   FastAPI composition and entry point
  app/middleware/               reusable request/error infrastructure
  tests/                        service and middleware qualification
  pyproject.toml, uv.lock        isolated application environment; no wheel
packages/
  nuxt-ui/                      owned UI components and theme
  nuxt-platform/                reusable shell with navigation slot
  management-client/            plain TypeScript client and generated API types
spec/management.openapi.json    provisional management API contract
tests/                         client/layer boundary and browser integration tests
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

Install the test browser once, then run the repository gate:

```bash
cd platform
npx playwright install chromium
cd ..
uv run python scripts/check.py
```

`scripts/check_platform.py` runs platform lint, strict Python and TypeScript
checks, OpenAPI/type drift checks, HTTP/client/boundary tests, a production Nuxt
build, and Playwright against the built console and real FastAPI service. Ports
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
