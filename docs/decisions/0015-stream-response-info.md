# 0015 — Preserve response identity through canonical streams

- **Status:** accepted direction; implementation for review
- **Date:** 2026-11-11
- **Deciders:** maintainer

## Context

G-11 exposed a mismatch between architecture §3.1's full fold law and execution
checks that remove ResponseInfo before comparing. Unary OpenAI and Anthropic
responses already populate this type; their streams have no typed carrier.
DeepSeek qualification exposed the shared gap. The maintainer approved the
reusable carrier resolution rather than weakening equality.

## Decision

1. Add optional keyword-only `ChatChunk.info: ResponseInfo | None`. Keep the
   existing type/name and optional fields (scoped response id, model echo, provider
   timestamp). Old chunks without it remain valid. No new part/delta is needed:
   this describes the response envelope, not generated content.
2. Codecs emit canonical METADATA events with populated info independently of
   content, start and terminal events. Accumulation accepts an info lane wherever
   present, allowing old event producers and late metadata without buffering
   content. No client-side clock, request alias or synthetic response id fills a
   missing field.
3. Accumulation owns detached copies. A missing field can be filled later;
   semantically equal repeats are idempotent. Conflicting populated values retain
   the first value and preserve each distinct alternative under the registered
   `ocai.response_info_conflicts` extension with a source path, while adding an
   EXTENSIONS FieldLoss to the fold report. No silent last-write-wins. This is
   evidence-bearing completion, not an automatic provider retry or invented error.
4. Available info survives incomplete streams. It neither creates a successful
   StreamEnd nor changes finish/usage. Existing response-policy mechanisms can
   reject findings; this does not promise an accumulator report is evaluated by
   a caller that never folds a stream.
5. ResponseInfo's tolerant reader retains malformed known fields and envelope
   values under `ocai.response_info_unparsed`; unknown keys follow the existing
   extension sweep. Non-object chunk info is retained under
   `ocai.chunk_info_unparsed`. Accumulation reports this fallback evidence. No
   exception or silent timestamp loss is introduced on this newly qualified path.
6. Qualify existing OpenAI and Anthropic stream edges with censuses and complete
   fold triples, preserving recorded wire inputs and strengthening expected
   canonical outputs. Identity becomes part of paired unary equality. Existing
   canonical-to-client stream encoding must report any new lane it cannot encode.
7. This is an additive frozen-candidate change under ADR 0005, not a new canonical
   node/revision or a change to the freeze gate. Other capability interfaces and
   metadata beyond the existing ResponseInfo responsibilities remain separately
   reviewed designs.

## Alternatives considered

- Exclude info from the public fold guarantee: rejected in favor of a complete
  canonical result, avoiding gateway-side provider parsing.
- Rename only the streaming lane metadata: two names for one existing type.
- Put identity in StreamEnd: prevents early use and loses the clean incomplete
  stream path; terminal success is independent of knowing response identity.
- Overwrite on conflicting updates: conceals contradictions. Raising on decode
  conflicts would violate the tolerant data-decoding contract.

## Consequences

WU-46a owns the carrier, schemas, evidence and existing-provider qualification;
WU-46 consumes it for DeepSeek. Optional-field growth is compatible with older
chunks; updated stream decoders can emit additional METADATA events, so consumers
must use event kinds rather than assume a fixed event count. Conflict evidence
is explicit and may be rejected by caller policy when the fold report is used.
