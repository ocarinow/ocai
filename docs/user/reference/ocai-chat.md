# `ocai.chat` API reference

Generated from the checked-out package sources. Signatures, declared fields,
methods, type aliases and explicit re-exports are checked for drift. Inherited
members follow their named base class; a type's presence does not establish
provider execution support. See [supported features](../provider-feature-matrix.md).

## `ocai.chat`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-chat-canonical-chat-chunk"></span>`CANONICAL_CHAT_CHUNK` | [`ocai.chat.canonical.CANONICAL_CHAT_CHUNK`](ocai-chat.md#ocai-chat-canonical-canonical-chat-chunk) |
| <span id="ocai-chat-canonical-chat-request"></span>`CANONICAL_CHAT_REQUEST` | [`ocai.chat.canonical.CANONICAL_CHAT_REQUEST`](ocai-chat.md#ocai-chat-canonical-canonical-chat-request) |
| <span id="ocai-chat-canonical-chat-response"></span>`CANONICAL_CHAT_RESPONSE` | [`ocai.chat.canonical.CANONICAL_CHAT_RESPONSE`](ocai-chat.md#ocai-chat-canonical-canonical-chat-response) |
| <span id="ocai-chat-ocai-interface"></span>`OCAI_INTERFACE` | [`ocai.chat.canonical.OCAI_INTERFACE`](ocai-chat.md#ocai-chat-canonical-ocai-interface) |
| <span id="ocai-chat-revision"></span>`REVISION` | [`ocai.chat.canonical.REVISION`](ocai-chat.md#ocai-chat-canonical-revision) |
| <span id="ocai-chat-wirechatmodel"></span>`WireChatModel` | [`ocai.chat.facade.WireChatModel`](ocai-chat.md#ocai-chat-facade-wirechatmodel) |
| <span id="ocai-chat-chatmodel"></span>`ChatModel` | [`ocai.chat.protocol.ChatModel`](ocai-chat.md#ocai-chat-protocol-chatmodel) |
| <span id="ocai-chat-asyncchatstream"></span>`AsyncChatStream` | [`ocai.chat.types.stream.AsyncChatStream`](ocai-chat.md#ocai-chat-types-stream-asyncchatstream) |
| <span id="ocai-chat-chatchunk"></span>`ChatChunk` | [`ocai.chat.types.stream.ChatChunk`](ocai-chat.md#ocai-chat-types-stream-chatchunk) |
| <span id="ocai-chat-chatconfig"></span>`ChatConfig` | [`ocai.chat.types.config.ChatConfig`](ocai-chat.md#ocai-chat-types-config-chatconfig) |
| <span id="ocai-chat-chatrequest"></span>`ChatRequest` | [`ocai.chat.types.request.ChatRequest`](ocai-chat.md#ocai-chat-types-request-chatrequest) |
| <span id="ocai-chat-chatresponse"></span>`ChatResponse` | [`ocai.chat.types.response.ChatResponse`](ocai-chat.md#ocai-chat-types-response-chatresponse) |
| <span id="ocai-chat-chatstream"></span>`ChatStream` | [`ocai.chat.types.stream.ChatStream`](ocai-chat.md#ocai-chat-types-stream-chatstream) |
| <span id="ocai-chat-finishinfo"></span>`FinishInfo` | [`ocai.core.finish.FinishInfo`](ocai-core.md#ocai-core-finish-finishinfo) |
| <span id="ocai-chat-message"></span>`Message` | [`ocai.chat.types.message.Message`](ocai-chat.md#ocai-chat-types-message-message) |
| <span id="ocai-chat-part"></span>`Part` | [`ocai.chat.types.parts.Part`](ocai-chat.md#ocai-chat-types-parts-part) |
| <span id="ocai-chat-role"></span>`Role` | [`ocai.chat.types.role.Role`](ocai-chat.md#ocai-chat-types-role-role) |
| <span id="ocai-chat-servertool"></span>`ServerTool` | [`ocai.chat.types.tools.ServerTool`](ocai-chat.md#ocai-chat-types-tools-servertool) |
| <span id="ocai-chat-servertoollocation"></span>`ServerToolLocation` | [`ocai.chat.types.tools.ServerToolLocation`](ocai-chat.md#ocai-chat-types-tools-servertoollocation) |
| <span id="ocai-chat-streamaccumulator"></span>`StreamAccumulator` | [`ocai.chat.types.stream.StreamAccumulator`](ocai-chat.md#ocai-chat-types-stream-streamaccumulator) |
| <span id="ocai-chat-streamend"></span>`StreamEnd` | [`ocai.chat.types.stream.StreamEnd`](ocai-chat.md#ocai-chat-types-stream-streamend) |
| <span id="ocai-chat-streamoutcome"></span>`StreamOutcome` | [`ocai.core.result.StreamOutcome`](ocai-core.md#ocai-core-result-streamoutcome) |
| <span id="ocai-chat-tool"></span>`Tool` | [`ocai.chat.types.tools.Tool`](ocai-chat.md#ocai-chat-types-tools-tool) |
| <span id="ocai-chat-toolchoice"></span>`ToolChoice` | [`ocai.chat.types.tools.ToolChoice`](ocai-chat.md#ocai-chat-types-tools-toolchoice) |
| <span id="ocai-chat-tooldefinition"></span>`ToolDefinition` | [`ocai.chat.types.tools.ToolDefinition`](ocai-chat.md#ocai-chat-types-tools-tooldefinition) |
| <span id="ocai-chat-toolunknown"></span>`ToolUnknown` | [`ocai.chat.types.tools.ToolUnknown`](ocai-chat.md#ocai-chat-types-tools-toolunknown) |
| <span id="ocai-chat-usage"></span>`Usage` | [`ocai.core.usage.Usage`](ocai-core.md#ocai-core-usage-usage) |

### `model` { #ocai-chat-model }

```python
def model(spec: str, *, credentials: Credential, host: Host | str | None=None, catalog: Catalog | None=None, transport: Transport | SyncTransport | None=None, interceptors: Sequence[CallInterceptor]=(), policies: Sequence[WirePolicy]=(), observers: Sequence[Observer]=(), conversion_policy: FidelityPolicy | None=None, interface: str | None=None, tag: str | None=None) -> WireChatModel | InterceptedChatModel | ObservedChatModel
```

````text
Build a chat model from one spec string — the §3.4 core front door.

The whole provider+model choice is ONE data value
(`model(os.environ["OCAI_MODEL"], ...)` — switching providers is a
deployment change, zero code):

```python
import ocai.chat
from ocai.core import ApiKey

chat = ocai.chat.model("openai/gpt-5", credentials=ApiKey.from_env("OPENAI_API_KEY"))
res = chat.chat(ChatRequest(messages=[Message.user("hello")]))
```

The factory resolves the provider against the catalog, builds the codec
from the serving fragment's registered component factory, composes the
`Binding` internally (a `Direct` host at the fragment's declared
first-party origin unless `host` is passed), and binds the model name to
the returned object — requests stay pure conversation. Unpinned
resolution considers only interfaces the catalog can actually *serve*
(those with a registered chat component); a nodes-only stub interface is
reachable by explicit `interface=` pin only.

Everything composed here is reachable by hand (`WireChatModel` + a
`Binding` + a `Catalog`); this door adds nothing a power user cannot
build — and the plugin `chat_model` helpers are sugar over exactly this
path, never a separate one.

Args:
    spec: The model spec `"<provider>/<model>"` (the LiteLLM/OpenRouter
        convention). Split on the FIRST slash only — the model part may
        itself contain slashes (`"openai/meta-llama/Llama-3.3-70B"` on a
        vLLM gateway). The spec never carries an interface; pinning is
        the `interface`/`tag` kwargs.
    credentials: The credential the driver applies at the leaf, per
        attempt. Required — there is no ambient discovery (rule 13).
    host: A hosting target, a host name explicitly declared in the catalog,
        or None for first-party `Direct` at the dialect's declared origin.
    catalog: The governed conversion catalog, or None for the
        entry-point-discovered `default_catalog()`.
    transport: The wire transport, or None for a fresh `HttpxTransport`.
    interceptors: The port-tier chain wrapped around the facade,
        outermost first; empty for the bare facade.
    conversion_policy: Caller-defined acceptance over field losses and shifts.
    observers: Authorized passive metadata-only lifecycle observers.
    policies: The wire-tier hooks (retry, rate-limit, wiretap) the
        drivers consult on every attempt, in order.
    interface: An interface pin (e.g. `"chat_completions"`), or None to
        let the catalog choose among serveable interfaces.
    tag: A revision-tag pin, or None for latest eligible.

Returns:
    A composed `ChatModel` bound to the parsed model name.

Raises:
    ValueError: If `spec` is not of the `"<provider>/<model>"` form.
    ResolutionError: If the provider is not in the catalog (the message
        names the providers that are), or no serveable interface
        matches the pins.
    LookupError: If a pinned interface has no registered component
        factory (a declared stub, or a missing plugin distribution).
    CompositionError: If the dialect declares no first-party endpoint
        and no explicit `host` was given.
````

## `ocai.chat.canonical`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/canonical.py)

### `OCAI_INTERFACE` { #ocai-chat-canonical-ocai-interface }

```python
OCAI_INTERFACE: Final[str] = CANONICAL_INTERFACE
```

### `REVISION` { #ocai-chat-canonical-revision }

```python
REVISION: Final[str] = CANONICAL_REVISION
```

### `CANONICAL_CHAT_REQUEST` { #ocai-chat-canonical-canonical-chat-request }

```python
CANONICAL_CHAT_REQUEST: Final[NodeId] = canonical_node(CHAT_REQUEST, REVISION)
```

### `CANONICAL_CHAT_RESPONSE` { #ocai-chat-canonical-canonical-chat-response }

```python
CANONICAL_CHAT_RESPONSE: Final[NodeId] = canonical_node(CHAT_RESPONSE, REVISION)
```

### `CANONICAL_CHAT_CHUNK` { #ocai-chat-canonical-canonical-chat-chunk }

```python
CANONICAL_CHAT_CHUNK: Final[NodeId] = canonical_node(CHAT_CHUNK, REVISION)
```

## `ocai.chat.facade`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/facade.py)

### `ChatCodec` { #ocai-chat-facade-chatcodec }

```python
class ChatCodec(Protocol):
    provider: str
    interface: str
    request_node: NodeId
    response_node: NodeId
    chunk_node: NodeId
```

````text
The dialect-codec surface a chat plugin ships, typed structurally.

What `ocai.openai.chat_completions.ChatCompletionsCodec` and
`ocai.anthropic.messages.MessagesCodec` actually share (§7): the
interface's identity (provider/interface labels and the three shape
nodes), the pure mapping halves (`encode_request` / `decode_response` /
`decode_event` — wrapped into graph edges by the plugin's fragment, so
the facade converts through the catalog and never calls them directly),
and the wire-hygiene members the facade *does* consult per call:
`native_path`, `dialect_traits`, `bind_resource`, and `map_error`.

The protocol's home is this module because the facade is the only core
consumer of the codec surface; plugins satisfy it structurally and never
import it.
````

#### `ChatCodec.native_path` { #ocai-chat-facade-chatcodec-native-path }

```python
def native_path(self, model: str) -> str
```

````text
Return the dialect's first-party URL path for a chat call.
````

#### `ChatCodec.dialect_traits` { #ocai-chat-facade-chatcodec-dialect-traits }

```python
def dialect_traits(self) -> DialectTraits
```

````text
Return the dialect's hosting traits, read by any `Host` as data.
````

#### `ChatCodec.bind_resource` { #ocai-chat-facade-chatcodec-bind-resource }

```python
def bind_resource(self, payload: dict[str, Any], resource: str) -> dict[str, Any]
```

````text
Inject the bound model name into an encoded wire payload.
````

#### `ChatCodec.bind_stream` { #ocai-chat-facade-chatcodec-bind-stream }

```python
def bind_stream(self, payload: dict[str, Any]) -> dict[str, Any]
```

````text
Mark an encoded wire payload as a streaming request.
````

#### `ChatCodec.encode_request` { #ocai-chat-facade-chatcodec-encode-request }

```python
def encode_request(self, request: ChatRequest) -> EdgeOutput
```

````text
Encode a canonical `ChatRequest` into this dialect's wire body.
````

#### `ChatCodec.decode_response` { #ocai-chat-facade-chatcodec-decode-response }

```python
def decode_response(self, payload: dict[str, Any]) -> EdgeOutput
```

````text
Decode this dialect's response body into a canonical `ChatResponse`.
````

#### `ChatCodec.decode_event` { #ocai-chat-facade-chatcodec-decode-event }

```python
def decode_event(self, event: str | None, data: str) -> ChatChunk | None
```

````text
Decode one SSE frame into a canonical `ChatChunk`, if it surfaces one.
````

#### `ChatCodec.map_error` { #ocai-chat-facade-chatcodec-map-error }

```python
def map_error(self, status: int | None, body: dict[str, Any] | None) -> OcaiError | None
```

````text
Refine a coarse taxonomy error from the provider's error body.
````

### `StalePreparationError` { #ocai-chat-facade-stalepreparationerror }

```python
class StalePreparationError(OcaiError)
```

````text
Prepared request or configuration changed; inspect and approve again.
````

### `PreparedChatCall` { #ocai-chat-facade-preparedchatcall }

```python
class PreparedChatCall
```

````text
A detached execution snapshot with public inspection and governed call faces.

Inspection and request properties return copies. Execution runs the original
snapshot, through the same middleware/observation composition that prepared it.
A handle is in-process, not a portable authorization token or durable job.
````

#### `PreparedChatCall.__init__` { #ocai-chat-facade-preparedchatcall---init-- }

```python
def __init__(self, request: ChatRequest, inspection: ExecutionInspection, model: ChatModel) -> None
```

````text
Build through a model's prepare method; callers inspect returned handles.
````

#### `PreparedChatCall.inspection` { #ocai-chat-facade-preparedchatcall-inspection }

```python
@property
def inspection(self) -> ExecutionInspection
```

````text
Return detached route, declarations, coverage and request findings.
````

#### `PreparedChatCall.request` { #ocai-chat-facade-preparedchatcall-request }

```python
@property
def request(self) -> ChatRequest
```

````text
Return a detached canonical request for admission and diagnostics.
````

#### `PreparedChatCall.wrap` { #ocai-chat-facade-preparedchatcall-wrap }

```python
def wrap(self, wrapper: Callable[[ChatModel], ChatModel]) -> PreparedChatCall
```

````text
Wrap the approved execution port while retaining its inspection snapshot.
````

#### `PreparedChatCall.chat` { #ocai-chat-facade-preparedchatcall-chat }

```python
def chat(self, *, ctx: CallContext | None=None) -> CallResult[ChatResponse]
```

````text
Execute the approved unary snapshot through its original governance chain.
````

#### `PreparedChatCall.achat` { #ocai-chat-facade-preparedchatcall-achat }

```python
async def achat(self, *, ctx: CallContext | None=None) -> CallResult[ChatResponse]
```

````text
Execute the approved unary snapshot asynchronously.
````

#### `PreparedChatCall.stream` { #ocai-chat-facade-preparedchatcall-stream }

```python
def stream(self, *, ctx: CallContext | None=None) -> ChatStream
```

````text
Execute the approved stream snapshot with explicit stream ownership.
````

#### `PreparedChatCall.astream` { #ocai-chat-facade-preparedchatcall-astream }

```python
async def astream(self, *, ctx: CallContext | None=None) -> AsyncChatStream
```

````text
Execute the approved stream snapshot asynchronously.
````

### `WireChatModel` { #ocai-chat-facade-wirechatmodel }

```python
class WireChatModel
```

````text
The wire-backed `ChatModel`: codec + binding + catalog behind the port.

Satisfies the `ChatModel` protocol structurally. Local adapters are its
peers, not its subclasses — anything this facade returns (`CallResult`
with a `Route` whose `host` names the physical destination) an
in-process adapter can return too (`route.host = "in-process"`), which
is what keeps the interceptor tier implementation-agnostic.

Both §3.4 front doors resolve to this class: the core string door
(`ocai.chat.model(provider, model_name, ...)`) and the plugin sugar
(`ocai.openai.chat_model(model_name, ...)`) each bind the model name
HERE, at construction. Switching provider — or model — is building a
new facade; the `ChatRequest`s replay unchanged.
````

#### `WireChatModel.__init__` { #ocai-chat-facade-wirechatmodel---init-- }

```python
def __init__(self, codec: ChatCodec, binding: Binding, catalog: Catalog, *, model_name: str, interface: str | None=None, tag: str | None=None, policies: Sequence[WirePolicy]=(), strict: bool=False, attempt_observers: Sequence[Observer]=(), conversion_policy: FidelityPolicy | None=None) -> None
```

````text
Compose the facade from its three values and the bound resource.

Args:
    codec: The dialect codec for the target provider interface —
        the `ChatCodec` surface the plugin ships (architecture §7).
    binding: The remote nucleus: host, credentials, transport, and
        headers. `binding.validate()` is expected to have checked
        sync/async coherence at composition time.
    catalog: The governed conversion catalog used to resolve the
        target `NodeId` and plan every conversion leg; its lockfile
        hash lands in each call's `Route`.
    model_name: The bound resource (§3.4): the provider-specific
        model name every call targets. Becomes
        `EndpointSpec.resource` and is injected into each encoded
        wire payload via the codec's `bind_resource` — requests
        never carry it.
    interface: The provider interface to pin, or None to pin the
        codec's own interface — the facade is composed *of* a
        dialect, so resolution can never wander onto a wire the
        codec does not speak (letting the catalog choose freely is
        the §3.4 front doors' job: they resolve first, then build
        the matching codec from the fragment's component factory).
    tag: The interface revision tag to pin, or None for latest
        eligible.
    policies: The wire-tier hooks (retry, rate-limit, wiretap) the
        drivers consult on every attempt, in order.
    conversion_policy: Enforce field and semantic acceptance before I/O
        and after response conversion; stream output cannot be retracted.
    attempt_observers: Physical-attempt metadata observers. Wrap this
        model in ObservedChatModel for logical invocation events; the
        core model factory composes both automatically.
    strict: The feature-gate mode (§2.5). False (annotate, the
        default): a request feature the destination's
        `CapabilityProfile` declares `ABSENT` is recorded as an
        `UNSUPPORTED` field loss on the call's report and the call
        proceeds, payload untouched. True (strict): the same fact
        raises `UnsupportedFeatureError` before the request is
        encoded — nothing reaches the wire.
````

#### `WireChatModel.prepare` { #ocai-chat-facade-wirechatmodel-prepare }

```python
def prepare(self, request: ChatRequest, *, streaming: bool=False) -> PreparedChatCall
```

````text
Inspect and snapshot conversion without authentication or provider I/O.
````

#### `WireChatModel.chat` { #ocai-chat-facade-wirechatmodel-chat }

```python
def chat(self, request: ChatRequest, *, ctx: CallContext | None=None) -> CallResult[ChatResponse]
```

````text
Prepare and execute one governed synchronous call.
````

#### `WireChatModel.achat` { #ocai-chat-facade-wirechatmodel-achat }

```python
async def achat(self, request: ChatRequest, *, ctx: CallContext | None=None) -> CallResult[ChatResponse]
```

````text
Prepare and execute one governed async call.
````

#### `WireChatModel.stream` { #ocai-chat-facade-wirechatmodel-stream }

```python
def stream(self, request: ChatRequest, *, ctx: CallContext | None=None) -> ChatStream
```

````text
Prepare eagerly and return an owned, lazy stream.
````

#### `WireChatModel.astream` { #ocai-chat-facade-wirechatmodel-astream }

```python
async def astream(self, request: ChatRequest, *, ctx: CallContext | None=None) -> AsyncChatStream
```

````text
Prepare eagerly and return an owned async stream.
````

#### `WireChatModel.details` { #ocai-chat-facade-wirechatmodel-details }

```python
@property
def details(self) -> dict[str, Any]
```

````text
Describe this facade's composition.

Returns:
    A mapping with the codec's dialect coordinates, the bound model
    name, and the pins.
````

### `InterceptedChatModel` { #ocai-chat-facade-interceptedchatmodel }

```python
class InterceptedChatModel
```

````text
A `ChatModel` wrapped in a port-tier `CallInterceptor` chain.

What the §3.4 front door returns when `interceptors` are composed in: the
chain is folded over the inner port's own call exactly once, at
construction (`compose`/`acompose` from `ocai.runtime.interceptors`), and
every `chat`/`achat` travels the onion — outermost interceptor first. The
wrapper satisfies the `ChatModel` protocol structurally, so interceptors
stack: an `InterceptedChatModel` can wrap another.

`stream`/`astream` use the separate `StreamInterceptor` continuation.
Every configured interceptor must support it or streaming fails closed
before the inner port is invoked; unary-only governance is never bypassed.
````

#### `InterceptedChatModel.__init__` { #ocai-chat-facade-interceptedchatmodel---init-- }

```python
def __init__(self, inner: ChatModel, interceptors: Sequence[CallInterceptor]) -> None
```

````text
Fold `interceptors` over `inner`'s unary faces.

Args:
    inner: The port to wrap — typically a `WireChatModel`, but any
        `ChatModel` composes (local adapters included; that symmetry
        is the interceptor tier's admission test).
    interceptors: The chain, outermost first.
````

#### `InterceptedChatModel.prepare` { #ocai-chat-facade-interceptedchatmodel-prepare }

```python
def prepare(self, request: ChatRequest, *, streaming: bool=False) -> PreparedChatCall
```

````text
Retain the complete admission chain around an approved inner snapshot.
````

#### `InterceptedChatModel.chat` { #ocai-chat-facade-interceptedchatmodel-chat }

```python
def chat(self, request: ChatRequest, *, ctx: CallContext | None=None) -> CallResult[ChatResponse]
```

````text
Send a blocking chat request down the interceptor chain.

Args:
    request: The canonical chat request.
    ctx: The per-request governance context, visible to every
        interceptor on the way down.

Returns:
    The `CallResult` the chain hands back — the inner port's result,
    or an interceptor's short-circuit.
````

#### `InterceptedChatModel.achat` { #ocai-chat-facade-interceptedchatmodel-achat }

```python
async def achat(self, request: ChatRequest, *, ctx: CallContext | None=None) -> CallResult[ChatResponse]
```

````text
Send a blocking chat request down the async interceptor chain.

Args:
    request: The canonical chat request.
    ctx: The per-request governance context.

Returns:
    The `CallResult` the chain hands back.
````

#### `InterceptedChatModel.stream` { #ocai-chat-facade-interceptedchatmodel-stream }

```python
def stream(self, request: ChatRequest, *, ctx: CallContext | None=None) -> ChatStream
```

````text
Run eager streaming admission through every configured interceptor.

Args:
    request: The canonical chat request.
    ctx: The per-request governance context.

Returns:
    The inner port's canonical chunk stream.
````

#### `InterceptedChatModel.astream` { #ocai-chat-facade-interceptedchatmodel-astream }

```python
async def astream(self, request: ChatRequest, *, ctx: CallContext | None=None) -> AsyncChatStream
```

````text
Run eager async streaming admission through every interceptor.

Args:
    request: The canonical chat request.
    ctx: The per-request governance context.

Returns:
    The inner port's async canonical chunk stream.
````

#### `InterceptedChatModel.details` { #ocai-chat-facade-interceptedchatmodel-details }

```python
@property
def details(self) -> dict[str, Any]
```

````text
Describe the wrapped composition.

Returns:
    The inner port's details, unchanged — interceptors are transparent
    to diagnostics that describe the destination.
````

### `ObservedChatModel` { #ocai-chat-facade-observedchatmodel }

```python
class ObservedChatModel
```

````text
Observe a local or remote capability outside its admission middleware.

Invocation starts eagerly at the public call, including stream creation.
A lazy stream finishes on exhaustion, failure or explicit close. An abandoned
stream remains pending: callers must use its ownership contract. This wrapper
never treats observers as enforceable admission or required durable audit.
````

#### `ObservedChatModel.__init__` { #ocai-chat-facade-observedchatmodel---init-- }

```python
def __init__(self, inner: ChatModel, observers: Sequence[Observer]) -> None
```

````text
Register authorized passive observers around the complete port chain.
````

#### `ObservedChatModel.prepare` { #ocai-chat-facade-observedchatmodel-prepare }

```python
def prepare(self, request: ChatRequest, *, streaming: bool=False) -> PreparedChatCall
```

````text
Inspect without starting a call; observation begins when the handle executes.
````

#### `ObservedChatModel.details` { #ocai-chat-facade-observedchatmodel-details }

```python
@property
def details(self) -> dict[str, Any]
```

````text
Describe the underlying target without exporting credentials.
````

#### `ObservedChatModel.chat` { #ocai-chat-facade-observedchatmodel-chat }

```python
def chat(self, request: ChatRequest, *, ctx: CallContext | None=None) -> CallResult[ChatResponse]
```

````text
Observe one synchronous invocation including admission and conversion.
````

#### `ObservedChatModel.achat` { #ocai-chat-facade-observedchatmodel-achat }

```python
async def achat(self, request: ChatRequest, *, ctx: CallContext | None=None) -> CallResult[ChatResponse]
```

````text
Observe one async invocation with the same correlation and accounting.
````

#### `ObservedChatModel.stream` { #ocai-chat-facade-observedchatmodel-stream }

```python
def stream(self, request: ChatRequest, *, ctx: CallContext | None=None) -> ChatStream
```

````text
Start a logical invocation now; observe its owned lazy stream later.
````

#### `ObservedChatModel.astream` { #ocai-chat-facade-observedchatmodel-astream }

```python
async def astream(self, request: ChatRequest, *, ctx: CallContext | None=None) -> AsyncChatStream
```

````text
Observe async creation and its one eventual terminal outcome.
````

## `ocai.chat.protocol`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/protocol.py)

### `ChatModel` { #ocai-chat-protocol-chatmodel }

```python
class ChatModel(Protocol)
```

````text
A chat provider port — structural, never subclassed.

Implementers accept the canonical `ChatRequest` and return canonical
results wrapped in `CallResult` — the uniform envelope carrying the
route, the `FidelityReport` (its only home), usage, and the raw body.
Payloads stay pure; honesty rides the envelope.

The protocol is `runtime_checkable`, so `isinstance` verifies member
presence; `Binding.validate()` performs the deeper composition-time
check.
````

#### `ChatModel.chat` { #ocai-chat-protocol-chatmodel-chat }

```python
def chat(self, request: ChatRequest, *, ctx: CallContext | None=None) -> CallResult[ChatResponse]
```

````text
Send a blocking chat request, synchronously.

Args:
    request: The canonical chat request.
    ctx: The per-request governance context, seen by every
        interceptor and policy hook on the way down.

Returns:
    The uniform envelope carrying the canonical `ChatResponse`.
````

#### `ChatModel.achat` { #ocai-chat-protocol-chatmodel-achat }

```python
async def achat(self, request: ChatRequest, *, ctx: CallContext | None=None) -> CallResult[ChatResponse]
```

````text
Send a blocking chat request, asynchronously.

Args:
    request: The canonical chat request.
    ctx: The per-request governance context.

Returns:
    The uniform envelope carrying the canonical `ChatResponse`.
````

#### `ChatModel.stream` { #ocai-chat-protocol-chatmodel-stream }

```python
def stream(self, request: ChatRequest, *, ctx: CallContext | None=None) -> ChatStream
```

````text
Send a streaming chat request, synchronously.

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
````

#### `ChatModel.astream` { #ocai-chat-protocol-chatmodel-astream }

```python
async def astream(self, request: ChatRequest, *, ctx: CallContext | None=None) -> AsyncChatStream
```

````text
Send a streaming chat request, asynchronously.

Args:
    request: The canonical chat request.
    ctx: The per-request governance context.

Returns:
    The async-iterable canonical chunk stream.
````

#### `ChatModel.details` { #ocai-chat-protocol-chatmodel-details }

```python
@property
def details(self) -> dict[str, Any]
```

````text
Describe this model implementation.

Returns:
    A free-form mapping of descriptive metadata (e.g. the dialect
    spoken, the host label, declared capabilities) used by
    interceptors and diagnostics — never by conversion logic.
````

## `ocai.chat.types`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/types/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-chat-types-annotation"></span>`Annotation` | [`ocai.chat.types.annotations.Annotation`](ocai-chat.md#ocai-chat-types-annotations-annotation) |
| <span id="ocai-chat-types-sourceresultref"></span>`SourceResultRef` | [`ocai.chat.types.annotations.SourceResultRef`](ocai-chat.md#ocai-chat-types-annotations-sourceresultref) |
| <span id="ocai-chat-types-span"></span>`Span` | [`ocai.chat.types.annotations.Span`](ocai-chat.md#ocai-chat-types-annotations-span) |
| <span id="ocai-chat-types-audiooutputconfig"></span>`AudioOutputConfig` | [`ocai.chat.types.config.AudioOutputConfig`](ocai-chat.md#ocai-chat-types-config-audiooutputconfig) |
| <span id="ocai-chat-types-cacheconfig"></span>`CacheConfig` | [`ocai.chat.types.config.CacheConfig`](ocai-chat.md#ocai-chat-types-config-cacheconfig) |
| <span id="ocai-chat-types-cachehint"></span>`CacheHint` | [`ocai.chat.types.config.CacheHint`](ocai-chat.md#ocai-chat-types-config-cachehint) |
| <span id="ocai-chat-types-chatconfig"></span>`ChatConfig` | [`ocai.chat.types.config.ChatConfig`](ocai-chat.md#ocai-chat-types-config-chatconfig) |
| <span id="ocai-chat-types-outputformat"></span>`OutputFormat` | [`ocai.chat.types.config.OutputFormat`](ocai-chat.md#ocai-chat-types-config-outputformat) |
| <span id="ocai-chat-types-outputmode"></span>`OutputMode` | [`ocai.chat.types.config.OutputMode`](ocai-chat.md#ocai-chat-types-config-outputmode) |
| <span id="ocai-chat-types-reasoningconfig"></span>`ReasoningConfig` | [`ocai.chat.types.config.ReasoningConfig`](ocai-chat.md#ocai-chat-types-config-reasoningconfig) |
| <span id="ocai-chat-types-reasoningeffort"></span>`ReasoningEffort` | [`ocai.chat.types.config.ReasoningEffort`](ocai-chat.md#ocai-chat-types-config-reasoningeffort) |
| <span id="ocai-chat-types-detail-registry"></span>`DETAIL_REGISTRY` | [`ocai.core.finish.DETAIL_REGISTRY`](ocai-core.md#ocai-core-finish-detail-registry) |
| <span id="ocai-chat-types-detailopaque"></span>`DetailOpaque` | [`ocai.core.finish.DetailOpaque`](ocai-core.md#ocai-core-finish-detailopaque) |
| <span id="ocai-chat-types-detailtype"></span>`DetailType` | [`ocai.core.finish.DetailType`](ocai-core.md#ocai-core-finish-detailtype) |
| <span id="ocai-chat-types-errordetail"></span>`ErrorDetail` | [`ocai.core.finish.ErrorDetail`](ocai-core.md#ocai-core-finish-errordetail) |
| <span id="ocai-chat-types-finishdetail"></span>`FinishDetail` | [`ocai.core.finish.FinishDetail`](ocai-core.md#ocai-core-finish-finishdetail) |
| <span id="ocai-chat-types-finishinfo"></span>`FinishInfo` | [`ocai.core.finish.FinishInfo`](ocai-core.md#ocai-core-finish-finishinfo) |
| <span id="ocai-chat-types-finishreason"></span>`FinishReason` | [`ocai.core.finish.FinishReason`](ocai-core.md#ocai-core-finish-finishreason) |
| <span id="ocai-chat-types-incompletedetail"></span>`IncompleteDetail` | [`ocai.core.finish.IncompleteDetail`](ocai-core.md#ocai-core-finish-incompletedetail) |
| <span id="ocai-chat-types-refusaldetail"></span>`RefusalDetail` | [`ocai.core.finish.RefusalDetail`](ocai-core.md#ocai-core-finish-refusaldetail) |
| <span id="ocai-chat-types-safetydetail"></span>`SafetyDetail` | [`ocai.core.finish.SafetyDetail`](ocai-core.md#ocai-core-finish-safetydetail) |
| <span id="ocai-chat-types-safetyrating"></span>`SafetyRating` | [`ocai.core.finish.SafetyRating`](ocai-core.md#ocai-core-finish-safetyrating) |
| <span id="ocai-chat-types-cast-detail"></span>`cast_detail` | [`ocai.core.finish.cast_detail`](ocai-core.md#ocai-core-finish-cast-detail) |
| <span id="ocai-chat-types-message"></span>`Message` | [`ocai.chat.types.message.Message`](ocai-chat.md#ocai-chat-types-message-message) |
| <span id="ocai-chat-types-part-registry"></span>`PART_REGISTRY` | [`ocai.chat.types.parts.PART_REGISTRY`](ocai-chat.md#ocai-chat-types-parts-part-registry) |
| <span id="ocai-chat-types-executedby"></span>`ExecutedBy` | [`ocai.chat.types.parts.ExecutedBy`](ocai-chat.md#ocai-chat-types-parts-executedby) |
| <span id="ocai-chat-types-part"></span>`Part` | [`ocai.chat.types.parts.Part`](ocai-chat.md#ocai-chat-types-parts-part) |
| <span id="ocai-chat-types-partaudio"></span>`PartAudio` | [`ocai.chat.types.parts.PartAudio`](ocai-chat.md#ocai-chat-types-parts-partaudio) |
| <span id="ocai-chat-types-partbase"></span>`PartBase` | [`ocai.chat.types.parts.PartBase`](ocai-chat.md#ocai-chat-types-parts-partbase) |
| <span id="ocai-chat-types-partdocument"></span>`PartDocument` | [`ocai.chat.types.parts.PartDocument`](ocai-chat.md#ocai-chat-types-parts-partdocument) |
| <span id="ocai-chat-types-partimage"></span>`PartImage` | [`ocai.chat.types.parts.PartImage`](ocai-chat.md#ocai-chat-types-parts-partimage) |
| <span id="ocai-chat-types-partopaque"></span>`PartOpaque` | [`ocai.chat.types.parts.PartOpaque`](ocai-chat.md#ocai-chat-types-parts-partopaque) |
| <span id="ocai-chat-types-partreasoning"></span>`PartReasoning` | [`ocai.chat.types.parts.PartReasoning`](ocai-chat.md#ocai-chat-types-parts-partreasoning) |
| <span id="ocai-chat-types-partrefusal"></span>`PartRefusal` | [`ocai.chat.types.parts.PartRefusal`](ocai-chat.md#ocai-chat-types-parts-partrefusal) |
| <span id="ocai-chat-types-partservertoolcall"></span>`PartServerToolCall` | [`ocai.chat.types.parts.PartServerToolCall`](ocai-chat.md#ocai-chat-types-parts-partservertoolcall) |
| <span id="ocai-chat-types-partservertoolresult"></span>`PartServerToolResult` | [`ocai.chat.types.parts.PartServerToolResult`](ocai-chat.md#ocai-chat-types-parts-partservertoolresult) |
| <span id="ocai-chat-types-parttext"></span>`PartText` | [`ocai.chat.types.parts.PartText`](ocai-chat.md#ocai-chat-types-parts-parttext) |
| <span id="ocai-chat-types-parttoolcall"></span>`PartToolCall` | [`ocai.chat.types.parts.PartToolCall`](ocai-chat.md#ocai-chat-types-parts-parttoolcall) |
| <span id="ocai-chat-types-parttoolresult"></span>`PartToolResult` | [`ocai.chat.types.parts.PartToolResult`](ocai-chat.md#ocai-chat-types-parts-parttoolresult) |
| <span id="ocai-chat-types-parttype"></span>`PartType` | [`ocai.chat.types.parts.PartType`](ocai-chat.md#ocai-chat-types-parts-parttype) |
| <span id="ocai-chat-types-partunknown"></span>`PartUnknown` | [`ocai.chat.types.parts.PartUnknown`](ocai-chat.md#ocai-chat-types-parts-partunknown) |
| <span id="ocai-chat-types-partvideo"></span>`PartVideo` | [`ocai.chat.types.parts.PartVideo`](ocai-chat.md#ocai-chat-types-parts-partvideo) |
| <span id="ocai-chat-types-servertoolkind"></span>`ServerToolKind` | [`ocai.chat.types.parts.ServerToolKind`](ocai-chat.md#ocai-chat-types-parts-servertoolkind) |
| <span id="ocai-chat-types-toolcallstatus"></span>`ToolCallStatus` | [`ocai.chat.types.parts.ToolCallStatus`](ocai-chat.md#ocai-chat-types-parts-toolcallstatus) |
| <span id="ocai-chat-types-cast-part"></span>`cast_part` | [`ocai.chat.types.parts.cast_part`](ocai-chat.md#ocai-chat-types-parts-cast-part) |
| <span id="ocai-chat-types-chatrequest"></span>`ChatRequest` | [`ocai.chat.types.request.ChatRequest`](ocai-chat.md#ocai-chat-types-request-chatrequest) |
| <span id="ocai-chat-types-chatresponse"></span>`ChatResponse` | [`ocai.chat.types.response.ChatResponse`](ocai-chat.md#ocai-chat-types-response-chatresponse) |
| <span id="ocai-chat-types-responseinfo"></span>`ResponseInfo` | [`ocai.chat.types.response.ResponseInfo`](ocai-chat.md#ocai-chat-types-response-responseinfo) |
| <span id="ocai-chat-types-role"></span>`Role` | [`ocai.chat.types.role.Role`](ocai-chat.md#ocai-chat-types-role-role) |
| <span id="ocai-chat-types-decode-role"></span>`decode_role` | [`ocai.chat.types.role.decode_role`](ocai-chat.md#ocai-chat-types-role-decode-role) |
| <span id="ocai-chat-types-encode-role"></span>`encode_role` | [`ocai.chat.types.role.encode_role`](ocai-chat.md#ocai-chat-types-role-encode-role) |
| <span id="ocai-chat-types-delta-registry"></span>`DELTA_REGISTRY` | [`ocai.chat.types.stream.DELTA_REGISTRY`](ocai-chat.md#ocai-chat-types-stream-delta-registry) |
| <span id="ocai-chat-types-incomplete-extension"></span>`INCOMPLETE_EXTENSION` | [`ocai.chat.types.stream.INCOMPLETE_EXTENSION`](ocai-chat.md#ocai-chat-types-stream-incomplete-extension) |
| <span id="ocai-chat-types-signature-buffer-extension"></span>`SIGNATURE_BUFFER_EXTENSION` | [`ocai.chat.types.stream.SIGNATURE_BUFFER_EXTENSION`](ocai-chat.md#ocai-chat-types-stream-signature-buffer-extension) |
| <span id="ocai-chat-types-asyncchatstream"></span>`AsyncChatStream` | [`ocai.chat.types.stream.AsyncChatStream`](ocai-chat.md#ocai-chat-types-stream-asyncchatstream) |
| <span id="ocai-chat-types-chatchunk"></span>`ChatChunk` | [`ocai.chat.types.stream.ChatChunk`](ocai-chat.md#ocai-chat-types-stream-chatchunk) |
| <span id="ocai-chat-types-chatstream"></span>`ChatStream` | [`ocai.chat.types.stream.ChatStream`](ocai-chat.md#ocai-chat-types-stream-chatstream) |
| <span id="ocai-chat-types-chunktype"></span>`ChunkType` | [`ocai.chat.types.stream.ChunkType`](ocai-chat.md#ocai-chat-types-stream-chunktype) |
| <span id="ocai-chat-types-delta"></span>`Delta` | [`ocai.chat.types.stream.Delta`](ocai-chat.md#ocai-chat-types-stream-delta) |
| <span id="ocai-chat-types-deltaannotation"></span>`DeltaAnnotation` | [`ocai.chat.types.stream.DeltaAnnotation`](ocai-chat.md#ocai-chat-types-stream-deltaannotation) |
| <span id="ocai-chat-types-deltablob"></span>`DeltaBlob` | [`ocai.chat.types.stream.DeltaBlob`](ocai-chat.md#ocai-chat-types-stream-deltablob) |
| <span id="ocai-chat-types-deltareasoning"></span>`DeltaReasoning` | [`ocai.chat.types.stream.DeltaReasoning`](ocai-chat.md#ocai-chat-types-stream-deltareasoning) |
| <span id="ocai-chat-types-deltarefusal"></span>`DeltaRefusal` | [`ocai.chat.types.stream.DeltaRefusal`](ocai-chat.md#ocai-chat-types-stream-deltarefusal) |
| <span id="ocai-chat-types-deltasignature"></span>`DeltaSignature` | [`ocai.chat.types.stream.DeltaSignature`](ocai-chat.md#ocai-chat-types-stream-deltasignature) |
| <span id="ocai-chat-types-deltatext"></span>`DeltaText` | [`ocai.chat.types.stream.DeltaText`](ocai-chat.md#ocai-chat-types-stream-deltatext) |
| <span id="ocai-chat-types-deltatoolargs"></span>`DeltaToolArgs` | [`ocai.chat.types.stream.DeltaToolArgs`](ocai-chat.md#ocai-chat-types-stream-deltatoolargs) |
| <span id="ocai-chat-types-deltatype"></span>`DeltaType` | [`ocai.chat.types.stream.DeltaType`](ocai-chat.md#ocai-chat-types-stream-deltatype) |
| <span id="ocai-chat-types-deltaunknown"></span>`DeltaUnknown` | [`ocai.chat.types.stream.DeltaUnknown`](ocai-chat.md#ocai-chat-types-stream-deltaunknown) |
| <span id="ocai-chat-types-errorinfo"></span>`ErrorInfo` | [`ocai.chat.types.stream.ErrorInfo`](ocai-chat.md#ocai-chat-types-stream-errorinfo) |
| <span id="ocai-chat-types-streamaccumulator"></span>`StreamAccumulator` | [`ocai.chat.types.stream.StreamAccumulator`](ocai-chat.md#ocai-chat-types-stream-streamaccumulator) |
| <span id="ocai-chat-types-streamend"></span>`StreamEnd` | [`ocai.chat.types.stream.StreamEnd`](ocai-chat.md#ocai-chat-types-stream-streamend) |
| <span id="ocai-chat-types-streamoutcome"></span>`StreamOutcome` | [`ocai.core.result.StreamOutcome`](ocai-core.md#ocai-core-result-streamoutcome) |
| <span id="ocai-chat-types-cast-delta"></span>`cast_delta` | [`ocai.chat.types.stream.cast_delta`](ocai-chat.md#ocai-chat-types-stream-cast-delta) |
| <span id="ocai-chat-types-servertool"></span>`ServerTool` | [`ocai.chat.types.tools.ServerTool`](ocai-chat.md#ocai-chat-types-tools-servertool) |
| <span id="ocai-chat-types-servertoollocation"></span>`ServerToolLocation` | [`ocai.chat.types.tools.ServerToolLocation`](ocai-chat.md#ocai-chat-types-tools-servertoollocation) |
| <span id="ocai-chat-types-tool"></span>`Tool` | [`ocai.chat.types.tools.Tool`](ocai-chat.md#ocai-chat-types-tools-tool) |
| <span id="ocai-chat-types-toolchoice"></span>`ToolChoice` | [`ocai.chat.types.tools.ToolChoice`](ocai-chat.md#ocai-chat-types-tools-toolchoice) |
| <span id="ocai-chat-types-toolchoicemode"></span>`ToolChoiceMode` | [`ocai.chat.types.tools.ToolChoiceMode`](ocai-chat.md#ocai-chat-types-tools-toolchoicemode) |
| <span id="ocai-chat-types-tooldefinition"></span>`ToolDefinition` | [`ocai.chat.types.tools.ToolDefinition`](ocai-chat.md#ocai-chat-types-tools-tooldefinition) |
| <span id="ocai-chat-types-toolunknown"></span>`ToolUnknown` | [`ocai.chat.types.tools.ToolUnknown`](ocai-chat.md#ocai-chat-types-tools-toolunknown) |
| <span id="ocai-chat-types-consumption"></span>`Consumption` | [`ocai.core.usage.Consumption`](ocai-core.md#ocai-core-usage-consumption) |
| <span id="ocai-chat-types-usage"></span>`Usage` | [`ocai.core.usage.Usage`](ocai-core.md#ocai-core-usage-usage) |
| <span id="ocai-chat-types-usagemodality"></span>`UsageModality` | [`ocai.core.usage.UsageModality`](ocai-core.md#ocai-core-usage-usagemodality) |
| <span id="ocai-chat-types-usagesource"></span>`UsageSource` | [`ocai.core.usage.UsageSource`](ocai-core.md#ocai-core-usage-usagesource) |
| <span id="ocai-chat-types-usageunit"></span>`UsageUnit` | [`ocai.core.usage.UsageUnit`](ocai-core.md#ocai-core-usage-usageunit) |

## `ocai.chat.types.annotations`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/types/annotations.py)

### `Span` { #ocai-chat-types-annotations-span }

```python
class Span:
    start: int
    end: int
    extensions: dict[str, Any] = field(default_factory=dict[str, Any], kw_only=True)
```

````text
A half-open character range `[start, end)` into decoded text.

Offsets are counted in Unicode code points of the *decoded* `PartText`
text before any normalization. NFC, byte or UTF-16 offset conversions need
their own validated mapping; this value never guesses or rescales offsets.

Attributes:
    start: The inclusive start offset.
    end: The exclusive end offset; `end >= start`.
````

#### `Span.valid_for` { #ocai-chat-types-annotations-span-valid-for }

```python
def valid_for(self, text: str, *, attributed_text: str | None=None) -> bool
```

````text
Check code-point bounds and an optional exact attributed output slice.

Args:
    text: The exact decoded text, without normalization.
    attributed_text: Expected output slice, when the codec supplies one;
        not the source quotation in Annotation.cited_text.

Returns:
    Whether the span can safely attribute this text.
````

#### `Span.to_dict` { #ocai-chat-types-annotations-span-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize the span to a plain JSON-compatible dict.

Returns:
    A dict with `start` and `end`.
````

#### `Span.from_dict` { #ocai-chat-types-annotations-span-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `Span` from a serialized dict, totally.

Args:
    data: A mapping with `start` and `end`. Malformed offsets are
        retained under `ocai.invalid_span`, never coerced to integers.
        Unknown span keys follow the ordinary extensions sweep.

Returns:
    The decoded `Span`.
````

### `SourceResultRef` { #ocai-chat-types-annotations-sourceresultref }

```python
class SourceResultRef(IRObject):
    call_id: str = ''
    pointer: str = ''
```

````text
A local citation reference into a sibling server-tool result.

Attributes:
    call_id: Identity of the corresponding server-tool call/result.
    pointer: JSON Pointer within that result payload; empty names its root.
        This is data, never fetched or resolved implicitly.
````

#### `SourceResultRef.from_dict` { #ocai-chat-types-annotations-sourceresultref-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Decode a local reference while preserving unknown envelope fields.
````

### `Annotation` { #ocai-chat-types-annotations-annotation }

```python
class Annotation(IRObject):
    span: Span | None = None
    url: str | None = None
    document_index: int | None = None
    file: ProviderRef | None = None
    title: str | None = None
    cited_text: str | None = None
    opaque: ProviderRef | None = None
    kind: str | None = None
    source_result: SourceResultRef | None = None
```

````text
One span-anchored citation carried by a `PartText`.

Lives in `PartText.annotations`; each record attributes the `span` slice
of the part's text to a source. During streaming, annotations arrive as
`DeltaAnnotation` events and are appended by the `StreamAccumulator`.

Attributes:
    span: The text range being attributed, or None when the provider
        cited the whole part.
    url: The cited web URL, when the source is a web page.
    document_index: The zero-based index of the cited request document,
        when the source is caller-supplied material.
    file: The provider-side file handle backing the citation, when the
        source is an uploaded file. Crossing another
        `(provider, interface)` is reported `UNSUPPORTED`.
    title: The human-readable title of the cited source.
    cited_text: The verbatim excerpt the provider quoted, when given.
    opaque: Provider-opaque citation state (e.g. an encrypted grounding
        token) that must ride along verbatim to keep the citation
        replayable.
    kind: Open citation kind, including `url_citation`; unknown kinds survive.
    source_result: Local server-tool result reference, without provider replay authority.
````

#### `Annotation.validated` { #ocai-chat-types-annotations-annotation-validated }

```python
def validated(self, text: str, *, attributed_text: str | None=None) -> Self
```

````text
Return detached citation data validated against final decoded text.

Invalid spans become unpositioned citations with original evidence in a
registered extension. Source quotations need not equal output wording.
Call only when text is final; streaming annotations can arrive earlier.

Args:
    text: Exact final part text, counted in Unicode code points.
    attributed_text: Optional expected output slice for offset validation.

Returns:
    A detached annotation; unknown kinds and source metadata are retained.
````

#### `Annotation.from_dict` { #ocai-chat-types-annotations-annotation-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build an `Annotation` from a serialized dict, totally.

Args:
    data: A mapping with any of the annotation fields plus the
        common IR envelope keys; unknown keys sweep to `extensions`.

Returns:
    The decoded `Annotation`.
````

## `ocai.chat.types.config`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/types/config.py)

### `OutputMode` { #ocai-chat-types-config-outputmode }

```python
class OutputMode:
    TEXT: Final = 'text'
    JSON: Final = 'json'
    JSON_SCHEMA: Final = 'json_schema'
```

````text
Canonical constants for the open `OutputFormat.mode` code.

Attributes:
    TEXT: Free-form text generation (the default).
    JSON: Provider-enforced syntactically-valid JSON, no schema.
    JSON_SCHEMA: Provider-enforced conformance to `OutputFormat.schema`.
````

### `ReasoningEffort` { #ocai-chat-types-config-reasoningeffort }

```python
class ReasoningEffort:
    LOW: Final = 'low'
    MEDIUM: Final = 'medium'
    HIGH: Final = 'high'
```

````text
Canonical constants for the open `ReasoningConfig.effort` code.

Attributes:
    LOW: Minimal reasoning budget.
    MEDIUM: Moderate reasoning budget.
    HIGH: Maximal reasoning budget.
````

### `ReasoningConfig` { #ocai-chat-types-config-reasoningconfig }

```python
class ReasoningConfig(IRObject):
    effort: str | None = None
    budget_tokens: int | None = None
    include_thoughts: bool | None = None
```

````text
How much the model should think, and whether thoughts are surfaced.

Bridges the two native idioms — effort levels (OpenAI `/responses`) and
token budgets (Anthropic, Gemini) — as sibling optionals: a request sets
the one its author thinks in, and the codec maps or `APPROXIMATED`-reports
the translation to the destination's idiom.

Attributes:
    effort: The open effort code; canonical constants on
        `ReasoningEffort` (`low | medium | high`).
    budget_tokens: The maximum tokens the model may spend thinking.
    include_thoughts: Whether reasoning content should be surfaced as
        `PartReasoning` parts in the response.
````

#### `ReasoningConfig.from_dict` { #ocai-chat-types-config-reasoningconfig-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `ReasoningConfig` from a serialized dict, totally.

Args:
    data: A mapping with any of the reasoning fields plus the common
        IR envelope keys.

Returns:
    The decoded `ReasoningConfig`.
````

### `OutputFormat` { #ocai-chat-types-config-outputformat }

```python
class OutputFormat(IRObject):
    mode: str = OutputMode.TEXT
    name: str | None = None
    schema: Schema | None = None
    strict: bool | None = None
```

````text
The structured-output contract for a generation.

Attributes:
    mode: The open output-mode code; canonical constants on `OutputMode`
        (`text | json | json_schema`).
    name: The schema's name, where the destination requires one (OpenAI
        `json_schema.name`).
    schema: The JSON Schema the output must conform to when `mode` is
        `json_schema`.
    strict: Whether the provider must enforce the schema exactly rather
        than best-effort.
````

#### `OutputFormat.from_dict` { #ocai-chat-types-config-outputformat-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build an `OutputFormat` from a serialized dict, totally.

Args:
    data: A mapping with any of the output fields plus the common IR
        envelope keys; `schema` is decoded via `decode_schema`.

Returns:
    The decoded `OutputFormat`.
````

### `CacheHint` { #ocai-chat-types-config-cachehint }

```python
class CacheHint(IRObject):
    ttl: str | None = None
```

````text
[provisional] A per-part prompt-caching marker.

Carried on any part's `cache_hint` field (the shared part base); marks
the position up to which the provider should cache the prompt prefix
(Anthropic `cache_control` is the model). Interfaces with implicit
caching report it `EMULATED` or `ABSENT` per their `CapabilityProfile`.

Attributes:
    ttl: The requested cache lifetime as an open provider-shaped token
        (e.g. `"5m"`, `"1h"`), or None for the provider default.
````

#### `CacheHint.from_dict` { #ocai-chat-types-config-cachehint-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `CacheHint` from a serialized dict, totally.

Args:
    data: A mapping with an optional `ttl` plus the common IR
        envelope keys.

Returns:
    The decoded `CacheHint`.
````

### `CacheConfig` { #ocai-chat-types-config-cacheconfig }

```python
class CacheConfig(IRObject):
    mode: str | None = None
    ref: ProviderRef | None = None
```

````text
[provisional] Request-level prompt-caching configuration.

The request-scoped complement to per-part `CacheHint`s: it selects the
caching regime and can name an existing provider-side cache to reuse.

Attributes:
    mode: The open caching-mode code (`"auto" | "explicit" | "off"`),
        or None for the provider default.
    ref: An existing provider-side cache handle to generate against
        (Gemini `cachedContent`); a `ProviderRef`, so crossing another
        `(provider, interface)` is reported `UNSUPPORTED`.
````

#### `CacheConfig.from_dict` { #ocai-chat-types-config-cacheconfig-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `CacheConfig` from a serialized dict, totally.

Args:
    data: A mapping with the optional `mode` and nested `ref` plus
        the common IR envelope keys.

Returns:
    The decoded `CacheConfig`.
````

### `AudioOutputConfig` { #ocai-chat-types-config-audiooutputconfig }

```python
class AudioOutputConfig(IRObject):
    voice: str | None = None
    format: str | None = None
```

````text
[provisional] Configuration for audio output generation.

Consulted only when `"audio"` is among `ChatConfig.modalities`; the pair
ships provisional because only one first-party interface (OpenAI
`audio`) exercises it today.

Attributes:
    voice: The provider voice identifier, verbatim.
    format: The requested audio container/encoding (e.g. `"wav"`,
        `"mp3"`, `"pcm16"`), as an open code.
````

#### `AudioOutputConfig.from_dict` { #ocai-chat-types-config-audiooutputconfig-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build an `AudioOutputConfig` from a serialized dict, totally.

Args:
    data: A mapping with the optional audio fields plus the common
        IR envelope keys.

Returns:
    The decoded `AudioOutputConfig`.
````

### `ChatConfig` { #ocai-chat-types-config-chatconfig }

```python
class ChatConfig(IRObject):
    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int | None = None
    stop_sequences: list[str] | None = None
    seed: int | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    parallel_tool_calls: bool | None = None
    top_k: int | None = None
    logprobs: int | None = None
    modalities: list[str] | None = None
    audio: AudioOutputConfig | None = None
    reasoning: ReasoningConfig | None = None
    output: OutputFormat | None = None
    cache: CacheConfig | None = None
```

````text
Provider-neutral generation configuration for a `ChatRequest`.

Every field is optional; None means "provider default", and the codec
emits nothing for it (omit-absent). `top_k` and `logprobs` are
profile-gated: the feature gate consults the destination's
`CapabilityProfile` before conversion, so an unsupported knob is refused
(strict) or loss-reported (annotate) instead of silently dropped.

Attributes:
    temperature: Sampling temperature, passed verbatim — out-of-range
        values are `APPROXIMATED`-reported, never clamped.
    top_p: Nucleus-sampling probability mass.
    max_output_tokens: The output token ceiling, reasoning included
        where the provider counts it that way (dialect codecs own the
        per-interface accounting shift).
    stop_sequences: Sequences that end generation when emitted.
    seed: Best-effort determinism seed.
    frequency_penalty: Repetition penalty scaled by frequency.
    presence_penalty: Repetition penalty for mere presence.
    parallel_tool_calls: Whether the model may emit several tool calls
        in one turn.
    top_k: Profile-gated top-k sampling cutoff.
    logprobs: Profile-gated count of top logprobs to return per token;
        None disables.
    modalities: The open output-modality codes requested
        (e.g. `["text", "audio"]`); None means text.
    audio: Audio-output settings, meaningful when `"audio"` is in
        `modalities` [provisional].
    reasoning: How much to think and whether thoughts are surfaced.
    output: The structured-output contract.
    cache: Request-level caching configuration [provisional].
````

#### `ChatConfig.from_dict` { #ocai-chat-types-config-chatconfig-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `ChatConfig` from a serialized dict, totally.

The typed sub-configs (`audio`, `reasoning`, `output`, `cache`) are
decoded through their own `from_dict`; scalar knobs pass through.

Args:
    data: A mapping with any of the config fields plus the common IR
        envelope keys; unknown keys sweep to `extensions`.

Returns:
    The decoded `ChatConfig`.
````

## `ocai.chat.types.finish`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/types/finish.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-chat-types-finish-detail-registry"></span>`DETAIL_REGISTRY` | [`ocai.core.finish.DETAIL_REGISTRY`](ocai-core.md#ocai-core-finish-detail-registry) |
| <span id="ocai-chat-types-finish-detailopaque"></span>`DetailOpaque` | [`ocai.core.finish.DetailOpaque`](ocai-core.md#ocai-core-finish-detailopaque) |
| <span id="ocai-chat-types-finish-detailtype"></span>`DetailType` | [`ocai.core.finish.DetailType`](ocai-core.md#ocai-core-finish-detailtype) |
| <span id="ocai-chat-types-finish-errordetail"></span>`ErrorDetail` | [`ocai.core.finish.ErrorDetail`](ocai-core.md#ocai-core-finish-errordetail) |
| <span id="ocai-chat-types-finish-finishdetail"></span>`FinishDetail` | [`ocai.core.finish.FinishDetail`](ocai-core.md#ocai-core-finish-finishdetail) |
| <span id="ocai-chat-types-finish-finishinfo"></span>`FinishInfo` | [`ocai.core.finish.FinishInfo`](ocai-core.md#ocai-core-finish-finishinfo) |
| <span id="ocai-chat-types-finish-finishreason"></span>`FinishReason` | [`ocai.core.finish.FinishReason`](ocai-core.md#ocai-core-finish-finishreason) |
| <span id="ocai-chat-types-finish-incompletedetail"></span>`IncompleteDetail` | [`ocai.core.finish.IncompleteDetail`](ocai-core.md#ocai-core-finish-incompletedetail) |
| <span id="ocai-chat-types-finish-refusaldetail"></span>`RefusalDetail` | [`ocai.core.finish.RefusalDetail`](ocai-core.md#ocai-core-finish-refusaldetail) |
| <span id="ocai-chat-types-finish-safetydetail"></span>`SafetyDetail` | [`ocai.core.finish.SafetyDetail`](ocai-core.md#ocai-core-finish-safetydetail) |
| <span id="ocai-chat-types-finish-safetyrating"></span>`SafetyRating` | [`ocai.core.finish.SafetyRating`](ocai-core.md#ocai-core-finish-safetyrating) |
| <span id="ocai-chat-types-finish-cast-detail"></span>`cast_detail` | [`ocai.core.finish.cast_detail`](ocai-core.md#ocai-core-finish-cast-detail) |

## `ocai.chat.types.message`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/types/message.py)

### `Message` { #ocai-chat-types-message-message }

```python
class Message(IRObject):
    object: ClassVar[str] = 'message'
    role: str
    parts: list[Part]
```

````text
A single conversation turn: who spoke, and the parts they produced.

The unit every codec encodes/decodes and every conversion edge maps.
The constructor accepts sugar — a bare string (or strings inside the
list, or a single `Part`) — and `__post_init__` normalizes everything
to `list[Part]`, so downstream machinery only ever sees one shape.

Attributes:
    role: The author's open role code; canonical constants on `Role`.
    parts: The ordered content parts making up the turn.
````

#### `Message.user` { #ocai-chat-types-message-message-user }

```python
@classmethod
def user(cls, parts: str | Part | list[Part | str]) -> Self
```

````text
Build a user-authored message.

Args:
    parts: The content, with the same sugar the constructor accepts.

Returns:
    A `Message` with `role == Role.USER`.
````

#### `Message.model` { #ocai-chat-types-message-message-model }

```python
@classmethod
def model(cls, parts: str | Part | list[Part | str]) -> Self
```

````text
Build a model-authored message.

Args:
    parts: The content, with the same sugar the constructor accepts.

Returns:
    A `Message` with `role == Role.MODEL`.
````

#### `Message.system` { #ocai-chat-types-message-message-system }

```python
@classmethod
def system(cls, parts: str | Part | list[Part | str]) -> Self
```

````text
Build a system-instruction message.

Codecs relocate it per dialect (e.g. Gemini `systemInstruction`),
recording the move as a `SemanticShift`, never silently.

Args:
    parts: The content, with the same sugar the constructor accepts.

Returns:
    A `Message` with `role == Role.SYSTEM`.
````

#### `Message.tool` { #ocai-chat-types-message-message-tool }

```python
@classmethod
def tool(cls, parts: str | Part | list[Part | str]) -> Self
```

````text
Build a tool-result message.

Typically carries `PartToolResult` parts correlated to earlier
`PartToolCall`s by `call_id`.

Args:
    parts: The content, with the same sugar the constructor accepts.

Returns:
    A `Message` with `role == Role.TOOL`.
````

#### `Message.text` { #ocai-chat-types-message-message-text }

```python
@property
def text(self) -> str
```

````text
Return the concatenated text of every `PartText`, in order.

A derived view, never storage — the parts stay authoritative, so
annotations and non-text parts are never flattened away by reading
it.
````

#### `Message.from_dict` { #ocai-chat-types-message-message-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `Message` from a serialized dict, totally.

The role is normalized via `decode_role` (unknown roles preserved
verbatim); parts decode through `PART_REGISTRY` (unknown tags fall
back to `PartUnknown`); bare strings in the parts list ride the same
sugar the constructor accepts.

Args:
    data: A mapping with `role`, `parts`, and the common IR envelope
        keys.

Returns:
    The decoded `Message`.
````

## `ocai.chat.types.parts`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/types/parts.py)

### `PartType` { #ocai-chat-types-parts-parttype }

```python
class PartType(str, Enum):
    UNDEFINED = 'undefined'
    TEXT = 'text'
    IMAGE = 'image'
    AUDIO = 'audio'
    VIDEO = 'video'
    DOCUMENT = 'document'
    REASONING = 'reasoning'
    TOOL_CALL = 'tool_call'
    TOOL_RESULT = 'tool_result'
    SERVER_TOOL_CALL = 'server_tool_call'
    SERVER_TOOL_RESULT = 'server_tool_result'
    REFUSAL = 'refusal'
    OPAQUE = 'opaque'
```

````text
Canonical discriminator tags for the core `Part` variants.

Constants for the tags core ships — the union itself stays open through
`PART_REGISTRY` (unknown tags decode to `PartUnknown`; plugins register
namespaced tags).

Attributes:
    UNDEFINED: No part kind set (the unknown/placeholder tag).
    TEXT: A text part (`PartText`).
    IMAGE: An image part (`PartImage`).
    AUDIO: An audio part (`PartAudio`).
    VIDEO: A video part (`PartVideo`).
    DOCUMENT: A document part (`PartDocument`).
    REASONING: A model-reasoning part (`PartReasoning`).
    TOOL_CALL: A client-executed tool invocation (`PartToolCall`).
    TOOL_RESULT: The result of a client-executed tool (`PartToolResult`).
    SERVER_TOOL_CALL: A provider-executed built-in tool invocation
        (`PartServerToolCall`).
    SERVER_TOOL_RESULT: A provider-executed built-in tool result
        (`PartServerToolResult`).
    REFUSAL: A refusal part (`PartRefusal`).
    OPAQUE: Deliberate provider-unique content (`PartOpaque`).
````

### `ToolCallStatus` { #ocai-chat-types-parts-toolcallstatus }

```python
class ToolCallStatus:
    INPUT_STREAMING: Final = 'input_streaming'
    INPUT_COMPLETE: Final = 'input_complete'
    APPROVAL_REQUESTED: Final = 'approval_requested'
    APPROVAL_DENIED: Final = 'approval_denied'
    EXECUTING: Final = 'executing'
    OUTPUT_AVAILABLE: Final = 'output_available'
    OUTPUT_ERROR: Final = 'output_error'
```

````text
Canonical constants for the open tool-call lifecycle code.

Shared between `PartToolCall.status`, `PartServerToolCall.status`, and
their result siblings — the same lifecycle the streaming deltas advance:
`input_streaming → input_complete → executing →
output_available | output_error`. Open: providers may surface states
core has not named, preserved verbatim.

The approval constants are **agent-tier** states: they exist for agent
frameworks built on ocai (human-in-the-loop approval between
`input_complete` and `executing`) and never appear on any provider
wire. Agent-tier statuses are never wire-encoded: codecs encode the
nearest wire-legal ancestor or refuse — they never invent wire values.

Attributes:
    INPUT_STREAMING: Argument fragments are still arriving.
    INPUT_COMPLETE: The arguments are complete; the call is ready to
        execute.
    APPROVAL_REQUESTED: Agent-tier — the call awaits an approval
        decision before executing.
    APPROVAL_DENIED: Agent-tier — approval was refused; the call will
        not execute.
    EXECUTING: The tool is running (meaningful for provider-executed
        tools; client executions live outside the transcript).
    OUTPUT_AVAILABLE: The result is present.
    OUTPUT_ERROR: Execution failed; the result carries the error.
````

### `ExecutedBy` { #ocai-chat-types-parts-executedby }

```python
class ExecutedBy:
    CLIENT: Final = 'client'
    PROVIDER: Final = 'provider'
```

````text
Canonical constants for the open `PartToolCall.executed_by` code.

Attributes:
    CLIENT: The caller runs the tool and replies with a
        `PartToolResult` (the classic function-calling loop).
    PROVIDER: The provider runs the tool server-side (built-in tools);
        results arrive as `PartServerToolResult`s.
````

### `ServerToolKind` { #ocai-chat-types-parts-servertoolkind }

```python
class ServerToolKind:
    WEB_SEARCH: Final = 'web_search'
    CODE_EXECUTION: Final = 'code_execution'
    MCP_CALL: Final = 'mcp_call'
```

````text
Canonical constants for the open `PartServerToolCall.kind` code.

An open vocabulary over the industry's fastest-moving surface — these
name the kinds core recognizes today; unrecognized kinds are preserved
verbatim and remain visible and reportable.

Attributes:
    WEB_SEARCH: A provider-side web search.
    CODE_EXECUTION: Provider-side code execution.
    MCP_CALL: A provider-brokered MCP tool call.
````

### `PartBase` { #ocai-chat-types-parts-partbase }

```python
class PartBase(IRObject):
    object: ClassVar[str] = 'part'
    id: str | None = field(default=None, kw_only=True)
    anchor: ProviderRef | None = field(default=None, kw_only=True)
    cache_hint: CacheHint | None = field(default=None, kw_only=True)
```

````text
The shared base of every canonical part — the universal optionals.

Concrete parts extend this and add their payload fields plus a fixed
`type` tag. The three fields here are cross-cutting: they exist on every
part so codecs, the accumulator, and conversion edges can address parts
uniformly.

Attributes:
    id: The part's stable identity within its message, when the provider
        (or ocai) assigned one. Preserving it is what lets `/responses`
        item semantics round-trip.
    anchor: Provider-side state backing this part (an item id, a file
        handle); inherits `ProviderRef`'s cross-interface `UNSUPPORTED`
        rule.
    cache_hint: A per-part prompt-caching marker [provisional].
````

### `PartText` { #ocai-chat-types-parts-parttext }

```python
class PartText(PartBase):
    text: str = ''
    annotations: list[Annotation] = field(default_factory=list[Annotation])
    type: Literal[PartType.TEXT] = field(default=PartType.TEXT)
```

````text
A run of text, with its citations anchored on it.

The workhorse part. Citations are span-anchored `Annotation`s carried
*here*, never in a side channel, so text and its attributions move
together through slicing, folding, and conversion.

Attributes:
    text: The text content.
    annotations: The span-anchored citations attributing ranges of
        `text` to sources.
    type: The part discriminator, fixed to `PartType.TEXT`.
````

#### `PartText.from_dict` { #ocai-chat-types-parts-parttext-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `PartText` from a serialized dict, totally.

Args:
    data: A mapping with `text`, optional `annotations`, and the
        shared part/envelope keys.

Returns:
    The decoded `PartText`.
````

### `PartImage` { #ocai-chat-types-parts-partimage }

```python
class PartImage(PartBase):
    source: Source | None = None
    type: Literal[PartType.IMAGE] = field(default=PartType.IMAGE)
```

````text
An image, referenced through the `Source` union.

Attributes:
    source: Where the image bytes live — inline base64, a URL, or a
        provider-hosted `SourceRef`.
    type: The part discriminator, fixed to `PartType.IMAGE`.
````

#### `PartImage.from_dict` { #ocai-chat-types-parts-partimage-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `PartImage` from a serialized dict, totally.

Args:
    data: A mapping with the nested `source` and the shared
        part/envelope keys.

Returns:
    The decoded `PartImage`.
````

### `PartAudio` { #ocai-chat-types-parts-partaudio }

```python
class PartAudio(PartBase):
    source: Source | None = None
    type: Literal[PartType.AUDIO] = field(default=PartType.AUDIO)
```

````text
An audio clip, referenced through the `Source` union.

Attributes:
    source: Where the audio bytes live — inline base64, a URL, or a
        provider-hosted `SourceRef` (e.g. an OpenAI audio id via its
        `ProviderRef`).
    type: The part discriminator, fixed to `PartType.AUDIO`.
````

#### `PartAudio.from_dict` { #ocai-chat-types-parts-partaudio-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `PartAudio` from a serialized dict, totally.

Args:
    data: A mapping with the nested `source` and the shared
        part/envelope keys.

Returns:
    The decoded `PartAudio`.
````

### `PartVideo` { #ocai-chat-types-parts-partvideo }

```python
class PartVideo(PartBase):
    source: Source | None = None
    start_offset: str | None = None
    end_offset: str | None = None
    fps: float | None = None
    type: Literal[PartType.VIDEO] = field(default=PartType.VIDEO)
```

````text
A video, referenced through the `Source` union.

The clipping/sampling metadata (Gemini `videoMetadata`) rides as per-part
optionals here; interfaces without it report the fields `ABSENT` via
their `CapabilityProfile` rather than dropping them silently.

Attributes:
    source: Where the video bytes live — inline base64, a URL, or a
        provider-hosted `SourceRef`.
    start_offset: Where playback/sampling starts, as a provider-shaped
        duration token (e.g. `"20s"`), verbatim.
    end_offset: Where playback/sampling ends, same form as
        `start_offset`.
    fps: The frame-sampling rate requested for the model.
    type: The part discriminator, fixed to `PartType.VIDEO`.
````

#### `PartVideo.from_dict` { #ocai-chat-types-parts-partvideo-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `PartVideo` from a serialized dict, totally.

Args:
    data: A mapping with the nested `source`, the optional video
        metadata, and the shared part/envelope keys.

Returns:
    The decoded `PartVideo`.
````

### `PartDocument` { #ocai-chat-types-parts-partdocument }

```python
class PartDocument(PartBase):
    source: Source | None = None
    title: str | None = None
    context: str | None = None
    type: Literal[PartType.DOCUMENT] = field(default=PartType.DOCUMENT)
```

````text
A document (PDF and friends), referenced through the `Source` union.

The citation-support metadata (Anthropic document `title`/`context`)
rides as per-part optionals; `Annotation.document_index` points back at
documents by position.

Attributes:
    source: Where the document bytes live — inline base64, a URL, or a
        provider-hosted `SourceRef`.
    title: The document's title, surfaced to the model for citations.
    context: Caller-supplied context about the document, surfaced to the
        model but never quoted as content.
    type: The part discriminator, fixed to `PartType.DOCUMENT`.
````

#### `PartDocument.from_dict` { #ocai-chat-types-parts-partdocument-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `PartDocument` from a serialized dict, totally.

Args:
    data: A mapping with the nested `source`, the optional
        title/context, and the shared part/envelope keys.

Returns:
    The decoded `PartDocument`.
````

### `PartReasoning` { #ocai-chat-types-parts-partreasoning }

```python
class PartReasoning(PartBase):
    text: str | None = None
    summary: str | None = None
    signature: ProviderRef | None = None
    opaque: ProviderRef | None = None
    type: Literal[PartType.REASONING] = field(default=PartType.REASONING)
```

````text
Model reasoning — ONE merged shape for every provider's idiom.

An OpenAI `/responses` reasoning item (summary + encrypted content), an
Anthropic thinking block (text + signature), and a Gemini thought
(text + thoughtSignature) are all **one part each**, never two
correlated ones — correlation-by-adjacency does not survive conversion.

Replay rules (per `ProviderRef.replay`): `signature` and `opaque` marked
`REQUIRED` are weighted as *breakage* in planning — dropping them
produces a 400 on replay, not degraded output.

Attributes:
    text: The raw reasoning text, when the provider surfaces it.
    summary: The provider-generated summary of the reasoning, when that
        is what the interface returns instead of (or besides) raw text.
    signature: The provider's integrity signature over the reasoning,
        required back on replay by some interfaces.
    opaque: Encrypted/opaque reasoning state (OpenAI
        `encrypted_content`) that must ride along verbatim.
    type: The part discriminator, fixed to `PartType.REASONING`.
````

#### `PartReasoning.from_dict` { #ocai-chat-types-parts-partreasoning-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `PartReasoning` from a serialized dict, totally.

Args:
    data: A mapping with any of the reasoning lanes and the shared
        part/envelope keys.

Returns:
    The decoded `PartReasoning`.
````

### `PartToolCall` { #ocai-chat-types-parts-parttoolcall }

```python
class PartToolCall(PartBase):
    call_id: str = ''
    name: str = ''
    args_json: str = ''
    status: str = ToolCallStatus.INPUT_COMPLETE
    executed_by: str = ExecutedBy.CLIENT
    type: Literal[PartType.TOOL_CALL] = field(default=PartType.TOOL_CALL)
```

````text
The model's request to invoke a named tool.

`args_json` is **the authoritative wire truth**: every first-party
interface streams tool arguments as string fragments, so the canonical
form is the raw string, parsed on read via `args()` — never re-serialized
through a dict that could reorder or renormalize what the model wrote.

Cross-provider conversion regenerates `call_id`s (providers reject
foreign id shapes); that is recorded as a `SemanticShift`
(`ID_REGENERATED`), never silent.

Attributes:
    call_id: The id correlating this call with its `PartToolResult`
        sibling.
    name: The tool name, matching a request `Tool.name`.
    args_json: The arguments as the verbatim JSON string the model
        produced.
    status: The open lifecycle code shared with streaming; constants on
        `ToolCallStatus`.
    executed_by: Who runs the tool; constants on `ExecutedBy`.
    type: The part discriminator, fixed to `PartType.TOOL_CALL`.
````

#### `PartToolCall.args` { #ocai-chat-types-parts-parttoolcall-args }

```python
def args(self) -> Any
```

````text
Parse `args_json` on read.

Parse-on-read keeps the wire string authoritative: the parsed form
is a *view*, never stored, so canonical equality (`canonjson`) can
apply its parse-compare/preserve-verbatim rule to the string lane.

Returns:
    The parsed JSON value (typically a dict of arguments); `None`
    when `args_json` is empty.

Raises:
    json.JSONDecodeError: If `args_json` is not valid JSON — a
        *read-time* error by design; decode never parses it.
````

#### `PartToolCall.from_dict` { #ocai-chat-types-parts-parttoolcall-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `PartToolCall` from a serialized dict, totally.

`args_json` passes through verbatim — it is never parsed at decode
time.

Args:
    data: A mapping with the call fields and the shared
        part/envelope keys.

Returns:
    The decoded `PartToolCall`.
````

### `PartToolResult` { #ocai-chat-types-parts-parttoolresult }

```python
class PartToolResult(PartBase):
    call_id: str = ''
    parts: list[Part] = field(default_factory=list['Part'])
    is_error: bool = False
    type: Literal[PartType.TOOL_RESULT] = field(default=PartType.TOOL_RESULT)
```

````text
The caller's answer to a `PartToolCall`, correlated by `call_id`.

A *sibling* of the call in the transcript, never nested inside it —
nesting is a provider idiom (Gemini) that codecs flatten. The result
body is itself a list of parts, so tools can return text, images, and
documents without a parallel content model.

Attributes:
    call_id: The id of the `PartToolCall` this answers.
    parts: The result content (text/image/document parts nest here).
    is_error: Whether the tool execution failed; the parts then carry
        the error content.
    type: The part discriminator, fixed to `PartType.TOOL_RESULT`.
````

#### `PartToolResult.from_dict` { #ocai-chat-types-parts-parttoolresult-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `PartToolResult` from a serialized dict, totally.

Nested `parts` are decoded through `PART_REGISTRY`, so unknown
nested tags fall back to `PartUnknown` like everywhere else.

Args:
    data: A mapping with `call_id`, nested `parts`, `is_error`, and
        the shared part/envelope keys.

Returns:
    The decoded `PartToolResult`.
````

### `PartServerToolCall` { #ocai-chat-types-parts-partservertoolcall }

```python
class PartServerToolCall(PartBase):
    kind: str = ''
    call_id: str = ''
    status: str = ToolCallStatus.EXECUTING
    payload: dict[str, Any] = field(default_factory=dict[str, Any])
    type: Literal[PartType.SERVER_TOOL_CALL] = field(default=PartType.SERVER_TOOL_CALL)
```

````text
A provider-executed built-in tool invocation — the typed spine.

Built-in tools (web search, code execution, MCP) are the industry's
fastest-moving surface, so this part types only the spine — kind, id,
lifecycle — and keeps the provider payload **verbatim and
byte-faithful**: visible and reportable without freezing shapes that
change monthly.

Attributes:
    kind: The open tool-kind code; constants on `ServerToolKind`.
    call_id: The id correlating this call with its
        `PartServerToolResult` sibling.
    status: The open lifecycle code shared with `ToolCallStatus`.
    payload: The provider's invocation payload, verbatim.
    type: The part discriminator, fixed to
        `PartType.SERVER_TOOL_CALL`.
````

#### `PartServerToolCall.from_dict` { #ocai-chat-types-parts-partservertoolcall-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `PartServerToolCall` from a serialized dict, totally.

Args:
    data: A mapping with the spine fields, the verbatim `payload`,
        and the shared part/envelope keys.

Returns:
    The decoded `PartServerToolCall`.
````

### `PartServerToolResult` { #ocai-chat-types-parts-partservertoolresult }

```python
class PartServerToolResult(PartBase):
    kind: str = ''
    call_id: str = ''
    status: str = ToolCallStatus.OUTPUT_AVAILABLE
    payload: dict[str, Any] = field(default_factory=dict[str, Any])
    type: Literal[PartType.SERVER_TOOL_RESULT] = field(default=PartType.SERVER_TOOL_RESULT)
```

````text
A provider-executed built-in tool result, correlated by `call_id`.

The result half of the `PartServerToolCall` spine; same design — typed
identity and lifecycle over a verbatim payload.

Attributes:
    kind: The open tool-kind code; constants on `ServerToolKind`.
    call_id: The id of the `PartServerToolCall` this answers.
    status: The open lifecycle code; typically `OUTPUT_AVAILABLE` or
        `OUTPUT_ERROR`.
    payload: The provider's result payload, verbatim and byte-faithful.
    type: The part discriminator, fixed to
        `PartType.SERVER_TOOL_RESULT`.
````

#### `PartServerToolResult.from_dict` { #ocai-chat-types-parts-partservertoolresult-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `PartServerToolResult` from a serialized dict, totally.

Args:
    data: A mapping with the spine fields, the verbatim `payload`,
        and the shared part/envelope keys.

Returns:
    The decoded `PartServerToolResult`.
````

### `PartRefusal` { #ocai-chat-types-parts-partrefusal }

```python
class PartRefusal(PartBase):
    text: str = ''
    type: Literal[PartType.REFUSAL] = field(default=PartType.REFUSAL)
```

````text
A refusal surfaced as content (OpenAI's refusal lane).

Pairs with `FinishInfo.reason == "refusal"`. Boundary rule: a
*mid-generation* refusal is a response (this part); a *pre-generation*
block is a `ContentFilterError`, not a response at all.

Attributes:
    text: The refusal text.
    type: The part discriminator, fixed to `PartType.REFUSAL`.
````

#### `PartRefusal.from_dict` { #ocai-chat-types-parts-partrefusal-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `PartRefusal` from a serialized dict, totally.

Args:
    data: A mapping with `text` and the shared part/envelope keys.

Returns:
    The decoded `PartRefusal`.
````

### `PartOpaque` { #ocai-chat-types-parts-partopaque }

```python
class PartOpaque(PartBase):
    kind: str = ''
    payload: dict[str, Any] = field(default_factory=dict[str, Any])
    type: Literal[PartType.OPAQUE] = field(default=PartType.OPAQUE)
```

````text
*Deliberate* provider-unique content, census-registered.

The escape hatch for content a codec understands but canonical cannot
(yet) represent first-class. Every `kind` must be schema-registered in
`spec/extensions/` — an unregistered kind is a CI failure — so the
opaque lane can never silently become the real schema. Strictly distinct
from `PartUnknown`, which is the decoder fallback for *future canonical*
tags.

Attributes:
    kind: The namespaced, censused content key
        (e.g. `"anthropic.mid_conv_system"`).
    payload: The provider content, verbatim.
    type: The part discriminator, fixed to `PartType.OPAQUE`.
````

#### `PartOpaque.from_dict` { #ocai-chat-types-parts-partopaque-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `PartOpaque` from a serialized dict, totally.

Args:
    data: A mapping with the censused `kind`, the verbatim
        `payload`, and the shared part/envelope keys.

Returns:
    The decoded `PartOpaque`.
````

### `PartUnknown` { #ocai-chat-types-parts-partunknown }

```python
class PartUnknown(PartBase):
    data: dict[str, Any] = field(default_factory=dict[str, Any])
    type: str = PartType.UNDEFINED.value
```

````text
Decoder fallback for a part tag this revision does not know.

Preserves the payload verbatim (byte-faithful through `to_dict`) so a
*future* canonical part survives decode/encode untouched and can be
upgraded later via IR self-migration edges. Total decode's safety net —
never constructed deliberately (that is `PartOpaque`'s job).

Attributes:
    data: The verbatim serialized payload, including its original tag.
    type: The unrecognized discriminator value, preserved verbatim.
````

#### `PartUnknown.to_dict` { #ocai-chat-types-parts-partunknown-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize back to the verbatim payload this instance preserved.

Returns:
    A copy of the original serialized mapping, untouched.
````

#### `PartUnknown.from_dict` { #ocai-chat-types-parts-partunknown-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Preserve an unrecognized part payload verbatim.

Args:
    data: The serialized mapping whose tag no registered part
        matched.

Returns:
    A new `PartUnknown` carrying the payload untouched.
````

### `Part` { #ocai-chat-types-parts-part }

```python
type Part = PartText | PartImage | PartAudio | PartVideo | PartDocument | PartReasoning | PartToolCall | PartToolResult | PartServerToolCall | PartServerToolResult | PartRefusal | PartOpaque | PartUnknown
```

### `PART_REGISTRY` { #ocai-chat-types-parts-part-registry }

```python
PART_REGISTRY: TagRegistry[Any] = TagRegistry(unknown=PartUnknown)
```

### `cast_part` { #ocai-chat-types-parts-cast-part }

```python
def cast_part(data: dict[str, Any]) -> Part
```

````text
Decode a serialized part into its concrete `Part` variant.

Dispatches on the `type` tag via `PART_REGISTRY`; unknown tags decode to
`PartUnknown` — this function never raises on unknown input.

Args:
    data: The serialized part mapping, including its `type`
        discriminator.

Returns:
    The decoded `Part` variant.
````

## `ocai.chat.types.request`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/types/request.py)

### `ChatRequest` { #ocai-chat-types-request-chatrequest }

```python
class ChatRequest(IRObject):
    object: ClassVar[str] = 'chat.request'
    messages: list[Message]
    tools: list[ToolDefinition] | None = None
    tool_choice: ToolChoice | None = None
    config: ChatConfig | None = None
    anchors: list[ProviderRef] | None = None
```

````text
A provider-neutral chat generation request — a pure graph payload.

Enters the lifecycle at the port (`ChatModel.chat(request)`), rides the
interceptor chain unchanged, and is encoded by the conversion graph from
`CANONICAL_CHAT_REQUEST` to the resolved provider node. This revision is
single-candidate: there is no `n` — a request for multiple candidates fails
admission at the codec. And no `model`: the model name is routing data
bound to the model object at construction (§3.4), injected on the wire by
the codec from the bound resource — never carried in the request.

Attributes:
    messages: The conversation so far, in order.
    tools: The tools the model may call, if any.
    tool_choice: The whether/which tool policy, if constrained.
    config: The typed generation configuration, if any.
    anchors: Scoped continuation references; availability requires a qualified codec.
````

#### `ChatRequest.from_dict` { #ocai-chat-types-request-chatrequest-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `ChatRequest` from a serialized dict, totally.

The true inverse of `to_dict`: `messages`, `tools`, `tool_choice`,
and `config` all decode through their typed `from_dict`s (the old
scaffold left tools/config as raw dicts — that asymmetry is dead).

Args:
    data: A mapping with the request fields plus the common IR
        envelope keys; unknown keys sweep to `extensions`.

Returns:
    The decoded `ChatRequest`.
````

## `ocai.chat.types.response`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/types/response.py)

### `ResponseInfo` { #ocai-chat-types-response-responseinfo }

```python
class ResponseInfo(IRObject):
    id: ProviderRef | None = None
    model: str | None = None
    created: datetime | None = None
```

````text
The provider anchors identifying one response.

Attributes:
    id: The response's provider-side identity as a `ProviderRef`
        (kind `"response_id"`), reusable as a follow-up anchor; crossing
        another `(provider, interface)` is reported `UNSUPPORTED`.
    model: The provider's echo of the model that actually served the
        call (which may be more specific than the requested alias).
    created: When the provider says the response was created.
````

#### `ResponseInfo.from_dict` { #ocai-chat-types-response-responseinfo-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `ResponseInfo` from a serialized dict, totally.

Args:
    data: A mapping with the nested `id`, the optional `model`, an
        ISO-8601 `created`, and the common IR envelope keys.

Returns:
    The decoded `ResponseInfo`.
````

### `ChatResponse` { #ocai-chat-types-response-chatresponse }

```python
class ChatResponse(IRObject):
    object: ClassVar[str] = 'chat.response'
    message: Message
    finish: FinishInfo | None = None
    usage: Usage | None = None
    info: ResponseInfo | None = None
    raw: Any | None = field(default=None, kw_only=True)
```

````text
A non-streaming chat result — pure payload, no report.

Produced by the response leg of the conversion graph (provider node →
`CANONICAL_CHAT_RESPONSE`) or by `StreamAccumulator.fold`, whose output
must equal it (the fold law). Delivered to callers inside
`CallResult.value`; the route, report, and untouched provider body ride
the `CallResult`, keeping this type identical whether it came from a
live call, a fold, or a fixture.

Attributes:
    message: The model's reply turn.
    finish: Why generation stopped, when reported.
    usage: What the call consumed, when reported.
    info: The response's provider anchors, when reported.
    raw: The provider's untouched response body for power users — never
        contains credentials. Kept keyword-only and off the positional
        construction path.
````

#### `ChatResponse.validated_annotations` { #ocai-chat-types-response-chatresponse-validated-annotations }

```python
def validated_annotations(self) -> Self
```

````text
Detach the final response and validate citations against each text part.
````

#### `ChatResponse.from_dict` { #ocai-chat-types-response-chatresponse-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `ChatResponse` from a serialized dict, totally.

Args:
    data: A mapping with the nested `message`, `finish`, `usage`,
        `info`, an optional `raw`, and the common IR envelope keys.

Returns:
    The decoded `ChatResponse`.
````

## `ocai.chat.types.role`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/types/role.py)

### `Role` { #ocai-chat-types-role-role }

```python
class Role:
    USER: Final = 'user'
    MODEL: Final = 'model'
    SYSTEM: Final = 'system'
    TOOL: Final = 'tool'
```

````text
Canonical constants for the open message-role code.

`Message.role` is a plain `str`; these constants name the values core
itself understands. Codecs map provider wire roles onto them (OpenAI
`assistant` → `MODEL`) and preserve anything unmapped verbatim, so a
role this revision has never seen survives a round trip untouched.

Attributes:
    USER: The end user speaking to the model.
    MODEL: The model / assistant. Canonical name is `model`, not
        `assistant` — codecs translate.
    SYSTEM: System-level instructions.
    TOOL: A tool returning a result into the conversation.
````

### `decode_role` { #ocai-chat-types-role-decode-role }

```python
def decode_role(value: str | None) -> str
```

````text
Normalize a wire role into the canonical open code — totally.

Known values are case-normalized to their canonical constant; unknown
values are preserved verbatim (never coerced, never raised on); a missing
role decodes to the empty string so the caller — the codec, which knows
its wire context — decides what an absent role means.

Args:
    value: The role read off the wire, or None when the wire carried
        none.

Returns:
    The canonical role constant, the verbatim unknown value, or `""`
    when `value` is None.
````

### `encode_role` { #ocai-chat-types-role-encode-role }

```python
def encode_role(role: str) -> str
```

````text
Render a canonical role as its wire value.

The canonical constants are already wire-ready strings, so this is the
identity — it exists as the named inverse of `decode_role` so codecs
have exactly one hook to specialize per dialect (e.g. emitting
`assistant` for `Role.MODEL` on OpenAI wires).

Args:
    role: The canonical (or preserved-verbatim) role code.

Returns:
    The role, verbatim.
````

## `ocai.chat.types.stream`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/types/stream.py)

### `INCOMPLETE_EXTENSION` { #ocai-chat-types-stream-incomplete-extension }

```python
INCOMPLETE_EXTENSION: Final = 'ocai.incomplete'
```

### `SIGNATURE_BUFFER_EXTENSION` { #ocai-chat-types-stream-signature-buffer-extension }

```python
SIGNATURE_BUFFER_EXTENSION: Final = 'ocai.signature_buffer'
```

### `ChunkType` { #ocai-chat-types-stream-chunktype }

```python
class ChunkType(str, Enum):
    STREAM_START = 'streamStart'
    STREAM_STOP = 'streamStop'
    PART_START = 'partStart'
    PART_DELTA = 'partDelta'
    PART_STOP = 'partStop'
    USAGE = 'usage'
    FINISH = 'finish'
    METADATA = 'metadata'
    ERROR = 'error'
    RAW = 'raw'
    PING = 'ping'
```

````text
The kind of a streamed `ChatChunk` event.

The wire vocabulary of the canonical chunk stream. `STREAM_STOP` is the
terminal event and carries `ChatChunk.end` — a stream that ends without
one was aborted, and the accumulator seals its parts `incomplete`.

Attributes:
    STREAM_START: The stream has begun.
    STREAM_STOP: The terminal event; carries the authoritative
        `StreamEnd`.
    PART_START: A new content part is starting; carries the part
        skeleton in `ChatChunk.part`.
    PART_DELTA: An incremental update; carries `ChatChunk.delta`.
    PART_STOP: The current part is complete; may carry the final part,
        which MUST equal the delta accumulation (fold law).
    USAGE: A usage update; `ChatChunk.usage_cumulative` says whether it
        replaces or extends previous updates.
    FINISH: The generation finished; carries `ChatChunk.finish`.
    METADATA: A metadata-bearing event.
    ERROR: A mid-stream error; carries the wire-shaped
        `ChatChunk.error`.
    RAW: An untouched provider event passed through.
    PING: A keep-alive ping.
````

### `DeltaType` { #ocai-chat-types-stream-deltatype }

```python
class DeltaType(str, Enum):
    UNDEFINED = 'undefined'
    TEXT = 'text'
    TOOL_ARGS = 'tool_args'
    REASONING = 'reasoning'
    SIGNATURE = 'signature'
    ANNOTATION = 'annotation'
    REFUSAL = 'refusal'
    BLOB = 'blob'
```

````text
Canonical discriminator tags for the core `Delta` variants.

Constants for the tags core ships — the union stays open through
`DELTA_REGISTRY` (unknown tags decode to `DeltaUnknown`).

Attributes:
    UNDEFINED: No delta kind set (the unknown/placeholder tag).
    TEXT: A text fragment (`DeltaText`).
    TOOL_ARGS: A tool-argument string fragment (`DeltaToolArgs`).
    REASONING: A reasoning fragment (`DeltaReasoning`).
    SIGNATURE: A reasoning-signature fragment (`DeltaSignature`).
    ANNOTATION: A completed citation (`DeltaAnnotation`).
    REFUSAL: A refusal-text fragment (`DeltaRefusal`).
    BLOB: A binary/base64 media fragment (`DeltaBlob`).
````

### `DeltaText` { #ocai-chat-types-stream-deltatext }

```python
class DeltaText(IRObject):
    text: str = ''
    type: Literal[DeltaType.TEXT] = field(default=DeltaType.TEXT)
```

````text
A text fragment appended to the open `PartText`.

Attributes:
    text: The fragment, appended verbatim.
    type: The delta discriminator, fixed to `DeltaType.TEXT`.
````

#### `DeltaText.from_dict` { #ocai-chat-types-stream-deltatext-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `DeltaText` from a serialized dict, totally.

Args:
    data: A mapping with `text` and the common IR envelope keys.

Returns:
    The decoded `DeltaText`.
````

### `DeltaToolArgs` { #ocai-chat-types-stream-deltatoolargs }

```python
class DeltaToolArgs(IRObject):
    fragment: str = ''
    type: Literal[DeltaType.TOOL_ARGS] = field(default=DeltaType.TOOL_ARGS)
```

````text
A tool-argument fragment appended to the open `PartToolCall`.

The fragment is a **raw string** — every interface streams argument
JSON as string pieces — concatenated onto `args_json` and parsed once,
at `PART_STOP`, never per-fragment (fragments are rarely valid JSON on
their own).

Attributes:
    fragment: The raw argument-string fragment, appended verbatim.
    type: The delta discriminator, fixed to `DeltaType.TOOL_ARGS`.
````

#### `DeltaToolArgs.from_dict` { #ocai-chat-types-stream-deltatoolargs-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `DeltaToolArgs` from a serialized dict, totally.

Args:
    data: A mapping with `fragment` and the common IR envelope
        keys.

Returns:
    The decoded `DeltaToolArgs`.
````

### `DeltaReasoning` { #ocai-chat-types-stream-deltareasoning }

```python
class DeltaReasoning(IRObject):
    text: str | None = None
    summary: str | None = None
    type: Literal[DeltaType.REASONING] = field(default=DeltaType.REASONING)
```

````text
A reasoning fragment appended to the open `PartReasoning`.

Mirrors the part's two textual lanes: raw thinking text and provider
summaries stream independently on some interfaces.

Attributes:
    text: A raw reasoning-text fragment, when streamed.
    summary: A summary fragment, when streamed.
    type: The delta discriminator, fixed to `DeltaType.REASONING`.
````

#### `DeltaReasoning.from_dict` { #ocai-chat-types-stream-deltareasoning-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `DeltaReasoning` from a serialized dict, totally.

Args:
    data: A mapping with the optional `text`/`summary` and the
        common IR envelope keys.

Returns:
    The decoded `DeltaReasoning`.
````

### `DeltaSignature` { #ocai-chat-types-stream-deltasignature }

```python
class DeltaSignature(IRObject):
    signature: str = ''
    type: Literal[DeltaType.SIGNATURE] = field(default=DeltaType.SIGNATURE)
```

````text
A reasoning-signature fragment for the open `PartReasoning`.

Signatures (Anthropic `signature_delta`, Gemini `thoughtSignature`)
stream as opaque string fragments; the codec's transducer mints the
final `ProviderRef` on the sealed part.

Attributes:
    signature: The signature fragment, verbatim.
    type: The delta discriminator, fixed to `DeltaType.SIGNATURE`.
````

#### `DeltaSignature.from_dict` { #ocai-chat-types-stream-deltasignature-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `DeltaSignature` from a serialized dict, totally.

Args:
    data: A mapping with `signature` and the common IR envelope
        keys.

Returns:
    The decoded `DeltaSignature`.
````

### `DeltaAnnotation` { #ocai-chat-types-stream-deltaannotation }

```python
class DeltaAnnotation(IRObject):
    annotation: Annotation | None = None
    type: Literal[DeltaType.ANNOTATION] = field(default=DeltaType.ANNOTATION)
```

````text
A completed citation appended to the open `PartText`.

Annotations arrive whole (providers emit them as units, not fragments)
and are appended to the part's `annotations` list in arrival order.

Attributes:
    annotation: The completed span-anchored citation.
    type: The delta discriminator, fixed to `DeltaType.ANNOTATION`.
````

#### `DeltaAnnotation.from_dict` { #ocai-chat-types-stream-deltaannotation-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `DeltaAnnotation` from a serialized dict, totally.

Args:
    data: A mapping with the nested `annotation` and the common IR
        envelope keys.

Returns:
    The decoded `DeltaAnnotation`.
````

### `DeltaRefusal` { #ocai-chat-types-stream-deltarefusal }

```python
class DeltaRefusal(IRObject):
    text: str = ''
    type: Literal[DeltaType.REFUSAL] = field(default=DeltaType.REFUSAL)
```

````text
A refusal-text fragment appended to the open `PartRefusal`.

Attributes:
    text: The fragment, appended verbatim.
    type: The delta discriminator, fixed to `DeltaType.REFUSAL`.
````

#### `DeltaRefusal.from_dict` { #ocai-chat-types-stream-deltarefusal-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `DeltaRefusal` from a serialized dict, totally.

Args:
    data: A mapping with `text` and the common IR envelope keys.

Returns:
    The decoded `DeltaRefusal`.
````

### `DeltaBlob` { #ocai-chat-types-stream-deltablob }

```python
class DeltaBlob(IRObject):
    data: str = ''
    type: Literal[DeltaType.BLOB] = field(default=DeltaType.BLOB)
```

````text
A base64 media fragment appended to the open media part.

Streams audio/image output (e.g. OpenAI audio deltas) as base64 string
pieces; the sealed part's inline `SourceBase64` is their concatenation.

Attributes:
    data: The base64 fragment, appended verbatim.
    type: The delta discriminator, fixed to `DeltaType.BLOB`.
````

#### `DeltaBlob.from_dict` { #ocai-chat-types-stream-deltablob-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `DeltaBlob` from a serialized dict, totally.

Args:
    data: A mapping with the base64 `data` and the common IR
        envelope keys.

Returns:
    The decoded `DeltaBlob`.
````

### `DeltaUnknown` { #ocai-chat-types-stream-deltaunknown }

```python
class DeltaUnknown(IRObject):
    data: dict[str, Any] = field(default_factory=dict[str, Any])
    type: str = DeltaType.UNDEFINED.value
```

````text
Decoder fallback for a delta tag this revision does not know.

Preserves the payload verbatim, mirroring `PartUnknown` — a future
canonical delta survives decode/encode untouched. Total decode's
safety net for the streaming lane.

Attributes:
    data: The verbatim serialized payload, including its original tag.
    type: The unrecognized discriminator value, preserved verbatim.
````

#### `DeltaUnknown.to_dict` { #ocai-chat-types-stream-deltaunknown-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize back to the verbatim payload this instance preserved.

Returns:
    A copy of the original serialized mapping, untouched.
````

#### `DeltaUnknown.from_dict` { #ocai-chat-types-stream-deltaunknown-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Preserve an unrecognized delta payload verbatim.

Args:
    data: The serialized mapping whose tag no registered delta
        matched.

Returns:
    A new `DeltaUnknown` carrying the payload untouched.
````

### `Delta` { #ocai-chat-types-stream-delta }

```python
type Delta = DeltaText | DeltaToolArgs | DeltaReasoning | DeltaSignature | DeltaAnnotation | DeltaRefusal | DeltaBlob | DeltaUnknown
```

### `DELTA_REGISTRY` { #ocai-chat-types-stream-delta-registry }

```python
DELTA_REGISTRY: TagRegistry[Any] = TagRegistry(unknown=DeltaUnknown)
```

### `cast_delta` { #ocai-chat-types-stream-cast-delta }

```python
def cast_delta(data: dict[str, Any]) -> Delta
```

````text
Decode a serialized delta into its concrete `Delta` variant.

Dispatches on the `type` tag via `DELTA_REGISTRY`; unknown tags decode
to `DeltaUnknown` — this function never raises on unknown input.

Args:
    data: The serialized delta mapping, including its `type`
        discriminator.

Returns:
    The decoded `Delta` variant.
````

### `ErrorInfo` { #ocai-chat-types-stream-errorinfo }

```python
class ErrorInfo:
    code: str
    native: Any | None = None
    retryable: bool | None = None
```

````text
A mid-stream error in wire shape — data, not just an exception.

Carried on `ChatChunk.error` so a recorded stream replays identically
to a live one; the driver *also* raises the mapped taxonomy exception,
but the stream's own record is this value.

Attributes:
    code: The canonical error-taxonomy code (`"rate_limit"`, `"auth"`,
        `"context_length"`, `"content_filter"`, `"transient"`,
        `"unknown"`), open.
    native: The provider's verbatim error payload.
    retryable: Whether retrying the call could succeed, when the
        taxonomy mapping knows.
````

#### `ErrorInfo.to_dict` { #ocai-chat-types-stream-errorinfo-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize the error to a plain JSON-compatible dict.

Returns:
    A dict with `code` and the optional `native`/`retryable` when
    set.
````

#### `ErrorInfo.from_dict` { #ocai-chat-types-stream-errorinfo-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build an `ErrorInfo` from a serialized dict, totally.

Args:
    data: A mapping with `code` and the optional
        `native`/`retryable`.

Returns:
    The decoded `ErrorInfo`.
````

### `StreamEnd` { #ocai-chat-types-stream-streamend }

```python
class StreamEnd(IRObject):
    usage: Usage | None = None
    finish: FinishInfo | None = None
    report: FidelityReport | None = None
```

````text
The authoritative terminal record of a stream.

Carried by the `STREAM_STOP` chunk. Its `usage` and `finish` override
any mid-stream updates in the fold, and `report` is the stream's
`FidelityReport` — the streaming path's one report home, mirroring
`CallResult.report` on the blocking path.

Attributes:
    usage: The final consumption record, when reported.
    finish: The final stop record, when reported.
    report: The fidelity account of the stream's conversion legs.
````

#### `StreamEnd.from_dict` { #ocai-chat-types-stream-streamend-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `StreamEnd` from a serialized dict, totally.

Args:
    data: A mapping with the nested `usage`/`finish`/`report` and
        the common IR envelope keys.

Returns:
    The decoded `StreamEnd`.
````

### `ChatChunk` { #ocai-chat-types-stream-chatchunk }

```python
class ChatChunk(IRObject):
    object: ClassVar[str] = 'chat.chunk'
    type: ChunkType | str
    seq: int | None = None
    index: int | None = None
    part: Part | None = None
    delta: Delta | None = None
    usage: Usage | None = None
    usage_cumulative: bool | None = None
    finish: FinishInfo | None = None
    error: ErrorInfo | None = None
    end: StreamEnd | None = None
    info: ResponseInfo | None = field(default=None, kw_only=True)
    raw_event: Any | None = field(default=None, kw_only=True)
```

````text
The one canonical streaming event — every provider frame becomes one.

Emitted by dialect codecs (via `StreamEdge` transducers in the graph),
consumed by user code through `ChatStream`/`AsyncChatStream`, and folded
into a `ChatResponse` by `StreamAccumulator`. `type` says which lanes
are populated; everything else is None.

Attributes:
    type: The event kind; unknown wire kinds decode to their verbatim
        string (total decode).
    seq: The chunk's zero-based position in the canonical stream,
        stamped by the emitting codec — the replay/fold ordering key.
    index: The content-part slot this event concerns, for the
        `PART_*` types.
    part: The part skeleton (`PART_START`) or authoritative final part
        (`PART_STOP`).
    delta: The incremental update (`PART_DELTA`).
    usage: A consumption update (`USAGE`).
    usage_cumulative: Whether `usage` replaces (True) or extends
        (False) previous updates; None when unspecified.
    finish: The stop record (`FINISH`).
    error: The wire-shaped mid-stream error (`ERROR`).
    end: The authoritative terminal record (`STREAM_STOP`).
    info: Partial response identity/provenance, accumulated independently of content.
    raw_event: The untouched provider frame this chunk was decoded
        from, for power users and the wiretap archive. Keyword-only.
````

#### `ChatChunk.from_dict` { #ocai-chat-types-stream-chatchunk-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `ChatChunk` from a serialized dict, totally.

An unknown `type` string is preserved verbatim rather than raised
on; every nested lane decodes through its own total decoder.

Args:
    data: A mapping with `type` and any populated lanes plus the
        common IR envelope keys.

Returns:
    The decoded `ChatChunk`.
````

### `StreamAccumulator` { #ocai-chat-types-stream-streamaccumulator }

```python
class StreamAccumulator
```

````text
Folds a canonical chunk stream into the equivalent `ChatResponse`.

The executable half of the fold law: `fold(stream(request))` must be
semantically equal to `complete(request)`, and `PART_STOP`'s final part
must equal its delta accumulation — the conformance harness asserts
both over fold-triple fixtures.

Mechanics per chunk type: `PART_START` opens a *slot* holding the part
skeleton; `PART_DELTA` applies the typed delta to the open slot
(append semantics per delta type); `PART_STOP` *seals* the slot,
preferring the authoritative final part when the codec sent one;
`USAGE`/`FINISH` track the latest mid-stream records; `STREAM_STOP`
records the authoritative `StreamEnd`, which overrides them.

The fold has its own honesty channel: a delta it cannot apply (a
mismatched delta/part pair, a `DeltaUnknown`, an unaccumulated blob) is
never silently swallowed — each records a `FieldLoss`, surfaced as one
`EdgeReport` via `report` and merged into the terminal
`StreamEnd.report` at `finalize`.

Use it incrementally (`feed` per chunk, then `finalize`) or in one shot
via the `fold` classmethod.
````

#### `StreamAccumulator.__init__` { #ocai-chat-types-stream-streamaccumulator---init-- }

```python
def __init__(self) -> None
```

````text
Create an empty accumulator ready to receive a stream.
````

#### `StreamAccumulator.feed` { #ocai-chat-types-stream-streamaccumulator-feed }

```python
def feed(self, chunk: ChatChunk) -> None
```

````text
Apply one chunk to the accumulation state.

Args:
    chunk: The next canonical chunk, in `seq` order.
````

#### `StreamAccumulator.report` { #ocai-chat-types-stream-streamaccumulator-report }

```python
@property
def report(self) -> FidelityReport
```

````text
The fold's own fidelity account, freshly assembled.

Empty when every delta applied cleanly; otherwise one `EdgeReport`
(canonical chunk node → canonical response node) carrying the
recorded `FieldLoss`es in arrival order. `finalize` merges the same
edge into the terminal `StreamEnd.report`; this property is the
report's home when a stream aborted before its `STREAM_STOP`.
````

#### `StreamAccumulator.finalize` { #ocai-chat-types-stream-streamaccumulator-finalize }

```python
def finalize(self) -> ChatResponse
```

````text
Assemble the folded `ChatResponse` from the accumulated state.

The terminal `StreamEnd`'s usage/finish are authoritative over
mid-stream updates. An aborted stream (no `STREAM_STOP` arrived)
still folds, but every slot it left open is sealed with an explicit
`extensions[INCOMPLETE_EXTENSION]` marker — accumulated content is
never passed off as complete. Any fold losses merge into the
terminal `StreamEnd.report` (once, however many times `finalize`
runs); an aborted stream's losses stay reachable via `report`.

Returns:
    The response the equivalent blocking call would have returned.
````

#### `StreamAccumulator.fold` { #ocai-chat-types-stream-streamaccumulator-fold }

```python
@classmethod
def fold(cls, chunks: Iterable[ChatChunk]) -> ChatResponse
```

````text
Fold a whole chunk stream into its equivalent response.

The normative law's entry point: `fold(stream(request))` must be
semantically equal to `complete(request)`.

Args:
    chunks: The canonical chunks, in stream order.

Returns:
    The folded `ChatResponse`.
````

### `ChatStream` { #ocai-chat-types-stream-chatstream }

```python
class ChatStream
```

````text
An owned synchronous stream; use `with` or close explicitly on early exit.

Normal exhaustion preserves `.end`. `.outcome` also records aborted
execution and known accounting; it never synthesizes successful StreamEnd.
A stream created but never consumed is pending until explicitly closed.
Garbage collection is not a lifecycle or durable-audit guarantee.
````

#### `ChatStream.__init__` { #ocai-chat-types-stream-chatstream---init-- }

```python
def __init__(self, chunks: Iterator[ChatChunk], *, report: Callable[[], FidelityReport | None] | None=None) -> None
```

````text
Wrap chunks and an optional snapshot of conversion evidence.
````

#### `ChatStream.end` { #ocai-chat-types-stream-chatstream-end }

```python
@property
def end(self) -> StreamEnd | None
```

````text
The successful terminal record, or None for pending/aborted streams.
````

#### `ChatStream.outcome` { #ocai-chat-types-stream-chatstream-outcome }

```python
@property
def outcome(self) -> StreamOutcome | None
```

````text
The single execution outcome once exhaustion or close finalizes it.
````

#### `ChatStream.on_termination` { #ocai-chat-types-stream-chatstream-on-termination }

```python
def on_termination(self, callback: Callable[[StreamOutcome], None]) -> None
```

````text
Register a passive notification; failures are isolated, never admission.
````

#### `ChatStream.close` { #ocai-chat-types-stream-chatstream-close }

```python
def close(self) -> None
```

````text
Release upstream promptly and finalize once; repeated closes are inert.
````

#### `ChatStream.fold` { #ocai-chat-types-stream-chatstream-fold }

```python
def fold(self) -> ChatResponse
```

````text
Drain and fold the remaining chunks; failed streams still raise.
````

### `AsyncChatStream` { #ocai-chat-types-stream-asyncchatstream }

```python
class AsyncChatStream
```

````text
Owned async stream; `async with` guarantees close on consumer cancellation.
````

#### `AsyncChatStream.__init__` { #ocai-chat-types-stream-asyncchatstream---init-- }

```python
def __init__(self, chunks: AsyncIterator[ChatChunk], *, report: Callable[[], FidelityReport | None] | None=None) -> None
```

````text
Wrap async chunks and optional conversion evidence without buffering.
````

#### `AsyncChatStream.end` { #ocai-chat-types-stream-asyncchatstream-end }

```python
@property
def end(self) -> StreamEnd | None
```

````text
The successful terminal record, or None for pending/aborted streams.
````

#### `AsyncChatStream.outcome` { #ocai-chat-types-stream-asyncchatstream-outcome }

```python
@property
def outcome(self) -> StreamOutcome | None
```

````text
The single execution outcome once exhaustion or close finalizes it.
````

#### `AsyncChatStream.on_termination` { #ocai-chat-types-stream-asyncchatstream-on-termination }

```python
def on_termination(self, callback: Callable[[StreamOutcome], None]) -> None
```

````text
Register a passive notification; required audit must use middleware.
````

#### `AsyncChatStream.aclose` { #ocai-chat-types-stream-asyncchatstream-aclose }

```python
async def aclose(self) -> None
```

````text
Release upstream promptly and finalize once; repeated closes are inert.
````

#### `AsyncChatStream.fold` { #ocai-chat-types-stream-asyncchatstream-fold }

```python
async def fold(self) -> ChatResponse
```

````text
Drain and fold the remaining chunks without hiding stream failure.
````

## `ocai.chat.types.tools`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/types/tools.py)

### `AnyFunction` { #ocai-chat-types-tools-anyfunction }

```python
type AnyFunction = Callable[..., Any]
```

### `Tool` { #ocai-chat-types-tools-tool }

```python
class Tool(IRObject):
    object: ClassVar[str] = 'tool'
    name: str
    parameters: JsonSchema
    description: str | None = None
    output: JsonSchema | None = None
```

````text
A model-invocable tool described as pure, serializable data.

Captures a tool's name, its input parameter schema, an optional human
description, and an optional output schema. No underlying callable is
retained, so a `Tool` stays serializable across the IR and identical in
every language port.

Attributes:
    name: The tool's name, as exposed to the model.
    parameters: JSON Schema describing the tool's input parameters.
    description: Human-readable description of the tool, if any.
    output: JSON Schema describing the tool's output, if known.
````

#### `Tool.from_dict` { #ocai-chat-types-tools-tool-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Rebuild a `Tool` from its serialized mapping, totally.

The `parameters` schema is decoded via `JsonSchema.from_dict`;
`output` the same way when present.

Args:
    data: The serialized mapping to rebuild from.

Returns:
    The reconstructed `Tool`.
````

#### `Tool.from_function` { #ocai-chat-types-tools-tool-from-function }

```python
@classmethod
def from_function(cls, fn: AnyFunction) -> Self
```

````text
Build a `Tool` by introspecting a Python callable.

Ingestion-boundary sugar: the function's signature + type hints become the
tool's `parameters` JSON Schema and its docstring becomes `description`.
The callable itself is *not* retained -- only the derived schema enters the
IR, so a `Tool` stays pure, serializable data.
````

#### `Tool.from_schema` { #ocai-chat-types-tools-tool-from-schema }

```python
@classmethod
def from_schema(cls, obj: Any, *, name: str | None=None, description: str | None=None) -> Self
```

````text
Build a `Tool` from anything schema-shaped, by duck typing.

The pydantic bridge (rule 11): pydantic users hand their model class
straight in and its `model_json_schema()` is consumed — without
pydantic ever appearing in ocai's dependencies. Accepted shapes, in
dispatch order:

1. An object exposing `model_json_schema()` (pydantic v2 models and
   anything imitating them) — called, and the resulting dict used as
   the parameters schema.
2. A dataclass *type* — its fields become an object schema via the
   same annotation mapping `from_function` uses.
3. A plain dict — treated as an already-built JSON Schema for the
   parameters and decoded via `JsonSchema.from_dict` (unknown
   keywords ride `JsonSchema.extra`, lossless).

Args:
    obj: The schema donor — a dict, a dataclass type, or anything
        exposing `model_json_schema()`.
    name: The tool name; when omitted it is derived from the
        schema's `title`, the donor's `__name__`, or left empty.
    description: The tool description; when omitted it is derived
        from the schema's `description` or the donor's docstring.

Returns:
    The constructed `Tool`.

Raises:
    TypeError: If `obj` matches none of the accepted shapes.
````

### `ServerToolLocation` { #ocai-chat-types-tools-servertoollocation }

```python
class ServerToolLocation(IRObject):
    country: str | None = None
    region: str | None = None
    city: str | None = None
    timezone: str | None = None
```

````text
Approximate search location; not a device location or execution authority.

Attributes:
    country: Country code supplied by the caller.
    region: Region supplied by the caller.
    city: City supplied by the caller.
    timezone: Time zone supplied by the caller.
````

#### `ServerToolLocation.from_dict` { #ocai-chat-types-tools-servertoollocation-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Decode location data without interpreting or normalizing its values.
````

### `ServerTool` { #ocai-chat-types-tools-servertool }

```python
class ServerTool(IRObject):
    kind: str
    allowed_domains: list[str] | None = None
    blocked_domains: list[str] | None = None
    user_location: ServerToolLocation | None = None
    type: str = field(default='server', init=False)
```

````text
Provider-executed tool intent, separate from a callable function definition.

Attributes:
    kind: Open intent code, for example `web_search`.
    allowed_domains: Explicit domain allowlist; never normalized implicitly.
    blocked_domains: Explicit domain blocklist; conflicts are provider-qualified.
    user_location: Approximate caller-supplied search location.
    type: Fixed discriminator; legacy function tools remain untagged.
````

#### `ServerTool.to_dict` { #ocai-chat-types-tools-servertool-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize intent, preserving explicitly empty domain lists.
````

#### `ServerTool.from_dict` { #ocai-chat-types-tools-servertool-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Decode server intent and retain unparsed location evidence.
````

### `ToolUnknown` { #ocai-chat-types-tools-toolunknown }

```python
class ToolUnknown:
    data: Any
```

````text
A future or malformed tool entry preserved verbatim, with no execution meaning.

Attributes:
    data: The original JSON value, retained without interpreting its tag.
````

#### `ToolUnknown.to_dict` { #ocai-chat-types-tools-toolunknown-to-dict }

```python
def to_dict(self) -> Any
```

````text
Return detached original data, including unknown non-object entries.
````

#### `ToolUnknown.from_dict` { #ocai-chat-types-tools-toolunknown-from-dict }

```python
@classmethod
def from_dict(cls, data: Any) -> Self
```

````text
Preserve the unknown tool payload without imposing this revision's schema.
````

### `ToolDefinition` { #ocai-chat-types-tools-tooldefinition }

```python
type ToolDefinition = Tool | ServerTool | ToolUnknown
```

### `decode_tool` { #ocai-chat-types-tools-decode-tool }

```python
def decode_tool(data: Any) -> ToolDefinition
```

````text
Decode the open tool union; untagged mappings retain legacy function semantics.
````

### `ToolChoiceMode` { #ocai-chat-types-tools-toolchoicemode }

```python
class ToolChoiceMode:
    AUTO: Final = 'auto'
    NONE: Final = 'none'
    REQUIRED: Final = 'required'
    NAMED: Final = 'named'
```

````text
Canonical constants for the open `ToolChoice.mode` code.

Attributes:
    AUTO: The model decides whether to call a tool (the default).
    NONE: The model must not call any tool.
    REQUIRED: The model must call at least one tool.
    NAMED: The model must call the tool named by `ToolChoice.name`.
````

### `ToolChoice` { #ocai-chat-types-tools-toolchoice }

```python
class ToolChoice(IRObject):
    mode: str = ToolChoiceMode.AUTO
    name: str | None = None
```

````text
Request-level policy for whether/which tool the model must call.

Rides `ChatRequest.tool_choice`; codecs map the open `mode` onto each
dialect's idiom (OpenAI `tool_choice`, Anthropic `tool_choice`, Gemini
`functionCallingConfig`).

Attributes:
    mode: The open choice code; canonical constants on `ToolChoiceMode`
        (`auto | none | required | named`).
    name: The tool the model must call when `mode` is `named`.
````

#### `ToolChoice.from_dict` { #ocai-chat-types-tools-toolchoice-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `ToolChoice` from a serialized dict, totally.

Args:
    data: A mapping with `mode`, an optional `name`, and the common
        IR envelope keys.

Returns:
    The decoded `ToolChoice`.
````

## `ocai.chat.types.usage`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/types/usage.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-chat-types-usage-consumption"></span>`Consumption` | [`ocai.core.usage.Consumption`](ocai-core.md#ocai-core-usage-consumption) |
| <span id="ocai-chat-types-usage-usage"></span>`Usage` | [`ocai.core.usage.Usage`](ocai-core.md#ocai-core-usage-usage) |
| <span id="ocai-chat-types-usage-usagemodality"></span>`UsageModality` | [`ocai.core.usage.UsageModality`](ocai-core.md#ocai-core-usage-usagemodality) |
| <span id="ocai-chat-types-usage-usagesource"></span>`UsageSource` | [`ocai.core.usage.UsageSource`](ocai-core.md#ocai-core-usage-usagesource) |
| <span id="ocai-chat-types-usage-usageunit"></span>`UsageUnit` | [`ocai.core.usage.UsageUnit`](ocai-core.md#ocai-core-usage-usageunit) |
