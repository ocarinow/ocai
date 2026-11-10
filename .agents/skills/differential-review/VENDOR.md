# Vendored skill — do not edit in place

- **Source:** https://github.com/trailofbits/skills, path `plugins/differential-review/skills/differential-review/`
- **Pinned commit:** e4dd0bb5b15535f7c5a0834187dffba6ac37e4ff (fetched 2026-11-10)
- **License:** CC-BY-SA-4.0 (attribution: Trail of Bits). `UPSTREAM-README.md` is the plugin README.
- **Removed:** brand image assets only.
- **Local notes:** the upstream references companion agents/skills that are NOT vendored
  (`differential-review`-specific analyzer agents, `audit-context-building`, `issue-writer`). Treat those
  mentions as "do the phase yourself". Report files go in the scratchpad, never in the repo.
  ocai's own rules (`AGENTS.md`) win over anything here; the honesty-reviewer role covers
  fidelity rules, this skill covers security.

To update: re-fetch at a newer commit, diff against this copy, read the diff, bump the pin.
