"""[PROVISIONAL] The named vector store payloads: `Record` and `QueryResult`.

`Record` is the unit of storage the port reads and writes; `QueryResult`
pairs a matched record with its similarity score. Both are the "named
result objects, never bare tuples" fix (rule 4) for the old port, whose
methods returned nothing at all.

`Vector` is aliased locally (capabilities depend on `ocai.core` only, so
this package does not import `ocai.embedding` for a `list[float]`).

Provisional per architecture §9: these freeze only after they carry
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
class Record(IRObject):
    """One stored entry: id, vector, and what the vector stands for.

    The shape `create`/`update` write and `get`/`query` read — one type on
    both sides of the port, so round-tripping a record through a store is
    the identity.

    Attributes:
        id: The record's identifier within its store.
        vector: The stored vector; None when the store elides vectors on
            read (many do unless asked).
        metadata: Free-form metadata attached to the record, used by
            `filters`.
        content: The source text the vector encodes, when the store keeps
            it alongside.
    """

    object: ClassVar[str] = "record"

    id: str
    vector: Vector | None = None
    metadata: dict[str, Any] | None = None
    content: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `Record` from a serialized dict, totally.

        Args:
            data: A mapping with `id` and the optional
                `vector`/`metadata`/`content`, plus the common IR envelope
                keys.

        Returns:
            The decoded `Record`.
        """
        return cls(
            id=data.get("id", ""),
            vector=data.get("vector"),
            metadata=data.get("metadata"),
            content=data.get("content"),
            **cls._from_dict_common(data),
        )


@dataclass
class QueryResult(IRObject):
    """One similarity match: the record found and how similar it was.

    `query` returns a `CallResult[list[QueryResult]]`, best match first.

    Attributes:
        record: The matched record.
        score: The store's similarity score, higher-is-closer, when the
            store reports one. Metric semantics (cosine, dot, L2) are
            store-specific and surfaced via `VectorStore.details`.
    """

    object: ClassVar[str] = "query.result"

    record: Record
    score: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `QueryResult` from a serialized dict, totally.

        Args:
            data: A mapping with the nested `record`, the optional `score`,
                and the common IR envelope keys.

        Returns:
            The decoded `QueryResult`.
        """
        return cls(
            record=Record.from_dict(data.get("record") or {}),
            score=data.get("score"),
            **cls._from_dict_common(data),
        )
