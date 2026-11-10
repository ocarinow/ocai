"""Standalone dataclasses for the JSON Schema standard (Draft 2020-12).

This module is intentionally self-contained: it imports nothing from `ocai` and
models the JSON Schema specification exactly as published at
https://json-schema.org/ (the 2020-12 dialect). It can be lifted out and used on
its own.

Design notes:
* **A schema is `object | bool`.** In 2020-12 a (sub)schema may be a boolean:
  `true` (allow anything) / `false` (allow nothing). The object form is
  modelled by `JsonSchema`; the boolean form is carried as a plain
  `bool`. The recursive type `Schema` is therefore `JsonSchema | bool`,
  and `decode_schema` / `encode_schema` move between the wire form
  and this type.
* **Every keyword lives on one flat class.** JSON Schema keywords are independent
  and freely combinable on a single schema object, so `JsonSchema` exposes
  *all* keywords as optional fields rather than splitting by `type`. Absent
  keywords are `None` (or `MISSING` for the value-bearing keywords whose
  legitimate value may itself be `null` -- `const` and `default`).
* **Lossless.** Unknown / custom keywords (other vocabularies, `x-` extensions,
  `$` anchors not in the core set) round-trip through `JsonSchema.extra`.
* **Field naming.** Python-legal field names map to the wire keys via
  `_PY_TO_JSON` (e.g. `ref` -> `$ref`, `all_of` -> `allOf`,
  `not_`/`if_`/`else_` for the reserved words).
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from ocai.core.ir import is_json_array
from ocai.core.ir import is_json_object

__all__ = [
    "MISSING",
    "JsonSchema",
    "Schema",
    "decode_schema",
    "encode_schema",
]


class _Missing:
    """Sentinel distinguishing "keyword absent" from "keyword present and null".

    Needed for `const` / `default`, whose valid value includes JSON `null`;
    `None` cannot double as "absent" there the way it can for every other field.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        """Return the constant representation `"MISSING"`."""
        return "MISSING"

    def __bool__(self) -> bool:
        """Return `False`, so the sentinel is always falsy."""
        return False


MISSING: Any = _Missing()


# Python field name -> JSON Schema wire key. Drives both (de)serialization and
# field ordering of ``to_dict``. Grouped by 2020-12 vocabulary.
_PY_TO_JSON: dict[str, str] = {
    # --- Core vocabulary -------------------------------------------------
    "schema": "$schema",
    "vocabulary": "$vocabulary",
    "id": "$id",
    "anchor": "$anchor",
    "dynamic_anchor": "$dynamicAnchor",
    "ref": "$ref",
    "dynamic_ref": "$dynamicRef",
    "defs": "$defs",
    "comment": "$comment",
    # --- Applicator vocabulary ------------------------------------------
    "all_of": "allOf",
    "any_of": "anyOf",
    "one_of": "oneOf",
    "not_": "not",
    "if_": "if",
    "then": "then",
    "else_": "else",
    "dependent_schemas": "dependentSchemas",
    "prefix_items": "prefixItems",
    "items": "items",
    "contains": "contains",
    "properties": "properties",
    "pattern_properties": "patternProperties",
    "additional_properties": "additionalProperties",
    "property_names": "propertyNames",
    # --- Unevaluated locations vocabulary -------------------------------
    "unevaluated_items": "unevaluatedItems",
    "unevaluated_properties": "unevaluatedProperties",
    # --- Validation vocabulary ------------------------------------------
    "type": "type",
    "enum": "enum",
    "const": "const",
    "multiple_of": "multipleOf",
    "maximum": "maximum",
    "exclusive_maximum": "exclusiveMaximum",
    "minimum": "minimum",
    "exclusive_minimum": "exclusiveMinimum",
    "max_length": "maxLength",
    "min_length": "minLength",
    "pattern": "pattern",
    "max_items": "maxItems",
    "min_items": "minItems",
    "unique_items": "uniqueItems",
    "max_contains": "maxContains",
    "min_contains": "minContains",
    "max_properties": "maxProperties",
    "min_properties": "minProperties",
    "required": "required",
    "dependent_required": "dependentRequired",
    # --- Meta-data vocabulary -------------------------------------------
    "title": "title",
    "description": "description",
    "default": "default",
    "deprecated": "deprecated",
    "read_only": "readOnly",
    "write_only": "writeOnly",
    "examples": "examples",
    # --- Format vocabulary ----------------------------------------------
    "format": "format",
    # --- Content vocabulary ---------------------------------------------
    "content_encoding": "contentEncoding",
    "content_media_type": "contentMediaType",
    "content_schema": "contentSchema",
}

_JSON_TO_PY: dict[str, str] = {wire: py for py, wire in _PY_TO_JSON.items()}

# Keywords whose value is itself a (sub)schema, i.e. ``Schema`` (object | bool).
# Used by ``from_dict`` to know where to recurse. Keyed by wire name.
_SCHEMA_FIELDS: frozenset[str] = frozenset(
    {
        "not",
        "if",
        "then",
        "else",
        "items",
        "contains",
        "additionalProperties",
        "propertyNames",
        "unevaluatedItems",
        "unevaluatedProperties",
        "contentSchema",
    }
)
# Keywords whose value is a list of schemas.
_SCHEMA_LIST_FIELDS: frozenset[str] = frozenset({"allOf", "anyOf", "oneOf", "prefixItems"})
# Keywords whose value is a string-keyed map of schemas.
_SCHEMA_MAP_FIELDS: frozenset[str] = frozenset(
    {"$defs", "properties", "patternProperties", "dependentSchemas"}
)

# Python fields whose legitimate value may be ``null``; ``None`` there means
# "present and null", not "absent" (absent is ``MISSING``).
_NULLABLE_VALUE_FIELDS: frozenset[str] = frozenset({"const", "default"})


def encode_schema(value: Any) -> Any:
    """Recursively encode a value to its plain JSON form.

    `JsonSchema` instances become dicts; lists and dicts recurse; everything
    else passes through unchanged (raw JSON in `enum` / `const` / `default` /
    `examples` is copied structurally, never reinterpreted).
    """
    if isinstance(value, JsonSchema):
        return value.to_dict()
    if is_json_array(value):
        return [encode_schema(v) for v in value]
    if is_json_object(value):
        return {k: encode_schema(v) for k, v in value.items()}
    return value


def decode_schema(value: Any) -> Schema:
    """Decode a wire (sub)schema into `Schema` (`JsonSchema | bool`).

    Tolerant: a boolean stays a boolean, a mapping becomes a `JsonSchema`,
    and anything else is returned unchanged rather than raising.
    """
    if isinstance(value, bool):
        return value
    if is_json_object(value):
        return JsonSchema.from_dict(value)
    # Tolerant passthrough (rule 6): a non-schema value is preserved verbatim,
    # so this branch is typed `Schema` by declaration only.
    return value  # type: ignore[no-any-return]


@dataclass(kw_only=True)
class JsonSchema:
    """An object-form JSON Schema (Draft 2020-12).

    All keywords are optional. `None` marks an absent keyword for every field
    except `const` / `default`, which use `MISSING` so that an explicit
    JSON `null` is representable. Unknown keywords survive in `extra`.
    """

    # --- Core vocabulary ($schema, identifiers, references, defs) --------
    schema: str | None = None
    vocabulary: dict[str, bool] | None = None
    id: str | None = None
    anchor: str | None = None
    dynamic_anchor: str | None = None
    ref: str | None = None
    dynamic_ref: str | None = None
    defs: dict[str, Schema] | None = None
    comment: str | None = None

    # --- Applicator vocabulary ------------------------------------------
    all_of: list[Schema] | None = None
    any_of: list[Schema] | None = None
    one_of: list[Schema] | None = None
    not_: Schema | None = None
    if_: Schema | None = None
    then: Schema | None = None
    else_: Schema | None = None
    dependent_schemas: dict[str, Schema] | None = None
    prefix_items: list[Schema] | None = None
    items: Schema | None = None
    contains: Schema | None = None
    properties: dict[str, Schema] | None = None
    pattern_properties: dict[str, Schema] | None = None
    additional_properties: Schema | None = None
    property_names: Schema | None = None

    # --- Unevaluated locations vocabulary -------------------------------
    unevaluated_items: Schema | None = None
    unevaluated_properties: Schema | None = None

    # --- Validation vocabulary ------------------------------------------
    type: str | list[str] | None = None
    enum: list[Any] | None = None
    const: Any = MISSING
    multiple_of: float | int | None = None
    maximum: float | int | None = None
    exclusive_maximum: float | int | None = None
    minimum: float | int | None = None
    exclusive_minimum: float | int | None = None
    max_length: int | None = None
    min_length: int | None = None
    pattern: str | None = None
    max_items: int | None = None
    min_items: int | None = None
    unique_items: bool | None = None
    max_contains: int | None = None
    min_contains: int | None = None
    max_properties: int | None = None
    min_properties: int | None = None
    required: list[str] | None = None
    dependent_required: dict[str, list[str]] | None = None

    # --- Meta-data vocabulary -------------------------------------------
    title: str | None = None
    description: str | None = None
    default: Any = MISSING
    deprecated: bool | None = None
    read_only: bool | None = None
    write_only: bool | None = None
    examples: list[Any] | None = None

    # --- Format vocabulary ----------------------------------------------
    format: str | None = None

    # --- Content vocabulary ---------------------------------------------
    content_encoding: str | None = None
    content_media_type: str | None = None
    content_schema: Schema | None = None

    # --- Lossless escape hatch for unknown / custom keywords ------------
    extra: dict[str, Any] = field(default_factory=dict[str, Any])

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain JSON Schema dict, omitting absent keywords."""
        out: dict[str, Any] = {}
        for py_name, wire_key in _PY_TO_JSON.items():
            value = getattr(self, py_name)
            if value is MISSING:
                continue
            if value is None and py_name not in _NULLABLE_VALUE_FIELDS:
                continue
            out[wire_key] = encode_schema(value)
        for key, value in self.extra.items():
            out[key] = encode_schema(value)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JsonSchema:
        """Build from a plain JSON Schema dict; unknown keys land in `extra`."""
        kwargs: dict[str, Any] = {}
        extra: dict[str, Any] = {}
        for wire_key, value in data.items():
            py_name = _JSON_TO_PY.get(wire_key)
            if py_name is None:
                extra[wire_key] = value
            elif wire_key in _SCHEMA_FIELDS:
                kwargs[py_name] = decode_schema(value)
            elif wire_key in _SCHEMA_LIST_FIELDS:
                kwargs[py_name] = [decode_schema(v) for v in value]
            elif wire_key in _SCHEMA_MAP_FIELDS:
                kwargs[py_name] = {k: decode_schema(v) for k, v in value.items()}
            else:
                kwargs[py_name] = value
        return cls(extra=extra, **kwargs)


# A (sub)schema is the object form or a boolean (2020-12). Declared after the
# class; PEP 695 type aliases are lazily evaluated, and the forward references in
# ``JsonSchema``'s annotations are strings thanks to ``from __future__``.
type Schema = JsonSchema | bool
type DataSchema = Schema