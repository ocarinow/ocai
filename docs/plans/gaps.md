# Kernel gaps

Things the kernel lacks, discovered by building *on* it — a satellite, a
spike, a port, a review. Each entry is evidence, not opinion: what was being
built, what was needed, what exists today, and the smallest kernel change that
would close it. Entries graduate into WUs in the milestone files; the WU link
goes in the last column when that happens.

Rules for an entry:

- Written by the agent that hit the gap, in the same PR as the work that
  exposed it (a gap noted a week later loses its evidence).
- Names the architecture section or rule the gap lives under.
- Never edits kernel source to work around it silently — the workaround, if
  any, is named here so the WU can remove it.

| # | Date | Found while | Gap | Today | Proposed change | WU |
|---|---|---|---|---|---|---|
| G-01 | 2026-11-10 | Planning the agent runtime and satellites | Request-side continuation anchors (`previous_response_id` on the way *in*) have no canonical home | `ProviderRef` exists for response ids on the way out; `ChatRequest` carries no anchors | `ChatRequest.anchors: list[ProviderRef] \| None`, additive, with the UNSUPPORTED-on-crossing obligation (architecture §2.4; horizon H1) | H1 |
| G-02 | 2026-11-10 | Planning audit and eval satellites | No normative recorded-pair format in `spec/` for HTTP/SSE request+response archives | Test fixtures under `python/packages/*/tests/http/` are the de facto format, Python-only | Promote the recorded-pair shape to `spec/` with a schema, so archive and eval satellites and every language port share it (architecture §6 `HttpRequest/HttpResponse` is "the audit-archive contract shape") | — |
| G-03 | 2026-11-10 | Planning the agent runtime | No fixture class proving a full multi-turn transcript (tool calls, reasoning signatures, server-tool payloads) round-trips through encode → decode → canonical JSON unchanged | Per-edge fixtures and unknown vectors exist; nothing exercises a whole transcript | A `transcript` fixture kind in `spec/fixtures/canonical/` plus a conformance check | — |
| G-04 | 2026-11-10 | Planning the telemetry satellite (rescoped by the observability survey) | `Observer` events lack stream-level events (no StreamEnd / time-to-first-chunk event), an inbound trace-context slot on `CallContext` (`traceparent`), and a documented `call_id` format | `call_id` and `attempt` already exist on `CallStarted`/`WireExchanged`/`CallFinished`; `WireExchanged` has no emission site on `main` | Add stream events and the trace-context slot before the first satellite; document `call_id`; freeze at v1.0 per §9. See `docs/capabilities/observability.md` | — |
| G-05 | 2026-11-10 | Planning tool/MCP registries | No decision on whether an MCP client is a §11 capability (it has a versioned wire protocol) or a satellite concern | `PartServerToolCall(kind="mcp_call")` covers provider-executed MCP; client-side execution is undefined | ADR in the freeze review | — |
| G-06 | 2026-11-10 | Strict-typing pass (ADR 0002) | `decode_frame` in `ocai.anthropic.messages.codec` assumes an SSE `data:` payload is a JSON object; a valid JSON array or scalar would raise `AttributeError` | Anthropic never emits such frames, so untested | Guard with `is_json_object` and route a non-object frame to `DeltaUnknown`/extensions (rule 6); add an unknown vector | — |
| G-07 | 2026-11-10 | Strict-typing pass (ADR 0002) | Tolerant readers iterate `data.get("parts") or []` directly: a *string* value becomes one `PartText` per character and a non-iterable raises `TypeError` | `Message.from_dict` and sibling list fields in `ocai.chat.types` | Iterate through `is_json_array` (empty on non-array) and sweep the offending value into `extensions`; add unknown vectors for a string and an int in a list slot | — |
| G-08 | 2026-11-10 | Strict-typing pass (ADR 0002) | `Message(parts=(p1, p2))` with a tuple is stored as `[(p1, p2)]` by the constructor sugar | The typed overloads deliberately admit only `str | Part | list[...]`, so the type is honest; the runtime is not | Either normalize any non-string sequence in `__post_init__` or reject it; same for `EmbeddingRequest` | — |
