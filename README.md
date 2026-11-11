# ocai

**One Common interface for AI** — a single, stable, provider-neutral API in
front of every AI capability (LLM chat, embeddings, vector stores, monitoring)
so application code never imports a provider SDK. The differentiator is
**honest, version-resilient conversion**: switching provider, provider
*interface* (OpenAI `/chat/completions` → `/responses`), or provider *version*
is ocai's problem, not the user's, and every conversion reports exactly what
it cost (`FidelityReport`), never silently. Target users are enterprises
putting GenAI in production; auditability, governance, and determinism are the
product, not a nice-to-have.

The Python library currently qualifies unary and streaming chat on OpenAI Chat
Completions, Anthropic Messages and DeepSeek, plus Anthropic unary InvokeModel
hosting on Bedrock with explicit AWS credentials. Conversion, stream middleware,
inspection and observer events are exercised by recorded tests. Responses is a
stub; embeddings/vector stores are provisional contracts; TypeScript and Go are
not implemented. See the [support matrix](docs/user/provider-feature-matrix.md).

The platform is a foundation preview: a status console/API and internal identity,
organization storage and authorization services. It does not yet expose a working
inference gateway. Product designs and planned satellites are not shipped features.

- **Use the packages:** [installation and first call](docs/user/libraries/python/README.md).
- **Use the platform:** [current platform guide](docs/user/platform/README.md).
- **Browse APIs:** [source-derived reference](docs/user/reference/README.md).
- **Contribute or inspect plans:** [documentation map](docs/README.md).

## Repository map

| Directory | Role | Start at |
|---|---|---|
| `spec/` | Language-neutral source of truth: canonical JSON, JSON Schema, golden fixtures (incl. fold triples), extension census, interface descriptors, draft proposals | [spec/README.md](spec/README.md) |
| `python/` | The first implementation: a uv workspace with six distributions (`ocai`, three codecs, AWS credentials and Bedrock hosting) | [python/README.md](python/README.md) |
| `typescript/` | Placeholder; will mirror `spec/` and run the same fixtures | [typescript/README.md](typescript/README.md) |
| `go/` | Placeholder; will mirror `spec/` and run the same fixtures | [go/README.md](go/README.md) |
| `docs/` | Published user docs (`user/`), contributor docs (`development/`), proposed designs (`design/`), dated research (`research/`), architecture, decisions and plans | [docs/README.md](docs/README.md) |
| `examples/` | The cross-conversion fidelity demo and `ocai-contrib-echo`, the plugin template | [examples/ocai-contrib-echo/README.md](examples/ocai-contrib-echo/README.md) |
| `scripts/` | `check.py`, the one verification command (lint, import contracts, strict typing, tests) | [scripts/check.py](scripts/check.py) |
| `Taskfile.yml`, `tasks/` (one `<domain>.Taskfile.yml` each) | Domain-scoped development commands over the canonical ones (`task` lists them, `task check` is the gate) | [Taskfile.yml](Taskfile.yml) |
| `.agents/` | Procedures and role bodies for coding agents, shared by every tool; `.claude/` and `.codex/` hold only pointers | [.agents/skills/README.md](.agents/skills/README.md) |

## Start here

- **Use the library:** [python/README.md](python/README.md) — install,
  front door, streaming, developer commands.
- **Read the docs site:** <https://ocarinow.github.io/ocai/>.
- **Understand the structure:** [docs/architecture.md](docs/architecture.md)
  is the structural contract every layer, object, and interaction follows.
- **Read the spec:** [spec/README.md](spec/README.md) — the equality
  predicate, the schemas, and the fixture shapes every port must pass.
- **See what is next:** [docs/plans/README.md](docs/plans/README.md) (roadmap
  and work units) and [docs/decisions/README.md](docs/decisions/README.md)
  (ADRs: why each settled shape was chosen).
- **Contribute, as a human or a coding agent:** [AGENTS.md](AGENTS.md) is the
  single instruction file (rules, layout, session procedure);
  [CONTRIBUTING.md](CONTRIBUTING.md) covers the DCO sign-off and review
  expectations.

## How the pieces relate

`spec/` is the truth. It serializes the structural contract in
`docs/architecture.md` as normative documents, JSON Schema, and golden
fixtures; every language port consumes those same files, and a port that
drifts from `spec/` fails its own conformance suite (CI re-runs every
implementation's suite whenever `spec/**` changes). `python/` is the first
port and the proof that the contracts hold on real provider traffic, through
recorded wire pairs rather than live keys. Provider support ships as separate
distributions in the same `ocai` namespace, each contributing a frozen
`CatalogFragment` to the conversion graph; `examples/ocai-contrib-echo` is the
template for a third-party one. The platform satellites, when they arrive,
will be separate libraries built on the kernel's hook protocols and
`CallResult`, never features of the kernel itself.

## License

Source-available under **FSL-1.1-ALv2**, converting to Apache-2.0 two years
after each version's release. ocai is not open source. See
[LICENSE](LICENSE) and [CONTRIBUTING.md](CONTRIBUTING.md); contributions
require DCO sign-off.
