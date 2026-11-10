"""[PROVISIONAL] The canonical `Embedding` type and the `Vector` alias.

`Vector` is the plain `list[float]` shape a raw vector takes. `Embedding`
wraps a vector with per-result metadata — its batch position, numeric
encoding, and normalization state — so a response can describe each vector
without flattening to bare floats.

Provisional per architecture §9: this shape freezes only after it carries
`CallResult` in real use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import ClassVar
from typing import Self

from ocai.core.ir import IRObject

type Vector = list[float]


@dataclass
class Embedding(IRObject):
    """A single embedding vector, one per input in an `EmbeddingRequest`.

    Wrapping the raw vector (rather than returning a bare `list[float]`)
    lets a response carry per-vector metadata — its position in the batch,
    the numeric encoding, and whether it is already L2-normalized — without
    lying that every provider returns floats. `int8`/`binary` dtypes still
    serialize as ints.

    Attributes:
        index: Position of this vector in the request batch (providers may
            reorder).
        values: The vector itself. For non-float `dtype`s the entries are
            ints.
        dtype: The open numeric-encoding code:
            `float32 | int8 | uint8 | binary | ubinary`.
        normalized: Whether `values` is L2-normalized, if the provider says;
            None means unknown.
        metadata: Free-form metadata attached to this vector, if any.
    """

    object: ClassVar[str] = "embedding"

    index: int
    values: Vector
    dtype: str = "float32"
    normalized: bool | None = None
    metadata: dict[str, Any] | None = None

    @property
    def dimensions(self) -> int:
        """Return the vector length — derived, never stored, so it cannot drift from `values`."""
        return len(self.values)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build an `Embedding` from a serialized dict, totally.

        Args:
            data: A mapping with `index`, `values`, and the optional
                `dtype`/`normalized`/`metadata`, plus the common IR
                envelope keys.

        Returns:
            The decoded `Embedding`.
        """
        return cls(
            index=data.get("index", 0),
            values=data.get("values") or [],
            dtype=data.get("dtype", "float32"),
            normalized=data.get("normalized"),
            metadata=data.get("metadata"),
            **cls._from_dict_common(data),
        )
