# `spec/extensions/` — the extension census

**Status: placeholder — format normative, census population pending.**

This directory is lane 2 of the three-lane knob law
([`docs/architecture.md`](../../docs/architecture.md) §3.4): a
**censused extension** is provider-unique data that is not (yet) a
first-class canonical field but *is* schema-registered here. The census is
what keeps the `extensions` bag honest: **an extension key that appears in a
codec, a fixture, or a shipped payload without a schema in this directory is
a CI failure.** The bags can never silently become the real schema.

## Census format

One JSON Schema file per registered extension key. The file name **is** the
key:

```
spec/extensions/<namespace>.<key>.schema.json
```

- `namespace` is the owning provider or distribution (`openai`,
  `anthropic`, `contrib.echo`); bare (un-namespaced) keys are reserved for
  core and never registered here.
- The schema describes **the value stored under that key** in an
  `extensions` bag, not the bag itself.
- Required schema annotations:
  - `title` — the extension key, verbatim;
  - `description` — what the data means and which interface(s) emit it;
  - `x-ocai-origin` — the registering distribution (`"ocai-openai"`);
  - `x-ocai-promotion` — one line on the pre-registered trigger that would
    promote this key to a first-class field (or `"none expected"`).

## Worked example

`spec/extensions/openai.logit_bias.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "openai.logit_bias",
  "description": "Token-id -> bias map accepted by openai/chat_completions. Provider-unique sampling control; rides ChatRequest.extensions when converting toward canonical so the field survives a round-trip without pretending to be portable.",
  "x-ocai-origin": "ocai-openai",
  "x-ocai-promotion": "promote if a second interface ships congruent per-token biasing",
  "type": "object",
  "propertyNames": { "pattern": "^[0-9]+$" },
  "additionalProperties": { "type": "number", "minimum": -100, "maximum": 100 }
}
```

A codec that decodes `logit_bias` then stores it as
`extensions["openai.logit_bias"]`, reports the field with disposition
`EXTENSIONS` in its `EdgeContract`, and its golden fixtures pin both the
value and the loss record.

## Rules

- Keys are namespaced, dot-joined, and never renamed; retiring one is an
  annotation (`"deprecated": true` in the schema), never a deletion.
- Registering a key here is *cheap on purpose* — the pressure this census
  applies is visibility, not gatekeeping. Promotion to a first-class field
  goes through the lane-1 checklist instead.
- CI validates every `extensions` bag appearing in `spec/fixtures/` against
  this directory.
