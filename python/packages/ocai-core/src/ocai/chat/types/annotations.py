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

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import Any
from typing import Self

from ocai.core.ir import IRObject
from ocai.core.ir import is_json_array
from ocai.core.ir import is_json_object
from ocai.core.refs import ProviderRef


@dataclass(frozen=True, slots=True)
class Span:
    """A half-open character range `[start, end)` into decoded text.

    Offsets are counted in Unicode code points of the *decoded* `PartText`
    text before any normalization. NFC, byte or UTF-16 offset conversions need
    their own validated mapping; this value never guesses or rescales offsets.

    Attributes:
        start: The inclusive start offset.
        end: The exclusive end offset; `end >= start`.
    """

    start: int
    end: int
    extensions: dict[str, Any] = field(default_factory=dict[str, Any], kw_only=True)

    def valid_for(self, text: str, *, attributed_text: str | None = None) -> bool:
        """Check code-point bounds and an optional exact attributed output slice.

        Args:
            text: The exact decoded text, without normalization.
            attributed_text: Expected output slice, when the codec supplies one;
                not the source quotation in Annotation.cited_text.

        Returns:
            Whether the span can safely attribute this text.
        """
        return (
            "ocai.invalid_span" not in self.extensions
            and type(self.start) is int
            and type(self.end) is int
            and 0 <= self.start <= self.end <= len(text)
            and (attributed_text is None or text[self.start : self.end] == attributed_text)
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the span to a plain JSON-compatible dict.

        Returns:
            A dict with `start` and `end`.
        """
        result: dict[str, Any] = {"start": self.start, "end": self.end}
        if self.extensions:
            result["extensions"] = deepcopy(self.extensions)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `Span` from a serialized dict, totally.

        Args:
            data: A mapping with `start` and `end`. Malformed offsets are
                retained under `ocai.invalid_span`, never coerced to integers.
                Unknown span keys follow the ordinary extensions sweep.

        Returns:
            The decoded `Span`.
        """
        raw_extensions = data.get("extensions")
        extensions: dict[str, Any] = (
            deepcopy(raw_extensions) if is_json_object(raw_extensions) else {}
        )
        extensions.update(
            {
                key: deepcopy(value)
                for key, value in data.items()
                if key not in {"start", "end", "extensions"}
            }
        )
        start, end = data.get("start"), data.get("end")
        if type(start) is not int or type(end) is not int:
            extensions["ocai.invalid_span"] = deepcopy(data)
            return cls(0, 0, extensions=extensions)
        return cls(start=start, end=end, extensions=extensions)


@dataclass
class SourceResultRef(IRObject):
    """A local citation reference into a sibling server-tool result.

    Attributes:
        call_id: Identity of the corresponding server-tool call/result.
        pointer: JSON Pointer within that result payload; empty names its root.
            This is data, never fetched or resolved implicitly.
    """

    call_id: str = ""
    pointer: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Decode a local reference while preserving unknown envelope fields."""
        return cls(
            call_id=data.get("call_id", ""),
            pointer=data.get("pointer", ""),
            **cls._from_dict_common(data),
        )


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
        kind: Open citation kind, including `url_citation`; unknown kinds survive.
        source_result: Local server-tool result reference, without provider replay authority.
    """

    span: Span | None = None
    url: str | None = None
    document_index: int | None = None
    file: ProviderRef | None = None
    title: str | None = None
    cited_text: str | None = None
    opaque: ProviderRef | None = None
    kind: str | None = None
    source_result: SourceResultRef | None = None

    def _unpositioned(self, raw_span: Any, reason: str) -> Self:
        """Retain invalid position evidence without asserting a text attribution."""
        extensions = deepcopy(self.extensions)
        previous = extensions.get("ocai.annotation_invalid_span")
        records = deepcopy(previous) if is_json_array(previous) else []
        if previous is not None and not is_json_array(previous):
            records.append({"span": previous, "reason": "prior evidence"})
        records.append({"span": deepcopy(raw_span), "reason": reason})
        extensions["ocai.annotation_invalid_span"] = records
        return replace(self, span=None, extensions=extensions)

    def validated(self, text: str, *, attributed_text: str | None = None) -> Self:
        """Return detached citation data validated against final decoded text.

        Invalid spans become unpositioned citations with original evidence in a
        registered extension. Source quotations need not equal output wording.
        Call only when text is final; streaming annotations can arrive earlier.

        Args:
            text: Exact final part text, counted in Unicode code points.
            attributed_text: Optional expected output slice for offset validation.

        Returns:
            A detached annotation; unknown kinds and source metadata are retained.
        """
        if self.span is not None and not self.span.valid_for(text, attributed_text=attributed_text):
            return self._unpositioned(self.span.to_dict(), "invalid position for decoded text")
        return deepcopy(self)

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
        source_result = data.get("source_result")
        result = cls(
            span=Span.from_dict(span) if is_json_object(span) else None,
            url=data.get("url"),
            document_index=data.get("document_index"),
            file=ProviderRef.from_dict(file) if is_json_object(file) else None,
            title=data.get("title"),
            cited_text=data.get("cited_text"),
            opaque=ProviderRef.from_dict(opaque) if is_json_object(opaque) else None,
            kind=data.get("kind"),
            source_result=SourceResultRef.from_dict(source_result)
            if is_json_object(source_result)
            else None,
            **cls._from_dict_common(data),
        )
        if source_result is not None and not is_json_object(source_result):
            result.extensions["ocai.annotation_unparsed_source"] = deepcopy(source_result)
        if span is not None and (
            not is_json_object(span)
            or result.span is None
            or "ocai.invalid_span" in result.span.extensions
        ):
            return result._unpositioned(span, "malformed span")
        return result
