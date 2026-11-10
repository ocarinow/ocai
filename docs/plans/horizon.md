# Horizon milestones

**Historical ordering.** The [core modernization plan](core-modernization.md)
now determines execution order; the release gate is defined by
[ADR 0005](../decisions/0005-revised-freeze-gate.md). The descriptions below
retain the July scope for reference. The `/responses` proof (H1) remains
required for the freeze but no longer qualifies it alone, and TypeScript/Go
implementation is deferred.

One paragraph each, detailed into WUs only when reached (the roadmap's
anti-staleness rule: no pretend-detail a year out). Order is intent, not law.

## H1 — `/responses` interface + the migration proof (required for the freeze gate)

Implement `ocai.openai.responses` for real: msgspec wire structs, codec (the
merged `PartReasoning` shape carrying summary + encrypted_content in one part;
`previous_response_id` as a `ProviderRef` anchor; item-id identity), full
certification bar (fixtures, fold triples, census). Precondition inside this
milestone: settle the interface-preference resolution policy flagged at
`catalog.py:556`. H1 must also settle the request-side continuation-anchor
shape **before its fixtures multiply** (recommended:
`ChatRequest.anchors: list[ProviderRef] | None`, additive, carrying the
UNSUPPORTED-on-crossing edge obligation of every `ProviderRef`) — the home
for `previous_response_id` on the way *in*, not just the response id on the
way out. The proof itself — the wedge feature: identical user code,
catalog resolution flips `openai/chat_completions → openai/responses`,
`Route.reason` shows the decision, and the `FidelityReport` shows exactly what
the migration cost. Per architecture §9 and ADR 0005 this is one item of the freeze
qualification; the data-contract freeze cuts after the whole qualification
is met, not after H1 alone.

## H2 — Gemini (`ocai-gemini`)

The IR stress test: `systemInstruction` relocation as a declared shift,
`thoughtSignature` as a `replay=REQUIRED` anchor weighted as breakage in
planning, grounding citations re-anchored only when spans validate (else
censused extension), `promptFeedback` pre-generation block →
`ContentFilterError` (the §3.1 boundary rule), and the Vertex host path
exercising `hosting.Vertex` + `DialectTraits` as data. Same bar: fixtures,
fold triples, certification, recorded pairs. By now this should be a
mechanical replay of WU-06/07/10/14 — that being true is itself the claim
under test.

## H3 — Embedding / vectorstore promotion

Graduate the provisional ports by carrying `CallResult` in anger: one remote
embedding interface (OpenAI embeddings — a new capability shape through the
same catalog/driver machinery, proving the harness is capability-neutral) and
one local in-process vectorstore adapter implementing the port directly with
`route.host = "in-process"` — the port-plane peer proof that interceptors
compose identically over local and remote. Exit: `ocai.embedding` /
`ocai.vectorstore` leave provisional status (§9).

## H4 — Enterprise satellites + hardening (v1.0 gate)

`RateLimitPolicy` (token bucket + provider rate-header parsing), `WireTap`
feeding a content-addressed archive satellite, port-tier interceptors
exercised for real — including **one real cross-provider failover** (the
second v1.0 freeze qualification per §9), observer events exercised then
frozen, and a canonical-revision bump rehearsal (`ocai@2026-07 → next`) via
`migrate.py` through ordinary certified edges. Dual adapters and `CallContext`
governance paths under load-shaped tests.

## H5 — Polyglot

The TypeScript port starts from `spec/canonical-json.md` (implement
`canonical`/`semantic_equal` first) and must pass the **identical**
`spec/fixtures/` suite: unknown-X vectors, edge fixtures, fold triples. That
is the moat's portability proof and the reason WU-02/03/05/08 invest so
heavily in fixture vocabulary. CI's typescript job goes from stub to real; Go
follows the same recipe when pulled.

## H6 — Capability breadth: rerank, files, jobs

Three additions by the architecture §11 recipe, none touching a frozen
surface. **Rerank**: provider rerank APIs (Cohere, Voyage, hosted
open-weights) become a real capability — identity as data, `ocai.rerank` IR
importing core only, a port returning `CallResult[RerankResult]`, canonical
nodes, provider fragments; the first multi-provider capability added after
the freeze, so it is the recipe's proof. **Files**: a small CRUD capability
whose artifacts are cross-capability `ProviderRef`s — upload once, and the
provider-scoped handle rides chat, embedding, or batch requests under the
scoped crossing rule. **`ocai.jobs`**: the capability-neutral
submit/poll/fetch helper at the runtime tier — `Job`/`JobHandle` vocabulary
(never `Operation`), each leg its own `Operation` returning its own
`CallResult` and `Route`, anchored by `ProviderRef(kind="job")`; batch APIs
and long-running generations compose over it in facades.

## H7 — Eval & safety substrate

Moderation endpoints become a capability (they have provider-varying wire
dialects — the §11 scope litmus test admits them); eval tooling is built ON
ocai as a satellite leveraging the ledger: a `Route` + catalog lock hash +
`FidelityReport` make every eval run reproducible and attributable, so a
regression is attributable to the prompt, the provider revision, or the
conversion — not smeared across all three. The kernel contributes substrate
(pure-data IR, canonical JSON, `CallContext`, the ledger), never the eval
feature itself.
