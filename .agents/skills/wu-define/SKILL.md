---
name: wu-define
description: Turn a horizon item, a gap entry, or a maintainer request into a fully specified ocai work unit (WU) before any code is written — scope, done-criteria, architecture sections, census/fixture/freeze impact, decisions already made. Use whenever asked to "plan", "split", "define", or "start" work that has no WU entry yet, or when a WU entry lacks a Done bullet.
---

# Define a work unit

A WU is one PR's worth of work with a testable **Done** bullet. Nothing in
this repo starts from a sentence in chat; it starts from a WU entry in
`docs/plans/`. This skill produces that entry. It does not write code.

The failure it prevents: an agent that reads a goal, infers the rest, and
lands four units of work in one unreviewable stack. If the answers below are
not known, the WU is not ready, and saying so is the correct output.

## 1. Locate the source

One of:

- a paragraph in `docs/plans/horizon.md` or the current program file;
- a row in `docs/plans/gaps.md` (carry its evidence over verbatim);
- a maintainer request (quote it in the entry's first line).

Read `AGENTS.md` and the `docs/architecture.md` sections the source names.
Check `docs/decisions/` for an ADR on the same surface: a settled decision is
not reopened by a WU.

## 2. Answer these before writing the entry

Work through all of them. Write "none" explicitly where that is the answer;
an unanswered question is a reason to stop and ask the maintainer.

| Question | Why it matters |
|---|---|
| What is the **one** observable outcome? State it as a test that passes at the end. | It becomes the **Done** bullet. If there are two outcomes, there are two WUs. |
| Which `docs/architecture.md` sections does it touch, by number? | Those sections are updated in the same PR (blueprint law). |
| Which shapes/nodes/edges change? New edge, changed census, new fixture kind? | Each new or changed edge follows the `add-edge` skill; the fixtures and census are part of the WU, never a follow-up. |
| Does it touch a frozen-candidate surface (core vocabulary, chat port, chat IR, their schemas)? | Before v0.2: allowed, needs an ADR. After v0.2: additive only. |
| Does it add a first-class field, an extension key, or a `provider_options` knob? | The three-lane law (§3.5) decides which; a first-class field needs ≥2–3 interfaces with congruent semantics. |
| Does it stream? | Then it ships the delta type, fold law, and fold triples in the same change (rule 7). |
| Does it add a dependency? | `ocai.core` takes none (rule 11); plugins never take wire/httpx (§7); no provider SDK anywhere (rule 12). |
| Which files does it own? Does another open WU touch the same files? | Overlap means sequencing or a worktree, decided now, not at merge time. |
| What is explicitly **out** of scope? | Written down so the implementer does not drift and the reviewer can check. |
| What decisions are already made (by ADR, by a prior WU's Decision bullet, by the maintainer)? | Listed so they are not re-litigated. |
| What decision is **still open** that would change the shape? | A WU with an open shape decision is not ready; resolve it (ADR) or scope it out. |

## 3. Write the entry

In the milestone or program file under `docs/plans/`, matching the existing
format:

```markdown
## WU-NN — <imperative title>

- **Scope:** <what is built, which files, which fixtures; what is out>
- **Done:** <the observable outcome, phrased as the test that passes>
- **Deps:** <WU numbers that must be ✅ first, or "none">
- **Architecture:** §<n>, §<m> (sections updated in the same PR)
- **Freeze:** <none | pre-v0.2 change to <surface>, ADR NNNN | additive>
- **Decision (<topic>):** <each decision already made, one bullet each>
- **Open:** <none, or the question that blocks starting>
```

Add the row to the table in `docs/plans/README.md` with status ⬜.

## 4. Size check

A WU is too big if any of these is true: more than one **Done** bullet,
more than one capability, a new edge *and* a new interface, or an estimated
diff over roughly 40 files that is not mechanical. Split it; the split is the
deliverable of this skill, and the entries list their dependencies.

## 5. Hand-off and the board card

The entry PR is small and reviewable on its own. Implementation starts in a
separate PR via the `wu-session` skill, after the entry is merged or the
maintainer approves it in place.

Once the entry is on `main`, the WU gets its **board card**: an issue from
the `work-unit` template whose title is exactly `WU-NN: <title>` and whose
body is only the plan link, the owner, and the tier. The board sync
(`scripts/board_sync.py`, run by CI on every push to `main` and nightly)
creates missing cards from the plan table and keeps their status in step
with the linked PR; to create it immediately:

```bash
gh issue create --template work-unit.yml --title "WU-NN: <title>" --body-file <file>
```

Scope never lives on the card. If the entry changes, the plan file changes
in a PR; the card only links to it.
