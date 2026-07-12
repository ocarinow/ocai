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

## Before you open a PR

Read [`CLAUDE.md`](./CLAUDE.md) — it holds the cross-cutting rules every change
must follow. In particular:

- **One work unit per PR.** Keep diffs small and reviewable.
- `uv run ruff check` is clean and `uv run pytest` is green.
- Tests use **recorded HTTP request/response pairs** (respx/VCR-style), never
  live API keys and never provider-SDK mocks.
- No provider SDKs and no pydantic in `ocai-core`; credentials are explicit-only.

See the milestone plans in [`plans/`](plans/README.md) to pick a work unit.
