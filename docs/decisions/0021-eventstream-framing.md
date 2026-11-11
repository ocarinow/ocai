# 0021 — Bounded EventStream framing with explicit partial evidence

- **Status:** accepted; corresponding implementation merged on main
- **Date:** 2026-11-11
- **Deciders:** maintainer review of WU-49

## Context

ADR 0014 permits host-selected framing without moving provider semantics into
transport. Bedrock InvokeModel streaming uses binary Amazon EventStream, so
WU-50 needs a parser before its host envelope can reach the Anthropic codec.
The [provider research §17](../research/providers/amazon-bedrock.md) records the Smithy
wire format, CRC coverage, signed timestamp encoding and service-only size limits.

## Decision

Add provisional wire values `EventStreamHeader` and `EventStreamFrame`, a sans-io
`EventStreamParser`, and `eventstream_framing(max_frame_bytes=64 * 1024 * 1024)`.
They depend only on stdlib and existing ocai contracts. No canonical node, edge,
part, schema, frozen-candidate contract or dependency changes.

Each frame retains headers in wire order, with their numeric type codes and
exact typed values. Timestamp headers retain signed integer milliseconds; UUID
headers use stdlib UUID. Payload bytes and unknown semantic event names remain
opaque. Header type codes are closed by the framing protocol. Invalid UTF-8,
duplicate/empty header names, unknown header types, impossible lengths, CRC
failures and truncated EOF are explicit `EventStreamProtocolError` failures.
This is framing validation, not canonical IR decoding.

Validate the 12-byte prelude CRC before trusting lengths; validate the message
CRC before interpreting headers. The finite configurable frame budget is local
resource policy and includes framing overhead. It bounds the parser's retained
partial frame, not caller-owned input or the list of completed output frames.
The client does not enforce the service-only 24 MiB payload and 128 KiB header
quotas. Decoded Python objects and temporary copies require additional memory
proportional to the verified frame size.

Each admitted stream gets a fresh parser through the existing StreamFraming
factory. Options contain only the explicit non-secret local budget and participate
in the existing preparation identity. No context, credential or SDK object crosses
this boundary. Closing is idempotent and clears partial bytes; failure closes the
parser. A fresh parser is required after close/failure. Successful finish is
idempotent, checks framing EOF only, and never invents provider completion.

A failed feed retains its already verified prefix frames in
`EventStreamProtocolError.completed`. Frames returned by earlier feed calls are
not repeated. Error messages contain fixed descriptions, not raw corrupt bytes.
The retained frames are explicit application evidence, not observer payload logs.
The existing driver propagates a failed feed without converting its same-batch
prefix. G-16 records that separate generic delivery/accounting gap; this ADR does
not claim chunk-independent semantic accounting or enable Bedrock streaming.

## Alternatives considered

- Parse binary data as SSE: cannot preserve typed headers or validate CRCs.
- Use an AWS SDK transport: transfers I/O ownership and couples framing to a
  provider client; the existing wire layer already owns streaming resources.
- Buffer an unlimited frame: trusts hostile lengths and removes caller control
  over resource consumption.
- Discard verified frames when a later frame fails: loses available evidence.
- Change the generic decoder/driver delivery contract in this WU: combines
  byte-level parsing with a separate semantic accounting outcome; G-16 tracks it.

## Consequences and qualification

`python/packages/ocai-core/tests/http/eventstream_frames.json` is a synthetic
recorded binary exchange with expected typed frames and corruption vectors.
`test_eventstream.py` exercises every byte split and partial EOF, all ten header
types, CRC/length/header errors, local limits, independent factories and sync/async
transport cleanup. Rule-10 recordings require no credentials or SDK mocks.

WU-50 still needs G-14 streaming host outcomes, G-16 framing-failure accounting,
provider envelope handling, and paired semantic fold fixtures. The current unary
Bedrock host continues to reject streaming before I/O. Reverting this additive
parser is sufficient; there is no persisted format or canonical migration.
