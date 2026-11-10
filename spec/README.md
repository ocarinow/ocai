# `spec/` — the language-neutral source of truth

This directory is the **single source of truth** for ocai. Every language
implementation (Python first; TypeScript and Go later) consumes the same
normative documents, the same JSON Schema, and the same golden fixtures. If an
implementation drifts from `spec/`, its conformance suite fails — that is the
intended **drift alarm**, and CI re-runs every implementation's conformance
suite whenever `spec/**` changes.

The structural contract this spec serializes lives in
[`docs/architecture.md`](../docs/architecture.md).

## Layout

```
spec/
├── canonical-json.md   NORMATIVE: the canonical JSON form + the semantic-
│                       equality predicate every language must implement
├── schema/             JSON Schema per core contract + capability IR
│                       (see schema/README.md — regeneration in progress)
├── fixtures/           golden conversion fixtures, one per graph edge,
│                       plus fold triples per streaming edge
├── extensions/         the extension census: one JSON Schema per registered
│                       extension key (see extensions/README.md)
└── interfaces/         catalog descriptors as data: one document per
│                       (provider, interface) (see interfaces/README.md)
```

## The equality predicate comes first

Every guarantee below is stated in terms of `semantic_equal` over canonical
JSON, defined normatively in [`canonical-json.md`](canonical-json.md) (key
ordering, number normalization, NFC, absent-vs-null, the
parse-compare/preserve-verbatim rule for `*_json` fields). Read it before
authoring a fixture; implement it before anything else in a new language port.

## Fixture shapes

Draft designs live separately in [`proposals/`](proposals/ordered-items/README.md).
Their schemas and examples do not change the active canonical revision.
Proposal fixtures carry `provenance`, a candidate `schema`, and a `document`;
optional `input`/`preserved` pairs record design requirements. They are validated
by a dedicated schema suite, not treated as certified conversion edges or fold
triples. Promotion requires implemented converters and the ordinary gates below.

### Recorded binary transport pairs

Wire recordings under `python/packages/*/tests/http/` are transport tests, not new
conversion edges. WU-39 adds `response.chunks_hex`: an ordered array of hexadecimal
byte strings for a binary response, alongside HTTP status/headers and the exact
request body. Replaying `bytes.fromhex` for each entry preserves network bytes;
tests may split entries further to qualify incremental parsing. The description
must state captured versus synthetic provenance, the framing grammar, the unary
pair and the existing semantic fold triple. A synthetic framing adapter does not
qualify a vendor format. Existing JSON and `response.sse` formats stay unchanged.

### Edge fixture (one per conversion-graph edge)

```jsonc
{
  "description": "what this fixture exercises",
  "src":  {"provider": "openai", "interface": "chat_completions",
           "tag": "2026-01", "shape": "chat.request"},
  "dst":  {"provider": "ocai", "interface": "ocai",
           "tag": "2026-07", "shape": "chat.request"},
  "input":  { /* verbatim src-format payload */ },
  "expect": { /* the expected dst-format payload */ },
  "expect_losses": [           // the honest part — may be empty, never absent-by-accident
    {"path": "logit_bias", "disposition": "extensions",
     "note": "openai.logit_bias rides the censused extension"}
  ],
  "expect_shifts": [
    {"kind": "relocation", "path": "messages[0]",
     "note": "system role hoisted to systemInstruction"}
  ]
}
```

`src`/`dst` are `NodeId` coordinates (`released`/`status` MAY be omitted; they
resolve from `interfaces/`). A conforming implementation MUST satisfy, for
every edge fixture:

1. running the edge on `input` yields a value `semantic_equal` to `expect`;
2. the runtime `FieldLoss`/`SemanticShift` records match `expect_losses` /
   `expect_shifts`;
3. runtime loss never exceeds the edge's declared `EdgeContract` census — an
   edge claiming lossless that drops a field cannot ship.

Census and loss paths follow the contract path grammar (normative statement:
`EdgeContract.certify` in `ocai/convert/contract.py`): dotted member names,
concrete `[0]` indexes, the empty wildcard `[]`, and non-numeric selector
tokens (`[reasoning]`). The token `[**]` is **reserved** for recursive
descent — "this entry covers any suffix below this point", needed for
unbounded filter trees — and must not appear in a census today (the current
grammar would read it as an ordinary one-level selector); its implementation
lands with the vectorstore capability.

External plugins can package this same edge-fixture format through
`CatalogFragment.conformance`. `check_fragment` enforces coordinate matching,
coverage of every payload edge, independent expected output/records, and
contract bounds. Resources are explicitly loaded from installed package data;
no repository checkout is required. A manifest is not proof of certification.

### Fold triple (one per streaming edge)

The stream-first law `fold(stream(request)) == complete(request)` is asserted
by **fold triples** — three correlated artifacts in one fixture:

```jsonc
{
  "description": "what this stream exercises",
  "node": {"provider": "openai", "interface": "chat_completions",
           "tag": "2026-01", "shape": "chat.chunk"},
  "wire_events": ["data: {...}", "data: {...}", "data: [DONE]"],  // verbatim SSE log
  "chunks":   [ /* expected canonical ChatChunk documents, in order */ ],
  "response": { /* the ChatResponse that folding those chunks must yield */ }
}
```

A conforming implementation MUST decode `wire_events` into documents
`semantic_equal` to `chunks`, `StreamAccumulator.fold(chunks)` MUST be
`semantic_equal` to `response` (with the `raw`/`raw_event` lanes excluded, per
`canonical-json.md` §8), and every `partStop` carrying an authoritative final
part MUST have that part equal the slot's delta accumulation (the ratchet's
second clause — the harness checks it by re-folding with the finals stripped).
`wire_events` is OPTIONAL: a canonical-node triple (`node.provider == "ocai"`)
carries its chunks already canonical, so the decode leg is skipped and only
the fold clauses run. No new part type is admissible without its delta
type, its fold law, and paired chunks/response fixtures **in the same change**.

### Canonical document fixture (one canonical payload)

For pinning a single canonical-IR document — a wire-accurate example of one
shape rather than a conversion:

```jsonc
{
  "description": "what this document exercises",
  "shape": "chat.request",   // the canonical shape token
  "document": { /* the canonical payload, exactly as an omit-absent
                   to_dict() encoder emits it — no nulls, no empty bags */ }
}
```

### Normative unknown-X fixtures (unknown vectors)

`fixtures/unknown/` carries total-decode vectors every port must pass: unknown
part tags decode to `PartUnknown`, unknown deltas to `DeltaUnknown`, unknown
finish-detail tags to `DetailOpaque`, unknown envelope keys sweep into
`extensions`, unknown finish reasons decode to `reason: "unknown"` with the
`native` lane preserved, and unknown role codes are preserved verbatim. **No
decode path may ever raise on unknown input.**

Each vector is a canonical document fixture — same `shape`/`document` keys,
same schema mapping (the open schemas accept unknown content by construction)
— plus a required `expect` block declaring what total decode must do with the
unknown material:

```jsonc
{
  "description": "what unknown material this vector carries",
  "shape": "message",
  "document": { /* canonical payload with deliberately unknown content */ },
  "expect": {
    "fallbacks": [   // paths that MUST decode to the named fallback type
      {"path": "parts[1]", "type": "PartUnknown"}
    ],
    "extensions": [  // undeclared keys that MUST sweep into their owner's extensions bag
      {"owner": "", "key": "routing_tier"}
    ],
    "preserved": [   // paths whose re-encoded value MUST equal the document's, verbatim
      {"path": "role"}
    ]
  }
}
```

Paths are dot-separated member names with zero-based `[i]` indexing
(`messages[0].parts[1]`); the empty string names the document root. The three
`expect` lists are each optional and empty by default:

- **`fallbacks`** — the value at `path` in the *decoded object graph* must be
  an instance of the canonical fallback type named by `type`: one of
  `PartUnknown`, `DeltaUnknown`, `DetailOpaque`, or `SourceUnknown`. The names
  are the cross-language vocabulary; each port maps them onto its native types
  (in Python, the class name).
- **`extensions`** — `key` is not a declared member of the object at document
  path `owner`; the tolerant reader must sweep it into that object's
  `extensions` bag under the same key, where re-encoding must emit it.
- **`preserved`** — the re-encoded value at `path` must be `semantic_equal` to
  the document's value at `path` (open codes like unknown roles, the finish
  `native` lane).

A conforming implementation MUST satisfy, for every unknown vector (this is
`conformance.check_unknown_inputs`, mirrored by every language port):

1. decoding `document` never raises — total decode;
2. every `fallbacks`, `extensions`, and `preserved` expectation holds;
3. re-encoding the decoded value is `semantic_equal` to `document` *after
   applying the declared sweeps* (each `extensions` entry relocates
   `owner.key` to `owner.extensions.key`); with no sweeps declared the round
   trip is verbatim — nothing is lost on the way to a future revision that
   names the unknown material.

## How fixtures map to schemas (the validation convention)

CI validates **every** `fixtures/**/*.json` against the schemas in
`schema/` (`tests/test_spec_schemas.py` in the Python tree; every language
port mirrors the same harness). The mapping is structural — derived from the
fixture document itself, no side registry:

- **Shape → schema file.** The canonical schema for shape token `x.y` is
  `schema/x_y.schema.json` (dots become underscores): `chat.request` →
  `chat_request.schema.json`. Each schema's `$id` is
  `https://ocai.dev/spec/schema/<filename>`, and cross-file `$ref`s resolve
  against those ids.
- **Canonical document fixture** (top-level `shape` + `document`): the
  `document` payload validates against the schema for `shape`.
- **Unknown vector** (top-level `shape` + `document` + `expect`, under
  `fixtures/unknown/`): validates exactly like a canonical document fixture —
  the additive `expect` block is the total-decode contract (see "Normative
  unknown-X fixtures" above), not a validated payload.
- **Edge fixture** (top-level `src` + `dst` + `input` + `expect`): each side
  whose coordinate names the canonical interface (`provider == "ocai"`)
  validates its payload — `input` for `src`, `expect` for `dst` — against
  the schema for that side's `shape`. Provider-wire payloads are *not*
  validated against `schema/`: provider wire truth is the codec conformance
  suite's job, not the canonical schemas'.
- **Fold triple** (top-level `node` + `chunks` + `response`; `wire_events`
  optional): every entry of `chunks` validates against the canonical
  schema for `<capability>.chunk`, and `response` against the canonical
  schema for `<capability>.response`, where `<capability>` is the first
  segment of `node.shape`.

The harness fails loudly when a fixture matches none of the three kinds, or
when a payload maps to a schema file that does not exist — a fixture that
cannot be validated is a spec bug, never a skip.

### Reverse client fold triples

`openai/chat_completions/gateway/streams/` uses the same `node`, `chunks`,
`response` fold-triple core plus `src`/`dst`, expected client JSON `events`,
and `client_response`. These qualify the reverse edge without prescribing SSE
framing or inventing serving metadata. The harness compares source fold, exact
client events and report records, certifies the edge, then applies explicit
metadata/framing and proves decoded client stream equals decoded client unary.
Unknown/incomplete streams never gain successful finish frames during flush.

## Three version axes — never conflate

- **interface tag** — a provider interface's opaque dated wire revision
  (`NodeId.tag`, ordered by `released`).
- **canonical IR revision** — dated `ocai@YYYY-MM`; the canonical IR is just
  another interface named `ocai`, so IR migration is ordinary graph
  conversion with its own edge fixtures.
- **library public-API version** — semver of the shipped package.

## The schema-first change sequence

Every contract change lands in this order, in one PR where feasible:

1. **spec** — update/add the JSON Schema (additively), the extension census
   entry, or the interface descriptor; document semantics here.
2. **fixtures** — add the golden fixtures that pin the new behavior,
   including fold triples for anything streamed and unknown-X vectors for
   anything open-coded.
3. **code** — implement until the conformance suite is green.

Schemas are additive-only: nothing is renamed, removed, or repurposed; new
fields are optional; readers are tolerant. Fixtures are validated against
schemas in CI, so a spec-vs-code contradiction is structurally detectable
rather than a matter of review vigilance.

### Canonical citation evidence

`fixtures/canonical/citations/` contains canonical fold triples for URL citations,
local source-result references, open future citation kinds, Unicode code-point
positions and invalid bounds. The tests also compare exact decoded text and
positions, since canonical JSON equality normalizes Unicode. Annotations may
precede text deltas; contextual validation runs when text is final.

`ocai.annotation_invalid_span` preserves rejected raw positions with a reason;
`ocai.invalid_span` preserves a malformed standalone span; and
`ocai.annotation_unparsed_source` preserves an undecodable source-result reference.
These are evidence extensions, never valid positional or replay authority.
No provider edge or new canonical node is registered by this qualification.

### Server-tool request intent

`fixtures/canonical/server_tools.json` qualifies the open request tool union:
legacy functions remain untagged, `type: server` declares provider-executed intent,
and future/non-object tool entries retain their complete original value. Provider
request fixtures report `tools[index]` as unsupported until mapping is qualified.
`ocai.server_tool_unparsed_location` preserves uninterpreted location evidence.
The accompanying recorded unary/SSE pairs reuse the existing response fold
fixtures; this request-only change registers no streaming conversion edge.

### Replay transcript evidence

`fixtures/canonical/replay_transcript.json` uses the canonical document format
with a `history` list of preceding shape/document pairs. Its dedicated conformance
test round-trips history responses and the final request through canonical IR
serialization and compares opaque token values exactly. This is carrier evidence,
not a provider-search compatibility claim. Recorded Anthropic thinking replay
pairs separately prove the qualified wire path and existing response fold law.
`ocai.request_unparsed_anchors` retains indexed unknown/malformed continuation
input without turning unknown replay obligations into optional ones.
