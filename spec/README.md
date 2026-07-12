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
`semantic_equal` to `chunks`, and `StreamAccumulator.fold(chunks)` MUST be
`semantic_equal` to `response` (with the `raw`/`raw_event` lanes excluded, per
`canonical-json.md` §8). No new part type is admissible without its delta
type, its fold law, and paired chunks/response fixtures **in the same change**.

### Normative unknown-X fixtures

`fixtures/` also carries total-decode vectors every port must pass: unknown
part tags decode to `PartUnknown`, unknown deltas to `DeltaUnknown`, unknown
envelope keys sweep into `extensions`, unknown finish reasons decode to
`reason: "unknown"` with the `native` lane preserved. **No decode path may
ever raise on unknown input.**

> Status: the fixtures currently in `fixtures/` predate the July 2026
> re-architecture (old flat-`content` IR, `(provider, version)` sources).
> They are stale-pending-regeneration against the new shapes, alongside
> `schema/` — kept until the regenerated set lands so history stays diffable.

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
