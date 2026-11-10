"""[PROVISIONAL] The canonical embedding response.

The named result the `EmbeddingModel` port returns inside `CallResult` —
the structural fix for the old port, which returned a bare
`list[Embedding]` and therefore had no channel for usage.

Provisional per architecture §9: freezes only after it carries `CallResult`
in real use.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import ClassVar
from typing import Self

from ocai.core.ir import IRObject
from ocai.core.ir import is_json_object
from ocai.core.usage import Usage
from ocai.embedding.types.embedding import Embedding


@dataclass
class EmbeddingResponse(IRObject):
    """A provider-neutral embedding result — a pure graph payload.

    Delivered inside `CallResult.value`; the route, report, and raw body
    ride the `CallResult` envelope, exactly as on the chat port.

    Attributes:
        embeddings: One `Embedding` per request input; each carries its
            `index` because providers may reorder.
        usage: What the call consumed, when reported — the core-owned
            dimensional `Usage` model.
        model: The provider's echo of the model that served the call.
    """

    object: ClassVar[str] = "embedding.response"

    embeddings: list[Embedding] = field(default_factory=list[Embedding])
    usage: Usage | None = None
    model: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build an `EmbeddingResponse` from a serialized dict, totally.

        Args:
            data: A mapping with `embeddings`, the optional
                `usage`/`model`, and the common IR envelope keys.

        Returns:
            The decoded `EmbeddingResponse`.
        """
        embeddings: list[Any] = data.get("embeddings") or []
        usage = data.get("usage")
        return cls(
            embeddings=[Embedding.from_dict(item) for item in embeddings if is_json_object(item)],
            usage=Usage.from_dict(usage) if is_json_object(usage) else None,
            model=data.get("model"),
            **cls._from_dict_common(data),
        )
