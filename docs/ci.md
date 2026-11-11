# CI without repeated waiting

Code validation and PR administration run independently. Metadata checks retain
privacy and template enforcement while code results remain attached to the tested
revision. Both Python interpreters, packaging, strict typing, security analysis,
real service integration and browser coverage remain pre-merge checks when relevant.

| Event | Work |
|---|---|
| Open, reopen, or push a PR | All suites affected by its complete diff; metadata checks |
| Edit title/body | Metadata checks; title changes also refresh the board |
| Mark ready or draft | Metadata checks and board refresh |
| Change base branch | Full code validation, metadata checks and board refresh |
| Push main | Affected validation and existing deployment/release workflows |
| Nightly or manual full run | Full code suites, independent of paths |

A body edit still appears as an Actions event, but code jobs are skipped **under
separate names** containing `(metadata event)`. GitHub may show the unevaluated
name expression for a job skipped before scheduling. These jobs allocate no runners and
cannot overwrite `python`, `platform`, or another required code result. Their
concurrency group is separate too: editing prose cannot cancel running tests.
New code cancels superseded PR code runs. Main code runs use unique groups; scheduled docs builds have a separate group. Pages
publishing remains serialized and is never cancelled in flight.

## Impact selection

`scripts/ci_scope.py` owns the suite dependency map used by Actions, the local
gate and PR verification-evidence checks. Git reads the full PR base/head diff;
there is no API file-count cutoff. Renames include the old and new paths, and
local verification includes staged, unstaged and untracked files. Use
`uv run python scripts/check.py --base origin/<parent>` for stacked work.

Shared runtime versions, root dependency/configuration files and CI policy
changes force all suites. Kernel or language-neutral spec changes also select
the platform, so consumers remain covered as they adopt kernel packages. Unknown
paths and unavailable history run everything. A selector execution failure fails
the job. `--all` forces every local step; Actions manual dispatch and nightly
runs bypass selection. Neither workflow-level path skipping nor cached green
statuses are used for required code checks.

The local gate intentionally retains its cheap always-on kernel checks. Optional
checks use the same dependency map as CI. The dependency-review job remains
unconditional on code PR events because it is cheap and security-sensitive.

## Platform execution and measurement

The platform gate installs the gateway environment once, then runs independent
backend and frontend lanes concurrently. Each lane retains its own ordered steps
and log. Browser tests follow the production build and start a real gateway;
backend tests use disposable containers. Both lanes finish and retain failure
output; any failure fails the platform check. A missing Docker daemon is a
failure. `--no-tests` remains an explicitly incomplete local diagnostic mode.

Each platform run reports command and lane durations in the log and Actions
summary. Compare the same checkout and environment with:

```bash
uv run python scripts/check_platform.py --serial
uv run python scripts/check_platform.py
```

Read-only Actions measurements separate queue time, workflow elapsed time, and
summed runner time, and report medians and P90 with sample sizes:

```bash
uv run python scripts/ci_timing.py --created 2026-11-10..2026-11-10 --limit 20
uv run python scripts/ci_timing.py --created 2026-11-11..2026-11-11 --branch wu-106-ci-latency --limit 20
```

Use comparable change types and outcome distributions before interpreting speed
changes. A single run is acceptance evidence, not a statistically reliable speed
claim. Workflow completion excludes human review and other required workflows.
Dependency downloads and browser binaries are cached by their existing lockfile
keys; installs, builds and tests execute freshly. Publishing jobs remain uncached.

## Rollout and required checks

Regression tests under `scripts/tests/` exercise the checked-in routing
expressions, full diffs, renames/deletions, uncertain history, shared configuration,
large diffs, platform failures and ruleset preservation. Run the complete gate,
then verify a PR body edit produces metadata jobs without starting or replacing
required code checks. This was verified on PR #123: a body edit allocated no
code/docs/board runners and preserved the previous code-check results. A ready transition must do the same. Base changes force a
fresh full validation.

The desired checks are `python`, `python-next`, `privacy`, `pr-hygiene`,
`platform`, `docs`, `workflows`, `semgrep`, and `dependency-review`. A live read-only audit during WU-106 found all nine already required. The repository
ruleset is external state and cannot be activated by a source-code PR alone.
After the workflow change merges, prepare and review the minimal update:

```bash
uv run python scripts/ci_rules.py --output /tmp/ocai-ruleset.json
# Exit 1 means drift; the generated JSON preserves other rules and check bindings.
gh api --method PUT repos/ocarinow/ocai/rulesets/26964282 --input /tmp/ocai-ruleset.json
uv run python scripts/ci_rules.py
```

Do not apply a stale generated body: read and prepare again immediately before
application. The update adds missing checks, keeps unrelated protections, and
preserves strict up-to-date enforcement. It never removes checks or bypass rules.

## Working efficiently

Prepare the PR title and body together and submit one metadata update. Push a
coherent revision after relevant local checks; keep the first draft visible as
required by the work-unit process. Restack a child once after its parent merges,
then validate against the new base. A passing result from a different revision or
base is not reusable evidence. Draft PRs continue receiving affected validation.
