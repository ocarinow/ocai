# ocai

**One Common interface for AI** — provider-neutral Python contracts and
conversion machinery, designed as the foundation of an enterprise AI platform.

**Status:** M1–M3 are implemented: OpenAI Chat Completions and Anthropic Messages
support synchronous/asynchronous chat and streaming over the shared runtime.
Tests use synthetic and recorded wire-shaped fixtures, without live credentials.
Responses remains a stub; Gemini, embeddings/vector-store implementations,
telemetry exporters, auditing services, and agent hosting are future work.

The active canonical revision is `2026-07`. The
[core modernization plan](docs/plans/core-modernization.md) introduces ordered
interaction items, richer content/resources, stronger fidelity evidence, and
modern provider APIs before freezing revised contracts. Draft schemas live under
`spec/proposals/`; TypeScript and Go implementation are deferred.

## Why ocai

Applications use common requests and receive a `CallResult`:

- `value`: the canonical response.
- `route`: selected provider interface/revision and catalog fingerprint.
- `report`: per-edge conversion losses and semantic changes.
- `usage` and `raw`: consumption and provider output.

Conversions report renamed, approximated, emulated, preserved-in-extension,
dropped, and unsupported fields. `lossless` is derived from emitted records.
Fixtures check output and reporting against expectations; this is not a proof
that arbitrary third-party code reports every loss. See the
[architecture](docs/architecture.md#current-fidelity-and-admission-guarantees).

## Development and usage

Python 3.13+ and [uv](https://docs.astral.sh/uv/) are required.

```bash
uv sync --all-packages
uv run python scripts/check.py
uv run python examples/cross_conversion_demo.py
```

For a live call, install the HTTP extra and a provider plugin. Credentials are
explicit; constructing a model does not discover them from the environment.

```python
import ocai.chat
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.core import ApiKey

model = ocai.chat.model(
    "openai/gpt-4o",
    credentials=ApiKey.from_env("OPENAI_API_KEY"),
)
result = model.chat(ChatRequest(messages=[Message.user("Hello!")]))
print(result.value.message.text)
print(result.report)
```

The model name is routing configuration, not a field on `ChatRequest`.
The example model must be available to your account. Explicit catalogs let an
application select its plugins; omitted catalogs discover installed
`ocai.fragments` entry points.

## Layers and packages

| Layer | Purpose |
|---|---|
| `ocai.core` | Standard-library contracts, identities, context, results, fidelity, references |
| `ocai.chat / embedding / vectorstore` | Capability data and ports; only chat currently exercised end to end |
| `ocai.convert` | Catalog composition, graph planning, conversion and conformance |
| `ocai.runtime` | Drivers, bindings, policy decisions, interceptor composition |
| `ocai.wire` | HTTP/SSE, hosting and retry; HTTP dependency is optional |
| Provider distributions | Pure interface-specific codecs, edges, profiles and factories |

The `ocai` distribution contains the shared layers. `ocai-openai` and
`ocai-anthropic` extend the PEP 420 namespace without provider SDKs.
The [community example](examples/ocai-contrib-echo/) demonstrates an independently
installed conversion-only plugin; see the [author guide](docs/writing-a-plugin.md).

## Repository

- `spec/schema`, `spec/fixtures`: active schemas and conformance evidence.
- `spec/proposals`: isolated draft contracts, not registered runtime revisions.
- `python/packages`: shared library and provider distributions.
- `docs`: architecture, [support matrix](docs/provider-feature-matrix.md), and plans.
- `examples`: cross-conversion demo and community plugin.
- `typescript`, `go`: placeholders.

The platform roadmap adds telemetry, durable audit, evaluations, typed asset
registries, and agent execution/management as separate libraries and services.
The kernel stays independent of those backends.

## License

Source-available under **FSL-1.1-ALv2**, converting to Apache-2.0 two years after
each version's release. ocai is not open source.
See [LICENSE](LICENSE) and [CONTRIBUTING.md](CONTRIBUTING.md); contributions
require DCO sign-off.
