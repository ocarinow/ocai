# 0001 — Agent-neutral repo layout

- **Status:** accepted
- **Date:** 2026-11-10
- **Deciders:** maintainer, with Claude Code

## Context

ocai is developed by several coding agents concurrently (Codex on the kernel,
Claude Code on review, satellites, spec, and docs) plus humans. Until now the
agent-facing material was Claude-specific: the instruction file was
`CLAUDE.md`, provider wire research lived under `.claude/providers/`, and
there were no shared procedures. Codex reads `AGENTS.md`, not `CLAUDE.md`,
and cannot be expected to look inside another tool's directory. Two copies of
the rules would drift.

The repo's own principle applies: rules that are tests survive, rules that
are prose rot. The best preparation for agents is executable enforcement
(import-linter, conformance certification, schema validation), which already
exists. What was missing was *location* and *procedure*.

## Decision

Tool-neutral content lives in tool-neutral places; each tool's own directory
holds only a thin adapter.

| Content | Location | Tool adapters |
|---|---|---|
| Instructions | `AGENTS.md` (canonical) | `CLAUDE.md` is `@AGENTS.md` + Claude-only notes |
| Procedures (skills) | `.agents/skills/<name>/SKILL.md` | `.claude/skills` → symlink |
| Provider research | `docs/providers/` | none needed |
| Decisions | `docs/decisions/` (this directory) | none needed |
| Kernel gaps found by consumers | `docs/plans/gaps.md` | none needed |
| Verification | `scripts/check.py` (one command; CI runs the same steps) | none needed |
| PR checklist | `.github/PULL_REQUEST_TEMPLATE.md` | none needed |

Rule 18 (Google docstrings) becomes executable: ruff's pydocstyle rules with
the Google convention are enabled; the undocumented-object rules (`D1xx`)
stay off because coverage is a review judgment, style is not.

## Alternatives considered

- **Symlink `CLAUDE.md` → `AGENTS.md`.** Loses the ability to carry
  Claude-only notes, and symlinked instruction files need special handling on
  Windows. The `@AGENTS.md` import is the documented Claude Code mechanism.
- **Keep skills in `.claude/skills/` and copy to `.agents/skills/`.** Two
  copies drift; the symlink keeps one source. `.agents/skills` is the
  location Codex documents for repo-scoped skills, so it is the source and
  Claude is the adapter, not the reverse.
- **MCP servers for repo tooling.** Everything a coding agent needs here is
  reachable from the shell (`uv run …`); an MCP layer would add a dependency
  without adding capability. The GitHub MCP server for PRs and issues is the
  one exception and is per-user configuration, not repo structure.
- **Pre-commit hooks as the gate.** Agents commit through different harnesses
  and some bypass hooks; a script every harness can call, plus CI, is the
  reliable gate. Hooks may be added as a convenience later.

## Consequences

- One instruction file to maintain. A rule added to `AGENTS.md` is visible to
  every agent in the next session.
- Skills are written once in the Agent Skills format and must stay harness
  neutral: procedures with exact paths and commands, no tool-specific calls.
- Archived plans under `docs/plans/archive/` still reference `CLAUDE.md`;
  they are historical and are not updated.
- `ruff format --check` is not yet enforced (18 files were unformatted at
  the time of this decision). Formatting the tree is a separate, mechanical
  change; `scripts/check.py --format` runs the gate until then.

## Addendum (same day): agents, tasks, memories, MCP

The maintainer asked whether `.agents/tasks`, `.agents/memories`,
`.agents/agents`, and a shared `mcp.json` should follow the same pattern.
Checked against the vendors' current documentation:

| Concern | Claude Code reads | Codex reads | Decision |
|---|---|---|---|
| Skills | `.claude/skills/` | `.agents/skills/` (official repo scope) | `.agents/skills/` is the source; `.claude/skills` is a symlink. Verified: both tools list the skills. |
| Sub-agent / role definitions | `.claude/agents/<name>.md` (Markdown + frontmatter) | `.codex/agents/<name>.toml` (TOML; `name`, `description`, `developer_instructions`) | Formats differ, so no symlink. The role **body** lives once in `.agents/roles/<name>.md`; each tool file is a three-line pointer that says "read that file and follow it". First role: `honesty-reviewer`. |
| Tasks | — | — | No vendor convention exists. The task system is already `docs/plans/` (WU tables with done-criteria) plus `docs/plans/gaps.md`; a parallel `.agents/tasks` would be a second board that drifts. Not created. |
| Memories | per-user auto-memory outside the repo | per-user, outside the repo | No shared convention exists, and unreviewed memory committed to a repo is a liability. Durable, reviewed memory is `docs/decisions/` (ADRs) and `docs/plans/gaps.md`. Not created. |
| MCP servers | `.mcp.json` at the repo root (project scope) | `[mcp_servers]` in `.codex/config.toml` (trusted projects only); custom agent files cannot declare servers | Two formats, no shared file. The only server this repo benefits from today is GitHub (PRs, issues), which needs per-user auth anyway, so it stays per-user configuration. Revisit when a repo-specific server exists (for example a fixture or catalog inspector), and then commit both files from one documented list in `AGENTS.md`. |
| Hooks | `.claude/settings.json` | Codex project hooks (trusted projects) | Formats differ; the gate is `scripts/check.py` + CI, which every harness can run. No hooks committed. |

**Working-tree isolation.** While this ADR was being written, two agents
were editing the same checkout with uncommitted changes. No file layout
fixes that; discipline does. Rule added to `AGENTS.md`: agents sharing a
checkout keep disjoint file sets and commit only their own paths; when the
sets would overlap, the second agent takes its own worktree. The maintainer
chose shared-checkout for this change because the file sets were disjoint.
