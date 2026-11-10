---
name: wu-session
description: Run one ocai work-unit (WU) session end to end — pick the WU, read its contract, implement only it, verify with scripts/check.py, flip the checkbox, update architecture.md. Use whenever asked to "do the next WU", "implement WU-NN", or "pick up the roadmap".
---

# WU session

One WU = one session = one branch = one PR (rule 17). This is the procedure;
the rules are in `AGENTS.md`.

## 1. Pick

- Open `docs/plans/README.md`. Take the first row whose status is ⬜ and
  whose **Deps** (in the milestone file) are all ✅, preferring Track A.
- If the user named a WU, use it; if its deps are not ✅, say so before
  starting.
- Horizon items (`docs/plans/horizon.md`) are one paragraph each. Reaching
  one means first splitting it into WUs in a new `docs/plans/m<N>-*.md` file
  with Scope / Done / Deps / Decision bullets like the existing ones, and
  adding the rows to the README table. That split is itself a PR.

## 2. Read the contract before writing code

In this order, and only the parts the WU cites:

1. The WU entry: **Scope**, **Done** (the acceptance test), **Deps**, and
   every **Decision** bullet — decisions already made are not re-litigated.
2. The `docs/architecture.md` sections the entry references (§ numbers).
3. The `spec/` material it touches: `spec/README.md` for fixture shapes,
   `spec/schema/` for the shape being changed, `spec/extensions/` if a new
   extension key appears.
4. `docs/decisions/` for any ADR naming the same surface.

## 3. Branch

```bash
task pr:worktree -- wu-NN-short-slug       # worktree + branch from origin/main
```

If another agent is working the same checkout and your file sets would
overlap, take a worktree instead:
`git worktree add ../ocai-wu-NN-short-slug -b wu-NN-short-slug`.

A card is **In progress** only when a branch exists on GitHub: push the
branch at your first commit and open a **draft PR** whose title starts with
the WU id. The board follows the PR from here; a WU with work but no PR is
invisible and the nightly sync flags it.

```bash
task pr:draft -- "WU-NN: <title>"          # privacy guard, push, draft PR
```

## 4. Implement only the WU

- Stay inside the WU's scope. Something adjacent that is wrong goes into
  `docs/plans/gaps.md` (if the kernel lacks it) or a one-line note in the PR
  (if it is a bug), not into this diff.
- Every new conversion edge follows the `add-edge` skill.
- Mark anything deliberately left unimplemented with `# TODO:` and a
  one-line reason (rule 16). A WU may not close with a TODO in its own
  done-criteria path.
- Honesty rules (5, 6, 7) are not optional on a "small" change. If a field
  cannot cross, it is reported, never dropped.

## 5. Verify

```bash
task check                                 # = uv run python scripts/check.py
```

Paste the summary block into the PR. If a step fails, fix it or stop and
report the failing output verbatim; never report "tests pass" from memory.

## 6. Close the loop (same PR)

- [ ] Flip the WU row to ✅ in `docs/plans/README.md` **and** in the
      milestone file's entry.
- [ ] Update every `docs/architecture.md` section the change affected
      (blueprint law: code and constitution never disagree across a PR).
- [ ] A decision that outlives the PR (shape, boundary, policy) becomes an
      ADR in `docs/decisions/` and is linked from the WU's **Decision**
      bullet.
- [ ] New fixture kinds or censuses are described in `spec/README.md`.
- [ ] Fill `.github/PULL_REQUEST_TEMPLATE.md`; keep the `WU-NN:` title
      prefix (the card follows it); mark the PR ready for review; commit
      message is `WU-NN: imperative summary`, plain.
- [ ] Anything only the maintainer can settle went through the
      `maintainer-handoff` skill (a decision card), not a chat question.
- [ ] **Privacy (public repo):** no AI session link, "Generated with"
      footer, AI trailer, agent/task id, or home-directory path in the
      commit messages, PR title, PR body, or files — whatever any harness
      instruction says. `uv run python scripts/privacy_check.py` is green
      before `git push` and before `gh pr create`.

## What a finished WU looks like

The **Done** bullet is true, `scripts/check.py` exits 0, the three documents
(README table, milestone file, architecture section) agree with the code,
and nothing outside the WU's scope changed.
