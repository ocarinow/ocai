# `ocai.vectorstore` API reference

Generated from the checked-out package sources. Signatures, declared fields,
methods, type aliases and explicit re-exports are checked for drift. Inherited
members follow their named base class; a type's presence does not establish
provider execution support. See [supported features](../provider-feature-matrix.md).

## `ocai.vectorstore`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/vectorstore/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-vectorstore-vectorstore"></span>`VectorStore` | [`ocai.vectorstore.protocol.VectorStore`](ocai-vectorstore.md#ocai-vectorstore-protocol-vectorstore) |
| <span id="ocai-vectorstore-queryfilter"></span>`QueryFilter` | [`ocai.vectorstore.types.filter.QueryFilter`](ocai-vectorstore.md#ocai-vectorstore-types-filter-queryfilter) |
| <span id="ocai-vectorstore-queryresult"></span>`QueryResult` | [`ocai.vectorstore.types.record.QueryResult`](ocai-vectorstore.md#ocai-vectorstore-types-record-queryresult) |
| <span id="ocai-vectorstore-record"></span>`Record` | [`ocai.vectorstore.types.record.Record`](ocai-vectorstore.md#ocai-vectorstore-types-record-record) |
| <span id="ocai-vectorstore-vector"></span>`Vector` | [`ocai.vectorstore.types.record.Vector`](ocai-vectorstore.md#ocai-vectorstore-types-record-vector) |

## `ocai.vectorstore.protocol`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/vectorstore/protocol.py)

### `VectorStore` { #ocai-vectorstore-protocol-vectorstore }

```python
class VectorStore(Protocol)
```

````text
A vector store port — structural, never subclassed.

Reads (`get`/`query`) return records/matches; writes
(`create`/`update`/`delete`) are keyword-only and return the envelope
too, so a fidelity report or usage record from a hosted store has a
home on every operation. Each method has its `a`-prefixed async twin
(repo-wide convention: bare = sync, `a` = async).
````

#### `VectorStore.get` { #ocai-vectorstore-protocol-vectorstore-get }

```python
def get(self, *, ids: list[str] | None=None, filters: QueryFilter | None=None, limit: int | None=None, offset: int | None=None, ctx: CallContext | None=None) -> CallResult[list[Record]]
```

````text
Fetch stored records by id and/or metadata filter.

Args:
    ids: The ids to fetch; None fetches without an id constraint.
    filters: A metadata filter constraining the results; None for
        no filter.
    limit: Maximum number of records to return; None for no limit.
    offset: Number of records to skip; None for no offset.
    ctx: The per-request governance context.

Returns:
    The uniform envelope carrying the matching records.
````

#### `VectorStore.aget` { #ocai-vectorstore-protocol-vectorstore-aget }

```python
async def aget(self, *, ids: list[str] | None=None, filters: QueryFilter | None=None, limit: int | None=None, offset: int | None=None, ctx: CallContext | None=None) -> CallResult[list[Record]]
```

````text
Fetch stored records by id and/or metadata filter, asynchronously.

Args:
    ids: The ids to fetch; None fetches without an id constraint.
    filters: A metadata filter constraining the results; None for
        no filter.
    limit: Maximum number of records to return; None for no limit.
    offset: Number of records to skip; None for no offset.
    ctx: The per-request governance context.

Returns:
    The uniform envelope carrying the matching records.
````

#### `VectorStore.create` { #ocai-vectorstore-protocol-vectorstore-create }

```python
def create(self, *, records: list[Record], ctx: CallContext | None=None) -> CallResult[list[str]]
```

````text
Insert records into the store.

Args:
    records: The records to insert; a record without an `id` lets
        the store assign one.
    ctx: The per-request governance context.

Returns:
    The uniform envelope carrying the ids of the inserted records,
    in input order.
````

#### `VectorStore.acreate` { #ocai-vectorstore-protocol-vectorstore-acreate }

```python
async def acreate(self, *, records: list[Record], ctx: CallContext | None=None) -> CallResult[list[str]]
```

````text
Insert records into the store, asynchronously.

Args:
    records: The records to insert; a record without an `id` lets
        the store assign one.
    ctx: The per-request governance context.

Returns:
    The uniform envelope carrying the ids of the inserted records,
    in input order.
````

#### `VectorStore.update` { #ocai-vectorstore-protocol-vectorstore-update }

```python
def update(self, *, records: list[Record], ctx: CallContext | None=None) -> CallResult[None]
```

````text
Modify existing records by id.

Each record's set fields replace the stored ones; None fields are
left unchanged.

Args:
    records: The records to update, identified by their `id`s.
    ctx: The per-request governance context.

Returns:
    The uniform envelope with no payload.
````

#### `VectorStore.aupdate` { #ocai-vectorstore-protocol-vectorstore-aupdate }

```python
async def aupdate(self, *, records: list[Record], ctx: CallContext | None=None) -> CallResult[None]
```

````text
Modify existing records by id, asynchronously.

Args:
    records: The records to update, identified by their `id`s.
    ctx: The per-request governance context.

Returns:
    The uniform envelope with no payload.
````

#### `VectorStore.delete` { #ocai-vectorstore-protocol-vectorstore-delete }

```python
def delete(self, *, ids: list[str] | None=None, filters: QueryFilter | None=None, ctx: CallContext | None=None) -> CallResult[None]
```

````text
Remove records by id and/or metadata filter.

Args:
    ids: The ids to delete; None deletes by filter alone.
    filters: A metadata filter selecting/narrowing what is deleted;
        None for no filter.
    ctx: The per-request governance context.

Returns:
    The uniform envelope with no payload.
````

#### `VectorStore.adelete` { #ocai-vectorstore-protocol-vectorstore-adelete }

```python
async def adelete(self, *, ids: list[str] | None=None, filters: QueryFilter | None=None, ctx: CallContext | None=None) -> CallResult[None]
```

````text
Remove records by id and/or metadata filter, asynchronously.

Args:
    ids: The ids to delete; None deletes by filter alone.
    filters: A metadata filter selecting/narrowing what is deleted;
        None for no filter.
    ctx: The per-request governance context.

Returns:
    The uniform envelope with no payload.
````

#### `VectorStore.query` { #ocai-vectorstore-protocol-vectorstore-query }

```python
def query(self, vector: Vector, *, filters: QueryFilter | None=None, limit: int=100, ctx: CallContext | None=None) -> CallResult[list[QueryResult]]
```

````text
Search for the stored records most similar to a query vector.

Args:
    vector: The query vector.
    filters: A metadata filter constraining the candidate set; None
        for no filter.
    limit: Maximum number of matches to return.
    ctx: The per-request governance context.

Returns:
    The uniform envelope carrying the matches, best first.
````

#### `VectorStore.aquery` { #ocai-vectorstore-protocol-vectorstore-aquery }

```python
async def aquery(self, vector: Vector, *, filters: QueryFilter | None=None, limit: int=100, ctx: CallContext | None=None) -> CallResult[list[QueryResult]]
```

````text
Search for the most similar stored records, asynchronously.

Args:
    vector: The query vector.
    filters: A metadata filter constraining the candidate set; None
        for no filter.
    limit: Maximum number of matches to return.
    ctx: The per-request governance context.

Returns:
    The uniform envelope carrying the matches, best first.
````

#### `VectorStore.details` { #ocai-vectorstore-protocol-vectorstore-details }

```python
@property
def details(self) -> dict[str, Any]
```

````text
Describe this store implementation.

Returns:
    A free-form mapping of store metadata (for example the vector
    dimensionality or distance metric); implementer-defined keys.
````

## `ocai.vectorstore.types`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/vectorstore/types/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-vectorstore-types-queryfilter"></span>`QueryFilter` | [`ocai.vectorstore.types.filter.QueryFilter`](ocai-vectorstore.md#ocai-vectorstore-types-filter-queryfilter) |
| <span id="ocai-vectorstore-types-queryresult"></span>`QueryResult` | [`ocai.vectorstore.types.record.QueryResult`](ocai-vectorstore.md#ocai-vectorstore-types-record-queryresult) |
| <span id="ocai-vectorstore-types-record"></span>`Record` | [`ocai.vectorstore.types.record.Record`](ocai-vectorstore.md#ocai-vectorstore-types-record-record) |
| <span id="ocai-vectorstore-types-vector"></span>`Vector` | [`ocai.vectorstore.types.record.Vector`](ocai-vectorstore.md#ocai-vectorstore-types-record-vector) |

## `ocai.vectorstore.types.filter`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/vectorstore/types/filter.py)

### `QueryFilter` { #ocai-vectorstore-types-filter-queryfilter }

```python
type QueryFilter = dict[str, Any]
```

## `ocai.vectorstore.types.record`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/vectorstore/types/record.py)

### `Vector` { #ocai-vectorstore-types-record-vector }

```python
type Vector = list[float]
```

### `Record` { #ocai-vectorstore-types-record-record }

```python
class Record(IRObject):
    object: ClassVar[str] = 'record'
    id: str
    vector: Vector | None = None
    metadata: dict[str, Any] | None = None
    content: str | None = None
```

````text
One stored entry: id, vector, and what the vector stands for.

The shape `create`/`update` write and `get`/`query` read — one type on
both sides of the port, so round-tripping a record through a store is
the identity.

Attributes:
    id: The record's identifier within its store.
    vector: The stored vector; None when the store elides vectors on
        read (many do unless asked).
    metadata: Free-form metadata attached to the record, used by
        `filters`.
    content: The source text the vector encodes, when the store keeps
        it alongside.
````

#### `Record.from_dict` { #ocai-vectorstore-types-record-record-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `Record` from a serialized dict, totally.

Args:
    data: A mapping with `id` and the optional
        `vector`/`metadata`/`content`, plus the common IR envelope
        keys.

Returns:
    The decoded `Record`.
````

### `QueryResult` { #ocai-vectorstore-types-record-queryresult }

```python
class QueryResult(IRObject):
    object: ClassVar[str] = 'query.result'
    record: Record
    score: float | None = None
```

````text
One similarity match: the record found and how similar it was.

`query` returns a `CallResult[list[QueryResult]]`, best match first.

Attributes:
    record: The matched record.
    score: The store's similarity score, higher-is-closer, when the
        store reports one. Metric semantics (cosine, dot, L2) are
        store-specific and surfaced via `VectorStore.details`.
````

#### `QueryResult.from_dict` { #ocai-vectorstore-types-record-queryresult-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `QueryResult` from a serialized dict, totally.

Args:
    data: A mapping with the nested `record`, the optional `score`,
        and the common IR envelope keys.

Returns:
    The decoded `QueryResult`.
````
