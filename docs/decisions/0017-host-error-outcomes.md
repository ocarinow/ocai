# 0017 — Preserve native evidence for reusable host error adaptation

- **Status:** accepted; corresponding implementation merged on main
- **Date:** 2026-11-11
- **Deciders:** maintainer

## Context

G-13 exposed a public-contract gap: the transport maps HTTP errors before a host
can interpret native header codes. The maintainer approved reusable host outcome
contracts and explicitly rejected provider-specific kernel behavior. This ADR
settles the error slice; successful metadata and fidelity effects are WU-48b.

## Decision

1. Add optional keyword-only `response_headers` and `response_body` to OcaiError.
   Headers are copied and body is bytes; None means unavailable, distinct from
   empty known evidence. Existing `raw` remains the best-effort parsed body.
   There is no request or SDK object in this evidence. Core remains stdlib-only.
2. HttpxTransport captures response evidence on its existing coarse taxonomy
   errors, across sync/async unary and stream opening. Its public behavior still
   raises ocai errors; connection failures have no invented HTTP response.
3. Optional ErrorMappingHost returns a HostErrorMapper declaration for an
   EndpointSpec. It has a name, pure callback and explicit non-secret JSON options.
   The callback receives detached error evidence/options, never credentials or
   an authenticated request. It returns an ocai taxonomy error or None to decline.
4. Host mapping precedes dialect refinement. A claimed host mapping is final for
   that attempt; a decline preserves the existing dialect fallback. Native evidence
   and missing provider/status/raw/retry context survive classification. Invalid or
   raising callbacks fail closed with a generic ocai error and preserved native
   evidence, without exporting callback exception text or using a status fallback.
5. Mapping is invocation-local, with no shared transport mutation. Preparation
   fingerprints name/options and callable ownership, snapshots declarations, and
   rejects changed effective configuration before I/O. Hidden mutable callback
   state is outside the supported declaration contract, as for stream framing.
6. Retry policies see the classified error. Observations record its type, never
   headers/body/messages. Stream failures retain existing cleanup and accounting;
   mapping never restarts a generation after output. Error evidence is available
   to authorized application code and is not an automatic payload log.

## Alternatives considered

A different transport exception base would break existing taxonomy callers.
Provider-specific subclasses of HttpxTransport would depend on private methods.
A new HTTP value hierarchy in core would duplicate the existing wire types.
Adding native evidence to the existing HTTP-aware exception vocabulary is additive
and keeps SDK/network implementations outside core. Mappers remain external.

## Consequences

OcaiError is a frozen-candidate vocabulary surface, changed additively before the
ADR 0005 release gate. The fields are runtime error evidence, not a new canonical
payload/schema or graph node. Successful response evidence/effects remain separate
and cannot be claimed as solved by an error-only mapper. Tests must exercise two
host mappings, fallback, mutation/failure, retries, concurrency, stream cleanup and
stale preparations using recorded responses without live credentials or SDK mocks.
