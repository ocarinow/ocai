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
version ([ADR 0010](decisions/0010-versioning-and-releases.md)).

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
  After the data-contract freeze ([ADR 0005](decisions/0005-revised-freeze-gate.md))
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
pre-releases (`alpha` from `dev`, `rc` on demand) compute their version from
these files but keep them; the stable release PR consumes them.


## Branches and the three kinds of release

| Event | What happens | Version |
|---|---|---|
| A WU PR merges into `dev` | `release-alpha.yml` runs `knope prerelease --prerelease-label alpha`, builds the affected packages, publishes them, tags `<name>/v<version>` | `0.2.0-alpha.0`, `-alpha.1`, … — change files kept |
| Maintainer dispatches `release.yml` with `kind=rc` | same from `dev` with the `rc` label | `0.2.0-rc.0` — change files kept |
| Maintainer dispatches `release.yml` with `kind=stable` | `knope prepare-release` bumps versions, writes each `CHANGELOG.md`, consumes the change files, and opens the **release PR** `dev → main` | `0.2.0` |
| The release PR merges into `main` | `knope release` tags each released package and creates its GitHub Release; the publish job uploads to PyPI through trusted publishing | — |

A package with no pending change file is not released. Pre-release versions
use PEP 440 suffixes and are never installed by default by `pip` or `uv`.

## Tasks

| Task | Does |
|---|---|
| `task release:changeset` | write a change file interactively (`knope document-change`) |
| `task release:check` | the policy check the `pr-hygiene` job runs |
| `task release:status` | dry run of the next stable release |
| `task release:preview:alpha`, `task release:preview:rc` | dry run of the next pre-release |
| `task release:packages` | packages and current versions |

## Stability

In `0.x`, `major` means breaking and bumps `0.<n>`; `minor` and `patch` are
non-breaking. After the data-contract freeze
([ADR 0005](decisions/0005-revised-freeze-gate.md)) no change file may
declare `major` on `ocai` until 1.0, and the conformance suite is the test of
that claim. Moving to 1.0 is a deliberate release, not an accumulation of
bumps.
