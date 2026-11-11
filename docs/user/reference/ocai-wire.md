# `ocai.wire` API reference

Generated from the checked-out package sources. Signatures, declared fields,
methods, type aliases and explicit re-exports are checked for drift. Inherited
members follow their named base class; a type's presence does not establish
provider execution support. See [supported features](../provider-feature-matrix.md).

## `ocai.wire`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/wire/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-wire-dialecttraits"></span>`DialectTraits` | [`ocai.core.traits.DialectTraits`](ocai-core.md#ocai-core-traits-dialecttraits) |
| <span id="ocai-wire-eventstreamframe"></span>`EventStreamFrame` | [`ocai.wire.eventstream.EventStreamFrame`](ocai-wire.md#ocai-wire-eventstream-eventstreamframe) |
| <span id="ocai-wire-eventstreamheader"></span>`EventStreamHeader` | [`ocai.wire.eventstream.EventStreamHeader`](ocai-wire.md#ocai-wire-eventstream-eventstreamheader) |
| <span id="ocai-wire-eventstreamparser"></span>`EventStreamParser` | [`ocai.wire.eventstream.EventStreamParser`](ocai-wire.md#ocai-wire-eventstream-eventstreamparser) |
| <span id="ocai-wire-eventstreamprotocolerror"></span>`EventStreamProtocolError` | [`ocai.wire.eventstream.EventStreamProtocolError`](ocai-wire.md#ocai-wire-eventstream-eventstreamprotocolerror) |
| <span id="ocai-wire-eventstream-framing"></span>`eventstream_framing` | [`ocai.wire.eventstream.eventstream_framing`](ocai-wire.md#ocai-wire-eventstream-eventstream-framing) |
| <span id="ocai-wire-streamdecoder"></span>`StreamDecoder` | [`ocai.wire.framing.StreamDecoder`](ocai-wire.md#ocai-wire-framing-streamdecoder) |
| <span id="ocai-wire-streamframing"></span>`StreamFraming` | [`ocai.wire.framing.StreamFraming`](ocai-wire.md#ocai-wire-framing-streamframing) |
| <span id="ocai-wire-sse-framing"></span>`sse_framing` | [`ocai.wire.framing.sse_framing`](ocai-wire.md#ocai-wire-framing-sse-framing) |
| <span id="ocai-wire-custom"></span>`Custom` | [`ocai.wire.hosting.Custom`](ocai-wire.md#ocai-wire-hosting-custom) |
| <span id="ocai-wire-direct"></span>`Direct` | [`ocai.wire.hosting.Direct`](ocai-wire.md#ocai-wire-hosting-direct) |
| <span id="ocai-wire-endpointspec"></span>`EndpointSpec` | [`ocai.wire.hosting.EndpointSpec`](ocai-wire.md#ocai-wire-hosting-endpointspec) |
| <span id="ocai-wire-envelopetransform"></span>`EnvelopeTransform` | [`ocai.wire.hosting.EnvelopeTransform`](ocai-wire.md#ocai-wire-hosting-envelopetransform) |
| <span id="ocai-wire-errormappinghost"></span>`ErrorMappingHost` | [`ocai.wire.hosting.ErrorMappingHost`](ocai-wire.md#ocai-wire-hosting-errormappinghost) |
| <span id="ocai-wire-framinghost"></span>`FramingHost` | [`ocai.wire.hosting.FramingHost`](ocai-wire.md#ocai-wire-hosting-framinghost) |
| <span id="ocai-wire-host"></span>`Host` | [`ocai.wire.hosting.Host`](ocai-wire.md#ocai-wire-hosting-host) |
| <span id="ocai-wire-identityenvelope"></span>`IdentityEnvelope` | [`ocai.wire.hosting.IdentityEnvelope`](ocai-wire.md#ocai-wire-hosting-identityenvelope) |
| <span id="ocai-wire-operation"></span>`Operation` | [`ocai.wire.hosting.Operation`](ocai-wire.md#ocai-wire-hosting-operation) |
| <span id="ocai-wire-responsemappinghost"></span>`ResponseMappingHost` | [`ocai.wire.hosting.ResponseMappingHost`](ocai-wire.md#ocai-wire-hosting-responsemappinghost) |
| <span id="ocai-wire-vertex"></span>`Vertex` | [`ocai.wire.hosting.Vertex`](ocai-wire.md#ocai-wire-hosting-vertex) |
| <span id="ocai-wire-driverresponse"></span>`DriverResponse` | [`ocai.wire.http.DriverResponse`](ocai-wire.md#ocai-wire-http-driverresponse) |
| <span id="ocai-wire-httprequest"></span>`HttpRequest` | [`ocai.wire.http.HttpRequest`](ocai-wire.md#ocai-wire-http-httprequest) |
| <span id="ocai-wire-httpresponse"></span>`HttpResponse` | [`ocai.wire.http.HttpResponse`](ocai-wire.md#ocai-wire-http-httpresponse) |
| <span id="ocai-wire-hostadaptation"></span>`HostAdaptation` | [`ocai.wire.outcomes.HostAdaptation`](ocai-wire.md#ocai-wire-outcomes-hostadaptation) |
| <span id="ocai-wire-hosterrormapper"></span>`HostErrorMapper` | [`ocai.wire.outcomes.HostErrorMapper`](ocai-wire.md#ocai-wire-outcomes-hosterrormapper) |
| <span id="ocai-wire-hostresponseadapter"></span>`HostResponseAdapter` | [`ocai.wire.outcomes.HostResponseAdapter`](ocai-wire.md#ocai-wire-outcomes-hostresponseadapter) |
| <span id="ocai-wire-ratelimitpolicy"></span>`RateLimitPolicy` | [`ocai.wire.policies.RateLimitPolicy`](ocai-wire.md#ocai-wire-policies-ratelimitpolicy) |
| <span id="ocai-wire-retrypolicy"></span>`RetryPolicy` | [`ocai.wire.policies.RetryPolicy`](ocai-wire.md#ocai-wire-policies-retrypolicy) |
| <span id="ocai-wire-wiretap"></span>`WireTap` | [`ocai.wire.policies.WireTap`](ocai-wire.md#ocai-wire-policies-wiretap) |
| <span id="ocai-wire-sseparser"></span>`SSEParser` | [`ocai.wire.sse.SSEParser`](ocai-wire.md#ocai-wire-sse-sseparser) |
| <span id="ocai-wire-ssevent"></span>`SSEvent` | [`ocai.wire.sse.SSEvent`](ocai-wire.md#ocai-wire-sse-ssevent) |
| <span id="ocai-wire-httpxtransport"></span>`HttpxTransport` | [`ocai.wire.transport.HttpxTransport`](ocai-wire.md#ocai-wire-transport-httpxtransport) |
| <span id="ocai-wire-synctransport"></span>`SyncTransport` | [`ocai.wire.transport.SyncTransport`](ocai-wire.md#ocai-wire-transport-synctransport) |
| <span id="ocai-wire-transport"></span>`Transport` | [`ocai.wire.transport.Transport`](ocai-wire.md#ocai-wire-transport-transport) |

## `ocai.wire.eventstream`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/wire/eventstream.py)

### `EventStreamHeader` { #ocai-wire-eventstream-eventstreamheader }

```python
class EventStreamHeader:
    name: str
    type_code: int
    value: bool | int | bytes | str | UUID
```

````text
A typed wire header; timestamp values retain exact signed milliseconds.
````

### `EventStreamFrame` { #ocai-wire-eventstream-eventstreamframe }

```python
class EventStreamFrame:
    headers: tuple[EventStreamHeader, ...]
    payload: bytes
```

````text
One CRC-verified message, including opaque payload and typed headers.
````

### `EventStreamProtocolError` { #ocai-wire-eventstream-eventstreamprotocolerror }

```python
class EventStreamProtocolError(StreamProtocolError)
```

````text
Framing failure with verified prefix frames from the failed feed only.

Completed frames are explicit application evidence, never automatic payload
logs. Frames returned by earlier feed calls are not repeated here.
````

#### `EventStreamProtocolError.__init__` { #ocai-wire-eventstream-eventstreamprotocolerror---init-- }

```python
def __init__(self, message: str, *, code: str='invalid_eventstream', completed: tuple[EventStreamFrame, ...]=()) -> None
```

````text
Retain the verified prefix without exposing corrupt bytes in the message.
````

### `EventStreamParser` { #ocai-wire-eventstream-eventstreamparser }

```python
class EventStreamParser
```

````text
Parse complete frames, buffering at most one configured-size frame.

max_frame_bytes is a local resource budget, not a service quota. Service-only
payload/header size limits are deliberately not checked by this client.
After failure or close, a new parser is required. finish is idempotent after
successful EOF; it validates framing only, never semantic completion.
````

#### `EventStreamParser.__init__` { #ocai-wire-eventstream-eventstreamparser---init-- }

```python
def __init__(self, max_frame_bytes: int=_DEFAULT_LIMIT) -> None
```

````text
Create an empty parser with an explicit finite frame-memory budget.
````

#### `EventStreamParser.buffered_bytes` { #ocai-wire-eventstream-eventstreamparser-buffered-bytes }

```python
@property
def buffered_bytes(self) -> int
```

````text
Return retained framing bytes, without exposing their content.
````

#### `EventStreamParser.feed` { #ocai-wire-eventstream-eventstreamparser-feed }

```python
def feed(self, chunk: bytes) -> list[EventStreamFrame]
```

````text
Consume bytes in order; reject malformed framing and retain its prefix.

Args:
    chunk: An arbitrary slice of the incoming byte stream.

Returns:
    Verified frames completed by this slice, in wire order.

Raises:
    EventStreamProtocolError: On invalid framing, resource exhaustion or
        use after termination. completed contains this feed's valid prefix.
````

#### `EventStreamParser.finish` { #ocai-wire-eventstream-eventstreamparser-finish }

```python
def finish(self) -> list[EventStreamFrame]
```

````text
Validate EOF; never emit a synthetic provider terminal record.
````

#### `EventStreamParser.close` { #ocai-wire-eventstream-eventstreamparser-close }

```python
def close(self) -> None
```

````text
Release partial bytes without interpreting them or emitting anything.
````

### `eventstream_framing` { #ocai-wire-eventstream-eventstream-framing }

```python
def eventstream_framing(max_frame_bytes: int=_DEFAULT_LIMIT) -> StreamFraming
```

````text
Select independent EventStream decoders with a fingerprinted local budget.
````

## `ocai.wire.framing`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/wire/framing.py)

### `StreamDecoder` { #ocai-wire-framing-streamdecoder }

```python
class StreamDecoder(Protocol)
```

````text
One stream's owned, synchronous framing/envelope decoder.

Emit plugin input events, never canonical capability parts. Implementations
buffer incomplete frames rather than whole responses, and reject malformed
or truncated frames according to their framing's rules. Factories return fresh
instances; decoders never perform I/O.
````

#### `StreamDecoder.feed` { #ocai-wire-framing-streamdecoder-feed }

```python
def feed(self, chunk: bytes) -> list[Any]
```

````text
Consume raw bytes and emit complete, unwrapped events in wire order.
````

#### `StreamDecoder.finish` { #ocai-wire-framing-streamdecoder-finish }

```python
def finish(self) -> list[Any]
```

````text
Validate normal EOF and emit remaining complete events, once.

Never invoked on cancellation, explicit close or failure. EOF alone is
not provider success; semantic terminal validation stays in the plugin.
````

#### `StreamDecoder.close` { #ocai-wire-framing-streamdecoder-close }

```python
def close(self) -> None
```

````text
Discard buffers on every exit, including after finish; never emit events.
````

### `StreamFraming` { #ocai-wire-framing-streamframing }

```python
class StreamFraming:
    name: str
    factory: Callable[[dict[str, Any]], StreamDecoder]
    options: Mapping[str, Any] = field(default_factory=dict[str, Any])
```

````text
Explicit framing selection with a fresh decoder factory and copied options.

Attributes:
    name: Non-secret framing/configuration vocabulary, not an interface tag.
    factory: Stable trusted callable taking detached options and producing a
        fresh decoder. No hidden mutable configuration or ambient discovery.
    options: All effective decoder configuration, as non-secret JSON data.
        Changes invalidate prepared calls; factories receive separate copies.
````

#### `StreamFraming.snapshot` { #ocai-wire-framing-streamframing-snapshot }

```python
def snapshot(self) -> StreamFraming
```

````text
Detach configuration while preserving the trusted factory identity.
````

#### `StreamFraming.configuration_id` { #ocai-wire-framing-streamframing-configuration-id }

```python
@property
def configuration_id(self) -> str
```

````text
Fingerprint options and factory identity for in-process preparation.

Bound methods identify their function and owner, not the temporary bound
method object. This detects replacement, not changes to executable code or
hidden factory state; factories must use the declared options exclusively.
````

#### `StreamFraming.build` { #ocai-wire-framing-streamframing-build }

```python
def build(self) -> StreamDecoder
```

````text
Build the one-attempt decoder from an independent configuration copy.
````

### `sse_framing` { #ocai-wire-framing-sse-framing }

```python
def sse_framing() -> StreamFraming
```

````text
Return legacy SSE selection; no stateful decoder is allocated until I/O.
````

## `ocai.wire.hosting`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/wire/hosting.py)

### `Operation` { #ocai-wire-hosting-operation }

```python
class Operation:
    name: str
    kind: str
    method: str = 'POST'
    streaming: bool = False
```

````text
A single callable operation on a composed stack — the unit a driver runs.

`Operation` is what lets one `Host` serve every capability without knowing
chat from vectors: a host switches on `kind` (an endpoint family), never
on a capability's semantics. Chat has one streaming operation; a vector
store has several (`query`, `upsert`, `delete`).

Attributes:
    name: The operation name (e.g. `"chat"`, `"embed"`, `"query"`).
    kind: The endpoint family a `Host` switches on (e.g. `"generative"`,
        `"embeddings"`, `"vector.query"`). Distinct from `name` so unrelated
        operations that share a URL shape can share a `kind`.
    method: The HTTP method for the operation. Defaults to `"POST"`.
    streaming: Whether the operation streams its response. Defaults to
        `False`.
````

### `EndpointSpec` { #ocai-wire-hosting-endpointspec }

```python
class EndpointSpec:
    dialect: NodeId
    traits: DialectTraits
    op: Operation
    resource: str
    native_path: str
```

````text
Everything a `Host` needs to place a request — passed as plain data.

Assembled by the wire-backed facade (which alone knows the codec) and
handed to a driver; the host receives it and never sees a codec, a
capability IR, or an SDK. It carries the dialect identity, the dialect's
declared traits, the operation being run, the target resource, and the
dialect's own first-party path (so `Direct` can build a first-party URL
without dialect-specific code).

Attributes:
    dialect: The wire dialect's `NodeId` — the conversion-graph node the
        payload was encoded for.
    traits: The dialect's declared `DialectTraits`.
    op: The `Operation` being performed.
    resource: The model or index/collection name the operation targets.
    native_path: The dialect's first-party URL path for `op` (e.g.
        `"/v1/messages"`), used by first-party / gateway hosts.
````

### `EnvelopeTransform` { #ocai-wire-hosting-envelopetransform }

```python
class EnvelopeTransform(Protocol)
```

````text
An optional body reshape applied on top of a dialect payload at send time.

Cloud hosts wrap/unwrap the dialect body (lift `model` into the URL,
inject a cloud version field, peel a response envelope). First-party
hosts use `IdentityEnvelope`. The driver calls `wrap` when building each
attempt's request and `unwrap` on the response body before handing it
back to the facade for graph decode.
````

#### `EnvelopeTransform.wrap` { #ocai-wire-hosting-envelopetransform-wrap }

```python
def wrap(self, payload: dict[str, Any]) -> dict[str, Any]
```

````text
Outgoing: dialect payload → host wire payload.
````

#### `EnvelopeTransform.unwrap` { #ocai-wire-hosting-envelopetransform-unwrap }

```python
def unwrap(self, payload: dict[str, Any]) -> dict[str, Any]
```

````text
Incoming: host wire payload → dialect payload.
````

### `IdentityEnvelope` { #ocai-wire-hosting-identityenvelope }

```python
class IdentityEnvelope
```

````text
The no-op envelope: first-party hosts send the dialect payload as-is.
````

#### `IdentityEnvelope.wrap` { #ocai-wire-hosting-identityenvelope-wrap }

```python
def wrap(self, payload: dict[str, Any]) -> dict[str, Any]
```

````text
Return the outgoing dialect payload unchanged.

Args:
    payload: The outgoing dialect wire payload.

Returns:
    The same `payload`, unmodified.
````

#### `IdentityEnvelope.unwrap` { #ocai-wire-hosting-identityenvelope-unwrap }

```python
def unwrap(self, payload: dict[str, Any]) -> dict[str, Any]
```

````text
Return the incoming host payload unchanged.

Args:
    payload: The incoming host wire payload.

Returns:
    The same `payload`, unmodified.
````

### `Host` { #ocai-wire-hosting-host }

```python
class Host(Protocol)
```

````text
Where a request goes: envelope + endpoint + headers, bundled.

A host is **dialect-agnostic** — every method takes an `EndpointSpec`
(plain data) so the same `Vertex(...)` value serves every dialect and
every capability that Vertex can host. First-party, cloud, and gateway
targets are all hosts; there is no `CloudProvider` base class. The
drivers read the three methods in pipeline order: `envelope(spec).wrap`
on the body, `endpoint(spec)` for the URL, `headers(spec)` merged under
the binding's `extra_headers`.
````

#### `Host.envelope` { #ocai-wire-hosting-host-envelope }

```python
def envelope(self, spec: EndpointSpec) -> EnvelopeTransform
```

````text
Return the body reshape this host applies for `spec`.
````

#### `Host.endpoint` { #ocai-wire-hosting-host-endpoint }

```python
def endpoint(self, spec: EndpointSpec) -> str
```

````text
Return the fully-qualified URL for `spec`.
````

#### `Host.headers` { #ocai-wire-hosting-host-headers }

```python
def headers(self, spec: EndpointSpec) -> Mapping[str, str]
```

````text
Return the headers this host contributes for `spec` (before auth).
````

### `FramingHost` { #ocai-wire-hosting-framinghost }

```python
class FramingHost(Protocol)
```

````text
Optional host selection of framing and stream-envelope removal.

Existing Host implementations need no new method. Selection is pure; its
factory is not invoked during preparation or for an unconsumed stream.
````

#### `FramingHost.stream_framing` { #ocai-wire-hosting-framinghost-stream-framing }

```python
def stream_framing(self, spec: EndpointSpec) -> StreamFraming
```

````text
Select non-secret decoder configuration for this streaming operation.
````

### `stream_framing` { #ocai-wire-hosting-stream-framing }

```python
def stream_framing(host: Host, spec: EndpointSpec) -> StreamFraming
```

````text
Snapshot explicit host framing or retain SSE for legacy hosts.
````

### `ErrorMappingHost` { #ocai-wire-hosting-errormappinghost }

```python
class ErrorMappingHost(Protocol)
```

````text
Optional pure host classification, selected from plain endpoint data.
````

#### `ErrorMappingHost.error_mapper` { #ocai-wire-hosting-errormappinghost-error-mapper }

```python
def error_mapper(self, spec: EndpointSpec) -> HostErrorMapper | None
```

````text
Declare a mapper for this endpoint, or retain legacy refinement.
````

### `host_error_mapper` { #ocai-wire-hosting-host-error-mapper }

```python
def host_error_mapper(host: Host, spec: EndpointSpec) -> HostErrorMapper | None
```

````text
Snapshot a declared mapper without modifying the host or transport.
````

### `ResponseMappingHost` { #ocai-wire-hosting-responsemappinghost }

```python
class ResponseMappingHost(Protocol)
```

````text
Optional governed unary response adaptation over detached wire evidence.
````

#### `ResponseMappingHost.response_adapter` { #ocai-wire-hosting-responsemappinghost-response-adapter }

```python
def response_adapter(self, spec: EndpointSpec) -> HostResponseAdapter | None
```

````text
Select explicit host response semantics, or retain the legacy path.
````

### `host_response_adapter` { #ocai-wire-hosting-host-response-adapter }

```python
def host_response_adapter(host: Host, spec: EndpointSpec) -> HostResponseAdapter | None
```

````text
Snapshot a host response declaration without executing its callback.
````

### `Direct` { #ocai-wire-hosting-direct }

```python
class Direct:
    base_url: str
```

````text
First-party hosting: the dialect's own URL, headers, and identity body.

The degenerate composition — what every first-party provider uses. The full
URL is `base_url` + the dialect's `native_path`; the headers are the
dialect's declared `first_party_headers` (e.g. Anthropic's `anthropic-version`).

Attributes:
    base_url: The provider's API origin, e.g. `"https://api.anthropic.com"`
        (no trailing slash; the dialect's `native_path` supplies the path).
````

#### `Direct.envelope` { #ocai-wire-hosting-direct-envelope }

```python
def envelope(self, spec: EndpointSpec) -> EnvelopeTransform
```

````text
Return the identity envelope: first-party sends the body unchanged.

Args:
    spec: The endpoint spec for the request (unused).

Returns:
    An `IdentityEnvelope`.
````

#### `Direct.endpoint` { #ocai-wire-hosting-direct-endpoint }

```python
def endpoint(self, spec: EndpointSpec) -> str
```

````text
Return `base_url` joined with the dialect's first-party path.

Args:
    spec: The endpoint spec carrying the dialect's `native_path`.

Returns:
    The fully-qualified first-party URL.
````

#### `Direct.headers` { #ocai-wire-hosting-direct-headers }

```python
def headers(self, spec: EndpointSpec) -> Mapping[str, str]
```

````text
Return the dialect's declared first-party headers.

Args:
    spec: The endpoint spec carrying the dialect traits.

Returns:
    Detached dialect headers with explicit version/feature groups resolved.
````

### `Custom` { #ocai-wire-hosting-custom }

```python
class Custom(HostDescriptor)
```

````text
A self-hosted or gateway target speaking a known dialect's wire.

Covers OpenAI-compatible servers (vLLM, Ollama, LiteLLM), internal proxies,
and staging endpoints: a fixed origin plus optional per-`kind` path templates.
A template may interpolate `{resource}` (the model/index name). When no
template is given for an operation's `kind`, the dialect's `native_path` is
used, so a Custom host pointed at an OpenAI-compatible server needs no paths
at all.

Attributes:
    base_url: The origin to send to, e.g. `"https://vllm.internal"`.
    paths: Optional map of `Operation.kind` → path template. A template may
        contain `{resource}`. Defaults to empty (fall back to `native_path`).

Remaining fields are declared by `HostDescriptor`: explicit path prefix,
streaming paths, non-secret static headers/query, and profile aliases/suffixes.
All declaration maps are detached from caller-owned inputs.
````

#### `Custom.from_descriptor` { #ocai-wire-hosting-custom-from-descriptor }

```python
@classmethod
def from_descriptor(cls, descriptor: HostDescriptor) -> Custom
```

````text
Compose a wire host from detached catalog data.
````

#### `Custom.profile_key` { #ocai-wire-hosting-custom-profile-key }

```python
def profile_key(self, resource: str) -> str
```

````text
Resolve declared aliases/suffixes without changing the wire resource.
````

#### `Custom.envelope` { #ocai-wire-hosting-custom-envelope }

```python
def envelope(self, spec: EndpointSpec) -> EnvelopeTransform
```

````text
Return the identity envelope: a gateway speaks the dialect verbatim.

Args:
    spec: The endpoint spec for the request (unused).

Returns:
    An `IdentityEnvelope`.
````

#### `Custom.endpoint` { #ocai-wire-hosting-custom-endpoint }

```python
def endpoint(self, spec: EndpointSpec) -> str
```

````text
Return `base_url` joined with the per-kind template (or `native_path`).

Args:
    spec: The endpoint spec carrying the operation kind, resource, and
        the dialect's `native_path`.

Returns:
    The fully-qualified URL.
````

#### `Custom.headers` { #ocai-wire-hosting-custom-headers }

```python
def headers(self, spec: EndpointSpec) -> Mapping[str, str]
```

````text
Return the dialect's first-party headers (a gateway mimics first-party).

Args:
    spec: The endpoint spec carrying the dialect traits.

Returns:
    Detached dialect headers with explicit version/feature groups resolved.
````

### `ProfileHost` { #ocai-wire-hosting-profilehost }

```python
class ProfileHost(Protocol)
```

````text
Optional profile-lookup normalization; legacy Host implementations need no change.
````

#### `ProfileHost.profile_key` { #ocai-wire-hosting-profilehost-profile-key }

```python
def profile_key(self, resource: str) -> str
```

````text
Return the catalog profile lookup key, leaving execution resource untouched.
````

### `profile_key` { #ocai-wire-hosting-profile-key }

```python
def profile_key(host: Host, resource: str) -> str
```

````text
Resolve an optional host alias, otherwise use the exact execution resource.
````

### `Vertex` { #ocai-wire-hosting-vertex }

```python
class Vertex:
    project: str
    region: str
```

````text
Google Vertex AI hosting via the `:rawPredict` family of endpoints.

Computes the URL from region/project, the dialect's `vendor` (the Vertex
*publisher*), and the model; reshapes the body via `_RawPredictEnvelope`. The
same `Vertex(...)` value hosts any dialect Vertex supports (Anthropic, Gemini,
Llama, …) — proof that hosting composes rather than multiplies. Authentication
is a separate Google OAuth/ADC `Credential`, not this host's concern.

Attributes:
    project: The Google Cloud project id.
    region: The Vertex region, e.g. `"us-east5"`; also selects the regional
        API host.
````

#### `Vertex.envelope` { #ocai-wire-hosting-vertex-envelope }

```python
def envelope(self, spec: EndpointSpec) -> EnvelopeTransform
```

````text
Return the trait-driven `:rawPredict` body reshape for `spec`.

Args:
    spec: The endpoint spec carrying the dialect traits.

Returns:
    A `_RawPredictEnvelope` configured for the dialect.
````

#### `Vertex.endpoint` { #ocai-wire-hosting-vertex-endpoint }

```python
def endpoint(self, spec: EndpointSpec) -> str
```

````text
Compute the Vertex `:rawPredict` URL for `spec`.

Args:
    spec: The endpoint spec carrying the dialect `vendor` (publisher),
        the target model in `resource`, and the operation kind/stream.

Returns:
    The fully-qualified Vertex prediction URL.
````

#### `Vertex.headers` { #ocai-wire-hosting-vertex-headers }

```python
def headers(self, spec: EndpointSpec) -> Mapping[str, str]
```

````text
Return explicit feature headers that the envelope does not relocate.

First-party version headers are not forwarded: Vertex injects its body
version. Explicit feature headers remain headers unless a trait declares
their relocation into the body. Legacy unclassified headers stay ignored.

Args:
    spec: The endpoint spec carrying feature declarations.

Returns:
    Explicit feature headers not relocated by the Vertex envelope.
````

## `ocai.wire.http`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/wire/http.py)

### `HttpRequest` { #ocai-wire-http-httprequest }

```python
class HttpRequest:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict[str, str])
    body: bytes | None = None
    stream: bool = False
    timeout: float | None = None
    ctx: CallContext | None = None
    attempt: int = 0
    admission: int = 0
```

````text
An outgoing HTTP request, already serialized to the wire.

Built by the drivers (`ocai.runtime.drivers`) from the host's endpoint,
envelope-wrapped body, and merged headers; judged by every
`WirePolicy.on_request` while still unauthenticated; then copied with independent headers for
`Credential.apply` at the driver leaf. Only this transport-only copy
acquires authentication; the original remains safe for retained references
and outcome hooks.

`body` is the encoded payload (or `None`). Build a JSON request with
`from_json`, which serializes the payload and sets `Content-Type`.
````

#### `HttpRequest.from_json` { #ocai-wire-http-httprequest-from-json }

```python
@classmethod
def from_json(cls, method: str, url: str, payload: dict[str, Any] | None, *, headers: dict[str, str] | None=None, stream: bool=False, timeout: float | None=None) -> HttpRequest
```

````text
Build a request whose body is `payload` JSON-encoded to bytes.

Args:
    method: The HTTP method.
    url: The fully-qualified URL.
    payload: The JSON body, or `None` for a bodiless request.
    headers: Initial headers; `Content-Type` is set when a body is
        present and not already given.
    stream: Whether the response will be consumed as a stream.
    timeout: An optional per-request timeout override in seconds.

Returns:
    The built request.
````

### `HttpResponse` { #ocai-wire-http-httpresponse }

```python
class HttpResponse:
    status: int
    headers: dict[str, str] = field(default_factory=dict[str, str])
    body: bytes = b''
```

````text
A fully-read HTTP response: status, headers, and the body bytes.

Returned by `Transport.send` / `SyncTransport.send_sync` on 2xx (non-2xx
raises the shared taxonomy instead, so policies branch on error types,
never on status codes). Rides `Outcome.response` through the on-outcome
hooks, may be synthesized by a `Return` decision (a wire-cache hit), and
pairs with its `HttpRequest` as the archived exchange record.
````

#### `HttpResponse.json` { #ocai-wire-http-httpresponse-json }

```python
def json(self) -> Any
```

````text
Parse the body as JSON (`None` for an empty body).

Returns:
    The decoded JSON value, or `None` when the body is empty.
````

### `DriverResponse` { #ocai-wire-http-driverresponse }

```python
class DriverResponse:
    payload: dict[str, Any]
    response: HttpResponse
```

````text
The final selected HTTP response and its legacy envelope-unwrapped payload.

Public driver execution evidence, detached after outcome policies select it.
No live connection or authenticated request is retained.
````

## `ocai.wire.outcomes`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/wire/outcomes.py)

### `preserve_error_evidence` { #ocai-wire-outcomes-preserve-error-evidence }

```python
def preserve_error_evidence(mapped: OcaiError, original: OcaiError) -> OcaiError
```

````text
Keep native response evidence independent from the new classification.
````

### `HostErrorMapper` { #ocai-wire-outcomes-hosterrormapper }

```python
class HostErrorMapper:
    name: str
    mapper: Callable[[OcaiError, dict[str, Any]], OcaiError | None]
    options: Mapping[str, Any] = field(default_factory=dict[str, Any])
```

````text
Declare a pure host error classifier with explicit, detached options.

The callback receives a copy of an ocai error containing native response
evidence. None declines to the existing dialect/coarse fallback. A returned
error claims classification; native evidence remains unchanged. Callbacks
must use declared options rather than hidden mutable state. They never
receive authenticated requests or SDK objects.
````

#### `HostErrorMapper.snapshot` { #ocai-wire-outcomes-hosterrormapper-snapshot }

```python
def snapshot(self) -> HostErrorMapper
```

````text
Detach declaration data while preserving callback ownership.
````

#### `HostErrorMapper.configuration_id` { #ocai-wire-outcomes-hosterrormapper-configuration-id }

```python
@property
def configuration_id(self) -> str
```

````text
Identify declared data and callback ownership for in-process approval.
````

#### `HostErrorMapper.apply` { #ocai-wire-outcomes-hosterrormapper-apply }

```python
def apply(self, error: OcaiError) -> OcaiError | None
```

````text
Classify HTTP evidence, fail closed on invalid/raising callbacks.

Connection failures have no HTTP status and are left to the existing
fallback. The original error and declaration cannot be mutated through
the callback. Callback exceptions are not chained or exposed as text.
````

### `HostAdaptation` { #ocai-wire-outcomes-hostadaptation }

```python
class HostAdaptation:
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict[str, Any])
    losses: tuple[FieldLoss, ...] = ()
    shifts: tuple[SemanticShift, ...] = ()
    error: OcaiError | None = None
```

````text
A pure unary host adapter's dialect payload, metadata and actual effects.
````

### `AdaptedHostResponse` { #ocai-wire-outcomes-adaptedhostresponse }

```python
class AdaptedHostResponse:
    payload: dict[str, Any]
    evidence: HostEvidence
    report: HostEffectReport
    violations: tuple[ContractViolation, ...] = ()
    error: OcaiError | None = None
```

````text
Validated adapter output with immutable attribution and census evidence.
````

### `HostResponseAdapter` { #ocai-wire-outcomes-hostresponseadapter }

```python
class HostResponseAdapter:
    host: str
    name: str
    adapter: Callable[[HttpResponse, dict[str, Any], dict[str, Any]], HostAdaptation]
    contract: HostEffectContract = field(default_factory=HostEffectContract)
    options: Mapping[str, Any] = field(default_factory=dict[str, Any])
```

````text
Explicit pure unary response adaptation; SDKs and requests stay outside.
````

#### `HostResponseAdapter.snapshot` { #ocai-wire-outcomes-hostresponseadapter-snapshot }

```python
def snapshot(self) -> HostResponseAdapter
```

````text
Detach data while retaining callable ownership.
````

#### `HostResponseAdapter.configuration_id` { #ocai-wire-outcomes-hostresponseadapter-configuration-id }

```python
@property
def configuration_id(self) -> str
```

````text
Identify declared configuration and in-process callable ownership.
````

#### `HostResponseAdapter.declaration` { #ocai-wire-outcomes-hostresponseadapter-declaration }

```python
@property
def declaration(self) -> HostEffectDeclaration
```

````text
Expose a detached declaration without claiming provider qualification.
````

#### `HostResponseAdapter.apply` { #ocai-wire-outcomes-hostresponseadapter-apply }

```python
def apply(self, response: HttpResponse, payload: dict[str, Any]) -> AdaptedHostResponse
```

````text
Adapt detached facts and retain native evidence, failing closed on misuse.
````

## `ocai.wire.policies`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/wire/policies.py)

### `RetryPolicy` { #ocai-wire-policies-retrypolicy }

```python
class RetryPolicy:
    attempts: int = 3
    base_delay: float = 0.1
```

````text
Retry transient failures with exponential backoff, as pure decisions.

The Decision-model rework of the old transport `RetryMiddleware`: instead
of looping around a send itself, it judges each `Outcome` and returns
`Retry(after=…)` — the driver executes the wait and re-attempts (with a
fresh request and freshly applied credential). It reacts only to
`TransientError` (the transport raises it for 5xx/429/connection
failures), honors a server-provided `retry_after` when present, and
otherwise backs off exponentially from `base_delay`.

The policy is **stateless**: backoff derives from `Outcome.attempt`, so
one frozen instance is safely shared across concurrent calls and both
drivers. Streams are not retried after the first byte — the drivers do
not run outcome-phase retries for streams, since a partially consumed
stream cannot be safely replayed.

Attributes:
    attempts: The maximum number of send attempts (including the first).
        Defaults to 3.
    base_delay: The base backoff delay in seconds, doubled per attempt
        when the server gives no `retry_after`. Defaults to 0.1.
````

#### `RetryPolicy.on_request` { #ocai-wire-policies-retrypolicy-on-request }

```python
def on_request(self, request: HttpRequest) -> Decision
```

````text
Admit every request — retry is purely an outcome concern.

Args:
    request: The outgoing (unauthenticated) wire request.

Returns:
    `Proceed`, always.
````

#### `RetryPolicy.on_outcome` { #ocai-wire-policies-retrypolicy-on-outcome }

```python
def on_outcome(self, outcome: Outcome) -> Decision
```

````text
Return `Retry` with the computed delay for a retryable failure.

Retries when the outcome carries a `TransientError` and attempts
remain, sleeping the server's `retry_after` when present, else
`base_delay * 2**attempt`. Anything else — success, a non-transient
error, or an exhausted budget — proceeds, letting the driver return
the response or raise the (refined) error.

Args:
    outcome: The attempt's result — response or refined error.

Returns:
    `Retry(after=…)` while budget remains for a transient failure,
    else `Proceed`.
````

### `RateLimitPolicy` { #ocai-wire-policies-ratelimitpolicy }

```python
class RateLimitPolicy
```

````text
Client-side rate limiting via `Retry`/`Fail` admission decisions [stub].

Will meter requests against a token bucket and defer admission with
`Retry(after=…)` (or veto with `Fail` when a deadline makes waiting
pointless). The bucket itself is an effectful *backend* declaring
`SyncBackend`/`AsyncBackend` faces — an in-process bucket for a single
node, a redis/distributed one for a fleet — so the decision stays pure
while the state lives wherever the deployment needs it.
````

#### `RateLimitPolicy.on_request` { #ocai-wire-policies-ratelimitpolicy-on-request }

```python
def on_request(self, request: HttpRequest) -> Decision
```

````text
Decide whether to admit, defer, or veto `request` against the budget.

Args:
    request: The outgoing (unauthenticated) wire request.

Returns:
    The admission decision.

Raises:
    NotImplementedError: Skeleton stub.
````

#### `RateLimitPolicy.on_outcome` { #ocai-wire-policies-ratelimitpolicy-on-outcome }

```python
def on_outcome(self, outcome: Outcome) -> Decision
```

````text
Feed provider rate signals back into the budget.

Args:
    outcome: The attempt's result — response or refined error.

Returns:
    `Proceed`, always (the limiter never overrides an outcome).

Raises:
    NotImplementedError: Skeleton stub.
````

### `WireTap` { #ocai-wire-policies-wiretap }

```python
class WireTap
```

````text
Post-redaction exchange capture feeding archive satellites [stub].

Records each attempt's `(HttpRequest, HttpResponse | error)` pair — the
audit-archive contract shape (`ocai.wire.http`) — and hands it to a
content-addressed archive sink (a future `ocai-archive-*` satellite).
Because every `WirePolicy` runs **before** `Credential.apply`, the
captured request is structurally guaranteed to be the unauthenticated,
post-redaction shape: a tap cannot leak a secret even by accident.

A tap observes and never steers: `on_request` always proceeds, and
`on_outcome` will capture-and-proceed once implemented.
````

#### `WireTap.on_request` { #ocai-wire-policies-wiretap-on-request }

```python
def on_request(self, request: HttpRequest) -> Decision
```

````text
Admit every request — a tap never vetoes.

Args:
    request: The outgoing (unauthenticated) wire request.

Returns:
    `Proceed`, always.
````

#### `WireTap.on_outcome` { #ocai-wire-policies-wiretap-on-outcome }

```python
def on_outcome(self, outcome: Outcome) -> Decision
```

````text
Capture the completed exchange, then proceed.

Args:
    outcome: The attempt's result — response or refined error.

Returns:
    `Proceed`, always (after capture).

Raises:
    NotImplementedError: Skeleton stub.
````

## `ocai.wire.sse`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/wire/sse.py)

### `SSEvent` { #ocai-wire-sse-ssevent }

```python
class SSEvent:
    data: dict[str, Any] | str
    event: str | None = None
    id: str | None = None
```

````text
A single Server-Sent Events frame.

Built by `SSEParser` from the wire (`data` is then the raw payload
string), and re-serializable back to the `event:`/`data:` wire format
(used by recorded-fixture tooling). Decoding the payload (typically JSON)
into a canonical `ChatChunk` is the codec's job, so this stays
provider-neutral.

Attributes:
    data: The event payload — the raw `data:` string as parsed from the
        wire, or a dict when an event is constructed for serialization.
    event: The optional SSE event name (the `event:` line), when present.
    id: The optional SSE event id (the `id:` line), when present.
````

#### `SSEvent.serialize` { #ocai-wire-sse-ssevent-serialize }

```python
def serialize(self, encoder: Callable[[dict[str, Any]], str]=json.dumps) -> str
```

````text
Render the event to the SSE wire format.

Emits an `event:` line and an `id:` line when set, followed by a
`data:` line terminated by a blank line. Dict payloads are encoded via
`encoder`; string payloads are written as-is.

Args:
    encoder: Callable used to encode a dict `data` payload to a
        string; defaults to `json.dumps`.

Returns:
    The SSE-formatted text for this event.
````

### `SSEParser` { #ocai-wire-sse-sseparser }

```python
class SSEParser
```

````text
Incremental Server-Sent-Events parser, safe across network chunk splits.

A **pure** SSE wire parser: feed raw bytes as they arrive, get back
completed `SSEvent` frames. It handles:

- **chunk boundaries** — a line split across two `feed` calls is buffered
  until its terminating newline arrives;
- **comment / keep-alive lines** — lines beginning with `:` are ignored;
- **multi-line data** — consecutive `data:` lines in one event are joined
  with `\\n` per the SSE spec;
- **the `event:` / `id:` lines** — captured onto the emitted `SSEvent`.

It deliberately knows **nothing about end-of-stream**: a provider's
terminal signal — OpenAI's `[DONE]` data sentinel, Anthropic's
`message_stop` event — is a *dialect* concern, so it is emitted as an
ordinary `SSEvent` and recognized by the codec's `decode_event`, never
special-cased here. Likewise the `data` payload is left as a raw string;
JSON decoding is the codec's job. That keeps this parser provider-neutral.
````

#### `SSEParser.__init__` { #ocai-wire-sse-sseparser---init-- }

```python
def __init__(self) -> None
```

````text
Construct a parser with empty buffers.
````

#### `SSEParser.feed` { #ocai-wire-sse-sseparser-feed }

```python
def feed(self, chunk: bytes | str) -> list[SSEvent]
```

````text
Consume a chunk; return any `SSEvent` frames completed by it.

Args:
    chunk: The next raw slice of the response body, as delivered by
        the transport (any split point is safe).

Returns:
    The frames whose terminating blank line arrived within `chunk`.
````

## `ocai.wire.transport`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/wire/transport.py)

### `Transport` { #ocai-wire-transport-transport }

```python
class Transport(Protocol)
```

````text
The async HTTP send port — the boundary `AsyncDriver` sends through.

A `Transport` turns an `HttpRequest` into an `HttpResponse`. It is
**provider- and capability-neutral** — chat, embeddings, and vector
facades all send through one — and **client-agnostic**: the httpx
implementation (`HttpxTransport`) is one concrete leaf; a fake transport
for tests is just a class returning canned `HttpResponse`s (rule 10).

This is the **async** port; the synchronous call path is the separate
`SyncTransport` port. The split is deliberate: async-ness is confined to
the one network call, so nothing above the transport is duplicated
between the sync and async pipelines. Its `aclose` doubles as the
`AsyncBackend` face anchor, so `Binding.validate` admits it for async
mode by the same structural rule as any policy backend.

`send` raises the shared taxonomy (`ocai.core.errors`) on a non-success
status and returns only on 2xx, so retry policies branch on
`TransientError` rather than re-reading status codes.
````

#### `Transport.send` { #ocai-wire-transport-transport-send }

```python
async def send(self, request: HttpRequest) -> HttpResponse
```

````text
Send `request`; return the response, or raise the error taxonomy.

Args:
    request: The authenticated, fully-built wire request.

Returns:
    The detached 2xx response snapshot.

Raises:
    OcaiError: The coarse taxonomy classification of any non-2xx
        status or connection failure.
````

#### `Transport.stream` { #ocai-wire-transport-transport-stream }

```python
def stream(self, request: HttpRequest) -> AsyncIterator[bytes]
```

````text
Stream the response body as raw byte chunks (framing is above).

Args:
    request: The authenticated, fully-built wire request.

Returns:
    An async iterator of raw body chunks; the driver pumps them into
    the host-selected sans-io stream decoder.
````

#### `Transport.aclose` { #ocai-wire-transport-transport-aclose }

```python
async def aclose(self) -> None
```

````text
Release any underlying connection resources.
````

### `SyncTransport` { #ocai-wire-transport-synctransport }

```python
class SyncTransport(Protocol)
```

````text
The synchronous twin of `Transport` — what `SyncDriver` sends through.

Same contract as `Transport` — turn an `HttpRequest` into an
`HttpResponse`, raising the shared taxonomy on non-2xx — but blocking, so
a caller that is not in an event loop (a script, a notebook cell, a sync
web handler) needs no `asyncio.run`. The method names are distinct from
the async port (`send_sync`/`stream_sync`/`close`) so one class can
implement **both** ports without name collisions; everything above the
transport is shared between the two pipelines. `close` doubles as the
`SyncBackend` face anchor for composition-time validation.
````

#### `SyncTransport.send_sync` { #ocai-wire-transport-synctransport-send-sync }

```python
def send_sync(self, request: HttpRequest) -> HttpResponse
```

````text
Send `request` synchronously; return the response, or raise the taxonomy.

Args:
    request: The authenticated, fully-built wire request.

Returns:
    The detached 2xx response snapshot.

Raises:
    OcaiError: The coarse taxonomy classification of any non-2xx
        status or connection failure.
````

#### `SyncTransport.stream_sync` { #ocai-wire-transport-synctransport-stream-sync }

```python
def stream_sync(self, request: HttpRequest) -> Iterator[bytes]
```

````text
Stream the response body as raw byte chunks, synchronously.

Args:
    request: The authenticated, fully-built wire request.

Returns:
    An iterator of raw body chunks; the driver pumps them into the
    host-selected sans-io stream decoder.
````

#### `SyncTransport.close` { #ocai-wire-transport-synctransport-close }

```python
def close(self) -> None
```

````text
Release any underlying connection resources.
````

### `HttpxTransport` { #ocai-wire-transport-httpxtransport }

```python
class HttpxTransport
```

````text
The concrete httpx leaf implementing **both** transport ports.

Implements `Transport` (async: `send`/`stream`/`aclose`) and
`SyncTransport` (sync: `send_sync`/`stream_sync`/`close`), so a single
instance serves both drivers. The two underlying httpx clients
(`AsyncClient`, `Client`) are created **lazily** on first use, so a
purely-sync program never spins up an async client (and never binds an
event loop) and vice versa.

Owns timeout + connection-pool config. Does a single send (no
retry/replay — compose a `RetryPolicy` for that) and maps non-success
responses onto the shared taxonomy. Deals only in `HttpRequest` /
`HttpResponse`; httpx never leaks past this class.
````

#### `HttpxTransport.__init__` { #ocai-wire-transport-httpxtransport---init-- }

```python
def __init__(self, *, timeout: float=60.0, max_connections: int=100, provider: str | None=None) -> None
```

````text
Configure the transport; httpx clients are created lazily on first use.

`httpx` is imported lazily (per call) so that importing `ocai.wire`
never requires httpx to be installed (it ships behind the `[http]`
extra).

Args:
    timeout: The request timeout in seconds applied to the client.
        Defaults to 60.0.
    max_connections: The maximum number of pooled connections.
        Defaults to 100.
    provider: An optional provider name stamped onto raised errors for
        context.
````

#### `HttpxTransport.aclose` { #ocai-wire-transport-httpxtransport-aclose }

```python
async def aclose(self) -> None
```

````text
Close the async httpx client, if one was created.
````

#### `HttpxTransport.close` { #ocai-wire-transport-httpxtransport-close }

```python
def close(self) -> None
```

````text
Close the sync httpx client, if one was created.
````

#### `HttpxTransport.send` { #ocai-wire-transport-httpxtransport-send }

```python
async def send(self, request: HttpRequest) -> HttpResponse
```

````text
Send `request` once (async); return the response or raise the taxonomy.

Args:
    request: The authenticated wire request.

Returns:
    The detached 2xx response snapshot.

Raises:
    TransientError: On connect/read/timeout failures.
    OcaiError: The taxonomy classification of a non-2xx status.
````

#### `HttpxTransport.send_sync` { #ocai-wire-transport-httpxtransport-send-sync }

```python
def send_sync(self, request: HttpRequest) -> HttpResponse
```

````text
Send `request` once (sync); return the response or raise the taxonomy.

Args:
    request: The authenticated wire request.

Returns:
    The detached 2xx response snapshot.

Raises:
    TransientError: On connect/read/timeout failures.
    OcaiError: The taxonomy classification of a non-2xx status.
````

#### `HttpxTransport.stream` { #ocai-wire-transport-httpxtransport-stream }

```python
async def stream(self, request: HttpRequest) -> AsyncIterator[bytes]
```

````text
Stream the response body as raw byte chunks, async (framing is above).

No retry: a partially consumed stream can't be safely replayed, which
is also why the drivers ignore outcome-phase `Retry` decisions for
streams.

Args:
    request: The authenticated wire request.

Yields:
    Raw body chunks as they arrive.

Raises:
    TransientError: On connect/read/timeout failures — at open or
        mid-stream (a wire that dies mid-body maps to the taxonomy
        like any other wire failure, rule 8).
    OcaiError: The taxonomy classification of a non-2xx status.
````

#### `HttpxTransport.stream_sync` { #ocai-wire-transport-httpxtransport-stream-sync }

```python
def stream_sync(self, request: HttpRequest) -> Iterator[bytes]
```

````text
Stream the response body as raw byte chunks, synchronously.

Args:
    request: The authenticated wire request.

Yields:
    Raw body chunks as they arrive.

Raises:
    TransientError: On connect/read/timeout failures — at open or
        mid-stream (a wire that dies mid-body maps to the taxonomy
        like any other wire failure, rule 8).
    OcaiError: The taxonomy classification of a non-2xx status.
````
