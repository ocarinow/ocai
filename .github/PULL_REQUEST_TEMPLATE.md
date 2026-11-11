## Work unit

WU-__ — <title from docs/plans/>. One WU per PR (rule 17). The PR title starts with the WU id; the board card follows it.

## What changed

<two or three sentences: the behavior, not the diff>

## Honesty ledger

- [ ] Every new/changed edge has an `EdgeContract` census and golden fixtures in `spec/` (rule 9)
- [ ] Runtime loss ⊆ declared census (`certify_edge` returns `[]`)
- [ ] Nothing is silently dropped, clamped, or rescaled; new extension keys are schema-registered in `spec/extensions/` (rule 5)
- [ ] Streaming changes ship delta type + fold law + fold-triple fixtures (rule 7)
- [ ] Tests are recorded wire pairs; no live keys, no SDK mocks (rule 10)

## Contracts

- [ ] No new third-party dependency in `ocai.core` (rule 11); no provider SDK anywhere (rule 12)
- [ ] Frozen-candidate surfaces changed additively only, or the change is before the v0.2 freeze and recorded in `docs/decisions/`
- [ ] `docs/architecture.md` section(s) affected: §__ (updated in this PR)
- [ ] WU checkbox flipped in `docs/plans/README.md` and the milestone file

## Release

- [ ] A changeset in `.changeset/` names every published package this PR changes with its semver level and a user-facing note, or no published package changed

## Privacy

- [ ] No AI session link, "Generated with" footer, AI `Co-Authored-By`/`Claude-Session` trailer, agent/task id, or local home path anywhere in this PR's commits, title, body, or files (`scripts/privacy_check.py` is green). The repository is public.

## Verification

Paste the summary block of `uv run python scripts/check.py`:

```
```
