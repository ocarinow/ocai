"""The IR envelope and total decode (architecture §2.6).

Two objects make the canonical IR *additive* and *crash-proof*:

- `IRObject` — the base every IR dataclass extends. Its `to_dict` is
  **omit-absent** (absent/None and empty-by-default fields are not emitted),
  which is what makes "additive" real: adding an optional field never
  invalidates a fixture. Its `_from_dict_common` is **tolerant**: unknown
  envelope keys sweep into `extensions`, never raise.
- `TagRegistry` — open registration for tagged unions (parts, deltas,
  details, sources). Decoding an unknown tag returns the registered
  *Unknown* fallback; **no decode path in the IR may ever raise on unknown
  input.**

Precedence rule (normative): unknown *envelope keys* sweep to `extensions`;
unknown *content tags* fall back to the Unknown type; a decoder never applies
both to the same bytes — a payload is either a field of a known object (swept
if unknown) or a tagged member of a union (fallback-typed if unknown).

Plugin tags must be namespaced (`"anthropic.mid_conv_system"`); bare tags are
reserved for core.
"""

from __future__ import annotations

from dataclasses import MISSING
from dataclasses import Field
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from datetime import date
from enum import Enum
from typing import Any
from typing import Protocol
from typing import Self
from typing import runtime_checkable

from ocai.core.identity import CANONICAL_REVISION


@runtime_checkable
class DataClassProto(Protocol):
    """The structural serialization contract every IR dataclass satisfies.

    `TagRegistry` and the encoder dispatch on this shape rather than on a
    base class, so plugin-defined IR types (and core types that do not extend
    `IRObject`, like `ProviderRef`) participate equally.
    """

    def to_dict(self) -> dict[str, Any]:
        """Serialize the object to a plain JSON-compatible dict.

        Returns:
            The serialized mapping, omit-absent.
        """
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build an instance from a serialized dict, totally (never raises on unknown input).

        Args:
            data: The serialized mapping to decode.

        Returns:
            The decoded instance.
        """
        ...


def _encode(value: Any) -> Any:
    """Recursively encode `value` into plain JSON-compatible data.

    Enums become their `value`; dates/datetimes become ISO-8601 strings;
    objects exposing `to_dict` are expanded; lists/tuples and dicts recurse;
    everything else passes through unchanged.
    """
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):  # covers datetime (subclass)
        return value.isoformat()
    if hasattr(value, "to_dict") and not isinstance(value, type):
        return value.to_dict()
    if isinstance(value, (list, tuple)):
        return [_encode(item) for item in value]
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items()}
    return value


def _is_empty_container(value: Any) -> bool:
    """Return whether `value` is an empty dict/list/tuple/set/frozenset."""
    return isinstance(value, (dict, list, tuple, set, frozenset)) and len(value) == 0


def _absent(f: Field[Any], value: Any) -> bool:
    """Return whether field `f` holding `value` counts as *absent*.

    Absent means: the value is None, or the value is an empty container and
    the field's declared default is also empty/None — i.e. nothing meaningful
    was ever set. A *required* container field explicitly holding an empty
    value is NOT absent (an empty `parts` list is data) and is emitted.
    """
    if value is None:
        return True
    if _is_empty_container(value):
        if f.default_factory is not MISSING:
            return _is_empty_container(f.default_factory())
        if f.default is not MISSING:
            return f.default is None or _is_empty_container(f.default)
    return False


@dataclass
class IRObject:
    """Common base for canonical IR dataclasses — the envelope.

    Carries the three cross-cutting fields every IR object shares, all
    keyword-only, and implements the two normative (de)serialization halves:
    omit-absent `to_dict` and the tolerant `_from_dict_common` sweep that
    subclasses' `from_dict` build on.

    Attributes:
        version: The canonical IR revision this object conforms to; defaults
            to `CANONICAL_REVISION`. A dated tag on the `ocai` interface —
            never the library semver, never a provider tag.
        provider_options: Request passthrough, **namespaced by destination
            interface** (`{"openai.chat_completions": {...}}`). A codec
            expands only its own namespace; foreign namespaces are never
            forwarded.
        extensions: The namespaced bag for unmapped-but-preserved provider
            data (`extensions["openai.logit_bias"]`). Censused: every key's
            schema is registered in `spec/extensions/`.
    """

    version: str = field(default=CANONICAL_REVISION, kw_only=True)
    provider_options: dict[str, Any] = field(default_factory=dict, kw_only=True)
    extensions: dict[str, Any] = field(default_factory=dict, kw_only=True)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict, omitting absent fields.

        Omit-absent is the normative encoding rule: None-valued fields and
        empty containers whose declared default is also empty are not
        emitted. This is what keeps fixtures stable as optional fields are
        added, and it pairs with `canonjson`'s absent-vs-null distinction
        (an emitted `null` is meaningful; an omitted key is absent).

        Returns:
            A dict keyed by field name with recursively encoded values.
        """
        out: dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if _absent(f, value):
                continue
            out[f.name] = _encode(value)
        return out

    @classmethod
    def _from_dict_common(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Extract the envelope kwargs from `data`, sweeping unknown keys.

        The tolerant half of total decode: every key of `data` that is not a
        declared field of `cls` is swept into the returned `extensions`
        (merged over any explicit `extensions` payload), so a newer peer's
        additive fields survive a round trip through an older ocai instead
        of raising.

        Args:
            data: The full serialized mapping being decoded.

        Returns:
            Kwargs for `version`, `provider_options`, and `extensions`,
            ready to splat into the subclass constructor.
        """
        known = {f.name for f in fields(cls)}
        extensions: dict[str, Any] = dict(data.get("extensions") or {})
        extensions.update({key: value for key, value in data.items() if key not in known})
        return {
            "version": data.get("version", CANONICAL_REVISION),
            "provider_options": dict(data.get("provider_options") or {}),
            "extensions": extensions,
        }


class TagRegistry[T: DataClassProto]:
    """Open registration for one tagged union (parts, deltas, details, …).

    Each tagged union in the IR owns one registry instance. Core registers
    its bare tags at import of the type module; plugins register namespaced
    tags (`"anthropic.mid_conv_system"`) from their `CatalogFragment` —
    bare tags are reserved for core.

    Decoding is **total**: an unknown or missing tag falls back to the
    registered Unknown type (`PartUnknown`, `DeltaUnknown`, …), which
    preserves the payload verbatim for later upgrade via IR self-migration
    edges. A registry with no Unknown fallback is a configuration error, not
    a decode-time surprise.
    """

    __slots__ = ("_tag_key", "_by_tag", "_unknown")

    def __init__(self, *, tag_key: str = "type", unknown: type[T] | None = None) -> None:
        """Create a registry for one tagged union.

        Args:
            tag_key: The discriminator key read from payloads.
            unknown: The fallback type decoded when the tag is unknown; may
                also be supplied later via `register_unknown`.
        """
        self._tag_key = tag_key
        self._by_tag: dict[str, type[T]] = {}
        self._unknown: type[T] | None = unknown

    def register(self, tag: str, cls: type[T]) -> type[T]:
        """Register `cls` as the decoder for `tag`.

        Idempotent for the same class; re-registering a tag to a *different*
        class raises, because silently shadowing another distribution's tag
        is exactly the governance failure catalogs exist to prevent.

        Args:
            tag: The discriminator value (bare for core, namespaced for
                plugins).
            cls: The dataclass whose `from_dict` decodes payloads so tagged.

        Returns:
            `cls`, so the call can be used as a registration helper.

        Raises:
            ValueError: If `tag` is already registered to a different class.
        """
        existing = self._by_tag.get(tag)
        if existing is not None and existing is not cls:
            raise ValueError(
                f"tag {tag!r} is already registered to {existing.__qualname__}; "
                f"refusing to shadow it with {cls.__qualname__}"
            )
        self._by_tag[tag] = cls
        return cls

    def register_unknown(self, cls: type[T]) -> type[T]:
        """Register the Unknown fallback type decoded for unrecognized tags.

        Args:
            cls: The fallback dataclass; its `from_dict` must preserve the
                payload verbatim.

        Returns:
            `cls`, so the call can be used as a registration helper.
        """
        self._unknown = cls
        return cls

    def decode(self, data: dict[str, Any]) -> T:
        """Decode a tagged payload into its registered type — totally.

        Reads `data[tag_key]`, dispatches to the registered class, and falls
        back to the Unknown type for missing/unrecognized/non-string tags.
        This replaces the old `decode_tagged`, which raised `KeyError` on
        unknown tags.

        Args:
            data: The serialized mapping, including its discriminator.

        Returns:
            The decoded instance.

        Raises:
            LookupError: Only when the tag is unknown AND no Unknown
                fallback was registered — a registry configuration error;
                every core registry registers a fallback.
        """
        tag = data.get(self._tag_key)
        cls = self._by_tag.get(tag) if isinstance(tag, str) else None
        if cls is None:
            cls = self._unknown
        if cls is None:
            raise LookupError(
                f"no decoder registered for tag {tag!r} and no Unknown fallback "
                f"is registered; register one with register_unknown()"
            )
        return cls.from_dict(data)

    @property
    def tags(self) -> frozenset[str]:
        """Return the currently registered discriminator values."""
        return frozenset(self._by_tag)
