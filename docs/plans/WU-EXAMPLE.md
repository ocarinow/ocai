# Work unit entry — filled example

A complete entry that passes `scripts/board_sync.py check`, written against
[`WU-TEMPLATE.md`](WU-TEMPLATE.md). The subject is real (gap G-11, the
response-identity decision card) but the numbers, names, and tests below are
**illustrative**: copy the shape, not the content. Mandatory bullets appear
in template order; the optional ones are present because this change has a
code surface, changes an existing behavior, and can be reproduced offline.

```markdown
## WU-EX — Carry response identity through the canonical stream

- **Status:** ⬜ defined
- **Context:** `fold(stream(request))` must equal `complete(request)`
  (architecture §3.1), yet a folded stream has no `info` while the unary
  response carries `ResponseInfo(id, model, created)`. The existing OpenAI
  facade test hides this by deleting `info` from both sides before
  comparing. Gap G-11 reproduced it on checked-in recordings; the decision
  card "Preserve response identity in stream folding" chose the carrier
  option. Until this lands, every streaming qualification (WU-46 onward)
  certifies a weaker law than the one the spec states.
- **Goal:** A canonical stream carries the provider's response identity, so
  folding a recorded stream yields a `ChatResponse` whose `info` equals the
  paired unary response's, and gateways correlate, audit, and replay from
  one result shape without parsing provider frames.
- **Scope:** `ocai.chat.types.stream` (`ChatChunk`, `StreamAccumulator`),
  `spec/schema/chat.chunk.schema.json`, the OpenAI and Anthropic stream
  transducers and their censuses, fold-triple fixtures for three providers,
  `docs/architecture.md` §3.1 and §3.3. About 15 non-mechanical files.
- **Non-goals:** DeepSeek streaming itself (WU-46 consumes this). Replay
  through `previous_response_id` on interfaces that support it (horizon;
  needs its own census). Changing `StreamEnd` (identity belongs to the
  response, not to the usage/finish/fidelity envelope).
- **Acceptance:**
  - A recorded OpenAI stream folds to a response whose `info` equals the
    paired unary `info`, with only `raw`/`raw_event` excluded —
    `python/packages/ocai-core/tests/test_fold_law.py::test_fold_preserves_response_info`
  - Same for Anthropic Messages —
    `python/packages/ocai-anthropic/tests/test_conformance.py::test_fold_info_parity`
  - Metadata arriving late or on repeated frames with identical values folds
    once; conflicting values surface as `SemanticShift` evidence, never a
    silent overwrite —
    `spec/fixtures/openai.chat_completions/stream_info_conflict.json`
  - An incomplete stream keeps the identity it saw without manufacturing a
    completion — `test_streaming.py::test_partial_stream_keeps_info`
  - Old chunks without `info` still decode (total decode, rule 6) —
    `test_unknown_inputs.py::test_chunk_without_info`
  - The `_assert_fold_law` helper no longer strips `info` —
    `test_facade_stream.py`
- **Done:** Every paired recording folds to `semantic_equal(folded, unary)`
  with only raw evidence excluded, including `info`, and the conflict,
  late-metadata, and partial-stream fixtures pass on OpenAI and Anthropic.
- **Deps:** ADR for the carrier shape (accepted in the entry PR); none else.
- **Architecture:** §3.1 (canonical response and fold law), §3.3 (stream
  framing and accumulation).
- **Integration:**
  - Layer: `ocai.chat` (IR) and the two plugins `ocai.openai.chat_completions`,
    `ocai.anthropic.messages`; arrows unchanged (plugins → core + convert).
  - Modules: `chat/types/stream.py` (field + fold state), each plugin's
    `codec.py` stream transducer (mint `info` from the first frame),
    `spec/schema/chat.chunk.schema.json`.
  - Flow: SSE frame → transducer decodes id/model/created → `ChatChunk(info=…)`
    on the STREAM_START (or first carrying) event → `StreamAccumulator.feed`
    records it → `finalize()` sets `ChatResponse.info`.
  - Diagram:
    ```mermaid
    sequenceDiagram
      participant W as SSE frames
      participant T as StreamTransducer
      participant A as StreamAccumulator
      W->>T: {id, model, created, choices…}
      T->>A: ChatChunk(STREAM_START, info=ResponseInfo)
      T->>A: ChatChunk(PART_DELTA …)
      A->>A: finalize() → ChatResponse(info, message, finish, usage)
    ```
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class ChatChunk:
      type: ChunkType
      ...
      info: ResponseInfo | None = None   # NEW, optional, additive

  class StreamAccumulator:
      def feed(self, chunk: ChatChunk) -> None:
          if chunk.info is not None:
              self._info = _merge_info(self._info, chunk.info)  # identical → keep; conflict → SemanticShift
      def finalize(self) -> ChatResponse:
          return ChatResponse(info=self._info, message=..., finish=..., usage=...)
  ```
  Schema: `chat.chunk.schema.json` gains an optional `info` referencing
  `response-info.schema.json`; no required-field change.
- **Before / after:**
  | Field | Unary today | Folded today | Folded after |
  |---|---|---|---|
  | `info.id` | scoped `ProviderRef` | absent | same reference |
  | `info.model` | provider echo | absent | same echo |
  | `info.created` | UTC timestamp | absent | same timestamp |
  | `raw`/`raw_event` | body | frames | unchanged, excluded from equality |
- **Alternatives considered:** Projection — amend the fold law to exclude
  `info` (benefit: no schema change; cost: unary and folded results stay
  observably different, every fidelity claim must carry the caveat).
  Rejected by the decision card. Carrying identity on `StreamEnd` (benefit:
  one event; cost: identity is not usage/finish accounting and would be
  absent on an incomplete stream).
- **Reproduce:**
  ```bash
  uv run python - <<'PY'
  # folds the checked-in OpenAI SSE recording and compares with its paired unary body
  ...
  print('Equality excluding only raw evidence:', semantic_equal(actual, expected))  # False today, True after
  PY
  ```
- **Freeze:** additive change to the chat IR (`ChatChunk.info`) under ADR
  NNNN; frozen-candidate surface, before the v0.2 gate.
- **Decision (carrier over projection):** settled by the decision card and
  ADR NNNN; the field is optional and additive.
- **Decision (conflict handling):** identical repeats merge silently;
  differing values are reported as a `SemanticShift` on the fold report,
  the first value wins in `info` (rule 5: visible, never silent).
- **Risks:** A provider that emits a different `model` on the last frame
  (observed on some gateways) would flag every stream; bounded by the
  conflict fixture and by scoping the comparison per field. Rollback: revert
  is enough (optional field, no migration).
- **Dependency impact:** unblocks WU-46 (DeepSeek streaming); WU-47 is
  sequenced after WU-46 by plan order only.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** chat IR
- **Priority:** P1
- **Tier:** 1
- **Owner:** unassigned
```

What the check enforces on this entry: every mandatory bullet present and
non-empty (Evidence may be the placeholder while the row is ⬜ or 🔄);
**Design sketch** present with content; **Alternatives considered** present
because a Decision bullet cites an ADR number that does not exist yet
(`NNNN`); **Acceptance** has at least one item naming a test path. When the
row flips to ✅, Evidence must carry the `gate: <sha> …` line.
