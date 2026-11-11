# Management TypeScript client

The platform provides a **private workspace package**, `@ocarinow/management-client`.
It is used by the console; it is not a published general-purpose TypeScript AI SDK.
Its checked-in types come from the management OpenAPI contract.

```typescript
import { createManagementClient } from '@ocarinow/management-client'

const client = createManagementClient('/api/management')
const { status, requestId } = await client.getStatus()
```

`getStatus(signal?: AbortSignal)` returns
`Promise<{ status: SystemStatus; requestId: string | null }>`.
The base URL defaults to `/api/management` for the console's proxy. Direct service
consumers use the service's `/management/v1` base. An optional second factory
argument injects a fetch-compatible function for integration/testing.

The client uses `GET`, same-origin credentials, no-store caching and a five-second
timeout combined with the optional cancellation signal. It validates the foundation
status shape and returns only its allowlisted fields. An invalid request ID becomes
`null`; it is not echoed blindly.

Failures throw `ManagementApiError`, whose `status` is the HTTP status, `0` for a
transport failure, or `502` for an invalid response shape. `requestId` may be null.
The message is deliberately generic. This client does not implement login,
organization operations, API-key issuance or inference.
