# 0020 — Validate package wiring according to explicit responsibility

- **Status:** accepted; corresponding implementation merged on main
- **Date:** 2026-11-11
- **Deciders:** maintainer review

## Context

The expanded workspace gate treats every non-core distribution as a semantic
plugin. Credential and service-host packages have different responsibilities;
requiring catalog fragments and core extras would blur the approved separation.

## Decision

Optional build metadata tool.ocai.role selects kernel, codec, credential or host.
Existing defaults remain kernel for ocai and codec for other distributions.
Unknown roles and a kernel role on another package fail. All packages retain
namespace, typing, metadata, release, bounded core dependency and inventory checks.
Only codecs require conversion fragments and core convenience extras. Credential
and host packages require explicit import-linter boundaries prohibiting direct
HTTP transport ownership; credential packages also cannot import capability,
conversion or runtime machinery. No provider-name allowlist is introduced.

## Alternatives considered

Empty fragments imply conversion ownership that auth does not have. Provider-name
exceptions do not scale. Exempting external packages from all checks weakens the
gate. Adding an unbounded satellite role would preempt its architectural contract.

## Consequences

Provider packages declare responsibility alongside their build metadata. No kernel
runtime or frozen-candidate type changes. New responsibilities need explicit gate
rules; metadata is not a runtime registry or authentication mechanism.
