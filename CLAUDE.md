# CLAUDE.md

Guidance for Claude Code (and humans) working in this repo. Read this first; it
is inherited by every session. The structural contract — every layer, object,
and interaction — lives in [`docs/architecture.md`](docs/architecture.md);
milestone plans live in [`docs/plans/`](docs/plans/README.md). When code and
`docs/architecture.md` disagree, fix one in the same PR — stale constitution is
how drift compounds in agent-driven development.

## What ocai is

**ocai** (short for **"Ocarinow AI"**) is **One Common interface for AI**: a
single, stable, provider-neutral API in front of every AI capability (LLM
chat/generation, embeddings, vector stores, monitoring) so user code never
imports a provider SDK. Target users are enterprises putting GenAI in
production; foundations (auditability, governance, determinism, honest
reporting) are the product, not a nice-to-have. Status: re-architected
skeleton — structure and contracts are laid out end to end; most behavior is
`# TODO` stubs.

The differentiator is **honest, version-resilient conversion**: switching
provider, provider *interface* (e.g. OpenAI `/chat/completions` →
`/responses`), or provider *version* is ocai's problem, not the user's — and
every conversion reports exactly what it cost (`FidelityReport`), never
silently.

ocai is **source-available** under FSL-1.1-ALv2, not open source — never
describe it as "open source".

## Architecture (five load-bearing ideas)

1. **Contract kernel.** `ocai.core` is a pure-stdlib, zero-dependency,
   zero-I/O data-contract layer (identity, fidelity, errors, `CallResult`,
   credentials, `ProviderRef`, `CapabilityProfile`, IR envelope, canonical
   JSON). Everything else is replaceable machinery behind it.
2. **Four-level identity.** `Capability` (chat) → `Interface`
   (openai/chat_completions and openai/responses are *sibling interfaces*, not
   versions) → `tag` (dated revision) → `Shape` (chat.request…). A graph node
   is `NodeId(provider, interface, tag, shape)`. The canonical IR is itself
   the interface named `ocai` with dated revisions, so IR migration is
   ordinary graph conversion.
3. **Governed conversion catalog.** Immutable, provenance-stamped `Catalog`s
   (no process-global registries). Edges declare an `EdgeContract` (per-field
   disposition census); planner weights are *derived* from it and CI certifies
   runtime loss never exceeds the declaration. `TrustPolicy.OWNED_ENDPOINTS`
   by default; `Catalog.lock()` hashes into every `Route`.
4. **Sans-io execution.** All logic that is not the physical I/O call is pure
   and synchronous; two thin drivers (`SyncDriver`/`AsyncDriver`) execute it.
   Policy hooks return Decisions (`Proceed|Retry|Fail|Return`). Credentials
   are applied at the driver leaf, per attempt, *after* every hook — no
   middleware can see a secret. Port-tier `CallInterceptor`s (fallback,
   policy, cost, cache, tracing) work for local AND remote adapters; the port
   is the only contract, wire-backed is one implementation.
5. **Stream-first IR.** `fold(stream(request)) == complete(request)` is
   normative. Streams end with `StreamEnd(usage, finish, report)`. No new part
   type without its delta type, fold law, and paired fixtures.

## Repository layout

```
spec/        language-neutral source of truth: canonical-json.md, JSON Schema,
             golden fixtures (incl. fold triples), extension censuses
docs/        architecture.md (structural contract) + plans/ + guides
python/      uv workspace:
  packages/ocai-core       dist "ocai": ocai.core / ocai.chat / ocai.embedding /
                           ocai.vectorstore / ocai.convert / ocai.runtime / ocai.wire
  packages/ocai-openai     ocai.openai.chat_completions + ocai.openai.responses
  packages/ocai-anthropic  ocai.anthropic.messages
typescript/  go/           placeholders — mirror spec/ (not yet implemented)
examples/    ocai-contrib-echo (plugin template)
.claude/providers/         provider wire research informing the IR
```

Layer dependency arrows (enforced; violations are build failures):
capabilities → core; convert → core; runtime → core+convert; wire → runtime;
`ocai.chat.facade` is the one chat module allowed to import convert/runtime/wire
(a facade module never shares the front-door factory's name — `ocai.chat.model()`
stays free for the factory);
plugins → core+convert ONLY (never wire/httpx).

## Three version axes — keep distinct, never conflate

- **interface tag** — a provider interface's dated wire revision (`NodeId.tag`).
- **canonical IR revision** — dated `ocai@YYYY-MM` (also a `NodeId.tag`).
- **library public-API version** — semver of the shipped package.

## Commands

Requires [uv](https://docs.astral.sh/uv/) and Python 3.13+.

```bash
uv sync                  # create env + install workspace distributions
uv run ruff check        # lint (must be clean)
uv run pytest            # tests: invariants + conformance
uv run python -c "from ocai.core import CallResult; print('core ok')"
uv run python -c "import ocai.openai; print('plugin ok')"
```

## Cross-cutting rules (apply to every change)

1. **PEP 420 namespace:** never create `ocai/__init__.py` at the namespace
   root in any distribution. Only subpackages get `__init__.py`.
2. **Stability domains are earned.** At v0.2 only data contracts freeze
   additive-only: `ocai.core` vocabulary + `ocai.chat` port and IR + their
   spec/ schemas. `ocai.embedding`/`ocai.vectorstore` are provisional until
   they carry `CallResult` in real use. Hook protocols, plugin ABI
   (`CatalogFragment`), profile keys freeze at v1.0 only after the
   `/responses` migration and one real cross-provider failover have been
   exercised through them.
3. **Three version axes stay distinct** (above).
4. **Every port returns `CallResult(value, route, report, usage, raw)`** —
   named result objects, never bare tuples. The FidelityReport lives on
   `CallResult` only; IR payloads stay pure.
5. **Honesty is structural.** Nothing is silently dropped, approximated,
   clamped, or rescaled: unmapped fields ride namespaced `extensions`
   (censused — schema-registered in `spec/extensions/`, unregistered keys fail
   CI); semantic divergence is a `SemanticShift`; out-of-range values pass
   verbatim with an `APPROXIMATED` report; `ProviderRef`s crossing a
   `(provider, interface)` boundary are `UNSUPPORTED`-and-reported.
6. **Total decode / forward compat.** No IR decode path may ever raise on
   unknown input: unknown part tags → `PartUnknown`, unknown deltas →
   `DeltaUnknown`, unknown envelope keys → swept into `extensions`, enums are
   open string codes with the provider's verbatim value preserved in a
   `native` lane. Nothing is ever renamed or removed; deprecations are
   annotations; reform happens via dated canonical revisions with migration
   edges.
7. **Streaming has honesty parity.** One canonical `ChatChunk` event type;
   every stream ends with `StreamEnd(usage, finish, report)`;
   `StreamAccumulator.fold(chunks)` must equal the non-streaming response
   (golden fold-triple fixtures per streaming edge); PART_STOP's final part
   must equal its delta accumulation.
8. **Errors map to the shared taxonomy** (`RateLimitError`, `AuthError`,
   `ContextLengthError`, `ContentFilterError`, `TransientError`); mid-stream
   errors have a wire shape (canonical code + native + retryable), not just a
   Python exception.
9. **Every edge ships an `EdgeContract` + golden fixtures** in `spec/`;
   conformance certifies runtime loss ⊆ declared census. A change to `spec/**`
   re-runs every language suite.
10. **Tests are wire-level:** recorded HTTP/SSE pairs (respx-style), never
    live keys, never provider-SDK mocks. CI must pass with no secrets.
11. **No pydantic, no msgspec in `ocai.core`** — canonical types are stdlib
    dataclasses, zero third-party deps. msgspec is sanctioned only at plugin
    wire-decode boundaries. Pydantic users are served by duck-typed
    `model_json_schema()` acceptance and optional satellite dists — never a
    core dependency. The hand-authored JSON Schema in `spec/` is the neutral
    source of truth; dataclasses are conformance-tested against it.
12. **No provider SDKs anywhere.** ocai owns the wire via `ocai.wire`. The
    only permitted provider-adjacent dependency is a narrow signing library
    inside a cloud-hosting plugin.
13. **Credentials are explicit-only** — no ambient discovery; only
    `ApiKey.from_env/.from_file` may read env/filesystem and only when called.
    Applied by the driver at the leaf, per attempt, after all hooks; redacted
    in `repr`/logs; never in `raw`, reports, or `provider_options`.
14. **Catalogs, not globals.** Plugins export a frozen declarative
    `CatalogFragment`; no import-time mutation of shared state. Hosting is
    composed (`Direct`/`Custom`/`Vertex` values reading `DialectTraits` as
    data) — no `CloudProvider` base class; codecs are keyed by interface,
    never by host.
15. **Source-available, not open source** (FSL-1.1-ALv2). No OSI classifiers.
16. **Full type hints, `py.typed` in every distribution, `ruff` clean,
    `pytest` green.** Mark stubs with `# TODO:` and a one-line note.
17. **One work unit (WU) per PR.**
18. **Docstrings are Google style** (`Args:`/`Returns:`/`Raises:`/`Yields:`),
    never reST field lists or NumPy sections; never repeat a type the
    signature already declares; code references in prose are single-backtick.

## How to work a session

1. Pick one WU from [`docs/plans/`](docs/plans/README.md); read its
   done-criteria and the relevant `docs/architecture.md` + `spec/` sections.
2. Implement only that WU. Add/extend golden fixtures and recorded wire pairs.
3. Verify: `uv run ruff check && uv run pytest`. Report results.
4. Update the WU checkbox AND any architecture.md section your change affects.

## Sequencing principle

Never build the wedge on shaky table stakes. The two flagship WUs **are** the
product: the visible fidelity report and the interface-migration-with-no-user-
code-change proof (`/responses`). The conformance fixture set is the moat and
grows from day one. Three providers (OpenAI, Anthropic, Gemini) is plenty
until v1. Rules that are tests survive; rules that are prose rot — when you
add a rule, add its test.
