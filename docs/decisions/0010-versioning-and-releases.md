# 0010 — Versioning and releases: independent semver, changesets, two branches

- **Status:** accepted
- **Date:** 2026-11-11
- **Deciders:** maintainer, with Claude Code

## Context

The monorepo holds publishable libraries (`ocai`, `ocai-openai`,
`ocai-anthropic`, future satellites, later TypeScript and Go packages), a
language-neutral `spec/` with dated canonical revisions, and platform
services that are deployed rather than published. Rule 3 keeps three version
axes distinct: interface tag, canonical IR revision, library semver. Commit
and PR titles are `WU-NN: …`, which every board and review tool relies on, so
a conventional-commits release tool does not fit. The maintainer wants
semantic versioning, release candidates and alphas, and branch-dependent
publishing.

## Decision

1. **Independent semver per published distribution.** Each package under
   `python/packages/` has its own version and tag `<name>/v<version>`.
   Compatibility is expressed by dependency ranges (a plugin pins
   `ocai>=X,<Y`) and tested in CI against the kernel at the same commit.
   Lockstep versioning is rejected.
2. **The spec keeps its own axis.** A canonical revision (`ocai@YYYY-MM`) is
   tagged `spec-YYYY-MM` on the commit that freezes its schemas and fixtures.
   Library versions never encode the revision.
3. **Changesets record release intent in the PR.** Any PR changing a file
   under a published package adds `.changeset/<id>.md` with `package: level`
   front matter and a user-facing note ending in the WU id and PR number.
   `pr-hygiene` refuses the PR otherwise. Titles stay `WU-NN: …`; semver and
   WU ids coexist because each lives where it is owned.
4. **knope for the mechanics, one script for the policy.** `knope.toml`
   declares the packages; knope bumps `pyproject.toml` (and later
   `package.json`, `go.mod`), writes each package's `CHANGELOG.md`, tags
   `<name>/v<version>`, and creates the GitHub Releases; pre-releases use
   `--prerelease-label alpha|rc` and keep the change files. The only custom
   code is `scripts/release.py check`: a change file is required when a
   published package changed. A hand-rolled bump engine was started and
   dropped: the release path must outlive any one script.
5. **Two branches, three kinds of release.** `dev` is the integration branch
   every WU PR targets; each merge to `dev` publishes an **alpha** of the
   affected packages. A **release candidate** is cut from `dev` on demand.
   The **stable** release is the merge of a release PR from `dev` into
   `main`: versions bumped, changelogs written, changesets consumed, tags
   pushed, packages published. Both branches carry the same rulesets.
6. **Publishing is trusted publishing.** PyPI (later npm) is configured to
   trust this repository's release workflow through OIDC; no registry token
   is stored. Each publish is a GitHub Release per tag with the changelog
   section.
7. **Platform services are deployed, not published.** Images are tagged with
   the git SHA and promoted through GitHub environments (`dev` branch →
   staging, `main` → production); the kernel version they embed is recorded
   in image labels and the release note. A service's semver matters only at
   its external API, which for the gateway is the dated canonical interface.
8. **Stability and the 0.x rule.** knope applies pre-1.0 semver: while a
   package is `0.x`, `major` (breaking) bumps the middle number and `minor`
   and `patch` bump the last. A breaking change is therefore declared
   `major` even in 0.x. After the data-contract freeze (ADR 0005) no change
   file may declare `major` on `ocai` until 1.0; the conformance suite is
   the test of that claim. Pre-releases are `X.Y.Z-alpha.N` / `-rc.N`,
   normalized by Python builds to PEP 440.

## Alternatives considered

- **Conventional commits with python-semantic-release or release-please.**
  Replaces the `WU-NN:` grammar or buries it; a wrong type silently produces
  a wrong bump; one commit cannot bump two packages at different levels.
- **Lockstep versions across all packages.** Forces plugin releases for
  kernel-only changes and hides which package actually changed.
- **The npm `changesets` CLI directly.** JavaScript-only bumping; knope
  reads the same file format and bumps Python, npm, and Go files.
- **A custom release script.** Small today, a liability over the project's
  lifetime (pre-release sequencing, changelog merging, Go tags, npm). knope's
  risk — a small open-source project — is bounded because its inputs and
  outputs are plain files we own.
- **Publishing alphas to TestPyPI.** A second credential surface and a
  second index to configure for little benefit; PEP 440 pre-releases on the
  real index are not installed by default.

## Consequences

- `AGENTS.md` carries the ground rule; `wu-session` adds the changeset step;
  the PR template gains a Release section; `review-pr` checks it.
- Workflows: `release-alpha.yml` on push to `dev`, `release.yml` on dispatch
  (`rc` from `dev`, `stable` by release PR to `main`). Rulesets on `dev`
  mirror `main`. The maintainer configures trusted publishing on PyPI once
  per package.
- `task release:*` wraps the script; `task pr:worktree` and `task pr:draft`
  default to `dev`.
