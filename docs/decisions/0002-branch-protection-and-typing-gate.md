# 0002 — Branch protection and the strict typing gate

- **Status:** accepted; amended 2026-11-11 (required checks, path filtering, workflow hardening)
- **Date:** 2026-11-10
- **Deciders:** maintainer, with Claude Code

## Context

The repository went public on GitHub on 2026-11-10 (`ocarinow/ocai`, default
branch `main`) and CI ran for the first time. Two coding agents and one
maintainer now land changes. Rule 17 (one WU per PR) and rule 16 (full type
hints) were prose; neither was enforced by anything.

The maintainer's bar for typing: opening the repo in an IDE must show nothing
resolving to `Unknown`. That is Pyright's strict-mode vocabulary (what Pylance
displays), so Pyright strict is the gate that matches the requirement; mypy
strict is cheap because the tree was already fully annotated and catches a
different class of errors. Baseline measured before enforcement:

| Checker | Diagnostics | Where |
|---|---|---|
| pyright strict | 652 | 354 in tests, 178 in the two provider codecs, 130 in `ocai-core` src, 6 in examples/scripts |
| mypy strict | 11 | 7 in `ocai-core`, 4 in `ocai-anthropic` |

## Decision

**Branch ruleset on `main`** (GitHub ruleset 26964282, active, no bypass
actors):

- pull requests only; squash or rebase merges; linear history;
- required status checks `python`, `privacy`, `pr-hygiene`, `platform`, and
  `docs` (the CI and Docs jobs), branch must be up to date with `main`
  before merge (amended 2026-11-11; originally `python` alone);
- review threads must be resolved; zero required approvals while there is
  one human maintainer;
- no force push, no deletion.

**Typing gate**, part of `scripts/check.py` and the CI `python` job:

- `pyright` in `typeCheckingMode = "strict"` over all three `src` trees,
  all three test trees, `examples/`, and `scripts/`, configured in the root
  `pyproject.toml` so the IDE and CI see the same thing;
- `mypy --strict` over the nine namespace portions (never `ocai` itself,
  rule 1), configured in the same file;
- `Any` is permitted where data is genuinely dynamic (wire JSON); `Unknown`
  is never permitted; `# type: ignore` / `# pyright: ignore` require a rule
  code and a one-line reason.
- The 652 + 11 baseline diagnostics are fixed in the same change that
  enables the gate, so `main` is never red.

## Alternatives considered

- **mypy only.** Does not report `Unknown`; the IDE would still show it.
- **A ratchet (baseline file or per-file `# pyright: basic`).** Would let
  the gate land before the fixes, but every excluded file is a place the
  IDE still shows `Unknown`, which is the exact thing the maintainer asked
  to eliminate. Fixing first is one larger PR but leaves no debt.
- **Required approvals = 1.** Blocks a solo maintainer on themself. Set it
  when a second human reviewer exists.
- **Enforcing DCO sign-off.** CONTRIBUTING asks for it, no commit has it;
  decide whether the DCO is real before a check enforces it.

## Consequences

- Every PR runs ruff, import contracts, pyright strict, mypy strict, and
  pytest. `scripts/check.py` runs the identical steps locally.
- `pyright` and `mypy` join the dev dependency group; neither is a runtime
  dependency of any distribution (rule 11 untouched).
- Provider codecs carry explicit `dict[str, Any]` annotations at the wire
  boundary; that is the honest shape of wire JSON, not a weakening.
- Branch names are convention (`wu-NN-short-slug`), not ruleset.

## Amendment 2026-11-11 — required checks match the gate

**Context.** `scripts/check.py` had grown to cover the platform (gateway,
console, browser tests) and the docs site built on every docs change, but
the ruleset still required only `python`, `privacy`, and `pr-hygiene`. A PR
that broke the gateway or the Nuxt build could merge. Workflows also ran
with the default token permissions, synced the uv workspace without
`--locked`, had no timeouts, no concurrency groups, reinstalled Playwright
on every run, and referenced actions by movable tag.

**Decision.**

- The required status checks on `main` are `python`, `privacy`,
  `pr-hygiene`, `platform`, and `docs` — every job that `scripts/check.py`
  runs locally, plus the docs build. The gate and the protection are the
  same set.
- A required check must report on every pull request, so **path filtering
  happens inside the job**, never at the workflow trigger: each job starts,
  runs `dorny/paths-filter`, and skips its heavy steps when the change does
  not touch its tree, reporting success in seconds. A `paths:` filter on the
  trigger would leave the check "expected" forever and block the merge.
- Every workflow declares `permissions: contents: read` at the top; a job
  that needs more (Pages deploy, release PR) declares it on the job.
- Every action is pinned to a commit SHA with the version as a trailing
  comment; Dependabot keeps both current. Floating refs such as
  `release/v1` are not used.
- `uv sync --locked` in CI: a lockfile that drifted from `pyproject.toml`
  fails the run instead of being re-resolved silently.
- Every job has a `timeout-minutes`; pull-request runs share a concurrency
  group per PR with cancel-in-progress, pushes to `main` never cancel.
  Pages deploys stay serialized under one group.
- Playwright browsers are cached on the platform lockfile hash.

**Consequences.** Kernel-only PRs still see the `platform` and `docs` checks,
but they finish in under a minute. The `python` job's filter now also covers
`scripts/`, `tasks/`, `uv.lock`, `knope.toml`, and all of `examples/`, since
the gate reads them. The DCO question above is answered separately: the DCO
GitHub App is the chosen enforcement, installed by the maintainer, and its
check joins this list once it reports on pull requests.

## Amendment 2026-11-11 (b) — the gate grows; the checks follow

**Context.** The gate verified lint, types, tests, and the platform, but
nothing opened the wheels it ships, audited the workflows that publish them,
scanned the code for the classic security mistakes, reviewed the licenses of
new dependencies, ran the kernel on the next interpreter, or linted the
TypeScript. The maintainer judged the gate insufficient for a project of
this size and set three conditions on every new tool: free, no account or
key, open source.

**Decision.**

- **Kernel steps added to `scripts/check.py` and CI:** `uv lock --check`
  (both uv environments), the task catalogue freshness check, ruff's
  flake8-bandit rules (`S`, with per-file exceptions written next to their
  reason in `pyproject.toml`), pytest with `filterwarnings = ["error"]`,
  `--strict-markers`, `--strict-config`, mypy over the gateway tests, and
  `scripts/wheel_check.py`, which builds every distribution and opens the
  wheel (no namespace-root `__init__.py`, `py.typed` per portion, license
  expression and project URLs in METADATA, no OSI classifier).
- **Interpreters:** the kernel job runs on 3.13 (`python`) and 3.14
  (`python-next`); both are required checks; the names stay fixed when the
  versions roll so the ruleset does not change.
- **Workflows:** `zizmor` (security audit of GitHub Actions workflows) runs
  locally as a path-aware gate step and in CI with `actionlint`; both are
  MIT-licensed and keyless. Every finding they raised on the existing
  workflows was fixed in the same change: no persisted checkout
  credentials, job-level permissions, no cache in publishing jobs,
  expressions passed through `env`, every action pinned to a commit.
- **Static analysis:** Semgrep Community Edition (LGPL, no account) with the
  Python, TypeScript and GitHub Actions rulesets, blocking. CodeQL was
  considered and rejected: free on public repositories but its engine is
  not open source. Suppressions are `# nosemgrep` on the matched line with
  the reason on the line above.
- **Dependencies:** `actions/dependency-review-action` on pull requests
  fails on a high-severity advisory or a copyleft license (GPL, AGPL,
  SSPL). `npm audit --audit-level=high` runs in a nightly job only; on pull
  requests it would be noise.
- **Frontend:** ESLint through `@nuxt/eslint-config` over the console, the
  platform layer, the client, and the tests; the vendored shadcn-vue
  catalogue is not linted. Nuxt's routed files (`pages/`, `layouts/`) are
  exempt from the multi-word component name rule by configuration.
- **Required checks on `main`** become `python`, `python-next`, `privacy`,
  `pr-hygiene`, `platform`, `docs`, `workflows`, `semgrep`, and
  `dependency-review`, all path-filtered or cheap. `audit (nightly)` is
  not a check.

**Consequences.** The local gate for a kernel change still finishes in
under a minute; the wheel and zizmor steps add a few seconds when their
trees change. A warning in a dependency now fails the suite the day it
appears. The S-rule exceptions name the production asserts that should
become explicit raises; that is kernel work and is tracked as a follow-up.

## Amendment 2026-11-11 (c) — preserve validation, reduce repeated waiting

**Context.** PR metadata events restarted all code checks, while platform checks
executed independently runnable commands in sequence. Workflow path lists and
local gate paths could disagree. The maintainer requested one remediation PR
without reducing quality (WU-106).

**Decision.** Metadata validation has its own workflow and concurrency group.
Required jobs remain directly in their event workflows with the original stable
names. Title/body edits rerun affected checks; avoiding those reruns is deferred.
Skipped reusable callers were rejected after the live rollout left required
checks pending despite historical successful jobs. Conditional expressions in
job names are prohibited; the Python matrix name is evaluated without a job-level
skip condition. Ready/draft transitions do not restart code validation. Every
new revision still receives affected validation, including drafts; base retargets
force full validation.

`ci_scope.py` owns conservative suite dependencies for CI, local optional gate
steps and PR evidence checks. Full Git diffs include both sides of renames and
deleted files; shared inputs select their consumers. Unknown paths or missing
history run everything; selector execution errors fail the job. Nightly/manual
full runs supplement, never replace, pre-merge checks. Kernel and spec changes
select the platform conservatively.

The platform executes backend and frontend lanes concurrently with separate
logs and ordered dependencies. Browser tests follow the production build. Both
Python versions and all existing checks remain. Timing reports distinguish queue
time, elapsed time and summed runner usage. No result is cached across revisions.

**Enforcement.** The nine validations from amendment (b) remain unchanged.
The original contexts remain `python`, `python-next`, `platform`, `docs`,
`workflows`, `semgrep`, `dependency-review`, `privacy`, and `pr-hygiene`. The
read-only ruleset tool restores these names from the attempted caller prefixes,
preserving app bindings, other protections and strict up-to-date enforcement.
Live acceptance requires a `CLEAN` merge state, not only successful job records.
See [CI verification](../ci.md).

**Alternatives.** Disabling draft validation or moving affected integration to
nightly would weaken pre-merge assurance. Reusing green statuses across changed
bases risks stale evidence. Workflow-level path skipping can strand required
checks; unconditional skipped results under existing names can mask failures.

**Consequences.** Title/body edits still allocate affected code runners. Stable
required names restore compatibility with existing PRs; ready/draft events remain
limited to metadata/board work. Conservative classification may run extra suites. The impact policy and
routing expressions are covered by `scripts/tests/`; rollback changes scheduling
only and does not touch product data or contracts.
