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

## Clone setup

`task setup` creates the environment, installs the docs group, installs the
git hooks (`.pre-commit-config.yaml`: checks at commit, on the commit message
and at push, so a failing check or a privacy leak is caught before it leaves
your machine), and checks `gh` authentication. `.editorconfig`, `.python-version` (3.13), and
`.node-version` (the Node release CI uses) are honoured by the usual tools.

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
A merge to `main` publishes nothing; merging the standing Release PR publishes
the stable release, and an alpha or a release candidate is published only on
demand. See ADR 0010, ADR 0022 and [`docs/development/releasing.md`](docs/development/releasing.md).

## Before you open a PR

Read [`AGENTS.md`](./AGENTS.md) — it holds the cross-cutting rules every change
must follow (coding agents read the same file). In particular:

- **One work unit per PR.** Keep diffs small and reviewable.
- Checks run by themselves once `task setup` has installed the hooks: the
  privacy guard, lint with the bandit rules, format, lockfile, import
  contracts and strict types at commit; the tests (warnings are errors), the
  change-file policy and the privacy guard on commits at push. Each hook runs
  only when a file it covers changed. `task check` runs all of them on the
  whole repository with [Task](https://taskfile.dev) installed; `task` lists
  every development command. Do not bypass a hook.
- CI runs the same tools and adds what is too slow for a hook: the wheel
  build, the docs build, the isolated plugin install and the platform suite,
  plus Semgrep, actionlint, a dependency review on pull requests, a nightly
  `npm audit`, and the kernel on Python 3.13 and 3.14.
  A platform change needs Docker and the Node and browser runtime described in
  [platform development](platform/README.md).
- Tests use **recorded HTTP request/response pairs** (respx/VCR-style), never
  live API keys and never provider-SDK mocks.
- No provider SDKs and no pydantic in `ocai-core`; credentials are explicit-only.

See the milestone plans in [`docs/plans/`](docs/plans/README.md) to pick a work
unit, and [`docs/decisions/`](docs/decisions/README.md) for settled decisions.

## CI feedback

Editing a pull request's title or body re-checks the text and never replays the
code checks. A change runs only the suites that depend on the files it touches;
two checks are required, `ci` for the code and `pr` for the text.
See [CI verification](docs/development/ci.md) for the selection rules and the required checks.
