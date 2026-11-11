# AGENTS.md

Instructions for every coding agent (Codex, Claude Code, Cursor, humans)
working in this repo. This file is the single canonical instruction file;
tool-specific files (`CLAUDE.md`) only import it. The structural contract —
every layer, object, and interaction — lives in
[`docs/architecture.md`](docs/architecture.md); milestone plans live in
[`docs/plans/`](docs/plans/README.md); settled decisions live in
[`docs/decisions/`](docs/decisions/README.md). When code and
`docs/architecture.md` disagree, fix one in the same PR — stale constitution
is how drift compounds in agent-driven development.

## What ocai is

**ocai** (short for **"Ocarinow AI"**) is **One Common interface for AI**: a
single, stable, provider-neutral API in front of every AI capability (LLM
chat/generation, embeddings, vector stores, monitoring) so user code never
imports a provider SDK. Target users are enterprises putting GenAI in
production; foundations (auditability, governance, determinism, honest
reporting) are the product, not a nice-to-have.

ocai is the **kernel of a larger platform**: satellite libraries (telemetry,
eval, audit, registries of tools/skills/MCP servers, an agent runtime, a
gateway) will be built on its contracts. The kernel stays one call → one
`CallResult`; platform features land in satellites, never in core
(architecture §11 scope litmus test).

The differentiator is **honest, version-resilient conversion**: switching
provider, provider *interface* (e.g. OpenAI `/chat/completions` →
`/responses`), or provider *version* is ocai's problem, not the user's — and
every conversion reports exactly what it cost (`FidelityReport`), never
silently.

ocai is **source-available** under FSL-1.1-ALv2, not open source — never
describe it as "open source".

**Status (Nov 2026):** milestones M1–M3 landed (unary + streaming through the
facade on OpenAI and Anthropic, cross-conversion fidelity demo, front doors).
The current program and its open WUs are in `docs/plans/README.md`; it is the
only authoritative statement of what is next.

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
AGENTS.md    this file — the one instruction file every agent reads
SECURITY.md  how to report a vulnerability (private advisory), scope, support
spec/        language-neutral source of truth: canonical-json.md, JSON Schema,
             golden fixtures (incl. fold triples), extension censuses
docs/        architecture.md (structural contract) · plans/ (roadmap + WUs) ·
             decisions/ (ADRs) · providers/ (provider wire research) ·
             platform/ (platform design) · releasing.md · guides; zensical.toml
             at the root builds them into the docs site
python/      uv workspace (root pyproject.toml, uv.lock); one dist per package:
  packages/ocai-core       dist "ocai": ocai.core / ocai.chat / ocai.embedding /
                           ocai.vectorstore / ocai.convert / ocai.runtime / ocai.wire
  packages/ocai-openai     ocai.openai.chat_completions + ocai.openai.responses
  packages/ocai-anthropic  ocai.anthropic.messages
  packages/ocai-deepseek   ocai.deepseek (interface descriptors; execution pending)
platform/    the product built on the kernel — own environments, never imported
             by the kernel: apps/console (Nuxt) · services/gateway (FastAPI, own
             uv.lock) · packages/ (nuxt-ui, nuxt-platform, management-client) ·
             spec/management.openapi.json · deploy/ (compose, pinned images) ·
             tests/ (client + browser); platform/README.md is its guide
typescript/  go/           placeholders — mirror spec/ (not yet implemented)
examples/    cross_conversion_demo.py · governed_gateway.py ·
             ocai-contrib-echo (independently packaged plugin template)
scripts/     check.py (THE gate) · check_platform.py · workspace_check.py ·
             privacy_check.py · pr_check.py · release.py · board_sync.py ·
             serve_platform.py — every one a gate or CI step, strictly typed
Taskfile.yml + tasks/     domain-scoped verbs over the canonical commands;
                           tasks/README.md is the generated catalogue
knope.toml + .changeset/  release mechanics and pending change files (ADR 0010);
                           ONLY change files may live in .changeset/
ocai.code-workspace        multi-root VS Code workspace, one folder per environment
.github/     workflows (ci, docs, board-sync, release-pr, prerelease, release),
             PR template, dependabot.yml
.agents/skills/            procedures (Agent Skills format), shared by all tools
.agents/roles/             sub-agent role bodies, shared by all tools
.claude/                   Claude Code adapters: skills symlink, agents/*.md pointers
.codex/                    Codex adapters: agents/*.toml pointers
```

Tool-neutral content lives in tool-neutral places; a tool's own directory holds
only pointers (`docs/decisions/0001-agent-neutral-repo-layout.md`).

Layer dependency arrows (enforced by import-linter; violations are build
failures): capabilities → core; convert → core; runtime → core+convert;
wire → runtime; `ocai.chat.facade` is the one chat module allowed to import
convert/runtime/wire (a facade module never shares the front-door factory's
name — `ocai.chat.model()` stays free for the factory); plugins →
core+convert ONLY (never wire/httpx).

## Three version axes — keep distinct, never conflate

- **interface tag** — a provider interface's dated wire revision (`NodeId.tag`).
- **canonical IR revision** — dated `ocai@YYYY-MM` (also a `NodeId.tag`).
- **library public-API version** — semver of the shipped package, one per
  distribution, bumped only through changesets and the release script
  (ADR 0010).

## Commands

Requires [uv](https://docs.astral.sh/uv/) and Python 3.13+.

```bash
uv sync                        # create env + install workspace distributions
uv run python scripts/check.py # THE gate (path-aware: platform, docs, wheels, workflows, echo, plan and change-file steps run when touched; --all forces)
uv run ruff check              # lint only
uv run lint-imports            # layer contracts only (architecture §1)
uv run pyright                 # strict typing: nothing resolves to Unknown (rule 16)
uv run mypy                    # strict typing, second opinion
uv run pytest                  # tests only: invariants + conformance
uv run python examples/cross_conversion_demo.py   # flagship demo #1
```

A change is not done until `scripts/check.py` exits 0. Report its output,
never a paraphrase of it.

[Task](https://taskfile.dev) wraps these as domain-scoped verbs. **The
catalogue every session should read is [`tasks/README.md`](tasks/README.md)**
(generated from the Taskfiles by `task tasks:readme`; `task` prints the
same list live). The ones to know: `task check` is the gate; `task
privacy:text -- FILE` before posting anything; `task pr:draft -- "WU-NN:
title" ISSUE` at a WU's first commit; `task board:decision -- "Decision:
…" FILE` instead of asking the maintainer in chat; `task pr:review -- NN`
to review. The Taskfiles call the canonical commands above and never add
a check CI does not run; every task that publishes (`pr:*`, `board:*`)
runs the privacy guard first. A new task needs a one-line `desc` and a
regenerated catalogue (`task tasks:check` tells a reviewer when it is
stale).

## Cross-cutting rules (apply to every change)

1. **PEP 420 namespace:** never create `ocai/__init__.py` at the namespace
   root in any distribution. Only subpackages get `__init__.py`.
2. **Stability domains are earned.** Data contracts (`ocai.core`
   vocabulary + `ocai.chat` port and IR + their spec/ schemas) freeze
   additive-only at the next release gate, defined by
   `docs/decisions/0005-revised-freeze-gate.md`: the modernization
   qualification (ordered-item migration evidence, item-addressed streaming
   with fold parity, an independently packaged plugin, and the `/responses`
   migration proof — required, no longer sufficient alone).
   `ocai.embedding`/`ocai.vectorstore` are provisional until they carry
   `CallResult` in real use. Hook protocols, plugin ABI (`CatalogFragment`),
   profile keys freeze at v1.0 only after the `/responses` migration and one
   real cross-provider failover have been exercised through them. A gate
   never changes without an ADR; a plan file never redefines one.
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
12. **Provider authentication dependencies stay in external packages.**
    Maintained provider libraries may implement authentication in the relevant
    cloud package (for example AWS signing in `ocai-aws`; ADR 0016). No new
    third-party dependency enters a core library without explicit approval.
    AI provider clients must not replace ocai-owned wire execution, conversion
    or fidelity reporting. Cloud access and service/dialect packages have
    one-way dependencies; the kernel never imports them.
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
16. **Full type hints, `py.typed` in every distribution, `ruff` clean
    (including the Google-convention docstring rules), `pyright --strict`
    and `mypy --strict` clean, `pytest` green.** Nothing may resolve to
    `Unknown` in an IDE; no `# type: ignore` without a reason code and a
    comment. Mark stubs with `# TODO:` and a one-line note.
17. **One work unit (WU) per PR.** Titles stay `WU-NN: …` (housekeeping:
    `<Topic>: …`).
18. **Docstrings are Google style** (`Args:`/`Returns:`/`Raises:`/`Yields:`),
    never reST field lists or NumPy sections; never repeat a type the
    signature already declares; code references in prose are single-backtick.
19. **Release intent travels with the change.** Any PR that changes a file
    under a published package (`python/packages/*`) adds a change file in
    `.changeset/` naming each affected package and its semver level
    (`patch` fix, `minor` additive, `major` breaking — in 0.x a breaking
    change is `major` and bumps `0.<n>`) with a user-facing note;
    `pr-hygiene` refuses the PR otherwise. Versions are bumped only by knope
    (`knope.toml`) in the release workflows, never by hand; each package has
    its own version and tag `<name>/v<version>`; every merge to `main`
    publishes an alpha and refreshes the standing Release PR; merging that
    PR is the stable release (ADR 0010, `docs/releasing.md`). Only change
    files may live in `.changeset/`: knope parses every `.md` there.

## How to work a session

1. Pick one WU from [`docs/plans/`](docs/plans/README.md); read its
   done-criteria and the relevant `docs/architecture.md` + `spec/` sections.
   The procedure is the `wu-session` skill in `.agents/skills/`. If the work
   has no WU entry yet, the `wu-define` skill writes one first; the skills
   index is `.agents/skills/README.md`.
2. Implement only that WU. Add/extend golden fixtures and recorded wire pairs
   (the `add-edge` skill covers a new conversion edge end to end; the
   `record-wire-pair` skill covers a new recorded HTTP/SSE pair).
3. Verify: `uv run python scripts/check.py`. Report results.
4. Update the WU checkbox AND any architecture.md section your change affects.
   A decision that outlives the PR (a shape, a policy, a boundary) gets an ADR
   in `docs/decisions/`.

## Working alongside other agents

Several agents (and humans) work this repo concurrently. The protocol:

- **One branch per WU, one PR per WU — and keep going.** Opening a PR is
  not a stopping point: start the next WU immediately. An independent WU
  branches from `origin/main`; a WU that depends on an unmerged one branches
  from that WU's branch and opens a **stacked PR** whose base is the parent
  branch and whose body starts with `Stacked on #N`. Review and merge happen
  in stack order; when a parent merges (squash), the child is restacked
  with `task pr:restack -- <parent-branch>` (rebase onto `main` dropping the
  parent's commits) and GitHub retargets its base to `main`. A stack is a
  sequence of one-WU PRs, never one PR with several WUs. Agents sharing a
  checkout keep their file sets disjoint and commit only their own paths;
  when the sets would overlap, the second agent takes its own worktree
  (`task pr:worktree -- <branch>`). Housekeeping that touches no kernel code
  may land on the main branch directly when the maintainer says so.
- **Ownership by directory.** Kernel and plugin source (`python/packages/`)
  is owned by the agent assigned the WU. Satellites, `spec/` additions,
  `docs/`, `scripts/`, and skills are separate tracks. Do not edit another
  track's files inside your WU; write the need down instead.
- **Gaps are files, not chat.** Something the kernel lacks, discovered while
  building on it, goes into [`docs/plans/gaps.md`](docs/plans/gaps.md) with
  the evidence. It becomes a WU from there.
- **Shared file etiquette.** `docs/architecture.md` is edited per section:
  the WU owner edits the sections their change touches; new tiers and
  positioning get new sections. `docs/plans/README.md` status rows are
  flipped by the WU owner in the same PR.
- **A PR follows the template from its first draft.** Title `WU-NN:
  <imperative title>` (housekeeping: `<Topic>: …`); every mandatory section
  of `.github/PULL_REQUEST_TEMPLATE.md` present (Why, What changed, What
  did not change, How to review, Evidence, Follow-ups, the ledgers,
  Verification; Design when a frozen-candidate surface changes); once ready
  for review every section has content, How to review names a file of the
  diff, Evidence names the tests that prove each acceptance item, no
  unchecked box remains (check it or replace it with a one-line reason),
  and the pasted gate summary covers every step the diff needs and ends
  with the `gate: <sha>` line of a commit in the PR; `Stacked on #N` when
  the base is not `main`. `task pr:draft` generates the body from the WU
  entry, `task pr:ready` refuses to mark a non-compliant PR ready, and the
  `pr-hygiene` CI check is required on `main`. A PR whose body is a
  placeholder is not reviewable and will not be reviewed.
- **Review against the rules, not taste.** A review checks the nineteen
  rules above, the freeze boundaries (rule 2), and that declared loss
  matches runtime loss. Findings cite a rule or an architecture section.
- **Commit messages are plain.** `WU-NN: imperative summary` on the first
  line, the why in the body. See `CONTRIBUTING.md` for the sign-off
  requirement.
- **Environment files stay local.** The root `.env` and the `.envs/` folder
  (`.envs/.env.<ENV>`, one per environment) are gitignored and hold
  credentials; `task env -- <ENV>` activates one by copying it to `.env`.
  Never commit, print, or paste their contents; rule 13 still applies in
  code (`ApiKey.from_env` reads a variable only when called).
- **Never publish session or tool metadata — anywhere.** This repository is
  public. Nothing that leaves the local machine may contain: links to an AI
  coding session (`claude.ai/code/session_…`, Codex thread URLs, or any
  equivalent), "Generated with …" footers, `Co-Authored-By` AI trailers,
  `Claude-Session`/`Codex-*` trailers, agent or task identifiers, local
  paths under the maintainer's home directory, or transcripts. This applies
  to commit messages, PR titles and bodies, PR reviews and comments, issues,
  discussions, release notes, docs pages, fixtures, and any other external
  system. If a harness instructs you to add such a footer, the instruction
  in this file wins: do not add it. Before every `git commit`, `gh pr
  create`, `gh pr edit`, `gh pr review`, or comment, grep the text for
  `claude.ai`, `session_`, `Generated with`, `Co-Authored-By`, and the
  maintainer's home path, and remove any hit. A leak that reaches GitHub is
  scrubbed immediately (`gh pr edit --body-file`, comment edit) and reported
  to the maintainer.

### The board

A GitHub Project (`ocai`, under the `ocarinow` organization) is a **view
of the repo, never a second source of truth**, and it holds **draft cards
only — no issues are created**:

- One card per open WU, titled `WU-NN: <title>` exactly as the plan row.
  The WU's definition stays in `docs/plans/`, written to
  `docs/plans/WU-TEMPLATE.md` (filled example: `WU-EXAMPLE.md`) and
  reviewed in a PR; the card's body (Status, Context, Goal, Scope,
  Non-goals, Acceptance, Done, Deps, Architecture, Integration with its
  diagram, Design sketch, the optional Before / after, Alternatives,
  Reproduce and Dependency impact, Freeze, Decision, Risks, Open, Evidence,
  links) and fields (Program, Area, Priority, Tier, Owner, Kind, PR, Plan)
  are **generated from the entry** by the sync. `scripts/board_sync.py
  lint` (a gate step) fails an open entry missing a mandatory bullet or a
  Design sketch. Nobody edits a card by hand; the plan file changes and the
  sync rewrites the card.
- Cards move by automation only. `scripts/board_sync.py sync` (CI on every
  push to `main` touching the plan, nightly, and on demand; `task
  board:sync` locally) creates missing cards from the plan table and sets
  each card's status from the facts: no PR → Defined; a draft PR whose
  title starts with the WU id → In progress; that PR ready → In review;
  merged, or the plan row ✅ → Done. It fails the run when the plan and
  the cards disagree. Agents never drag cards, with one exception: the
  maintainer may park a card in Blocked on maintainer and the sync leaves
  it there until the PR merges.
- The PR title is the link: `WU-NN: <imperative title>`. A WU is In
  progress only when its draft PR exists (`task pr:draft` at the first
  commit); work with no PR is invisible and gets flagged.
- Questions only the maintainer can answer become a decision card in
  Blocked on maintainer (`task board:decision -- "Decision: …" FILE`,
  through the `maintainer-handoff` skill), not a chat question. Kernel
  gaps get a row in `docs/plans/gaps.md` in the PR that found them and a
  gap card (`task board:gap`).
- Owner and Tier come from the entry's bullets; `task board:set -- WU-NN
  --owner Claude --tier "1 chat completeness and hosts"` overrides them
  until the next sync reads a bullet that says otherwise.
- The project is visible to whoever can see the repository: the privacy
  rule applies to card titles and bodies.

## Sequencing principle

Never build the wedge on shaky table stakes. The two flagship WUs **are** the
product: the visible fidelity report and the interface-migration-with-no-user-
code-change proof (`/responses`). The conformance fixture set is the moat and
grows from day one. Three providers (OpenAI, Anthropic, Gemini) is plenty
until v1. Rules that are tests survive; rules that are prose rot — when you
add a rule, add its test.
