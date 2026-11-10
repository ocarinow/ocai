# Platform stack and shared console

Status: selected product technologies with proposed integration boundaries.
The WU-35 foundation implements the shell, UI layer, typed status client, and
FastAPI request infrastructure; see [development instructions](../../platform/README.md).
Identity, persistence, authorization, and inference remain subsequent work.

## Selected technologies

| Concern | Choice | Boundary |
|---|---|---|
| Console | Nuxt, Vue, TypeScript | Product UI and browser session experience |
| UI | shadcn-vue and Tailwind | Owned components and Ocarinow design tokens |
| Tables | TanStack Table through shadcn-vue patterns | Table behavior; backend enforces authorized filtering and pagination |
| Backend | FastAPI | Management API and gateway serving; Pydantic stays outside the kernel |
| State | PostgreSQL | Authoritative platform state and configuration versions |
| Authorization | OpenFGA | Resource relationships and qualified conditions; backend enforces decisions |
| Instrumentation | OpenTelemetry | Export adapters; audit and accounting have separate durability contracts |

Start with Nuxt routing and built-in data fetching. TanStack Query is an optional
later choice when shared server-state caching requirements justify it; TanStack
Table does not require adopting Query or another router. The
[shadcn-vue data table guide](https://www.shadcn-vue.com/docs/components/data-table)
provides the table composition pattern.

Exact versions, migration tooling, session implementation, and the reference
identity provider must be selected and qualified in implementation WUs. OIDC is
the proposed first federation protocol; Keycloak is a candidate reference
integration, not a required customer identity provider. Anticipate SAML brokering
and later SCIM provisioning without implementing our own federation protocols.

## Shared frontend structure

```text
platform/
  apps/console/
    app/pages/
    app/features/
      gateway/
      administration/
      requests/
  packages/
    nuxt-ui/
      nuxt.config.ts
      app/assets/css/
      app/components/
    nuxt-platform/
      nuxt.config.ts
      app/layouts/
      app/components/
      app/composables/
      app/middleware/
    management-client/
```

The UI layer owns tokens, component source, accessible interaction patterns, and
reusable table behavior. It has no organization model or management API calls.
The platform layer extends it with the application shell, navigation extension
points, organization/compartment context, sessions, permission presentation, and
shared error handling. Product pages remain in the console.

The management client is an ordinary typed TypeScript package with no Nuxt
dependency. The platform layer and application features can consume it. Keep
layer composition shallow, dependencies explicit, and overrides deliberate;
avoid implicit product routes or domain behavior in generic components. Layers
compose applications at build time and do not create independently deployed
microfrontends. See the [Nuxt layer documentation](https://nuxt.com/docs/4.x/getting-started/layers).

Begin with one modular console. Add another application when its audience and
deployment lifecycle justify it, rather than creating empty future applications.
Organization switches must rescope or clear cached data, selections, subscriptions,
and in-flight work. UI permission helpers improve presentation; FastAPI remains
the enforcement boundary.

## Identity and configuration integration

Organizations establish account boundaries; teams group membership; users and
service accounts act as principals. Compartments constrain resource access and
processing. Their exact relationships, inheritance, and delegation rules need
an OpenFGA model exercised against real customer examples.

Resource grants and attribute conditions supplement roles. The backend supplies
trusted attributes, checks every operation, and intersects API-key scope with
current principal permissions. Explain effective access in the administration
experience without exposing resources the viewer cannot inspect.

PostgreSQL and OpenFGA updates need explicit ownership, synchronization, recovery,
and revocation semantics. Do not treat two independent writes as one transaction.
Keep OpenFGA administration private and service-authenticated. Pin authorization
model versions and test changes before rollout.

Console changes go through the management API. Versioned database configuration
is authoritative; files support bootstrap and import/export. Native generation
and provider-compatible entry points share the same governance and evidence
services. Platform code consumes public ocai APIs and does not add product
dependencies to `ocai.core`.
