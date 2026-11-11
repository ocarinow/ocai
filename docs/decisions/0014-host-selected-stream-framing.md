# 0014 — Host-selected stream framing before semantic conversion

- **Status:** accepted; corresponding implementation merged on main
- **Date:** 2026-11-10
- **Deciders:** maintainer review of the WU-39 implementation

## Context

The integration program's WU-39 requires host framing selection without another
provider codec. The [Bedrock survey §6/13(a)](../research/providers/amazon-bedrock.md)
distinguishes binary transport framing and InvokeModel envelope removal from
Converse's provider semantics. The drivers previously hard-coded SSE. Existing
public preparation, lifecycle, credential isolation and stream ownership from
ADR 0007 must cover a different framing choice as well.

This decision changes provisional wire machinery only. No canonical capability
interface, chunk type, schema, graph node or conversion edge changes. AWS parsing,
provider exception envelopes and concrete cloud qualification remain later WUs.

## Proposed decision

Add optional `FramingHost.stream_framing(spec)` alongside the existing Host
protocol. Hosts without it retain SSE. Selection returns `StreamFraming(name,
factory, options)`: explicit non-secret JSON options plus a stable trusted factory.
Factories receive detached options and return fresh sans-io `StreamDecoder`s.
The decoder removes framing and host envelopes; it emits existing plugin inputs,
not canonical parts. Semantic conversion continues through the same graph edges.

Factories must declare all effective configuration in options and avoid ambient
or hidden mutable configuration. Prepared identity includes name/options and
in-process callable identity. Bound methods identify both function and owner.
Snapshotting copies options while preserving factory ownership, so approved
execution cannot accidentally run a cloned callable with different state. This
is not a hash of executable artifacts or a sandbox for application code.

Construct the decoder after admission, before credentials and physical-attempt
observation. Request/outcome hooks and observers retain the existing safe request
boundary. Neither decoder factories nor options receive credentials or context.
Construction failure and admission retries produce no physical attempt. Lazy
streams created and closed without consumption never construct a decoder.

`feed(bytes)` emits complete events in order. On normal EOF, call `finish()` once
and route its tail through the graph. On every exit, call `close()`, close upstream
transport and flush the conversion ledger. Aborts do not call `finish` or emit a
success tail. A primary exception survives secondary cleanup failures; cleanup
failure alone fails the stream. Retain available accounting without reporting
successful StreamEnd. Streaming remains non-replayable after I/O starts.

The default adapter uses incremental UTF-8 decoding around the existing SSE
parser; no provider terminal sentinel is interpreted in wire. Raw EOF is never
proof of semantic success. Async reads use the remaining whole-call deadline;
sync reads retain cooperative timeout/check behavior. Output from feed/finish is
checked against that budget before delivery.

## Alternatives considered

- Choose framing inside each codec: couples host transport to provider meaning,
  duplicates mappings and breaks the plugin dependency boundary.
- Add required methods to Host or transport protocols: breaks existing custom
  hosts and transports when an optional selector suffices.
- Store a decoder instance on a shared host: leaks buffers across concurrent calls
  and makes inspection allocate execution resources.
- Fingerprint only the HTTP request: lets an unchanged URL/body silently approve
  a different stream interpretation. Explicit options and factory identity are
  needed in addition to the HTTP identity.

## Consequences

Recorded HTTP pairs replay a test-only length-prefixed JSON envelope over existing
Chat Completions events. They assert the same canonical fold, terminal accounting,
resource cleanup, isolation, deadlines and configuration enforcement in both
drivers. No vendor behavior is inferred from this test adapter. The recording's
`chunks_hex` field preserves binary bytes and is documented in `spec/README.md`.
The frozen-candidate gate remains ADR 0005; future non-chat capability designs
still require separate maintainer approval before implementation.
