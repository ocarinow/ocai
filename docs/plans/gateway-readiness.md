# Governed gateway readiness

Maintainer request: “make ocai ready to support a governed AI Gateway.”

This program follows merged WU-17–20 on main and takes priority over further
ordered-item modernization. Canonical 2026-07 stays active; ADR 0003 remains a
proposal. The gateway owns authentication, compartments, deployment selection,
budgets, persistence and HTTP serving. This program implements package contracts
only. One WU per PR, sequential stacks allowed; no merge is implied.

The maintainer explicitly authorized definition and implementation together;
implementation PRs follow this definition PR without a second approval pause.

## Supported client contract (initial qualification target, not shipped claims)

OpenAI Chat Completions single-choice chat with text, system/user/assistant/tool
history, function tools and results, tool choice, parallel tool identity/order,
JSON-object and JSON-schema output intent, refusal, stop/length/tool/content-filter
finish reasons, and available input/output/cache/reasoning usage. Provider/model
capability differences remain findings or admission failures, not guarantees.
The client model is a gateway deployment selector, never a canonical request field.
Response id/model/timestamp are serving metadata supplied explicitly by the gateway
or preserved by the plugin when available, never invented provider provenance.

Unknown fields survive decode in censused extensions; unknown finish values stay
verbatim. Unsupported fields are reported on encoding. Provider-scoped references
are governed by their scope and cannot be laundered across providers. Initial
qualification excludes n>1 choices, audio/video generation, realtime, hosted search,
MCP execution, background jobs, logprobs, and transparent generation continuation.
Excluded input must be reported/rejected, not silently advertised as compatible.
Immediate streaming exposes content before complete response inspection; a later
violation terminates delivery with partial accounting, never retracts output.

## Decisions and testing shared by every WU

ADR 0007 fixes the public design direction. No new canonical revision, part/delta,
provider API, runtime dependency, provider SDK, authentication or storage feature.
Core/port additions are before-release-gate frozen-candidate additions, documented by ADR;
runtime hooks remain provisional. No extension/provider_options knob is introduced
except a specifically censused preservation key in conversion WUs. Existing and
new synthetic recorded HTTP/SSE pairs use fake credentials and explicit provenance.
Each WU updates affected architecture sections and both status entries, runs
`uv run python scripts/check.py`, and pastes its summary verbatim into its PR.
New/changed edges follow `add-edge`; new wire pairs follow `record-wire-pair`.
Files shared by WUs are sequenced, never concurrently edited.

## Work units

## WU-21 — Define the gateway readiness program

- **Status:** ✅ Complete
- **Workstream:** Documentation.
- **Scope:** Publish this sequenced program, the supported client surface, and ADR 0007; no runtime change. Owns docs/plans/, docs/decisions/, docs/architecture.md. Other WU outcomes are out of scope.
- **Done:** A reviewer can trace every requested acceptance criterion to a WU and a documented contract.
- **Deps:** none.
- **Architecture:** §2–8, §11.
- **Freeze:** none (documentation only); ADR 0007.
- **Shapes/edges:** none; existing conversion behavior retained.
- **Decision:** Use the shared contracts and limits above and ADR 0007; no new dependency or provider knob.
- **Open:** none within this scope.

## WU-22 — Isolate transport credentials

- **Status:** ✅ Complete
- **Workstream:** Execution.
- **Scope:** Clone the wire request and its mutable fields before applying credentials on every driver path. Owns runtime/drivers.py, runtime/decisions.py, core/credentials.py, wire/http.py, driver tests. Other WU outcomes are out of scope.
- **Done:** Recorded transports receive auth while request/outcome hooks and retained references stay unauthenticated on success, failure, retry, and concurrent sync/async calls.
- **Deps:** 21.
- **Architecture:** §5–6, §8.
- **Freeze:** before-release-gate additive contracts where applicable; provisional runtime/plugin changes; ADR 0007.
- **Shapes/edges:** none; existing conversion behavior retained.
- **Decision:** Use the shared contracts and limits above and ADR 0007; no new dependency or provider knob.
- **Open:** none within this scope.

## WU-23 — Propagate context and enforce deadlines

- **Status:** ✅ Complete
- **Workstream:** Execution.
- **Scope:** Thread a per-call context snapshot through facade, drivers, and policies; carry trusted compartment and correlation facts; bound retry waits and physical operations by one deadline. Owns core/result.py, core/errors.py, runtime/decisions.py, runtime/drivers.py, wire/policies.py, wire/http.py, wire/transport.py, chat/facade.py, tests. Other WU outcomes are out of scope.
- **Done:** Different concurrent contexts reach every applicable hook without entering provider JSON/headers; expiration stops further attempts and sync/async deadline tests agree.
- **Deps:** 22.
- **Architecture:** §2.3, §3.3, §5–6, §8.
- **Freeze:** before-release-gate additive contracts where applicable; provisional runtime/plugin changes; ADR 0007.
- **Shapes/edges:** none; existing conversion behavior retained.
- **Decision:** Use the shared contracts and limits above and ADR 0007; no new dependency or provider knob.
- **Open:** none within this scope.

## WU-24 — Own and terminate streams explicitly

- **Status:** ✅ Complete
- **Workstream:** Streaming.
- **Scope:** Add close/aclose, context managers, and separate aborted evidence; propagate closure and failure through all generators and transport resources. Owns chat/types/stream.py, chat/facade.py, runtime/drivers.py, wire/transport.py, tests. Other WU outcomes are out of scope.
- **Done:** Normal fold behavior is unchanged; early close, cancellation, malformed EOF, and provider/transport failure release resources and preserve available usage/report without success synthesis.
- **Deps:** 23.
- **Architecture:** §3.1, §3.3, §5–6, §8.
- **Freeze:** before-release-gate additive contracts where applicable; provisional runtime/plugin changes; ADR 0007.
- **Shapes/edges:** none; existing conversion behavior retained.
- **Decision:** Use the shared contracts and limits above and ADR 0007; no new dependency or provider knob.
- **Open:** none within this scope.

## WU-25 — Govern streaming through port middleware

- **Status:** ✅ Complete
- **Workstream:** Streaming.
- **Scope:** Add explicit stream continuations and composable stream interception for local and remote ports; reject unary-only middleware on streaming rather than bypass it. Owns runtime/interceptors.py, chat/facade.py, chat/__init__.py, tests. Other WU outcomes are out of scope.
- **Done:** Admission denial performs no I/O on all four call faces; wrappers observe completion/failure/cancellation without buffering or generation restart.
- **Deps:** 24.
- **Architecture:** §3.2–3.4, §5, §8.
- **Freeze:** before-release-gate additive contracts where applicable; provisional runtime/plugin changes; ADR 0007.
- **Shapes/edges:** none; existing conversion behavior retained.
- **Decision:** Use the shared contracts and limits above and ADR 0007; no new dependency or provider knob.
- **Open:** none within this scope.

## WU-26 — Emit correlated passive lifecycle events

- **Status:** ✅ Complete
- **Workstream:** Streaming.
- **Scope:** Emit invocation and physical-attempt lifecycle events with safe metadata, terminal state, accounting and caller correlations; isolate observer failures. Owns runtime/observe.py, runtime/drivers.py, chat/facade.py, chat/__init__.py, tests. Other WU outcomes are out of scope.
- **Done:** Each invocation including rejection or unconsumed-then-closed streams has exactly one terminal event; attempts exclude admission waits; concurrent events remain isolated and credential-free.
- **Deps:** 25.
- **Architecture:** §2.3, §3.3, §5, §8.
- **Freeze:** before-release-gate additive contracts where applicable; provisional runtime/plugin changes; ADR 0007.
- **Shapes/edges:** none; existing conversion behavior retained.
- **Decision:** Use the shared contracts and limits above and ADR 0007; no new dependency or provider knob.
- **Open:** none within this scope.

## WU-27 — Expose immutable execution inspection

- **Status:** ✅ Complete
- **Workstream:** Conversion.
- **Scope:** Publish prepared execution handles and inspection data: route/path, declarations, coverage uncertainty, payload findings, catalog/configuration identity; snapshots cannot change between inspection and execution. Owns chat/facade.py, convert/, core/profile.py, tests. Other WU outcomes are out of scope.
- **Done:** Public APIs inspect and execute the same preparation; mutable input changes cannot change approved payload, and foreign/stale preparation is rejected before I/O.
- **Deps:** 23.
- **Architecture:** §2.5, §3.3, §4.1–4.3, §8.
- **Freeze:** before-release-gate additive contracts where applicable; provisional runtime/plugin changes; ADR 0007.
- **Shapes/edges:** none; existing conversion behavior retained.
- **Decision:** Use the shared contracts and limits above and ADR 0007; no new dependency or provider knob.
- **Open:** none within this scope.

## WU-28 — Enforce request and response fidelity policy

- **Status:** ✅ Complete
- **Workstream:** Conversion.
- **Scope:** Enforce caller predicates over FieldLoss and SemanticShift; reject request violations before I/O, retain accounting on response rejection, and document incremental streaming limits. Owns core/fidelity.py, chat/facade.py, chat/types/stream.py, tests. Other WU outcomes are out of scope.
- **Done:** Forbidden requests perform zero calls; response-policy errors retain reports and usage, including already-delivered stream output without claiming retraction.
- **Deps:** 24, 27.
- **Architecture:** §2.2, §3.3, §4, §8.
- **Freeze:** before-release-gate additive contracts where applicable; provisional runtime/plugin changes; ADR 0007.
- **Shapes/edges:** none; existing conversion behavior retained.
- **Decision:** Use the shared contracts and limits above and ADR 0007; no new dependency or provider knob.
- **Open:** none within this scope.

## WU-29 — Qualify client request decoding

- **Status:** ✅ Complete
- **Workstream:** Conversion.
- **Scope:** Audit OpenAI Chat Completions request decoding against the matrix below; record unsupported multi-choice/provider references and unknown fields with edge contracts and golden examples. Owns ocai-openai/chat_completions/, spec/fixtures/, spec/extensions/, plugin tests. Other WU outcomes are out of scope.
- **Done:** Supported tools and structured-output requests survive client-to-canonical-to-provider fixtures; unknown data is preserved and unsupported semantics are reported.
- **Deps:** 28.
- **Architecture:** §4.2, §7, §10.
- **Freeze:** before-release-gate additive contracts where applicable; provisional runtime/plugin changes; ADR 0007.
- **Shapes/edges:** existing chat request edge census/fixtures.
- **Decision:** Use the shared contracts and limits above and ADR 0007; no new dependency or provider knob.
- **Open:** none within this scope.

## WU-30 — Encode canonical client responses

- **Status:** ✅ Complete
- **Workstream:** Conversion.
- **Scope:** Register canonical response to OpenAI Chat Completions response edge with a complete contract and golden fixtures. Owns ocai-openai/chat_completions/, spec/fixtures/, plugin tests. Other WU outcomes are out of scope.
- **Done:** Text/tools/refusal, tool identity, finish and known usage map to the client wire contract with explicit findings for unsupported content/references.
- **Deps:** 29.
- **Architecture:** §4.2, §7, §10.
- **Freeze:** before-release-gate additive contracts where applicable; provisional runtime/plugin changes; ADR 0007.
- **Shapes/edges:** new canonical-to-client chat.response edge and golden fixtures.
- **Decision:** Use the shared contracts and limits above and ADR 0007; no new dependency or provider knob.
- **Open:** none within this scope.

## WU-31 — Encode canonical client stream events

- **Status:** ✅ Complete
- **Workstream:** Conversion.
- **Scope:** Register canonical chunk to OpenAI Chat Completions chunk transducer; gateway supplies SSE framing, plugin supplies semantic event mapping. Owns ocai-openai/chat_completions/, spec/fixtures/, plugin tests. Other WU outcomes are out of scope.
- **Done:** Fold triples prove unary/stream equivalence for supported text/tools/finish/usage; aborts never produce successful terminal output.
- **Deps:** 30.
- **Architecture:** §3.1, §4.1–4.2, §7, §10.
- **Freeze:** before-release-gate additive contracts where applicable; provisional runtime/plugin changes; ADR 0007.
- **Shapes/edges:** new canonical-to-client chat.chunk edge and fold triples.
- **Decision:** Use the shared contracts and limits above and ADR 0007; no new dependency or provider knob.
- **Open:** none within this scope.

## WU-32 — Prove governed gateway paths

- **Status:** ⬜ Planned
- **Workstream:** Qualification.
- **Scope:** Exercise public APIs over recorded OpenAI and Anthropic HTTP/SSE pairs through all conversion legs, admission, policy, closure and observations; publish a gateway integration example. Owns tests/, examples/, docs/gateway-integration.md. Other WU outcomes are out of scope.
- **Done:** The combined gateway completion target passes for unary and streaming with separate per-leg reports, zero credential exposure and no private-method dependencies.
- **Deps:** 26, 28, 31.
- **Architecture:** §3–8, §10.
- **Freeze:** before-release-gate additive contracts where applicable; provisional runtime/plugin changes; ADR 0007.
- **Shapes/edges:** none; existing conversion behavior retained.
- **Decision:** Use the shared contracts and limits above and ADR 0007; no new dependency or provider knob.
- **Open:** none within this scope.

