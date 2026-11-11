# `ocai.anthropic` API reference

Generated from the checked-out package sources. Signatures, declared fields,
methods, type aliases and explicit re-exports are checked for drift. Inherited
members follow their named base class; a type's presence does not establish
provider execution support. See [supported features](../provider-feature-matrix.md).

## `ocai.anthropic`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-anthropic/src/ocai/anthropic/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-anthropic-messages"></span>`messages` | [`ocai.anthropic.messages`](ocai-anthropic.md#ocai-anthropic-messages) |
| <span id="ocai-anthropic-fragment"></span>`FRAGMENT` | [`ocai.anthropic.messages.FRAGMENT`](ocai-anthropic.md#ocai-anthropic-messages-fragment) |
| <span id="ocai-anthropic-chat-model"></span>`chat_model` | [`ocai.anthropic.messages.chat_model`](ocai-anthropic.md#ocai-anthropic-messages-chat-model) |

## `ocai.anthropic.messages`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-anthropic/src/ocai/anthropic/messages/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-anthropic-messages-messages-chunk"></span>`MESSAGES_CHUNK` | [`ocai.anthropic.messages.codec.MESSAGES_CHUNK`](ocai-anthropic.md#ocai-anthropic-messages-codec-messages-chunk) |
| <span id="ocai-anthropic-messages-messages-request"></span>`MESSAGES_REQUEST` | [`ocai.anthropic.messages.codec.MESSAGES_REQUEST`](ocai-anthropic.md#ocai-anthropic-messages-codec-messages-request) |
| <span id="ocai-anthropic-messages-messages-response"></span>`MESSAGES_RESPONSE` | [`ocai.anthropic.messages.codec.MESSAGES_RESPONSE`](ocai-anthropic.md#ocai-anthropic-messages-codec-messages-response) |
| <span id="ocai-anthropic-messages-messagescodec"></span>`MessagesCodec` | [`ocai.anthropic.messages.codec.MessagesCodec`](ocai-anthropic.md#ocai-anthropic-messages-codec-messagescodec) |

### `FRAGMENT` { #ocai-anthropic-messages-fragment }

```python
FRAGMENT = CatalogFragment(origin=ORIGIN, nodes=NODES, edges=EDGES, transducers=TRANSDUCERS, profiles=PROFILES, traits=(dialect_traits(),), components=(Component(provider=MessagesCodec.provider, interface=MessagesCodec.interface, capability=CHAT, factory=MessagesCodec),))
```

### `chat_model` { #ocai-anthropic-messages-chat-model }

```python
def chat_model(model_name: str, *, credentials: Credential) -> ChatModel
```

````text
Sanctioned sugar (§3.4 door 2): a first-party Anthropic chat model.

A THIN wrapper over the exact same fragment + facade machinery as the
core string door — never a separate code path: it *is* a call to
`ocai.chat.model(f"anthropic/{model_name}", ...)` over a minimal catalog
built from this interface's `FRAGMENT` (so the front door composes a
`Direct` host at the Anthropic origin from the fragment's declared
traits — which inject the `anthropic-version` header — the
`MessagesCodec` from the fragment's component factory, and an
`HttpxTransport`). The model name binds to the returned model object
here, at construction; `ChatRequest`s stay pure conversation and never
carry it. For Vertex/Bedrock, compose the pieces directly with the
appropriate host and credential.

Args:
    model_name: The Anthropic model name bound to the returned model
        object (the facade's `EndpointSpec.resource`).
    credentials: The credential applied per request at the driver leaf —
        `x-api-key` first-party, so supply
        `ApiKey(key, header="x-api-key", scheme="")`. Required; there is
        no ambient discovery (rule 13).

Returns:
    A `ChatModel` implementation backed by this interface.
````

## `ocai.anthropic.messages.codec`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-anthropic/src/ocai/anthropic/messages/codec.py)

### `PROVIDER` { #ocai-anthropic-messages-codec-provider }

```python
PROVIDER = 'anthropic'
```

### `INTERFACE` { #ocai-anthropic-messages-codec-interface }

```python
INTERFACE = 'messages'
```

### `TAG` { #ocai-anthropic-messages-codec-tag }

```python
TAG = '2023-06'
```

### `ANTHROPIC_BASE_URL` { #ocai-anthropic-messages-codec-anthropic-base-url }

```python
ANTHROPIC_BASE_URL = 'https://api.anthropic.com'
```

### `MESSAGES_PATH` { #ocai-anthropic-messages-codec-messages-path }

```python
MESSAGES_PATH = '/v1/messages'
```

### `ANTHROPIC_VERSION` { #ocai-anthropic-messages-codec-anthropic-version }

```python
ANTHROPIC_VERSION = '2023-06-01'
```

### `ANTHROPIC_VERTEX_VERSION` { #ocai-anthropic-messages-codec-anthropic-vertex-version }

```python
ANTHROPIC_VERTEX_VERSION = 'vertex-2023-10-16'
```

### `ANTHROPIC_BEDROCK_VERSION` { #ocai-anthropic-messages-codec-anthropic-bedrock-version }

```python
ANTHROPIC_BEDROCK_VERSION = 'bedrock-2023-05-31'
```

### `DEFAULT_MAX_TOKENS` { #ocai-anthropic-messages-codec-default-max-tokens }

```python
DEFAULT_MAX_TOKENS = 1024
```

### `MESSAGES_REQUEST` { #ocai-anthropic-messages-codec-messages-request }

```python
MESSAGES_REQUEST = NodeId(provider=PROVIDER, interface=INTERFACE, tag=TAG, shape=CHAT_REQUEST, released=_RELEASED, status=Status.STABLE)
```

### `MESSAGES_RESPONSE` { #ocai-anthropic-messages-codec-messages-response }

```python
MESSAGES_RESPONSE = NodeId(provider=PROVIDER, interface=INTERFACE, tag=TAG, shape=CHAT_RESPONSE, released=_RELEASED, status=Status.STABLE)
```

### `MESSAGES_CHUNK` { #ocai-anthropic-messages-codec-messages-chunk }

```python
MESSAGES_CHUNK = NodeId(provider=PROVIDER, interface=INTERFACE, tag=TAG, shape=CHAT_CHUNK, released=_RELEASED, status=Status.STABLE)
```

### `CANONICAL_REQUEST` { #ocai-anthropic-messages-codec-canonical-request }

```python
CANONICAL_REQUEST = canonical_node(CHAT_REQUEST)
```

### `CANONICAL_RESPONSE` { #ocai-anthropic-messages-codec-canonical-response }

```python
CANONICAL_RESPONSE = canonical_node(CHAT_RESPONSE)
```

### `CANONICAL_CHUNK` { #ocai-anthropic-messages-codec-canonical-chunk }

```python
CANONICAL_CHUNK = canonical_node(CHAT_CHUNK)
```

### `dialect_traits` { #ocai-anthropic-messages-codec-dialect-traits }

```python
def dialect_traits() -> DialectTraits
```

````text
Build the hosting traits the wire layer composes for this interface.

Anthropic first-party auth is the `x-api-key` header plus the required
`anthropic-version` header; cloud hosts (Vertex) drop the header and
require the `anthropic_version` body field instead. Declaring both here
is what lets the one codec run first-party, on Vertex, or on Bedrock
with no codec change (rule 14). The first-party origin
(`ANTHROPIC_BASE_URL`) rides along so the §3.4 front door can compose a
`Direct` binding without importing this plugin.

Returns:
    The interface's `DialectTraits`.
````

### `MessagesCodec` { #ocai-anthropic-messages-codec-messagescodec }

```python
class MessagesCodec:
    provider = PROVIDER
    interface = INTERFACE
    request_node = MESSAGES_REQUEST
    response_node = MESSAGES_RESPONSE
    chunk_node = MESSAGES_CHUNK
```

````text
The `anthropic/messages` dialect codec — pure mapping, no I/O.

Same obligations as its OpenAI sibling: every conversion returns a
`EdgeOutput` with its loss/shift records; unknown input never raises; only the
`"anthropic.messages"` `provider_options` namespace is expanded. See the
module docstring for this dialect's signature moves (system relocation,
REQUIRED thinking signatures, `input` ↔ `args_json`).
````

#### `MessagesCodec.native_path` { #ocai-anthropic-messages-codec-messagescodec-native-path }

```python
def native_path(self, model: str) -> str
```

````text
Return the first-party endpoint path for a Messages call.

Args:
    model: The target model name (unused first-party; a cloud host
        lifts it into the URL instead — that is the host's job).

Returns:
    The Messages API path.
````

#### `MessagesCodec.dialect_traits` { #ocai-anthropic-messages-codec-messagescodec-dialect-traits }

```python
def dialect_traits(self) -> DialectTraits
```

````text
Return this interface's hosting traits (the module `dialect_traits`).

The codec-attached face of the facade seam (WU-07): `WireChatModel`
builds each call's `EndpointSpec.traits` from the codec it was
composed with, so the wire layer reads the dialect's hosting facts
(the `anthropic-version` header, the Vertex body-version injection)
as data without the facade ever reaching into plugin modules.

Returns:
    The interface's `DialectTraits`.
````

#### `MessagesCodec.bind_resource` { #ocai-anthropic-messages-codec-messagescodec-bind-resource }

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

#### `MessagesCodec.bind_stream` { #ocai-anthropic-messages-codec-messagescodec-bind-stream }

```python
def bind_stream(self, payload: dict[str, Any]) -> dict[str, Any]
```

````text
Mark an encoded wire payload as a streaming request.

The streaming half of the bind seam (WU-11): how a dialect asks for
a stream is wire hygiene, not conversation, so graph edges never
emit it — the facade calls this after `bind_resource` when serving
`stream`/`astream`. On this wire that is the single `stream: true`
body member; usage needs no opt-in (`message_start`/`message_delta`
carry it natively).

Args:
    payload: The encoded wire request body, model already bound.

Returns:
    A new payload dict with `stream` set; the input is not mutated.
````

#### `MessagesCodec.encode_request` { #ocai-anthropic-messages-codec-messagescodec-encode-request }

```python
def encode_request(self, request: ChatRequest) -> EdgeOutput
```

````text
Encode a canonical `ChatRequest` into a Messages body.

The `canonical chat.request → anthropic/messages` edge function.
Leading system messages relocate to the top-level `system` field (a
`SemanticShift`, data-exact); mid-conversation system messages have
no wire home and ride the censused `anthropic.mid_conv_system`
extension lane with reported loss. `max_tokens` is required by the
wire: an omitted `config.max_output_tokens` gets `DEFAULT_MAX_TOKENS`
with a reported shift, never silently.

The emitted body has **no `model` member**: the canonical request
carries none (§3.4 — routing data binds to the model object), so
there is nothing to lose or report here; the facade injects the
bound resource via `bind_resource` before send.

Args:
    request: The canonical request to encode.

Returns:
    An `EdgeOutput` with the wire request dict and this edge's records.
````

#### `MessagesCodec.decode_request` { #ocai-anthropic-messages-codec-messagescodec-decode-request }

```python
def decode_request(self, payload: dict[str, Any]) -> EdgeOutput
```

````text
Decode a Messages request body into a `ChatRequest`.

The `anthropic/messages → canonical chat.request` edge function —
the audit direction: re-converting archived wire traffic back into
the canonical IR with no ability to make network calls (§1), and the
first hop of every cross-provider request conversion (WU-15). The
inverse of `encode_request`, with the dialect's signature moves run
backwards: the top-level `system` field **un-hoists** to a leading
canonical system message (a declared `SemanticShift(relocation)`),
`role: user` wire messages carrying `tool_result` blocks re-thread
as canonical tool turns (the inverse relocation, declared), and
`tool_use.input` objects serialize to the canonical `args_json`
wire-truth lane (the declared `anthropic.args_serialized` shift).
The wire `model` member is **routing data, not canonical content**
(§3.4): its echo rides `extensions["anthropic.model"]` with an
`EXTENSIONS` record; re-encoding anywhere binds a fresh resource at
the front door. Unknown envelope keys sweep into `extensions` —
total decode, never a raise (rule 6).

Args:
    payload: The raw archived request body, already JSON-parsed.

Returns:
    An `EdgeOutput` with the canonical `ChatRequest` and this
    edge's records.
````

#### `MessagesCodec.decode_response` { #ocai-anthropic-messages-codec-messagescodec-decode-response }

```python
def decode_response(self, payload: dict[str, Any]) -> EdgeOutput
```

````text
Decode a Messages response body into a `ChatResponse`.

The `anthropic/messages → canonical chat.response` edge function.
Every content block becomes a typed part (the honesty upgrade over the
old text-only adapter): `text` → `PartText`, `thinking` →
`PartReasoning` with its REQUIRED signature anchor,
`redacted_thinking` → `PartReasoning` with an opaque anchor,
`tool_use` → `PartToolCall` (the `input` object serialized to
`args_json` — a recorded shift, since the string form is canonical
truth), `server_tool_use`/`*_tool_result` → the server-tool spine
with byte-faithful payloads, and anything unrecognized →
`PartOpaque`, reported — this decoder never raises on unknown input
(rule 6).

Args:
    payload: The raw response body, already JSON-parsed.

Returns:
    An `EdgeOutput` with the canonical `ChatResponse` and this
    edge's records.
````

#### `MessagesCodec.decode_event` { #ocai-anthropic-messages-codec-messagescodec-decode-event }

```python
def decode_event(self, event: str | None, data: str) -> ChatChunk | None
```

````text
Decode one Messages SSE event into its first canonical chunk.

The single-chunk face of the event decoder — the shape the facade's
`ChatCodec` protocol declares. Most Messages events carry exactly one
signal, and this returns it; a multi-signal event (`message_start`
with usage, `message_delta` with finish and usage) surfaces only its
*first* chunk here — `decode_frame` is the total, ordered decoder
the `MessagesStreamTransducer` consumes on the streaming path.

Args:
    event: The SSE `event:` name (mirrors the payload `type`).
    data: The SSE `data:` payload.

Returns:
    The event's first canonical chunk, or `None` when the event
    surfaces nothing.
````

#### `MessagesCodec.decode_frame` { #ocai-anthropic-messages-codec-messagescodec-decode-frame }

```python
def decode_frame(self, event: str | None, data: str) -> EdgeOutput
```

````text
Decode one Messages SSE event into its ordered canonical chunks.

The total per-event half of the chunk-shape `StreamEdge` (the WU-10
pattern replayed on this dialect); the sans-io SSE field parsing
lives in `ocai.wire.sse` and hands this method the event's name and
`data` payload, so the plugin never touches a socket. Anthropic types
each event on the SSE `event:` line and in the payload's `type`, and
one wire event may carry several signals, each its own chunk in wire
order:

- `message_start` → `STREAM_START`, then the opening snapshot's
  cumulative usage as a `USAGE` chunk (`usage_cumulative=True`) —
  the wire's running totals, flagged per the chunk vocabulary;
- `content_block_start` → `PART_START` with the typed skeleton
  (`tool_use` opens a `PartToolCall` with empty `args_json` and
  `input_streaming` status — the wire's placeholder `input: {}`
  never seeds the string lane; thinking/redacted_thinking/text and
  the server-tool spine decode as in the unary edge);
- `content_block_delta` → one typed `PART_DELTA` (`text_delta` →
  `DeltaText`, `thinking_delta` → `DeltaReasoning`,
  `input_json_delta` → `DeltaToolArgs` raw fragments parsed once at
  PART_STOP, `signature_delta` → `DeltaSignature`); a delta type
  with no canonical lane yet is dropped with a
  reported `FieldLoss`, recoverable from the event log;
- `content_block_stop` → a bare `PART_STOP` (this wire carries no
  authoritative final part — the delta accumulation is the only
  carrier, so the fold law's strip-and-refold clause is vacuous);
- `message_delta` → the accumulating `FINISH` (typed `FinishInfo`;
  a matched `stop_sequence` rides the chunk's censused
  `anthropic.stop_sequence` extension, reported), then the
  cumulative `USAGE` chunk (`usage_cumulative=True` — the wire
  reports running totals for exactly the keys it names);
- `message_stop` → a bare `STREAM_STOP`; the transducer owns the
  terminal contract and stamps `StreamEnd(usage, finish)` onto it;
- `ping` → a `PING` keep-alive chunk;
- `error` → an `ERROR` chunk carrying the wire-shaped `ErrorInfo`
  (canonical taxonomy code + verbatim native payload + retryability,
  rule 8) — see `_stream_error`;
- any unrecognized event surfaces nothing canonical — never an
  exception (rule 6).

Args:
    event: The SSE `event:` name (mirrors the payload `type`).
    data: The SSE `data:` payload.

Returns:
    An `EdgeOutput` whose value is the event's canonical chunks, in
    order (possibly empty), with any drop/extension records.
````

#### `MessagesCodec.map_error` { #ocai-anthropic-messages-codec-messagescodec-map-error }

```python
def map_error(self, status: int | None, body: dict[str, Any] | None) -> OcaiError | None
```

````text
Refine an Anthropic error body onto the precise error taxonomy.

Anthropic returns `{"type": "error", "error": {"type", "message"}}`
uniformly; `error.type` is the authoritative classifier. Recognized
types map to the taxonomy (carrying the type as `code`); anything
else defers to the wire layer's status-based mapping.

Args:
    status: The HTTP status of the failed response, if known.
    body: The parsed Anthropic error body, if any.

Returns:
    A precise `OcaiError`, or `None` to defer to the neutral mapping.

TODO: Anthropic signals context overflow as a generic
    `invalid_request_error` with no distinct code; promoting it to
    `ContextLengthError` would need brittle message matching, so it
    intentionally defers.
````

### `MessagesStreamTransducer` { #ocai-anthropic-messages-codec-messagesstreamtransducer }

```python
class MessagesStreamTransducer
```

````text
Streaming transducer: Messages SSE events → canonical chunks.

The stateful per-stream object the chunk-shape `StreamEdge` manufactures
(one per stream — transducers are never shared). `feed` maps each wire
event through `MessagesCodec.decode_frame` (one event may split into
several canonical chunks, in order), stamps monotonic `seq` numbers, and
adds the statefulness a well-formed canonical stream needs on this
dialect:

- **Cumulative usage settlement.** `message_start` and `message_delta`
  report CUMULATIVE usage snapshots covering exactly the keys each names
  (`message_delta` typically carries only running `output_tokens`), so
  the transducer merges per (modality, unit, source) — last snapshot wins per
  tuple, keys a later snapshot omits keep their earlier values — and
  the terminal `StreamEnd.usage` carries the settled totals.
- **The terminal contract.** `message_stop` is this wire's terminal:
  any still-open slot (a block whose `content_block_stop` never came)
  is sealed first (`PART_STOP`, advancing tool calls to
  `input_complete` in the fold), then the `STREAM_STOP` is enriched
  with `StreamEnd(usage, finish)` — usage from the settled cumulative
  snapshots, finish from the accumulated `message_delta` record. A
  stream that dies before `message_stop` gets **no** terminal chunk:
  synthesizing one would pass accumulated content off as complete, and
  the accumulator's aborted-stream sealing (`extensions
  ["ocai.incomplete"]`) is the honest downstream. A mid-stream `error`
  event passes through as its wire-shaped `ERROR` chunk; the wire then
  closes without a terminal, honestly.

`flush` hands the graph this edge's `EdgeReport` (extension banks and
dropped delta lanes) so streaming conversion pays the same visible toll
as non-streaming (§4.1).
````

#### `MessagesStreamTransducer.__init__` { #ocai-anthropic-messages-codec-messagesstreamtransducer---init-- }

```python
def __init__(self) -> None
```

````text
Initialize per-stream state (codec, sequence counter, accumulators).
````

#### `MessagesStreamTransducer.feed` { #ocai-anthropic-messages-codec-messagesstreamtransducer-feed }

```python
def feed(self, event: Any) -> list[ChatChunk]
```

````text
Convert one wire SSE event into zero or more canonical chunks.

Args:
    event: The sans-io SSE event (duck-typed: `event`/`data`
        attributes) produced by the wire layer's `SSEParser`.

Returns:
    The canonical chunks this event surfaced, `seq`-stamped, in
    order — including, on `message_stop`, any synthesized slot
    seals and the enriched terminal.
````

#### `MessagesStreamTransducer.flush` { #ocai-anthropic-messages-codec-messagesstreamtransducer-flush }

```python
def flush(self) -> tuple[list[ChatChunk], EdgeReport]
```

````text
Return remaining incomplete search evidence and accumulated fidelity, never success.
````

## `ocai.anthropic.messages.edges`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-anthropic/src/ocai/anthropic/messages/edges.py)

### `ORIGIN` { #ocai-anthropic-messages-edges-origin }

```python
ORIGIN = Origin(distribution='ocai-anthropic', version='0.1.0')
```

### `ENCODE_REQUEST_CONTRACT` { #ocai-anthropic-messages-edges-encode-request-contract }

```python
ENCODE_REQUEST_CONTRACT  # See source for the full declaration.
```

### `DECODE_RESPONSE_CONTRACT` { #ocai-anthropic-messages-edges-decode-response-contract }

```python
DECODE_RESPONSE_CONTRACT  # See source for the full declaration.
```

### `DECODE_REQUEST_CONTRACT` { #ocai-anthropic-messages-edges-decode-request-contract }

```python
DECODE_REQUEST_CONTRACT  # See source for the full declaration.
```

### `DECODE_CHUNK_CONTRACT` { #ocai-anthropic-messages-edges-decode-chunk-contract }

```python
DECODE_CHUNK_CONTRACT  # See source for the full declaration.
```

### `encode_request` { #ocai-anthropic-messages-edges-encode-request }

```python
def encode_request(request: ChatRequest) -> EdgeOutput
```

````text
Edge fn `canonical chat.request → anthropic/messages`.

Args:
    request: The canonical request the planner routed to this edge.

Returns:
    The wire request dict with this edge's report.
````

### `decode_response` { #ocai-anthropic-messages-edges-decode-response }

```python
def decode_response(payload: dict[str, Any]) -> EdgeOutput
```

````text
Edge fn `anthropic/messages → canonical chat.response`.

Args:
    payload: The raw response body, already JSON-parsed.

Returns:
    The canonical `ChatResponse` with this edge's report.
````

### `decode_request` { #ocai-anthropic-messages-edges-decode-request }

```python
def decode_request(payload: dict[str, Any]) -> EdgeOutput
```

````text
Edge fn `anthropic/messages → canonical chat.request`.

The audit-tool direction: re-converting archived wire traffic back into
the canonical IR without any ability to make network calls (§1), and the
first hop of every cross-provider request conversion (WU-15).

Args:
    payload: The raw archived request body.

Returns:
    The canonical `ChatRequest` with this edge's report.
````

### `NODES` { #ocai-anthropic-messages-edges-nodes }

```python
NODES: tuple[NodeId, ...] = (MESSAGES_REQUEST, MESSAGES_RESPONSE, MESSAGES_CHUNK)
```

### `EDGES` { #ocai-anthropic-messages-edges-edges }

```python
EDGES  # See source for the full declaration.
```

### `TRANSDUCERS` { #ocai-anthropic-messages-edges-transducers }

```python
TRANSDUCERS: tuple[StreamEdge, ...] = (StreamEdge(src=MESSAGES_CHUNK, dst=CANONICAL_CHUNK, factory=MessagesStreamTransducer, contract=DECODE_CHUNK_CONTRACT, origin=ORIGIN),)
```

### `PROFILES` { #ocai-anthropic-messages-edges-profiles }

```python
PROFILES  # See source for the full declaration.
```

## `ocai.anthropic.messages.search`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-anthropic/src/ocai/anthropic/messages/search.py)

### `VERSION` { #ocai-anthropic-messages-search-version }

```python
VERSION = 'web_search_20250305'
```

### `OPTIONS` { #ocai-anthropic-messages-search-options }

```python
OPTIONS = 'anthropic.messages'
```

### `CONTROL` { #ocai-anthropic-messages-search-control }

```python
CONTROL = 'anthropic.web_search'
```

### `CITATION` { #ocai-anthropic-messages-search-citation }

```python
CITATION = 'anthropic.web_search_citation'
```

### `encode_tool` { #ocai-anthropic-messages-search-encode-tool }

```python
def encode_tool(tool: ServerTool, path: str, losses: list[FieldLoss]) -> dict[str, Any] | None
```

````text
Map only the qualified basic direct-search intent, reporting all exclusions.
````

### `decode_tool` { #ocai-anthropic-messages-search-decode-tool }

```python
def decode_tool(raw: dict[str, Any], path: str, losses: list[FieldLoss]) -> ServerTool | None
```

````text
Decode the selected tool version; retain other versions in the caller's fallback.
````

### `decode_call` { #ocai-anthropic-messages-search-decode-call }

```python
def decode_call(raw: dict[str, Any]) -> PartServerToolCall
```

````text
Preserve a native search-call block with a scoped replay identity.
````

### `decode_result` { #ocai-anthropic-messages-search-decode-result }

```python
def decode_result(raw: dict[str, Any]) -> PartServerToolResult
```

````text
Keep all native results, including encrypted bytes, under one scoped anchor.
````

### `encode_part` { #ocai-anthropic-messages-search-encode-part }

```python
def encode_part(part: PartServerToolCall | PartServerToolResult, path: str, losses: list[FieldLoss]) -> dict[str, Any] | None
```

````text
Replay a complete native search block only with matching scoped evidence.
````

### `decode_citation` { #ocai-anthropic-messages-search-decode-citation }

```python
def decode_citation(raw: Any, path: str, losses: list[FieldLoss]) -> Annotation
```

````text
Map a whole-block web citation; future forms retain their complete native record.
````

### `encode_citation` { #ocai-anthropic-messages-search-encode-citation }

```python
def encode_citation(annotation: Annotation, path: str, losses: list[FieldLoss]) -> dict[str, Any] | None
```

````text
Replay a qualified whole-block citation using its original encrypted index.
````

## `ocai.anthropic.messages.wire`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-anthropic/src/ocai/anthropic/messages/wire.py)

### `CacheControlEphemeral` { #ocai-anthropic-messages-wire-cachecontrolephemeral }

```python
class CacheControlEphemeral(_Wire):
    type: str = 'ephemeral'
    ttl: str | None = None
```

````text
An `ephemeral` cache-control breakpoint attachable to most blocks.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    type: Cache-control type; always `ephemeral`.
    ttl: Cache lifetime, `5m` or `1h`; defaults server-side to `5m`.
````

### `CitationsConfig` { #ocai-anthropic-messages-wire-citationsconfig }

```python
class CitationsConfig(_Wire):
    enabled: bool | None = None
```

````text
The `citations` config attached to a document or search-result block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    enabled: Whether the model may cite from this source.
````

### `Base64Source` { #ocai-anthropic-messages-wire-base64source }

```python
class Base64Source(_Wire):
    media_type: str
    data: str
```

````text
A base64-encoded binary source (image bytes or PDF bytes).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    media_type: The MIME type (e.g. `image/png`, `application/pdf`).
    data: The base64-encoded bytes.
````

### `URLSource` { #ocai-anthropic-messages-wire-urlsource }

```python
class URLSource(_Wire):
    url: str
```

````text
A source referenced by public URL (image or PDF).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    url: The publicly fetchable URL of the resource.
````

### `FileSource` { #ocai-anthropic-messages-wire-filesource }

```python
class FileSource(_Wire):
    file_id: str
```

````text
A source referencing a previously uploaded file by id (Files API).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    file_id: Identifier of the uploaded file to use as the source.
````

### `PlainTextSource` { #ocai-anthropic-messages-wire-plaintextsource }

```python
class PlainTextSource(_Wire):
    data: str
    media_type: str = 'text/plain'
```

````text
A plain-text document source (`media_type: text/plain`).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    data: The document text.
    media_type: The MIME type; always `text/plain`.
````

### `ContentBlockSource` { #ocai-anthropic-messages-wire-contentblocksource }

```python
class ContentBlockSource(_Wire):
    content: str | list[TextBlockParam | ImageBlockParam]
```

````text
A document source composed of inline content blocks.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    content: Either text, or an array of text/image content-block params.
````

### `ImageSource` { #ocai-anthropic-messages-wire-imagesource }

```python
ImageSource = Base64Source | URLSource | FileSource
```

### `DocumentSource` { #ocai-anthropic-messages-wire-documentsource }

```python
DocumentSource = Base64Source | PlainTextSource | URLSource | FileSource | ContentBlockSource
```

### `TextBlockParam` { #ocai-anthropic-messages-wire-textblockparam }

```python
class TextBlockParam(_Wire):
    text: str
    citations: list[dict[str, Any]] | None = None
    cache_control: CacheControlEphemeral | None = None
```

````text
A `text` content block on an input message.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    text: The text content.
    citations: Citation references attached to this text.
    cache_control: Optional cache breakpoint placed after this block.
````

### `ImageBlockParam` { #ocai-anthropic-messages-wire-imageblockparam }

```python
class ImageBlockParam(_Wire):
    source: ImageSource
    cache_control: CacheControlEphemeral | None = None
```

````text
An `image` content block on an input message.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    source: The image source (base64, URL, or uploaded file).
    cache_control: Optional cache breakpoint placed after this block.
````

### `DocumentBlockParam` { #ocai-anthropic-messages-wire-documentblockparam }

```python
class DocumentBlockParam(_Wire):
    source: DocumentSource
    title: str | None = None
    context: str | None = None
    citations: CitationsConfig | None = None
    cache_control: CacheControlEphemeral | None = None
```

````text
A `document` content block (PDF, plain text, or inline content).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    source: The document source.
    title: Optional human-readable document title.
    context: Optional extra context describing the document to the model.
    citations: Optional citation configuration for this document.
    cache_control: Optional cache breakpoint placed after this block.
````

### `ToolUseBlockParam` { #ocai-anthropic-messages-wire-tooluseblockparam }

```python
class ToolUseBlockParam(_Wire):
    id: str
    name: str
    input: dict[str, Any]
    cache_control: CacheControlEphemeral | None = None
```

````text
A `tool_use` block replayed on an input assistant message.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    id: Identifier of this tool invocation, echoed by the matching
        `tool_result` block's `tool_use_id`.
    name: Name of the tool the model called.
    input: The tool input object the model produced.
    cache_control: Optional cache breakpoint placed after this block.
````

### `ToolResultBlockParam` { #ocai-anthropic-messages-wire-toolresultblockparam }

```python
class ToolResultBlockParam(_Wire):
    tool_use_id: str
    content: str | list[ToolResultContent] | None = None
    is_error: bool | None = None
    cache_control: CacheControlEphemeral | None = None
```

````text
A `tool_result` block carrying the output of a single tool call.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    tool_use_id: Id of the `tool_use` block this result answers.
    content: The tool's output as text, or an array of content-block params
        (text/image/document/search-result).
    is_error: Whether the tool execution errored.
    cache_control: Optional cache breakpoint placed after this block.
````

### `ThinkingBlockParam` { #ocai-anthropic-messages-wire-thinkingblockparam }

```python
class ThinkingBlockParam(_Wire):
    thinking: str
    signature: str
```

````text
A `thinking` block replayed on an input assistant message.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    thinking: The internal reasoning text.
    signature: Signature verifying the block across turns.
````

### `RedactedThinkingBlockParam` { #ocai-anthropic-messages-wire-redactedthinkingblockparam }

```python
class RedactedThinkingBlockParam(_Wire):
    data: str
```

````text
A `redacted_thinking` block (opaque, server-encrypted reasoning).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    data: The redacted, encrypted reasoning payload.
````

### `SearchResultBlockParam` { #ocai-anthropic-messages-wire-searchresultblockparam }

```python
class SearchResultBlockParam(_Wire):
    title: str
    source: str
    content: list[TextBlockParam]
    citations: CitationsConfig | None = None
    cache_control: CacheControlEphemeral | None = None
```

````text
A `search_result` content block supplying citable retrieved content.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    title: Title of the search result.
    source: Source identifier (e.g. a URL or document id).
    content: The result body, as an array of text blocks.
    citations: Optional citation configuration for this result.
    cache_control: Optional cache breakpoint placed after this block.
````

### `ServerToolUseBlockParam` { #ocai-anthropic-messages-wire-servertooluseblockparam }

```python
class ServerToolUseBlockParam(_Wire):
    id: str
    name: str
    input: dict[str, Any]
    cache_control: CacheControlEphemeral | None = None
```

````text
A `server_tool_use` block replayed on an input message.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    id: Identifier of this server-tool invocation.
    name: Server tool name (`web_search`, `web_fetch`, `code_execution`, …).
    input: The tool input object.
    cache_control: Optional cache breakpoint placed after this block.
````

### `ToolResultContent` { #ocai-anthropic-messages-wire-toolresultcontent }

```python
ToolResultContent = TextBlockParam | ImageBlockParam | SearchResultBlockParam | DocumentBlockParam
```

### `ContentBlockParam` { #ocai-anthropic-messages-wire-contentblockparam }

```python
ContentBlockParam = TextBlockParam | ImageBlockParam | DocumentBlockParam | ToolUseBlockParam | ToolResultBlockParam | ThinkingBlockParam | RedactedThinkingBlockParam | SearchResultBlockParam | ServerToolUseBlockParam
```

### `MessageParam` { #ocai-anthropic-messages-wire-messageparam }

```python
class MessageParam(_Wire):
    role: str
    content: str | list[ContentBlockParam]
```

````text
A single input message in the `messages` array.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    role: Conversational role — `user` or `assistant`.
    content: Either a plain string, or an array of content-block params.
````

### `Tool` { #ocai-anthropic-messages-wire-tool }

```python
class Tool(_Wire):
    name: str
    input_schema: dict[str, Any]
    description: str | None = None
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    eager_input_streaming: bool | None = None
    input_examples: list[dict[str, Any]] | None = None
    allowed_callers: list[str] | None = None
```

````text
A custom (client-side) tool the model may call.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    name: Tool name the model uses to call it.
    input_schema: JSON Schema (`type: object`) for the tool's input.
    description: Natural-language description guiding when to call it.
    cache_control: Optional cache breakpoint placed after this tool.
    strict: Whether to guarantee the model's input validates against schema.
    defer_loading: Defer loading until a `tool_reference` is returned.
    eager_input_streaming: Stream input params eagerly (fine-grained).
    input_examples: Example inputs that prime the model.
    allowed_callers: Which callers (`direct`, code-execution variants) may
        invoke this tool.
````

### `BashTool` { #ocai-anthropic-messages-wire-bashtool }

```python
class BashTool(_Wire):
    name: str = 'bash'
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    input_examples: list[dict[str, Any]] | None = None
    allowed_callers: list[str] | None = None
```

````text
The server-side `bash` tool (`bash_20250124`).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    name: Tool name; always `bash`.
    cache_control: Optional cache breakpoint placed after this tool.
    strict: Whether to guarantee strict schema validation.
    defer_loading: Defer loading until referenced.
    input_examples: Example inputs that prime the model.
    allowed_callers: Which callers may invoke this tool.
````

### `CodeExecutionTool` { #ocai-anthropic-messages-wire-codeexecutiontool }

```python
class CodeExecutionTool(_Wire):
    name: str = 'code_execution'
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    allowed_callers: list[str] | None = None
```

````text
The server-side `code_execution` tool (`code_execution_20250825`).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    name: Tool name; always `code_execution`.
    cache_control: Optional cache breakpoint placed after this tool.
    strict: Whether to guarantee strict schema validation.
    defer_loading: Defer loading until referenced.
    allowed_callers: Which callers may invoke this tool.
````

### `CodeExecutionTool20260120` { #ocai-anthropic-messages-wire-codeexecutiontool20260120 }

```python
class CodeExecutionTool20260120(_Wire):
    name: str = 'code_execution'
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    allowed_callers: list[str] | None = None
```

````text
The `code_execution` tool with REPL state persistence (`code_execution_20260120`).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    name: Tool name; always `code_execution`.
    cache_control: Optional cache breakpoint placed after this tool.
    strict: Whether to guarantee strict schema validation.
    defer_loading: Defer loading until referenced.
    allowed_callers: Which callers may invoke this tool.
````

### `TextEditorTool` { #ocai-anthropic-messages-wire-texteditortool }

```python
class TextEditorTool(_Wire):
    name: str = 'str_replace_based_edit_tool'
    max_characters: int | None = None
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    input_examples: list[dict[str, Any]] | None = None
    allowed_callers: list[str] | None = None
```

````text
The server-side text-editor tool (`text_editor_20250728`).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    name: Tool name; always `str_replace_based_edit_tool`.
    max_characters: Max characters to display when viewing a file.
    cache_control: Optional cache breakpoint placed after this tool.
    strict: Whether to guarantee strict schema validation.
    defer_loading: Defer loading until referenced.
    input_examples: Example inputs that prime the model.
    allowed_callers: Which callers may invoke this tool.
````

### `MemoryTool` { #ocai-anthropic-messages-wire-memorytool }

```python
class MemoryTool(_Wire):
    name: str = 'memory'
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    input_examples: list[dict[str, Any]] | None = None
    allowed_callers: list[str] | None = None
```

````text
The server-side `memory` tool (`memory_20250818`).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    name: Tool name; always `memory`.
    cache_control: Optional cache breakpoint placed after this tool.
    strict: Whether to guarantee strict schema validation.
    defer_loading: Defer loading until referenced.
    input_examples: Example inputs that prime the model.
    allowed_callers: Which callers may invoke this tool.
````

### `UserLocation` { #ocai-anthropic-messages-wire-userlocation }

```python
class UserLocation(_Wire):
    type: str = 'approximate'
    city: str | None = None
    region: str | None = None
    country: str | None = None
    timezone: str | None = None
```

````text
The optional `user_location` hint on the web-search tool.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    type: Location type; always `approximate`.
    city: Approximate city.
    region: Approximate region/state.
    country: Approximate country.
    timezone: IANA timezone identifier.
````

### `BasicWebSearchTool` { #ocai-anthropic-messages-wire-basicwebsearchtool }

```python
class BasicWebSearchTool(_Wire):
    name: str = 'web_search'
    allowed_domains: list[str] | None = None
    blocked_domains: list[str] | None = None
    max_uses: int | None = None
    user_location: UserLocation | None = None
    allowed_callers: list[str] | None = None
```

````text
The explicitly qualified basic direct-search definition.

Attributes:
    name: Tool name, always web_search.
    allowed_domains: Optional inclusion restriction.
    blocked_domains: Optional exclusion restriction, mutually exclusive with inclusion.
    max_uses: Positive limit on search uses.
    user_location: Approximate location hints.
    allowed_callers: Only direct callers are qualified by WU-43.
````

### `WebSearchTool` { #ocai-anthropic-messages-wire-websearchtool }

```python
class WebSearchTool(_Wire):
    name: str = 'web_search'
    allowed_domains: list[str] | None = None
    blocked_domains: list[str] | None = None
    max_uses: int | None = None
    user_location: UserLocation | None = None
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    allowed_callers: list[str] | None = None
```

````text
The server-side `web_search` tool (`web_search_20260209`).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    name: Tool name; always `web_search`.
    allowed_domains: Only include results from these domains.
    blocked_domains: Exclude results from these domains.
    max_uses: Maximum number of searches per request.
    user_location: Approximate user location to localize results.
    cache_control: Optional cache breakpoint placed after this tool.
    strict: Whether to guarantee strict schema validation.
    defer_loading: Defer loading until referenced.
    allowed_callers: Which callers may invoke this tool.
````

### `WebFetchTool` { #ocai-anthropic-messages-wire-webfetchtool }

```python
class WebFetchTool(_Wire):
    name: str = 'web_fetch'
    allowed_domains: list[str] | None = None
    blocked_domains: list[str] | None = None
    max_content_tokens: int | None = None
    max_uses: int | None = None
    citations: CitationsConfig | None = None
    use_cache: bool | None = None
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    allowed_callers: list[str] | None = None
```

````text
The server-side `web_fetch` tool (`web_fetch_20260309`).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    name: Tool name; always `web_fetch`.
    allowed_domains: Only fetch from these domains.
    blocked_domains: Never fetch from these domains.
    max_content_tokens: Cap on tokens of fetched page text.
    max_uses: Maximum number of fetches per request.
    citations: Optional citation configuration for fetched content.
    use_cache: Whether to allow cached content (false bypasses the cache).
    cache_control: Optional cache breakpoint placed after this tool.
    strict: Whether to guarantee strict schema validation.
    defer_loading: Defer loading until referenced.
    allowed_callers: Which callers may invoke this tool.
````

### `ToolSearchToolBm25` { #ocai-anthropic-messages-wire-toolsearchtoolbm25 }

```python
class ToolSearchToolBm25(_Wire):
    name: str = 'tool_search_tool_bm25'
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    allowed_callers: list[str] | None = None
```

````text
The BM25 tool-search tool (`tool_search_tool_bm25_20251119`).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    name: Tool name; always `tool_search_tool_bm25`.
    cache_control: Optional cache breakpoint placed after this tool.
    strict: Whether to guarantee strict schema validation.
    defer_loading: Defer loading until referenced.
    allowed_callers: Which callers may invoke this tool.
````

### `ToolSearchToolRegex` { #ocai-anthropic-messages-wire-toolsearchtoolregex }

```python
class ToolSearchToolRegex(_Wire):
    name: str = 'tool_search_tool_regex'
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    allowed_callers: list[str] | None = None
```

````text
The regex tool-search tool (`tool_search_tool_regex_20251119`).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    name: Tool name; always `tool_search_tool_regex`.
    cache_control: Optional cache breakpoint placed after this tool.
    strict: Whether to guarantee strict schema validation.
    defer_loading: Defer loading until referenced.
    allowed_callers: Which callers may invoke this tool.
````

### `ToolUnion` { #ocai-anthropic-messages-wire-toolunion }

```python
ToolUnion = Tool | BashTool | CodeExecutionTool | CodeExecutionTool20260120 | TextEditorTool | MemoryTool | WebSearchTool | BasicWebSearchTool | WebFetchTool | ToolSearchToolBm25 | ToolSearchToolRegex
```

### `ToolChoiceAuto` { #ocai-anthropic-messages-wire-toolchoiceauto }

```python
class ToolChoiceAuto(_Wire):
    disable_parallel_tool_use: bool | None = None
```

````text
`tool_choice` letting the model decide whether to call a tool.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    disable_parallel_tool_use: Cap the model to at most one tool call.
````

### `ToolChoiceAny` { #ocai-anthropic-messages-wire-toolchoiceany }

```python
class ToolChoiceAny(_Wire):
    disable_parallel_tool_use: bool | None = None
```

````text
`tool_choice` forcing the model to call some (any) tool.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    disable_parallel_tool_use: Force exactly one tool call.
````

### `ToolChoiceTool` { #ocai-anthropic-messages-wire-toolchoicetool }

```python
class ToolChoiceTool(_Wire):
    name: str
    disable_parallel_tool_use: bool | None = None
```

````text
`tool_choice` forcing a specific named tool.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    name: Name of the tool the model must call.
    disable_parallel_tool_use: Force exactly one tool call.
````

### `ToolChoiceNone` { #ocai-anthropic-messages-wire-toolchoicenone }

```python
class ToolChoiceNone(_Wire)
```

````text
`tool_choice` forbidding all tool use.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)
````

### `ToolChoice` { #ocai-anthropic-messages-wire-toolchoice }

```python
ToolChoice = ToolChoiceAuto | ToolChoiceAny | ToolChoiceTool | ToolChoiceNone
```

### `ThinkingConfigEnabled` { #ocai-anthropic-messages-wire-thinkingconfigenabled }

```python
class ThinkingConfigEnabled(_Wire):
    budget_tokens: int
    display: str | None = None
```

````text
Extended-thinking config with an explicit token budget.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    budget_tokens: Tokens reserved for internal reasoning (>=1024 and less
        than `max_tokens`).
    display: How thinking surfaces in the response (`summarized`/`omitted`).
````

### `ThinkingConfigDisabled` { #ocai-anthropic-messages-wire-thinkingconfigdisabled }

```python
class ThinkingConfigDisabled(_Wire)
```

````text
Extended-thinking config explicitly disabled.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)
````

### `ThinkingConfigAdaptive` { #ocai-anthropic-messages-wire-thinkingconfigadaptive }

```python
class ThinkingConfigAdaptive(_Wire):
    display: str | None = None
```

````text
Adaptive extended-thinking config (the model decides when to think).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    display: How thinking surfaces in the response (`summarized`/`omitted`).
````

### `ThinkingConfig` { #ocai-anthropic-messages-wire-thinkingconfig }

```python
ThinkingConfig = ThinkingConfigEnabled | ThinkingConfigDisabled | ThinkingConfigAdaptive
```

### `JSONOutputFormat` { #ocai-anthropic-messages-wire-jsonoutputformat }

```python
class JSONOutputFormat(_Wire):
    schema: dict[str, Any]
```

````text
A JSON-schema output format for structured outputs.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    schema: The JSON Schema the output must conform to.
````

### `OutputConfig` { #ocai-anthropic-messages-wire-outputconfig }

```python
class OutputConfig(_Wire):
    format: JSONOutputFormat | None = None
    effort: str | None = None
```

````text
The `output_config` controlling output format and effort.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    format: Structured-output format selector (a JSON schema).
    effort: Output-generation effort (`low`/`medium`/`high`/`xhigh`/`max`).
````

### `Metadata` { #ocai-anthropic-messages-wire-metadata }

```python
class Metadata(_Wire):
    user_id: str | None = None
```

````text
The request `metadata` object.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    user_id: An opaque external identifier for the end user (abuse
        detection); a uuid, hash, or other non-PII id.
````

### `MessagesRequest` { #ocai-anthropic-messages-wire-messagesrequest }

```python
class MessagesRequest(_Wire):
    model: str
    max_tokens: int
    messages: list[MessageParam]
    system: str | list[TextBlockParam] | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    stop_sequences: list[str] | None = None
    stream: bool | None = None
    thinking: ThinkingConfig | None = None
    tool_choice: ToolChoice | None = None
    tools: list[ToolUnion] | None = None
    metadata: Metadata | None = None
    output_config: OutputConfig | None = None
    service_tier: str | None = None
    container: str | None = None
    inference_geo: str | None = None
```

````text
A `POST /v1/messages` request body.

Models Anthropic's documented, stable request fields; newer/rare knobs are
not enumerated and instead survive via the codec's extras sweep (module
docstring).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    model: The model that will complete the prompt (e.g. `claude-opus-4-6`).
    max_tokens: Maximum tokens to generate before stopping.
    messages: The conversation so far, as alternating-role messages.
    system: System prompt — a string or an array of text blocks.
    temperature: Sampling randomness (0.0..1.0).
    top_p: Nucleus-sampling probability mass.
    top_k: Sample only from the top K tokens.
    stop_sequences: Custom sequences that stop generation.
    stream: Whether to stream the response as server-sent events.
    thinking: Extended-thinking configuration.
    tool_choice: Whether/which tool the model must use.
    tools: Tool definitions the model may use.
    metadata: Request metadata (e.g. `user_id`).
    output_config: Structured-output / effort configuration.
    service_tier: Capacity preference (`auto` or `standard_only`).
    container: Container identifier to reuse across requests.
    inference_geo: Geographic region preference for inference.
````

### `CitationCharLocation` { #ocai-anthropic-messages-wire-citationcharlocation }

```python
class CitationCharLocation(_Wire):
    cited_text: str
    document_index: int
    start_char_index: int
    end_char_index: int
    document_title: str | None = None
    file_id: str | None = None
```

````text
A citation referencing a character range of a document.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    cited_text: The quoted source text.
    document_index: Index of the cited document in the request.
    document_title: Title of the cited document, if any.
    start_char_index: Inclusive start character offset.
    end_char_index: Exclusive end character offset.
    file_id: Id of the cited file, if sourced from the Files API.
````

### `CitationPageLocation` { #ocai-anthropic-messages-wire-citationpagelocation }

```python
class CitationPageLocation(_Wire):
    cited_text: str
    document_index: int
    start_page_number: int
    end_page_number: int
    document_title: str | None = None
    file_id: str | None = None
```

````text
A citation referencing a page range of a document.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    cited_text: The quoted source text.
    document_index: Index of the cited document in the request.
    document_title: Title of the cited document, if any.
    start_page_number: Inclusive start page number.
    end_page_number: Exclusive end page number.
    file_id: Id of the cited file, if sourced from the Files API.
````

### `CitationContentBlockLocation` { #ocai-anthropic-messages-wire-citationcontentblocklocation }

```python
class CitationContentBlockLocation(_Wire):
    cited_text: str
    document_index: int
    start_block_index: int
    end_block_index: int
    document_title: str | None = None
    file_id: str | None = None
```

````text
A citation referencing a content-block range of a document.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    cited_text: The quoted source text.
    document_index: Index of the cited document in the request.
    document_title: Title of the cited document, if any.
    start_block_index: Inclusive start content-block index.
    end_block_index: Exclusive end content-block index.
    file_id: Id of the cited file, if sourced from the Files API.
````

### `CitationWebSearchResultLocation` { #ocai-anthropic-messages-wire-citationwebsearchresultlocation }

```python
class CitationWebSearchResultLocation(_Wire):
    cited_text: str
    url: str
    encrypted_index: str
    title: str | None = None
```

````text
A citation referencing a web-search result.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    cited_text: The quoted source text.
    url: URL of the cited web result.
    title: Title of the cited web result.
    encrypted_index: Opaque index used to resolve the cited result.
````

### `CitationSearchResultLocation` { #ocai-anthropic-messages-wire-citationsearchresultlocation }

```python
class CitationSearchResultLocation(_Wire):
    cited_text: str
    source: str
    search_result_index: int
    start_block_index: int
    end_block_index: int
    title: str | None = None
```

````text
A citation referencing a supplied `search_result` block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    cited_text: The quoted source text.
    source: Source identifier of the cited search result.
    title: Title of the cited search result, if any.
    search_result_index: Index of the cited search-result block.
    start_block_index: Inclusive start content-block index.
    end_block_index: Exclusive end content-block index.
````

### `TextCitation` { #ocai-anthropic-messages-wire-textcitation }

```python
TextCitation = CitationCharLocation | CitationPageLocation | CitationContentBlockLocation | CitationWebSearchResultLocation | CitationSearchResultLocation
```

### `TextBlock` { #ocai-anthropic-messages-wire-textblock }

```python
class TextBlock(_Wire):
    text: str
    citations: list[TextCitation] | None = None
```

````text
A `text` content block in a response.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    text: The generated text.
    citations: Citations supporting this text, if citation was enabled.
````

### `ThinkingBlock` { #ocai-anthropic-messages-wire-thinkingblock }

```python
class ThinkingBlock(_Wire):
    thinking: str
    signature: str | None = None
```

````text
A `thinking` content block in a response.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    thinking: The internal reasoning text.
    signature: Signature verifying the block across turns.
````

### `RedactedThinkingBlock` { #ocai-anthropic-messages-wire-redactedthinkingblock }

```python
class RedactedThinkingBlock(_Wire):
    data: str
```

````text
A `redacted_thinking` content block in a response.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    data: The redacted, encrypted reasoning payload.
````

### `ToolUseBlock` { #ocai-anthropic-messages-wire-tooluseblock }

```python
class ToolUseBlock(_Wire):
    id: str
    name: str
    input: dict[str, Any]
    caller: Caller | None = None
```

````text
A `tool_use` content block in a response (the model's tool call).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    id: Identifier of this tool call, echoed by the `tool_result`.
    name: Name of the tool the model is calling.
    input: The tool input object the model produced.
    caller: Who invoked the tool (the model directly, or a server tool).
````

### `ServerToolUseBlock` { #ocai-anthropic-messages-wire-servertooluseblock }

```python
class ServerToolUseBlock(_Wire):
    id: str
    name: str
    input: dict[str, Any]
    caller: Caller | None = None
```

````text
A `server_tool_use` content block in a response.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    id: Identifier of this server-tool invocation.
    name: Server tool name (`web_search`, `web_fetch`, `code_execution`, …).
    input: The tool input object.
    caller: Who invoked the tool.
````

### `WebSearchResultBlock` { #ocai-anthropic-messages-wire-websearchresultblock }

```python
class WebSearchResultBlock(_Wire):
    title: str
    url: str
    encrypted_content: str
    page_age: str | None = None
```

````text
A single web-search result inside a `web_search_tool_result` block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    title: Result title.
    url: Result URL.
    encrypted_content: Opaque encrypted result content for follow-up.
    page_age: Approximate age of the page, if known.
````

### `WebSearchToolResultError` { #ocai-anthropic-messages-wire-websearchtoolresulterror }

```python
class WebSearchToolResultError(_Wire):
    error_code: str
```

````text
An error payload inside a `web_search_tool_result` block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    error_code: Machine-readable failure code (e.g. `max_uses_exceeded`).
````

### `WebSearchToolResultBlock` { #ocai-anthropic-messages-wire-websearchtoolresultblock }

```python
class WebSearchToolResultBlock(_Wire):
    tool_use_id: str
    content: list[WebSearchResultBlock] | WebSearchToolResultError
    caller: Caller | None = None
```

````text
A `web_search_tool_result` content block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    tool_use_id: Id of the `server_tool_use` block this answers.
    content: Either the list of results, or an error payload.
    caller: Who invoked the originating tool.
````

### `WebFetchBlock` { #ocai-anthropic-messages-wire-webfetchblock }

```python
class WebFetchBlock(_Wire):
    url: str
    content: DocumentBlock
    retrieved_at: str | None = None
```

````text
The fetched-content payload inside a `web_fetch_tool_result` block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    url: The URL that was fetched.
    retrieved_at: When the content was retrieved.
    content: The fetched content as a document block.
````

### `WebFetchToolResultError` { #ocai-anthropic-messages-wire-webfetchtoolresulterror }

```python
class WebFetchToolResultError(_Wire):
    error_code: str
```

````text
An error payload inside a `web_fetch_tool_result` block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    error_code: Machine-readable failure code (e.g. `url_not_allowed`).
````

### `WebFetchToolResultBlock` { #ocai-anthropic-messages-wire-webfetchtoolresultblock }

```python
class WebFetchToolResultBlock(_Wire):
    tool_use_id: str
    content: WebFetchBlock | WebFetchToolResultError
    caller: Caller | None = None
```

````text
A `web_fetch_tool_result` content block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    tool_use_id: Id of the `server_tool_use` block this answers.
    content: Either the fetched content, or an error payload.
    caller: Who invoked the originating tool.
````

### `CodeExecutionOutputBlock` { #ocai-anthropic-messages-wire-codeexecutionoutputblock }

```python
class CodeExecutionOutputBlock(_Wire):
    file_id: str
```

````text
A file output emitted by a code-execution run.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    file_id: Id of the produced output file.
````

### `CodeExecutionResultBlock` { #ocai-anthropic-messages-wire-codeexecutionresultblock }

```python
class CodeExecutionResultBlock(_Wire):
    stdout: str
    stderr: str
    return_code: int
    content: list[CodeExecutionOutputBlock] | None = None
```

````text
A successful `code_execution` result payload.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    stdout: Captured standard output.
    stderr: Captured standard error.
    return_code: Process exit code.
    content: Output file blocks produced by the run.
````

### `CodeExecutionToolResultError` { #ocai-anthropic-messages-wire-codeexecutiontoolresulterror }

```python
class CodeExecutionToolResultError(_Wire):
    error_code: str
```

````text
An error payload inside a `code_execution_tool_result` block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    error_code: Machine-readable failure code (e.g. `execution_time_exceeded`).
````

### `CodeExecutionToolResultBlock` { #ocai-anthropic-messages-wire-codeexecutiontoolresultblock }

```python
class CodeExecutionToolResultBlock(_Wire):
    tool_use_id: str
    content: CodeExecutionResultBlock | CodeExecutionToolResultError
```

````text
A `code_execution_tool_result` content block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    tool_use_id: Id of the `server_tool_use` block this answers.
    content: Either the execution result, or an error payload.
````

### `BashCodeExecutionResultBlock` { #ocai-anthropic-messages-wire-bashcodeexecutionresultblock }

```python
class BashCodeExecutionResultBlock(_Wire):
    stdout: str
    stderr: str
    return_code: int
    content: list[CodeExecutionOutputBlock] | None = None
```

````text
A successful `bash_code_execution` result payload.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    stdout: Captured standard output.
    stderr: Captured standard error.
    return_code: Process exit code.
    content: Output file blocks produced by the run.
````

### `BashCodeExecutionToolResultError` { #ocai-anthropic-messages-wire-bashcodeexecutiontoolresulterror }

```python
class BashCodeExecutionToolResultError(_Wire):
    error_code: str
```

````text
An error payload inside a `bash_code_execution_tool_result` block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    error_code: Machine-readable failure code (e.g. `output_file_too_large`).
````

### `BashCodeExecutionToolResultBlock` { #ocai-anthropic-messages-wire-bashcodeexecutiontoolresultblock }

```python
class BashCodeExecutionToolResultBlock(_Wire):
    tool_use_id: str
    content: BashCodeExecutionResultBlock | BashCodeExecutionToolResultError
```

````text
A `bash_code_execution_tool_result` content block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    tool_use_id: Id of the `server_tool_use` block this answers.
    content: Either the execution result, or an error payload.
````

### `TextEditorViewResultBlock` { #ocai-anthropic-messages-wire-texteditorviewresultblock }

```python
class TextEditorViewResultBlock(_Wire):
    content: str
    file_type: str
    start_line: int | None = None
    num_lines: int | None = None
    total_lines: int | None = None
```

````text
A text-editor `view` result.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    content: The viewed file content.
    file_type: Kind of file viewed (`text`, `image`, or `pdf`).
    start_line: First line shown, if a range was requested.
    num_lines: Number of lines shown.
    total_lines: Total lines in the file.
````

### `TextEditorCreateResultBlock` { #ocai-anthropic-messages-wire-texteditorcreateresultblock }

```python
class TextEditorCreateResultBlock(_Wire):
    is_file_update: bool
```

````text
A text-editor `create` result.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    is_file_update: Whether the create overwrote an existing file.
````

### `TextEditorStrReplaceResultBlock` { #ocai-anthropic-messages-wire-texteditorstrreplaceresultblock }

```python
class TextEditorStrReplaceResultBlock(_Wire):
    old_start: int | None = None
    old_lines: int | None = None
    new_start: int | None = None
    new_lines: int | None = None
    lines: list[str] | None = None
```

````text
A text-editor `str_replace` result (the applied diff hunk).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    old_start: Start line of the replaced region.
    old_lines: Number of lines replaced.
    new_start: Start line of the inserted region.
    new_lines: Number of lines inserted.
    lines: The resulting line context.
````

### `TextEditorToolResultError` { #ocai-anthropic-messages-wire-texteditortoolresulterror }

```python
class TextEditorToolResultError(_Wire):
    error_code: str
    error_message: str | None = None
```

````text
An error payload inside a `text_editor_code_execution_tool_result` block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    error_code: Machine-readable failure code (e.g. `file_not_found`).
    error_message: Human-readable error message.
````

### `TextEditorToolResultBlock` { #ocai-anthropic-messages-wire-texteditortoolresultblock }

```python
class TextEditorToolResultBlock(_Wire):
    tool_use_id: str
    content: TextEditorViewResultBlock | TextEditorCreateResultBlock | TextEditorStrReplaceResultBlock | TextEditorToolResultError
```

````text
A `text_editor_code_execution_tool_result` content block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    tool_use_id: Id of the `server_tool_use` block this answers.
    content: A view/create/str_replace result, or an error payload.
````

### `ToolReferenceBlock` { #ocai-anthropic-messages-wire-toolreferenceblock }

```python
class ToolReferenceBlock(_Wire):
    name: str
```

````text
A tool reference surfaced by tool-search.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    name: Name of the referenced tool.
````

### `ToolSearchToolSearchResultBlock` { #ocai-anthropic-messages-wire-toolsearchtoolsearchresultblock }

```python
class ToolSearchToolSearchResultBlock(_Wire):
    tool_references: list[ToolReferenceBlock]
```

````text
A successful tool-search result payload.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    tool_references: The tools the search surfaced.
````

### `ToolSearchToolResultError` { #ocai-anthropic-messages-wire-toolsearchtoolresulterror }

```python
class ToolSearchToolResultError(_Wire):
    error_code: str
    error_message: str | None = None
```

````text
An error payload inside a `tool_search_tool_result` block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    error_code: Machine-readable failure code.
    error_message: Human-readable error message.
````

### `ToolSearchToolResultBlock` { #ocai-anthropic-messages-wire-toolsearchtoolresultblock }

```python
class ToolSearchToolResultBlock(_Wire):
    tool_use_id: str
    content: ToolSearchToolSearchResultBlock | ToolSearchToolResultError
```

````text
A `tool_search_tool_result` content block.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    tool_use_id: Id of the `server_tool_use` block this answers.
    content: Either the surfaced tool references, or an error payload.
````

### `ContainerUploadBlock` { #ocai-anthropic-messages-wire-containeruploadblock }

```python
class ContainerUploadBlock(_Wire):
    file_id: str
```

````text
A `container_upload` content block referencing an uploaded file.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    file_id: Id of the uploaded file in the container.
````

### `DocumentBlock` { #ocai-anthropic-messages-wire-documentblock }

```python
class DocumentBlock(_Wire):
    source: DocumentSource
    title: str | None = None
    citations: CitationsConfig | None = None
```

````text
A `document` content block returned inside a web-fetch result.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    source: The document source.
    title: Optional document title.
    citations: Optional citation configuration.
````

### `ContentBlock` { #ocai-anthropic-messages-wire-contentblock }

```python
ContentBlock = TextBlock | ThinkingBlock | RedactedThinkingBlock | ToolUseBlock | ServerToolUseBlock | WebSearchToolResultBlock | WebFetchToolResultBlock | CodeExecutionToolResultBlock | BashCodeExecutionToolResultBlock | TextEditorToolResultBlock | ToolSearchToolResultBlock | ContainerUploadBlock
```

### `DirectCaller` { #ocai-anthropic-messages-wire-directcaller }

```python
class DirectCaller(_Wire)
```

````text
A tool invoked directly by the model.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)
````

### `ServerToolCaller` { #ocai-anthropic-messages-wire-servertoolcaller }

```python
class ServerToolCaller(_Wire):
    tool_id: str
```

````text
A tool invoked from server-side code execution (`code_execution_20250825`).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    tool_id: Id of the server tool that invoked this call.
````

### `ServerToolCaller20260120` { #ocai-anthropic-messages-wire-servertoolcaller20260120 }

```python
class ServerToolCaller20260120(_Wire):
    tool_id: str
```

````text
A tool invoked from server-side code execution (`code_execution_20260120`).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    tool_id: Id of the server tool that invoked this call.
````

### `Caller` { #ocai-anthropic-messages-wire-caller }

```python
Caller = DirectCaller | ServerToolCaller | ServerToolCaller20260120
```

### `CacheCreation` { #ocai-anthropic-messages-wire-cachecreation }

```python
class CacheCreation(_Wire):
    ephemeral_5m_input_tokens: int | None = None
    ephemeral_1h_input_tokens: int | None = None
```

````text
Breakdown of cache-creation input tokens by TTL.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    ephemeral_5m_input_tokens: Tokens written to the 5-minute cache.
    ephemeral_1h_input_tokens: Tokens written to the 1-hour cache.
````

### `OutputTokensDetails` { #ocai-anthropic-messages-wire-outputtokensdetails }

```python
class OutputTokensDetails(_Wire):
    thinking_tokens: int | None = None
```

````text
Breakdown of output tokens by category.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    thinking_tokens: Output tokens spent on extended thinking.
````

### `ServerToolUsage` { #ocai-anthropic-messages-wire-servertoolusage }

```python
class ServerToolUsage(_Wire):
    web_search_requests: int | None = None
    web_fetch_requests: int | None = None
```

````text
Counts of server-tool requests billed on the response.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    web_search_requests: Number of web-search requests issued.
    web_fetch_requests: Number of web-fetch requests issued.
````

### `Usage` { #ocai-anthropic-messages-wire-usage }

```python
class Usage(_Wire):
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    cache_creation: CacheCreation | None = None
    output_tokens_details: OutputTokensDetails | None = None
    server_tool_use: ServerToolUsage | None = None
    service_tier: str | None = None
    inference_geo: str | None = None
```

````text
Token usage and billing detail on the response (and `message_delta`).

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    input_tokens: Input tokens consumed.
    output_tokens: Output tokens generated.
    cache_creation_input_tokens: Input tokens written to the prompt cache.
    cache_read_input_tokens: Input tokens served from the prompt cache.
    cache_creation: Per-TTL cache-creation breakdown.
    output_tokens_details: Per-category output-token breakdown.
    server_tool_use: Server-tool request counts.
    service_tier: Tier that served the request (`standard`/`priority`/`batch`).
    inference_geo: Region where inference ran.
````

### `RefusalStopDetails` { #ocai-anthropic-messages-wire-refusalstopdetails }

```python
class RefusalStopDetails(_Wire):
    category: str | None = None
    explanation: str | None = None
```

````text
Structured refusal information on a response.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    category: Policy category that triggered the refusal (`cyber`/`bio`/
        `reasoning_extraction`).
    explanation: Human-readable explanation of the refusal.
````

### `Container` { #ocai-anthropic-messages-wire-container }

```python
class Container(_Wire):
    id: str
    expires_at: str | None = None
```

````text
Container info attached to a response when a container was used.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    id: Container identifier.
    expires_at: ISO-8601 timestamp when the container expires.
````

### `Message` { #ocai-anthropic-messages-wire-message }

```python
class Message(_Wire):
    id: str
    role: str
    model: str
    content: list[ContentBlock]
    type: str = 'message'
    stop_reason: str | None = None
    stop_sequence: str | None = None
    stop_details: RefusalStopDetails | None = None
    usage: Usage | None = None
    container: Container | None = None
```

````text
A `POST /v1/messages` (non-streaming) response body.

Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

Attributes:
    id: Unique message identifier.
    type: Object type discriminator; always `message`.
    role: Author role; always `assistant`.
    model: Model that produced the message.
    content: The generated content blocks.
    stop_reason: Why generation stopped (`end_turn`, `max_tokens`,
        `stop_sequence`, `tool_use`, `pause_turn`, `refusal`).
    stop_sequence: The custom stop sequence that was hit, if any.
    stop_details: Structured stop detail (e.g. refusal information).
    usage: Token usage and billing detail.
    container: Container info, when a container was used.
````

### `ContentBlockDeltaText` { #ocai-anthropic-messages-wire-contentblockdeltatext }

```python
class ContentBlockDeltaText(_Wire):
    text: str
```

````text
A `text_delta` inside a `content_block_delta` event.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

Attributes:
    text: A fragment of generated text to concatenate.
````

### `ContentBlockDeltaInputJson` { #ocai-anthropic-messages-wire-contentblockdeltainputjson }

```python
class ContentBlockDeltaInputJson(_Wire):
    partial_json: str
```

````text
An `input_json_delta` inside a `content_block_delta` event.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

Attributes:
    partial_json: A partial JSON string fragment of the tool `input` to
        accumulate; the final `input` is always an object.
````

### `ContentBlockDeltaThinking` { #ocai-anthropic-messages-wire-contentblockdeltathinking }

```python
class ContentBlockDeltaThinking(_Wire):
    thinking: str
```

````text
A `thinking_delta` inside a `content_block_delta` event.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

Attributes:
    thinking: A fragment of extended-thinking text to concatenate.
````

### `ContentBlockDeltaSignature` { #ocai-anthropic-messages-wire-contentblockdeltasignature }

```python
class ContentBlockDeltaSignature(_Wire):
    signature: str
```

````text
A `signature_delta` inside a `content_block_delta` event.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

Attributes:
    signature: The thinking-block signature (sent just before stop).
````

### `ContentBlockDeltaCitations` { #ocai-anthropic-messages-wire-contentblockdeltacitations }

```python
class ContentBlockDeltaCitations(_Wire):
    citation: TextCitation
```

````text
A `citations_delta` inside a `content_block_delta` event.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

Attributes:
    citation: A single citation appended to the text block.
````

### `ContentBlockDelta` { #ocai-anthropic-messages-wire-contentblockdelta }

```python
ContentBlockDelta = ContentBlockDeltaText | ContentBlockDeltaInputJson | ContentBlockDeltaThinking | ContentBlockDeltaSignature | ContentBlockDeltaCitations
```

### `MessageStartEvent` { #ocai-anthropic-messages-wire-messagestartevent }

```python
class MessageStartEvent(_Wire):
    message: Message
```

````text
The `message_start` event opening a stream.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

Attributes:
    message: The initial `Message` with empty `content`.
````

### `ContentBlockStartEvent` { #ocai-anthropic-messages-wire-contentblockstartevent }

```python
class ContentBlockStartEvent(_Wire):
    index: int
    content_block: ContentBlock
```

````text
A `content_block_start` event opening a content block.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

Attributes:
    index: Index of the block in the final `content` array.
    content_block: The initial (empty) content block being opened.
````

### `ContentBlockDeltaEvent` { #ocai-anthropic-messages-wire-contentblockdeltaevent }

```python
class ContentBlockDeltaEvent(_Wire):
    index: int
    delta: ContentBlockDelta
```

````text
A `content_block_delta` event updating a content block.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

Attributes:
    index: Index of the block being updated.
    delta: The incremental update (text/json/thinking/signature/citation).
````

### `ContentBlockStopEvent` { #ocai-anthropic-messages-wire-contentblockstopevent }

```python
class ContentBlockStopEvent(_Wire):
    index: int
```

````text
A `content_block_stop` event closing a content block.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

Attributes:
    index: Index of the block being closed.
````

### `MessageDeltaInfo` { #ocai-anthropic-messages-wire-messagedeltainfo }

```python
class MessageDeltaInfo(_Wire):
    stop_reason: str | None = None
    stop_sequence: str | None = None
```

````text
The top-level `delta` carried by a `message_delta` event.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

Attributes:
    stop_reason: Final stop reason, set as the message completes.
    stop_sequence: Custom stop sequence that was hit, if any.
````

### `MessageDeltaEvent` { #ocai-anthropic-messages-wire-messagedeltaevent }

```python
class MessageDeltaEvent(_Wire):
    delta: MessageDeltaInfo
    usage: Usage | None = None
```

````text
A `message_delta` event carrying top-level Message changes.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

Attributes:
    delta: The top-level field updates (`stop_reason`, `stop_sequence`).
    usage: Cumulative token usage for the message so far.
````

### `MessageStopEvent` { #ocai-anthropic-messages-wire-messagestopevent }

```python
class MessageStopEvent(_Wire)
```

````text
The `message_stop` event ending a stream.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)
````

### `PingEvent` { #ocai-anthropic-messages-wire-pingevent }

```python
class PingEvent(_Wire)
```

````text
A `ping` keep-alive event, dispersed throughout a stream.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)
````

### `StreamError` { #ocai-anthropic-messages-wire-streamerror }

```python
class StreamError(_Wire):
    type: str
    message: str | None = None
```

````text
The `error` object inside an `error` stream event.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

Attributes:
    type: Error type (e.g. `overloaded_error`).
    message: Human-readable error message.
````

### `ErrorEvent` { #ocai-anthropic-messages-wire-errorevent }

```python
class ErrorEvent(_Wire):
    error: StreamError
```

````text
An `error` event the API may emit mid-stream.

Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

Attributes:
    error: The error payload.
````

### `StreamEvent` { #ocai-anthropic-messages-wire-streamevent }

```python
StreamEvent = MessageStartEvent | ContentBlockStartEvent | ContentBlockDeltaEvent | ContentBlockStopEvent | MessageDeltaEvent | MessageStopEvent | PingEvent | ErrorEvent
```
