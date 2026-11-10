# Provider feature matrix

Baseline inspected November 10, 2026. **R** means represented by current
canonical types, **C** means a converter exists, and **E** means exercised by
the runtime over fixtures. Representation alone does not establish provider
support. The active canonical revision is `2026-07`.

| Feature | Current representation | Chat Completions | Anthropic Messages | Responses / Gemini Interactions | Next proof |
|---|---|---|---|---|---|
| Chat and function tools | Messages, calls/results | R/C/E | R/C/E | Responses stub; no Gemini adapter | Preserve existing behavior |
| Ordered messages/actions | One message with mixed parts | Single-message contract | Mixed content blocks | New contract needed | Boundaries, phases, IDs, grouping |
| Reasoning | Text, summary, signature/opaque refs | Partial mapping | Thinking/signature mapping | Not implemented | Replay metadata/state |
| Caching | CacheConfig(mode, ref), CacheHint(ttl), usage | No complete typed mapping | Request cache dropped; usage decoded | Not implemented | Interface/model controls |
| Hosted tools / MCP | Opaque server-tool payload | No complete surface | Some blocks decoded | Not implemented | Declaration, approval/resume |
| Citations | Annotations and answer spans | Preserved in extensions | Streaming citation deltas dropped | Not implemented | Validated answer/evidence locations |
| Search results | Server-tool payload | No shared hit structure | Provider payload retained | Not implemented | Evidence identity, ranking provenance |
| Binary/media | Base64, URL, provider ref | Partial/preserved extensions | Several encode paths dropped | Not implemented | Generic artifacts, byte-preserving streams |
| Continuation | ProviderRef and response IDs | No typed request continuation | Explicit history | Not implemented | Replay or scoped continuation |
| Background work | No job port | Not implemented | Not implemented | Not implemented | Submit/retrieve/cancel |
| Native decisions | No capability | Not implemented | Not implemented | Decisions adapter absent | Questions/answers shapes |

`DeltaBlob` is declared but not accumulated. Call interceptors wrap unary calls
only. Observer types exist but are not emitted. Keep these gaps visible until
implementation tests exercise them.

## Provider references for the next design

These references establish requirements, not ocai support. Recheck relevant pages
when implementing an adapter and record provenance on its fixtures.

- [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state): replay and continuation.
- [Reasoning](https://developers.openai.com/api/docs/guides/reasoning): ordered items and assistant phase.
- [MCP tools](https://developers.openai.com/api/docs/guides/tools-connectors-mcp): declarations and approvals.
- [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching): model/interface controls; retention is not a deletion deadline.
- [Background mode](https://developers.openai.com/api/docs/guides/background): persistent work differs from an async function.
- [Decisions](https://developers.openai.com/api/docs/guides/decisions): typed questions/answers and JSON evidence.
- [Gemini Interactions](https://ai.google.dev/gemini-api/docs/interactions-overview): steps, state, background work.
- [Gemini caching](https://ai.google.dev/gemini-api/docs/caching): interface-specific support.
- [Anthropic caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching): request/block control.

WU-19 will add ordered-item fixtures under `spec/proposals/ordered-items/`.
They must carry provenance; synthetic design examples are not live captures. Existing Messages examples
are also labelled synthetic. Canonical schema validation cannot establish that
a provider accepts a payload or that a converter preserves its semantics.
