"""[PROVISIONAL] The canonical `Document` type and the `Embeddable` alias.

A `Document` is the richer embedding input — an optional id, its content
(inline text or a `Source` reference), and free-form metadata. `Embeddable`
is the union of every input sugar the request constructor accepts: a bare
string or `Document`, or a list of either.

Provisional per architecture §9: this shape freezes only after it carries
`CallResult` in real use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import ClassVar
from typing import Self

from ocai.core.ir import IRObject
from ocai.core.ir import is_json_object
from ocai.core.sources import Source
from ocai.core.sources import cast_source


@dataclass
class Document(IRObject):
    """A canonical embedding input with optional id, content, and metadata.

    Wrapping content (rather than passing bare strings everywhere) lets a
    single input carry an identifier and metadata through the embedding
    flow — and back out, since `Embedding.index` aligns results to inputs.
    Content may be inline text or a `Source` reference (including a
    provider-hosted `SourceRef`).

    Attributes:
        id: The document identifier, if any.
        content: The document body — inline text, a `Source` reference, or
            None.
        metadata: Free-form metadata attached to the document, if any.
    """

    object: ClassVar[str] = "document"

    id: str | None = None
    content: str | Source | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `Document` from a serialized dict, totally.

        A string `content` is kept as-is; a mapping `content` is decoded
        through `cast_source` (unknown source tags fall back to
        `SourceUnknown`).

        Args:
            data: A mapping with the optional `id`/`content`/`metadata`
                plus the common IR envelope keys.

        Returns:
            The decoded `Document`.
        """
        raw_content = data.get("content")
        content: str | Source | None = None
        if isinstance(raw_content, str):
            content = raw_content
        elif is_json_object(raw_content):
            content = cast_source(raw_content)
        return cls(
            id=data.get("id"),
            content=content,
            metadata=data.get("metadata"),
            **cls._from_dict_common(data),
        )


type Embeddable = str | list[str] | Document | list[Document]
