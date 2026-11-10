# Tasks

Every development command, one verb per job, grouped by domain. Generated
from the Taskfiles by `task tasks:readme`; do not edit by hand. Requires
[Task](https://taskfile.dev) (`brew install go-task` on macOS).

How to read a line: `task <domain>:<verb>` runs it; `-- ARGS` passes
arguments where the description shows them. `task` alone prints this list
from the live definitions; `task --summary <name>` prints one task's details.

Two rules hold for every task here, from `AGENTS.md`:

- the Taskfiles **wrap** the canonical commands and never add a check CI
  does not run — the gate has one definition, `scripts/check.py`
  (`task check`);
- every task that publishes anything (`pr:*`, `board:*`) runs the privacy
  guard first; a leak fails the task before `gh` is called.

For a coding agent: `task check` before every claim of done, `task
privacy:text -- FILE` before every PR body, review, or issue you post,
`task pr:draft` at the first commit of a WU so its card is In progress,
`task board:decision` instead of asking the maintainer in chat.

## Root — aliases and setup

| Task | Does |
|---|---|
| `task check` | The full gate, identical to CI (alias of py:check) |
| `task default` | List every task |
| `task env` | Activate an environment: copy .envs/.env.<ENV> to the root .env (task env -- <ENV>); with no argument, list the available ones |
| `task setup` | One-time setup for a fresh clone — environment, docs group, gh auth check |

## Python workspace — environment, lint, types, tests, the gate

| Task | Does |
|---|---|
| `task py:check` | The full gate — privacy guard, ruff, import contracts, pyright strict, mypy strict, pytest |
| `task py:check:fast` | The gate without tests (lint, contracts, types) |
| `task py:demo` | Flagship demo 1 — the cross-conversion fidelity report (no network) |
| `task py:echo` | Run the community plugin template's own suite in isolation |
| `task py:fmt` | Ruff format the tree (not enforced in CI yet — see ADR 0001) |
| `task py:fmt:check` | Report files ruff would reformat |
| `task py:imports` | Architecture §1 layer contracts (import-linter) |
| `task py:lint` | Ruff lint (includes the Google-convention docstring rules) |
| `task py:mypy` | Mypy strict only |
| `task py:pyright` | Pyright strict only |
| `task py:sync` | Create the environment and install the workspace distributions |
| `task py:test` | Pytest — invariants and conformance (pass -- -k expr to filter) |
| `task py:test:core` | Only the ocai-core suite |
| `task py:test:plugins` | Only the provider plugin suites (OpenAI, Anthropic) |
| `task py:types` | Strict typing — pyright then mypy (nothing may resolve to Unknown) |

## Zensical site — preview, build, link checks

| Task | Does |
|---|---|
| `task docs:build` | Render the static site into ./site (gitignored), exactly as the deploy job does |
| `task docs:check` | Build and fail on any warning (missing nav page, broken link) |
| `task docs:clean` | Remove the built site |
| `task docs:orphans` | List docs pages that are not in the zensical.toml nav |
| `task docs:serve` | Live preview at http://127.0.0.1:8000 (rebuilds on save) |

## Privacy guard — nothing from a session goes public

| Task | Does |
|---|---|
| `task privacy:check` | Scan commits ahead of origin/main and all tracked/untracked text files |
| `task privacy:range` | Scan an explicit commit range (task privacy:range -- A..B) |
| `task privacy:text` | Scan a file holding a PR body, review, or message before posting it (task privacy:text -- FILE) |

## Branches, worktrees, pull requests, reviews

| Task | Does |
|---|---|
| `task pr:checks` | Watch the checks of a PR until they finish (task pr:checks -- NN) |
| `task pr:draft` | Push and open a DRAFT PR for the current branch (task pr:draft -- "WU-NN: title" [PARENT_BRANCH]); stacked when a parent branch is given |
| `task pr:open` | Open a PR from a body file that was written against the template (task pr:open -- "title" BODYFILE) |
| `task pr:post-review` | Post a review file as a comment review after the privacy scan (task pr:post-review -- NN FILE) |
| `task pr:ready` | Mark the current branch's draft PR ready for review |
| `task pr:rebase` | Rebase the current branch onto origin/main and force-push with lease |
| `task pr:restack` | After the parent PR merged (squash), rebase this branch onto origin/main dropping the parent's commits (task pr:restack -- PARENT_BRANCH) |
| `task pr:review` | Review a PR in a scratch worktree with the full gate (task pr:review -- NN); see the review-pr skill |
| `task pr:stack` | New worktree + branch stacked on an unmerged WU branch (task pr:stack -- PARENT_BRANCH NEW_BRANCH) |
| `task pr:status` | Open PRs with merge state and the required checks |
| `task pr:worktree` | New worktree + branch from origin/main (task pr:worktree -- wu-NN-slug) |
| `task pr:worktree:rm` | Remove a worktree and its local branch after merge (task pr:worktree:rm -- wu-NN-slug) |

## The GitHub Project board — cards, sync, maintainer handoffs

| Task | Does |
|---|---|
| `task board:card` | Add a WU card now (task board:card -- "WU-NN: title"); the sync would create it anyway |
| `task board:decision` | Add a decision card in Blocked on maintainer (task board:decision -- "Decision: question" BODYFILE); see maintainer-handoff |
| `task board:gap` | Add a kernel-gap card mirroring a gaps.md row (task board:gap -- "Gap: what" BODYFILE) |
| `task board:open` | Open the board in the browser |
| `task board:set` | Set Owner and/or Tier on a WU card (task board:set -- WU-NN --owner Claude --tier "1 chat completeness and hosts") |
| `task board:sync` | Report plan ↔ PRs ↔ cards differences (exit 1 when out of sync) |
| `task board:sync:apply` | Create missing cards and set statuses from the facts |

## spec/ — schema and fixture validation

| Task | Does |
|---|---|
| `task spec:conformance` | Schema conformance of the dataclasses plus every plugin certification suite |
| `task spec:fixtures` | Count fixtures per edge directory |
| `task spec:fold` | The fold law and streaming suites (rule 7) |
| `task spec:unknown` | The total-decode vectors (rule 6) |
| `task spec:validate` | Validate every fixture under spec/fixtures against spec/schema |

## tasks

| Task | Does |
|---|---|
| `task tasks:check` | Fail if tasks/README.md is stale (run tasks:readme) |
| `task tasks:readme` | Regenerate tasks/README.md (the task catalogue every session reads) from the task definitions |
