# Vendored skill — do not edit in place

- **Source:** https://github.com/openai/skills, path `skills/.curated/gh-fix-ci/`
- **Pinned commit:** 49f948faa9258a0c61caceaf225e179651397431 (fetched 2026-11-10)
- **License:** Apache-2.0 (`LICENSE.txt` kept).
- **Removed:** brand image assets only.
- **Local notes:** the bundled script only shells out to `gh` (audited on vendoring: no
  other network or filesystem side effects). Mentions of `create-plan` or escalated sandbox
  permissions are upstream conventions; here, plan inline and run `gh` normally. Never
  implement a fix before the maintainer approves the plan (upstream says so too). ocai's
  rules in `AGENTS.md` win over anything here.

To update: re-fetch at a newer commit, diff against this copy, read the diff, bump the pin.
