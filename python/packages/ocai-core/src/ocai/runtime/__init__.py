"""`ocai.runtime` — movement (architecture §5).

The execution layer between the capability facades and the wire: sans-io
policy vocabulary (`decisions`), the two thin pipeline executors (`drivers`),
port-tier middleware (`interceptors`), the composition roots (`binding`),
visible sync/async bridging (`dual`), and passive observability (`observe`).

Depends downward on `ocai.core` (and `ocai.convert` for stream transducer
types); `ocai.wire` depends on *this* package — the drivers touch wire value
objects only inside the pipeline, never at import time. All logic that is not
the one physical I/O call is synchronous and shared, which is what keeps the
sync and async paths from ever drifting.
"""

from __future__ import annotations

from ocai.runtime.binding import Binding
from ocai.runtime.binding import CompositionError
from ocai.runtime.binding import Mode
from ocai.runtime.binding import Workspace
from ocai.runtime.decisions import AsyncBackend
from ocai.runtime.decisions import Decision
from ocai.runtime.decisions import Fail
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.decisions import Retry
from ocai.runtime.decisions import Return
from ocai.runtime.decisions import SyncBackend
from ocai.runtime.decisions import WirePolicy
from ocai.runtime.drivers import AsyncDriver
from ocai.runtime.drivers import ErrorRefiner
from ocai.runtime.drivers import SyncDriver
from ocai.runtime.dual import from_async
from ocai.runtime.dual import from_sync
from ocai.runtime.interceptors import AsyncNextHandler
from ocai.runtime.interceptors import Call
from ocai.runtime.interceptors import CallInterceptor
from ocai.runtime.interceptors import NextHandler
from ocai.runtime.interceptors import acompose
from ocai.runtime.interceptors import compose
from ocai.runtime.observe import CallFinished
from ocai.runtime.observe import CallStarted
from ocai.runtime.observe import ObserveEvent
from ocai.runtime.observe import Observer
from ocai.runtime.observe import WireExchanged

__all__ = [
    "AsyncBackend",
    "AsyncDriver",
    "AsyncNextHandler",
    "Binding",
    "Call",
    "CallFinished",
    "CallInterceptor",
    "CallStarted",
    "CompositionError",
    "Decision",
    "ErrorRefiner",
    "Fail",
    "Mode",
    "NextHandler",
    "ObserveEvent",
    "Observer",
    "Outcome",
    "Proceed",
    "Retry",
    "Return",
    "SyncBackend",
    "SyncDriver",
    "WireExchanged",
    "WirePolicy",
    "Workspace",
    "acompose",
    "compose",
    "from_async",
    "from_sync",
]
