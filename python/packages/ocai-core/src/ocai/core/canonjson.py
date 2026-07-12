"""The equality predicate: canonical JSON, defined once, normatively (§2.7).

Every conformance guarantee in this repo — golden fixtures, round-trips, fold
triples, the cross-language drift alarm — reduces to "semantic equality over
canonical JSON", so the rules live in exactly one place: here and in
`spec/canonical-json.md`. The TypeScript and Go ports implement the same
spec; no implementation may invent its own.

Normative rules:

1. **Key ordering** — object keys are sorted by Unicode code point after
   normalization. (TODO: RFC 8785/JCS sorts by UTF-16 code units, which
   differs above the BMP; pick one in `spec/canonical-json.md` and align.)
2. **Numbers** — booleans are booleans, never numbers. A float with an
   integral value is the same number as the integer (`1.0 == 1`); canonical
   form emits it as an integer. Non-integral floats use Python's shortest
   round-trip repr. `NaN`/`Infinity` are not JSON and are rejected.
3. **Unicode** — every string (keys and values) is NFC-normalized.
4. **Absent vs null** — an omitted key and a key present with `null` are
   **different documents**. `IRObject.to_dict` is omit-absent, so "absent"
   is expressible; an emitted `null` is deliberate and preserved.
5. **Embedded JSON strings** (`*_json` fields, e.g. `args_json`) —
   *preserve-verbatim / parse-compare*: `canonical` keeps the string byte
   -faithful (the wire truth is the string), while `semantic_equal` parses
   both sides and compares the parsed values, so two serializations of the
   same arguments are equal without ocai ever rewriting the wire bytes.

`canonical` accepts JSON-shaped data or any object exposing `to_dict`
(every IR dataclass), making `canonical(a) == canonical(b)` usable directly
in fixtures.
"""

from __future__ import annotations

import json
import unicodedata
from typing import Any

# Suffix marking a field whose string value is embedded JSON (wire truth).
_EMBEDDED_JSON_SUFFIX = "_json"


def _nfc(text: str) -> str:
    """Return `text` normalized to Unicode NFC."""
    return unicodedata.normalize("NFC", text)


def _normalize(value: Any, *, parse_embedded: bool, key: str | None = None) -> Any:
    """Recursively rewrite `value` into its canonical structural form.

    Applies the normative rules: `to_dict` expansion, NFC strings, integral
    floats to ints, list/dict recursion, and — when `parse_embedded` is true
    — the parse-compare rule for `*_json` string fields (`key` is the object
    key the value sits under, when any).

    Raises:
        TypeError: If `value` is not JSON-shaped (or a non-string dict key
            is encountered).
        ValueError: If a non-finite float (`NaN`/`Infinity`) is encountered.
    """
    if hasattr(value, "to_dict") and not isinstance(value, type):
        value = value.to_dict()
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("NaN and Infinity are not representable in canonical JSON")
        if value.is_integer():
            return int(value)
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = _nfc(value)
        if parse_embedded and key is not None and key.endswith(_EMBEDDED_JSON_SUFFIX):
            # Parse-compare rule: compare the parsed value, never the bytes.
            # TODO: an unparseable *_json string currently compares as its
            # verbatim text; decide whether that should be a hard error.
            try:
                parsed = json.loads(text)
            except ValueError:
                return text
            return _normalize(parsed, parse_embedded=True)
        return text
    if isinstance(value, (list, tuple)):
        return [_normalize(item, parse_embedded=parse_embedded) for item in value]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, item in value.items():
            if not isinstance(k, str):
                raise TypeError(
                    f"canonical JSON object keys must be strings, got {type(k).__name__}"
                )
            out[_nfc(k)] = _normalize(item, parse_embedded=parse_embedded, key=k)
        return out
    raise TypeError(f"value of type {type(value).__name__} is not JSON-shaped")


def canonical(obj: Any) -> str:
    """Serialize `obj` to its one canonical JSON string.

    The normative encoding fixtures are compared against: sorted keys,
    minimal separators, non-ASCII characters unescaped (NFC-normalized),
    integral floats as integers, embedded `*_json` strings preserved
    verbatim (rule 5's preserve half).

    Args:
        obj: JSON-shaped data, or any object exposing `to_dict`.

    Returns:
        The canonical JSON text.

    Raises:
        TypeError: If `obj` is not JSON-shaped.
        ValueError: If `obj` contains a non-finite float.
    """
    normalized = _normalize(obj, parse_embedded=False)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def semantic_equal(a: Any, b: Any) -> bool:
    """Return whether `a` and `b` are the same document, semantically.

    The single equality predicate conformance asserts with: both sides are
    normalized under the full rule set — including the parse-compare half of
    rule 5, so `{"args_json": "{\\"a\\": 1}"}` equals
    `{"args_json": "{\\"a\\":1}"}` — and compared structurally. Absent and
    null remain distinct (rule 4).

    Args:
        a: One side; JSON-shaped data or an object exposing `to_dict`.
        b: The other side, likewise.

    Returns:
        True when the two normalize to the same structure.
    """
    return _normalize(a, parse_embedded=True) == _normalize(b, parse_embedded=True)
