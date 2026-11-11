# Errors, deadlines and troubleshooting

Provider failures map to shared exceptions such as `AuthError`, `RateLimitError`,
`ContextLengthError`, `ContentFilterError` and `TransientError`. Inspect their
canonical code, native evidence and retryability without logging raw sensitive
provider content. See [core exceptions](../reference/ocai-core.md).

| Symptom | Check |
|---|---|
| Provider cannot be resolved | Install its codec in the same environment; inspect your explicit catalog |
| `LookupError` when pinning Responses | This interface has declarations but no executable component |
| Missing credential / `CredentialError` | Supply a nonempty credential explicitly; confirm the requested env/file exists |
| Anthropic authentication failure | Use `x-api-key` with an empty scheme, not the default bearer header |
| Fidelity rejection | Inspect the phase, field losses and shifts; do not blindly retry an unsupported conversion |
| Incomplete stream | Inspect `outcome`; do not invent terminal usage or a successful finish |
| Platform readiness is 503 | The current foundation service deliberately has no configured inference path |

A `CallContext` may carry an aware UTC deadline. It bounds attempts and retry waits;
async I/O is cancelled at expiry. Sync enforcement is cooperative and cannot
preempt arbitrary blocking user code. A timeout does not prove an upstream operation
was not processed or charged. Configure bounded retries with an understanding of
possible duplicate side effects, especially around tool execution.

Use explicit transport and stream context managers to release resources. Keep
credentials out of `raw`, reports, context and logs. The HTTP transport does not make
caller-provided request/response content safe to publish.
