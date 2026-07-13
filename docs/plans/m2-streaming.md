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
- **Decision:** the fold's reporting channel is ONE `EdgeReport`
  (`CANONICAL_CHAT_CHUNK → CANONICAL_CHAT_RESPONSE`, note "stream fold")
  collecting `FieldLoss` records for every delta the accumulator could not
  apply — mismatched delta/part pairs, `DeltaUnknown`, and the
  not-yet-accumulated `DeltaBlob` all record `DROPPED` (reported, never
  silent). `finalize` merges it into the terminal `StreamEnd.report` exactly
  once (idempotent across re-finalize); an aborted stream's losses stay
  reachable on the new `StreamAccumulator.report` property.
- **Decision:** `DeltaSignature` fragments buffer per slot as an opaque
  string; at seal, a codec-minted final `signature` ref subsumes the buffer,
  otherwise the verbatim concatenation is preserved under the censused
  `extensions["ocai.signature_buffer"]` with an `EXTENSIONS` record — the
  accumulator never mints a `ProviderRef` (it has no (provider, interface)
  context; the codec transducer stays the sole minter). Aborted-stream
  sealing marks only the slots no `PART_STOP` sealed, and only when no
  `STREAM_STOP` arrived, with `extensions["ocai.incomplete"] = true`; both
  keys are registered in `spec/extensions/`.
- **Decision:** `FidelityReport.from_dict` (plus `EdgeReport`/`FieldLoss`/
  `SemanticShift` twins, all additive) reads only `edges` — `path`,
  `lossless`, `total_cost`, and per-edge `cost` are derived views recomputed
  on replay, never trusted from data. Node labels parse back totally
  (`released` re-derived from dated tags, `date.min` sentinel otherwise;
  malformed labels land whole in `provider`); an unknown disposition code
  decodes to `DROPPED` — a replayed report may overstate loss, never
  understate it.
- **Decision:** the fold-triple contract makes `wire_events` optional
  (canonical-node triples carry already-canonical chunks; the decode leg is
  skipped, the fold leg is mandatory) — `spec/README.md` and the validator
  harness detection updated accordingly. The PART_STOP clause is enforced
  structurally: strip the authoritative final from every *delta-fed*
  `partStop` and assert the re-fold still reproduces the response (vacuous
  for delta-less slots, where the final is the part's only carrier). The
  harness speaks plain dicts (`decode_event`/`fold` wrap the codec and
  `StreamAccumulator.fold`), staying capability-neutral. `chat_chunk.
  schema.json` `$ref`s `deltas.schema.json`/`usage.schema.json`/
  `finish.schema.json`/`parts.schema.json`; the serialized-report `$defs`
  live in `stream_end.schema.json`.

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
- **Decision:** the composite is a concrete `StreamPipeline` (not a
  `StreamConverter` — its `flush` returns one `EdgeReport` **per stage**, in
  path order, preserving per-edge attribution for `FidelityReport.edges`).
  Flush reports reach the facade by being **exposed on
  `StreamPipeline.reports` after flush** rather than as a generator return
  value: async generators cannot return values, and the exposure keeps the
  sync/async driver twins identical. The driver takes
  `pipeline: StreamPipeline | None` (replacing the never-called
  `transducers: Sequence[StreamEdge]` seam sketch), flushes exactly once at
  end-of-stream (tail yielded), and flushes on the mid-stream error path too
  (tail undeliverable while raising; accounting preserved). Freshness lives
  in `stream_converter`: the *plan* is cached per `(src, dst)`,
  `StreamEdge.build()` runs per planned edge per call. Double-flush raises
  `RuntimeError`.

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

- **Scope:** `ocai/chat/facade.py` — `stream`/`astream`: encode via graph;
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
- **Decision:** undeclared feature keys resolve **NATIVE** — profiles declare
  EXCEPTIONS; the absence of a declared limitation is not a limitation (keys
  are open data, so the opposite default would demand enumerating an
  unbounded universe, and NATIVE-by-default is what keeps profiles additive).
  Layering: `Catalog.profiles_for` returns matches most-specific-first
  (specificity = literal-prefix length before the first wildcard; ties keep
  admission order), and `ocai.core.profile.resolve_support` takes the first
  profile *declaring* the key — a specific sheet silent about a key never
  masks the interface-wide sheet. `Catalog.profile` is the ranking's head.
  The scaffold's `CapabilityProfile.resolve` stub shipped implemented as
  `check_feature` (the plan's name; nothing referenced the stub, and it
  avoids overloading `Catalog.resolve`).
- **Decision:** gate mode is a plain `WireChatModel(strict: bool = False)`
  ctor flag — annotate is the default; a richer fidelity-policy enum can
  supersede it additively. Strict raises the new `UnsupportedFeatureError`
  (taxonomy + `ocai.core` export; carries `features`/`model`/`provider`)
  from `_prepare` after resolve and BEFORE `catalog.convert` — proven by a
  spy catalog recording zero converts and respx recording zero wire calls.
  Annotate mode emits one gate `EdgeReport`
  (`CANONICAL_CHAT_REQUEST → route.node`, note `"feature gate (pre-encode)"`)
  with a `FieldLoss(UNSUPPORTED)` per occurrence, merged AHEAD of the encode
  leg; the payload still goes out **verbatim** — never stripped, never
  clamped — the report warns, the provider stays authoritative.
- **Decision:** the request census (`_request_features`) derives
  `(feature key, canonical path)` pairs for every set config knob, the
  reasoning dials, `output.mode` json/json_schema, `chat.tools` /
  `chat.tools.parallel`, and the gated part kinds (image/audio/video/
  document, reasoning-in-request = `chat.parts.reasoning.replay`); keys the
  plugins never declare resolve NATIVE, so the census may safely name more
  than any profile does.
- **Decision:** OpenAI reasoning census = two profiles (`o*`, `gpt-5*`)
  sharing one fact sheet (fnmatch has no alternation): temperature/top_p
  ABSENT, `reasoning.effort` NATIVE. Anthropic census = one class pattern
  `claude-opus-4-[678]*` with temperature plain ABSENT (extend the class as
  families ship); top_p stays NATIVE via the `"*"` sheet — the documented
  temperature/top_p mutual exclusion is a cross-knob constraint the
  per-feature gate deliberately does not model (top_p alone is accepted;
  declaring it ABSENT would refuse valid requests).
