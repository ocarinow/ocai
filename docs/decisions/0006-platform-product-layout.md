# 0006 — Platform product layout

- **Status:** accepted
- **Date:** 2026-11-10
- **Deciders:** maintainer

## Context

The AI Gateway is the first deployable product built on ocai. Observability,
evaluation, catalogs, and agent tooling will follow. The repository's top-level
language directories represent independently distributed libraries: Python
packages for PyPI, future TypeScript packages for npm, and future Go modules.

Putting the gateway under `python/apps/` would organize a product by its backend
implementation language and blur the established library boundary. The maintainer
preferred a top-level `platform/` home for deployable products and internal shared
code. This decision records the target layout; it does not create a running
gateway or change the active kernel work queue.

## Decision

Keep distributed libraries in the existing language directories. Place platform
products under `platform/`, organized by responsibility:

```text
python/packages/                    independently distributed Python libraries
typescript/                         future distributed TypeScript libraries
go/                                 future distributed Go modules
spec/                               language-neutral kernel contracts

platform/
  services/
    gateway/                        first deployable backend service
      pyproject.toml
      app/                          application modules (ADR 0009)
      tests/
      migrations/
  apps/
    console/                        platform web application
  packages/
    contracts/                      minimal internal shared platform contracts
  spec/                             platform API, event, configuration contracts
  deploy/
    gateway/                        image, deployment, example configuration assets
  tests/
    integration/                    tests spanning platform components

examples/gateway-knowledge-assistant/  pilot integration example
docs/design/platform/                      platform architecture and product documentation
docs/plans/                         authoritative WU queue for all tracks
docs/decisions/                     shared architectural decision records
scripts/check.py                    repository verification entry point
```

Create directories when their first implementation needs them. The tree is an
ownership map, not a requirement to populate empty projects. A backend can have
a `pyproject.toml` and produce a wheel without being a public library.

Dependencies flow from platform applications/services into internal platform
packages and independently distributed ocai libraries. Distributed libraries must
not import platform implementation code or require the platform to be installed.
Provider conversion remains in provider plugins; gateway routing, administration,
persistence, and HTTP serving belong to the product.

Internal shared packages are not automatically published. A telemetry, evaluation,
or other satellite library belongs under a language directory when deliberately
designed and qualified for independent use. A deployable service using that
library stays under `platform/services/`.

Keep platform contracts distinct from canonical kernel schemas. Platform contracts
may reference kernel contracts without copying or silently changing them. The
platform asset catalog remains distinct from `ocai.convert.Catalog`.

Give the platform Python projects a separate dependency environment and lockfile
from the public-library workspace. The frontend has its own JavaScript dependency
workspace. Released platform artifacts pin qualified library dependencies;
integration CI also exercises locally built library wheels. Exact workspace
configuration, frontend tooling, import namespaces, and package versions are
implementation decisions still to settle. Preserve PEP 420 for any packages that
contribute to the `ocai` namespace.

The first gateway may serve inference and administration in one process, with
explicit authorization and internal boundaries. This layout does not require a
microservice per product feature or separate control/data-plane deployments.

## Alternatives considered

- **`python/apps/ocai-gateway` with a separate root web directory.** Rejected
  because top-level language directories identify distributed libraries and
  should not become the home of platform products.
- **Put every shared platform module in public library packages.** Rejected
  because internal reuse does not establish an independently supportable API or
  justify public distribution.
- **Create a complete service tree for the long-term portfolio immediately.**
  Deferred because service boundaries should follow implemented workflows and
  operational needs, not a list of possible future products.

## Consequences

The kernel and gateway can develop and release independently. The platform can
pin a qualified kernel release while integration tests reveal incompatibilities
with ongoing library work. Separate lockfiles add dependency-update work but
avoid coupling public-library development to all platform dependencies.

The gateway scaffolding WU must add executable dependency-boundary checks,
isolated artifact tests, and the relevant platform checks to repository
verification. Until platform code exists, this is an accepted layout decision,
not a claim that its runtime boundaries have already been tested.

Implement the gateway service, console, and management API together in the first
product slice, with the shared contracts they actually use, deployment assets,
and integration tests. Keep planning and ADRs in the existing shared documentation locations.
