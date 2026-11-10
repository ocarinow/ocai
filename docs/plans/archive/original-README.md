# ocai roadmap — v0.1 → v1.0 → expansion

> **⚠️ July 2026 re-architecture landed.**
> [`docs/architecture.md`](../../architecture.md) is now the **structural
> contract** for every layer, object, and interaction — read it before any
> milestone file in this directory. The WU numbering and module references
> below **predate the re-architecture and are being remapped** onto the new
> layout (`ocai.core` / `ocai.chat` / `ocai.convert` / `ocai.runtime` /
> `ocai.wire`, one plugin subpackage per interface). Where a milestone file
> contradicts `architecture.md`, the architecture wins. Do **not** rewrite
> the milestone files ahead of the remapping — they are kept verbatim as the
> planning record.

A milestone plan optimized for driving Claude Code. Each **work unit (WU)** is
sized to be one focused session / one small PR, with explicit done-criteria and
dependencies so instances can run in parallel where the graph allows.

The shared rules every session inherits live in the root
[`CLAUDE.md`](https://github.com/ocarinow/ocai/blob/main/CLAUDE.md). This directory holds the milestone breakdown.

## Milestones

### Core track — prove the moat (v0.1 → v1.0)

| Milestone | Theme | Provider added | File |
|---|---|---|---|
| **v0.1** | Walking skeleton (internal) | OpenAI | [v0.1-walking-skeleton.md](v0.1-walking-skeleton.md) |
| **v0.2** | The wedge, made visible (first public release) | Anthropic | [v0.2-the-wedge.md](v0.2-the-wedge.md) |
| **v0.3** | Credibility & version-resilience proof | Gemini | [v0.3-credibility.md](v0.3-credibility.md) |
| **v0.4** | Polyglot parity (TypeScript, Go optional) | — | [v0.4-polyglot.md](v0.4-polyglot.md) |
| **v1.0** | Promise-keeping & hardening | — | [v1.0-hardening.md](v1.0-hardening.md) |

### Expansion track — breadth across GenAI (post-v1.0, additive only)

Only after the conversion/fidelity moat is proven on chat. Each milestone adds
**new ports / middleware** to the v1.0-frozen `ocai.core` surface — never a
rename or removal — so the track doubles as the proof that "extensible" is real.
Every new modality is held to the same fidelity-`Report` and recorded-fixture bar
as the original three providers.

| Milestone | Theme | What it adds | File |
|---|---|---|---|
| **v1.1** | Honest economics | `TokenCounter`, cost-in-currency, batch + `Operation`, `ModelRegistry` | [v1.1-honest-economics.md](v1.1-honest-economics.md) |
| **v1.2** | Retrieval, completed | `Reranker`, `Files` lifecycle, real `VectorStore`, scope ADR | [v1.2-retrieval-complete.md](v1.2-retrieval-complete.md) |
| **v1.3** | Generative media | multimodal content parts, `ImageModel`, `SpeechModel`, `TranscriptionModel` | [v1.3-generative-media.md](v1.3-generative-media.md) |
| **v1.4** | Realtime & duplex | `DuplexTransport` (WebSocket), `RealtimeSession`, canonical realtime events | [v1.4-realtime-duplex.md](v1.4-realtime-duplex.md) |
| **v1.5** | Safety & evaluation | `Moderation`, guardrails middleware, `Evaluator`, feedback capture | [v1.5-safety-and-eval.md](v1.5-safety-and-eval.md) |

**Why this order:** economics first (it's pure leverage on the existing
differentiator — "report what it cost" in dollars, no new modality, lowest
risk); retrieval next (completes a pillar that's already half-built); then the
generative-media modalities; realtime last among additive work because it's the
only one that stresses an architectural assumption (the one-way `Transport`);
safety/eval closes the monitoring loop. Video gen, OCR-as-a-port, fine-tuning,
and a fourth provider stay out until there's a concrete pull.

## Assumptions (adjust freely)

- First two providers: **OpenAI** then **Anthropic** (the canonical conversion
  pair). Third: **Gemini** (different enough to stress-test the abstraction).
- Polyglot order: **Python → TypeScript → Go**.

## Sequencing principle

Never build the wedge on top of shaky table stakes. Streaming, errors, and the
conversion fidelity report must be solid on the providers they span *before*
adding breadth. The conformance fixture set grows from day one — it is the moat,
not an afterthought. Three providers is plenty until v1.

## Flagship WUs (these *are* the product)

- **WU 2.4** — the visible, honest fidelity report (`convert` / `retarget`).
- **WU 3.5** — the version-bump-with-no-user-code-change proof.

Everything else is in service of those two demos. Do them carefully.

## Current scaffold state (what already exists)

The architecture is wired; treat the items below as **starting points to finish
and harden**, not greenfield. Don't redo them — extend them.

- ✅ Canonical IR dataclasses + `Report.merge()` — [types.py](../python/packages/ocai-core/src/ocai/core/types.py) (WU 1.1 mostly done; `ToolCall` exists as a stub, no sampling/`stop_reason` fields yet).
- ✅ Ports — [ports.py](../python/packages/ocai-core/src/ocai/core/ports.py) (`ChatModel`, `EmbeddingModel`, `VectorStore`, `Tracer`).
- ✅ Conversion graph (Dijkstra, loss-weighted, path cache, canonical backbone) — [graph.py](../python/packages/ocai-core/src/ocai/core/graph.py) (WU 2.2 largely done).
- ✅ Middleware base + `RetryMiddleware` — [middleware.py](../python/packages/ocai-core/src/ocai/core/middleware.py) (WU 1.5 partial: no usage/cost accounting yet; retry lacks jitter/Retry-After).
- ✅ Plugin discovery via entry points — [plugins.py](../python/packages/ocai-core/src/ocai/core/plugins.py).
- ✅ OpenAI adapter + codec **stub** (no network I/O, canned response) — [adapter.py](../python/packages/ocai-openai/src/ocai/openai/adapter.py) (WU 1.2 / 2.3 OpenAI side partial).
- ✅ Spec: JSON Schema + one golden fixture + conformance test — [spec/](https://github.com/ocarinow/ocai/blob/main/spec/README.md).
- ✅ Path-filtered CI (python active; ts/go stubbed).
- ❌ Missing: real HTTP I/O, streaming/`ChatChunk`, error taxonomy, recorded-fixture harness, Anthropic/Gemini, capabilities, embeddings/vector store, polyglot.

## How to brief each session

Give the instance: (1) the root `CLAUDE.md` rules, (2) the single WU's scope +
done-criteria from its milestone file, (3) the relevant `spec/` files, and (4)
an instruction to verify against recorded fixtures and report results before
finishing. **One WU per PR.**

### Suggested first three sessions

1. **WU 1.1** — finalize canonical types + `Report`. Solo first; it blocks v0.1.
   (Mostly scaffolded — finish `ToolCall`, confirm `Report.merge`, lock the API.)
2. **WU 1.6** — recorded-fixture test harness (respx/VCR). In parallel; makes
   every later WU verifiable without live keys.
3. Then fan out: WU 1.2 / 1.4 / 1.5 in parallel; WU 1.3 (streaming) after 1.2.
