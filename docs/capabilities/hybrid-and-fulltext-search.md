# Hybrid and full-text search

Currency: researched against official documentation on 2026-11-10. Syntax
and parameter names were read from the pages under Sources on that date;
items the pages did not show are marked unverified. Companion to the
[vector-stores](vector-stores.md) page, which holds the per-store filter
dialects and the canonical filter AST.

## Why this is one capability with vector search

A BM25 engine answers the same question a vector store does ("which stored
records best match this query, subject to this filter, top k") with a
different scoring function. Every engine below carries a lexical and a
dense (often also sparse) index behind one query endpoint, and every store
on the companion page has grown a lexical lane. So full-text engines are
peers of vector stores at the `VectorStore` port, differing in which query
lanes they accept and how they fuse them; by the §11 litmus test that is one
capability with several dialects, hence a `search` operation on the
vectorstore capability, not a new capability.

## Engines

### Elasticsearch

- Lexical `match`/`multi_match` (BM25). Dense `knn` retriever: `field`,
  `query_vector` (or `query_vector_builder`), `k`, `num_candidates` (≤
  10,000, default `min(1.5 * k, 10000)`), `filter`, `similarity` floor,
  `rescore_vector.oversample`. Sparse `sparse_vector` with ELSER;
  `semantic_text` hides the inference.
- Fusion in the `retriever` tree: `rrf {retrievers[] (each may carry
  weight since 9.2), rank_constant 60, rank_window_size 10, filter}` or the
  multi-field `{rrf: {query, fields}}`; `linear {retrievers[] {retriever,
  weight 1.0, normalizer}, normalizer none|minmax|l2_norm, rank_window_size,
  filter}`; `text_similarity_reranker` for inference reranking. Top-level
  `query`, `knn`, `sort`, `rescore`, `search_after` cannot coexist with a
  retriever. RRF `_score` values are small sums of `1/(k+rank)`, linear
  scores are normalized sums; neither compares to a raw cosine.

### OpenSearch

- Dense `knn` query (`vector`, `k`, Query DSL `filter`), `neural`
  (`query_text` + `model_id`), `neural_sparse` for learned sparse.
- Fusion: `hybrid` compound query with `queries[]` (≤ 5), one top-level
  `filter` (wrap several in `bool`), `pagination_depth` (required when
  `from > 0`), scored by a search pipeline named in the `search_pipeline`
  query parameter. `normalization-processor`: `normalization.technique
  min_max (default)|l2|z_score`, `normalization.parameters.lower_bounds[]
  {mode apply|clip|ignore, min_score}`, `combination.technique
  arithmetic_mean (default)|geometric_mean|harmonic_mean` (`z_score`
  supports only arithmetic), `combination.parameters.weights` summing to
  1.0. `score-ranker-processor`: `combination.technique: "rrf"` (only
  value), `rank_constant` 1..10000 default 60, `parameters.weights`.
  `post_filter` removes after scoring. Amazon OpenSearch Serverless exposes
  the same `knn` query (NextGen: 32x compression default, 5 s
  read-after-write).

### Typesense

- Lexical `q` + `query_by` (field order is rank order), `query_by_weights`,
  typo tolerance, prefix on by default. `filter_by`: `:=` exact, `:` word
  match, `:!=`, `:>` `:>=` `:<` `:<=`, `:[a, b]` any-of, `[min..max]`,
  `&&`, `||`, parentheses, nested `field.{...}`, prefix `name:=S*`:
  `genre:=drama && year:>=2020 && tag:[a,b] && archived:!=true`.
- Dense `float[]` with `num_dim`, `hnsw_params {ef_construction 200, M
  16}`, cosine default (inner product supported; `vec_dist` name
  unverified); `vector_query: "embedding:([...], k:100, distance_threshold:,
  ef:10, flat_search_cutoff:, alpha:, id:)"`; auto-embedding via
  `embed.from` + `model_config` (built-in `ts/e5-small`, OpenAI, Azure,
  Google, GCP, custom ONNX).
- Fusion: list text fields and the embedding field in `query_by`;
  `rank_fusion_score = 0.7 * K + 0.3 * S` over keyword rank and semantic
  rank, `alpha` (default 0.3) reweights, `rerank_hybrid_matches: true`
  scores every hit both ways. Hits carry `text_match` and `vector_distance`
  (cosine 0..2, ascending). Max 250 hits per page.

### Meilisearch

- `q`, `_rankingScore` 0..1 via `showRankingScore`, `rankingScoreThreshold`,
  `limit` default 20 capped by `pagination.maxTotalHits` (1000); auth
  `Authorization: Bearer`.
- `filter` over `filterableAttributes`: `=`, `!=`, `>`, `>=`, `<`, `<=`,
  `TO`, `EXISTS`, `IS EMPTY`, `IS NULL`, `IN`, `NOT IN`, `CONTAINS`
  (experimental), `STARTS WITH`, `NOT`, `AND`, `OR`, dot-notation nesting;
  array fields match on any element: `genre = drama AND year >= 2020 AND
  tag IN [a, b] AND NOT archived = true` (`NOT` also matches documents
  missing the field).
- Dense via index embedders or a raw `vector`; `retrieveVectors`. Fusion
  `hybrid: {embedder, semanticRatio}` (0.0 keyword-only .. 1.0
  semantic-only, default 0.5); `semanticHitCount` in the response.
  Federated search lives on `/multi-search`.

### Vespa

- Filters and retrieval are both YQL: `select * from sources * where genre
  contains "drama" and year >= 2020 and tag in ("a","b") and !(archived =
  true)`; operators `contains`, `matches` (regex), `=` `<` `>` `<=` `>=`,
  `range()`, `in`, `and`/`or`/`!`, `sameElement`, `phrase`, `near`,
  `weightedSet`, `wand`, `weakAnd`, `userQuery()`, `geoLocation`,
  `predicate`.
- Dense: tensor field with `index { hnsw { max-links-per-node,
  neighbors-to-explore-at-insert } }`, `attribute { distance-metric
  euclidean|angular|dotproduct|prenormalized-angular|hamming|geodegrees }`;
  `{targetHits: N, approximate: false, hnsw.exploreAdditionalHits: M}
  nearestNeighbor(field, query_tensor)` (`targetHits` required; query tensor
  declared in `inputs { query(q) tensor<float>(d[384]) }`).
- Fusion is the rank profile: `first-phase { expression { bm25(title) +
  ... } }`, `second-phase { ... rerank-count }`, `global-phase { expression
  { reciprocal_rank_fusion(a, b) } rerank-count: N }` with
  `normalize_linear(x)` and `reciprocal_rank(x, k=60)`; `closeness(field,
  name) = 1/(1+distance)` in 0..1. Pre-filtering by default with
  `approximate-threshold` / `post-filter-threshold`; `geoLocation` and
  `predicate` always post-filter.

### Tantivy and Lucene (in-process)

- Tantivy (Rust): `Schema::builder()` + `add_text_field(name, TEXT |
  STORED)`, `Index::create_in_dir`, `index.writer(heap)`, `add_document`,
  `commit`, `reader().searcher().search(&query, &TopDocs::with_limit(n))`
  → `(Score, DocAddress)`, `QueryParser::for_index(&index, fields)`; BM25
  scoring (not stated on the crate root; unverified). Python `tantivy`:
  `SchemaBuilder().add_text_field/add_integer_field().build()`, `Index(
  schema, path)`, `index.writer(heap_size, num_threads)`, `Document`,
  `index.parse_query(q, fields)`, `searcher.search(query, n).hits` as
  `(score, DocAddress)`, `searcher.doc(addr)`, `index.reload()`. Filters are
  query clauses (term, range); `Occur`, `delete_documents` and the `Query.*`
  constructors are in the reference but were not on the page read.
- Lucene is the JVM reference of the same model; both are the lexical local
  peers exactly as FAISS/hnswlib/usearch are for dense.

### PostgreSQL full-text and ParadeDB

- `to_tsvector([config,] text)`, `to_tsquery`, `plainto_tsquery`,
  `phraseto_tsquery`, `websearch_to_tsquery` (never raises; `"quoted"`,
  `OR`, `-`), match `tsvector @@ tsquery`, `ts_rank([weights,] vector,
  query [, normalization])` and `ts_rank_cd`, weights A–D via `setweight`,
  `ts_headline`, `CREATE INDEX ... USING GIN (col)` preferred over GiST.
  Hybrid with pgvector is a join of two ranked CTEs with RRF arithmetic;
  the filter is both queries' `WHERE`.
- ParadeDB `pg_search`: `CREATE INDEX ... USING bm25 (id, description) WITH
  (key_field = 'id')`, `WHERE description @@@ 'running shoes'`,
  `paradedb.score(id)`; official docs unreachable from our fetcher today,
  query builders and the reported `USING paradedb` rename unverified. Neon
  deprecated `pg_search` for `lakebase_text` (removal September 2026).

## How the vector stores fuse

| Store | Lexical lane | Fusion | Parameter home |
|---|---|---|---|
| Azure AI Search | `search` (BM25) alongside `vectorQueries[]` | RRF always; `hybridSearch.maxTextRecallSize` (1000, max 10000) and `countAndFacetMode` (preview); optional `queryType: semantic` reranker over the top 50; per-vector `weight` | request body |
| Elasticsearch | `standard` retriever | `rrf` / `linear` retrievers | `retriever` tree |
| OpenSearch | any Query DSL clause | `normalization-processor` / `score-ranker-processor` | search pipeline |
| Vertex Vector Search | `sparse_embedding {values, dimensions}` | RRF with `rrf_ranking_alpha` (1 dense-only, 0 sparse-only) | query |
| S3 Vectors | none | none | n/a |
| Pinecone (Documents API 2026-07) | `score_by.type: text` (BM25 over `full_text_search` fields) or `query_string` (Lucene syntax); `sparse_vector` / `sparse_embed` | none server-side ("Every search ranks by one scoring type"); text clauses act as filters on a dense search, or two searches merged client-side with RRF; no `alpha` | client |
| Weaviate | BM25F `bm25 {query, properties, searchOperator}` | `hybrid {query, alpha, fusionType: relativeScoreFusion (default since v1.24) or rankedFusion, targetVectors, maxVectorDistance}`; `alpha` 1 = pure vector, 0 = pure keyword | query |
| Qdrant | `text` payload index with `scoring: {type: "bm25"}`; sparse named vectors with `modifier: "idf"` | `prefetch[]` + top-level `query: {fusion: "rrf" or "dbsf"}` or `{rrf: {k, weights}}`; nested prefetch for multi-stage rescoring | query |
| Milvus / Zilliz | BM25 `Function` filling a `SPARSE_FLOAT_VECTOR` (`metric_type: "BM25"`); `TEXT_MATCH` / `PHRASE_MATCH` filters | `hybrid_search` with `rerank: {strategy: "rrf" or "weighted", params: {k (default 60) or weights}}` | query |
| Chroma | legacy `where_document` `$contains` / `$regex` are filters, not scored; Cloud `SparseVectorIndexConfig(bm25=True)` | Cloud Search API `Rrf(ranks=[Knn(return_rank=True), ...], k=60, weights, normalize)` or score arithmetic over `Knn` terms; scores are negated RRF (lower is better) | query `rank` expression |
| pgvector | `tsvector @@ tsquery` + `ts_rank_cd` | RRF or weighted sum as SQL over two ranked CTEs | your SQL |
| Turbopuffer | `rank_by: ["content", "BM25", q]`, multi-field `Sum` / `Max` / `Product` | `queries[]` (≤ 16) with `rerank_by: ["RRF"]` (k not documented) or model rerank; `compute_attributes` for client-side fusion | query |
| LanceDB | FTS index (BM25, `_score`) with `MatchQuery`, `PhraseQuery`, `BooleanQuery` | client-side `.rerank(RRFReranker())` default, `_relevance_score`; "Reranking runs in the application for both Embedded and Enterprise" | SDK |
| MongoDB Atlas | `$search` (Lucene) sibling pipeline | `$rankFusion {input.pipelines, combination.weights}` (RRF, k fixed 60; 8.0+); `$scoreFusion {input.normalization none, sigmoid or minMaxScaler; combination.method avg or expression}` (8.3+) | aggregation stage |
| Redis | `FT.SEARCH` BM25 (`SCORER BM25STD`) | `FT.HYBRID ... COMBINE RRF [CONSTANT 60] [WINDOW 20]` or `LINEAR [ALPHA] [BETA]` (8.4+); RedisVL `HybridQuery(combination_method=RRF or LINEAR, linear_alpha=0.3)` | command |

## Fusion methods compared

| Method | Formula | Engines | Score semantics |
|---|---|---|---|
| Reciprocal rank fusion | `sum_i w_i / (k + rank_i)`, `k` default 60 | Elasticsearch `rrf`, OpenSearch `score-ranker-processor`, Azure, Vespa `reciprocal_rank_fusion`, Qdrant `rrf`, Milvus `rrf`, Atlas `$rankFusion`, Redis `COMBINE RRF`, Chroma `Rrf`, Turbopuffer, LanceDB, Vertex (with alpha) | rank-only; raw scores discarded; tiny magnitudes |
| Normalized weighted sum | min-max / L2 / z-score per lane, then `sum_i w_i * s_i` | Elasticsearch `linear`, OpenSearch `normalization-processor`, Vespa `normalize_linear`, Milvus `weighted` (arctan), Atlas `$scoreFusion`, Redis `LINEAR`, Qdrant `dbsf`, Weaviate `relativeScoreFusion` | depends on the candidate window; not stable across queries |
| Alpha / ratio blend | one knob trading lexical vs semantic | Typesense `alpha` (rank-based, 0.3), Meilisearch `semanticRatio` (0.5), Weaviate `alpha`, Vertex `rrf_ranking_alpha` | engine-defined; same name, different math |
| Rank profile expression | arbitrary arithmetic over features | Vespa phases, Chroma rank arithmetic | user-defined |
| Server-side rerank | cross-encoder over the fused window | Elasticsearch `text_similarity_reranker`, Azure semantic ranker, Vespa global-phase models, Turbopuffer model `rerank_by`, Pinecone/Cohere/Voyage rerank endpoints | a new scale again |

Three facts drive the design: `alpha` means different math in different
engines; RRF discards scores, so a fused result has no distance to report;
and the fusion knob lives in a different place per engine (request body,
pipeline resource, deployed schema, SDK).

## Proposal: one `search` request shape

Add a third read operation beside `get` and `query`, shapes
`("vectorstore", "search.request")` / `("vectorstore", "search.response")`:

```python
@dataclass
class SearchRequest(IRObject):
    lanes: list[Lane]              # at least one
    fusion: Fusion | None = None   # None: single lane, or engine default
    filters: Filter | None = None  # canonical AST, vector-stores page
    limit: int = 10
    namespace: str | None = None
    rerank: RerankSpec | None = None   # maps to server-side rerank
```

- `Lane` is a tagged union through `TagRegistry` with an Unknown fallback:
  `DenseLane(vector, field=None)`, `SparseLane(indices, values, field=None)`,
  `TextLane(text, fields=None, mode="match|phrase|prefix")`,
  `ServerEmbedLane(text, model=None)` for engines that embed at query time
  (Typesense `embed`, OpenSearch `neural`, Elasticsearch
  `query_vector_builder`, Weaviate vectorizers). Each lane may carry
  `weight`.
- `Fusion` is an open-code record: `method rrf|normalized_sum|ratio|engine`
  with `k`, `normalizer`, `ratio`, `weights`. An edge that cannot honour the
  requested method never substitutes silently: it is `UNSUPPORTED`-and-
  reported at the feature gate (strict) or recorded as
  `SemanticShift(kind="fusion_substituted")` with the engine's method in
  `native` (annotate). `fusion=None` on a multi-lane request means the
  engine default, and the edge declares which default that is as a
  `SemanticShift`, so the report is never silent.
- Scores: `QueryResult.score` stays higher-is-better; the response gains
  `score_kind` (`similarity|distance|rrf|normalized|bm25|engine`) and
  `native_score` verbatim. Distance-to-similarity conversion is an
  `APPROXIMATED` field loss with the formula in the note, never a silent
  rescale.
- Per-lane filters (Azure `filterOverride`, Vespa per-clause YQL) are a P2
  extension; v1 applies one filter to all lanes, and an engine that can only
  post-filter declares `SemanticShift(kind="post_filter")`.
- `query(vector, filters, limit)` remains the sugar for a single
  `DenseLane`; the local adapter implements `search` by composing
  FAISS/usearch with tantivy and an in-process RRF — the H3 in-process peer
  with hybrid on top.
- Usage: per-query or per-unit billing reports `Consumption(unit=
  "search_units"|"read_units"|"requests")`; token-billed server embedding
  lanes report `tokens` with `source="input"`.

## Priority

P0: Elasticsearch/OpenSearch (one codec family covers Elastic Cloud, AWS
managed and Serverless) and the in-process tantivy + FAISS peer. P1: Azure
AI Search (enterprise; RRF + semantic ranker), Typesense and Meilisearch
(popular, clean filter grammars). P2: Vespa (rank profiles need a
schema-aware codec), Postgres FTS/ParadeDB (SQL printer shared with
pgvector).

## Sources

All read 2026-11-10.

- Elasticsearch: https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers, https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers/rrf-retriever, https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers/linear-retriever, https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers/knn-retriever
- OpenSearch: https://docs.opensearch.org/latest/query-dsl/compound/hybrid/, https://docs.opensearch.org/latest/search-plugins/search-pipelines/normalization-processor/, https://docs.opensearch.org/latest/search-plugins/search-pipelines/score-ranker-processor/, https://docs.opensearch.org/latest/vector-search/ai-search/hybrid-search/index/, https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-vector-search.html
- Typesense: https://typesense.org/docs/latest/api/search.html, https://typesense.org/docs/latest/api/vector-search.html
- Meilisearch: https://www.meilisearch.com/docs/learn/filtering_and_sorting/filter_expression_reference, https://www.meilisearch.com/docs/reference/api/search
- Vespa: https://docs.vespa.ai/en/querying/nearest-neighbor-search.html, https://docs.vespa.ai/en/querying/approximate-nn-hnsw.html, https://docs.vespa.ai/en/ranking/phased-ranking.html, https://docs.vespa.ai/en/reference/query-language-reference.html
- Tantivy: https://docs.rs/tantivy/latest/tantivy/, https://tantivy-py.readthedocs.io/en/latest/reference.html
- PostgreSQL / ParadeDB: https://www.postgresql.org/docs/current/textsearch-controls.html, https://www.postgresql.org/docs/current/textsearch-indexes.html, https://neon.com/docs/extensions/pg_search (ParadeDB syntax; official ParadeDB docs unreachable today)
- Store fusion rows: https://learn.microsoft.com/en-us/azure/search/hybrid-search-how-to-query, https://docs.cloud.google.com/vertex-ai/docs/vector-search/about-hybrid-search, https://docs.pinecone.io/guides/search/hybrid-search, https://docs.weaviate.io/weaviate/search/hybrid, https://qdrant.tech/documentation/concepts/hybrid-queries/, https://milvus.io/docs/multi-vector-search.md, https://docs.trychroma.com/cloud/search-api/hybrid-search, https://turbopuffer.com/docs/hybrid, https://docs.lancedb.com/search/hybrid-search, https://www.mongodb.com/docs/manual/reference/operator/aggregation/rankFusion/, https://redis.io/docs/latest/commands/ft.hybrid/
