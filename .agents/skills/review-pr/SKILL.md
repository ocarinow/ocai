---
name: review-pr
description: Review a pull request of ocai against the written rules — the honesty-reviewer role, run in a scratch worktree with the full gate, findings written to a file and posted when permitted. Use whenever asked to review a PR, before merging, or after a WU is implemented.
---

# Review a PR

The review is the `honesty-reviewer` role (`.agents/roles/honesty-reviewer.md`):
findings against the eighteen rules, the freeze boundaries, declared versus
runtime loss, and privacy. This skill is the mechanics around it.

## 1. Fetch into a scratch worktree, never the shared checkout

```bash
task pr:review -- NN      # scratch worktree at the PR head, diff stat, the full gate
cd ../ocai-worktrees/review-pr-NN
gh pr view NN --json title,body,baseRefName,headRefName,files
git diff origin/main...HEAD
```

## 2. Run the gate exactly as CI does

```bash
uv sync -q && uv run python scripts/check.py
```

Pin pyright to the repo config if the scratch path has a stray config above
it (`uv run pyright -p pyproject.toml`). Report the summary block verbatim.
A failing gate is a finding, but say whether it is pre-existing on `main`
or introduced by the PR.

## 3. Check the card and the entry

- The PR body says `Closes #N` and `N` is the WU's card (`work-unit` label,
  title `WU-NN: …`). No card → finding (the board cannot track it).
- The WU entry in `docs/plans/` has exactly one **Done** bullet and the PR
  satisfies it. Two outcomes → finding (rule 17).
- The plan row flips to ✅ in this PR; the architecture sections the entry
  names are updated in this PR; a lasting decision has an ADR numbered
  after rebase.

## 4. Review in the role's order

Privacy first (a session link, AI footer, trailer, agent id, or home path
anywhere in commits, title, body, or files is do-not-ship on its own), then
declared-vs-runtime loss, silence, total decode, streaming parity, freeze
boundaries, credentials, tests, constitution drift. Every finding cites a
rule or an architecture section, a `file:line`, and the concrete input that
exposes it. Unconfirmed items are labelled as such.

## 5. Write the review to a file, then post if permitted

Save the review to a file first (the maintainer can post it if posting is
blocked), run the privacy guard on it, then:

```bash
task pr:post-review -- NN <file>     # privacy scan, then a comment review
```

End with one verdict line (ship / ship after fixes / do not ship) and the
gate summary. Remove the worktree:
`git worktree remove --force <scratch>/review-pr-NN`.

## 6. Do not

Edit the PR's files, push to its branch, approve on the author's behalf,
or merge. Review is read-only; the author fixes, the maintainer merges.
