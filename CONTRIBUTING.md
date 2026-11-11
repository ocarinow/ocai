# Contributing to ocai

Thanks for your interest in ocai. ocai is **source-available** software licensed
under the [Functional Source License (FSL-1.1-ALv2)](./LICENSE) — not open
source. Contributions are welcome under the terms below.

## Developer Certificate of Origin (DCO) — required

Every commit must be signed off under the [Developer Certificate of Origin
1.1](https://developercertificate.org/). Signing off certifies that you wrote the
contribution or otherwise have the right to submit it under the project's
license, and it is what keeps **commercial relicensing** of the project possible.

Add a `Signed-off-by` trailer to each commit using your real name and email:

```
Signed-off-by: Jane Developer <jane@example.com>
```

The easy way is `git commit -s`, which appends the trailer automatically. Make
sure your `git config user.name` and `user.email` are set correctly. Commits
without a valid `Signed-off-by` line will not be merged.

By signing off you agree to the full text of the DCO:

> By making a contribution to this project, I certify that:
>
> (a) The contribution was created in whole or in part by me and I have the right
> to submit it under the open source license indicated in the file; or
>
> (b) The contribution is based upon previous work that, to the best of my
> knowledge, is covered under an appropriate open source license and I have the
> right under that license to submit that work with modifications, whether
> created in whole or in part by me, under the same license (unless I am
> permitted to submit under a different license), as indicated in the file; or
>
> (c) The contribution was provided directly to me by some other person who
> certified (a), (b) or (c) and I have not modified it.
>
> (d) I understand and agree that this project and the contribution are public
> and that a record of the contribution (including all personal information I
> submit with it, including my sign-off) is maintained indefinitely and may be
> redistributed consistent with this project or the license(s) involved.

## Privacy: nothing from your working session goes public

This repository is public. Commit messages, PR titles and bodies, reviews,
comments, issues, and files must never contain links to an AI coding
session, "Generated with …" footers, AI `Co-Authored-By` or `Claude-Session`
trailers, agent or task identifiers, or paths under your home directory.
`uv run python scripts/privacy_check.py` is part of the gate and a required
CI check; a server-side rule also rejects pushes whose commit messages carry
such content. If you use a coding agent, this applies to it too — see
`AGENTS.md`.

## Editor setup

The repository holds several Python environments (the root uv workspace for
the kernel and plugins, the gateway service, the plugin example) and a node
tree. Open **`ocai.code-workspace`** in VS Code (`task ide`), not the
repository folder: each environment is its own workspace folder with its own
interpreter in `<folder>/.vscode/settings.json`, so Pylance, Ruff, and the
test runner resolve against the right venv. Run `uv sync` in each Python
folder you work in (`task setup` does the root one).
## Versions and releases

Each distribution under `python/packages/` has its own semantic version. A
PR that changes one adds a changeset in `.changeset/` (package, level, note);
versions are bumped only by the release script when a release is cut.
Every merge to `main` publishes an alpha of each package with pending change
files; merging the standing Release PR publishes the stable release. See ADR
0010 and [`docs/releasing.md`](docs/releasing.md).

## Before you open a PR

Read [`AGENTS.md`](./AGENTS.md) — it holds the cross-cutting rules every change
must follow (coding agents read the same file). In particular:

- **One work unit per PR.** Keep diffs small and reviewable.
- `uv run python scripts/check.py` exits 0 (privacy guard, ruff, import contracts,
  pyright, mypy, pytest) — or `task check` with [Task](https://taskfile.dev)
  installed; `task` lists every development command.
- The gate also verifies the platform. Install its separate dependencies and
  browser runtime as described in [platform development](platform/README.md).
- Tests use **recorded HTTP request/response pairs** (respx/VCR-style), never
  live API keys and never provider-SDK mocks.
- No provider SDKs and no pydantic in `ocai-core`; credentials are explicit-only.

See the milestone plans in [`docs/plans/`](docs/plans/README.md) to pick a work
unit, and [`docs/decisions/`](docs/decisions/README.md) for settled decisions.
