# CI latency

Maintainer request: “Could you make all those changes in a single PR?”

## WU-106 — Reduce CI waiting without weakening validation

- **Status:** ✅ complete (PR #123)
- **Context:** PR metadata edits restart expensive validation; independent checks run
  sequentially and path policies differ between local verification and CI.
- **Goal:** Each relevant revision receives all required validation once, while metadata
  changes cannot restart, cancel, or overwrite code validation.
- **Scope:** Workflow routing, shared impact selection, platform check scheduling,
  workflow regression tests, timing reports, required-check reconciliation tooling,
  contributor guidance and ADR 0002.
- **Non-goals:** Kernel behavior, release cadence, runner migration, test removal,
  cross-commit result caching, and automatically merging this PR.
- **Acceptance:**
  - Metadata events cannot replace code results; base changes revalidate —
    `scripts/tests/test_ci_policy.py`.
  - Complete diffs, deleted and renamed files, shared dependencies and uncertain
    history select conservative coverage — `scripts/tests/test_ci_scope.py`.
  - Independent platform lanes retain all commands and propagate failures —
    `scripts/tests/test_check_platform.py`.
  - Required-check reconciliation preserves unrelated rules and reports drift —
    `scripts/tests/test_ci_rules.py`.
- **Done:** Routing, impact selection, scheduling and ruleset tests pass, the full
  applicable gate passes, and one PR contains the implementation and review evidence.
- **Deps:** Gate expansion (#113), ADR 0002.
- **Architecture:** none; development tooling does not change the runtime layers.
- **Integration:** Repository tooling selects the existing kernel/platform/docs gates;
  no runtime package imports development tooling.
- **Design sketch:**

  ```python
  affected(suite: str, changed: frozenset[str] | None) -> bool
  # None means uncertainty: run every suite.
  # Code validation uses its own check names and concurrency group.
  # Platform backend and frontend lanes execute independently.
  ```

- **Alternatives considered:** Disabling draft tests delays feedback; nightly-only
  integration weakens pre-merge assurance; caching green statuses risks stale evidence.
- **Freeze:** none; no public contracts, schemas, edges or stream shapes change.
- **Decision (validation):** Preserve validation coverage and strict up-to-date merge
  enforcement; amend ADR 0002 to specify metadata isolation and conservative selection.
- **Risks:** A false-negative selector could omit validation; regression cases,
  fail-open selection (run everything), and forced full runs bound that risk. Revert
  restores the previous scheduling without changing product data.
- **Open:** none.
- **Evidence:** 38 tooling regression cases pass; no fixtures or wire pairs added.
  Full gate baseline: `gate: 2018ee8` / `all checks passed.`; the final committed
  gate summary is pasted in PR #123. Both Python versions and all required live
  checks passed. A live body edit created no code/docs/board runner jobs and
  retained prior required code results. Platform timing on one installed local
  environment: 49.0s serial, 35.2s concurrent (not a population estimate).
  The live ruleset audit reported all nine desired checks already enforced.
- **Area:** tooling
- **Priority:** P1
- **Tier:** program
- **Owner:** Codex
