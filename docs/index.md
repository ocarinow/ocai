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
    canonical revision is `2026-07`. WU-17–20 are merged: the
    [modernization plan](plans/core-modernization.md), the independently
    installed conversion plugin, the ordered-item proposal (under
    `spec/proposals/`), and catalog-composition hardening. Responses is a
    stub; Gemini is not yet implemented; TypeScript and Go ports are deferred.
    See the [feature matrix](provider-feature-matrix.md).

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

The site is organised as tabs, one per information space:

- [Libraries](libraries/README.md) — the public implementations:
  [Python](libraries/python/README.md) (implemented), TypeScript and Go
  (deferred), and the [plugin author guide](writing-a-plugin.md).
- [Platform](platform/README.md) — the enterprise platform modules built on
  the kernel (gateway, telemetry, audit, eval, registries, agent runtime),
  each with its own status.
- [Spec](spec/README.md) — the language-neutral truth every port
  implements, plus the [provider wire research](providers/README.md) and the
  shipped [feature matrix](provider-feature-matrix.md).
- [Architecture](architecture.md) — **the structural contract**: every
  layer, object, and interaction. When code and this document disagree, one
  gets fixed in the same PR.
- [Roadmap](plans/README.md) — milestones, work units, and the core
  modernization program.
- [Decisions](decisions/README.md) — the ADRs: why each contract shape was
  chosen over the alternatives.

## Local docs workflow

These docs are built with [Zensical](https://zensical.org). It lives in the
`docs` dependency group, so run it through uv:

``` bash
uv run --group docs zensical serve           # live preview at http://127.0.0.1:8000
uv run --group docs zensical build --clean   # render the static site into ./site
```

`site/` is a build artifact and is gitignored. The published site at
<https://ocarinow.github.io/ocai/> is deployed by
[`.github/workflows/docs.yml`](https://github.com/ocarinow/ocai/blob/main/.github/workflows/docs.yml):
pull requests that touch `docs/**` or `zensical.toml` build the site as a
check; a push to `main` builds it again and deploys it to GitHub Pages.

!!! info "Source-available, not open source"

    ocai ships under the Functional Source License (FSL-1.1-ALv2). Please
    don't describe it as "open source".
