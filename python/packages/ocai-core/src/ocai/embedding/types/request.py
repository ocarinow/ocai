"""[PROVISIONAL] The canonical embedding request.

The named input the `EmbeddingModel` port takes — the structural fix for
the old port, which accepted a loose `Embeddable` union and therefore had
no home for per-request options.

There is deliberately **no `model` field** (mirroring chat's WU-05a
course-correction): the model name is provider-specific routing data, bound
to the model object at the front door and injected into the wire payload by
the codec from `EndpointSpec.resource` — a request is a pure, portable
graph payload.

Provisional per architecture §9: freezes only after it carries `CallResult`
in real use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar
from typing import Self
from typing import overload

from ocai.core.ir import IRObject
from ocai.core.ir import is_json_object
from ocai.embedding.types.document import Document


@dataclass
class EmbeddingRequest(IRObject):
    """A provider-neutral embedding request — a pure graph payload.

    The constructor accepts the same sugar the old port did — a bare string
    or `Document`, or a list of either — normalized to `list[Document]` in
    `__post_init__`, so codecs and edges only ever see one shape (the same
    boundary-sugar pattern as chat's `Message`). And no `model`: the model
    name is routing data bound to the model object at the front door,
    injected on the wire by the codec from the bound resource — the same
    request replays against any bound model with zero edits.

    Attributes:
        inputs: The documents to embed, in order; `Embedding.index` in the
            response aligns to this list.
        dimensions: The requested output dimensionality, where the provider
            supports truncation/selection; None for the model default.
    """

    object: ClassVar[str] = "embedding.request"

    inputs: list[Document]
    dimensions: int | None = None

    if TYPE_CHECKING:
        # The constructor's typed face (same pattern as chat's `Message`):
        # the dataclass-generated `__init__` is untouched at runtime; these
        # declarations only admit the documented sugar `__post_init__`
        # normalizes, so the stored field stays `list[Document]`.
        @overload
        def __init__[T: Document | str](
            self,
            inputs: list[T],
            dimensions: int | None = None,
            *,
            version: str = ...,
            provider_options: dict[str, Any] = ...,
            extensions: dict[str, Any] = ...,
        ) -> None: ...

        @overload
        def __init__(
            self,
            inputs: str | Document | list[Document | str],
            dimensions: int | None = None,
            *,
            version: str = ...,
            provider_options: dict[str, Any] = ...,
            extensions: dict[str, Any] = ...,
        ) -> None: ...

        def __init__(
            self,
            inputs: Any,
            dimensions: int | None = None,
            *,
            version: str = ...,
            provider_options: dict[str, Any] = ...,
            extensions: dict[str, Any] = ...,
        ) -> None: ...

    def __post_init__(self) -> None:
        """Normalize constructor sugar into the documents-only shape.

        A bare string becomes one `Document`; a single `Document` is
        wrapped in a list; string items inside a list each become a
        `Document`.
        """
        raw = self.inputs
        if isinstance(raw, str):
            self.inputs = [Document(content=raw)]
            return
        if not isinstance(raw, list):  # pyright: ignore[reportUnnecessaryIsInstance] -- constructor sugar: a single `Document` reaches here untyped
            self.inputs = [raw]
            return
        self.inputs = [
            Document(content=item) if isinstance(item, str) else item for item in raw
        ]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build an `EmbeddingRequest` from a serialized dict, totally.

        Args:
            data: A mapping with `inputs`, the optional `dimensions`, and
                the common IR envelope keys.

        Returns:
            The decoded `EmbeddingRequest`.
        """
        inputs: list[Any] = data.get("inputs") or []
        return cls(
            inputs=[Document.from_dict(item) for item in inputs if is_json_object(item)],
            dimensions=data.get("dimensions"),
            **cls._from_dict_common(data),
        )
