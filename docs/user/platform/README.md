# Platform usage

The current platform is a **foundation preview**. Its console shows service status;
the service exposes liveness, readiness and non-sensitive system status. Identity
verification, organization storage and OpenFGA authorization services are implemented
internally, but authenticated console sessions and organization HTTP workflows are
not available on the current main-branch baseline.

You cannot yet create provider connections, issue inference keys, configure routing,
run gateway inference or inspect usage through this console. Proposed team/ABAC,
budget, caching and evaluation workflows are not user-facing features of this build.

## Open the console

Use the console address supplied by your installation operator. In a local development
installation it is `http://localhost:3000`. The status page reads the fixed backend
status operation through the console server. It does not forward your browser's
credentials or accept an arbitrary upstream URL.

`stage: foundation` and `inference_ready: false` are expected. The service's
`/health/ready` returns **503** with `gateway_not_ready`; `/health/live` returning
200 only establishes process liveness, not inference readiness or dependency health.

## API consumers

- [Management HTTP reference](../reference/management.md): exact published operations and response schemas.
- [Management client](client.md): the private TypeScript workspace client used by the console.
- [Operating the preview](operations.md): setup boundaries, bootstrap and recovery limitations.

For embedding ocai in your own gateway service, the separate
[Python integration guide](../gateway-integration.md) describes executable library
contracts. It is not a hosted gateway API or a claim that this console serves inference.
