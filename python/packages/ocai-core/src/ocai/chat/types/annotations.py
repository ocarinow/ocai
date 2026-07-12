"""Span-anchored citations on text parts (architecture §3.1).

An `Annotation` attaches a citation to a character `Span` of a `PartText`'s
decoded text. Citations are anchored **on the text part itself** — never a
parallel side channel — so slicing, folding, and converting a message moves
the citations with the text they attribute.

The cited source can be named three ways, all optional and non-exclusive:
a web `url`, a `document_index` into the request's documents, or a provider
`file` handle (a `ProviderRef`, inheriting its cross-interface `UNSUPPORTED`
rule). Provider-opaque citation state (e.g. encrypted grounding payloads)
rides `opaque`.

Honesty rule (normative, from the blueprint): Gemini grounding metadata is
re-anchored into `Annotation`s **only** when its offsets validate against the
decoded text; otherwise it rides a censused extension. Never emit a
possibly-misattributed span.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Self

from ocai.core.ir import IRObject
from ocai.core.refs import ProviderRef


@dataclass(frozen=True, slots=True)
class Span:
    """A half-open character range `[start, end)` into decoded text.

    Offsets are counted in Unicode code points of the *decoded* `PartText`
    text — the same text `canonjson` normalizes — so a span means the same
    thing in every language port.

    Attributes:
        start: The inclusive start offset.
        end: The exclusive end offset; `end >= start`.
    """

    start: int
    end: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize the span to a plain JSON-compatible dict.

        Returns:
            A dict with `start` and `end`.
        """
        return {"start": self.start, "end": self.end}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `Span` from a serialized dict, totally.

        Args:
            data: A mapping with `start` and `end`; missing offsets default
                to 0 rather than raising.

        Returns:
            The decoded `Span`.
        """
        return cls(start=int(data.get("start", 0)), end=int(data.get("end", 0)))


@dataclass
class Annotation(IRObject):
    """One span-anchored citation carried by a `PartText`.

    Lives in `PartText.annotations`; each record attributes the `span` slice
    of the part's text to a source. During streaming, annotations arrive as
    `DeltaAnnotation` events and are appended by the `StreamAccumulator`.

    Attributes:
        span: The text range being attributed, or None when the provider
            cited the whole part.
        url: The cited web URL, when the source is a web page.
        document_index: The zero-based index of the cited request document,
            when the source is caller-supplied material.
        file: The provider-side file handle backing the citation, when the
            source is an uploaded file. Crossing another
            `(provider, interface)` is reported `UNSUPPORTED`.
        title: The human-readable title of the cited source.
        cited_text: The verbatim excerpt the provider quoted, when given.
        opaque: Provider-opaque citation state (e.g. an encrypted grounding
            token) that must ride along verbatim to keep the citation
            replayable.
    """

    span: Span | None = None
    url: str | None = None
    document_index: int | None = None
    file: ProviderRef | None = None
    title: str | None = None
    cited_text: str | None = None
    opaque: ProviderRef | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build an `Annotation` from a serialized dict, totally.

        Args:
            data: A mapping with any of the annotation fields plus the
                common IR envelope keys; unknown keys sweep to `extensions`.

        Returns:
            The decoded `Annotation`.
        """
        span = data.get("span")
        file = data.get("file")
        opaque = data.get("opaque")
        return cls(
            span=Span.from_dict(span) if isinstance(span, dict) else None,
            url=data.get("url"),
            document_index=data.get("document_index"),
            file=ProviderRef.from_dict(file) if isinstance(file, dict) else None,
            title=data.get("title"),
            cited_text=data.get("cited_text"),
            opaque=ProviderRef.from_dict(opaque) if isinstance(opaque, dict) else None,
            **cls._from_dict_common(data),
        )
