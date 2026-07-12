"""The `ChatModel` port — the one chat contract (architecture §3.2).

The port is the **only** contract; "wire-backed" (`WireChatModel`) is one
implementation. An in-process adapter (a local llama.cpp binding, a test
double) implements this protocol directly and returns the same
`CallResult` — that symmetry is what lets port-tier `CallInterceptor`s
(fallback, semantic cache, policy, cost, tracing) compose identically over
local and remote models.

Naming convention (repo-wide): bare name = sync, `a`-prefix = async
(`chat`/`achat`, `stream`/`astream`). Every method threads the optional
`CallContext` keyword — the sanctioned carrier for tenant, principal,
classification, and deadline, which routing policy needs *at call time*.
"""

from __future__ import annotations

from typing import Any
from typing import Protocol
from typing import runtime_checkable

from ocai.chat.types.request import ChatRequest
from ocai.chat.types.response import ChatResponse
from ocai.chat.types.stream import AsyncChatStream
from ocai.chat.types.stream import ChatStream
from ocai.core.result import CallContext
from ocai.core.result import CallResult


@runtime_checkable
class ChatModel(Protocol):
    """A chat provider port — structural, never subclassed.

    Implementers accept the canonical `ChatRequest` and return canonical
    results wrapped in `CallResult` — the uniform envelope carrying the
    route, the `FidelityReport` (its only home), usage, and the raw body.
    Payloads stay pure; honesty rides the envelope.

    The protocol is `runtime_checkable`, so `isinstance` verifies member
    presence; `Binding.validate()` performs the deeper composition-time
    check.
    """

    def chat(
        self,
        request: ChatRequest,
        *,
        ctx: CallContext | None = None,
    ) -> CallResult[ChatResponse]:
        """Send a blocking chat request, synchronously.

        Args:
            request: The canonical chat request.
            ctx: The per-request governance context, seen by every
                interceptor and policy hook on the way down.

        Returns:
            The uniform envelope carrying the canonical `ChatResponse`.
        """
        ...

    async def achat(
        self,
        request: ChatRequest,
        *,
        ctx: CallContext | None = None,
    ) -> CallResult[ChatResponse]:
        """Send a blocking chat request, asynchronously.

        Args:
            request: The canonical chat request.
            ctx: The per-request governance context.

        Returns:
            The uniform envelope carrying the canonical `ChatResponse`.
        """
        ...

    def stream(
        self,
        request: ChatRequest,
        *,
        ctx: CallContext | None = None,
    ) -> ChatStream:
        """Send a streaming chat request, synchronously.

        The returned stream yields canonical `ChatChunk`s and exposes the
        authoritative `StreamEnd` (usage, finish, report) as `.end` after
        exhaustion. The fold law binds it to `chat`:
        `StreamAccumulator.fold(stream(request))` equals
        `chat(request).value`.

        Args:
            request: The canonical chat request.
            ctx: The per-request governance context.

        Returns:
            The iterable canonical chunk stream.
        """
        ...

    async def astream(
        self,
        request: ChatRequest,
        *,
        ctx: CallContext | None = None,
    ) -> AsyncChatStream:
        """Send a streaming chat request, asynchronously.

        Args:
            request: The canonical chat request.
            ctx: The per-request governance context.

        Returns:
            The async-iterable canonical chunk stream.
        """
        ...

    @property
    def details(self) -> dict[str, Any]:
        """Describe this model implementation.

        Returns:
            A free-form mapping of descriptive metadata (e.g. the dialect
            spoken, the host label, declared capabilities) used by
            interceptors and diagnostics — never by conversion logic.
        """
        ...
