# Work unit entry template

Every work unit (WU) is one entry in a plan file under `docs/plans/`, written
with the `wu-define` skill and reviewed in a PR. The entry is the definition;
the board card on the GitHub Project is **generated from it** by
`scripts/board_sync.py` (body and fields), so what is written here is what
the maintainer reads on the board. One heading, one `Done`, bullets in this
order. Omit a bullet only when it truly does not apply; write "none" rather
than leaving a reader to guess.

```markdown
## WU-NN — <imperative title, identical to the plan table row>

- **Goal:** One paragraph for a reader who has not seen the plan: what
  exists when this is done and why it matters to the kernel or the platform.
- **Scope:** Files and surfaces touched (modules, fixtures, schemas, docs);
  rough size. Then what is explicitly OUT of scope.
- **Done:** The single observable outcome, phrased as the test that passes.
- **Deps:** WU numbers that must be ✅ first, ADRs that must be accepted, or
  "none".
- **Architecture:** §n, §m — the `docs/architecture.md` sections this entry
  touches and updates in the same PR.
- **Integration:** Where it lands in the structure and how it connects.
  - Layer: `ocai.core` | capability package | `ocai.convert` | `ocai.runtime`
    | `ocai.wire` | plugin `ocai.<provider>.<interface>` | satellite dist |
    platform service — with the dependency arrows it respects (§1).
  - Modules: new and changed modules, one line each.
  - Flow: the request/response or data path through existing objects
    (encode → policy hooks → host → credential → send → decode …).
  - Diagram (optional, recommended for anything touching more than one
    layer): a fenced ```mermaid block — classDiagram, sequenceDiagram, or
    flowchart — showing only the objects this WU adds or changes.
- **Freeze:** none | additive change to <frozen-candidate surface> under ADR
  NNNN | provisional surface.
- **Decision (<topic>):** one bullet per decision already settled, with the
  ADR, survey page, or prior WU that settled it.
- **Open:** none, or the question that blocks starting (then the WU is not
  ready; file it with `task board:decision`).
- **Area:** core | chat IR | convert | runtime | wire | plugin: openai |
  plugin: anthropic | plugin: other | spec | docs | platform | satellite |
  tooling
- **Priority:** P0 | P1 | P2 | P3 (from the capability roadmap or the program)
- **Tier:** program | 1 … 6 (the roadmap's sequencing tier)
- **Owner:** Codex | Claude | maintainer | unassigned
```

## How the card is built

| Card | From |
|---|---|
| Title | the heading |
| Body | Goal, Scope, Done, Deps, Architecture, Integration (diagram included), Freeze, Decision, Open, then links to the plan entry and the PR |
| Status | derived: no PR → Defined; draft PR titled `WU-NN: …` → In progress; ready → In review; merged or row ✅ → Done; parked by the maintainer → Blocked on maintainer |
| Program | the plan table's Milestone column |
| Area, Priority, Tier, Owner | the bullets above (Owner may also be set with `task board:set`) |
| Kind | WU (decision and gap cards are added separately) |
| PR, Plan | the PR URL once one exists; the GitHub URL of the entry |

Size rule (`wu-define` §4): two outcomes, two capabilities, or more than
about 40 non-mechanical files means two WUs.
