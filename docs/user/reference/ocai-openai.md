# `ocai.openai` API reference

Generated from the checked-out package sources. Signatures, declared fields,
methods, type aliases and explicit re-exports are checked for drift. Inherited
members follow their named base class; a type's presence does not establish
provider execution support. See [supported features](../provider-feature-matrix.md).

## `ocai.openai`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-openai/src/ocai/openai/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-openai-chat-completions"></span>`chat_completions` | [`ocai.openai.chat_completions`](ocai-openai.md#ocai-openai-chat-completions) |
| <span id="ocai-openai-responses"></span>`responses` | [`ocai.openai.responses`](ocai-openai.md#ocai-openai-responses) |
| <span id="ocai-openai-chat-model"></span>`chat_model` | [`ocai.openai.chat_completions.chat_model`](ocai-openai.md#ocai-openai-chat-completions-chat-model) |

### `FRAGMENT` { #ocai-openai-fragment }

```python
FRAGMENT  # See source for the full declaration.
```

## `ocai.openai.chat_completions`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-openai/src/ocai/openai/chat_completions/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-openai-chat-completions-chat-completions-chunk"></span>`CHAT_COMPLETIONS_CHUNK` | [`ocai.openai.chat_completions.codec.CHAT_COMPLETIONS_CHUNK`](ocai-openai.md#ocai-openai-chat-completions-codec-chat-completions-chunk) |
| <span id="ocai-openai-chat-completions-chat-completions-request"></span>`CHAT_COMPLETIONS_REQUEST` | [`ocai.openai.chat_completions.codec.CHAT_COMPLETIONS_REQUEST`](ocai-openai.md#ocai-openai-chat-completions-codec-chat-completions-request) |
| <span id="ocai-openai-chat-completions-chat-completions-response"></span>`CHAT_COMPLETIONS_RESPONSE` | [`ocai.openai.chat_completions.codec.CHAT_COMPLETIONS_RESPONSE`](ocai-openai.md#ocai-openai-chat-completions-codec-chat-completions-response) |
| <span id="ocai-openai-chat-completions-chatcompletionscodec"></span>`ChatCompletionsCodec` | [`ocai.openai.chat_completions.codec.ChatCompletionsCodec`](ocai-openai.md#ocai-openai-chat-completions-codec-chatcompletionscodec) |

### `FRAGMENT` { #ocai-openai-chat-completions-fragment }

```python
FRAGMENT = CatalogFragment(origin=ORIGIN, nodes=NODES, edges=EDGES, transducers=TRANSDUCERS, profiles=PROFILES, traits=(dialect_traits(),), components=(Component(provider=ChatCompletionsCodec.provider, interface=ChatCompletionsCodec.interface, capability=CHAT, factory=ChatCompletionsCodec),))
```

### `chat_model` { #ocai-openai-chat-completions-chat-model }

```python
def chat_model(model_name: str, *, credentials: Credential) -> ChatModel
```

````text
Sanctioned sugar (§3.4 door 2): a first-party OpenAI chat model.

A THIN wrapper over the exact same fragment + facade machinery as the
core string door — never a separate code path: it *is* a call to
`ocai.chat.model(f"openai/{model_name}", ...)` over a minimal catalog
built from this interface's `FRAGMENT` (so the front door composes a
`Direct` host at the OpenAI origin from the fragment's declared traits,
the `ChatCompletionsCodec` from the fragment's component factory, and an
`HttpxTransport`). The model name binds to the returned model object
here, at construction; `ChatRequest`s stay pure conversation and never
carry it. Power users compose the pieces themselves (any host, any
transport, richer catalogs); this factory adds nothing they cannot
reach.

Args:
    model_name: The OpenAI model name bound to the returned model
        object (the facade's `EndpointSpec.resource`).
    credentials: The credential applied per request at the driver leaf.
        Required — there is no ambient discovery (rule 13).

Returns:
    A `ChatModel` implementation backed by this interface.
````

## `ocai.openai.chat_completions.client`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-openai/src/ocai/openai/chat_completions/client.py)

### `ClientMetadata` { #ocai-openai-chat-completions-client-clientmetadata }

```python
class ClientMetadata:
    id: str
    model: str
    created: int
```

````text
Explicit gateway serving identity, never invented provider provenance.
````

#### `ClientMetadata.bind` { #ocai-openai-chat-completions-client-clientmetadata-bind }

```python
def bind(self, payload: dict[str, Any]) -> dict[str, Any]
```

````text
Bind serving metadata to a detached response or chunk document.
````

### `part_evidence` { #ocai-openai-chat-completions-client-part-evidence }

```python
def part_evidence(part: Part, path: str, losses: list[FieldLoss], *, streaming: bool=False) -> None
```

````text
Report part metadata with no client lane, including scoped anchors.
````

### `client_finish` { #ocai-openai-chat-completions-client-client-finish }

```python
def client_finish(finish: FinishInfo | None, losses: list[FieldLoss]) -> str | None
```

````text
Map finish semantics while retaining unknown native values with findings.
````

### `client_usage` { #ocai-openai-chat-completions-client-client-usage }

```python
def client_usage(usage: Usage | None, losses: list[FieldLoss]) -> dict[str, Any] | None
```

````text
Invert disjoint token buckets without inventing missing measurements.
````

### `encode_response` { #ocai-openai-chat-completions-client-encode-response }

```python
def encode_response(response: ChatResponse) -> EdgeOutput
```

````text
Convert canonical response semantics; callers explicitly bind serving metadata.
````

## `ocai.openai.chat_completions.client_stream`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-openai/src/ocai/openai/chat_completions/client_stream.py)

### `ClientStreamTransducer` { #ocai-openai-chat-completions-client-stream-clientstreamtransducer }

```python
class ClientStreamTransducer
```

````text
Map events without buffering response text or tool arguments.

Only part identities, rolling checksums, finish and usage remain in memory.
Successful finish/usage frames require a canonical StreamEnd. Flush on abort
produces evidence but no completion. The gateway emits its DONE framing only
after it has accepted the conversion report and upstream terminal outcome.
````

#### `ClientStreamTransducer.__init__` { #ocai-openai-chat-completions-client-stream-clientstreamtransducer---init-- }

```python
def __init__(self) -> None
```

````text
Start a fresh isolated client conversion.
````

#### `ClientStreamTransducer.feed` { #ocai-openai-chat-completions-client-stream-clientstreamtransducer-feed }

```python
def feed(self, event: Any) -> list[dict[str, Any]]
```

````text
Convert one canonical chunk into zero or more client JSON events.
````

#### `ClientStreamTransducer.flush` { #ocai-openai-chat-completions-client-stream-clientstreamtransducer-flush }

```python
def flush(self) -> tuple[list[dict[str, Any]], EdgeReport]
```

````text
Finalize evidence exactly once, never synthesize a successful terminal.
````

## `ocai.openai.chat_completions.codec`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-openai/src/ocai/openai/chat_completions/codec.py)

### `PROVIDER` { #ocai-openai-chat-completions-codec-provider }

```python
PROVIDER = 'openai'
```

### `INTERFACE` { #ocai-openai-chat-completions-codec-interface }

```python
INTERFACE = 'chat_completions'
```

### `TAG` { #ocai-openai-chat-completions-codec-tag }

```python
TAG = '2023-11'
```

### `OPENAI_BASE_URL` { #ocai-openai-chat-completions-codec-openai-base-url }

```python
OPENAI_BASE_URL = 'https://api.openai.com'
```

### `CHAT_COMPLETIONS_PATH` { #ocai-openai-chat-completions-codec-chat-completions-path }

```python
CHAT_COMPLETIONS_PATH = '/v1/chat/completions'
```

### `CHAT_COMPLETIONS_REQUEST` { #ocai-openai-chat-completions-codec-chat-completions-request }

```python
CHAT_COMPLETIONS_REQUEST = NodeId(provider=PROVIDER, interface=INTERFACE, tag=TAG, shape=CHAT_REQUEST, released=_RELEASED, status=Status.STABLE)
```

### `CHAT_COMPLETIONS_RESPONSE` { #ocai-openai-chat-completions-codec-chat-completions-response }

```python
CHAT_COMPLETIONS_RESPONSE = NodeId(provider=PROVIDER, interface=INTERFACE, tag=TAG, shape=CHAT_RESPONSE, released=_RELEASED, status=Status.STABLE)
```

### `CHAT_COMPLETIONS_CHUNK` { #ocai-openai-chat-completions-codec-chat-completions-chunk }

```python
CHAT_COMPLETIONS_CHUNK = NodeId(provider=PROVIDER, interface=INTERFACE, tag=TAG, shape=CHAT_CHUNK, released=_RELEASED, status=Status.STABLE)
```

### `CANONICAL_REQUEST` { #ocai-openai-chat-completions-codec-canonical-request }

```python
CANONICAL_REQUEST = canonical_node(CHAT_REQUEST)
```

### `CANONICAL_RESPONSE` { #ocai-openai-chat-completions-codec-canonical-response }

```python
CANONICAL_RESPONSE = canonical_node(CHAT_RESPONSE)
```

### `CANONICAL_CHUNK` { #ocai-openai-chat-completions-codec-canonical-chunk }

```python
CANONICAL_CHUNK = canonical_node(CHAT_CHUNK)
```

### `dialect_traits` { #ocai-openai-chat-completions-codec-dialect-traits }

```python
def dialect_traits() -> DialectTraits
```

````text
Build the hosting traits the wire layer composes for this interface.

OpenAI first-party auth is a plain `Bearer` token with no extra headers or
body fields, so the traits carry the vendor tag plus the first-party
origin (`OPENAI_BASE_URL`, riding the fragment so the §3.4 front door can
compose a `Direct` binding without importing this plugin). Consumed by
`ocai.wire.hosting` hosts (`Direct`/`Custom`) at composition time.

Returns:
    The interface's `DialectTraits`.
````

### `ChatCompletionsCodec` { #ocai-openai-chat-completions-codec-chatcompletionscodec }

```python
class ChatCompletionsCodec:
    provider = PROVIDER
    interface = INTERFACE
    request_node = CHAT_COMPLETIONS_REQUEST
    response_node = CHAT_COMPLETIONS_RESPONSE
    chunk_node = CHAT_COMPLETIONS_CHUNK
```

````text
The `openai/chat_completions` dialect codec — pure mapping, no I/O.

The conversion half the edge definitions wrap into graph `Edge`s
(encode/decode) and the error/endpoint half the driver consults
(`map_error`/`native_path`). Stateless and cheap to construct; the module
functions in `edges.py` share one instance.

Every conversion method returns an `EdgeOutput(value, losses, shifts)` so the graph
can accumulate a `FidelityReport` — the codec never silences a field it
cannot map (rule 5).
````

#### `ChatCompletionsCodec.__init__` { #ocai-openai-chat-completions-codec-chatcompletionscodec---init-- }

```python
def __init__(self, variant: ChatCompletionsVariant | None=None) -> None
```

````text
Configure compatible field lanes; each variant earns its own conformance.
````

#### `ChatCompletionsCodec.native_path` { #ocai-openai-chat-completions-codec-chatcompletionscodec-native-path }

```python
def native_path(self, model: str) -> str
```

````text
Return the first-party endpoint path for a chat call.

Args:
    model: The target model name (unused; the model travels in the
        request body on this interface).

Returns:
    The chat-completions path, joined to a host origin by the wire
    layer's endpoint resolution.
````

#### `ChatCompletionsCodec.dialect_traits` { #ocai-openai-chat-completions-codec-chatcompletionscodec-dialect-traits }

```python
def dialect_traits(self) -> DialectTraits
```

````text
Return this interface's hosting traits (the module `dialect_traits`).

The codec-attached face of the facade seam (WU-07): `WireChatModel`
builds each call's `EndpointSpec.traits` from the codec it was
composed with, so the wire layer reads the dialect's hosting facts
as data without the facade ever reaching into plugin modules.

Returns:
    The interface's `DialectTraits`.
````

#### `ChatCompletionsCodec.bind_resource` { #ocai-openai-chat-completions-codec-chatcompletionscodec-bind-resource }

```python
def bind_resource(self, payload: dict[str, Any], resource: str) -> dict[str, Any]
```

````text
Inject the bound model name as this wire's `model` member.

The facade half of the WU-05a seam: the canonical `ChatRequest`
carries no model (routing data binds to the model object, §3.4) and
the graph edges stay model-agnostic, so `encode_request` emits no
`model` key. `WireChatModel` calls this after graph conversion —
with `EndpointSpec.resource`, before the driver send — and only the
codec knows where its dialect carries the name (here: the `model`
body member; a hosting envelope may still relocate or strip it, e.g.
Vertex lifts it into the URL).

Args:
    payload: The encoded wire request body, without a model member.
    resource: The bound model name from `EndpointSpec.resource`.

Returns:
    A new payload dict with the `model` member set; the input is
    not mutated.
````

#### `ChatCompletionsCodec.bind_stream` { #ocai-openai-chat-completions-codec-chatcompletionscodec-bind-stream }

```python
def bind_stream(self, payload: dict[str, Any]) -> dict[str, Any]
```

````text
Mark an encoded wire payload as a streaming request.

The streaming half of the bind seam (WU-11): how a dialect asks for
a stream is wire hygiene, not conversation, so graph edges never
emit it — the facade calls this after `bind_resource` when serving
`stream`/`astream`. On this wire that means `stream: true` plus
`stream_options.include_usage` **defaulted on**, so every stream
ends with the authoritative usage the terminal `StreamEnd` promises
(M2 honesty parity) — a caller's own `stream_options` (via the
`provider_options` lane) is respected untouched.

Args:
    payload: The encoded wire request body, model already bound.

Returns:
    A new payload dict with the streaming members set; the input is
    not mutated.
````

#### `ChatCompletionsCodec.encode_request` { #ocai-openai-chat-completions-codec-chatcompletionscodec-encode-request }

```python
def encode_request(self, request: ChatRequest) -> EdgeOutput
```

````text
Encode a canonical `ChatRequest` into a chat-completions body.

The `canonical chat.request → openai/chat_completions` edge function.
Messages are flattened part-by-part (tool results become sibling
`role: tool` wire messages — a structural relocation recorded as a
`SemanticShift`), config knobs map per the edge contract's census, and
only this interface's own `provider_options` namespace
(`"openai.chat_completions"`) is expanded onto the payload — foreign
namespaces are never forwarded (three-lane law, §3.4).

The emitted body has **no `model` member**: the canonical request
carries none (§3.4 — routing data binds to the model object), so
there is nothing to lose or report here; the facade injects the
bound resource via `bind_resource` before send.

Args:
    request: The canonical request to encode.

Returns:
    An `EdgeOutput` with the wire request dict and this edge's records.
````

#### `ChatCompletionsCodec.decode_request` { #ocai-openai-chat-completions-codec-chatcompletionscodec-decode-request }

```python
def decode_request(self, payload: dict[str, Any]) -> EdgeOutput
```

````text
Decode a chat-completions request body into a `ChatRequest`.

The `openai/chat_completions → canonical chat.request` edge function
— the audit direction: re-converting archived wire traffic back into
the canonical IR with no ability to make network calls (§1), and the
first hop of every cross-provider request conversion (WU-15). The
inverse of `encode_request`, with one deliberate asymmetry: the wire
`model` member is **routing data, not canonical content** (§3.4 — a
`ChatRequest` never carries a model), so its echo is preserved
recoverably as the provider-scoped model extension with an `EXTENSIONS`
record; re-encoding toward any interface binds a fresh resource at
the front door. Sibling `role: tool` wire messages re-thread as
canonical tool turns (the inverse relocation, declared), and unknown
envelope keys sweep into `extensions` — total decode, never a raise
(rule 6).

Args:
    payload: The raw archived request body, already JSON-parsed.

Returns:
    An `EdgeOutput` with the canonical `ChatRequest` and this
    edge's records.
````

#### `ChatCompletionsCodec.decode_response` { #ocai-openai-chat-completions-codec-chatcompletionscodec-decode-response }

```python
def decode_response(self, payload: dict[str, Any]) -> EdgeOutput
```

````text
Decode a chat-completions response body into a `ChatResponse`.

The `openai/chat_completions → canonical chat.response` edge function.
The honesty upgrades over the old adapter: `tool_calls` become typed
`PartToolCall`s, `refusal` becomes `PartRefusal`, `finish_reason`
becomes a `FinishInfo` with the verbatim native lane, `choices[1:]`
land in the censused `openai.choices` extension with reported loss
(single message forever, §3.1), and unknown envelope keys sweep into
`extensions` — this decoder never raises on unknown input (rule 6).

Args:
    payload: The raw response body, already JSON-parsed.

Returns:
    An `EdgeOutput` with the canonical `ChatResponse` and this
    edge's records.
````

#### `ChatCompletionsCodec.decode_event` { #ocai-openai-chat-completions-codec-chatcompletionscodec-decode-event }

```python
def decode_event(self, event: str | None, data: str) -> ChatChunk | None
```

````text
Decode one chat-completions SSE frame into its first canonical chunk.

The single-chunk face of the frame decoder — the shape the facade's
`ChatCodec` protocol declares. Most chat-completions frames carry
exactly one signal, and this returns it; a multi-signal frame
(role+content, id+arguments, several `tool_calls` entries) surfaces
only its *first* chunk here — `decode_frame` is the total, ordered
decoder the `ChatCompletionsStreamTransducer` consumes on the
streaming path. The `[DONE]` sentinel returns `None`; the transducer
emits the terminal `STREAM_STOP`/`StreamEnd`.

Args:
    event: The SSE `event:` field, if the frame carried one (OpenAI
        does not use named events on this interface).
    data: The SSE `data:` payload.

Returns:
    The frame's first canonical chunk, or `None` when the frame
    surfaces nothing.
````

#### `ChatCompletionsCodec.decode_frame` { #ocai-openai-chat-completions-codec-chatcompletionscodec-decode-frame }

```python
def decode_frame(self, event: str | None, data: str) -> EdgeOutput
```

````text
Decode one chat-completions SSE frame into its ordered chunks.

The total per-frame half of the chunk-shape `StreamEdge`; the
sans-io SSE field parsing itself lives in `ocai.wire.sse` and hands
this method the frame's `event` name and `data` payload, so the
plugin never touches a socket. One wire frame may carry several
signals, and each becomes its own chunk, in wire order: the opening
`role` becomes `STREAM_START`, a `content` fragment
`PART_DELTA(DeltaText)`, a `refusal` fragment
`PART_DELTA(DeltaRefusal)`, each `tool_calls` entry a `PART_START`
(id frames, carrying the `PartToolCall` skeleton) and/or a
`PART_DELTA(DeltaToolArgs)` (raw string fragments, parsed once at
PART_STOP), a `finish_reason` a `FINISH` chunk with a typed
`FinishInfo`, and a `usage` object a cumulative `USAGE` chunk. The
`[DONE]` sentinel surfaces nothing — the transducer owns the
terminal contract.

Part slots follow the stateless `_TEXT_SLOT`/`_TOOL_SLOT_OFFSET`
mapping, reproducing the unary decoder's part order so a stream's
fold matches the blocking decode structurally.

Single message forever (§3.1): only the choice at index 0 is
decoded. A frame interleaving foreign choices (`n > 1`) drops them
with a reported `FieldLoss` — the frames stay recoverable verbatim
on the surfaced chunks' `raw_event` lane — mirroring the unary
edge's `choices[1:]` census.

Args:
    event: The SSE `event:` field, if the frame carried one (OpenAI
        does not use named events on this interface).
    data: The SSE `data:` payload.

Returns:
    An `EdgeOutput` whose value is the frame's canonical chunks, in
    order (possibly empty), with any dropped-choice records.
````

#### `ChatCompletionsCodec.map_error` { #ocai-openai-chat-completions-codec-chatcompletionscodec-map-error }

```python
def map_error(self, status: int | None, body: dict[str, Any] | None) -> OcaiError | None
```

````text
Refine an OpenAI error body onto the precise error taxonomy.

OpenAI returns `{"error": {"type", "code", "message"}}` on every
endpoint, and the precise meaning lives in `code`/`type`, not the HTTP
status (a context-length overflow is a 400, not a 413). The driver
applies this refinement on top of the wire layer's neutral
status-based mapping; returning `None` defers to that coarse error.

Args:
    status: The HTTP status of the failed response, if known.
    body: The parsed OpenAI error body, if any.

Returns:
    A precise `OcaiError`, or `None` to defer to the neutral mapping.
````

### `ChatCompletionsStreamTransducer` { #ocai-openai-chat-completions-codec-chatcompletionsstreamtransducer }

```python
class ChatCompletionsStreamTransducer
```

````text
Streaming transducer: chat-completions SSE frames → canonical chunks.

The stateful per-stream object a chunk-shape `StreamEdge` manufactures
(one per stream — transducers are never shared). `feed` maps each wire
frame through `ChatCompletionsCodec.decode_frame` (one frame may split
into several canonical chunks, in order), stamps monotonic `seq`
numbers, and adds the statefulness a well-formed canonical stream needs
on this dialect:

- **Part boundaries.** The wire opens tool-call parts explicitly (the
  id frame) but never text/refusal parts, so the first delta into an
  unopened slot is preceded by a synthesized `PART_START` carrying the
  matching skeleton — every delta-fed slot starts with its skeleton
  before its first delta.
- **The terminal contract.** When the `[DONE]` sentinel arrives, the
  still-open tool-call slots are sealed (`PART_STOP`, advancing them to
  `input_complete` in the fold) and the terminal `STREAM_STOP` is
  emitted carrying `StreamEnd(usage, finish)` — usage from the
  `stream_options` final chunk when present, finish from the
  accumulated `finish_reason`. A stream that dies before `[DONE]` gets
  **no** terminal chunk: synthesizing one would pass accumulated
  content off as complete, and the accumulator's aborted-stream sealing
  (`extensions["ocai.incomplete"]`) is the honest downstream.

`flush` hands the graph this edge's `EdgeReport` (dropped foreign
choices under §3.1's single-message rule) so streaming conversion pays
the same visible toll as non-streaming (§4.1).
````

#### `ChatCompletionsStreamTransducer.__init__` { #ocai-openai-chat-completions-codec-chatcompletionsstreamtransducer---init-- }

```python
def __init__(self, codec: ChatCompletionsCodec | None=None) -> None
```

````text
Initialize per-stream state (codec, sequence counter, slots, records).
````

#### `ChatCompletionsStreamTransducer.feed` { #ocai-openai-chat-completions-codec-chatcompletionsstreamtransducer-feed }

```python
def feed(self, event: Any) -> list[ChatChunk]
```

````text
Convert one wire SSE event into zero or more canonical chunks.

Args:
    event: The sans-io SSE event (duck-typed: `event`/`data`
        attributes) produced by the wire layer's `SSEParser`.

Returns:
    The canonical chunks this frame surfaced, `seq`-stamped, in
    order — including any synthesized part boundary and, on the
    `[DONE]` sentinel, the terminal chunks.
````

#### `ChatCompletionsStreamTransducer.flush` { #ocai-openai-chat-completions-codec-chatcompletionsstreamtransducer-flush }

```python
def flush(self) -> tuple[list[ChatChunk], EdgeReport]
```

````text
Seal the stream's accounting and report this edge's fidelity.

The terminal `STREAM_STOP` is emitted by `feed` when `[DONE]`
arrives, so the tail here is always empty: a stream that never
reached its sentinel was aborted, and synthesizing a terminal for
it would pass accumulated content off as complete — the
accumulator's aborted-stream sealing owns that case.

Returns:
    An empty tail and the edge's `EdgeReport` of accumulated
    losses (dropped foreign choices).
````

## `ocai.openai.chat_completions.edges`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-openai/src/ocai/openai/chat_completions/edges.py)

### `ORIGIN` { #ocai-openai-chat-completions-edges-origin }

```python
ORIGIN = Origin(distribution='ocai-openai', version='0.1.0')
```

### `ENCODE_REQUEST_CONTRACT` { #ocai-openai-chat-completions-edges-encode-request-contract }

```python
ENCODE_REQUEST_CONTRACT  # See source for the full declaration.
```

### `DECODE_RESPONSE_CONTRACT` { #ocai-openai-chat-completions-edges-decode-response-contract }

```python
DECODE_RESPONSE_CONTRACT  # See source for the full declaration.
```

### `DECODE_REQUEST_CONTRACT` { #ocai-openai-chat-completions-edges-decode-request-contract }

```python
DECODE_REQUEST_CONTRACT  # See source for the full declaration.
```

### `DECODE_CHUNK_CONTRACT` { #ocai-openai-chat-completions-edges-decode-chunk-contract }

```python
DECODE_CHUNK_CONTRACT  # See source for the full declaration.
```

### `ENCODE_RESPONSE_CONTRACT` { #ocai-openai-chat-completions-edges-encode-response-contract }

```python
ENCODE_RESPONSE_CONTRACT  # See source for the full declaration.
```

### `ENCODE_CHUNK_CONTRACT` { #ocai-openai-chat-completions-edges-encode-chunk-contract }

```python
ENCODE_CHUNK_CONTRACT  # See source for the full declaration.
```

### `encode_request` { #ocai-openai-chat-completions-edges-encode-request }

```python
def encode_request(request: ChatRequest) -> EdgeOutput
```

````text
Edge fn `canonical chat.request → openai/chat_completions`.

Args:
    request: The canonical request the planner routed to this edge.

Returns:
    The wire request dict with this edge's report.
````

### `decode_response` { #ocai-openai-chat-completions-edges-decode-response }

```python
def decode_response(payload: dict[str, Any]) -> EdgeOutput
```

````text
Edge fn `openai/chat_completions → canonical chat.response`.

Args:
    payload: The raw response body, already JSON-parsed.

Returns:
    The canonical `ChatResponse` with this edge's report.
````

### `decode_request` { #ocai-openai-chat-completions-edges-decode-request }

```python
def decode_request(payload: dict[str, Any]) -> EdgeOutput
```

````text
Edge fn `openai/chat_completions → canonical chat.request`.

The audit-tool direction: re-converting archived wire traffic back into
the canonical IR without any ability to make network calls (§1), and the
first hop of every cross-provider request conversion (WU-15).

Args:
    payload: The raw archived request body.

Returns:
    The canonical `ChatRequest` with this edge's report.
````

### `NODES` { #ocai-openai-chat-completions-edges-nodes }

```python
NODES: tuple[NodeId, ...] = (CHAT_COMPLETIONS_REQUEST, CHAT_COMPLETIONS_RESPONSE, CHAT_COMPLETIONS_CHUNK)
```

### `EDGES` { #ocai-openai-chat-completions-edges-edges }

```python
EDGES  # See source for the full declaration.
```

### `TRANSDUCERS` { #ocai-openai-chat-completions-edges-transducers }

```python
TRANSDUCERS  # See source for the full declaration.
```

### `PROFILES` { #ocai-openai-chat-completions-edges-profiles }

```python
PROFILES  # See source for the full declaration.
```

## `ocai.openai.chat_completions.variant`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-openai/src/ocai/openai/chat_completions/variant.py)

### `ChatCompletionsVariant` { #ocai-openai-chat-completions-variant-chatcompletionsvariant }

```python
class ChatCompletionsVariant:
    request_node: NodeId
    response_node: NodeId
    chunk_node: NodeId
    traits: DialectTraits
    path: str
    reasoning_field: str | None = None
    max_tokens_field: str = 'max_completion_tokens'
    knob_ranges: tuple[tuple[str, float, float], ...] | None = None
    finish_reasons: tuple[tuple[str, str], ...] = ()
```

````text
Select identity and compatible field lanes without inheriting edge contracts.

The owning plugin must publish its own census, fixtures and profiles. This
configuration registers no catalog component and performs no provider I/O.
````

## `ocai.openai.chat_completions.wire`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-openai/src/ocai/openai/chat_completions/wire.py)

### `ChatCompletionContentPartTextParam` { #ocai-openai-chat-completions-wire-chatcompletioncontentparttextparam }

```python
class ChatCompletionContentPartTextParam(_Wire):
    text: str
```

````text
A text content part.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_text%20%3E%20(schema)>)

Attributes:
    text: The text content.
    type: The content-part type discriminator; always `text`.
````

#### `ChatCompletionContentPartTextParam.type` { #ocai-openai-chat-completions-wire-chatcompletioncontentparttextparam-type }

```python
@property
def type(self) -> Literal['text']
```

````text
See the source declaration for this symbol.
````

### `ImageURL` { #ocai-openai-chat-completions-wire-imageurl }

```python
class ImageURL(_Wire):
    url: str
    detail: Literal['auto', 'low', 'high'] | None = None
```

````text
The `image_url` object nested in an image content part.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_image%20%3E%20(schema)>)

Attributes:
    url: Either a URL of the image or a base64 `data:` URL.
    detail: Detail level of the image (`auto`, `low`, or `high`).
````

### `ChatCompletionContentPartImageParam` { #ocai-openai-chat-completions-wire-chatcompletioncontentpartimageparam }

```python
class ChatCompletionContentPartImageParam(_Wire):
    image_url: ImageURL
```

````text
An image content part.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_image%20%3E%20(schema)>)

Attributes:
    image_url: The image URL and detail level.
    type: The content-part type discriminator; always `image_url`.
````

#### `ChatCompletionContentPartImageParam.type` { #ocai-openai-chat-completions-wire-chatcompletioncontentpartimageparam-type }

```python
@property
def type(self) -> Literal['image_url']
```

````text
See the source declaration for this symbol.
````

### `InputAudio` { #ocai-openai-chat-completions-wire-inputaudio }

```python
class InputAudio(_Wire):
    data: str
    format: Literal['wav', 'mp3']
```

````text
The `input_audio` object nested in an input-audio content part.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_input_audio%20%3E%20(schema)>)

Attributes:
    data: Base64-encoded audio data.
    format: The format of the encoded audio data (`wav` or `mp3`).
````

### `ChatCompletionContentPartInputAudioParam` { #ocai-openai-chat-completions-wire-chatcompletioncontentpartinputaudioparam }

```python
class ChatCompletionContentPartInputAudioParam(_Wire):
    input_audio: InputAudio
```

````text
An audio content part.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_input_audio%20%3E%20(schema)>)

Attributes:
    input_audio: The base64 audio payload and its format.
    type: The content-part type discriminator; always `input_audio`.
````

#### `ChatCompletionContentPartInputAudioParam.type` { #ocai-openai-chat-completions-wire-chatcompletioncontentpartinputaudioparam-type }

```python
@property
def type(self) -> Literal['input_audio']
```

````text
See the source declaration for this symbol.
````

### `FileFile` { #ocai-openai-chat-completions-wire-filefile }

```python
class FileFile(_Wire):
    file_data: str | None = None
    file_id: str | None = None
    filename: str | None = None
```

````text
The `file` object nested in a file content part (SDK name `FileFile`).

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_file%20%3E%20(schema)>)

Attributes:
    file_data: Base64-encoded file data, used when passing the file inline.
    file_id: The ID of an uploaded file to use as input.
    filename: The name of the file, used when passing the file inline.
````

### `File` { #ocai-openai-chat-completions-wire-file }

```python
class File(_Wire):
    file: FileFile
```

````text
A file content part (SDK union member name `File`).

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_file%20%3E%20(schema)>)

Attributes:
    file: The referenced or inline file.
    type: The content-part type discriminator; always `file`.
````

#### `File.type` { #ocai-openai-chat-completions-wire-file-type }

```python
@property
def type(self) -> Literal['file']
```

````text
See the source declaration for this symbol.
````

### `ChatCompletionContentPartRefusalParam` { #ocai-openai-chat-completions-wire-chatcompletioncontentpartrefusalparam }

```python
class ChatCompletionContentPartRefusalParam(_Wire):
    refusal: str
```

````text
A refusal content part (assistant output).

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_refusal%20%3E%20(schema)>)

Attributes:
    refusal: The refusal message generated by the model.
    type: The content-part type discriminator; always `refusal`.
````

#### `ChatCompletionContentPartRefusalParam.type` { #ocai-openai-chat-completions-wire-chatcompletioncontentpartrefusalparam-type }

```python
@property
def type(self) -> Literal['refusal']
```

````text
See the source declaration for this symbol.
````

### `ChatCompletionContentPartParam` { #ocai-openai-chat-completions-wire-chatcompletioncontentpartparam }

```python
ChatCompletionContentPartParam = ChatCompletionContentPartTextParam | ChatCompletionContentPartImageParam | ChatCompletionContentPartInputAudioParam | File
```

### `ContentArrayOfContentPart` { #ocai-openai-chat-completions-wire-contentarrayofcontentpart }

```python
ContentArrayOfContentPart = ChatCompletionContentPartTextParam | ChatCompletionContentPartRefusalParam
```

### `FunctionDefinition` { #ocai-openai-chat-completions-wire-functiondefinition }

```python
class FunctionDefinition(_Wire):
    name: str
    description: str | None = None
    parameters: dict[str, Any] | None = None
    strict: bool | None = None
```

````text
A function the model may call (shared `FunctionDefinition`).

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20function_definition%20%3E%20(schema)>)

Attributes:
    name: The function name (a-z, A-Z, 0-9, underscores, dashes; max len 64).
    description: What the function does, used by the model to choose it.
    parameters: The parameters as a JSON Schema object.
    strict: Whether to enforce strict schema adherence when generating args.
````

### `ChatCompletionFunctionToolParam` { #ocai-openai-chat-completions-wire-chatcompletionfunctiontoolparam }

```python
class ChatCompletionFunctionToolParam(_Wire):
    function: FunctionDefinition
```

````text
A function tool the model may call (aliased by `ChatCompletionToolParam`).

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_function_tool%20%3E%20(schema)>)

Attributes:
    function: The function definition.
    type: The tool type discriminator; always `function`.
````

#### `ChatCompletionFunctionToolParam.type` { #ocai-openai-chat-completions-wire-chatcompletionfunctiontoolparam-type }

```python
@property
def type(self) -> Literal['function']
```

````text
See the source declaration for this symbol.
````

### `ChatCompletionMessageFunctionToolCallParam` { #ocai-openai-chat-completions-wire-chatcompletionmessagefunctiontoolcallparam }

```python
class ChatCompletionMessageFunctionToolCallParam(_Wire):
    id: str
    function: _ToolCallFunction
```

````text
A function tool call on a request assistant message.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_message_function_tool_call%20%3E%20(schema)>)

Attributes:
    id: The ID of the tool call.
    function: The function the model called.
    type: The tool type discriminator; always `function`.
````

#### `ChatCompletionMessageFunctionToolCallParam.type` { #ocai-openai-chat-completions-wire-chatcompletionmessagefunctiontoolcallparam-type }

```python
@property
def type(self) -> Literal['function']
```

````text
See the source declaration for this symbol.
````

### `ChatCompletionNamedToolChoiceParam` { #ocai-openai-chat-completions-wire-chatcompletionnamedtoolchoiceparam }

```python
class ChatCompletionNamedToolChoiceParam(_Wire):
    function: _NamedToolChoiceFunction
```

````text
A `tool_choice` forcing a specific function call.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_named_tool_choice%20%3E%20(schema)>)

Attributes:
    function: The function the model must call.
    type: The tool type discriminator; always `function`.
````

#### `ChatCompletionNamedToolChoiceParam.type` { #ocai-openai-chat-completions-wire-chatcompletionnamedtoolchoiceparam-type }

```python
@property
def type(self) -> Literal['function']
```

````text
See the source declaration for this symbol.
````

### `ChatCompletionToolChoiceOptionParam` { #ocai-openai-chat-completions-wire-chatcompletiontoolchoiceoptionparam }

```python
ChatCompletionToolChoiceOptionParam = Literal['none', 'auto', 'required'] | ChatCompletionNamedToolChoiceParam
```

### `ResponseFormatText` { #ocai-openai-chat-completions-wire-responseformattext }

```python
class ResponseFormatText(_Wire)
```

````text
`response_format` selecting plain-text output.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20response_format_text%20%3E%20(schema)>)

Attributes:
    type: The response-format type discriminator; always `text`.
````

#### `ResponseFormatText.type` { #ocai-openai-chat-completions-wire-responseformattext-type }

```python
@property
def type(self) -> Literal['text']
```

````text
See the source declaration for this symbol.
````

### `ResponseFormatJSONObject` { #ocai-openai-chat-completions-wire-responseformatjsonobject }

```python
class ResponseFormatJSONObject(_Wire)
```

````text
`response_format` selecting a JSON object (legacy JSON mode).

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20response_format_json_object%20%3E%20(schema)>)

Attributes:
    type: The response-format type discriminator; always `json_object`.
````

#### `ResponseFormatJSONObject.type` { #ocai-openai-chat-completions-wire-responseformatjsonobject-type }

```python
@property
def type(self) -> Literal['json_object']
```

````text
See the source declaration for this symbol.
````

### `JSONSchema` { #ocai-openai-chat-completions-wire-jsonschema }

```python
class JSONSchema(_Wire):
    name: str
    description: str | None = None
    schema: dict[str, Any] | None = None
    strict: bool | None = None
```

````text
The `json_schema` object inside a structured-outputs response format.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20response_format_json_schema%20%3E%20(schema)>)

Attributes:
    name: The name of the response format (a-z, A-Z, 0-9, _ or -; max len 64).
    description: What the response format is for, used by the model.
    schema: The schema for the response format, as a JSON Schema object.
    strict: Whether to enable strict schema adherence.
````

### `ResponseFormatJSONSchema` { #ocai-openai-chat-completions-wire-responseformatjsonschema }

```python
class ResponseFormatJSONSchema(_Wire):
    json_schema: JSONSchema
```

````text
`response_format` selecting Structured Outputs against a JSON Schema.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20response_format_json_schema%20%3E%20(schema)>)

Attributes:
    json_schema: The named schema the output must satisfy.
    type: The response-format type discriminator; always `json_schema`.
````

#### `ResponseFormatJSONSchema.type` { #ocai-openai-chat-completions-wire-responseformatjsonschema-type }

```python
@property
def type(self) -> Literal['json_schema']
```

````text
See the source declaration for this symbol.
````

### `ResponseFormat` { #ocai-openai-chat-completions-wire-responseformat }

```python
ResponseFormat = ResponseFormatText | ResponseFormatJSONObject | ResponseFormatJSONSchema
```

### `ChatCompletionDeveloperMessageParam` { #ocai-openai-chat-completions-wire-chatcompletiondevelopermessageparam }

```python
class ChatCompletionDeveloperMessageParam(_Wire):
    content: str | list[ChatCompletionContentPartTextParam]
    name: str | None = None
```

````text
A `developer` message (replaces `system` for newer models).

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_developer_message_param%20%3E%20(schema)>)

Attributes:
    content: The developer instructions, as text or an array of text parts.
    name: An optional name to differentiate participants of the same role.
    role: The author role discriminator; always `developer`.
````

#### `ChatCompletionDeveloperMessageParam.role` { #ocai-openai-chat-completions-wire-chatcompletiondevelopermessageparam-role }

```python
@property
def role(self) -> Literal['developer']
```

````text
See the source declaration for this symbol.
````

### `ChatCompletionSystemMessageParam` { #ocai-openai-chat-completions-wire-chatcompletionsystemmessageparam }

```python
class ChatCompletionSystemMessageParam(_Wire):
    content: str | list[ChatCompletionContentPartTextParam]
    name: str | None = None
```

````text
A `system` message setting model behaviour.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_system_message_param%20%3E%20(schema)>)

Attributes:
    content: The system prompt, as text or an array of text parts.
    name: An optional name to differentiate participants of the same role.
    role: The author role discriminator; always `system`.
````

#### `ChatCompletionSystemMessageParam.role` { #ocai-openai-chat-completions-wire-chatcompletionsystemmessageparam-role }

```python
@property
def role(self) -> Literal['system']
```

````text
See the source declaration for this symbol.
````

### `ChatCompletionUserMessageParam` { #ocai-openai-chat-completions-wire-chatcompletionusermessageparam }

```python
class ChatCompletionUserMessageParam(_Wire):
    content: str | list[ChatCompletionContentPartParam]
    name: str | None = None
```

````text
A `user` message — the end-user's turn, optionally multimodal.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_user_message_param%20%3E%20(schema)>)

Attributes:
    content: Plain text or an array of multimodal content parts.
    name: An optional name to differentiate participants of the same role.
    role: The author role discriminator; always `user`.
````

#### `ChatCompletionUserMessageParam.role` { #ocai-openai-chat-completions-wire-chatcompletionusermessageparam-role }

```python
@property
def role(self) -> Literal['user']
```

````text
See the source declaration for this symbol.
````

### `ChatCompletionAssistantMessageParam` { #ocai-openai-chat-completions-wire-chatcompletionassistantmessageparam }

```python
class ChatCompletionAssistantMessageParam(_Wire):
    audio: _AssistantAudio | None = None
    content: str | list[ContentArrayOfContentPart] | None = None
    function_call: _AssistantFunctionCall | None = None
    name: str | None = None
    refusal: str | None = None
    tool_calls: list[ChatCompletionMessageFunctionToolCallParam] | None = None
```

````text
An `assistant` message — a prior model turn replayed in the request.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_assistant_message_param%20%3E%20(schema)>)

Attributes:
    audio: Reference to a prior audio response from the model.
    content: Assistant text or an array of text/refusal parts; may be omitted
        when only `tool_calls` or `refusal` are present.
    function_call: Deprecated; superseded by `tool_calls`.
    name: An optional name to differentiate participants of the same role.
    refusal: The refusal message by the assistant.
    tool_calls: Tool calls the assistant previously requested.
    role: The author role discriminator; always `assistant`.
````

#### `ChatCompletionAssistantMessageParam.role` { #ocai-openai-chat-completions-wire-chatcompletionassistantmessageparam-role }

```python
@property
def role(self) -> Literal['assistant']
```

````text
See the source declaration for this symbol.
````

### `ChatCompletionToolMessageParam` { #ocai-openai-chat-completions-wire-chatcompletiontoolmessageparam }

```python
class ChatCompletionToolMessageParam(_Wire):
    content: str | list[ChatCompletionContentPartTextParam]
    tool_call_id: str
```

````text
A `tool` message carrying the result of a single tool call.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_tool_message_param%20%3E%20(schema)>)

Attributes:
    content: The tool result, as text or an array of text parts.
    tool_call_id: The `tool_calls` entry this message responds to.
    role: The author role discriminator; always `tool`.
````

#### `ChatCompletionToolMessageParam.role` { #ocai-openai-chat-completions-wire-chatcompletiontoolmessageparam-role }

```python
@property
def role(self) -> Literal['tool']
```

````text
See the source declaration for this symbol.
````

### `ChatCompletionMessageParam` { #ocai-openai-chat-completions-wire-chatcompletionmessageparam }

```python
ChatCompletionMessageParam = ChatCompletionDeveloperMessageParam | ChatCompletionSystemMessageParam | ChatCompletionUserMessageParam | ChatCompletionAssistantMessageParam | ChatCompletionToolMessageParam
```

### `ChatCompletionStreamOptionsParam` { #ocai-openai-chat-completions-wire-chatcompletionstreamoptionsparam }

```python
class ChatCompletionStreamOptionsParam(_Wire):
    include_obfuscation: bool | None = None
    include_usage: bool | None = None
```

````text
Options for streaming responses (`stream_options`).

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_stream_options%20%3E%20(schema)>)

Attributes:
    include_obfuscation: When true (default), add an `obfuscation` field to
        streaming events to normalize payload sizes; disable to save bandwidth.
    include_usage: When true, stream a final chunk carrying token `usage`.
````

### `CompletionCreateParams` { #ocai-openai-chat-completions-wire-completioncreateparams }

```python
class CompletionCreateParams(_Wire):
    model: str
    messages: list[ChatCompletionMessageParam]
    audio: dict[str, Any] | None = None
    frequency_penalty: float | None = None
    function_call: dict[str, Any] | str | None = None
    functions: list[dict[str, Any]] | None = None
    logit_bias: dict[str, int] | None = None
    logprobs: bool | None = None
    max_completion_tokens: int | None = None
    max_tokens: int | None = None
    metadata: dict[str, str] | None = None
    modalities: list[Literal['text', 'audio']] | None = None
    moderation: dict[str, Any] | None = None
    n: int | None = None
    parallel_tool_calls: bool | None = None
    prediction: dict[str, Any] | None = None
    presence_penalty: float | None = None
    prompt_cache_key: str | None = None
    prompt_cache_retention: Literal['in_memory', '24h'] | None = None
    reasoning_effort: Literal['minimal', 'low', 'medium', 'high'] | None = None
    response_format: ResponseFormat | None = None
    safety_identifier: str | None = None
    seed: int | None = None
    service_tier: Literal['auto', 'default', 'flex', 'scale', 'priority'] | None = None
    stop: str | list[str] | None = None
    store: bool | None = None
    stream: bool | None = None
    stream_options: ChatCompletionStreamOptionsParam | None = None
    temperature: float | None = None
    tool_choice: ChatCompletionToolChoiceOptionParam | None = None
    tools: list[ChatCompletionFunctionToolParam] | None = None
    top_logprobs: int | None = None
    top_p: float | None = None
    user: str | None = None
    verbosity: Literal['low', 'medium', 'high'] | None = None
    web_search_options: dict[str, Any] | None = None
```

````text
A `POST /v1/chat/completions` request body (SDK `CompletionCreateParamsBase`).

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(method)%20create>)

Attributes:
    messages: The conversation so far, as role-tagged messages.
    model: The model ID to use.
    audio: Output audio parameters (for `audio` modality). Passthrough; TODO.
    frequency_penalty: Penalize tokens by existing frequency (-2.0..2.0).
    function_call: Deprecated; superseded by `tool_choice`. Passthrough.
    functions: Deprecated; superseded by `tools`. Passthrough.
    logit_bias: Per-token-ID additive logit bias (-100..100).
    logprobs: Whether to return log probabilities of output tokens.
    max_completion_tokens: Upper bound on generated completion tokens.
    max_tokens: Deprecated cap on generated tokens; prefer
        `max_completion_tokens`.
    metadata: Up to 16 key/value string pairs attached to the request.
    modalities: Output types to generate (`text`, and/or `audio`).
    moderation: Moderation configuration. Passthrough; TODO.
    n: How many completions to generate per prompt.
    parallel_tool_calls: Whether to allow tool calls in parallel.
    prediction: Predicted-output configuration. Passthrough; TODO.
    presence_penalty: Penalize tokens by prior presence (-2.0..2.0).
    prompt_cache_key: Cache key for prompt-prefix caching.
    prompt_cache_retention: Prompt-cache retention (`in_memory` or `24h`).
    reasoning_effort: Reasoning depth (`minimal`/`low`/`medium`/`high`).
    response_format: Output format selector (text / JSON / JSON Schema).
    safety_identifier: Stable identifier used for safety/abuse monitoring.
    seed: Best-effort determinism seed.
    service_tier: Latency/throughput tier hint.
    stop: Up to four stop sequences, as a string or list.
    store: Whether to store the output for model distillation/evals.
    stream_options: Options that apply only when `stream` is true.
    temperature: Sampling temperature (0..2).
    tool_choice: Whether/which tool the model must call.
    tools: Tools the model may call.
    top_logprobs: Number of most-likely tokens to return per position.
    top_p: Nucleus-sampling probability mass (0..1).
    user: Deprecated stable end-user identifier (use `safety_identifier`).
    verbosity: Output verbosity hint (`low`/`medium`/`high`).
    web_search_options: Built-in web-search tool options. Passthrough; TODO.
    stream: Whether to stream partial chunks as server-sent events.
````

### `PromptTokensDetails` { #ocai-openai-chat-completions-wire-prompttokensdetails }

```python
class PromptTokensDetails(_Wire):
    audio_tokens: int | None = None
    cached_tokens: int | None = None
```

````text
Breakdown of prompt tokens inside `usage`.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20completions%20%3E%20(model)%20completion_usage%20%3E%20(schema)>)

Attributes:
    audio_tokens: Audio tokens present in the prompt.
    cached_tokens: Prompt tokens served from the prompt cache.
````

### `CompletionTokensDetails` { #ocai-openai-chat-completions-wire-completiontokensdetails }

```python
class CompletionTokensDetails(_Wire):
    accepted_prediction_tokens: int | None = None
    audio_tokens: int | None = None
    reasoning_tokens: int | None = None
    rejected_prediction_tokens: int | None = None
```

````text
Breakdown of completion tokens inside `usage`.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20completions%20%3E%20(model)%20completion_usage%20%3E%20(schema)>)

Attributes:
    accepted_prediction_tokens: Predicted-output tokens that were accepted.
    audio_tokens: Audio tokens generated in the completion.
    reasoning_tokens: Tokens spent on internal reasoning.
    rejected_prediction_tokens: Predicted-output tokens that were rejected.
````

### `CompletionUsage` { #ocai-openai-chat-completions-wire-completionusage }

```python
class CompletionUsage(_Wire):
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int
    completion_tokens_details: CompletionTokensDetails | None = None
    prompt_tokens_details: PromptTokensDetails | None = None
```

````text
Token usage for the request (`usage` on the response and final chunk).

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20completions%20%3E%20(model)%20completion_usage%20%3E%20(schema)>)

Attributes:
    completion_tokens: Tokens in the generated completion.
    prompt_tokens: Tokens in the prompt.
    total_tokens: Sum of prompt and completion tokens.
    completion_tokens_details: Optional completion-token breakdown.
    prompt_tokens_details: Optional prompt-token breakdown.
````

### `ChatCompletionMessageFunctionToolCall` { #ocai-openai-chat-completions-wire-chatcompletionmessagefunctiontoolcall }

```python
class ChatCompletionMessageFunctionToolCall(_Wire):
    id: str
    function: _ResponseToolCallFunction
```

````text
A function tool call on a response message.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_message_function_tool_call%20%3E%20(schema)>)

Attributes:
    id: The ID of the tool call.
    function: The function the model called.
    type: The tool type discriminator; always `function`.
````

#### `ChatCompletionMessageFunctionToolCall.type` { #ocai-openai-chat-completions-wire-chatcompletionmessagefunctiontoolcall-type }

```python
@property
def type(self) -> Literal['function']
```

````text
See the source declaration for this symbol.
````

### `AnnotationURLCitation` { #ocai-openai-chat-completions-wire-annotationurlcitation }

```python
class AnnotationURLCitation(_Wire):
    end_index: int
    start_index: int
    title: str
    url: str
```

````text
A URL citation inside a message annotation.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_message%20%3E%20(schema)>)

Attributes:
    end_index: Last index of the URL citation in the message.
    start_index: First index of the URL citation in the message.
    title: The title of the web resource.
    url: The URL of the web resource.
````

### `Annotation` { #ocai-openai-chat-completions-wire-annotation }

```python
class Annotation(_Wire):
    url_citation: AnnotationURLCitation
```

````text
A message annotation (web-search URL citation).

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_message%20%3E%20(schema)>)

Attributes:
    url_citation: The URL citation when using web search.
    type: The annotation type discriminator; always `url_citation`.
````

#### `Annotation.type` { #ocai-openai-chat-completions-wire-annotation-type }

```python
@property
def type(self) -> Literal['url_citation']
```

````text
See the source declaration for this symbol.
````

### `ChatCompletionMessage` { #ocai-openai-chat-completions-wire-chatcompletionmessage }

```python
class ChatCompletionMessage(_Wire):
    role: Literal['assistant'] = 'assistant'
    content: str | None = None
    refusal: str | None = None
    annotations: list[Annotation] | None = None
    audio: dict[str, Any] | None = None
    function_call: _AssistantFunctionCall | None = None
    tool_calls: list[ChatCompletionMessageFunctionToolCall] | None = None
```

````text
The assistant message generated by the model (a choice's `message`).

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_message%20%3E%20(schema)>)

Attributes:
    role: The author role; always `assistant`.
    content: The message content, or `null` when only tools were called.
    refusal: The refusal message generated by the model.
    annotations: Web-search URL citations, when web search is used.
    audio: Audio response data. Passthrough; TODO model ChatCompletionAudio.
    function_call: Deprecated; superseded by `tool_calls`.
    tool_calls: Function tool calls the model generated.
````

### `ChoiceLogprobs` { #ocai-openai-chat-completions-wire-choicelogprobs }

```python
class ChoiceLogprobs(_Wire):
    content: list[dict[str, Any]] | None = None
    refusal: list[dict[str, Any]] | None = None
```

````text
Log-probability information for a choice.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion%20%3E%20(schema)>)

Attributes:
    content: Token log-probabilities for the message content. Passthrough; TODO.
    refusal: Token log-probabilities for the refusal. Passthrough; TODO.
````

### `Choice` { #ocai-openai-chat-completions-wire-choice }

```python
class Choice(_Wire):
    finish_reason: Literal['stop', 'length', 'tool_calls', 'content_filter', 'function_call']
    index: int
    message: ChatCompletionMessage
    logprobs: ChoiceLogprobs | None = None
```

````text
One completion choice within a chat completion response.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion%20%3E%20(schema)>)

Attributes:
    finish_reason: Why generation stopped.
    index: Position of this choice in the `choices` array.
    message: The generated assistant message.
    logprobs: Log-probability information, when requested.
````

### `ChatCompletion` { #ocai-openai-chat-completions-wire-chatcompletion }

```python
class ChatCompletion(_Wire):
    id: str
    choices: list[Choice]
    created: int
    model: str
    object: Literal['chat.completion'] = 'chat.completion'
    moderation: dict[str, Any] | None = None
    service_tier: Literal['auto', 'default', 'flex', 'scale', 'priority'] | None = None
    system_fingerprint: str | None = None
    usage: CompletionUsage | None = None
```

````text
A `/v1/chat/completions` (non-streaming) response body.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion%20%3E%20(schema)>)

Attributes:
    id: A unique identifier for the completion.
    choices: The generated choices (length `n`).
    created: Unix timestamp (seconds) of creation.
    model: The model used for the completion.
    object: The object type; always `chat.completion`.
    moderation: Moderation results. Passthrough; TODO model Moderation.
    service_tier: The service tier that processed the request.
    system_fingerprint: Backend configuration fingerprint.
    usage: Usage statistics for the completion request.
````

### `ChoiceDeltaFunctionCall` { #ocai-openai-chat-completions-wire-choicedeltafunctioncall }

```python
class ChoiceDeltaFunctionCall(_Wire):
    arguments: str | None = None
    name: str | None = None
```

````text
Incremental deprecated `function_call` fields in a streamed delta.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_chunk%20%3E%20(schema)>)

Attributes:
    arguments: A fragment of the JSON-encoded argument string.
    name: The name of the function to call.
````

### `ChoiceDeltaToolCallFunction` { #ocai-openai-chat-completions-wire-choicedeltatoolcallfunction }

```python
class ChoiceDeltaToolCallFunction(_Wire):
    arguments: str | None = None
    name: str | None = None
```

````text
Incremental `function` fields inside a streamed tool-call delta.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_chunk%20%3E%20(schema)>)

Attributes:
    arguments: A fragment of the JSON-encoded argument string to concatenate.
    name: The name of the function to call.
````

### `ChoiceDeltaToolCall` { #ocai-openai-chat-completions-wire-choicedeltatoolcall }

```python
class ChoiceDeltaToolCall(_Wire):
    index: int
    id: str | None = None
    function: ChoiceDeltaToolCallFunction | None = None
    type: Literal['function'] | None = None
```

````text
An incremental tool-call entry within a streamed choice delta.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_chunk%20%3E%20(schema)>)

Attributes:
    index: Position of this tool call in the assembled `tool_calls` array.
    id: The ID of the tool call (sent on the first delta for this index).
    function: Incremental name/argument fragments.
    type: The tool type; sent on the first delta; `function`.
````

### `ChoiceDelta` { #ocai-openai-chat-completions-wire-choicedelta }

```python
class ChoiceDelta(_Wire):
    content: str | None = None
    function_call: ChoiceDeltaFunctionCall | None = None
    refusal: str | None = None
    role: Literal['developer', 'system', 'user', 'assistant', 'tool'] | None = None
    tool_calls: list[ChoiceDeltaToolCall] | None = None
```

````text
The incremental `delta` carried by a streamed choice.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_chunk%20%3E%20(schema)>)

Attributes:
    content: A fragment of generated text to concatenate.
    function_call: Deprecated; superseded by `tool_calls`.
    refusal: A fragment of a refusal message to concatenate.
    role: The author role (sent once, on the first delta).
    tool_calls: Incremental tool-call fragments.
````

### `ChunkChoice` { #ocai-openai-chat-completions-wire-chunkchoice }

```python
class ChunkChoice(_Wire):
    delta: ChoiceDelta
    index: int
    finish_reason: Literal['stop', 'length', 'tool_calls', 'content_filter', 'function_call'] | None = None
    logprobs: ChoiceLogprobs | None = None
```

````text
One choice within a streamed chat completion chunk (SDK `Choice`).

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_chunk%20%3E%20(schema)>)

Attributes:
    delta: The incremental update for this choice.
    index: Position of this choice in the `choices` array.
    finish_reason: Set on the final chunk for the choice; otherwise `null`.
    logprobs: Log-probability information, when requested.
````

### `ChatCompletionChunk` { #ocai-openai-chat-completions-wire-chatcompletionchunk }

```python
class ChatCompletionChunk(_Wire):
    id: str
    choices: list[ChunkChoice]
    created: int
    model: str
    object: Literal['chat.completion.chunk'] = 'chat.completion.chunk'
    moderation: dict[str, Any] | None = None
    service_tier: Literal['auto', 'default', 'flex', 'scale', 'priority'] | None = None
    system_fingerprint: str | None = None
    usage: CompletionUsage | None = None
```

````text
A single `chat.completion.chunk` server-sent event body.

Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_chunk%20%3E%20(schema)>)

Attributes:
    id: Identifier shared by every chunk of a streamed completion.
    choices: The incremental choices in this chunk.
    created: Unix timestamp (seconds) of creation.
    model: The model that produced the completion.
    object: The object type; always `chat.completion.chunk`.
    moderation: Moderation results. Passthrough; TODO model Moderation.
    service_tier: The service tier that processed the request.
    system_fingerprint: Backend configuration fingerprint.
    usage: Final token usage, present only when stream usage is included.
````

## `ocai.openai.responses`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-openai/src/ocai/openai/responses/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-openai-responses-responses-chunk"></span>`RESPONSES_CHUNK` | [`ocai.openai.responses.codec.RESPONSES_CHUNK`](ocai-openai.md#ocai-openai-responses-codec-responses-chunk) |
| <span id="ocai-openai-responses-responses-request"></span>`RESPONSES_REQUEST` | [`ocai.openai.responses.codec.RESPONSES_REQUEST`](ocai-openai.md#ocai-openai-responses-codec-responses-request) |
| <span id="ocai-openai-responses-responses-response"></span>`RESPONSES_RESPONSE` | [`ocai.openai.responses.codec.RESPONSES_RESPONSE`](ocai-openai.md#ocai-openai-responses-codec-responses-response) |
| <span id="ocai-openai-responses-responsescodec"></span>`ResponsesCodec` | [`ocai.openai.responses.codec.ResponsesCodec`](ocai-openai.md#ocai-openai-responses-codec-responsescodec) |

### `FRAGMENT` { #ocai-openai-responses-fragment }

```python
FRAGMENT = CatalogFragment(origin=ORIGIN, nodes=NODES, edges=EDGES, transducers=TRANSDUCERS, profiles=PROFILES, traits=())
```

## `ocai.openai.responses.codec`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-openai/src/ocai/openai/responses/codec.py)

### `PROVIDER` { #ocai-openai-responses-codec-provider }

```python
PROVIDER = 'openai'
```

### `INTERFACE` { #ocai-openai-responses-codec-interface }

```python
INTERFACE = 'responses'
```

### `TAG` { #ocai-openai-responses-codec-tag }

```python
TAG = '2025-03'
```

### `RESPONSES_PATH` { #ocai-openai-responses-codec-responses-path }

```python
RESPONSES_PATH = '/v1/responses'
```

### `RESPONSES_REQUEST` { #ocai-openai-responses-codec-responses-request }

```python
RESPONSES_REQUEST = NodeId(provider=PROVIDER, interface=INTERFACE, tag=TAG, shape=CHAT_REQUEST, released=_RELEASED, status=Status.STABLE)
```

### `RESPONSES_RESPONSE` { #ocai-openai-responses-codec-responses-response }

```python
RESPONSES_RESPONSE = NodeId(provider=PROVIDER, interface=INTERFACE, tag=TAG, shape=CHAT_RESPONSE, released=_RELEASED, status=Status.STABLE)
```

### `RESPONSES_CHUNK` { #ocai-openai-responses-codec-responses-chunk }

```python
RESPONSES_CHUNK = NodeId(provider=PROVIDER, interface=INTERFACE, tag=TAG, shape=CHAT_CHUNK, released=_RELEASED, status=Status.STABLE)
```

### `CANONICAL_REQUEST` { #ocai-openai-responses-codec-canonical-request }

```python
CANONICAL_REQUEST = canonical_node(CHAT_REQUEST)
```

### `CANONICAL_RESPONSE` { #ocai-openai-responses-codec-canonical-response }

```python
CANONICAL_RESPONSE = canonical_node(CHAT_RESPONSE)
```

### `CANONICAL_CHUNK` { #ocai-openai-responses-codec-canonical-chunk }

```python
CANONICAL_CHUNK = canonical_node(CHAT_CHUNK)
```

### `ResponsesCodec` { #ocai-openai-responses-codec-responsescodec }

```python
class ResponsesCodec:
    provider = PROVIDER
    interface = INTERFACE
    request_node = RESPONSES_REQUEST
    response_node = RESPONSES_RESPONSE
    chunk_node = RESPONSES_CHUNK
```

````text
The `openai/responses` dialect codec — pure mapping, no I/O [stub].

Same shape and obligations as `ChatCompletionsCodec`: every conversion
returns an `EdgeOutput` with its loss/shift records, unknown input never raises,
and the codec expands only its own `provider_options` namespace
(`"openai.responses"`).
````

#### `ResponsesCodec.native_path` { #ocai-openai-responses-codec-responsescodec-native-path }

```python
def native_path(self, model: str) -> str
```

````text
Return the first-party endpoint path for a Responses call.

Args:
    model: The target model name (travels in the request body).

Returns:
    The Responses API path.
````

#### `ResponsesCodec.encode_request` { #ocai-openai-responses-codec-responsescodec-encode-request }

```python
def encode_request(self, request: ChatRequest) -> EdgeOutput
```

````text
Encode a canonical `ChatRequest` into a `/responses` body.

Args:
    request: The canonical request to encode.

Returns:
    An `EdgeOutput` with the wire request dict and this edge's records.
````

#### `ResponsesCodec.decode_response` { #ocai-openai-responses-codec-responsescodec-decode-response }

```python
def decode_response(self, payload: dict[str, Any]) -> EdgeOutput
```

````text
Decode a `/responses` body into a canonical `ChatResponse`.

Args:
    payload: The raw response body, already JSON-parsed.

Returns:
    An `EdgeOutput` with the canonical `ChatResponse` and this
    edge's records.
````

#### `ResponsesCodec.decode_event` { #ocai-openai-responses-codec-responsescodec-decode-event }

```python
def decode_event(self, event: str | None, data: str) -> ChatChunk | None
```

````text
Decode one `/responses` semantic SSE event into a `ChatChunk`.

Args:
    event: The SSE `event:` name (`response.output_text.delta`, …).
    data: The SSE `data:` payload.

Returns:
    The canonical chunk, or `None` when the frame surfaces nothing.
````

#### `ResponsesCodec.map_error` { #ocai-openai-responses-codec-responsescodec-map-error }

```python
def map_error(self, status: int | None, body: dict[str, Any] | None) -> OcaiError | None
```

````text
Refine a Responses error body onto the precise error taxonomy.

Args:
    status: The HTTP status of the failed response, if known.
    body: The parsed error body, if any.

Returns:
    A precise `OcaiError`, or `None` to defer to the neutral mapping.
````

## `ocai.openai.responses.edges`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-openai/src/ocai/openai/responses/edges.py)

### `ORIGIN` { #ocai-openai-responses-edges-origin }

```python
ORIGIN = Origin(distribution='ocai-openai', version='0.1.0')
```

### `ENCODE_REQUEST_CONTRACT` { #ocai-openai-responses-edges-encode-request-contract }

```python
ENCODE_REQUEST_CONTRACT = EdgeContract(census={}, note='canonical chat.request -> openai/responses [stub: census with the item-model encode]')
```

### `DECODE_RESPONSE_CONTRACT` { #ocai-openai-responses-edges-decode-response-contract }

```python
DECODE_RESPONSE_CONTRACT = EdgeContract(census={}, note='openai/responses -> canonical chat.response [stub: census with the item-model decode]')
```

### `DECODE_CHUNK_CONTRACT` { #ocai-openai-responses-edges-decode-chunk-contract }

```python
DECODE_CHUNK_CONTRACT = EdgeContract(census={}, note='openai/responses -> canonical chat.chunk [stub: census with the semantic-event decode]')
```

### `NODES` { #ocai-openai-responses-edges-nodes }

```python
NODES: tuple[NodeId, ...] = (RESPONSES_REQUEST, RESPONSES_RESPONSE, RESPONSES_CHUNK)
```

### `EDGES` { #ocai-openai-responses-edges-edges }

```python
EDGES: tuple[Edge, ...] = ()
```

### `TRANSDUCERS` { #ocai-openai-responses-edges-transducers }

```python
TRANSDUCERS: tuple[StreamEdge, ...] = ()
```

### `PROFILES` { #ocai-openai-responses-edges-profiles }

```python
PROFILES: tuple[CapabilityProfile, ...] = ()
```

## `ocai.openai.responses.wire`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-openai/src/ocai/openai/responses/wire.py)
