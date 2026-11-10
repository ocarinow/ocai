---
name: add-edge
description: Add or change a conversion edge in ocai — codec mapping, EdgeContract census, golden fixtures, fold triples for streaming, conformance certification, extension registration. Use whenever a provider interface gains a request/response/chunk mapping, a census is tightened, or a fixture is added.
---

# Add a conversion edge

An edge converts one `NodeId` shape into another and **declares what it
costs**. It ships in one change with: the mapping, the census, the fixtures,
and the certification test. None of the four lands alone (rule 9).

Reference implementation to copy from: `python/packages/ocai-anthropic/src/ocai/anthropic/messages/` (`codec.py` + `edges.py`) and its `tests/test_conformance.py`.

## 1. Name the two nodes

Source and destination are `NodeId(provider, interface, tag, shape)`.
One side is normally canonical: `provider="ocai", interface="ocai", tag=<current canonical revision>`. Constants for the canonical nodes live in `ocai.chat` (`CANONICAL_CHAT_REQUEST`, `CANONICAL_CHAT_RESPONSE`, …); the provider nodes are defined in the plugin's `codec.py`.

Graphs never mix shapes: a `chat.request` edge never produces a `chat.response`.

## 2. Write the fixture first

Location: `spec/fixtures/<provider>/<interface>/<descriptive_name>.json`.
Shape (normative, `spec/README.md` → "Edge fixture"):

```jsonc
{
  "description": "what this fixture exercises",
  "src": {"provider": "...", "interface": "...", "tag": "...", "shape": "chat.request"},
  "dst": {"provider": "ocai", "interface": "ocai", "tag": "2026-07", "shape": "chat.request"},
  "input":  { /* verbatim src payload */ },
  "expect": { /* expected dst payload */ },
  "expect_losses": [ {"path": "...", "disposition": "extensions", "note": "..."} ],
  "expect_shifts": [ {"kind": "relocation", "path": "...", "note": "..."} ]
}
```

- `expect_losses` and `expect_shifts` are **always present**, even when
  empty: an absent list is indistinguishable from an unexamined one.
- The canonical side must be an omit-absent document: no nulls, no empty
  bags. CI validates it against `spec/schema/<shape>.schema.json`.
- No `model` member in a canonical request (architecture §3.4): the wire
  `model` is injected by the codec's `bind_resource`, below the edge.
- One fixture per behavior: plain text, tool round, system relocation,
  out-of-range knob, extension sweep, error mapping. Name files by behavior.

## 3. Declare the census in `edges.py`

```python
ENCODE_REQUEST_CONTRACT = EdgeContract(
    census={
        "messages[].role": DeclaredDisposition(Disposition.EXACT),
        "messages[system]": DeclaredDisposition(Disposition.RENAMED),
        "config.temperature": DeclaredDisposition(Disposition.APPROXIMATED),
        "config.logit_bias": DeclaredDisposition(Disposition.EXTENSIONS),
        ...
    },
    semantic_shifts=(SemanticShift(kind=ShiftKind.RELOCATION, path="messages[system]", note="..."),),
)
```

Dispositions, from best to worst: `EXACT, RENAMED, APPROXIMATED, EMULATED,
EXTENSIONS, DROPPED, UNSUPPORTED`. Rules that are not negotiable:

- The census is an **upper bound over every payload the edge may see**. A
  knob the wire range-limits declares `APPROXIMATED` even though in-range
  values are `EXACT` at runtime (certification accepts a strictly better
  runtime disposition, never a worse one).
- A field with no wire lane is `DROPPED` or rides a **registered**
  extension: add `spec/extensions/<provider>.<key>.schema.json` in the same
  change; an unregistered key fails CI.
- Structural relocation, emulation, id regeneration, and injected defaults
  are `SemanticShift`s, not field losses (§2.2) — declare them on the
  contract so the runtime record can match.
- Path grammar: dotted members, `[0]` concrete index, `[]` wildcard,
  `[selector]` non-numeric token. `[**]` is reserved; do not use it.
- Tighten the census in the same change that tightens the mapping; never
  declare better than the code does.

## 4. Implement the mapping in `codec.py`

- Pure, synchronous, no I/O. Emit a `FieldLoss` for every census row the
  payload exercises with a disposition other than `EXACT`, and the declared
  `SemanticShift` whenever its condition fires.
- Out-of-range values pass **verbatim** with an `APPROXIMATED` loss; never
  clamp or rescale (rule 5).
- Decode direction is total (rule 6): unknown wire keys sweep into
  namespaced `extensions`, unknown enum values keep the `native` lane,
  unknown blocks become `PartUnknown` / `DeltaUnknown`. A decode path that
  can raise on input is a bug.
- `ProviderRef`s are minted with their `(provider, interface)` scope; a ref
  from another scope is `UNSUPPORTED`-and-reported, never forwarded.

## 5. Register the edge

In `edges.py`, append an `Edge(src, dst, fn, contract, origin=ORIGIN)` to
the frozen `EDGES` tuple (a `StreamEdge` for chunk shapes). The package
`__init__` folds the tuples into the exported `CatalogFragment`; nothing
mutates shared state at import time (rule 14).

## 6. Streaming edges ship the fold triple

For a `chat.chunk` edge, add `spec/fixtures/<provider>/<interface>/streams/<name>.json`:

```jsonc
{
  "description": "...",
  "node": {"provider": "...", "interface": "...", "tag": "...", "shape": "chat.chunk"},
  "wire_events": ["data: {...}", "..."],      // verbatim SSE log
  "chunks": [ /* expected canonical ChatChunk docs */ ],
  "response": { /* what StreamAccumulator.fold(chunks) must equal */ }
}
```

The paired unary fixture's `expect` must be `semantic_equal` to this
`response` (the fold law, rule 7). A new part type is inadmissible without
its delta type, fold law, and triple in the same change.

## 7. Certify in the plugin's `tests/test_conformance.py`

Three assertions per edge, using `ocai.convert.conformance`:

```python
check_edge(edge, fixture)              # output semantic_equal to expect; losses/shifts match exactly
assert certify_edge(edge, payloads) == []   # runtime loss ⊆ declared census
check_fold_triples(stream_edge, triples)    # streaming only
```

Plus the catalog round trip: the same fixture converts through a `Catalog`
built from the real `FRAGMENT`, proving the planner routes through the
certified edge. Recorded wire pairs for the facade live in
`python/packages/ocai-core/tests/http/`; never a live key, never an SDK mock
(rule 10).

## 8. Verify and document

```bash
uv run python scripts/check.py
```

Then: `spec/README.md` if a fixture kind changed; the plugin section of
`docs/architecture.md` (§7) if the plugin's surface changed; the WU's
**Decision** bullet for any census judgment call (precedent: the
census-upper-bound and max_tokens-injection decisions in
`docs/plans/m3-second-provider.md`).
