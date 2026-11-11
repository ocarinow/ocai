"""Passive metadata-only invocation and physical-attempt observations.

No event contains request/response bodies, headers, raw errors or error messages.
Registered observers can see trusted identity/correlation facts, route, usage and
fidelity evidence. Tags and extension bags are omitted from event contexts.
Exporters must allowlist identity fields and redact sensitive report paths/notes;
registration is the application's authorization boundary, not authentication here.
Required durable audit belongs in enforceable admission middleware, never observers.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import replace
from typing import Protocol
from typing import runtime_checkable
from uuid import uuid4

from ocai.core.errors import AuthError
from ocai.core.fidelity import FidelityReport
from ocai.core.fidelity import Route
from ocai.core.identity import CHAT
from ocai.core.identity import Capability
from ocai.core.identity import NodeId
from ocai.core.result import CallContext
from ocai.core.usage import Usage


@dataclass(frozen=True, slots=True)
class CallStarted:
    """One invocation starts eagerly, before admission and lazy stream I/O."""

    call_id: str
    capability: Capability = CHAT
    ctx: CallContext | None = None
    streaming: bool = False


@dataclass(frozen=True, slots=True)
class CallFinished:
    """Exactly one invocation outcome; accounting never implies output success."""

    call_id: str
    status: str
    usage: Usage | None = None
    report: FidelityReport | None = None
    route: Route | None = None
    error_type: str | None = None
    duration_s: float | None = None


@dataclass(frozen=True, slots=True)
class WireStarted:
    """A physical attempt starts; admission waits never emit this event."""

    call_id: str
    attempt: int
    node: NodeId
    streaming: bool = False


@dataclass(frozen=True, slots=True)
class WireExchanged:
    """A physical attempt ended, independently of logical conversion/admission."""

    call_id: str
    attempt: int
    status: str
    node: NodeId
    http_status: int | None = None
    error_type: str | None = None
    duration_s: float | None = None


type ObserveEvent = CallStarted | CallFinished | WireStarted | WireExchanged


@runtime_checkable
class Observer(Protocol):
    """A fast passive sink; each observer receives an independent event snapshot."""

    def on_event(self, event: ObserveEvent) -> None:
        """Observe metadata; exceptions are isolated and cannot enforce policy."""
        ...


def dispatch(observers: Sequence[Observer], event: ObserveEvent) -> None:
    """Isolate callback failures and mutations without logging sensitive exceptions."""
    for observer in observers:
        try:
            observer.on_event(deepcopy(event))
        except BaseException:
            pass


def failure_status(error: BaseException) -> str:
    """Classify cancellation without exporting exception text or provider bodies."""
    if isinstance(error, (asyncio.CancelledError, GeneratorExit, KeyboardInterrupt)):
        return "cancelled"
    if isinstance(error, AuthError) and error.status is None:
        return "rejected"
    return "failed"


class Invocation:
    """Per-invocation lifecycle state, explicitly carried by a capability wrapper."""

    def __init__(
        self, observers: Sequence[Observer], ctx: CallContext | None, *, streaming: bool = False
    ) -> None:
        """Snapshot context and emit start before any admission policy executes."""
        self.observers = tuple(observers)
        self.ctx = replace(
            deepcopy(ctx) if ctx else CallContext(),
            call_id=ctx.call_id if ctx and ctx.call_id else uuid4().hex,
        )
        self.call_id = self.ctx.call_id or ""
        self.started = time.monotonic()
        self.finished = False
        safe = replace(self.ctx, tags={}, extensions={})
        dispatch(self.observers, CallStarted(self.call_id, ctx=safe, streaming=streaming))

    def finish(
        self,
        *,
        status: str = "completed",
        usage: Usage | None = None,
        report: FidelityReport | None = None,
        route: Route | None = None,
        error: BaseException | None = None,
    ) -> None:
        """Emit once, after cleanup; error objects never enter the event."""
        if self.finished:
            return
        self.finished = True
        dispatch(
            self.observers,
            CallFinished(
                self.call_id,
                status,
                usage,
                report,
                route,
                type(error).__name__ if error else None,
                time.monotonic() - self.started,
            ),
        )


class Attempt:
    """Per-physical-attempt observations, correlated by explicit CallContext."""

    def __init__(
        self,
        observers: Sequence[Observer],
        ctx: CallContext | None,
        node: NodeId,
        attempt: int,
        *,
        streaming: bool = False,
    ) -> None:
        """Emit immediately before calling the transport, after credential setup."""
        self.observers = tuple(observers)
        self.call_id = ctx.call_id if ctx and ctx.call_id else uuid4().hex
        self.node, self.attempt = node, attempt
        self.started = time.monotonic()
        self.finished = False
        dispatch(self.observers, WireStarted(self.call_id, attempt, node, streaming))

    def finish(self, error: BaseException | None = None, http_status: int | None = None) -> None:
        """Close the attempt once; a successful HTTP stream may still be malformed."""
        if self.finished:
            return
        self.finished = True
        status = failure_status(error) if error is not None else "completed"
        if isinstance(error, GeneratorExit):
            status = "closed"
        dispatch(
            self.observers,
            WireExchanged(
                self.call_id,
                self.attempt,
                status,
                self.node,
                http_status,
                type(error).__name__ if error else None,
                time.monotonic() - self.started,
            ),
        )
