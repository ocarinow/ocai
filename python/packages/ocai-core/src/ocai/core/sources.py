"""Canonical IR media sources.

This module models the ways binary or remote media (images, audio, video,
documents) are referenced in the IR: inline base64 payloads (`SourceBase64`),
remote URLs (`SourceUrl`), and — new in this revision — provider-hosted file
handles (`SourceRef`, wrapping a `ProviderRef`, e.g. an OpenAI file id or a
Gemini Files API name). Media parts in every capability carry one member of
the `Source` union.

Decoding is total per architecture §2.6: `SOURCE_REGISTRY` is an open
`TagRegistry` whose Unknown fallback (`SourceUnknown`) preserves unrecognized
source payloads verbatim instead of raising, so a newer peer's source kinds
survive a round trip through an older ocai.

Because `SourceRef` names provider-side state, it inherits `ProviderRef`'s
scoped honesty rule (see `ocai.core.refs`): an interface-scoped ref is
`UNSUPPORTED` crossing any other `(provider, interface)`; a provider-scoped
ref (the natural scope for file handles — an OpenAI file id is valid across
`chat_completions`/`responses`/`batch`) survives same-provider
sibling-interface crossings unreported and is `UNSUPPORTED` across
providers; a model-scoped ref is additionally breakage when the bound
resource changes. Crossing beyond the ref's validity scope is always
reported, never silently dropped.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import ClassVar
from typing import Literal
from typing import Self

from ocai.core.ir import IRObject
from ocai.core.ir import TagRegistry
from ocai.core.refs import ProviderRef


class SourceType(str, Enum):
    """Canonical discriminator tags for the core `Source` variants.

    Constants for the tags core ships — the union itself stays open through
    `SOURCE_REGISTRY` (unknown tags decode to `SourceUnknown`, and plugins
    may register namespaced tags).

    Attributes:
        UNDEFINED: No source kind set (the unknown/placeholder tag).
        BASE64: An inline base64-encoded payload (`SourceBase64`).
        URL: A remote URL reference (`SourceUrl`).
        REF: A provider-hosted file handle (`SourceRef`).
    """

    UNDEFINED = "undefined"
    BASE64 = "base64"
    URL = "url"
    REF = "ref"


# TODO(wbenbihi): Make robust
type MimeType = str


@dataclass
class SourceBase64(IRObject):
    """A media source carrying an inline base64-encoded payload.

    Attributes:
        data: The base64-encoded media payload.
        mime_type: The media MIME type, or None if unknown.
        type: The source discriminator, fixed to `SourceType.BASE64`.
    """

    object: ClassVar[str] = "source"

    data: str
    mime_type: str | MimeType | None = field(default=None)
    type: Literal[SourceType.BASE64] = field(default=SourceType.BASE64)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `SourceBase64` from a serialized dict.

        Args:
            data: A mapping with the base64 `data`, an optional `mime_type`,
                and the common IR envelope fields.

        Returns:
            A new `SourceBase64` instance.
        """
        return cls(
            data=data.get("data", ""),
            mime_type=data.get("mime_type", None),
            **cls._from_dict_common(data),
        )


@dataclass
class SourceUrl(IRObject):
    """A media source referencing remote content by URL.

    Attributes:
        url: The URL of the remote media.
        mime_type: The media MIME type, or None if unknown.
        type: The source discriminator, fixed to `SourceType.URL`.
    """

    object: ClassVar[str] = "source"

    url: str
    mime_type: str | MimeType | None = field(default=None)
    type: Literal[SourceType.URL] = field(default=SourceType.URL)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `SourceUrl` from a serialized dict.

        Args:
            data: A mapping with the `url`, an optional `mime_type`, and the
                common IR envelope fields.

        Returns:
            A new `SourceUrl` instance.
        """
        return cls(
            url=data.get("url", ""),
            mime_type=data.get("mime_type", None),
            **cls._from_dict_common(data),
        )


@dataclass
class SourceRef(IRObject):
    """A media source held on a provider's side, named by a `ProviderRef`.

    Used for uploaded-file handles (OpenAI `file_id`, Gemini Files API
    names, Anthropic Files). The `ref`'s `scope` bounds where the handle is
    valid — converting a request carrying one beyond that scope reports
    `UNSUPPORTED` (the scoped honesty rule in `ocai.core.refs`).

    Attributes:
        ref: The provider-side handle.
        mime_type: The media MIME type, or None if unknown.
        type: The source discriminator, fixed to `SourceType.REF`.
    """

    object: ClassVar[str] = "source"

    ref: ProviderRef
    mime_type: str | MimeType | None = field(default=None)
    type: Literal[SourceType.REF] = field(default=SourceType.REF)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `SourceRef` from a serialized dict.

        Tolerates the pre-freeze `media_type` key (the field's name before
        the rename that aligned it with its `SourceBase64`/`SourceUrl`
        siblings): the value is accepted into `mime_type` and kept out of
        the `extensions` sweep, so old payloads decode losslessly while new
        payloads encode only `mime_type`.

        Args:
            data: A mapping with the nested `ref`, an optional `mime_type`
                (or legacy `media_type`), and the common IR envelope fields.

        Returns:
            A new `SourceRef` instance.
        """
        if "media_type" in data:
            data = dict(data)
            data.setdefault("mime_type", data["media_type"])
            del data["media_type"]
        return cls(
            ref=ProviderRef.from_dict(data.get("ref") or {}),
            mime_type=data.get("mime_type", None),
            **cls._from_dict_common(data),
        )


@dataclass
class SourceUnknown(IRObject):
    """Decoder fallback for a source tag this revision does not know.

    Preserves the payload verbatim (byte-faithful through `to_dict`) so an
    unknown source survives decode/encode untouched and can be upgraded
    later via IR self-migration edges. Strictly a *future-canonical-tag*
    fallback — total decode's safety net, never constructed deliberately.

    Attributes:
        data: The verbatim serialized payload, including its original tag.
        type: The unrecognized discriminator value, preserved verbatim.
    """

    object: ClassVar[str] = "source"

    data: dict[str, Any] = field(default_factory=dict)
    type: str = SourceType.UNDEFINED.value

    def to_dict(self) -> dict[str, Any]:
        """Serialize back to the verbatim payload this instance preserved.

        Returns:
            A copy of the original serialized mapping, untouched.
        """
        return dict(self.data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Preserve an unrecognized source payload verbatim.

        Args:
            data: The serialized mapping whose tag no registered source
                matched.

        Returns:
            A new `SourceUnknown` carrying the payload untouched.
        """
        tag = data.get("type")
        return cls(
            data=dict(data),
            type=tag if isinstance(tag, str) else SourceType.UNDEFINED.value,
        )


type Source = SourceBase64 | SourceUrl | SourceRef | SourceUnknown

# The open registry for the Source union. Core registers its bare tags here;
# plugins register namespaced tags. Unknown tags fall back to SourceUnknown.
SOURCE_REGISTRY: TagRegistry[Any] = TagRegistry(unknown=SourceUnknown)
SOURCE_REGISTRY.register(SourceType.BASE64.value, SourceBase64)
SOURCE_REGISTRY.register(SourceType.URL.value, SourceUrl)
SOURCE_REGISTRY.register(SourceType.REF.value, SourceRef)


def cast_source(data: dict[str, Any]) -> Source:
    """Decode a serialized source into its concrete `Source` variant.

    Dispatches on the `type` tag via `SOURCE_REGISTRY`; unknown tags decode
    to `SourceUnknown` — this function never raises on unknown input.

    Args:
        data: The serialized source mapping, including its `type`
            discriminator.

    Returns:
        The decoded `Source` variant.
    """
    decoded: Source = SOURCE_REGISTRY.decode(data)
    return decoded
