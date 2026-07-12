# M2 — Streaming with honesty parity

Goal: the fold law demonstrated at the port —
`fold(model.stream(req)) == model.chat(req).value` on a paired recorded
exchange, with every stream ending in `StreamEnd(usage, finish, report)`.
Architecture refs: §3.1 (stream types + fold law), §4.1 (StreamEdge), §5
(driver pump), rule 7.

Track D (WU-08, WU-09, WU-10) is file-disjoint from the M1 spine and can run
in parallel sessions/branches; WU-11 joins the tracks.

---

## WU-08 — Fold law hardening + streaming spec shapes

- **Scope:** `ocai/chat/types/stream.py` — close the accumulator TODOs:
  aborted-stream sealing (open parts sealed with `extensions["ocai.incomplete"]`,
  stream.py:733); mismatched-delta/`DeltaUnknown` reporting channel
  (stream.py:698); `DeltaSignature` buffering decision (stream.py:689);
  `FidelityReport.from_dict` for recorded-`StreamEnd` replay (stream.py:495).
  `ocai/convert/conformance.py` — implement `assert_fold_triple` (both legs +
  the PART_STOP-final-part-MUST-equal-accumulation clause), unlocking
  `check_fold_triples`. `spec/schema/` — `chat_chunk.schema.json` +
  `stream_end.schema.json`. One hand-authored minimal fold triple
  (echo/canonical) as the harness self-test.
- **Done:** `assert_fold_triple` implemented; `tests/test_fold_law.py` ≥8
  cases (aborted-stream sealing, implicit PART_START tolerance, authoritative
  PART_STOP part, StreamEnd overriding mid-stream usage/finish,
  PART_STOP-vs-accumulation mismatch detection); chunk fixtures validate
  against the new schemas; pytest green.
- **Deps:** WU-02 (validator harness). Fully parallel with WU-06/07.

## WU-09 — Stream conversion joins the graph

- **Scope:** `ocai/convert/graph.py` — `stream_converter` (graph.py:374):
  Dijkstra over stream edges with the same `LossGrade` and a separate plan
  cache; composite pipeline chaining `edge.build()` per planned edge (feed
  pipes stages in order; flush drains front-to-back concatenating
  `EdgeReport`s). `ocai/runtime/drivers.py` — replace the transducer
  `NotImplementedError` in both stream methods: pump `SSEvent`s through the
  composite; settle the seam: **driver yields converted events + returns flush
  reports; the facade stamps `StreamEnd.report`**.
- **Done:** no `NotImplementedError` in `graph.stream_converter` or the driver
  pumps; `tests/test_stream_planning.py` (grade-based multi-hop stream path
  choice, determinism, per-traversal transducer freshness) + a driver pump
  test over a fake `SyncTransport` streaming recorded SSE bytes into canonical
  chunks; pytest green.
- **Deps:** WU-00 (mechanics exist); WU-08 soft (the StreamEnd seam).
  Independent of WU-06/07 and of WU-08's accumulator work.

## WU-10 — OpenAI streaming codec completion + fold-triple fixtures

- **Scope:** `ocai/openai/chat_completions/codec.py` — the streaming TODOs:
  split multi-signal frames (role+content, id+arguments — codec.py:765/845);
  emit the terminal STREAM_STOP with `StreamEnd(usage, finish)` (codec.py:862);
  n>1 stream admission stance (codec.py:727). Record real SSE logs into
  `spec/fixtures/openai/chat_completions/streams/` as fold triples (≥3: text
  stream; tool-call args stream; usage-in-final-chunk via `stream_options`),
  at least one **paired** with a recorded unary response for the same request.
- **Done:** `check_fold_triples` green over the new directory using
  `StreamAccumulator.fold`; for the paired fixture, `fold(chunks)` is
  `semantic_equal` to the recorded unary canonical — the fold law on real wire
  data; ocai-openai tests extended; pytest green.
- **Deps:** WU-08 (harness + chunk schemas). Independent of WU-09.
- **Split flag:** if recording + frame-splitting both overrun, split (a) codec
  frame handling with unit tests, (b) the fixture set.

## WU-11 — Facade streaming: `stream/astream` — **MILESTONE M2**

- **Scope:** `ocai/chat/model.py` — `stream`/`astream`: encode via graph;
  `catalog.stream_converter(wire chunk node → canonical chunk node)`; driver
  stream pump; wrap in `ChatStream`/`AsyncChatStream` (verify
  `.end`-after-iteration); `StreamEnd.report` = request-leg report +
  transducer flush reports.
- **Done:** `model.stream(req)` over a recorded SSE exchange yields canonical
  chunks whose terminal chunk carries `StreamEnd(usage, finish, report)`;
  `StreamAccumulator.fold(chunks)` is `semantic_equal` to
  `model.chat(req).value` on the paired recording — **the fold law at the
  port**; `astream` twin; a recorded mid-stream error maps to the taxonomy
  with wire shape (rule 8); pytest green.
- **Deps:** WU-07, WU-09, WU-10.

## WU-12 — Profile gate

- **Scope:** `ocai/core/profile.py` — `matches` (fnmatch on model_pattern) +
  `check_feature`; `ocai/convert/catalog.py` — `profiles_for`
  (catalog.py:639); the facade consults the gate **before** payload
  conversion: strict mode raises a typed error (add `UnsupportedFeatureError`
  to the taxonomy if absent), annotate mode records the loss into the report.
  Flesh out the OpenAI reasoning-model profile (edges.py:234 —
  temperature/top_p rejected on o*/gpt-5*) and the Anthropic
  temperature-rejection census (edges.py:245).
- **Done:** no `NotImplementedError` in `profile.py`/`profiles_for`; tests:
  strict-refuse vs annotate-report for a gated knob; model-pattern matching
  cases; a facade test proving the gate runs before encode; pytest green.
- **Deps:** WU-07.
