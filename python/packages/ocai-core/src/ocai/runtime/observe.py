"""Observability: the `Observer` protocol and its event shapes [provisional].

Observers are the *read-only* counterpart of interceptors and policies: they
see what happened but can never change it — `on_event` returns nothing and a
raising observer must never break a call (dispatchers swallow and log observer
failures). Enterprise satellites (a future `ocai-otel`) implement this
protocol; the kernel never grows an opinion about telemetry backends.

The event dataclasses below are **[provisional]** per architecture §5/§9: they
freeze at v1.0 only after the `/responses` migration and a real cross-provider
failover have been exercised through them. Until then fields may be added or
reshaped; consumers should match on event type and tolerate new fields.

Events pair at two tiers, mirroring the interceptor/policy split:
`CallStarted`/`CallFinished` bracket one port-tier canonical call (local or
remote); `WireExchanged` records one wire-tier attempt (remote only, emitted
per retry). All wire events are **post-redaction**: the driver applies the
credential after every hook and emitted requests must never carry the auth
header.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol
from typing import runtime_checkable

from ocai.core.errors import OcaiError
from ocai.core.identity import Capability
from ocai.core.result import CallContext
from ocai.core.result import CallResult

if TYPE_CHECKING:
    from ocai.wire.http import HttpRequest
    from ocai.wire.http import HttpResponse


@dataclass(frozen=True, slots=True)
class CallStarted:
    """A port-tier call entered the interceptor chain [provisional].

    Emitted once per canonical call, before any interceptor runs, so a tracer
    can open a span that later `WireExchanged` and `CallFinished` events (same
    `call_id`) nest under.

    Attributes:
        call_id: A driver-generated correlation id shared by every event of
            one call, including its per-attempt wire exchanges.
        capability: The capability being invoked (`chat`, `embedding`, …),
            when known.
        ctx: The governance context riding with the call, if any — safe to
            emit because `CallContext` never carries payloads or secrets.
    """

    call_id: str
    capability: Capability | None = None
    ctx: CallContext | None = None


@dataclass(frozen=True, slots=True)
class CallFinished:
    """A port-tier call completed — successfully or not [provisional].

    Carries the whole `CallResult` on success so observers can meter usage,
    read the `FidelityReport`, and record the `Route` without re-deriving any
    of it; exactly one of `result`/`error` is set.

    Attributes:
        call_id: The correlation id from the matching `CallStarted`.
        result: The uniform result envelope, when the call succeeded.
        error: The taxonomy error, when the call failed.
        duration_s: Wall-clock seconds for the whole call, retries included.
    """

    call_id: str
    result: CallResult[Any] | None = None
    error: OcaiError | None = None
    duration_s: float | None = None


@dataclass(frozen=True, slots=True)
class WireExchanged:
    """One wire attempt completed: a request/response (or error) pair [provisional].

    Emitted by the drivers once per attempt — a call that retried twice emits
    three of these under one `call_id`. The `request` is the **post-redaction**
    shape: the credential is applied at the driver leaf after hooks, and the
    emitted value must never include the auth header. This event is also what
    a `WireTap` policy feeds to content-addressed archive satellites.

    Attributes:
        call_id: The correlation id of the owning canonical call.
        request: The wire request as the hooks saw it (never authenticated).
        response: The wire response, when the attempt succeeded.
        error: The refined taxonomy error, when the attempt failed.
        attempt: The zero-based attempt index within the call.
        duration_s: Wall-clock seconds for this single attempt.
    """

    call_id: str
    request: HttpRequest
    response: HttpResponse | None = None
    error: OcaiError | None = None
    attempt: int = 0
    duration_s: float | None = None


# The closed-for-now union observers receive. New event types may be added
# before the v1.0 freeze; observers must ignore types they do not know.
type ObserveEvent = CallStarted | CallFinished | WireExchanged


@runtime_checkable
class Observer(Protocol):
    """A passive sink for runtime events [provisional].

    Registered at composition time on the components that emit events;
    called synchronously on the calling thread by drivers and interceptor
    chains, so implementations must be fast and non-blocking (buffer and
    export elsewhere). An observer can never alter a call: it has no return
    channel and dispatchers isolate its exceptions.
    """

    def on_event(self, event: ObserveEvent) -> None:
        """Receive one runtime event.

        Args:
            event: The event that occurred; match on its type and ignore
                unknown types (the union grows until the v1.0 freeze).
        """
        ...
