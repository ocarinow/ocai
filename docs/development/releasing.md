---
icon: lucide/tag
---

# Releasing

!!! note "Status"

    Tooling in place (ADR 0010); the first stable release has not been cut.
    Trusted publishing on PyPI is configured by the maintainer once per
    package before the first publish.

Every published distribution has its **own semantic version** and its own
tag `<name>/v<version>`; the spec keeps its own dated axis (`spec-YYYY-MM`);
platform services are deployed, not published. Release intent is recorded in
the PR that makes the change, as a **change file**; the mechanics are
[knope](https://knope.tech); the policy is `scripts/release.py`.

## Change files — release intent, recorded in the PR that makes the change

A change file is one small Markdown file per PR in this directory. It declares
which published packages the PR affects, the semver level each one needs, and
the note that becomes their changelog entry. It is written when the author
knows the impact best, reviewed next to the code, and consumed by
[knope](https://knope.tech) when a stable release is cut. Nothing else bumps a
version ([ADR 0010](../decisions/0010-versioning-and-releases.md)).

Create one with `task release:changeset` (interactive) or by hand:

```markdown
---
ocai: minor
ocai-openai: minor
---

#### Server-tool definitions on `ChatRequest.tools`

Admit server-tool definitions and encode them for the OpenAI responses
interface. Optional field, additive; existing requests are unchanged. (WU-41, #80)
```

Rules:

- **Packages** are the names in `knope.toml`: `ocai`, `ocai-openai`,
  `ocai-anthropic`, and every future distribution (TypeScript and Go packages
  join the same file with their own entries).
- **Levels** are `patch` (fix), `minor` (feature, additive), `major`
  (breaking). While a package is `0.x`, knope applies pre-1.0 semver: a
  `major` bumps the middle number (`0.1.0 → 0.2.0`), `minor` and `patch` both
  bump the last (`0.1.0 → 0.1.1`) and differ only in the changelog section
  (Features vs Fixes). So **in 0.x, a breaking change is declared `major`.**
  After the data-contract freeze ([ADR 0005](../decisions/0005-revised-freeze-gate.md))
  nothing on `ocai` may be `major` until 1.0 — the conformance suite is the
  test. Pre-release versions are written `0.1.1-alpha.0`, `-alpha.1`, …,
  `-rc.0`; Python builds normalize them to PEP 440 (`0.1.1a0`, `0.1.1rc0`).
- **When required:** any PR that changes a file under a published package's
  path (`python/packages/<dist>/`, except its `CHANGELOG.md`). The
  `pr-hygiene` check (`scripts/release.py check`) refuses the PR otherwise.
  Docs, tooling, tests-only, and platform changes need none.
- **Body:** a `####` heading as the entry title, then the note written for a
  user of the package, ending with the WU id and PR number in parentheses. No
  session links, no local paths (the privacy rule applies).
- Several packages in one file, each at its own level, is normal. Several
  files per PR is fine. File names are free (`wu-41-server-tools.md`).

Lifecycle: `task release:status` previews the next stable release;
pre-releases (`alpha` on every merge to `main`, `rc` on demand) compute their version from
these files but keep them; the stable release PR consumes them.


## One branch, three kinds of release

Every WU PR merges into `main`. Nothing is released by that merge except an
alpha. The stable release is a PR like any other.

| Event | Workflow | What happens | Version |
|---|---|---|---|
| A PR merges into `main` and change files are pending | `prerelease.yml` | computes each affected package's target version from the change files, publishes an **alpha** with the CI run number, commits and tags nothing, keeps the change files | `0.2.0a123` |
| Same push | `release-pr.yml` | runs `knope prepare-release`: bumps versions, writes `CHANGELOG.md`, consumes the change files, and opens or updates the standing **Release PR** (branch `release`) | the diff shows `0.2.0` |
| Maintainer runs `task release:rc` | `prerelease.yml` (dispatch `kind=rc`) | same as the alpha with the `rc` label | `0.2.0rc124` |
| Maintainer merges the Release PR | `release.yml` | `knope release` tags `<name>/v<version>` and creates one GitHub Release per package from its changelog section; each released package is built and published to PyPI through trusted publishing | `0.2.0` |

Only packages with pending change files appear in any of this. The Release
PR passes the same required checks as every PR; its body is generated and
its version edits are exempt from the change-file policy. Pre-release
versions are never installed by default by `pip` or `uv`.

Why one branch: with squash merges and linear history, a long-lived `dev`
branch diverges from `main` after every release and needs a force-style sync
that the rulesets forbid. One branch with a standing Release PR gives the
same visible behavior with nothing to reconcile (ADR 0010).

## Setup, once (maintainer)

- **Trusted publishing on PyPI.** For each package name (`ocai`,
  `ocai-openai`, `ocai-anthropic`) add a *pending publisher* on PyPI with
  owner `ocarinow`, repository `ocai`, environment `pypi`, and workflow
  `release.yml`; add a second one for `prerelease.yml`. The first publish
  creates the project. No token is stored anywhere.
- **GitHub environment `pypi`** on the repository (the workflows reference it;
  protection rules optional).
- **`RELEASE_TOKEN` secret** (a token with `repo` scope) so the Release PR
  created by CI triggers the required checks; `BOARD_TOKEN` is used until it
  exists.

## Tasks

| Task | Does |
|---|---|
| `task release:changeset` | write a change file interactively (`knope document-change`) |
| `task release:check` | the policy check the `pr-hygiene` job runs |
| `task release:status` | dry run of the next stable release |
| `task release:rc` | publish a release candidate now (dispatches `prerelease.yml`) |
| `task release:preview:alpha`, `task release:preview:rc` | dry run of the next pre-release |
| `task release:packages` | packages and current versions |

## Stability

In `0.x`, `major` means breaking and bumps `0.<n>`; `minor` and `patch` are
non-breaking. After the data-contract freeze
([ADR 0005](../decisions/0005-revised-freeze-gate.md)) no change file may
declare `major` on `ocai` until 1.0, and the conformance suite is the test of
that claim. Moving to 1.0 is a deliberate release, not an accumulation of
bumps.
