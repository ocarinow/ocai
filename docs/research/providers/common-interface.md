# Designing a Common Provider Interface

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

How a single, stable interface should sit in front of OpenAI, Gemini, Anthropic, and
Mistral — grounded in what those APIs actually expose (see the per-provider docs and
[feature-matrix.md](feature-matrix.md)) and mapped onto `ocai`'s existing
architecture (`spec/schema/*.json`, `ocai.core.types`, `ocai.core.ports`,
`ocai.core.middleware`, `ocai.core.graph`).

This is a design document, not a re-implementation. `ocai` already commits to the right
shape — ports & adapters, a canonical IR, middleware, and a loss-weighted conversion
graph. The goal here is to record **what the four providers demand of that shape** and
where the current IR needs to grow.

## 1. The core problem the interface solves

The four request bodies share ~80% of one idea — *an ordered list of role-tagged
messages, plus sampling knobs, plus tool declarations* — and diverge in two ways:

1. **Cosmetic naming.** `assistant` vs `model`; `max_tokens` vs `maxOutputTokens`;
   `random_seed` vs `seed`. Pure renames — near-zero information loss.
2. **Structural / semantic divergence.** Where the system prompt lives (a role, a
   top-level field, or a separate `systemInstruction`); whether a tool result is its own
   role or a content block inside a user turn; flat content vs `parts[]`/blocks/chunks;
   reasoning as effort-enum vs token-budget; caching as automatic vs breakpoint-explicit;
   server-side built-in tools that have no analogue elsewhere.

A good common interface makes category (1) **invisible** and category (2) **explicit and
measurable** — never silently dropped. That is exactly the contract of `ocai`'s
conversion graph: every conversion returns `(output, Report)`, and edge weight encodes
information loss.

## 2. Design principles

1. **Neutral core, no SDK leakage.** The interface (the `ChatModel` port) speaks only
   the canonical IR. Nothing a caller touches imports a provider SDK. (Already enforced:
   `ocai.core` imports no provider.)
2. **Intersection is typed; union is carried.** Fields all four providers agree on get
   first-class IR fields. Everything else rides in two open bags so it is never lost:
   - **`provider_options`** — provider-specific *request* knobs with no canonical home
     yet (sampling penalties, `safe_prompt`, `reasoning_effort`).
   - **`extensions`** — forward-compatible additive data on any object (per the schema:
     "always present, may be empty; unknown keys preserved, never rejected").
   - **`ChatResponse.raw`** — the verbatim provider payload, the ultimate lossless escape.
3. **Open/tolerant schemas.** Readers must tolerate unknown roles and unknown keys
   (already the spec's stance: `additionalProperties: true`, open role enum). This is
   what lets a new provider or model land without a breaking change.
4. **Loss is data, not an exception.** Converting between two provider formats is a
   shortest-path search where weight = fidelity loss, and the canonical IR is a backbone
   node so any pair is reachable in ≤2 hops. Direct provider→provider edges are
   higher-fidelity shortcuts the path-finder prefers (e.g. OpenAI↔Mistral, which share
   the Chat-Completions shape).
5. **Three version axes stay separate** (already in the design): provider **wire**
   version (a graph node `Ref`), canonical **IR** version (`ir_version`), library
   **API** version (semver).
6. **Capabilities are introspectable.** `ChatModel.capabilities()` lets callers and
   middleware ask what a model supports (tools, streaming, vision, thinking, caching)
   rather than discovering by 400. Mirror each provider's `GET /models` capability data.

## 3. The neutral surface (ports)

`ocai` already defines the right ports in `ocai.core.ports`. The chat interface is:

```python
class ChatModel(Protocol):
    async def chat(self, request: ChatRequest) -> ChatResponse: ...
    def stream(self, request: ChatRequest) -> AsyncIterator[ChatResponse]: ...
    def capabilities(self) -> dict[str, Any]: ...
```

Sibling ports keep non-chat capabilities out of `ChatModel` (the matrix's "out of
scope" row): `EmbeddingModel` (OpenAI/Gemini/Mistral embeddings), `VectorStore` (RAG),
`Tracer` (monitoring). OCR, image/audio generation, and realtime bidi voice are future
ports — deliberately not forced into chat.

## 4. The canonical IR — current core and where it must grow

The current IR (`ocai.core.types`, mirrored by `spec/schema`) is intentionally minimal:

```
ChatRequest(model, messages, tools?, provider_options, extensions, ir_version)
Message(role, content: str|None, tool_calls?, extensions)
ToolCall(id, name, arguments: dict, extensions)
ChatResponse(message, usage?, raw?, extensions, ir_version)
Usage(prompt_tokens, completion_tokens, total_tokens)
```

This cleanly covers the **intersection** of all four providers. Measured against the
matrix, the following are the concrete gaps — each is a candidate to promote from an
escape hatch into a typed field as the IR version advances:

| Need | All four? | Recommendation |
|---|---|---|
| System instruction | ✅ (as role / top-level / `systemInstruction`) | Keep as a `system`-role `Message`; each adapter relocates it (role→`system` field for Anthropic, →`systemInstruction` for Gemini, →`instructions` for OpenAI Responses). **Document this as a structural edge**, not loss. |
| Sampling: temperature, top_p, max output, stop, seed | ✅ (naming varies) | **Promote to typed optional fields** on `ChatRequest` (e.g. `max_output_tokens`, `temperature`, `top_p`, `stop`). Low loss, universal. Note Anthropic 4.7+ rejects sampling params — the adapter drops them and records loss. |
| `tool_calls.arguments` as object | ✅ | Already an object in the IR (`dict`). Adapters must `json.loads` OpenAI/Mistral string `arguments` on the way in and re-serialize on the way out. |
| Tool *definitions* | ✅ (opaque `dict` today) | Consider a typed `ToolDef(name, description, parameters)` so adapters stop passing through provider-shaped dicts. Currently `tools: list[dict]` — acceptable but lossy to validate. |
| Multimodal content (image/audio/video/document) | ⚠️ (Anthropic no audio/video; Gemini all) | The biggest gap: IR `content` is `str|None`. Add a **typed content-part union** (`text`, `image`, `document`, `audio`…) as a future IR core, or keep parts in `extensions` short-term. This is where the most loss hides. |
| Reasoning controls + output | ⚠️ (effort vs budget) | Normalize to a neutral `reasoning: {effort: "low".."max"}` in `provider_options`; map effort↔budget per adapter. Reasoning *summaries* land in response `extensions`. |
| Token usage extras (cache/reasoning tokens) | ⚠️ | Grow `Usage` with optional `cache_read_tokens`, `cache_write_tokens`, `reasoning_tokens`, or stash in `Usage`/response `extensions`. |
| `stop_reason` / `finish_reason` | ✅ (every provider has one) | **Promote to a typed `ChatResponse.stop_reason`** with a neutral enum (`end_turn`, `max_tokens`, `tool_use`, `stop_sequence`, `refusal`, `safety`, `content_filter`). Anthropic's `refusal` and Gemini's `SAFETY` matter to callers. |

Everything else (prompt caching directives, server-side tools, statefulness, Mistral
`prefix`, Gemini grounding/safety, OpenAI `previous_response_id`/`background`) stays in
`provider_options` / `extensions` and is best served by **direct high-fidelity edges**
between same-family providers rather than round-tripping through canonical.

## 5. The conversion graph — fidelity routing

`ocai.core.graph` is the mechanism that keeps category-(2) divergence honest. Nodes are
`(provider, wire_version)`; the canonical IR (`CANONICAL = ("ocai", IR_VERSION)`) is the
backbone every format connects to. Implications from this research:

- **Backbone edges** (provider ↔ canonical) must exist for all four. They are the
  ≤2-hop guarantee. Each carries the structural cost of relocating the system prompt,
  flattening parts/blocks, and normalizing tool-result threading.
- **Direct shortcut edges** are worth building where loss is genuinely low:
  - **OpenAI ↔ Mistral** — both Chat-Completions-shaped; near-lossless for text + tools.
  - OpenAI Chat Completions ↔ OpenAI Responses — same provider, different wire shape.
- **High-loss edges** should *say so* in their weight: anything that drops a server-side
  tool, a multimodal part, reasoning state, or a cache directive. The `Report` then tells
  the caller exactly what degraded and which path was taken (`Report.path`,
  `Report.total_loss`, per-edge `LossEntry.note`).
- **Conformance fixtures** (`spec/fixtures/`) are the drift alarm: each provider format
  round-trips through canonical and is checked against golden output, so a provider API
  change surfaces in CI.

## 6. Cross-cutting concerns belong in middleware, not adapters

`ocai.core.middleware` already establishes that retry, cache, rate-limit, tracing, and
fallback are `ChatModel`-wrapping middleware that compose. This research reinforces *why*
that split matters:

- **Fallback** middleware is a natural home for Anthropic's `stop_reason:"refusal"` →
  retry-on-another-model pattern, generalized across providers.
- **Cache** middleware can implement a neutral caching policy on top of providers whose
  native caching differs wildly (automatic OpenAI/Gemini vs breakpoint Anthropic vs none
  Mistral) — or defer to native caching via `provider_options`.
- **Rate-limit / retry** must read each provider's distinct signals (`retry-after`,
  `x-ratelimit-*`, 429-means-two-things on OpenAI). Keeping this in middleware means
  adapters stay thin translators.

## 7. Worked example — one request, four wires

A caller builds one neutral request:

```python
req = ChatRequest(
    model="…",                       # provider model id, passed through verbatim
    messages=[
        Message(role="system", content="You are concise."),
        Message(role="user", content="Summarize this PDF."),
    ],
    tools=[…],
    provider_options={"temperature": 0.2, "reasoning": {"effort": "high"}},
)
```

Each adapter renders it differently, and the differences are exactly category (2):

- **OpenAI (Responses)**: `system` → `instructions`; messages → `input`; `temperature`
  passed; `reasoning:{effort:"high"}`. Chat Completions instead keeps a `system` message
  and uses `response_format`/`max_tokens`.
- **Gemini**: `system` → `systemInstruction`; user msg → `contents[].parts[]`;
  `assistant`→`model` on the way back; `temperature` → `generationConfig.temperature`;
  effort → `thinkingConfig` (budget/level).
- **Anthropic**: `system` → top-level `system` field; `temperature` **dropped on 4.7+**
  (recorded as loss) and replaced by `output_config.effort:"high"`; thinking adaptive.
- **Mistral**: nearly 1:1 — `system` role kept, `temperature` passed, effort →
  `reasoning_effort`.

Each returns a provider payload the adapter normalizes back to `ChatResponse` (typed
`message` + `usage` + `stop_reason`, full payload in `raw`), and the conversion `Report`
records what each translation cost.

## 8. Summary checklist for the IR

- [x] Neutral ports, no SDK leakage — **done** (`ocai.core.ports`).
- [x] Open/tolerant schemas with `extensions` + `provider_options` + `raw` — **done**.
- [x] Loss-weighted conversion graph with canonical backbone — **done** (`ocai.core.graph`).
- [x] Composable middleware for retry/cache/rate-limit/trace/fallback — **done**.
- [ ] Promote universal sampling/limit knobs (`max_output_tokens`, `temperature`,
      `top_p`, `stop`) to typed `ChatRequest` fields.
- [ ] Add a typed `stop_reason` to `ChatResponse` (incl. `refusal` / `safety`).
- [ ] Design a typed multimodal content-part union (image/audio/video/document) — the
      largest current fidelity gap.
- [ ] Grow `Usage` with cache/reasoning token fields.
- [ ] Consider a typed `ToolDef`; normalize a neutral `reasoning.effort`.
- [ ] Build direct high-fidelity edges (OpenAI↔Mistral, OpenAI CC↔Responses) alongside
      the canonical backbone edges.
