"""[PROVISIONAL] The `VectorStore` port.

The provider-neutral vector store contract, reshaped to the uniform port
grammar (architecture §2.3): every method returns a `CallResult`-wrapped
named result (`Record`/`QueryResult`), every mutating method is
keyword-only, filtering goes by the one name `filters` everywhere (the old
`where`-vs-`filters` split is dead), and the optional `CallContext` rides
each call — so governance and cost interceptors compose over FAISS exactly
as over a hosted store.

Provisional per architecture §9: this port freezes only after it carries
`CallResult` in real use.
"""

from __future__ import annotations

from typing import Any
from typing import Protocol
from typing import runtime_checkable

from ocai.core.result import CallContext
from ocai.core.result import CallResult
from ocai.vectorstore.types.filter import QueryFilter
from ocai.vectorstore.types.record import QueryResult
from ocai.vectorstore.types.record import Record
from ocai.vectorstore.types.record import Vector


@runtime_checkable
class VectorStore(Protocol):
    """A vector store port — structural, never subclassed.

    Reads (`get`/`query`) return records/matches; writes
    (`create`/`update`/`delete`) are keyword-only and return the envelope
    too, so a fidelity report or usage record from a hosted store has a
    home on every operation. Each method has its `a`-prefixed async twin
    (repo-wide convention: bare = sync, `a` = async).
    """

    def get(
        self,
        *,
        ids: list[str] | None = None,
        filters: QueryFilter | None = None,
        limit: int | None = None,
        offset: int | None = None,
        ctx: CallContext | None = None,
    ) -> CallResult[list[Record]]:
        """Fetch stored records by id and/or metadata filter.

        Args:
            ids: The ids to fetch; None fetches without an id constraint.
            filters: A metadata filter constraining the results; None for
                no filter.
            limit: Maximum number of records to return; None for no limit.
            offset: Number of records to skip; None for no offset.
            ctx: The per-request governance context.

        Returns:
            The uniform envelope carrying the matching records.
        """
        ...

    async def aget(
        self,
        *,
        ids: list[str] | None = None,
        filters: QueryFilter | None = None,
        limit: int | None = None,
        offset: int | None = None,
        ctx: CallContext | None = None,
    ) -> CallResult[list[Record]]:
        """Fetch stored records by id and/or metadata filter, asynchronously.

        Args:
            ids: The ids to fetch; None fetches without an id constraint.
            filters: A metadata filter constraining the results; None for
                no filter.
            limit: Maximum number of records to return; None for no limit.
            offset: Number of records to skip; None for no offset.
            ctx: The per-request governance context.

        Returns:
            The uniform envelope carrying the matching records.
        """
        ...

    def create(
        self,
        *,
        records: list[Record],
        ctx: CallContext | None = None,
    ) -> CallResult[list[str]]:
        """Insert records into the store.

        Args:
            records: The records to insert; a record without an `id` lets
                the store assign one.
            ctx: The per-request governance context.

        Returns:
            The uniform envelope carrying the ids of the inserted records,
            in input order.
        """
        ...

    async def acreate(
        self,
        *,
        records: list[Record],
        ctx: CallContext | None = None,
    ) -> CallResult[list[str]]:
        """Insert records into the store, asynchronously.

        Args:
            records: The records to insert; a record without an `id` lets
                the store assign one.
            ctx: The per-request governance context.

        Returns:
            The uniform envelope carrying the ids of the inserted records,
            in input order.
        """
        ...

    def update(
        self,
        *,
        records: list[Record],
        ctx: CallContext | None = None,
    ) -> CallResult[None]:
        """Modify existing records by id.

        Each record's set fields replace the stored ones; None fields are
        left unchanged.

        Args:
            records: The records to update, identified by their `id`s.
            ctx: The per-request governance context.

        Returns:
            The uniform envelope with no payload.
        """
        ...

    async def aupdate(
        self,
        *,
        records: list[Record],
        ctx: CallContext | None = None,
    ) -> CallResult[None]:
        """Modify existing records by id, asynchronously.

        Args:
            records: The records to update, identified by their `id`s.
            ctx: The per-request governance context.

        Returns:
            The uniform envelope with no payload.
        """
        ...

    def delete(
        self,
        *,
        ids: list[str] | None = None,
        filters: QueryFilter | None = None,
        ctx: CallContext | None = None,
    ) -> CallResult[None]:
        """Remove records by id and/or metadata filter.

        Args:
            ids: The ids to delete; None deletes by filter alone.
            filters: A metadata filter selecting/narrowing what is deleted;
                None for no filter.
            ctx: The per-request governance context.

        Returns:
            The uniform envelope with no payload.
        """
        ...

    async def adelete(
        self,
        *,
        ids: list[str] | None = None,
        filters: QueryFilter | None = None,
        ctx: CallContext | None = None,
    ) -> CallResult[None]:
        """Remove records by id and/or metadata filter, asynchronously.

        Args:
            ids: The ids to delete; None deletes by filter alone.
            filters: A metadata filter selecting/narrowing what is deleted;
                None for no filter.
            ctx: The per-request governance context.

        Returns:
            The uniform envelope with no payload.
        """
        ...

    def query(
        self,
        vector: Vector,
        *,
        filters: QueryFilter | None = None,
        limit: int = 100,
        ctx: CallContext | None = None,
    ) -> CallResult[list[QueryResult]]:
        """Search for the stored records most similar to a query vector.

        Args:
            vector: The query vector.
            filters: A metadata filter constraining the candidate set; None
                for no filter.
            limit: Maximum number of matches to return.
            ctx: The per-request governance context.

        Returns:
            The uniform envelope carrying the matches, best first.
        """
        ...

    async def aquery(
        self,
        vector: Vector,
        *,
        filters: QueryFilter | None = None,
        limit: int = 100,
        ctx: CallContext | None = None,
    ) -> CallResult[list[QueryResult]]:
        """Search for the most similar stored records, asynchronously.

        Args:
            vector: The query vector.
            filters: A metadata filter constraining the candidate set; None
                for no filter.
            limit: Maximum number of matches to return.
            ctx: The per-request governance context.

        Returns:
            The uniform envelope carrying the matches, best first.
        """
        ...

    @property
    def details(self) -> dict[str, Any]:
        """Describe this store implementation.

        Returns:
            A free-form mapping of store metadata (for example the vector
            dimensionality or distance metric); implementer-defined keys.
        """
        ...
