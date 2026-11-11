# `ocai.deepseek` API reference

Generated from the checked-out package sources. Signatures, declared fields,
methods, type aliases and explicit re-exports are checked for drift. Inherited
members follow their named base class; a type's presence does not establish
provider execution support. See [supported features](../provider-feature-matrix.md).

## `ocai.deepseek`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-deepseek/src/ocai/deepseek/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-deepseek-fragment"></span>`FRAGMENT` | [`ocai.deepseek.chat_completions.FRAGMENT`](ocai-deepseek.md#ocai-deepseek-chat-completions-fragment) |

## `ocai.deepseek.chat_completions`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-deepseek/src/ocai/deepseek/chat_completions/__init__.py)

### `FRAGMENT` { #ocai-deepseek-chat-completions-fragment }

```python
FRAGMENT = CatalogFragment(origin=ORIGIN, nodes=NODES, profiles=PROFILES, traits=(TRAITS,), edges=EDGES, transducers=TRANSDUCERS, components=(Component(provider=PROVIDER, interface=INTERFACE, capability=CHAT, factory=DeepSeekCodec),))
```

## `ocai.deepseek.chat_completions.codec`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-deepseek/src/ocai/deepseek/chat_completions/codec.py)

### `VARIANT` { #ocai-deepseek-chat-completions-codec-variant }

```python
VARIANT  # See source for the full declaration.
```

### `DeepSeekCodec` { #ocai-deepseek-chat-completions-codec-deepseekcodec }

```python
class DeepSeekCodec(ChatCompletionsCodec)
```

````text
Qualify text, tools, JSON-object and reasoning through the standard execution machinery.
````

#### `DeepSeekCodec.__init__` { #ocai-deepseek-chat-completions-codec-deepseekcodec---init-- }

```python
def __init__(self) -> None
```

````text
Use DeepSeek coordinates and field lanes, never OpenAI routing identity.
````

#### `DeepSeekCodec.encode_request` { #ocai-deepseek-chat-completions-codec-deepseekcodec-encode-request }

```python
def encode_request(self, request: ChatRequest) -> EdgeOutput
```

````text
Apply semantic findings to the effective shared-codec output before provider I/O.
````

#### `DeepSeekCodec.decode_request` { #ocai-deepseek-chat-completions-codec-deepseekcodec-decode-request }

```python
def decode_request(self, payload: dict[str, Any]) -> EdgeOutput
```

````text
Decode compatible request data and retain unknown native fields by source path.
````

#### `DeepSeekCodec.decode_response` { #ocai-deepseek-chat-completions-codec-deepseekcodec-decode-response }

```python
def decode_response(self, payload: dict[str, Any]) -> EdgeOutput
```

````text
Preserve reasoning, native identity and disjoint measured usage through total decode.
````

## `ocai.deepseek.chat_completions.descriptor`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-deepseek/src/ocai/deepseek/chat_completions/descriptor.py)

### `PROVIDER` { #ocai-deepseek-chat-completions-descriptor-provider }

```python
PROVIDER = 'deepseek'
```

### `INTERFACE` { #ocai-deepseek-chat-completions-descriptor-interface }

```python
INTERFACE = 'chat_completions'
```

### `TAG` { #ocai-deepseek-chat-completions-descriptor-tag }

```python
TAG = '2026-11'
```

### `RELEASED` { #ocai-deepseek-chat-completions-descriptor-released }

```python
RELEASED = date(2026, 11, 11)
```

### `BASE_URL` { #ocai-deepseek-chat-completions-descriptor-base-url }

```python
BASE_URL = 'https://api.deepseek.com'
```

### `PATH` { #ocai-deepseek-chat-completions-descriptor-path }

```python
PATH = '/chat/completions'
```

### `MODEL_IDS` { #ocai-deepseek-chat-completions-descriptor-model-ids }

```python
MODEL_IDS = ('deepseek-flash', 'deepseek-v4-pro')
```

### `ORIGIN` { #ocai-deepseek-chat-completions-descriptor-origin }

```python
ORIGIN = Origin(distribution='ocai-deepseek', version='0.1.0')
```

### `CHAT_COMPLETIONS_REQUEST` { #ocai-deepseek-chat-completions-descriptor-chat-completions-request }

```python
CHAT_COMPLETIONS_REQUEST = NodeId(PROVIDER, INTERFACE, TAG, CHAT_REQUEST, RELEASED, Status.STABLE)
```

### `CHAT_COMPLETIONS_RESPONSE` { #ocai-deepseek-chat-completions-descriptor-chat-completions-response }

```python
CHAT_COMPLETIONS_RESPONSE = NodeId(PROVIDER, INTERFACE, TAG, CHAT_RESPONSE, RELEASED, Status.STABLE)
```

### `CHAT_COMPLETIONS_CHUNK` { #ocai-deepseek-chat-completions-descriptor-chat-completions-chunk }

```python
CHAT_COMPLETIONS_CHUNK = NodeId(PROVIDER, INTERFACE, TAG, CHAT_CHUNK, RELEASED, Status.STABLE)
```

### `NODES` { #ocai-deepseek-chat-completions-descriptor-nodes }

```python
NODES = (CHAT_COMPLETIONS_REQUEST, CHAT_COMPLETIONS_RESPONSE, CHAT_COMPLETIONS_CHUNK)
```

### `TRAITS` { #ocai-deepseek-chat-completions-descriptor-traits }

```python
TRAITS = DialectTraits(vendor=PROVIDER, first_party_base_url=BASE_URL)
```

### `PROFILES` { #ocai-deepseek-chat-completions-descriptor-profiles }

```python
PROFILES = tuple((CapabilityProfile(provider=PROVIDER, interface=INTERFACE, model_pattern=model, features={'chat.config.output.json_schema': Support.ABSENT, 'chat.config.output.json': Support.NATIVE, 'chat.parts.reasoning.replay': Support.NATIVE}) for model in MODEL_IDS))
```

## `ocai.deepseek.chat_completions.edges`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-deepseek/src/ocai/deepseek/chat_completions/edges.py)

### `ENCODE_REQUEST_CONTRACT` { #ocai-deepseek-chat-completions-edges-encode-request-contract }

```python
ENCODE_REQUEST_CONTRACT  # See source for the full declaration.
```

### `DECODE_REQUEST_CONTRACT` { #ocai-deepseek-chat-completions-edges-decode-request-contract }

```python
DECODE_REQUEST_CONTRACT  # See source for the full declaration.
```

### `DECODE_RESPONSE_CONTRACT` { #ocai-deepseek-chat-completions-edges-decode-response-contract }

```python
DECODE_RESPONSE_CONTRACT  # See source for the full declaration.
```

### `EDGES` { #ocai-deepseek-chat-completions-edges-edges }

```python
EDGES  # See source for the full declaration.
```

### `DECODE_CHUNK_CONTRACT` { #ocai-deepseek-chat-completions-edges-decode-chunk-contract }

```python
DECODE_CHUNK_CONTRACT  # See source for the full declaration.
```

### `TRANSDUCERS` { #ocai-deepseek-chat-completions-edges-transducers }

```python
TRANSDUCERS = (StreamEdge(CHAT_COMPLETIONS_CHUNK, canonical_node(CHAT_CHUNK), DeepSeekStreamTransducer, DECODE_CHUNK_CONTRACT, ORIGIN),)
```

## `ocai.deepseek.chat_completions.evidence`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-deepseek/src/ocai/deepseek/chat_completions/evidence.py)

### `Evidence` { #ocai-deepseek-chat-completions-evidence-evidence }

```python
type Evidence = list[dict[str, Any]]
```

### `retain` { #ocai-deepseek-chat-completions-evidence-retain }

```python
def retain(evidence: Evidence, path: str, value: Any) -> None
```

````text
Bank one native value with its exact source location.
````

### `fields` { #ocai-deepseek-chat-completions-evidence-fields }

```python
def fields(raw: dict[str, Any], known: set[str], path: str, evidence: Evidence) -> dict[str, Any]
```

````text
Copy known fields and retain everything else by path.
````

### `tool_calls` { #ocai-deepseek-chat-completions-evidence-tool-calls }

```python
def tool_calls(raw: Any, path: str, evidence: Evidence) -> list[dict[str, Any]]
```

````text
Only assert typed tool identity when the native function record is complete.
````

### `response_payload` { #ocai-deepseek-chat-completions-evidence-response-payload }

```python
def response_payload(raw: Any) -> tuple[dict[str, Any], Evidence]
```

````text
Return a safe compatible response plus native evidence, without manufacturing content.
````

## `ocai.deepseek.chat_completions.policy`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-deepseek/src/ocai/deepseek/chat_completions/policy.py)

### `NAMESPACE` { #ocai-deepseek-chat-completions-policy-namespace }

```python
NAMESPACE = 'deepseek.chat_completions'
```

### `ALIASES` { #ocai-deepseek-chat-completions-policy-aliases }

```python
ALIASES = {'minimal': 'low', 'medium': 'high', 'xhigh': 'high', 'ultra': 'max'}
```

### `inspect_request` { #ocai-deepseek-chat-completions-policy-inspect-request }

```python
def inspect_request(request: ChatRequest, payload: dict[str, Any], losses: list[FieldLoss], shifts: list[SemanticShift]) -> None
```

````text
Report provider effects after passthrough expansion, so overrides cannot bypass policy.
````

## `ocai.deepseek.chat_completions.streaming`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-deepseek/src/ocai/deepseek/chat_completions/streaming.py)

### `DeepSeekStreamCodec` { #ocai-deepseek-chat-completions-streaming-deepseekstreamcodec }

```python
class DeepSeekStreamCodec(DeepSeekCodec)
```

````text
Decode total ordered frame signals; state and terminal validation live below.
````

#### `DeepSeekStreamCodec.decode_frame` { #ocai-deepseek-chat-completions-streaming-deepseekstreamcodec-decode-frame }

```python
def decode_frame(self, event: str | None, data: str) -> EdgeOutput
```

````text
Decode supported frame lanes and preserve every unqualified native field.
````

### `DeepSeekStreamTransducer` { #ocai-deepseek-chat-completions-streaming-deepseekstreamtransducer }

```python
class DeepSeekStreamTransducer(ChatCompletionsStreamTransducer)
```

````text
Use shared slot/sequence machinery with stricter DeepSeek terminal qualification.
````

#### `DeepSeekStreamTransducer.__init__` { #ocai-deepseek-chat-completions-streaming-deepseekstreamtransducer---init-- }

```python
def __init__(self) -> None
```

````text
See the source declaration for this symbol.
````

#### `DeepSeekStreamTransducer.feed` { #ocai-deepseek-chat-completions-streaming-deepseekstreamtransducer-feed }

```python
def feed(self, event: Any) -> list[ChatChunk]
```

````text
Reject trailing data after success; never restart or manufacture completion.
````

#### `DeepSeekStreamTransducer.flush` { #ocai-deepseek-chat-completions-streaming-deepseekstreamtransducer-flush }

```python
def flush(self) -> tuple[list[ChatChunk], EdgeReport]
```

````text
Preserve terminal evidence on truncation and fail exactly once.
````

## `ocai.deepseek.chat_completions.usage`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-deepseek/src/ocai/deepseek/chat_completions/usage.py)

### `decode_usage` { #ocai-deepseek-chat-completions-usage-decode-usage }

```python
def decode_usage(raw: Any, losses: list[FieldLoss]) -> Usage | None
```

````text
Keep aggregate counters when a disjoint breakdown cannot be established.
````

## `ocai.deepseek.chat_completions.wire`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-deepseek/src/ocai/deepseek/chat_completions/wire.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-deepseek-chat-completions-wire-chatcompletion"></span>`ChatCompletion` | [`ocai.openai.chat_completions.wire.ChatCompletion`](ocai-openai.md#ocai-openai-chat-completions-wire-chatcompletion) |
| <span id="ocai-deepseek-chat-completions-wire-chatcompletionchunk"></span>`ChatCompletionChunk` | [`ocai.openai.chat_completions.wire.ChatCompletionChunk`](ocai-openai.md#ocai-openai-chat-completions-wire-chatcompletionchunk) |
| <span id="ocai-deepseek-chat-completions-wire-completioncreateparams"></span>`CompletionCreateParams` | [`ocai.openai.chat_completions.wire.CompletionCreateParams`](ocai-openai.md#ocai-openai-chat-completions-wire-completioncreateparams) |
