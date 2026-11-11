# Work unit entry template

Every work unit (WU) is one entry in a plan file under `docs/plans/`, written
with the `wu-define` skill and reviewed in a PR. The entry is the definition;
the board card on the GitHub Project is **generated from it** by
`scripts/board_sync.py` (body and fields), so what is written here is what
the maintainer reads on the board, and the PR body is pre-filled from it by
`task pr:body`. One heading, one `Done`, bullets in this order.

Two kinds of bullet:

- **Mandatory** bullets are present on every entry. `scripts/board_sync.py
  check` (a gate step) fails a ⬜ or 🔄 row whose entry lacks one, and fails a
  ✅ row without **Evidence**. Write "none" rather than omitting a bullet: a
  missing bullet is an oversight, "none" is a decision.
- **Optional** bullets (marked *optional* below) are added when they carry
  information; when present they must have content.

A filled example that passes the check is
[`WU-EXAMPLE.md`](WU-EXAMPLE.md); copy it rather than this skeleton.

```markdown
## WU-NN — <imperative title, identical to the plan table row>

- **Status:** ⬜ defined | 🔄 in progress (PR #N) | ✅ complete (PR #N).
  One token first, so the board can parse it; the PR number once one exists.
- **Context:** Why now. The situation today, who is blocked or at risk, and
  what stays broken if this never lands. Cite the gap row (`gaps.md` G-NN),
  the program paragraph, or the maintainer request it comes from.
- **Goal:** What exists when this is done, for a reader who has not seen the
  plan, and why it matters to the kernel or the platform. One paragraph.
- **Scope:** Files and surfaces touched (modules, fixtures, schemas, docs),
  with a rough size.
- **Non-goals:** What a reader might expect here that is deliberately left
  out, and where it lives instead (another WU, the horizon, or "never,
  because …"). One line each.
- **Acceptance:** One line per observable check, each ending with the test
  module, fixture, or recorded pair that proves it:
  - <behavior> — `python/packages/<dist>/tests/test_<x>.py::test_<y>`
  - <behavior> — `spec/fixtures/<edge>/<case>.json`
- **Done:** The Acceptance list in one sentence, phrased as the test that
  passes.
- **Deps:** WU numbers that must be ✅ first, ADRs that must be accepted, or
  "none".
- **Architecture:** §n, §m — the `docs/architecture.md` sections this entry
  touches and updates in the same PR, or "none" for a change with no
  structural footprint (docs, tooling).
- **Integration:** Where it lands in the structure and how it connects.
  - Layer: `ocai.core` | capability package | `ocai.convert` | `ocai.runtime`
    | `ocai.wire` | plugin `ocai.<provider>.<interface>` | satellite dist |
    platform service | tooling — with the dependency arrows it respects (§1).
  - Modules: new and changed modules, one line each.
  - Flow: the request/response or data path through existing objects
    (encode → policy hooks → host → credential → send → decode …).
  - Diagram (recommended for anything touching more than one layer): a
    fenced ```mermaid block — classDiagram, sequenceDiagram, or flowchart —
    showing only the objects this WU adds or changes.
- **Design sketch:** A fenced code block with the new or changed surface as
  it will read in code: dataclass fields, function signatures, a schema
  fragment, an endpoint shape, a SQL table, a CLI flag. For a change with no
  code surface (docs, plan, process) write "n/a: no code surface" and say
  what the deliverable's shape is instead (a table of contents, a template).
  This is the bullet a reviewer reads before the diff.
- **Before / after** *(optional)*: a table with one row per field or behavior
  that changes: today, after this WU, what makes the difference observable.
  Use it when the WU changes an existing behavior rather than adding one.
- **Alternatives considered** *(optional, required when a Decision bullet
  below is not backed by an ADR)*: one line per rejected option with its
  benefit and cost, or "settled by ADR NNNN".
- **Reproduce** *(optional)*: a command or snippet that shows the gap today
  without network, credentials, or SDK mocks, and the output expected after
  the WU. It becomes the first acceptance test.
- **Freeze:** none | additive change to <frozen-candidate surface> under ADR
  NNNN | provisional surface.
- **Decision (<topic>):** one bullet per decision already settled, with the
  ADR, survey page, or prior WU that settled it. Decisions already made are
  not re-litigated by the implementer.
- **Risks:** What could go wrong, how the change bounds it, and how it is
  rolled back (a revert is enough, or a migration or re-projection is
  needed).
- **Dependency impact** *(optional)*: which WUs or open PRs this blocks,
  unblocks, or re-sequences, stated as plan facts, not inferred.
- **Open:** none, or the question that blocks starting (then the WU is not
  ready; file it with `task board:decision`).
- **Evidence:** Filled at completion, empty until then. The gate summary's
  final `gate: <sha> …` line, the number of tests added, the fixtures and
  wire pairs added, and anything verified by hand that the gate does not
  cover.
- **Area:** core | chat IR | convert | runtime | wire | plugin: openai |
  plugin: anthropic | plugin: deepseek | plugin: other | spec | docs |
  platform | satellite | tooling
- **Priority:** P0 | P1 | P2 | P3 (from the capability roadmap or the program)
- **Tier:** program | 1 … 6 (the roadmap's sequencing tier)
- **Owner:** Codex | Claude | maintainer | unassigned
```

## How the card is built

| Card | From |
|---|---|
| Title | the heading |
| Body | Status, Context, Goal, Scope, Non-goals, Acceptance, Done, Deps, Architecture, Integration (diagram included), Design sketch, Before / after, Alternatives considered, Reproduce, Freeze, Decision, Risks, Dependency impact, Open, Evidence, then links to the plan entry and the PR |
| Status | derived: no PR → Defined; draft PR titled `WU-NN: …` → In progress; ready → In review; merged or row ✅ → Done; parked by the maintainer → Blocked on maintainer |
| Program | the plan table's Milestone column |
| Area, Priority, Tier, Owner | the bullets above (Owner may also be set with `task board:set`) |
| Kind | WU (decision and gap cards are added separately) |
| PR, Plan | the PR URL once one exists; the GitHub URL of the entry |

## How the PR body is built

`task pr:body -- WU-NN` fills `.github/PULL_REQUEST_TEMPLATE.md` from the
entry: **Why** from Context and Goal, **What did not change** from Non-goals,
**Design** from Design sketch, **Before / after** and **Try it** from the
matching bullets, **Evidence** from Acceptance (one checkbox per item), the
**Contracts** architecture sections from Architecture. The implementer edits
the result; the generator saves the retyping, it does not replace the
thinking.

Size rule (`wu-define` §4): two outcomes, two capabilities, or more than
about 40 non-mechanical files means two WUs.
