"""[PROVISIONAL] The `EmbeddingModel` port.

The provider-neutral embedding contract, reshaped to the uniform port
grammar (architecture §2.3): named request in, `CallResult`-wrapped named
response out, optional `CallContext` threaded through — so governance,
cost, tracing, and fallback interceptors compose over an embedding adapter
exactly as they do over chat, local or remote.

Provisional per architecture §9: this port freezes only after it carries
`CallResult` in real use.
"""

from __future__ import annotations

from typing import Any
from typing import Protocol
from typing import runtime_checkable

from ocai.core.result import CallContext
from ocai.core.result import CallResult
from ocai.embedding.types.request import EmbeddingRequest
from ocai.embedding.types.response import EmbeddingResponse


@runtime_checkable
class EmbeddingModel(Protocol):
    """An embedding provider port — structural, never subclassed.

    Implementers accept the canonical `EmbeddingRequest` and return a
    `CallResult[EmbeddingResponse]` — the same uniform envelope every
    capability port returns, which is what fixed the old port's missing
    channel for usage and fidelity reports.
    """

    def embed(
        self,
        request: EmbeddingRequest,
        *,
        ctx: CallContext | None = None,
    ) -> CallResult[EmbeddingResponse]:
        """Embed the request's inputs, synchronously.

        Args:
            request: The canonical embedding request.
            ctx: The per-request governance context.

        Returns:
            The uniform envelope carrying one `Embedding` per input.
        """
        ...

    async def aembed(
        self,
        request: EmbeddingRequest,
        *,
        ctx: CallContext | None = None,
    ) -> CallResult[EmbeddingResponse]:
        """Embed the request's inputs, asynchronously.

        Args:
            request: The canonical embedding request.
            ctx: The per-request governance context.

        Returns:
            The uniform envelope carrying one `Embedding` per input.
        """
        ...

    @property
    def details(self) -> dict[str, Any]:
        """Describe this model implementation.

        Returns:
            A free-form mapping of model metadata (for example, model name
            or output dimensionality); implementer-defined keys.
        """
        ...
