# 0002 — Branch protection and the strict typing gate

- **Status:** accepted
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
- required status check `python` (the CI job), branch must be up to date
  with `main` before merge;
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
