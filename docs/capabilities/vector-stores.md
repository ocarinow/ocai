# Vector stores — provider survey and canonical IR proposal

Currency: researched against official documentation on 2026-11-10 (every
URL in Sources was read that day). Vector-store APIs move monthly — Pinecone
alone is mid-migration between two incompatible data-plane APIs — so names,
limits and prices are a snapshot. Anything a page did not state verbatim is
marked unverified.

Scope: this page informs [horizon H3](../plans/horizon.md) (graduate the
provisional `ocai.vectorstore` port by carrying `CallResult` in real use,
with one local in-process adapter as the port-plane peer proof) and applies
the architecture §11 recipe to the first multi-operation capability. Hybrid
fusion and BM25 engines are on [hybrid-and-fulltext-search](hybrid-and-fulltext-search.md);
provider-side retrieval on [managed-rag-and-file-search](managed-rag-and-file-search.md).

The reference filter rendered in every dialect below:
`genre == "drama" AND year >= 2020 AND tag IN ["a","b"] AND NOT archived == true`.

## 1. Provider survey

Field names are quoted as the provider documents them. "Score" states what
the store returns and which direction is better. Each table has the same
five rows: API and auth; data model; filter dialect and operator census;
score and hybrid; limits, consistency, pricing and errors.

### 1.1 Pinecone

| | |
|---|---|
| API, auth | Two data-plane APIs selected by the required `X-Pinecone-Api-Version` header: legacy Vectors/Records (`2025-10`: `POST /vectors/upsert`, `POST /query`, `GET /vectors/fetch`, `POST /vectors/delete`, `POST /vectors/update`, `GET /vectors/list`, `POST /records/namespaces/{ns}/upsert`, `.../search`) and Documents (`2026-07`: `POST /namespaces/{ns}/documents/upsert`, `search`, `fetch`, `update`, `delete`, `list`; `POST https://api.pinecone.io/indexes` is schema-only; upsert returns 202). Header `Api-Key`. Tenancy: namespaces (`__default__`). Standalone `POST https://api.pinecone.io/rerank`. |
| Data model | String id (1–512 chars); one dense slot (`dimension` ≤ 20,000) and one sparse slot (`indices`/`values`, ≤ 2,048 non-zeros); metadata is a flat JSON object ("Nested objects aren't supported"), no nulls, 40 KB; Documents `string` fields may declare `full_text_search`, `embed` or `sparse_embed` (hosted `llama-text-embed-v2`, `multilingual-e5-large`, `pinecone-sparse-english-v0`, `gemini-embedding-2`, OpenAI models). |
| Filter | `{"$and": [{"genre": {"$eq": "drama"}}, {"year": {"$gte": 2020}}, {"tag": {"$in": ["a","b"]}}, {"archived": {"$ne": true}}]}`. Operators `$eq $ne $gt $gte $lt $lte $in $nin $exists $and $or $not`, plus `$match_phrase`, `$match_all`, `$match_any` on FTS fields (search and fetch only; filtered update/delete rejects them with 400). List fields match on any element. Unsupported: contains-all, is-null, nested paths, geo, prefix/like/regex, date types. `$in` ≤ 10,000 values. |
| Score, hybrid | `metric euclidean`, `cosine`, `dotproduct`; `score` "Higher means more similar" (euclidean direction unverified); sparse-dense needs `dotproduct`. No server-side fusion ("Every search ranks by one scoring type"): text clauses act as filters on a dense search, or two searches are merged client-side with RRF; no `alpha`. |
| Limits, consistency, pricing, errors | 1,000 records / 2 MB per upsert (96 with embedding), `top_k` ≤ 10,000, fetch ≤ 1,000 ids; 100 upsert req/s and 2,000 read units/s per namespace. Eventually consistent; freshness via `x-pinecone-request-lsn` and `x-pinecone-max-indexed-lsn` headers. Read units $16–18/M and write units $4–4.50/M (Standard), $0.33/GB-month, egress $0.10/GB. 429 on rate limits; Documents error body `{status, error: {code, message}}`, legacy `{code, message, details}`. |

### 1.2 Weaviate

| | |
|---|---|
| API, auth | REST `/v1` plus gRPC (50051; 443 on Cloud) for search and batch import; GraphQL `Get{... where, nearVector, bm25, hybrid}`. `POST /v1/schema`, `POST /v1/objects`, `POST /v1/batch/objects` (429 rejects the whole batch), `GET`/`PUT`/`PATCH`/`DELETE /v1/objects/{class}/{id}`, `DELETE /v1/batch/objects` with `where` (≤ `QUERY_MAXIMUM_RESULTS`, default 10,000, per call), cursor list `GET /v1/objects?after=`, tenants under `/v1/schema/{class}/tenants`, backups `/v1/backups/{backend}`. Auth `Authorization: Bearer` (API key or OIDC; header name inferred, unverified verbatim); anonymous access on by default in OSS. |
| Data model | UUID ids; `properties[{name, dataType[], tokenization, indexFilterable, nestedProperties}]` with `text`, `int`, `number`, `boolean`, `date`, `uuid`, `geoCoordinates`, `object` (nests to any depth) and arrays; named vectors via `vectorConfig`, multi-vector via `Configure.MultiVectors`; no user sparse vectors (keyword lane is BM25F). Multi-tenancy: `multiTenancyConfig`, tenants `ACTIVE`, `INACTIVE`, `OFFLOADED`, tenant required on every call. |
| Filter | `where: {operator: And, operands: [{path: ["genre"], operator: Equal, valueText: "drama"}, {path: ["year"], operator: GreaterThanEqual, valueInt: 2020}, {path: ["tag"], operator: ContainsAny, valueText: ["a","b"]}, {path: ["archived"], operator: NotEqual, valueBoolean: true}]}`. Enum `And Or Equal Like NotEqual GreaterThan GreaterThanEqual LessThan LessThanEqual WithinGeoRange IsNull ContainsAny ContainsAll ContainsNone Not`; `Like` takes `*` and `?`; `IsNull` needs `indexNullState`; nested object paths are preview (v1.38+); no regex. |
| Score, hybrid | `distance` lower-is-better for `cosine` (default, 0..2), `dot` (negated), `l2-squared`, `hamming`, `manhattan`; BM25/hybrid `score` higher. `hybrid {query, alpha, fusionType relativeScoreFusion (default since v1.24) or rankedFusion, targetVectors, maxVectorDistance}`; server default `alpha` unverified. Generative modules add `generate` to results. |
| Limits, consistency, pricing, errors | No documented batch cap (server-side batching; gRPC message 100 MB). Consistency per request `ONE`, `QUORUM` (default), `ALL`; strong iff r + w > n; Raft for schema. Pricing per 1M vector dimensions stored per month (Flex from $0.00465) plus GiB storage, $45/month minimum. Errors `{"error": [{"message"}]}`; 200/204/400/401/403/404/422/429/500. |

### 1.3 Qdrant

| | |
|---|---|
| API, auth | REST 6333 / gRPC 6334; responses `{result, status, time}`. `PUT /collections/{name}`, `PUT .../points?wait=true`, `POST .../points/query` (one Query API: nearest, recommend, discover, `order_by`, `fusion`, `formula`, `text`), fetch `POST .../points` or `GET .../points/{id}`, `POST .../points/scroll`, `POST .../points/delete` (ids or filter), payload `POST .../points/payload` (merge), `PUT` (overwrite), `.../payload/delete`, `.../payload/clear`, `POST .../points/batch` (ordered), snapshots `/collections/{name}/snapshots` (S3 backend). Header `api-key` or `Authorization: Bearer`; optional JWT RBAC. Tenancy: `is_tenant` payload index or `shard_key`. |
| Data model | Ids u64 or UUID; named dense vectors (≤ 65,536 dims, `datatype float32`, `float16`, `uint8`), named sparse (`indices`/`values`, `modifier: "idf"`), multivectors (`max_sim`); payload is arbitrary JSON incl. nested objects, arrays, `datetime`, `uuid`, geo. Re-upserting an id replaces the whole point. |
| Filter | `{"must": [{"key": "genre", "match": {"value": "drama"}}, {"key": "year", "range": {"gte": 2020}}, {"key": "tag", "match": {"any": ["a","b"]}}], "must_not": [{"key": "archived", "match": {"value": true}}]}`. Clauses `must`, `should`, `must_not`, `min_should`; conditions `match.value`, `any`, `except`, `text`, `text_any`, `phrase`, `prefix`, `substring`; `range` (numbers and RFC 3339 datetimes); `geo_bounding_box`, `geo_radius`, `geo_polygon`; `values_count`, `is_empty`, `is_null`, `has_id`, `has_vector`, `nested` (same-element), `[]` array projection. `substring` is rejected in strict mode (Cloud default). No regex/like. |
| Score, hybrid | `distance Dot`, `Cosine`, `Euclid`, `Manhattan`; `score` is "distance to the query vector", Euclid lower-is-better, Cosine/Dot similarities (direction inferred, unverified verbatim). Hybrid: `prefetch[]` lanes fused by top-level `query: {fusion: "rrf"}` or `"dbsf"`, or `{rrf: {k, weights}}`; nested prefetch for multi-stage rescoring. |
| Limits, consistency, pricing, errors | Limits via strict mode (`max_query_limit`, `upsert_max_batchsize`, `filter_max_conditions`, rate limits), defaults unpublished. `wait=false` → `acknowledged` (eventual), `wait=true` → `completed`; distributed `ordering weak`, `medium`, `strong`; read `consistency` int, `majority`, `quorum`, `all`. Cloud bills vCPU, GB RAM, storage, backups and inference tokens hourly (no list prices). Errors `{"status": {"error"}, "time", "result": null}`; 401/403/429 (strict-mode rate limits, retry delay)/507. |

### 1.4 Milvus / Zilliz Cloud

| | |
|---|---|
| API, auth | REST v2 `/v2/vectordb/*` (gRPC 19530); Zilliz exposes the same data plane. `collections/create`, `entities/insert` and `upsert` (`partialUpdate`, `fieldOps`), `entities/search`, `entities/hybrid_search`, `entities/get`, `entities/query` (`limit + offset < 16,384`), `entities/delete` (filter required), partitions `create`/`load`/`release`/`drop`; a collection must be loaded before search. Auth `Authorization: Bearer <user:pass>` (Milvus) or a Zilliz API key. |
| Data model | Primary key `INT64` or `VARCHAR` (`auto_id`); `FLOAT_VECTOR`, `FLOAT16_VECTOR`, `BFLOAT16_VECTOR`, `INT8_VECTOR`, `BINARY_VECTOR`, `SPARSE_FLOAT_VECTOR`; ≤ 4 vector fields by default (max 10), `dim` ≤ 32,768; scalars incl. path-indexable `JSON`, `ARRAY(element_type, max_capacity)`, `nullable`, dynamic `$meta`. Partitions (`_default`, ≤ 1,024) and Partition Key. |
| Filter | String expression: `genre == "drama" and year >= 2020 and tag in ["a", "b"] and not archived == true`. Operators `== != > >= < <=`, chained ranges, `in`, `not in`, `like` (`%`, `_`), regex `=~` / `!~`, arithmetic, `and`/`or`/`not`, `IS NULL`, JSON paths `meta["a"]["b"]`, `json_contains`, `json_contains_all`, `json_contains_any`, `ARRAY_CONTAINS`, `ARRAY_CONTAINS_ALL`, `ARRAY_CONTAINS_ANY`, `ARRAY_LENGTH`, `TEXT_MATCH`, `PHRASE_MATCH`. No geo, no date type (numeric timestamps), no same-element nesting. |
| Score, hybrid | Response field is `distance` for every metric: `L2` squared lower-is-better, `IP` and `COSINE` higher, `JACCARD`/`HAMMING` lower, `BM25` higher. Hybrid `hybrid_search` with `rerank: {strategy: "rrf" or "weighted", params: {k (default 60) or weights}}`; BM25 `Function` fills a sparse field; `TEXTEMBEDDING` and `RERANK` functions. |
| Limits, consistency, pricing, errors | 64 MB per RPC, topk and nq 16,384 (1,024 and 10 on Zilliz Free/Serverless), 64 fields, 65,536 collections. Consistency `Strong`, `Bounded` (default), `Session`, `Eventually`, set at creation and overridable per search. Zilliz Serverless in vCUs (rates unpublished), Dedicated per CU-hour by CU type, Free 2.5M vCU/month. REST `{code: 0, cost, data}` on success, `{code, message}` on failure (HTTP status on failure unverified). |

### 1.5 Chroma

| | |
|---|---|
| API, auth | Legacy `query`/`get` everywhere (REST `/api/v2/tenants/{t}/databases/{d}/collections/{id}/add`, `upsert`, `update`, `query`, `get`, `delete`); the Search API (`collection.search(Search()...)`, `POST .../search`) is Chroma Cloud only. Header `x-chroma-token`; self-hosted ships no authentication since v1.0.0. Tenancy: tenant → database → collection path. |
| Data model | String ids; one embedding per record (Cloud ≤ 4,096 dims); flat metadata of string/int/float/bool or single-type arrays (no nested objects); `documents` text (Cloud ≤ 16,384 bytes); Cloud sparse vectors via `SparseVectorIndexConfig(bm25=True)` under a metadata key. Default embedding function `all-MiniLM-L6-v2`. |
| Filter | Legacy `where`: `{"$and": [{"genre": {"$eq": "drama"}}, {"year": {"$gte": 2020}}, {"tag": {"$in": ["a","b"]}}, {"archived": {"$ne": true}}]}` — `$ne` and `$lt` are absent from the current page (unverified; `{"$eq": false}` is safe). Documented `$eq $gt $gte $lte $in $nin $and $or $contains $not_contains`; `where_document` `$contains $not_contains $regex $not_regex`. Search API: `(K("genre") == "drama") & (K("year") >= 2020) & K("tag").is_in(["a","b"]) & (K("archived") != True)`. No `not` wrapper, exists, nesting, geo, dates; Cloud ≤ 8 predicates. |
| Score, hybrid | `space l2` (default, squared), `cosine`, `ip`; `distances` lower-is-better; Search API scores ascending, RRF negated. Hybrid (Cloud): `Rrf(ranks=[Knn(return_rank=True), ...], k=60, weights)` or score arithmetic over `Knn` terms. |
| Limits, consistency, pricing, errors | Cloud: 300 records per write, 300 results per query, 32 metadata keys, 5,000,000 records per collection. Consistency undocumented (`read_level index_and_wal`, `index_only`, `index_and_bounded_wal` hints at WAL reads). Pricing $2.50 per GiB written, $0.33 per GiB-month, $0.0075 per TiB scanned plus $0.09 per GiB returned. Errors `{"error", "message"}`; 400/401/404/409/500. |

### 1.6 pgvector

| | |
|---|---|
| API, auth | SQL only (`CREATE EXTENSION vector`); `INSERT ... ON CONFLICT DO UPDATE`, `SELECT ... ORDER BY embedding <=> $1 LIMIT k`, `DELETE`/`UPDATE ... WHERE`; `SET hnsw.ef_search = 100`. Auth and pricing are whatever hosts Postgres. |
| Data model | `vector(n)` (store 16,000 dims, index 2,000), `halfvec(n)` (index 4,000), `bit(n)` (index 64,000), `sparsevec(n)` (`'{1:1,3:2}/5'`, HNSW ≤ 1,000 non-zeros); any number of vector columns; metadata in ordinary columns incl. JSONB. Indexes `USING hnsw (col vector_cosine_ops) WITH (m = 16, ef_construction = 64)` or `ivfflat ... (lists = 100)`; partial and expression indexes (`binary_quantize`, `::halfvec`). |
| Filter | `WHERE genre = 'drama' AND year >= 2020 AND tag = ANY (ARRAY['a','b']) AND NOT archived = true`; JSONB paths (`metadata->'a'->>'b'`, `@>`, `?`, `jsonb_path_exists`), `LIKE`, `~`, arrays `&&` (any) and `@>` (all), `tsvector @@`, PostGIS. Caveat: "With approximate indexes, filtering is applied after the index is scanned"; iterative scans `hnsw.iterative_scan = strict_order` or `relaxed_order` (0.8.0+, `hnsw.max_scan_tuples` 20,000) recover the shortfall. |
| Score, hybrid | Operators return distances, lower-is-better: `<->` L2, `<#>` negative inner product, `<=>` cosine distance, `<+>` L1, `<~>` Hamming, `<%>` Jaccard. Hybrid is `tsvector` plus RRF written in SQL; no fusion parameter. |
| Limits, consistency, pricing, errors | Postgres limits only; ACID, read-your-writes in a transaction. Errors are `SQLSTATE` (dimension mismatch code unverified). |

### 1.7 Elasticsearch

| | |
|---|---|
| API, auth | `PUT /{index}/_doc/{id}`, `_bulk` (NDJSON, 100 MB request cap), `GET /_doc/{id}`, `_mget`, `DELETE`, `_delete_by_query`, `_update` (`doc`, `doc_as_upsert`), `_search` with `knn` or `retriever`. Auth `Authorization: ApiKey <base64>` or `Bearer`. |
| Data model | `dense_vector` (`dims` ≤ 4096, `element_type float`, `bfloat16`, `byte`, `bit`; `similarity l2_norm`, `dot_product`, `cosine` (default), `max_inner_product`; `index_options.type hnsw`, `int8_hnsw` (default), `int4_hnsw`, `bbq_hnsw`, `flat`, `bbq_disk`), `sparse_vector` (ELSER), `semantic_text` (auto-chunk and embed); nested `dense_vector` for many vectors per document. |
| Filter | Query DSL as `knn.filter` (applied during ANN, so k results come back): `{"bool": {"filter": [{"term": {"genre": "drama"}}, {"range": {"year": {"gte": 2020}}}, {"terms": {"tag": ["a","b"]}}], "must_not": [{"term": {"archived": true}}]}}`; plus `exists`, `prefix`, `wildcard`, `regexp`, `match`, `nested`, `geo_distance`, date math. Other filters in the tree post-filter. |
| Score, hybrid | `_score` is a similarity transformed per metric (`l2_norm` → `1/(1+d²)`, `cosine` → `(1+cos)/2`, `dot_product` → `(1+dot)/2`); `knn.similarity` floors the raw value. Hybrid via `retriever` (`rrf`, `linear`, `text_similarity_reranker`). |
| Limits, consistency, pricing, errors | `num_candidates` ≤ 10,000, `index.max_result_window` 10,000. Near-real-time, `refresh_interval` 1 s (5 s Serverless), `refresh=wait_for`. Serverless VCU-hours (Search $0.09), Hosted instance-hours. Errors `{"error": {"type", "reason", "root_cause"}, "status"}`; 409 on version conflict. |

### 1.8 OpenSearch and Amazon OpenSearch Serverless

| | |
|---|---|
| API, auth | Same document APIs as Elasticsearch; `_search` with `knn`, `neural`, `neural_sparse`, `hybrid` and `?search_pipeline=`. Security plugin Basic auth; Serverless SigV4 with service `aoss`, custom `_id` only on search collections. |
| Data model | `knn_vector` (`dimension` 1–16,000, `data_type float`, `byte`, `binary`, `half_float`; `space_type l1`, `l2`, `linf`, `cosinesimil`, `innerproduct`, `hamming`, `hammingbit`; `method {name hnsw, ivf, flat, disk_ann; engine faiss, lucene, jvector}`; `mode on_disk`; `compression_level` ≤ 32x); `rank_features` / `sparse_vector` for neural sparse; `semantic` field (3.1) auto-embeds. |
| Filter | Same Query DSL. `knn` query `k` 1–10,000 (or `max_distance` / `min_score`), `filter` (faiss/lucene only, "efficient filtering" during traversal), `rescore.oversample_factor`; Boolean post-filters "may return significantly fewer than k". |
| Score, hybrid | `1/(1+d)` for the `l2` family, `(2-d)/2` for `cosinesimil`, engine-dependent for `innerproduct`; always higher-is-better. Hybrid: `hybrid` (≤ 5 subqueries) plus `normalization-processor` or `score-ranker-processor` pipeline. |
| Limits, consistency, pricing, errors | Bulk guidance 5–15 MB; `refresh_interval` 1 s; Serverless NextGen 5 s read-after-write, scales to zero (classic minimum 2 OCUs). OCU-hour pricing (examples $0.24/OCU-hour). Errors as Elasticsearch (assumed, unverified). |

### 1.9 Turbopuffer

| | |
|---|---|
| API, auth | `POST /v2/namespaces/:ns` writes (`upsert_rows`, `upsert_columns`, `patch_rows`, `patch_columns`, `deletes`, `delete_by_filter` ≤ 5M rows, `patch_by_filter`, conditional `*_condition`, `distance_metric cosine_distance` or `euclidean_squared`, `schema`); `POST /v2/namespaces/:ns/query` (`rank_by`, `top_k` ≤ 10,000, `filters`, `include_attributes`, `queries[]` ≤ 16, `rerank_by`, `consistency {level: strong (default) or eventual}`); `GET /v1/namespaces`, `GET /v1/namespaces/:ns/metadata`, `DELETE /v2/namespaces/:ns`. No fetch-by-id endpoint (filter on `id`). `Authorization: Bearer`. |
| Data model | Id u64, UUID or string ≤ 64 bytes; ≤ 8 vector attributes (`[N]f32`, `[N]f16`, `[N]i8`, multi-vector `[][N]f32`, ≤ 10,752 dims), sparse `{}f16` with `sparse_knn`; typed attributes incl. `datetime`, `uuid`, arrays, `bytes`; 1,024 attributes; 64 MiB documents; native `embed` option. |
| Filter | Array syntax: `["And", [["genre","Eq","drama"], ["year","Gte",2020], ["tag","In",["a","b"]], ["Not", ["archived","Eq",true]]]]`. Operators `Eq NotEq In NotIn Lt Lte Gt Gte`; arrays `Contains`, `NotContains`, `ContainsAny`, `NotContainsAny`, `AnyLt`..`AnyGte`; patterns `Glob`, `IGlob`, `Regex`, `Fuzzy` (schema-gated); FTS `ContainsAllTokens`, `ContainsTokenSequence`, `ContainsAnyToken`; `And`, `Or`, `Not`. No object type (flatten), no geo, no `ContainsAll`. |
| Score, hybrid | `$dist` is the ANN distance (ascending) or the BM25 score (cosine formula unverified). Hybrid: multi-query `queries[]` with `rerank_by: ["RRF"]` (k undocumented) or model rerank; `compute_attributes` for client-side fusion. |
| Limits, consistency, pricing, errors | 512 MB writes, 256 shards, `limit + offset` < 10,000. Strong consistency by default ("a subsequent query will immediately see the write"); opt-in eventual (staleness up to about an hour). $0.33/GB-month indexed, $2/GB written, $1/PB queried (1.28 GB minimum per query), $0.05/GB returned, $16/month minimum. Errors `{"status": "error", "error"}`; 409 while an index builds, 429. |

### 1.10 LanceDB

| | |
|---|---|
| API, auth | Embedded (`lancedb.connect("./dir")`) and Enterprise/Cloud (`db://`, `api_key`; REST `x-api-key` and `x-lancedb-database`, OAuth 2.0). `create_table`, `add`, `merge_insert("id")` upsert, `search(...).where(...).limit(n)`, `delete(predicate)`, `update(where, values)`, versions (`list_versions`, `checkout`, `restore`). |
| Data model | Arrow tables; no mandatory id; many vector columns, multivector (cosine only); no sparse. Indexes `IVF_PQ`, `IVF_RQ`, `IVF_HNSW_SQ`, `IVF_HNSW_PQ`, `IVF_HNSW_FLAT`; scalar `BTREE`, `BITMAP`, `LABEL_LIST`; FTS index. |
| Filter | SQL/DataFusion string, pre-filter by default: `genre = 'drama' AND year >= 2020 AND tag IN ('a', 'b') AND NOT (archived IS TRUE)`; backtick nested paths, `LIKE`, `regexp_match`, `array_has_any`, `array_has_all`, `date '...'` literals; `!=` and `NOT IN` not on the filtering page (unverified); no geo. |
| Score, hybrid | `distance_type l2` (default), `cosine`, `dot`, `hamming`; `_distance` lower-is-better; hybrid `_relevance_score` higher via client-side `RRFReranker` (default). |
| Limits, consistency, pricing, errors | No documented dimension or batch caps. Every write is a table version; `read_consistency_interval`. Cloud pricing unverified; REST error codes unverified. |

### 1.11 MongoDB Atlas Vector Search

| | |
|---|---|
| API, auth | `$vectorSearch` aggregation stage (`index`, `path`, `queryVector`, `numCandidates` ≤ 10,000, `limit`, `exact`, `filter`, `parentFilter`, `returnStoredSource`), score `{$meta: "vectorSearchScore"}`; `createSearchIndex(name, "vectorSearch", {...})`; CRUD is ordinary MongoDB over the wire protocol, not HTTP (SCRAM/X.509/OIDC); Admin API OAuth service accounts. |
| Data model | `_id` any BSON; vector fields as number arrays or BinData `float32`, `int8`, `int1`; `{type: "vector", path, numDimensions ≤ 8192, similarity euclidean, cosine or dotProduct, quantization none, scalar or binary, hnswOptions}` plus `{type: "filter", path}`; many vector fields per index but one per `$vectorSearch`; `autoEmbed` fields (Voyage models, per-token). No sparse. |
| Filter | MQL subset, pre-filter: `{"$and": [{"genre": "drama"}, {"year": {"$gte": 2020}}, {"tag": {"$in": ["a","b"]}}, {"archived": {"$ne": true}}]}`; whitelist `$eq $ne $gt $lt $gte $lte $in $nin $exists $not $nor $and $or`; no `$regex`, `$all`, `$elemMatch`, geo or text operators. |
| Score, hybrid | Score "in a fixed range from 0 to 1", higher-is-better (per-metric formulas unverified). Hybrid `$rankFusion` (RRF, k fixed 60; 8.0+) and `$scoreFusion` (8.3+). |
| Limits, consistency, pricing, errors | Index sync through `mongot` is asynchronous (`queryable`). Cluster hours plus Search Nodes (S20 $0.13/h ...); Voyage auto-embedding per 1M tokens. Errors `{ok: 0, errmsg, code, codeName}`; overload rejection code 489. |

### 1.12 Redis (Query Engine, RedisVL)

| | |
|---|---|
| API, auth | `FT.CREATE idx ON HASH or JSON PREFIX 1 doc: SCHEMA f VECTOR FLAT, HNSW or SVS-VAMANA n TYPE FLOAT32 ... DIM d DISTANCE_METRIC L2, IP or COSINE`; records are keys (`HSET`/`JSON.SET`, indexed synchronously); `FT.SEARCH`, `FT.AGGREGATE`, `FT.HYBRID` (8.4+); fetch `HGETALL`; delete `DEL`; no server-side delete-by-query (RedisVL `drop_by_filter`). `AUTH`; RESP errors, no HTTP codes. Tenancy by key prefix. |
| Data model | Vector field types `BFLOAT16`, `FLOAT16`, `FLOAT32`, `FLOAT64`, `INT8`, `UINT8`; JSON `$.embeddings[*]` for several vectors; metadata `TEXT`, `TAG`, `NUMERIC`, `GEO`, `GEOSHAPE`; JSON indexed at leaves only; no sparse. Max `DIM` undocumented. |
| Filter | Query string, DIALECT 2: `(@genre:{drama} @year:[2020 +inf] @tag:{a\|b} -@archived:{true})=>[KNN 10 @vec $blob AS score]`. Tag union `{a\|b}` (in / contains-any), `-` not, numeric ranges and `>=`, `ismissing(@f)` (needs `INDEXMISSING`), prefix/infix/fuzzy text, geo; contains-all by repeating `@f:{a} @f:{b}`; no nested scoping. Pre-filter before KNN (`HYBRID_POLICY BATCHES` or `ADHOC_BF`). |
| Score, hybrid | `__<field>_score` is a distance (`COSINE` = 1 − cos, `IP` = 1 − dot, `L2`), lower-is-better. `FT.HYBRID ... COMBINE RRF [CONSTANT 60] [WINDOW 20]` or `LINEAR [ALPHA] [BETA]`; RedisVL `HybridQuery`. |
| Limits, consistency, pricing, errors | `search-max-search-results` 1,000,000 (10,000 on some Cloud tiers), `search-timeout` 500 ms. Writes index synchronously. Essentials from $5/month, Pro from $0.014/h with $200 minimum. |

### 1.13 Vespa

| | |
|---|---|
| API, auth | Schema-deployed (no runtime create). Document v1 `POST`/`PUT`/`GET`/`DELETE /document/v1/{ns}/{type}/docid/{id}`, selection-based delete/update, visiting with `continuation`; `POST /search/` with YQL (`hits` ≤ 400 default, `offset` ≤ 1000). Auth mTLS or `Authorization: Bearer` tokens on Vespa Cloud. |
| Data model | Document id `id:<ns>:<type>::<id>`; tensors `tensor<float>(x[384])` with `index { hnsw { max-links-per-node, neighbors-to-explore-at-insert } }` and `attribute { distance-metric euclidean, angular, dotproduct, prenormalized-angular, geodegrees or hamming }`; mixed tensors for many vectors; mapped tensors for sparse; `string` with `enable-bm25`. |
| Filter | YQL: `select * from doc where {targetHits:10}nearestNeighbor(embedding, q) and genre contains "drama" and year >= 2020 and tag in ("a","b") and !(archived = true)`; `sameElement` for struct arrays, `matches` regex, `range`, `geoLocation`, `weakAnd`; `is null` unverified. Pre-filtering by default, tuned by `post-filter-threshold`, `approximate-threshold`, `filter-first-threshold`. |
| Score, hybrid | `distance(field, name)` lower-is-better; `closeness = 1/(1+distance)` and `relevance` higher. Hybrid is the deployed rank profile (`reciprocal_rank_fusion`, `normalize_linear`). |
| Limits, consistency, pricing, errors | Writes sync to all replicas, reads best-effort, no read-your-writes; `condition` test-and-set (412); no multi-document transactions. Vespa Cloud per vCPU/GB-hour by tier. Errors `{"pathId", "message"}` (400/404/412/429/503/504); query `root.errors[]`. |

### 1.14 Azure AI Search

| | |
|---|---|
| API, auth | `POST /indexes/{name}/docs/search?api-version=2026-04-01` with `vectorQueries[] {kind vector or text, vector, fields, k, exhaustive, weight, filterOverride (preview)}`, `search`, `filter`, `vectorFilterMode preFilter (default for indexes created after Oct 2023), postFilter or strictPostFilter (preview)`, `queryType semantic`, `semanticConfiguration`, `top`, `select`. Auth `api-key` header or Entra ID roles (`Search Index Data Reader`). |
| Data model | Vector fields `Collection(Edm.Single)`, `Edm.Half`, `Edm.Int16`, `Edm.SByte` with `dimensions` and `vectorSearchProfile`; `vectorSearch.algorithms[]` `hnsw` or `exhaustiveKnn` with `metric cosine`, `euclidean`, `dotProduct`, `hamming`; scalar and binary compression; filterable string/numeric/collection fields. |
| Filter | OData: `genre eq 'drama' and year ge 2020 and tags/any(t: search.in(t, 'a,b')) and not (archived eq true)`. `eq ne gt lt ge le`, `and or not` (`not` needs parentheses around comparisons), `any`/`all` lambdas, `search.in`, `search.ismatch` and `search.ismatchscoring` (full-text inside a filter), `geo.distance`, `geo.intersects`, `eq null`, datetime literals. Clause count limited ("hundreds" is the risk zone). |
| Score, hybrid | `@search.score` is cosine similarity for pure vector, RRF values for hybrid, `@search.rerankerScore` for semantic ranking (needs `k` 50). Hybrid always RRF with `hybridSearch.maxTextRecallSize` (preview). |
| Limits, consistency, pricing, errors | Vector quota per partition; 429 on overload; indexing latency before visibility (not quantified). Pricing search units by tier (not re-verified). |

### 1.15 Google Vertex AI Vector Search

| | |
|---|---|
| API, auth | Index → IndexEndpoint → DeployedIndex; batch updates from GCS or streaming `upsertDatapoints` / `removeDatapoints` (per-request caps unverified; quotas page 404). `POST https://{public domain}/v1/projects/{p}/locations/{l}/indexEndpoints/{e}:findNeighbors` with `deployed_index_id`, `queries[] {datapoint {datapoint_id, feature_vector, sparse_embedding {values, dimensions}, restricts, numeric_restricts}, neighbor_count, per_crowding_attribute_neighbor_count, fraction_leaf_nodes_to_search_override, rrf_ranking_alpha}`. OAuth bearer. ScaNN. |
| Data model | Datapoints with one dense `feature_vector`, optional `sparse_embedding`, `restricts[] {namespace, allow[], deny[]}` and `numeric_restricts[] {namespace, value_int, value_float or value_double}`. No free-form metadata. |
| Filter | A namespace model, not an expression: queries carry `restricts` and `numeric_restricts` with `op LESS`, `LESS_EQUAL`, `EQUAL`, `GREATER_EQUAL`, `GREATER`; AND across namespaces, OR within, deny-lists exclude. Reference filter: `restricts: [{namespace: "genre", allow: ["drama"]}, {namespace: "tag", allow: ["a","b"]}, {namespace: "archived", deny: ["true"]}]`, `numeric_restricts: [{namespace: "year", value_int: 2020, op: "GREATER_EQUAL"}]`. Unsupported: `OR` across fields, `NOT_EQUAL`, nesting, prefix, exists. |
| Score, hybrid | Hybrid distances are inverted ("a higher value means a shorter distance"); distance measure enum not re-verified. Hybrid = RRF with `rrf_ranking_alpha` (1 dense-only, 0 sparse-only). |
| Limits, consistency, pricing, errors | Streaming vs batch index freshness; pricing serving node-hours by machine type plus per-GB index building (official page unreadable today; third-party figures around $3/GiB, unverified). |

### 1.16 Amazon S3 Vectors

| | |
|---|---|
| API, auth | Vector buckets → indexes (`distanceMetric euclidean` or `cosine`, 1–4,096 dims, non-filterable metadata keys fixed at creation). `PutVectors` ≤ 500, `GetVectors` ≤ 100, `DeleteVectors` ≤ 500, `ListVectors` (1,000 per page, 16 parallel segments), `POST /QueryVectors` (`queryVector {float32}`, `topK` ≤ 10,000, 100 per page, `filter`, `returnDistance`, `returnMetadata`, `queryMode CLASSIC` or `ENHANCED`) → `vectors[] {key, distance, metadata}` and `distanceMetric`. SigV4; filtering or returning metadata needs `s3vectors:GetVectors`. |
| Data model | One vector per key; metadata string, number, boolean, list; 40 KB per vector (2 KB filterable, ≤ 50 keys, ≤ 10 non-filterable keys per index). No sparse, no nesting. |
| Filter | `{"$and": [{"genre": {"$eq": "drama"}}, {"year": {"$gte": 2020}}, {"tag": {"$in": ["a","b"]}}, {"archived": {"$ne": true}}]}`. Operators `$eq $ne $gt $gte $lt $lte $startsWith $in $nin $exists $and $or`; `$eq` on a list matches any element; ≤ 100 constraints per query. ENHANCED indexes pre-filter; CLASSIC filters during search and may return fewer than `topK`. No `$not`, nesting, geo, dates. |
| Score, hybrid | `distance` lower-is-better (`euclidean`, `cosine`). No lexical lane, no fusion. |
| Limits, consistency, pricing, errors | 2 billion vectors per index, 10,000 indexes per bucket, 20 MiB payloads, 1,000 write req/s per index. Consistency not stated on the pages read (unverified). $0.06/GB-month, $0.20/GB PUT (128 KB minimum), $2.50 per million queries plus per-TB processed, $0.01/GB returned. `ValidationException` 400 (`fieldList`), `NotFoundException` 404, `TooManyRequestsException` 429, `ServiceUnavailableException` 503. |

### 1.17 In-process libraries (the local peer)

| Library | Ids | Metrics and score | Filtering | Persistence |
|---|---|---|---|---|
| FAISS | int64 via `IndexIDMap` / `add_with_ids`; `-1` = missing | `METRIC_L2` (squared, lower), `METRIC_INNER_PRODUCT` (higher), `L1`, `Linf`, `Lp`, `Canberra`, `BrayCurtis`, `JensenShannon`; cosine = normalize + IP | `SearchParameters.sel` with `IDSelectorRange`, `IDSelectorArray`, `IDSelectorBatch`, `IDSelectorBitmap`, `IDSelectorNot`; no metadata store | `write_index` / `read_index` (not re-read) |
| hnswlib | integer labels on `add_items(data, ids)`; `mark_deleted` | `l2` (squared), `ip` (`1 − dot`), `cosine` (`1 − cos`): all distances, lower | `knn_query(data, k, filter=<callable on label>)`, `num_threads=1` advised | `save_index` / `load_index` |
| USearch | 128-bit keys, several vectors per key | `DenseMetric.INNER`, `ANGULAR`, `EUCLIDEAN`, `HAMMING`, `JACCARD`; `Matches(keys, distances, counts)` | `predicate=lambda key: ...` admission predicate during traversal; `Traversal.SCAN` for exact | `save`, `load_ram`, `view_ram` |
| sqlite-vec, DuckDB VSS, NumPy | SQL rows / array index | SQL distance functions / `argpartition` | SQL `WHERE` / boolean masks | the database file |

None stores metadata beyond an id, so the in-process adapter owns a side
table and evaluates the canonical filter AST into an id selector or
predicate — which makes it the reference evaluator for filter fixtures.

## 2. Comparison

| Store | Id | Nested metadata | Sparse | Vectors/record | Score direction | Fusion locus | Consistency | Auth | Pricing unit |
|---|---|---|---|---|---|---|---|---|---|
| Pinecone | str | no | 1 slot | 1 + sparse | higher | client | eventual + LSN | `Api-Key` | RU/WU + GB |
| Weaviate | UUID | preview | no (BM25F) | named | distance lower; bm25 higher | `hybrid.fusionType` | ONE/QUORUM/ALL | Bearer | 1M dims/month |
| Qdrant | u64/UUID | yes + `nested` | named | named + multi | Euclid lower; Cosine/Dot higher | `query.fusion` | `wait`, `ordering` | `api-key` | vCPU/GB-hour |
| Milvus | i64/varchar | JSON paths | field | ≤ 4 (10) | L2 lower; IP/COSINE higher | `rerank.strategy` | Strong/Bounded/Session/Eventually | Bearer user:pass | vCU / CU-hour |
| Chroma | str | no | Cloud key | 1 | lower | `Rrf` rank expr | unverified | `x-chroma-token` | GiB written/stored/scanned |
| pgvector | any PK | JSONB | `sparsevec` | any | lower | SQL | ACID | Postgres | hosting |
| Elasticsearch | `_id` | `nested` | `sparse_vector` | many | higher (transformed) | `retriever` | NRT 1 s | ApiKey/Bearer | VCU-hour |
| OpenSearch | `_id` | `nested` | `rank_features` | many | higher | search pipeline | NRT 1–5 s | Basic / SigV4 | OCU-hour |
| Turbopuffer | u64/UUID/str | no | `{}f16` | ≤ 8 | lower (ANN) / higher (BM25) | `rerank_by` | strong default | Bearer | GB stored/written/queried |
| LanceDB | none required | dot path | no | many | lower | client reranker | versioned | `x-api-key` | unverified |
| MongoDB Atlas | `_id` | dot path | no | many, 1 per query | 0..1 higher | `$rankFusion` | async index | wire / OAuth | cluster + search nodes |
| Redis | key | leaves | no | JSON arrays | lower | `FT.HYBRID COMBINE` | sync index | `AUTH` | tiers |
| Vespa | doc id | `sameElement` | mapped tensors | mixed tensors | `distance` lower / `relevance` higher | rank profile | replica sync, no RYW | mTLS/Bearer | vCPU/GB-hour |
| Azure AI Search | key field | `any/all` | no | many | higher | RRF built-in | indexing latency | `api-key`/Entra | search units |
| Vertex | `datapoint_id` | no | `sparse_embedding` | 1 + sparse | inverted distance, higher | `rrf_ranking_alpha` | streaming/batch | OAuth | node-hour + GB |
| S3 Vectors | `key` | no | no | 1 | distance lower | none | not stated (unverified) | SigV4 | GB + queries |

## 3. Canonical IR proposal

### 3.1 Operations as shapes

Mint `Capability("vectorstore")` with one request/response shape pair per
operation (§11 step 1): `("vectorstore", "upsert.request")`,
`query.request`, `fetch.request`, `delete.request`, `update.request`
(metadata patch) and `search.request` (multi-lane; hybrid page). Index and
namespace management is deliberately not a shape: it has no cross-store
semantics worth converting and is bound at the front door
(`ocai.vectorstore.store("pinecone/my-index", namespace=...)`) the way a
model name is bound for chat (§11 step 3). Graphs are born partitioned per
shape, so `Catalog.resolve` gains the `role=` kwarg §11 reserves for the
first multi-op capability. Payloads: `UpsertRequest(records)`,
`QueryRequest(vector | sparse | id, filters, limit, include_vectors,
include_metadata)`, `FetchRequest(ids | filters, limit, cursor)`,
`DeleteRequest(ids | filters | all)`, `UpdateRequest(ids | filters, set,
remove)`; responses are `Record`/`QueryResult` lists plus a `cursor` on
fetch and `matched` counts on filtered delete/update.

### 3.2 Canonical filter AST

The filter is the survey's biggest divergence: four JSON-tree dialects
(Pinecone, Chroma, S3 Vectors, MongoDB), two clause-array dialects (Qdrant,
Turbopuffer), typed trees (Weaviate, Elasticsearch/OpenSearch, Bedrock),
string languages (Milvus, LanceDB SQL, pgvector SQL, Azure OData, Vespa
YQL, Redis, Meilisearch, Typesense) and one namespace model (Vertex). One
AST with a per-operator census keeps conversion reportable:

```python
@dataclass
class Cmp(IRObject):      # {field, op, value}; field is a dotted path, "tags[]" projects elements
@dataclass
class Bool(IRObject):     # {op: and|or|not, args: list[Filter]}
@dataclass
class Nested(IRObject):   # same-element scoping: {path, filter}
@dataclass
class FilterUnknown(IRObject)   # total-decode fallback
type Filter = Cmp | Bool | Nested | FilterUnknown
```

`FilterOp` is an open code. Census per dialect (Y native, E emulated by a
declared rewrite, N `UNSUPPORTED`-and-reported, never dropped):

| op | Pinecone | Weaviate | Qdrant | Milvus | Chroma | pgvector | ES/OS | Turbopuffer | LanceDB | Atlas | Redis | Vespa | Azure | Vertex | S3 Vectors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `eq` | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y (allow) | Y |
| `ne` | Y | Y | E (`must_not`) | Y | unverified | Y | E | Y | unverified | Y | E (`-`) | E (`!`) | Y | E (deny) | Y |
| `gt gte lt lte` | Y (numbers) | Y | Y | Y | Y (numbers; `lt` unverified) | Y | Y | Y | Y | Y | Y | Y | Y | Y (no `ne`) | Y (numbers) |
| `in` | Y | E (`ContainsAny`) | Y (`any`) | Y | Y | Y | Y (`terms`) | Y | Y | Y | E (`{a\|b}`) | Y | E (`search.in`) | Y (allow list) | Y |
| `nin` | Y | Y (`ContainsNone`) | Y (`except`) | Y | Y | Y | E | Y | unverified | Y | E | E | E | E (deny) | Y |
| `and or` | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | and across / or within namespaces only | Y |
| `not` | Y | Y | E | Y | N (leaf rewrite only) | Y | Y | Y | Y | Y | Y | Y | Y | N | N |
| `exists / is_null` | `$exists` only | `IsNull` (index flag) | Y | Y | N | Y | Y | E (`Eq null`) | Y | `$exists` | E (index flag) | unverified | Y | N | `$exists` |
| `contains_any` | E (`$in`) | Y | Y | Y | E | Y (`&&`) | Y | Y | Y | E (`$in`) | Y | E | E (`any`) | Y | E (`$in`) |
| `contains_all` | E | Y | E | Y | E | Y (`@>`) | E | N | Y | E | E | E | Y (`all`) | E | E |
| `prefix` | N | Y (`Like`) | Y | Y | N (documents only) | Y | Y | Y (`Glob`) | Y | N | Y | unverified | E | N | Y |
| `like / regex` | N | `Like` only | `substring` (strict mode rejects) | Y | documents only | Y | Y | Y | Y | N | Y | Y | E | N | N |
| `text_match` | FTS fields only | E (bm25 lane) | Y | Y | documents only | Y | Y | Y | E | N | Y | Y | Y | N | N |
| `geo` | N | Y | Y | N | N | PostGIS | Y | N | N | N | Y | Y | Y | N | N |
| `date range` | E (numbers) | Y | Y | E | E | Y | Y | Y | Y | Y | E | E | Y | E | E |
| `nested` | N | preview | Y | N | N | E (`jsonb_path`) | Y | N | N | N | N | Y | Y | N | N |

Rules that keep this honest rather than lowest-common-denominator:

- Each edge declares its column of this table in its `EdgeContract` census
  under the reserved recursive token `filters[**]` — this capability lands
  the `[**]` implementation `spec/README.md` reserves. An N cell is a
  census entry of disposition `UNSUPPORTED`: strict mode refuses, annotate
  mode records the loss. E cells are `RENAMED`/`EMULATED` with a note
  (Vertex `ne` → deny-list, Chroma `not` pushed to the leaf, Redis `in` →
  tag union).
- Differences that survive a successful mapping are `SemanticShift`s, not
  field losses: pre- vs post-filter execution (pgvector, Azure `postFilter`,
  OpenSearch Boolean post-filter, Vespa thresholds) changes how many rows
  return; list-field equality meaning "any element" (Pinecone, Qdrant, S3
  Vectors); `not` matching missing fields (Meilisearch).
- Values pass verbatim (rule 5): a `$in` list over 10,000 on Pinecone or
  over 100 constraints on S3 Vectors is the provider's 400 through the
  taxonomy, never pre-clamped.

### 3.3 Score semantics

One field carries three things across the survey: distances (Weaviate,
Qdrant Euclid, Milvus L2, Chroma, pgvector, Turbopuffer, LanceDB, Redis,
Vespa `distance`, S3 Vectors), similarities (Pinecone, Milvus IP/COSINE,
Elasticsearch/OpenSearch transformed, Atlas 0..1, Azure, Vertex inverted)
and fused ranks (RRF). `QueryResult.score` stays higher-is-closer; two
additive fields make the conversion visible: `score_kind` (open code
`similarity | distance | rrf | normalized | engine`) and `native_score`
(verbatim). An edge that negates or inverts a distance declares
`SemanticShift(kind="score_rescaled")` with the formula in `note`; it never
converts between metrics, which would be the vector-space conversion the
doctrine forbids. `VectorStore.details` keeps reporting the metric.

### 3.4 Namespaces and tenancy

Four models: a per-call namespace (Pinecone, Turbopuffer, Chroma
tenant/database path, Vespa), a tenant object with lifecycle (Weaviate), a
filterable key (Qdrant `is_tenant`, Milvus Partition Key, Atlas, every SQL
store), and none (S3 Vectors, Vertex, FAISS). Canonical: `namespace: str |
None` on every request, bound at the front door, overridable per call. An
edge to a store without namespaces maps it to a reserved metadata key
(`EMULATED`, declared) or reports `UNSUPPORTED`. `CallContext.tenant` is
governance, not routing: a policy hook may check that `namespace` matches
it; the kernel never derives one from the other.

### 3.5 Does the provisional port fit?

`ocai.vectorstore` (`Record`, `QueryResult`, `QueryFilter = dict[str,
Any]`, port `get/create/update/delete/query`) fits the shape of the survey
and needs only additive changes:

1. `QueryFilter` becomes the typed `Filter` union registered through
   `TagRegistry`; the dict alias keeps decoding via tolerant `from_dict`.
2. `Record` gains `sparse: SparseVector | None` (indices/values) and
   `vectors: dict[str, Vector] | None` for named vectors; `vector` stays
   the default lane.
3. `QueryResult` gains `score_kind` and `native_score`.
4. The port gains `search(request)` and a `namespace` keyword on every
   method; `get` returns a `cursor` for listing (most stores page by
   token); `create` is documented as upsert semantics (Pinecone, Qdrant,
   Turbopuffer, Milvus all replace on id).
5. `Usage` gains open unit codes `read_units`, `write_units`,
   `search_units`, `bytes_scanned`, `bytes_returned` — data, not a release.
6. `details` is required to carry `metric` and `dimension` so
   `score_kind` can be derived.
7. `Document`/`Vector` hoist decision (§2.8): keep `Vector` local;
   `Record.content: str` suffices for every store surveyed.

Nothing is removed or renamed; the package stays additive through promotion.

## 4. H3 recommendation, priority and effort

**First local adapter: FAISS** (`IndexFlatIP`/`IndexHNSWFlat` behind
`IndexIDMap`, SQLite side table for metadata and content), packaged as
`ocai-faiss` with USearch and hnswlib as optional extras behind one
`LocalVectorStore`. It proves the port-plane peer claim (`route.host =
"in-process"`, same `CallResult`, interceptors compose) and, because it
must evaluate the canonical filter AST itself, becomes the reference
evaluator for filter conformance fixtures. USearch is the runner-up
(predicate filtering during traversal resembles hosted pre-filtering).

**First remote store: Qdrant.** The richest, most regular filter dialect
(every census row except regex is native, so the first census is mostly
`EXACT`); one Query API covering dense, sparse, text and fusion (the
`search` shape is one wire call); explicit consistency knobs (`wait`,
`ordering`) that exercise `SemanticShift`; documented error bodies and 429
behaviour for the taxonomy; a self-hostable server for recorded wire pairs
without secrets; and the `api-key` header for the credential-at-the-leaf
rule. Pinecone has the larger installed base but is mid-migration between
two incompatible APIs with flat metadata that would make the first census
mostly `UNSUPPORTED`; it is the right second store precisely because it
stresses the honesty and version-resilience machinery.

| Store | Priority | Effort | Why |
|---|---|---|---|
| Qdrant | P0 | M | first remote; full AST; Query API covers `search` |
| In-process FAISS/USearch | P0 | M | H3 peer proof; reference filter evaluator |
| Pinecone (Documents API) | P1 | M–L | installed base; two API versions = version-resilience proof |
| pgvector | P1 | M | SQL printer shared with LanceDB and FTS; enterprise default |
| Elasticsearch / OpenSearch | P1 | L | one codec family; hybrid P0 on the companion page |
| Weaviate | P2 | L | gRPC-first clients, GraphQL filter tree, tenant lifecycle |
| Milvus / Zilliz | P2 | M | expression printer; partitions; load/release lifecycle |
| Chroma | P2 | S–M | local dev favourite; two query surfaces |
| Azure AI Search | P2 | M | OData printer; RRF + semantic ranker |
| MongoDB Atlas | P2 | M | wire protocol, not HTTP: needs a non-`ocai.wire` transport |
| Turbopuffer, LanceDB | P3 | S–M | clean APIs, smaller base; LanceDB is a library, not a wire |
| Redis | P3 | M | RESP transport; query-string printer |
| Vespa | P3 | L | schema-deployed; fusion lives in the deployed rank profile |
| Vertex Vector Search | P3 | M | namespace-restrict filter model is a poor fit |
| S3 Vectors | P3 | S | tiny API; SigV4; cheap cold tier |

Effort: S under a week, M one to three weeks, L more, including fixtures
and recorded wire pairs.

## Sources

All read 2026-11-10; the most load-bearing pages per store.

- Pinecone: https://docs.pinecone.io/guides/search/filter-by-metadata, https://docs.pinecone.io/guides/search/hybrid-search, https://docs.pinecone.io/reference/api/database-limits/operation-limits, https://docs.pinecone.io/guides/index-data/check-data-freshness, https://docs.pinecone.io/reference/api/errors, https://docs.pinecone.io/reference/api/2026-07/data-plane/search_documents, https://docs.pinecone.io/reference/api/2025-10/data-plane/query, https://www.pinecone.io/pricing/
- Weaviate: https://docs.weaviate.io/weaviate/api/graphql/filters, https://docs.weaviate.io/weaviate/search/hybrid, https://docs.weaviate.io/weaviate/config-refs/distances, https://docs.weaviate.io/weaviate/concepts/replication-architecture/consistency, https://docs.weaviate.io/weaviate/manage-collections/multi-tenancy, https://raw.githubusercontent.com/weaviate/weaviate/main/openapi-specs/schema.json, https://weaviate.io/pricing
- Qdrant: https://qdrant.tech/documentation/concepts/filtering/, https://qdrant.tech/documentation/concepts/hybrid-queries/, https://qdrant.tech/documentation/concepts/collections/, https://qdrant.tech/documentation/scaling/consistency-guarantees/, https://qdrant.tech/documentation/security/, https://api.qdrant.tech/api-reference/search/query-points, https://qdrant.tech/pricing/
- Milvus / Zilliz: https://milvus.io/docs/boolean.md, https://milvus.io/docs/json-operators.md, https://milvus.io/docs/array-operators.md, https://milvus.io/docs/multi-vector-search.md, https://milvus.io/docs/full-text-search.md, https://milvus.io/docs/consistency.md, https://milvus.io/docs/metric.md, https://milvus.io/docs/limitations.md, https://milvus.io/docs/authenticate.md, https://docs.zilliz.com/docs/limits, https://zilliz.com/pricing
- Chroma: https://docs.trychroma.com/docs/querying-collections/metadata-filtering, https://docs.trychroma.com/docs/querying-collections/full-text-search, https://docs.trychroma.com/cloud/search-api/filtering, https://docs.trychroma.com/cloud/search-api/hybrid-search, https://docs.trychroma.com/cloud/quotas-limits, https://docs.trychroma.com/cloud/pricing, https://api.trychroma.com/openapi.json
- pgvector: https://github.com/pgvector/pgvector/blob/master/README.md
- Elasticsearch: https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/dense-vector, https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-knn-query, https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers, https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-bulk, https://www.elastic.co/pricing/serverless-search
- OpenSearch: https://docs.opensearch.org/latest/mappings/supported-field-types/knn-vector/, https://docs.opensearch.org/latest/mappings/supported-field-types/knn-spaces/, https://docs.opensearch.org/latest/query-dsl/specialized/k-nn/index/, https://docs.opensearch.org/latest/query-dsl/compound/hybrid/, https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-vector-search.html, https://aws.amazon.com/opensearch-service/pricing/
- Turbopuffer: https://turbopuffer.com/docs/write, https://turbopuffer.com/docs/query, https://turbopuffer.com/docs/schema, https://turbopuffer.com/docs/limits, https://turbopuffer.com/docs/guarantees.md, https://turbopuffer.com/pricing
- LanceDB: https://docs.lancedb.com/search/filtering, https://docs.lancedb.com/search/vector-search, https://docs.lancedb.com/search/hybrid-search, https://docs.lancedb.com/tables/versioning, https://docs.lancedb.com/enterprise/authentication.md
- MongoDB Atlas: https://www.mongodb.com/docs/vector-search/query/aggregation-stages/vector-search-stage.md, https://www.mongodb.com/docs/vector-search/indexes/vector-search-type.md, https://www.mongodb.com/docs/manual/reference/operator/aggregation/rankFusion/, https://www.mongodb.com/docs/manual/reference/operator/aggregation/scoreFusion/, https://www.mongodb.com/pricing
- Redis: https://redis.io/docs/latest/develop/ai/search-and-query/vectors/, https://redis.io/docs/latest/develop/ai/search-and-query/query/vector-search/, https://redis.io/docs/latest/develop/ai/search-and-query/advanced-concepts/query_syntax/, https://redis.io/docs/latest/commands/ft.hybrid/, https://redis.io/docs/latest/develop/ai/search-and-query/administration/configuration/, https://redis.io/pricing/
- Vespa: https://docs.vespa.ai/en/querying/nearest-neighbor-search.html, https://docs.vespa.ai/en/querying/approximate-nn-hnsw.html, https://docs.vespa.ai/en/reference/query-language-reference.html, https://docs.vespa.ai/en/reference/document-v1-api-reference.html, https://docs.vespa.ai/en/content/consistency.html, https://cloud.vespa.ai/price-calculator.html
- Azure AI Search: https://learn.microsoft.com/en-us/azure/search/vector-search-filters, https://learn.microsoft.com/en-us/azure/search/search-query-odata-filter, https://learn.microsoft.com/en-us/azure/search/hybrid-search-how-to-query, https://learn.microsoft.com/en-us/azure/search/vector-search-index-size
- Vertex AI Vector Search: https://docs.cloud.google.com/vertex-ai/docs/vector-search/filtering, https://docs.cloud.google.com/vertex-ai/docs/vector-search/query-index-public-endpoint, https://docs.cloud.google.com/vertex-ai/docs/vector-search/about-hybrid-search, https://docs.cloud.google.com/vertex-ai/docs/vector-search/overview
- Amazon S3 Vectors: https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-metadata-filtering.html, https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-limitations.html, https://docs.aws.amazon.com/AmazonS3/latest/API/API_S3VectorBuckets_QueryVectors.html, https://aws.amazon.com/s3/pricing/
- In-process: https://github.com/facebookresearch/faiss/wiki/Setting-search-parameters-for-one-query, https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances, https://github.com/nmslib/hnswlib, https://github.com/unum-cloud/usearch, https://github.com/unum-cloud/usearch/blob/main/python/README.md
