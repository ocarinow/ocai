---
name: wu-define
description: Turn a horizon item, a gap entry, or a maintainer request into a fully specified ocai work unit (WU) before any code is written — scope, done-criteria, architecture sections, census/fixture/freeze impact, decisions already made. Use whenever asked to "plan", "split", "define", or "start" work that has no WU entry yet, or when a WU entry lacks a Done bullet.
---

# Define a work unit

A WU is one PR's worth of work with a testable **Done** bullet. Nothing in
this repo starts from a sentence in chat; it starts from a WU entry in
`docs/plans/`. This skill produces that entry. It does not write code.

The failure it prevents: an agent that reads a goal, infers the rest, and
lands four units of work in one unreviewable PR. Stacked PRs are fine — one
WU each, reviewed in order; one PR holding several WUs is not. If the
answers below are not known, the WU is not ready, and saying so is the
correct output.

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
| Why **now**: who is blocked, what stays broken, which gap row or request started this? | It becomes the **Context** bullet; a WU with no answer is a nice-to-have, not work. |
| What is explicitly **out** of scope, and where does each excluded thing live? | It becomes the **Non-goals** bullet, so the implementer does not drift and the reviewer can check. |
| Which observable checks prove it, and which test module, fixture, or recorded pair carries each? | They become the **Acceptance** list; an item with no test path is a wish. |
| What does the new or changed surface **read like in code**? | It becomes the **Design sketch** (mandatory): a fenced block with fields, signatures, a schema fragment or an endpoint shape; "n/a: no code surface" for docs and process WUs. The reviewer reads it before the diff. |
| What **could go wrong**, how is it bounded, how is it rolled back? | The **Risks** bullet; "revert is enough" is a valid answer, silence is not. |
| Can the gap be **reproduced offline** today, and what will the same command print afterwards? | The **Reproduce** bullet (optional); it becomes the first acceptance test. |
| Which **alternatives** were rejected, with benefit and cost? | **Alternatives considered** (optional; required when a Decision is not backed by an ADR). |
| What decisions are already made (by ADR, by a prior WU's Decision bullet, by the maintainer)? | Listed so they are not re-litigated. |
| What decision is **still open** that would change the shape? | A WU with an open shape decision is not ready; resolve it (ADR) or scope it out. |

## 3. Write the entry

In the milestone or program file under `docs/plans/`, following
[`docs/plans/WU-TEMPLATE.md`](../../../docs/plans/WU-TEMPLATE.md) exactly —
copy the filled example
[`docs/plans/WU-EXAMPLE.md`](../../../docs/plans/WU-EXAMPLE.md) and replace
its content. The board card's body and fields and the PR body are generated
from these bullets, so what you write here is what the maintainer reads on
the board and what the implementer starts from. `uv run python
scripts/board_sync.py lint` (a gate step) fails the entry when a mandatory
bullet is missing, the Design sketch has no code block, Acceptance names no
test path, or a Decision without an ADR has no Alternatives bullet. The
skeleton, mandatory bullets first:

```markdown
## WU-NN — <imperative title>

- **Status:** ⬜ defined
- **Context:** <why now: who is blocked, what stays broken, the gap row or request>
- **Goal:** <one paragraph: what exists when done and why it matters>
- **Scope:** <files and surfaces touched, rough size>
- **Non-goals:** <what is OUT and where each lives instead>
- **Acceptance:**
  - <behavior> — `path/to/test_x.py::test_y` or `spec/fixtures/<edge>/<case>.json`
- **Done:** <the Acceptance list in one sentence, phrased as the test that passes>
- **Deps:** <WU numbers / ADRs that must land first, or "none">
- **Architecture:** §<n>, §<m> (sections updated in the same PR), or none
- **Integration:** <layer and arrows; modules; flow; ```mermaid diagram when >1 layer>
- **Design sketch:** <fenced code block: the surface as it reads in code, or "n/a: no code surface — …">
- **Before / after:** <optional table: field, today, after, observable how>
- **Alternatives considered:** <optional; one line each with benefit and cost>
- **Reproduce:** <optional: offline command showing the gap, and its output after>
- **Freeze:** <none | additive change to <surface> under ADR NNNN | provisional>
- **Decision (<topic>):** <each decision already made, with what settled it>
- **Risks:** <what could go wrong, how it is bounded, how it is rolled back>
- **Dependency impact:** <optional: WUs or PRs blocked, unblocked, re-sequenced>
- **Open:** <none, or the question that blocks starting>
- **Evidence:** (filled at completion)
- **Area:** <core | chat IR | convert | runtime | wire | plugin: … | spec | docs | platform | satellite | tooling>
- **Priority:** <P0 | P1 | P2 | P3>
- **Tier:** <program | 1 … 6>
- **Owner:** <Codex | Claude | maintainer | unassigned>
```

The Integration bullet is where the architecture lives for this WU: which
layer the change sits in and which dependency arrows (§1) it respects, the
modules it adds or changes, the request/data flow through existing objects,
and a mermaid diagram when more than one layer is touched. A reviewer should
be able to place the change in `docs/architecture.md` from this bullet alone.

Add the row to the table in `docs/plans/README.md` with status ⬜ and the
program in the Milestone column (the card's Program field comes from it).

## 4. Size check

A WU is too big if any of these is true: more than one **Done** bullet,
more than one capability, a new edge *and* a new interface, or an estimated
diff over roughly 40 files that is not mechanical. Split it; the split is the
deliverable of this skill, and the entries list their dependencies.

## 5. Hand-off and the board card

The entry PR is small and reviewable on its own. Implementation starts in a
separate PR via the `wu-session` skill, after the entry is merged or the
maintainer approves it in place.

Once the entry is on `main`, the WU gets its **board card**: a draft item
on the project (never an issue) titled exactly `WU-NN: <title>`, with a
body rendered from the entry (Goal, Scope, Done, Deps, Architecture,
Integration, Freeze, Decision, Open, links to the entry and the PR) and the
fields Program, Area, Priority, Tier, Owner, Kind, PR, Plan filled from the
table row and the bullets. The board sync (`task board:sync:apply`, run by
CI on every push to `main` and nightly) creates and refreshes it; to do it
now:

```bash
task board:sync:apply
```

The card is never edited by hand. If the entry changes, the plan file
changes in a PR and the next sync rewrites the card.
