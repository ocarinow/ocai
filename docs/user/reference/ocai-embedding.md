# `ocai.embedding` API reference

Generated from the checked-out package sources. Signatures, declared fields,
methods, type aliases and explicit re-exports are checked for drift. Inherited
members follow their named base class; a type's presence does not establish
provider execution support. See [supported features](../provider-feature-matrix.md).

## `ocai.embedding`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/embedding/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-embedding-embeddingmodel"></span>`EmbeddingModel` | [`ocai.embedding.protocol.EmbeddingModel`](ocai-embedding.md#ocai-embedding-protocol-embeddingmodel) |
| <span id="ocai-embedding-document"></span>`Document` | [`ocai.embedding.types.document.Document`](ocai-embedding.md#ocai-embedding-types-document-document) |
| <span id="ocai-embedding-embeddable"></span>`Embeddable` | [`ocai.embedding.types.document.Embeddable`](ocai-embedding.md#ocai-embedding-types-document-embeddable) |
| <span id="ocai-embedding-embedding"></span>`Embedding` | [`ocai.embedding.types.embedding.Embedding`](ocai-embedding.md#ocai-embedding-types-embedding-embedding) |
| <span id="ocai-embedding-embeddingrequest"></span>`EmbeddingRequest` | [`ocai.embedding.types.request.EmbeddingRequest`](ocai-embedding.md#ocai-embedding-types-request-embeddingrequest) |
| <span id="ocai-embedding-embeddingresponse"></span>`EmbeddingResponse` | [`ocai.embedding.types.response.EmbeddingResponse`](ocai-embedding.md#ocai-embedding-types-response-embeddingresponse) |
| <span id="ocai-embedding-vector"></span>`Vector` | [`ocai.embedding.types.embedding.Vector`](ocai-embedding.md#ocai-embedding-types-embedding-vector) |

## `ocai.embedding.protocol`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/embedding/protocol.py)

### `EmbeddingModel` { #ocai-embedding-protocol-embeddingmodel }

```python
class EmbeddingModel(Protocol)
```

````text
An embedding provider port — structural, never subclassed.

Implementers accept the canonical `EmbeddingRequest` and return a
`CallResult[EmbeddingResponse]` — the same uniform envelope every
capability port returns, which is what fixed the old port's missing
channel for usage and fidelity reports.
````

#### `EmbeddingModel.embed` { #ocai-embedding-protocol-embeddingmodel-embed }

```python
def embed(self, request: EmbeddingRequest, *, ctx: CallContext | None=None) -> CallResult[EmbeddingResponse]
```

````text
Embed the request's inputs, synchronously.

Args:
    request: The canonical embedding request.
    ctx: The per-request governance context.

Returns:
    The uniform envelope carrying one `Embedding` per input.
````

#### `EmbeddingModel.aembed` { #ocai-embedding-protocol-embeddingmodel-aembed }

```python
async def aembed(self, request: EmbeddingRequest, *, ctx: CallContext | None=None) -> CallResult[EmbeddingResponse]
```

````text
Embed the request's inputs, asynchronously.

Args:
    request: The canonical embedding request.
    ctx: The per-request governance context.

Returns:
    The uniform envelope carrying one `Embedding` per input.
````

#### `EmbeddingModel.details` { #ocai-embedding-protocol-embeddingmodel-details }

```python
@property
def details(self) -> dict[str, Any]
```

````text
Describe this model implementation.

Returns:
    A free-form mapping of model metadata (for example, model name
    or output dimensionality); implementer-defined keys.
````

## `ocai.embedding.types`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/embedding/types/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-embedding-types-document"></span>`Document` | [`ocai.embedding.types.document.Document`](ocai-embedding.md#ocai-embedding-types-document-document) |
| <span id="ocai-embedding-types-embeddable"></span>`Embeddable` | [`ocai.embedding.types.document.Embeddable`](ocai-embedding.md#ocai-embedding-types-document-embeddable) |
| <span id="ocai-embedding-types-embedding"></span>`Embedding` | [`ocai.embedding.types.embedding.Embedding`](ocai-embedding.md#ocai-embedding-types-embedding-embedding) |
| <span id="ocai-embedding-types-vector"></span>`Vector` | [`ocai.embedding.types.embedding.Vector`](ocai-embedding.md#ocai-embedding-types-embedding-vector) |
| <span id="ocai-embedding-types-embeddingrequest"></span>`EmbeddingRequest` | [`ocai.embedding.types.request.EmbeddingRequest`](ocai-embedding.md#ocai-embedding-types-request-embeddingrequest) |
| <span id="ocai-embedding-types-embeddingresponse"></span>`EmbeddingResponse` | [`ocai.embedding.types.response.EmbeddingResponse`](ocai-embedding.md#ocai-embedding-types-response-embeddingresponse) |

## `ocai.embedding.types.document`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/embedding/types/document.py)

### `Document` { #ocai-embedding-types-document-document }

```python
class Document(IRObject):
    object: ClassVar[str] = 'document'
    id: str | None = None
    content: str | Source | None = None
    metadata: dict[str, Any] | None = None
```

````text
A canonical embedding input with optional id, content, and metadata.

Wrapping content (rather than passing bare strings everywhere) lets a
single input carry an identifier and metadata through the embedding
flow — and back out, since `Embedding.index` aligns results to inputs.
Content may be inline text or a `Source` reference (including a
provider-hosted `SourceRef`).

Attributes:
    id: The document identifier, if any.
    content: The document body — inline text, a `Source` reference, or
        None.
    metadata: Free-form metadata attached to the document, if any.
````

#### `Document.from_dict` { #ocai-embedding-types-document-document-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `Document` from a serialized dict, totally.

A string `content` is kept as-is; a mapping `content` is decoded
through `cast_source` (unknown source tags fall back to
`SourceUnknown`).

Args:
    data: A mapping with the optional `id`/`content`/`metadata`
        plus the common IR envelope keys.

Returns:
    The decoded `Document`.
````

### `Embeddable` { #ocai-embedding-types-document-embeddable }

```python
type Embeddable = str | list[str] | Document | list[Document]
```

## `ocai.embedding.types.embedding`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/embedding/types/embedding.py)

### `Vector` { #ocai-embedding-types-embedding-vector }

```python
type Vector = list[float]
```

### `Embedding` { #ocai-embedding-types-embedding-embedding }

```python
class Embedding(IRObject):
    object: ClassVar[str] = 'embedding'
    index: int
    values: Vector
    dtype: str = 'float32'
    normalized: bool | None = None
    metadata: dict[str, Any] | None = None
```

````text
A single embedding vector, one per input in an `EmbeddingRequest`.

Wrapping the raw vector (rather than returning a bare `list[float]`)
lets a response carry per-vector metadata — its position in the batch,
the numeric encoding, and whether it is already L2-normalized — without
lying that every provider returns floats. `int8`/`binary` dtypes still
serialize as ints.

Attributes:
    index: Position of this vector in the request batch (providers may
        reorder).
    values: The vector itself. For non-float `dtype`s the entries are
        ints.
    dtype: The open numeric-encoding code:
        `float32 | int8 | uint8 | binary | ubinary`.
    normalized: Whether `values` is L2-normalized, if the provider says;
        None means unknown.
    metadata: Free-form metadata attached to this vector, if any.
````

#### `Embedding.dimensions` { #ocai-embedding-types-embedding-embedding-dimensions }

```python
@property
def dimensions(self) -> int
```

````text
Return the vector length — derived, never stored, so it cannot drift from `values`.
````

#### `Embedding.from_dict` { #ocai-embedding-types-embedding-embedding-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build an `Embedding` from a serialized dict, totally.

Args:
    data: A mapping with `index`, `values`, and the optional
        `dtype`/`normalized`/`metadata`, plus the common IR
        envelope keys.

Returns:
    The decoded `Embedding`.
````

## `ocai.embedding.types.request`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/embedding/types/request.py)

### `EmbeddingRequest` { #ocai-embedding-types-request-embeddingrequest }

```python
class EmbeddingRequest(IRObject):
    object: ClassVar[str] = 'embedding.request'
    inputs: list[Document]
    dimensions: int | None = None
```

````text
A provider-neutral embedding request — a pure graph payload.

The constructor accepts the same sugar the old port did — a bare string
or `Document`, or a list of either — normalized to `list[Document]` in
`__post_init__`, so codecs and edges only ever see one shape (the same
boundary-sugar pattern as chat's `Message`). And no `model`: the model
name is routing data bound to the model object at the front door,
injected on the wire by the codec from the bound resource — the same
request replays against any bound model with zero edits.

Attributes:
    inputs: The documents to embed, in order; `Embedding.index` in the
        response aligns to this list.
    dimensions: The requested output dimensionality, where the provider
        supports truncation/selection; None for the model default.
````

#### `EmbeddingRequest.from_dict` { #ocai-embedding-types-request-embeddingrequest-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build an `EmbeddingRequest` from a serialized dict, totally.

Args:
    data: A mapping with `inputs`, the optional `dimensions`, and
        the common IR envelope keys.

Returns:
    The decoded `EmbeddingRequest`.
````

## `ocai.embedding.types.response`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/embedding/types/response.py)

### `EmbeddingResponse` { #ocai-embedding-types-response-embeddingresponse }

```python
class EmbeddingResponse(IRObject):
    object: ClassVar[str] = 'embedding.response'
    embeddings: list[Embedding] = field(default_factory=list[Embedding])
    usage: Usage | None = None
    model: str | None = None
```

````text
A provider-neutral embedding result — a pure graph payload.

Delivered inside `CallResult.value`; the route, report, and raw body
ride the `CallResult` envelope, exactly as on the chat port.

Attributes:
    embeddings: One `Embedding` per request input; each carries its
        `index` because providers may reorder.
    usage: What the call consumed, when reported — the core-owned
        dimensional `Usage` model.
    model: The provider's echo of the model that served the call.
````

#### `EmbeddingResponse.from_dict` { #ocai-embedding-types-response-embeddingresponse-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build an `EmbeddingResponse` from a serialized dict, totally.

Args:
    data: A mapping with `embeddings`, the optional
        `usage`/`model`, and the common IR envelope keys.

Returns:
    The decoded `EmbeddingResponse`.
````
