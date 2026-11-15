# Skills

Procedures every coding agent can load (Agent Skills format: one folder, one
`SKILL.md`). Codex discovers this directory natively; Claude Code reads it
through the `.claude/skills` symlink. Repo-specific skills come first: they
encode decisions no external skill knows. Vendored skills are copied in at a
pinned commit, read before adoption, and carry a `VENDOR.md` with source,
pin, license, and local notes. Never install skills from a marketplace at run
time; a skill is instructions the agents execute, so it is supply chain and
belongs in git where a diff is visible.

| Skill | Kind | Use when |
|---|---|---|
| `wu-define` | repo | a horizon item, gap, or request has no WU entry yet |
| `wu-session` | repo | implementing one WU end to end |
| `add-edge` | repo | adding or changing a conversion edge |
| `record-wire-pair` | repo | a test needs provider wire traffic |
| `review-pr` | repo | reviewing a pull request (the honesty-reviewer role, with every check run on it) |

Roles (sub-agent bodies) live in `../roles/`; the fidelity review is the
`honesty-reviewer` role, not a skill.

Not vendored, on purpose: property-based testing (deferred until the IR shape
settles after the freeze review), `insecure-defaults` (a Claude plugin with
JS workflows, not an Agent Skill; its pattern lists may be mined later),
`modern-python` (recommends a different type checker than ADR 0002).

Removed after a trial, do not vendor again without a reason: `differential-review`,
`sharp-edges`, `gh-fix-ci` and `gh-address-comments`. They were almost never
used, and the agents already know `gh`.
