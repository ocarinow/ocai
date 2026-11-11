# Documentation map

The published site is built **only from `docs/user/`**. Removing a page from
navigation is not sufficient to unpublish it; keep internal documentation outside
that root. Run `task docs:check` to check the audience boundary, references and build.

| Audience | Content | Source |
|---|---|---|
| Library and platform users | Installation, usage, supported features, troubleshooting, API reference | [user/](user/index.md) |
| Contributors and operators developing the platform | Setup, verification, releases, documentation maintenance | [development/](development/README.md), [platform development](../platform/README.md) |
| Maintainers and implementers | Structural contract and settled decisions | [architecture.md](architecture.md), [decisions/](decisions/README.md) |
| Product designers | Proposed platform workflows and boundaries | [design/](design/README.md) |
| Integration researchers | Dated provider and capability investigations, not support claims | [research/](research/README.md) |
| Delivery planning | Authoritative WUs and their dependencies/status | [plans/](plans/README.md) |
| Reviewers | Documentation audit, evidence and historical classification | [audits/](audits/documentation.md) |

The language-neutral schemas and fixtures remain in [spec/](../spec/README.md).
Keep historical ADR rationale and archived plans intact; update implementation
status or link a successor instead of rewriting history. User documentation states
only behavior supported by the checked-out code and qualification evidence.
