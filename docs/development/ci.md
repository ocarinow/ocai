# CI

Two checks are required on `main`: `ci` for the code and `pr` for the text of
the pull request. Each one is the last job of its workflow and fails when a
job it covers failed or was cancelled.

| Event | What runs |
|---|---|
| Open, reopen, or push a PR | The suites the change affects, then `ci`; the text checks, then `pr` |
| Edit the title or the body | The text checks and `pr` only. The code results of the commit stay as they are |
| Mark ready or draft | The text checks and `pr` |
| Push to `main` | The affected suites, the Release PR refresh, and the docs deployment when the site changed |
| Nightly or manual run | Every suite, whatever changed, plus the npm audit |

Nothing is published by a merge: a pre-release is dispatched by hand
([releasing](releasing.md)).

## How a change selects its suites

The first job of `ci.yml`, `changes`, runs `scripts/ci_scope.py` once. Every
suite job reads its flag and does not start when its suite is not affected.

| Files changed | Suites |
|---|---|
| `python/` | python (3.13 and 3.14), docs, semgrep |
| `spec/`, `examples/`, `.pre-commit-config.yaml` | python |
| `scripts/` | python, semgrep; `scripts/check_platform.py` also runs platform |
| `platform/` | platform, semgrep; the management contract also runs docs |
| `docs/` | docs |
| `.github/` | workflows, semgrep; a workflow file runs everything |
| `pyproject.toml`, `uv.lock`, runtime version files, the selection script | everything |
| Task definitions, change files, instruction files, agent settings | none |
| Anything not classified | everything |

A kernel change does not run the platform suite: the gateway declares no
dependency on the kernel packages and imports none. The nightly run covers
the rest. Add `python/` to the platform entry of `scripts/ci_scope.py` on the
day the gateway depends on the kernel.

Git reads the full base/head diff of the pull request; there is no file-count
cutoff, and a rename counts for its old and its new path. Uncertainty always
means more validation: an unclassified path, missing history, or a failure of
the selection job itself runs every suite. The suite conditions test for
`!= 'false'`, so an empty answer is not a skip.

## What each suite runs

- **python**: the git hooks from `.pre-commit-config.yaml` on the whole
  repository, at the commit and push stages, then the wheel inspection and the
  isolated plugin install. A contributor and CI run one definition of the
  checks. The change-file policy and the privacy guard on commits are left to
  the text checks, which know the pull request's base.
- **platform**: `scripts/check_platform.py`, with Docker, Node and the browser
  runtime.
- **docs**: the site build with zero warnings. `docs.yml` deploys it from
  `main`.
- **workflows**: zizmor and actionlint.
- **semgrep**: Semgrep Community Edition.
- **dependency-review**: every pull request.
- **pr-hygiene** and **privacy** (in `pr-metadata.yml`): the change-file policy,
  the title and body, the plan entries, and the privacy guard on commits, their
  identities, the text and the files.

## Required checks

The repository ruleset is external state. `scripts/ci_rules.py` reports
whether it requires exactly `ci` and `pr`, and writes the request body that
makes it so while keeping every other protection:

```bash
uv run python scripts/ci_rules.py --output /tmp/ocai-ruleset.json
gh api --method PUT repos/ocarinow/ocai/rulesets/26964282 --input /tmp/ocai-ruleset.json
uv run python scripts/ci_rules.py
```

Generate the body immediately before applying it. The individual job names
(`python`, `platform`, `docs`, …) still report, so a ruleset that requires
them keeps working; a job that did not start counts as passed.

A required check must come from a workflow that always starts. Filtering a
workflow with `on: paths` leaves its checks pending and blocks the merge,
which is why the selection happens inside `ci.yml`.

## Platform execution and measurement

The platform suite installs the gateway environment once, then runs
independent backend and frontend lanes concurrently. Each lane retains its own
ordered steps and log. Browser tests follow the production build and start a
real gateway; backend tests use disposable containers. Both lanes finish and
retain failure output; any failure fails the check. A missing Docker daemon is
a failure. `--no-tests` remains an explicitly incomplete local diagnostic mode.

Each platform run reports command and lane durations in the log and the
Actions summary. Compare the same checkout and environment with:

```bash
uv run python scripts/check_platform.py --serial
uv run python scripts/check_platform.py
```

`scripts/ci_timing.py` reads Actions measurements: queue time, workflow
elapsed time and summed runner time, with medians and P90.

```bash
uv run python scripts/ci_timing.py --created 2026-11-10..2026-11-10 --limit 20
```

Dependency downloads and browser binaries are cached by their lockfile keys;
installs, builds and tests execute freshly. Publishing jobs are not cached.
