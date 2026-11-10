---
icon: lucide/rocket
---

# ocai

**One Common interface for AI** — a single, stable, provider-neutral API in
front of every AI capability (LLM chat, embeddings, vector stores,
monitoring) so your code never imports a provider SDK.

!!! note "Status: M1–M3 implemented; modernization underway"

    Python provides unary and streaming chat through OpenAI Chat Completions
    and Anthropic Messages, conversion graphs, and fidelity reports. The active
    canonical revision is `2026-07`. Responses is a stub; Gemini is not yet
    implemented. See the [feature matrix](provider-feature-matrix.md) and
    [modernization plan](plans/core-modernization.md).

The differentiator is **honest, version-resilient conversion**: switching
provider, provider *interface* (OpenAI `/chat/completions` → `/responses`),
or provider *version* is ocai's problem, not yours — and every conversion
reports exactly what it cost (`FidelityReport`), never silently.

## The five load-bearing ideas

=== "Contract kernel"

    `ocai.core` is a pure-stdlib, zero-dependency, zero-I/O data-contract
    layer: identity, fidelity, errors, `CallResult`, credentials,
    `ProviderRef`, the IR envelope, canonical JSON. Everything else is
    replaceable machinery behind it.

=== "Four-level identity"

    `Capability` → *interface* → dated `tag` → `Shape`. A graph node is
    `NodeId(provider, interface, tag, shape)`. Sibling interfaces are
    concurrent, not versions of each other — and the canonical IR is itself
    the interface named `ocai`, so IR migration is ordinary graph conversion.

=== "Governed catalog"

    Immutable, provenance-stamped `Catalog`s composed from plugin
    `CatalogFragment`s — no process-global registries. Every edge declares an
    `EdgeContract` (per-field disposition census); planner weights are
    *derived* from it, and conformance certifies runtime loss never exceeds
    the declaration.

=== "Sans-io execution"

    All logic that is not the physical I/O call is pure and synchronous; two
    thin drivers execute it. Policy hooks return Decisions
    (`Proceed | Retry | Fail | Return`); credentials are applied at the
    driver leaf, after every hook — no middleware can see a secret.

=== "Stream-first IR"

    `fold(stream(request)) == complete(request)` is normative law. Streams
    end with `StreamEnd(usage, finish, report)`; no new part type ships
    without its delta type, fold law, and paired fixtures.

Every boundary crossing pays its toll in a `FidelityReport` — visibly:

``` mermaid
graph LR
  CC[openai/chat_completions] --> IR[ocai-2026-07]
  R[openai/responses: planned] -.-> IR
  A[anthropic/messages] --> IR
  IR --> CC
  IR -.-> R
  IR --> A
```

## Install

The core distribution is `ocai`; each provider plugin is a separate
distribution merging into the same PEP 420 namespace.

``` bash
uv add ocai            # core only
uv add "ocai[openai]"  # core + the OpenAI plugin
```

## Where to next

- [Architecture](architecture.md) — **the structural contract**: every layer,
  object, and interaction. When code and this document disagree, one gets
  fixed in the same PR.
- [Writing a plugin](writing-a-plugin.md) — the community-plugin guide, with
  the `ocai-contrib-echo` template.
- [Roadmap](plans/README.md) — milestones and work units.
- `spec/` in the repository — the language-neutral truth every port
  implements, starting with `spec/canonical-json.md`.

## Local docs workflow

These docs are built with [Zensical](https://zensical.org). It lives in the
`docs` dependency group, so run it through uv:

``` bash
uv run --group docs zensical serve   # live preview at http://127.0.0.1:8000
uv run --group docs zensical build   # render the static site into ./site
```

!!! info "Source-available, not open source"

    ocai ships under the Functional Source License (FSL-1.1-ALv2). Please
    don't describe it as "open source".
