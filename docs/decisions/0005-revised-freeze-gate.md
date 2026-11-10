# 0005 — Revised freeze gate: the modernization qualification

- **Status:** accepted (landed by the merge of PR #2 on 2026-11-10; written
  up here after the fact — the maintainer should reverse it by a new ADR if
  the merge was not meant as that decision)
- **Date:** 2026-11-10
- **Deciders:** maintainer (by merging WU-17), recorded by Claude Code

## Context

The July 2026 plan gated the v0.2 data-contract freeze on one proof: the
OpenAI `/responses` interface plus the migration-with-no-user-code-change
demonstration (horizon H1). WU-17 (PR #2) replaced that gate in prose:
`docs/architecture.md` §9 now defers to the
[core modernization plan](../plans/core-modernization.md), and
`docs/plans/horizon.md` states that `/responses` alone no longer qualifies a
freeze. No decision record was written, and `AGENTS.md` rule 2 kept the old
gate, so the instruction file and the constitution disagreed (review finding
F1 on PR #2). The reason behind the change is sound: ADR 0003 proposes
ordered interaction items for a later canonical revision, and freezing the
single-message response shape right before that proposal is exercised would
freeze the wrong thing.

## Decision

1. **Data contracts** (`ocai.core` vocabulary, the `ocai.chat` port and IR,
   their `spec/` schemas) freeze additive-only at the **first release after
   the modernization qualification is met**, as sequenced in
   `docs/plans/core-modernization.md`:
   - the ordered-item candidate (ADR 0003) exercised through dated migration
     edges with explicit, certified losses;
   - item-addressed streaming with fold parity (rule 7) on that revision;
   - an independently packaged plugin passing conformance from a wheel
     (WU-18 and WU-20, done);
   - the `/responses` interface and the migration proof (H1) — **still
     required, no longer sufficient**.
2. **Hook protocols, plugin ABI (`CatalogFragment`), profile keys, observer
   events** are unchanged: they freeze at v1.0 only after the `/responses`
   migration and one real cross-provider failover have been exercised
   through them.
3. **Wording on the single-message shape.** "Single message forever" becomes
   "single message in revision `2026-07`" in the architecture, the
   `ChatRequest` docstring, and the `chat.response` schema comment. The shape
   is unchanged; a later revision may adopt ADR 0003 through migration edges.
4. **Authority order.** `docs/architecture.md` states the gate; plan files
   sequence the work toward it; `AGENTS.md` rule 2 mirrors §9. A plan file
   never redefines a gate, and a gate never changes without an ADR.
5. **Version axes (rule 3).** The library semver `0.2` no longer implies the
   data-contract freeze; the freeze is a release gate, not a version number.

## Alternatives considered

- **Keep H1 as the sole gate.** Freezes the single-message response shape
  weeks before ADR 0003 proposes to reopen it; every downstream product would
  inherit a migration immediately after the freeze.
- **Freeze now, on the exercised M1–M3 surface.** The surface has one
  exercised capability and two interfaces; the ordered-item and plugin
  evidence the platform depends on does not exist yet.

## Consequences

- `AGENTS.md` rule 2, `docs/architecture.md` (status legend and §9), and
  `docs/plans/horizon.md` H1 are aligned to this ADR in the same PR.
- The **[frozen-candidate]** label keeps its meaning: freezes additive-only
  at the next release gate, which this ADR defines.
- The freeze review session the maintainer planned remains the last
  free-rename window and now precedes the qualification, not H1 alone.
