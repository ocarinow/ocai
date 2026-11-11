"""Port-tier middleware: `CallInterceptor` chains around any capability port.

Interceptors operate on **canonical IR calls** — a `Call` going down, a
`CallResult` coming back — one tier above the wire. The admission test for
this tier is strict: a concern belongs here only when it is *meaningful for
local AND remote adapters alike*. Fallback, semantic caching, policy and
governance gates, cost metering, and tracing all pass (a FAISS store and an
OpenAI model both deserve them); anything that presupposes HTTP — retry on
`TransientError`, rate limiting, exchange capture — does not, and lives in
`ocai.wire.policies` instead.

An interceptor wraps the *next* handler, onion-style: it may inspect or
replace the `Call`, short-circuit with its own `CallResult` (a cache hit, a
governance refusal), call `next` zero, one, or several times (fallback calls
it against a different target), and inspect or replace the result. Because
every port returns the uniform `CallResult`, one interceptor implementation
composes identically over every capability.

`compose`/`acompose` fold a sequence of interceptors over a terminal handler
(typically the facade's own call) into a single handler; the §3.4 front door
(`ocai.chat.model(..., interceptors=...)`) applies its chain to every model
it builds.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Iterator
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from typing import Protocol
from typing import runtime_checkable

from ocai.core.result import CallContext
from ocai.core.result import CallResult
from ocai.core.result import StreamOutcome


@dataclass(frozen=True, slots=True)
class Call:
    """One canonical invocation traveling down an interceptor chain.

    Pairs the capability request payload with the per-request governance
    context so interceptors can gate on `ctx` (classification, tenant,
    deadline) without the payload and context traveling out of band. The
    request stays `Any` at this tier because interceptors are
    capability-neutral — a chain serves `ChatRequest` and an embedding
    request with the same code.

    Attributes:
        request: The canonical request payload (e.g. a `ChatRequest`).
        ctx: The governance carrier riding along with the call, if any.
    """

    request: Any
    ctx: CallContext | None = None


# The continuation an interceptor invokes to pass the call inward. The
# innermost handler is the port's own call (the terminal).
type NextHandler = Callable[[Call], CallResult[Any]]
type AsyncNextHandler = Callable[[Call], Awaitable[CallResult[Any]]]


@runtime_checkable
class CallInterceptor(Protocol):
    """Port-tier middleware over canonical calls, with sync and async faces.

    Both faces express the same behavior; the driver mode selects which one
    runs. A pure interceptor implements both by sharing its logic; an
    interceptor bound to effectful backends declares the matching
    `SyncBackend`/`AsyncBackend` faces (`ocai.runtime.decisions`) so
    composition-time validation can reject an impossible composition up
    front.
    """

    def intercept(self, call: Call, next: NextHandler) -> CallResult[Any]:
        """Handle `call`, delegating inward via `next` as needed (sync face).

        Args:
            call: The canonical call traveling down the chain.
            next: The continuation for the rest of the chain; call it zero
                times to short-circuit, once to pass through, or several
                times (e.g. fallback across targets).

        Returns:
            The `CallResult` to hand back up the chain — `next`'s result,
            or a replacement.
        """
        ...

    async def aintercept(self, call: Call, next: AsyncNextHandler) -> CallResult[Any]:
        """Handle `call`, delegating inward via `next` as needed (async face).

        Args:
            call: The canonical call traveling down the chain.
            next: The async continuation for the rest of the chain.

        Returns:
            The `CallResult` to hand back up the chain.
        """
        ...


def compose(
    interceptors: Sequence[CallInterceptor],
    terminal: NextHandler,
) -> NextHandler:
    """Fold `interceptors` over `terminal` into one sync handler.

    The first interceptor in the sequence is the outermost layer: it sees the
    call first and the result last. An empty sequence returns `terminal`
    unchanged.

    Args:
        interceptors: The chain, outermost first.
        terminal: The innermost handler — typically the port's own call.

    Returns:
        A single handler running the whole onion.
    """
    handler = terminal
    for interceptor in reversed(interceptors):
        handler = _bind(interceptor, handler)
    return handler


def acompose(
    interceptors: Sequence[CallInterceptor],
    terminal: AsyncNextHandler,
) -> AsyncNextHandler:
    """Fold `interceptors` over `terminal` into one async handler.

    The async twin of `compose`, dispatching through each interceptor's
    `aintercept` face.

    Args:
        interceptors: The chain, outermost first.
        terminal: The innermost async handler.

    Returns:
        A single async handler running the whole onion.
    """
    handler = terminal
    for interceptor in reversed(interceptors):
        handler = _abind(interceptor, handler)
    return handler


def _bind(interceptor: CallInterceptor, next: NextHandler) -> NextHandler:
    """Close `interceptor` over `next` (avoids the late-binding loop pitfall)."""

    def handler(call: Call) -> CallResult[Any]:
        return interceptor.intercept(call, next)

    return handler


def _abind(interceptor: CallInterceptor, next: AsyncNextHandler) -> AsyncNextHandler:
    """Close `interceptor` over the async `next` continuation."""

    async def handler(call: Call) -> CallResult[Any]:
        return await interceptor.aintercept(call, next)

    return handler


@runtime_checkable
class SyncStream(Protocol):
    """Capability-neutral owned iterator returned by streaming middleware."""

    def __iter__(self) -> Iterator[Any]:
        """Return the iterator without consuming or buffering it."""
        ...

    def __next__(self) -> Any:
        """Pull one capability event."""
        ...

    def close(self) -> None:
        """Close upstream, including when no event has been consumed."""
        ...

    @property
    def outcome(self) -> StreamOutcome | None:
        """Available terminal execution evidence, or None while pending."""
        ...


@runtime_checkable
class AsyncStream(Protocol):
    """Async twin of the capability-neutral owned stream."""

    def __aiter__(self) -> AsyncIterator[Any]:
        """Return the async iterator without pulling events."""
        ...

    async def __anext__(self) -> Any:
        """Pull one capability event asynchronously."""
        ...

    async def aclose(self) -> None:
        """Close upstream, including an unconsumed stream."""
        ...

    @property
    def outcome(self) -> StreamOutcome | None:
        """Available terminal execution evidence, or None while pending."""
        ...


type NextStreamHandler = Callable[[Call], SyncStream]
type AsyncNextStreamHandler = Callable[[Call], Awaitable[AsyncStream]]


@runtime_checkable
class StreamInterceptor(Protocol):
    """Explicit stream admission/wrapping contract, distinct from unary results.

    Admission runs eagerly before delegating. Wrappers own and close their
    continuation's stream, preserve terminal accounting, and must not buffer
    the full response. Never restart generation after exposing an event.
    Implement alongside CallInterceptor to govern all four capability faces.
    """

    def intercept_stream(self, call: Call, next: NextStreamHandler) -> SyncStream:
        """Admit, reject or wrap the owned synchronous continuation stream."""
        ...

    async def aintercept_stream(self, call: Call, next: AsyncNextStreamHandler) -> AsyncStream:
        """Admit, reject or wrap the owned asynchronous continuation stream."""
        ...


def compose_stream(
    interceptors: Sequence[StreamInterceptor], terminal: NextStreamHandler
) -> NextStreamHandler:
    """Compose a streaming onion, outermost first, without pulling any events."""
    handler = terminal
    for interceptor in reversed(interceptors):
        handler = _bind_stream(interceptor, handler)
    return handler


def _bind_stream(interceptor: StreamInterceptor, next: NextStreamHandler) -> NextStreamHandler:
    def handler(call: Call) -> SyncStream:
        acquired: SyncStream | None = None
        used = False

        def once(inner: Call) -> SyncStream:
            nonlocal acquired, used
            if used:
                raise RuntimeError(
                    "a streaming continuation is single-use; generation cannot restart"
                )
            used = True
            acquired = next(inner)
            return acquired

        try:
            return interceptor.intercept_stream(call, once)
        except BaseException:
            if acquired is not None:
                acquired.close()
            raise

    return handler


def acompose_stream(
    interceptors: Sequence[StreamInterceptor], terminal: AsyncNextStreamHandler
) -> AsyncNextStreamHandler:
    """Compose the async streaming onion with the same admission order."""
    handler = terminal
    for interceptor in reversed(interceptors):
        handler = _abind_stream(interceptor, handler)
    return handler


def _abind_stream(
    interceptor: StreamInterceptor, next: AsyncNextStreamHandler
) -> AsyncNextStreamHandler:
    async def handler(call: Call) -> AsyncStream:
        acquired: AsyncStream | None = None
        used = False

        async def once(inner: Call) -> AsyncStream:
            nonlocal acquired, used
            if used:
                raise RuntimeError(
                    "a streaming continuation is single-use; generation cannot restart"
                )
            used = True
            acquired = await next(inner)
            return acquired

        try:
            return await interceptor.aintercept_stream(call, once)
        except BaseException:
            if acquired is not None:
                await acquired.aclose()
            raise

    return handler
