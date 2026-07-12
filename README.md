# ocai

**One Common interface for AI** — a single, stable, provider-neutral API in
front of every AI capability (LLM chat, embeddings, vector stores, monitoring)
so your code never imports a provider SDK.

> **Status: re-architected skeleton (July 2026).** Structure, contracts, and
> interactions are laid out end to end per
> [`docs/architecture.md`](docs/architecture.md); most behavior is an honest
> `# TODO` stub. Nothing here makes a network call yet.

## The pitch: honest, version-resilient conversion

Switching provider, provider *interface*, or provider *version* is ocai's
problem, not yours — and every conversion reports exactly what it cost,
never silently.

The canonical example: OpenAI ships `/responses` as the successor to
`/chat/completions`. In ocai these are *sibling interfaces* of one
capability, both nodes in a governed conversion catalog. Your code does not
change:

```python
result = model.chat(request)

result.value    # ChatResponse — the canonical payload, pure
result.route    # openai/responses@2026-03 — which interface+tag served the call, and why
result.report   # FidelityReport — per-field, per-edge account of what the conversion cost
```

When the catalog resolves to `/responses` instead of `/chat/completions`, the
`Route` says so and the `FidelityReport` itemizes every renamed,
approximated, emulated, or dropped field — `lossless` is derived, never
asserted. Out-of-range values pass verbatim with an `APPROXIMATED` report;
unmapped provider data rides censused `extensions`; a provider-anchored id
that cannot cross an interface boundary is `UNSUPPORTED`-and-reported, never
silently dropped.

## Layer map

One distribution (`ocai`), PEP 420 namespace packages, arrows enforced in CI:

```
ocai.core        CONTRACT — pure stdlib, zero deps, zero I/O: identity,
                 fidelity, CallResult, credentials, refs, IR envelope, canonjson
ocai.chat / .embedding / .vectorstore   CAPABILITY CONTRACTS — port + IR (→ core)
ocai.convert     MEANING — Catalog, planner, EdgeContract, conformance (→ core)
ocai.runtime     MOVEMENT — sans-io drivers, Decision hooks, Workspace (→ core, convert)
ocai.wire        REMOTE TRANSPORT — HTTP/SSE, hosts, wire policies (→ runtime; httpx via extra)
```

Plugins (`ocai-openai`, `ocai-anthropic`, …) ship one subpackage **per
interface** (`ocai.openai.chat_completions`, `ocai.openai.responses`) and
depend on core+convert only — never on the wire stack, so an offline audit
tool can re-convert archived traffic without the ability to make network
calls. Local adapters (FAISS, llama.cpp) implement a capability port directly;
local and remote are peers behind the same `CallResult`.

## Install & usage sketch

Requires [uv](https://docs.astral.sh/uv/) and Python 3.13+.

```bash
uv sync                  # create env + install workspace distributions
uv run ruff check        # lint (must be clean)
uv run pytest            # invariants + spec conformance
```

The intended shape (skeleton today — the pipeline is stubbed):

```python
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.convert.catalog import Catalog
from ocai.core.credentials import ApiKey
from ocai.runtime.binding import Binding
from ocai.runtime.binding import Workspace

import ocai.openai

workspace = Workspace(
    catalog=Catalog.of(ocai.openai.FRAGMENT),          # immutable, provenance-stamped
    bindings={"openai": Binding(credentials=ApiKey.from_env("OPENAI_API_KEY"))},
)
model = workspace.chat("openai")                       # a ChatModel port

result = model.chat(ChatRequest(model="gpt-5", messages=[Message("user", "Hello!")]))
result.value.message.text                              # the reply
result.report                                          # what conversion cost
```

Streaming ends with `StreamEnd(usage, finish, report)`, and
`StreamAccumulator.fold(chunks)` must equal the non-streaming response — a
law pinned by golden fold-triple fixtures, not a convention.

## Monorepo philosophy

- **Spec at the center.** [`spec/`](spec/README.md) is the language-neutral
  source of truth: the canonical-JSON equality predicate, JSON Schema, golden
  fixtures (including fold triples), the extension census, and interface
  descriptors. CI re-runs every language's conformance suite when `spec/**`
  changes — the drift alarm.
- **Languages as peers.** Python ships first; `typescript/` and `go/` mirror
  the same spec. None is privileged.
- **Separate distributions, one namespace.** `ocai` (core) and each plugin
  merge into the shared `ocai` PEP 420 namespace; there is intentionally no
  `ocai/__init__.py` anywhere. Community plugins ship under
  `ocai.contrib.<name>` — see the
  [plugin author guide](docs/writing-a-plugin.md) and the template in
  [`examples/ocai-contrib-echo/`](examples/ocai-contrib-echo/).

## Repository layout

```
spec/        language-neutral truth: canonical-json.md, schema/, fixtures/,
             extensions/ (census), interfaces/ (descriptors)
docs/        architecture.md (the structural contract) + guides + plans/
python/      uv workspace: ocai-core (dist "ocai") + ocai-openai + ocai-anthropic
typescript/  go/    placeholders — mirror spec (not yet implemented)
examples/    ocai-contrib-echo (community-plugin template)
.github/     path-filtered CI
```

## License

**Source-available** under the Functional Source License (**FSL-1.1-ALv2**) —
see [LICENSE](./LICENSE). The FSL grant converts to Apache-2.0 two years
after each version's release. ocai is *not* open source. Contributions
require a DCO sign-off — see [CONTRIBUTING.md](./CONTRIBUTING.md).
