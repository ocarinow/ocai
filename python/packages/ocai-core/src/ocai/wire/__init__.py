"""`ocai.wire` — remote transport (architecture §6).

Everything that only exists because a provider is on the other side of a
network: the HTTP value objects that cross the transport port (`http` — also
the audit-archive contract shape), the sans-io SSE parser (`sse`), the twin
transport ports and their httpx leaf (`transport` — httpx imported lazily,
behind the `[http]` extra), trait-driven hosting values (`hosting` — no
`CloudProvider` class), and Decision-based wire policies (`policies`).

Depends on `ocai.runtime` (policies speak its Decision vocabulary); plugins
depend on core+convert only and never on this package, so an offline audit
tool can re-convert archived traffic without the ability to make network
calls. Local adapters never touch this layer at all — local and remote are
peers at the capability port.
"""

from __future__ import annotations

from ocai.core.traits import DialectTraits
from ocai.wire.eventstream import EventStreamFrame
from ocai.wire.eventstream import EventStreamHeader
from ocai.wire.eventstream import EventStreamParser
from ocai.wire.eventstream import EventStreamProtocolError
from ocai.wire.eventstream import eventstream_framing
from ocai.wire.framing import StreamDecoder
from ocai.wire.framing import StreamFraming
from ocai.wire.framing import sse_framing
from ocai.wire.hosting import Custom
from ocai.wire.hosting import Direct
from ocai.wire.hosting import EndpointSpec
from ocai.wire.hosting import EnvelopeTransform
from ocai.wire.hosting import ErrorMappingHost
from ocai.wire.hosting import FramingHost
from ocai.wire.hosting import Host
from ocai.wire.hosting import IdentityEnvelope
from ocai.wire.hosting import Operation
from ocai.wire.hosting import ResponseMappingHost
from ocai.wire.hosting import Vertex
from ocai.wire.http import DriverResponse
from ocai.wire.http import HttpRequest
from ocai.wire.http import HttpResponse
from ocai.wire.outcomes import HostAdaptation
from ocai.wire.outcomes import HostErrorMapper
from ocai.wire.outcomes import HostResponseAdapter
from ocai.wire.policies import RateLimitPolicy
from ocai.wire.policies import RetryPolicy
from ocai.wire.policies import WireTap
from ocai.wire.sse import SSEParser
from ocai.wire.sse import SSEvent
from ocai.wire.transport import HttpxTransport
from ocai.wire.transport import SyncTransport
from ocai.wire.transport import Transport

__all__ = [
    "EventStreamFrame",
    "EventStreamHeader",
    "EventStreamParser",
    "EventStreamProtocolError",
    "eventstream_framing",
    "Custom",
    "DialectTraits",
    "Direct",
    "EndpointSpec",
    "EnvelopeTransform",
    "ErrorMappingHost",
    "ResponseMappingHost",
    "HostErrorMapper",
    "HostResponseAdapter",
    "HostAdaptation",
    "FramingHost",
    "Host",
    "HttpRequest",
    "DriverResponse",
    "HttpResponse",
    "HttpxTransport",
    "IdentityEnvelope",
    "Operation",
    "RateLimitPolicy",
    "RetryPolicy",
    "SSEParser",
    "SSEvent",
    "StreamDecoder",
    "StreamFraming",
    "sse_framing",
    "SyncTransport",
    "Transport",
    "Vertex",
    "WireTap",
]
