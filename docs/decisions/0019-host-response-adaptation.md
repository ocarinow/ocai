# 0019 — Adapt successful host responses through governed public contracts

- **Status:** accepted; corresponding implementation merged on main
- **Date:** 2026-11-11
- **Deciders:** maintainer

## Context

The reusable host remediation is approved. WU-48a preserves error evidence and
WU-48b gives host effects an honest report lane. Unary success still discards native
headers at envelope unwrap. A host must expose metadata and effects without private
transport overrides, provider-specific kernel branches or another codec implementation.

## Decision

Add detached HostEvidence(host, adapter, response_status, response_headers,
response_body, metadata) to core. It is execution evidence, never a canonical chat
payload. CallResult gains optional keyword-only host_evidence. OcaiError gains
optional report, usage and host_evidence so a rejected host outcome retains known
accounting through its existing neutral taxonomy. None remains unknown, never zero.

Expose DriverResponse(payload, response) through execute_response on both drivers;
existing execute keeps returning the unwrapped payload. The final response chosen
by policies is captured, including policy Return, after retries. No authenticated
request enters this envelope. Response snapshots and adapter input are detached.

An optional ResponseMappingHost selects HostResponseAdapter with host/name,
non-secret JSON options, a pure callback and HostEffectContract. Its census uses the
same disposition/semantic matching rules as edge contracts but no graph coordinates
or planner weights. Declarations are inspectable separately from payload findings
and conformance evidence. The declaration content has a deterministic identity;
preparation also fingerprints callback ownership and snapshots configuration.

The callback returns HostAdaptation: dialect payload, JSON metadata, losses, shifts
and optional ocai error. The facade decodes the dialect payload, merges exactly one
host report, retains known usage and enforces the existing FidelityPolicy. A census
breach fails closed with full report/accounting. A blocked outcome retains its
neutral error taxonomy and native evidence. Invalid or raising callbacks produce a
sanitized ocai failure, with no callback text or SDK exception chain. Fidelity-policy and census rejection retain report/usage but omit host_evidence
as well as raw payload, preserving their existing non-disclosure contract. Authorized
application code can inspect evidence on permitted results and host taxonomy errors; passive observers never export it.

This first adapter is unary-only. Selecting it for streaming raises before provider
I/O. A separate WU must define stream response-head capture, incremental effect
emission, terminal accounting and cleanup before enabling streaming. No fallback
silently skips a selected host adapter.

## Alternatives considered

Capturing headers in a policy does not define a governed transformation and can miss
policy-replaced responses. Putting metadata in chat extensions ties a transport
contract to one capability. Changing CallResult.raw would break existing consumers.
The separate execution evidence carrier preserves those boundaries. Reusing the
contract matching algorithm avoids a different definition of honesty for hosts.

## Freeze and scope

Core result/error additions are additive under ADR 0005; no dependency or provider
SDK enters core. Host declarations are provisional execution contracts, not new
graph nodes or qualification claims. This ADR does not qualify Bedrock or any
other real host; their recorded mappings remain separate WUs.
