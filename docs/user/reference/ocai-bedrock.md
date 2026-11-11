# `ocai.bedrock` API reference

Generated from the checked-out package sources. Signatures, declared fields,
methods, type aliases and explicit re-exports are checked for drift. Inherited
members follow their named base class; a type's presence does not establish
provider execution support. See [supported features](../provider-feature-matrix.md).

## `ocai.bedrock`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-bedrock/src/ocai/bedrock/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-bedrock-bedrock"></span>`Bedrock` | [`ocai.bedrock.hosting.Bedrock`](ocai-bedrock.md#ocai-bedrock-hosting-bedrock) |

## `ocai.bedrock.hosting`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-bedrock/src/ocai/bedrock/hosting.py)

### `Bedrock` { #ocai-bedrock-hosting-bedrock }

```python
class Bedrock:
    region: str
    endpoint_url: str | None = None
    beta: tuple[str, ...] = ()
    guardrail_identifier: str | None = None
    guardrail_version: str | None = None
    guardrail_config: Mapping[str, Any] | None = None
    trace: str | None = None
    performance_latency: str | None = None
    service_tier: str | None = None
    static_headers: Mapping[str, str] = field(default_factory=dict[str, str])
    profile_aliases: Mapping[str, str] = field(default_factory=dict[str, str])
```

````text
Host the qualified Anthropic Messages unary surface on InvokeModel.

Region and credentials are explicit; this value performs no discovery or I/O.
Pass it to ocai.chat.model with a separately supplied ocai credential. Optional
endpoint_url is explicit deployment configuration, not a discovery mechanism.
````

#### `Bedrock.endpoint` { #ocai-bedrock-hosting-bedrock-endpoint }

```python
def endpoint(self, spec: EndpointSpec) -> str
```

````text
Place the unchanged resource in one encoded InvokeModel path segment.
````

#### `Bedrock.headers` { #ocai-bedrock-hosting-bedrock-headers }

```python
def headers(self, spec: EndpointSpec) -> dict[str, str]
```

````text
Use trait-declared relocations and explicit non-secret host headers.
````

#### `Bedrock.envelope` { #ocai-bedrock-hosting-bedrock-envelope }

```python
def envelope(self, spec: EndpointSpec) -> EnvelopeTransform
```

````text
Relocate provider-bound resource/version fields without copying codecs.
````

#### `Bedrock.profile_key` { #ocai-bedrock-hosting-bedrock-profile-key }

```python
def profile_key(self, resource: str) -> str
```

````text
Use explicit aliases only; a cloud model identifier is not qualification.
````

#### `Bedrock.error_mapper` { #ocai-bedrock-hosting-bedrock-error-mapper }

```python
def error_mapper(self, spec: EndpointSpec) -> HostErrorMapper
```

````text
Select public native error adaptation for this qualified operation.
````

#### `Bedrock.response_adapter` { #ocai-bedrock-hosting-bedrock-response-adapter }

```python
def response_adapter(self, spec: EndpointSpec) -> HostResponseAdapter
```

````text
Select declared unary metadata and guardrail effects.
````

## `ocai.bedrock.outcomes`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-bedrock/src/ocai/bedrock/outcomes.py)

### `error_mapping` { #ocai-bedrock-outcomes-error-mapping }

```python
def error_mapping() -> HostErrorMapper
```

````text
Build a detached native-code classifier; no status-only provider guessing.
````

### `response_mapping` { #ocai-bedrock-outcomes-response-mapping }

```python
def response_mapping() -> HostResponseAdapter
```

````text
Declare unary host metadata and effects without changing Anthropic edges.
````
