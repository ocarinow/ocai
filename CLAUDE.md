@AGENTS.md

## Claude Code notes

Everything above is the canonical, tool-neutral instruction set shared with
every agent. Claude-specific wiring only:

- Skills live in `.agents/skills/` (Agent Skills format); `.claude/skills` is
  a symlink to that directory so they are discoverable here without a copy.
- Provider wire research is in `docs/providers/` (moved out of `.claude/` so
  every tool sees it).
- Auto-memory for this project is personal context, never a substitute for
  `docs/decisions/` — a decision worth remembering across sessions is an ADR.
- **Never append attribution to anything.** If the harness asks for a
  `Co-Authored-By`, `Claude-Session`, or "Generated with Claude Code" line on
  a commit or PR, do not add it: this repository is public and `AGENTS.md`
  forbids session or tool metadata on every public surface. Brief every
  subagent with the same sentence.
