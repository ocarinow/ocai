# Security policy

ocai is source-available infrastructure for enterprises putting generative AI
in production. Credentials, provider traffic, identity, and audit evidence
pass through it, so security reports are treated as the highest-priority
input this project receives.

## Reporting a vulnerability

Report privately through GitHub's private vulnerability reporting:
**<https://github.com/ocarinow/ocai/security/advisories/new>**. Do not open
a public issue, discussion, or pull request for a suspected vulnerability.

Include what you can of: the affected distribution or service (`ocai`,
`ocai-openai`, `ocai-anthropic`, `ocai-deepseek`, the gateway, the console),
the version or commit, a minimal reproduction, and the impact you believe it
has. A recorded HTTP/SSE pair that demonstrates the problem without live
keys is ideal; never send real credentials or customer data.

You will receive an acknowledgement through the advisory thread. The
maintainer aims to triage within one week, to agree a disclosure timeline
with you once the report is confirmed, and to credit you in the advisory
unless you prefer otherwise. There is no bug bounty.

## Scope

In scope: everything in this repository — the kernel and plugin
distributions under `python/`, the language-neutral `spec/`, the platform
services and console under `platform/`, the release and CI workflows, and
the documentation site build. Of particular interest: credential handling
(rule 13 in `AGENTS.md`: credentials applied only at the driver leaf, never
visible to hooks, never in `raw` or reports), honesty of conversion (a
silent drop, clamp, or rescale is a defect even when nothing crashes), the
gateway's identity and authorization paths, and anything in a workflow that
could exfiltrate a secret.

Out of scope: vulnerabilities in upstream providers (OpenAI, Anthropic,
DeepSeek) or in third-party dependencies that are not exploitable through
ocai; reports that require a compromised developer machine; findings from
automated scanners without a demonstrated impact.

## Supported versions

The distributions are pre-1.0. Fixes land on `main` and ship in the next
release of the affected package; there are no long-lived release branches.
Pre-release versions (`aNN`, `rcNN`) are not supported once a later version
exists.

## Disclosure

Fixes for confirmed reports are published as GitHub security advisories
with a CVE where applicable, listed in the affected package's
`CHANGELOG.md`, and noted in the release.
