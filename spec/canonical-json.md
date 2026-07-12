# Canonical JSON and semantic equality

**Status: NORMATIVE.** This document defines the one canonical JSON form and
the one semantic-equality predicate that every ocai implementation (Python,
TypeScript, Go) MUST implement identically. Every conformance guarantee in
this repository — golden edge fixtures, round-trips, fold triples, the
cross-language drift alarm — reduces to "semantic equality over canonical
JSON", so the rules are defined exactly once: here, mirrored by
`ocai.core.canonjson` in Python (`canonical(obj) -> str`,
`semantic_equal(a, b) -> bool`) and by the equivalent modules in each language
port. An implementation MUST NOT invent its own variant.

The key words MUST, MUST NOT, SHOULD, and MAY are to be interpreted as in
RFC 2119.

## 1. Scope

Two functions are specified:

- `canonical(value) -> string` — serialize a JSON document to its single
  canonical text.
- `semantic_equal(a, b) -> boolean` — decide whether two JSON documents mean
  the same thing.

`semantic_equal(a, b)` is **not** `canonical(a) == canonical(b)`: the
embedded-JSON rule (§7) applies only to equality, never to serialization.
Everything else is shared between the two.

Inputs are JSON documents (the result of parsing JSON text) or in-memory IR
values; an implementation MAY accept native IR objects by first converting
them through their omit-absent `to_dict` form (§6).

## 2. Serialization form

Canonical text MUST be encoded as UTF-8 and MUST contain:

- no insignificant whitespace (separators are exactly `,` and `:`);
- object members sorted per §3;
- strings escaped minimally: only `"` (`\"`), `\` (`\\`), and control
  characters U+0000–U+001F (shortest form, `\n` `\t` `\r` `\b` `\f` where
  available, `\uXXXX` otherwise) are escaped. Non-ASCII characters MUST be
  emitted as literal UTF-8, never `\u`-escaped.

## 3. Key ordering

Object members MUST be sorted by the Unicode **code point** sequence of their
keys, after NFC normalization (§5).

> Note: this deliberately differs from RFC 8785 (JCS), which sorts by UTF-16
> code units and therefore orders keys above the Basic Multilingual Plane
> differently. ocai chooses code-point order because it is the natural string
> order in Python and Go and is trivially reproducible in every language.
> This is a settled decision; do not "align with JCS" later.

## 4. Numbers

- Booleans are booleans; they MUST NOT be treated as the numbers 0 and 1.
- A floating-point value that is integral denotes the same number as the
  integer: `1.0` and `1` are semantically equal, and canonical text MUST emit
  the integer form (`1`). Negative zero normalizes to `0`.
- Integers MUST be emitted without fraction, exponent, or leading zeros.
- Non-integral numbers MUST be emitted as the shortest decimal string that
  round-trips to the same IEEE-754 binary64 value (the ECMA-262
  `Number::toString` algorithm, as used by RFC 8785).
- `NaN` and `Infinity` are not JSON; an implementation MUST reject them with
  an error rather than emit or compare them.

## 5. Unicode

Every string — object keys and string values alike — MUST be normalized to
Unicode Normalization Form C (NFC) before sorting, serialization, and
comparison. Two strings that differ only in normalization form are
semantically equal.

## 6. Absent versus null

An **omitted** member and a member **present with value `null`** are
**different documents**: `{}` and `{"a": null}` MUST NOT compare equal.

This is what makes the omit-absent encoding rule meaningful: IR `to_dict`
encoders MUST omit members whose value is absent (unset optionals, empty
`extensions`/`provider_options` bags), so "absent" is expressible, and an
emitted `null` is always deliberate and always preserved. Consequences:

- Fixture authors MUST NOT pad canonical-form documents with `null` or
  empty-bag members that an omit-absent encoder would not emit.
- Adding a new optional field to the IR never invalidates an existing
  fixture, because the field is absent from both sides.

## 7. Embedded JSON string fields (`*_json`)

Some IR fields carry JSON *as a string* because the string is the wire truth
— the normative example is `PartToolCall.args_json`, which every provider
streams as text fragments. For any member whose key ends in `_json`:

- **Preserve verbatim** — `canonical` MUST keep the string value byte-faithful
  (after NFC, as any string). Serialization MUST NOT parse, reformat, minify,
  or re-order it. ocai never rewrites wire bytes.
- **Parse-compare** — `semantic_equal` MUST parse both sides as JSON and
  compare the parsed values under the full rule set (recursively, including
  this rule). Two different serializations of the same arguments object are
  therefore equal, and fixture authors need not reproduce a provider's exact
  argument spelling.
- If either side fails to parse as JSON, both sides MUST be compared as plain
  NFC strings (a partial fragment of streamed arguments is still a legal
  value mid-stream).

The `_json` suffix is the complete trigger; there is no side registry of
field names.

## 8. Fold-fixture equality

A **fold triple** fixture (see `spec/README.md`) asserts the stream-first
law `fold(stream(request)) == complete(request)`. Its equality checks are
defined in terms of `semantic_equal` with one carve-out:

- The `raw` member of a response and the `raw_event` member of a chunk are
  **verbatim provider lanes**, not canonical content. They MUST be excluded
  from fold-fixture comparison (implementations compare the documents with
  those members removed at any depth of the compared payloads).
- Everything else — parts, finish, usage, ids, extensions — is compared with
  `semantic_equal` exactly as specified above. In particular a
  `PART_STOP` chunk's final part MUST be semantically equal to the
  accumulation of its deltas, with `args_json` compared under §7.

## 9. Conformance

`spec/fixtures/` contains normative vectors for this document (key ordering
including astral-plane keys, number forms, NFC pairs, absent-vs-null, and
`*_json` parse-compare cases). Every language port MUST pass them. A port
MUST expose `canonical` and `semantic_equal` under those names so
conformance harnesses are portable.
