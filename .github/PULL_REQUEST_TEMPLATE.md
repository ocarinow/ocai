## Work unit

WU-__ — <title from docs/plans/>. Entry: docs/plans/<file>.md#wu-__. One WU per PR (rule 17); housekeeping PRs replace this line with `<Topic> — <one line>`.
<!-- Stacked on #N  (keep this line only when the base branch is not main) -->

## Why

<The entry's Context and Goal in two to four sentences: the problem today, who it affects, what exists when this merges. A reviewer should know what this solves before reading a line of the diff.>

## What changed

<The behavior, by layer or module, not the file list. Name every new or changed public surface (types, fields, edges, endpoints, flags) explicitly.>

## Design

<The entry's Design sketch, updated to what actually landed: a fenced code block with the new or changed surface as it reads in code (dataclass fields, signatures, schema fragment, endpoint shape). Required when the diff touches `spec/schema/**` or a frozen-candidate module (architecture §3.1); otherwise optional, or "n/a: no code surface".>

## Before / after

<Optional. One row per field or behavior that changes: today, after this PR, what makes the difference observable. Delete the section if nothing existing changes.>

## What did not change

<The entry's Non-goals that a reviewer might otherwise expect here, and where each lives instead (WU id, horizon, or "never, because …").>

## How to review

<Reading order: the two or three files to start with (paths), the invariant or law the reviewer should try to break, and the place a mistake would hide. Say which parts can be skimmed (fixtures, generated types).>

## Try it

<Optional. The offline command or snippet from the entry's Reproduce bullet, with its output after this PR. No network, no credentials, no SDK mocks. Delete the section if there is nothing to run.>

## Evidence

Acceptance items from the entry, each with the test that proves it (a path in this PR):

- [ ] <behavior> — `python/packages/<dist>/tests/test_<x>.py::test_<y>`
- [ ] <behavior> — `spec/fixtures/<edge>/<case>.json`

New fixtures: <n>. New recorded wire pairs: <n>. Verified by hand (not covered by the gate): <none, or what and how>.

## Alternatives considered

<Optional. One line per rejected option with its benefit and cost, or "settled by ADR NNNN". Delete the section when the entry's Decision bullets are all ADR-backed.>

## Follow-ups

<What this PR knowingly leaves, each as a gap row (G-NN), a WU id, or "none". A TODO in the diff without a line here is a finding.>

## Honesty ledger

- [ ] Every new or changed edge has an `EdgeContract` census and golden fixtures in `spec/` (rule 9)
- [ ] Runtime loss ⊆ declared census (`certify_edge` returns `[]`)
- [ ] Nothing is silently dropped, clamped, or rescaled; new extension keys are schema-registered in `spec/extensions/` (rule 5)
- [ ] Streaming changes ship delta type + fold law + fold-triple fixtures (rule 7)
- [ ] Tests are recorded wire pairs; no live keys, no SDK mocks (rule 10)

## Contracts

- [ ] No new third-party dependency in `ocai.core` (rule 11); no provider SDK anywhere (rule 12)
- [ ] Frozen-candidate surfaces changed additively only, or the change is recorded in `docs/decisions/`
- [ ] `docs/architecture.md` section(s) affected: §__ (updated in this PR), or none because <reason>

## Docs and plan

- [ ] WU row flipped in `docs/plans/README.md`; the entry's Status and Evidence bullets filled
- [ ] ADR added or amended when a shape, policy, or boundary outlives this PR, or none needed because <reason>

## Release

- [ ] A change file in `.changeset/` names every published package this PR changes with its semver level and a user-facing note, or no published package changed

## Privacy

- [ ] No AI session link, "Generated with" footer, AI `Co-Authored-By`/`Claude-Session` trailer, agent/task id, or local home path anywhere in this PR's commits, title, body, or files (`scripts/privacy_check.py` is green). The repository is public.

## Verification

Paste the summary block of `uv run python scripts/check.py` (it ends with the `gate: <sha> …` line naming the commit it ran on):

```
```
