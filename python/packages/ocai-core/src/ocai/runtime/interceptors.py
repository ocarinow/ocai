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

from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from typing import Protocol
from typing import runtime_checkable

from ocai.core.result import CallContext
from ocai.core.result import CallResult


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
