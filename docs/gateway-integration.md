# Integrating a governed AI Gateway

ocai supplies execution and conversion mechanisms. The gateway authenticates the
caller, establishes trusted tenant/principal/compartment facts, selects a bound
model, owns budgets and persistence, and serves HTTP. No private facade method or
provider SDK is needed. The working integration is
[`examples/governed_gateway.py`](../examples/governed_gateway.py), exercised over
recorded OpenAI and Anthropic HTTP/SSE by `test_gateway_qualification.py`.

## Compose a governed model

Use `ocai.chat.model` with an explicit `Catalog`, credential, `conversion_policy`,
port `interceptors`, wire `policies` and passive `observers`. Credential application
belongs only to the transport leaf: for OpenAI use `ApiKey(key)`; Anthropic's direct
API uses `ApiKey(key, header="x-api-key", scheme="")`. The platform supplies keys;
there is no ambient discovery. Do not put secrets in context, options or reports.

Every configured unary interceptor must also implement `intercept_stream` and
`aintercept_stream`; otherwise streaming fails closed. Streaming continuations
return owned streams and are single-use. Admission happens before I/O for remote
and local ports. Durable required audit writes belong in admission middleware;
observer exceptions are deliberately isolated and cannot enforce a requirement.

`CallContext` carries trusted tenant, principal, compartment, call_id, parent_id,
correlation_id and an optional aware UTC deadline. Kernel code neither authenticates
these facts nor interprets customer authorization. Policies receive context on
request/outcome objects; governance metadata is not serialized into provider
bodies or headers. One deadline bounds attempts and retry waits. Async transport
operations are cancelled at expiry. Sync enforcement is cooperative: transport
phase timeouts are bounded and late results rejected, but arbitrary blocking user
code cannot be forcibly preempted. Use a separate execution boundary if that is
required by the gateway's service-level policy.

## Inspect, then execute

Convert the client request with:

```python
ingress = catalog.convert(client_payload, CHAT_COMPLETIONS_REQUEST, CANONICAL_CHAT_REQUEST)
policy.enforce(ingress.report, phase="client_request")
prepared = model.prepare(ingress.value, streaming=False)
inspection = prepared.inspection
policy.enforce(inspection.request_report, phase="request", route=inspection.route)
result = prepared.chat(ctx=trusted_context)
```

Import canonical constants from `ocai.chat`, and client constants from
`ocai.openai.chat_completions.codec`. `PreparedChatCall` also offers `achat`,
`stream`, and `astream`. Set `streaming=True` for either streaming face.
Preparation does no provider I/O and starts no logical invocation. The handle
executes a detached snapshot; changes to the caller's original request cannot
change it. Middleware changes to approved semantics and changes to effective
binding configuration are rejected before credentials are applied. A new request
or configuration requires new preparation. Handles are in-process execution
objects, not transferable authorization tokens.

Inspection separates selected route/path, edge contract declarations, actual
request findings, capability declarations, catalog/configuration identity and
conformance resource pointers. Unknown coverage is `None`; coverage is not claimed
complete. Resource pointers are not evidence that certification was run. Hashes
identify declarations/effective configuration, not executable artifact integrity.

Use `FidelityPolicy` to deny dispositions and semantic shift kinds, or supply
pure `allow_loss` / `allow_shift` predicates. A raising predicate fails closed.
`report.lossless` alone is insufficient: relocation and other semantic changes can
occur in a lossless report. Bind the same policy to the model so each physical
attempt rechecks request acceptance. `FidelityPolicyError` preserves report,
usage and route without exposing the rejected response body.

## Account for every leg exactly once

| Leg | Public API | Evidence |
| --- | --- | --- |
| Client request → canonical | `Catalog.convert` | `ingress.report` |
| Canonical request → selected provider | `model.prepare` / execution | Included in execution report |
| Selected provider response → canonical | `chat` or completed stream | Included in execution report |
| Canonical response → client | `Catalog.convert` / `stream_converter` | Egress report |

For unary delivery, merge ingress, **execution**, and egress reports. Do not also
append the preparation report: execution already contains it. Enforce the combined
response policy before serving the response. Keep `CallResult.usage` even when a
client wire schema cannot express a consumption dimension; the egress finding
reports that limitation. Never replace unknown usage with zero.

`ClientMetadata(id, model, created).bind(document)` in
`ocai.openai.chat_completions.client` binds explicit gateway serving identity.
The plugin does not invent timestamps or response IDs. A foreign provider reference
cannot become an OpenAI reference; the edge reports it and omits the foreign ID.
Serving metadata must not be treated as provider-side resumable state.

## Stream with explicit ownership

Use `with stream` or `async with stream`; otherwise call `close` or `aclose`.
Cancellation while pulling async data closes upstream. Cancellation inside the
consumer body requires the owning context manager. Streams have a single owner;
to stop an active async consumer, cancel and await that task. Do not concurrently
call `aclose` on a running async generator.

Feed canonical chunks through
`catalog.stream_converter(CANONICAL_CHAT_CHUNK, CHAT_COMPLETIONS_CHUNK)`. The egress
edge produces JSON events, not HTTP/SSE bytes. It keeps no accumulated text or
argument buffer. Tool slots preserve identity and order; part starts must be in
canonical order. A final part inconsistent with delivered deltas fails conversion.

Hold the terminal finish/usage events until upstream has exhausted successfully,
then `flush` the egress pipeline and enforce the complete ledger. The example
context manager does this and retains delivery evidence after early close or
failure, including a stream never consumed. Frame events as SSE in gateway code;
emit `[DONE]` only after the delivery outcome is completed. On a late violation,
stop delivery and use the gateway's chosen failure protocol. Previously delivered
content cannot be retracted. No transparent restart or cross-provider continuation
is supported. Incomplete/error streams never acquire a successful `StreamEnd`.

## Observe without turning events into payload logs

The factory emits one logical invocation start and one documented terminal outcome;
physical-attempt events count network attempts, not admission waits. Stream start
is eager and transport open is lazy. A never-consumed stream remains pending until
explicitly closed; garbage collection is not a durable audit mechanism.

Events contain correlation, safe accounting, route where available and error type;
they contain no request/response/header bodies or error messages. Context tags and
extensions are excluded. Authorized observers can receive tenant/principal facts
and fidelity evidence, so exporters must allowlist identity fields and redact or
omit sensitive report paths/notes. Client ingress rejection and client egress
serving outcomes are gateway events: kernel lifecycle describes the capability
invocation, not the surrounding HTTP transaction.

## Qualified initial surface

| Feature | Qualification |
| --- | --- |
| Single-choice text and system/user/assistant/tool history | Both provider paths; system relocation reported |
| Function calls, tool results, named choice and parallel identity/order | Canonical mapping and reverse fold fixtures; provider-specific losses remain visible |
| JSON-object / JSON-schema output intent | OpenAI mapping; Anthropic requires a schema and reports name/strict differences |
| Strict function-tool enforcement, message names, unknown nested fields | Preserved as evidence; not silently replayed or advertised as enforced |
| Refusal, stop/length/tool/filter finish | Client unary/stream mapping; unknown native codes retained with findings |
| Input/output/cache/reasoning usage | Known disjoint buckets survive; missing remains absent; other dimensions reported |
| Provider references | Scope guards apply; foreign IDs are not forwarded as resumable references |
| Unknown envelope/nested inputs | Forward-compatible preservation and encoding findings |
| n > 1, media execution, hosted search/MCP, background/realtime, logprobs | Outside this gateway qualification; report/reject, do not promise compatibility |

Tests use recorded synthetic wire pairs and golden/fold fixtures, never live
credentials or provider SDK mocks. Qualification concerns the selected repository
interface revisions, not every feature of a provider's evolving API.
