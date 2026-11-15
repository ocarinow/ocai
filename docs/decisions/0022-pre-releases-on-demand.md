# 0022 — Pre-releases are published on demand, never by a merge

- **Status:** accepted
- **Date:** 2026-11-16
- **Deciders:** maintainer

## Context

[ADR 0010](0010-versioning-and-releases.md), decision 5, made every merge into
`main` publish an alpha of each package with pending change files. In
practice every such merge put a new version of up to six packages on PyPI.
Nobody installs those alphas: they exist only because a merge happened, and
the list of published versions grows without telling a user anything. A
published version cannot be removed from PyPI, only yanked.

## Decision

A merge into `main` publishes nothing. `prerelease.yml` runs only when it is
dispatched by hand, for an alpha or a release candidate
(`task release:alpha`, `task release:rc`). It computes versions and publishes
exactly as before.

This supersedes the alpha-on-merge part of ADR 0010, decision 5. Everything
else in ADR 0010 stands: independent semantic versions, change files that
travel with the change, the standing Release PR refreshed on every push to
`main`, and the stable release when that pull request merges.

## Alternatives considered

- **Keep the alpha on every merge.** It gives an installable build of every
  merge without any action, but nothing consumes those builds and each one is
  a permanent entry on the index.
- **Publish an alpha on a pull request label.** It keeps publication tied to
  a merge, but adds a convention to remember for something a single command
  already does.
- **Publish alphas to a separate index.** ADR 0010 already rejected a second
  index and a second credential surface.

## Consequences

- The published versions of a package are the ones someone asked for.
- A build of `main` for early testing needs one command instead of none.
- Alphas already published stay on PyPI. Yanking them is a maintainer action
  on PyPI and is not part of this decision.
- `AGENTS.md` rule 19, `CONTRIBUTING.md`, `docs/development/releasing.md` and
  `knope.toml` are updated to say so.
