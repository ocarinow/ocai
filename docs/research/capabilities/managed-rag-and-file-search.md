# Managed RAG and file search

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

Currency: researched against official documentation on 2026-11-10. Provider
retrieval surfaces change monthly; field names below were read from the pages
listed under Sources on that date, and anything we could not confirm is marked
unverified. Prices are list prices as published on that date.

Status: research page, no WU attached. It informs the "files" capability in
[horizon H6](../../plans/horizon.md) and the decision below on what the platform
does with provider-side retrieval.

## What this page covers

Every major model provider and a crop of RAG-as-a-service vendors now sell
*provider-side retrieval*: you upload documents, they chunk, embed, index and
(usually) cite. These appear in two shapes:

1. **A server tool inside the chat call.** Retrieval happens during
   generation; the response carries a tool-call record and span-anchored
   citations. OpenAI `file_search`, Gemini `file_search`, Vertex RAG Engine as
   a `retrieval` tool, Bedrock `RetrieveAndGenerate`, Cohere `documents` with
   citations, Pinecone Assistant chat.
2. **A standalone retrieve endpoint.** Returns scored chunks and leaves
   generation to you. OpenAI `POST /vector_stores/{id}/search`, Bedrock
   `Retrieve`, Vertex `retrieveContexts`, Vectara `query`, Ragie
   `POST /retrievals`, Pinecone Assistant `context`.

ocai's chat IR already types shape 1 (`PartServerToolCall` with an open
`kind`, byte-faithful `payload`, plus span-anchored `Annotation` on
`PartText`, architecture §3). Shape 2 is a retrieval capability with a
provider-varying wire dialect, so by the §11 litmus test it is a capability,
not a platform concern. This page catalogs both and proposes where each lands.

## Per-provider survey

### OpenAI vector stores and `file_search`

- Resources: `POST /v1/vector_stores` (`name`, `file_ids` up to 500,
  `chunking_strategy` as `{type: "auto"}` or
  `{type: "static", static: {max_chunk_size_tokens, chunk_overlap_tokens}}`
  with defaults 800 / 400, range 100–4096, overlap at most half;
  `expires_after: {anchor: "last_active_at", days}` 1–365; `metadata` up to
  16 pairs). Vector store object: `id`, `status` in
  `expired | in_progress | completed`, `file_counts`, `usage_bytes`,
  `expires_at`, `last_active_at`.
- Files carry `attributes`: up to 16 key-value pairs, keys at most 64 chars
  (OpenAPI schema) or 256 chars (retrieval guide; the two pages disagree).
- Standalone search: `POST /v1/vector_stores/{id}/search` with `query`
  (string or array), `filters`, `max_num_results` 1–50 default 10,
  `ranking_options: {ranker: none|auto|default-2024-11-15, score_threshold
  0..1}`, `rewrite_query`. Response `object:
  "vector_store.search_results.page"`, `search_query[]`, `data[]` with
  `file_id`, `filename`, `score` 0..1, `attributes`, `content[] {type:
  "text", text}`, `has_more`, `next_page`.
- Filter dialect: comparison `{type: eq|ne|gt|gte|lt|lte|in|nin, key,
  value}` and compound `{type: and|or, filters[]}`. The live API reference
  lists `in`/`nin`; an OpenAPI snapshot we checked lists only `eq..lte`, so
  treat `in`/`nin` as newer. The retrieval guide also documents
  `hybrid_search` weights `embedding_weight` / `text_weight` (unverified
  whether that is on the search endpoint, the tool, or both).
- As a chat tool (Responses API): `{type: "file_search", vector_store_ids,
  max_num_results, ranking_options, filters}`. Output item
  `file_search_call` with `id`, `status` in `in_progress | searching |
  completed | incomplete | failed`, `queries[]`, and `results[]` only when
  the request passes `include: ["file_search_call.results"]`. Citations are
  `annotations[]` of type `file_citation` with `file_id`, `filename`,
  `index` on the output text.
- Limits and pricing: 512 MB and 5,000,000 tokens per file; storage
  $0.10/GB/day after 1 GB free. The per-call tool price ($2.50 per 1k calls
  in earlier pricing) was not on the pages read: unverified today.
- Chat Completions has no `file_search`; the Assistants API that carried it
  is deprecated (sunset August 2026, per the OpenAI provider page in this
  repo).

### Gemini File Search and context caching

- Stores: `file_search_stores.create` (config `display_name`,
  `embedding_model`, e.g. `models/gemini-embedding-2`),
  `upload_to_file_search_store`, `import_file` (file first uploaded through
  the Files API), both asynchronous operations polled through
  `operations.get`. Documents live under
  `fileSearchStores/{store}/documents/{doc}`.
- Chunking: `chunking_config.white_space_config` with `max_tokens_per_chunk`
  and `max_overlap_tokens`.
- Metadata: `custom_metadata[]` entries `{key, string_value | numeric_value}`;
  query-time `metadata_filter` is a string in AIP-160 filter syntax
  (`author="Robert Graves"`), not a JSON tree.
- Tool: a tools entry with `type: "file_search"`,
  `file_search_store_names[]`, optional `metadata_filter`. The current docs
  show it on the Interactions API (`client.interactions.create`), and
  citations come back as `annotations` of type `file_citation` on text
  content blocks with `file_name`, `source`, `document_uri`, `page_number`,
  `media_id`, `custom_metadata`. The older `generateContent` path returned
  `grounding_metadata` with `grounding_chunks` / `grounding_supports`;
  whether that still applies to file search is unverified today.
- Limits: 100 MB per document; store size tiers Free 1 GB, Tier 1 10 GB,
  Tier 2 100 GB, Tier 3 1 TB; raw File objects deleted after 48 hours,
  embeddings have no TTL. Not available in the Live API; cannot be combined
  with Google Search grounding or URL context.
- Pricing: indexing charged at embeddings pricing; storage and query-time
  embeddings free; retrieved tokens billed as ordinary context tokens.
- Context caching: implicit caching is on by default for Gemini 2.5 and
  newer, with per-model minimums (4,096 tokens for Gemini 3.x/4 models,
  2,048 for 2.5), and cache hits reported in `usage.total_cached_tokens`.
  Explicit `cachedContents` are not supported on the Interactions API nor
  on Gemini 4 models; they remain on `generateContent` for Gemini 3 and 2.5
  (TTL default and per-hour storage price unverified today).

### Anthropic Files API and citations

- Files API is out of beta: `POST /v1/files` (multipart), `GET /v1/files`,
  `GET /v1/files/{id}`, `DELETE /v1/files/{id}`, `GET /v1/files/{id}/content`
  (downloads only for files produced by skills or code execution). The
  `anthropic-beta: files-api-2025-04-14` header is optional and keeps the
  legacy list shape. File object: `id`, `type: "file"`, `filename`,
  `mime_type`, `size_bytes`, `created_at`, `downloadable`, `expires_at`.
  Upload-time `expires_in_seconds` 3,600–7,776,000. Limits 500 MB per file,
  1 TB per organization. Files are workspace-scoped, not user-scoped.
- Messages reference a file with `source: {type: "file", file_id}` inside
  `document`, `image` or `container_upload` blocks.
- Citations: a `document` block (`source` of type `text`, `base64`,
  `content` or `file`; `title`; `context`; `citations: {enabled: true}`)
  makes the response's text blocks carry `citations[]`. Types:
  `char_location` (`cited_text`, `document_index`, `document_title`,
  `start_char_index`, `end_char_index` exclusive), `page_location`
  (`start_page_number`, `end_page_number`), `content_block_location`
  (`start_block_index`, `end_block_index`), and `search_result_location`
  for the `search_result` input block. `cited_text` does not count toward
  output tokens, nor toward input tokens when replayed. Streaming delivers
  `citations_delta` events.
- Anthropic has no hosted vector store or file-search tool: the
  `search_result` block exists precisely so *your* retriever's results can
  be cited natively. The memory tool (`memory_20250818`) is client-side
  file storage, not retrieval (see the ingestion/memory page).

### Amazon Bedrock Knowledge Bases

- `POST /knowledgebases/{knowledgeBaseId}/retrieve` with
  `retrievalQuery.text`, `retrievalConfiguration.vectorSearchConfiguration
  {numberOfResults, overrideSearchType, filter, rerankingConfiguration,
  implicitFilterConfiguration}` (and a newer `managedSearchConfiguration`
  sibling), `nextToken`, `guardrailConfiguration`, `userContext.userId` for
  access-control trimming. Response `retrievalResults[] {content {text,
  type, byteContent, row[], audio, video}, documentId, location {type,
  s3Location.uri, webLocation.url, confluenceLocation, sharePointLocation,
  salesforceLocation, sqlLocation.query, kendraDocumentLocation,
  customDocumentLocation, ...}, metadata, score}`.
- Filter dialect: `equals`, `notEquals`, `greaterThan`,
  `greaterThanOrEquals`, `lessThan`, `lessThanOrEquals`, `in`, `notIn`,
  `startsWith`, `stringContains`, `listContains`, `andAll`, `orAll`, each
  `{key, value}`; metadata comes from a sidecar `<file>.metadata.json`.
- `POST /retrieveAndGenerate` with `input.text`,
  `retrieveAndGenerateConfiguration {type: KNOWLEDGE_BASE |
  EXTERNAL_SOURCES, knowledgeBaseConfiguration {knowledgeBaseId, modelArn,
  retrievalConfiguration, generationConfiguration {promptTemplate,
  inferenceConfig, guardrailConfiguration}, orchestrationConfiguration}}`,
  server-assigned `sessionId`. Response `output.text`, `citations[]
  {generatedResponsePart.textResponsePart {text, span {start, end}},
  retrievedReferences[] {content, location, metadata}}`, `guardrailAction`.
  Not usable with "managed knowledge bases" (use `Retrieve` or
  `AgenticRetrieveStream`).
- Errors: `ThrottlingException` 429, `ValidationException` 400,
  `ResourceNotFoundException` 404, `DependencyFailedException` 424,
  `BadGatewayException` 502. Auth: SigV4. Chunking strategies
  (FIXED_SIZE, HIERARCHICAL, SEMANTIC, NONE, custom Lambda), backing
  stores and pricing: not re-verified today, unverified.

### Azure AI Search as RAG backend

- Azure OpenAI "On Your Data" (`data_sources[] {type: "azure_search",
  parameters {endpoint, index_name, authentication, query_type: simple |
  semantic | vector | vector_simple_hybrid | vector_semantic_hybrid,
  semantic_configuration, embedding_dependency, fields_mapping
  {content_fields, vector_fields, title_field, url_field, filepath_field},
  filter, top_n_documents, strictness, in_scope, role_information,
  include_contexts}}`) **retired on 2026-10-14**. Microsoft's replacement is
  Foundry IQ knowledge bases (agentic retrieval, `2026-04-01` GA for
  extractive retrieval), with application-managed answer generation.
- Azure AI Search itself remains a first-class vector/hybrid store; see the
  vector-stores page for its query surface. Pricing: search-unit tiers,
  semantic ranker billed per 1,000 queries (figure not re-verified).

### Google Vertex AI RAG Engine

- Current SDK (`agentplatform`): `client.rag.create_corpus(rag_corpus=
  types.RagCorpus(display_name, rag_vector_db_config=
  types.RagVectorDbConfig(rag_embedding_model_config=...)))`,
  `client.rag.import_files(name, import_config=types.ImportRagFilesConfig(
  ... RagFileTransformationConfig(RagFileChunkingConfig(chunk_size=512,
  chunk_overlap=100)), max_embedding_requests_per_min))`,
  `client.rag.retrieve_contexts(vertex_rag_store, query=types.RagQuery(
  text, rag_retrieval_config=RagRetrievalConfig(top_k,
  filter=RagRetrievalConfigFilter(vector_distance_threshold))))`.
- As a tool: `Tool(retrieval=Retrieval(vertex_rag_store=...))` on
  `generate_content`. Backing store defaults to `RagManagedDb` (a
  RAG-Engine-managed Spanner instance, billed as Spanner); other backends
  and the response context schema (`contexts[].source_uri/text/score`) are
  unverified today. Regions `us-central1`, `us-east1`, `us-east4`,
  `europe-west1` are allowlist-only for new projects. VPC-SC and CMEK
  supported; data residency not.

### Cohere Chat v2 with documents

- `documents[]` of strings or `{id, data: {...}}`;
  `citation_options.mode` in `FAST | ACCURATE | OFF` (docs also list
  `ENABLED`/`DISABLED`; the enum is inconsistent across the page).
- Response `message.citations[] {start, end, text, sources[] {type:
  document | tool, id, document | tool_output}, content_index, type:
  TEXT_CONTENT | THINKING_CONTENT | PLAN}`. Streaming emits citation
  events (`citation-start` / `citation-end` not re-verified). Connectors
  are a v1 concept; not present in v2.

### Pinecone Assistant

- Host `https://prod-1-data.ke.pinecone.io`, header
  `X-Pinecone-Api-Version: 2026-07`. Chat: `POST
  /assistant/chat/{assistant_name}` with `messages[] {role, content}`,
  `stream`, `model` (`gpt-4o` default; also `gpt-4.1`, `gpt-5`,
  `claude-sonnet-4-5`, `gemini-3.5-flash`), `filter` (Pinecone metadata
  filter object), `json_response`, `include_highlights`,
  `context_options {top_k up to 64 default 16, snippet_size 512–8192
  default 2048}`, `temperature`. Response `id`, `finish_reason`, `message
  {role, content}`, `model`, `usage {prompt_tokens, completion_tokens,
  total_tokens}`, `citations[] {position, references[] {file {id, name,
  metadata, status, created_on, updated_on, size, signed_url, multimodal},
  pages[], highlight {type, content}}}`, `context_snippet_count`.
- Retrieval only: `POST /assistant/chat/{assistant_name}/context` with
  `query`, `top_k`, `snippet_size`; response `snippets[] {type, content,
  score, reference {type, file {...}, pages[]}}`. `signed_url` expires in
  one hour.
- Pricing: ingestion $0.0005 per unit (about 400 tokens); chat $8 / $15 per
  million input / output tokens; context retrieval $5 per million tokens;
  storage $3/GB/month; plan minimums $0 / $20 / $50 / $500. Limits: 10 MB
  text files, PDFs 10–100 MB by plan, 16 KB metadata per file.

### Vectara

- `POST /v2/corpora/{corpus_key}/query` with `search.corpora[] {corpus_key,
  metadata_filter, lexical_interpolation (0.025 recommended),
  custom_dimensions}`, `search.limit` default 10, `search.offset`,
  `search.context_configuration {sentences_before/after or
  characters_before/after, start_tag, end_tag}`, `search.reranker {type:
  customer_reranker | mmr | none, reranker_name, limit, cutoff,
  include_context}`, `generation {generation_preset_name, prompt_template,
  max_used_search_results default 5, response_language, citations {style:
  markdown | html | none, url_pattern, text_pattern}, model_parameters,
  enable_factual_consistency_score}`. Status codes 200/400/403/404/429.
- Filter dialect: SQL-like over `doc.*` and `part.*` scopes with `=`, `==`,
  `!=`, `<>`, `<`, `<=`, `>`, `>=`, `IS NULL`, `IN`, `NOT`, `AND`, `OR`,
  arithmetic; e.g. `doc.genre = 'drama' AND doc.year >= 2020`. Fields must
  be declared filter attributes on the corpus. `LIKE`/`BETWEEN` unverified.
- Response field names and the `x-api-key` header were not on the page
  read: unverified.

### Ragie

- `POST /retrievals` with `query`, `top_k`, `filter` (MongoDB-style; `$in`
  confirmed in the OpenAPI example, `$eq` and the rest unverified),
  `rerank` boolean, `max_chunks_per_document`; response `scored_chunks[]
  {text, score, document_id, document_name, metadata, links}`. Docs site
  refused TLS from our fetcher, so the remaining fields are unverified.

### Graphlit

- GraphQL API with client SDKs; `ingestUri`, `queryContents({search,
  searchType})` with `SearchTypes.Hybrid`, `createConversation` with a
  content filter, `promptConversation` returning `message.message`; feeds
  for 30+ sources. Citation shape, filter schema, pricing and auth are
  unverified.

## Comparison

| Service | Exposed as | Citation shape | Filter dialect | Chunking control | Pricing unit |
|---|---|---|---|---|---|
| OpenAI vector stores | both (tool + `/search`) | `file_citation {file_id, filename, index}` annotation; `file_search_call.results` on include | JSON tree `eq..lte, in, nin, and, or` | `auto` or `static` tokens/overlap | GB/day storage; tool call |
| Gemini File Search | tool (Interactions) | `file_citation` annotation with `document_uri`, `page_number` | AIP-160 string | `white_space_config` tokens/overlap | embedding tokens; storage free |
| Anthropic documents | neither (you retrieve) | `citations[]` typed by location (char/page/block/search_result) | n/a | n/a | input tokens; `cited_text` free |
| Bedrock KB | both | `citations[].generatedResponsePart.span` + `retrievedReferences` | `equals..orAll` JSON | strategy at KB creation | per retrieval + model tokens (unverified) |
| Azure OpenAI On Your Data | tool (retired 2026-10) | `context.citations` | OData string | n/a | search units |
| Vertex RAG Engine | both | tool grounding (schema unverified) | `vector_distance_threshold` only | `chunk_size/overlap` at import | Spanner + embeddings |
| Cohere documents | tool-like (`documents` param) | `citations[] {start, end, sources}` | n/a | n/a | tokens |
| Pinecone Assistant | both | `citations[] {position, references}` / `snippets[]` | Pinecone metadata filter | fixed | tokens + GB/month |
| Vectara | both | numbered citations in `summary` + `search_results` | SQL-like `doc./part.` | fixed | unverified |
| Ragie | retrieve | n/a | MongoDB-style | fixed | unverified |

Observations that matter for the IR:

- Three incompatible citation anchors coexist: character spans into the
  *generated* text (Bedrock `span`, Cohere `start/end`, Anthropic text
  block offsets), character/page/block spans into the *source* document
  (Anthropic `char_location`, `page_location`), and index-only pointers
  (OpenAI `index`, Gemini `page_number`). `Annotation.span` already carries
  the first kind; the second kind needs a source-side locator; the third
  is metadata on `file`.
- Every tool-shaped service reports its retrieval as a distinct output
  item with a lifecycle (`file_search_call.status`, Gemini operation
  steps, Bedrock `retrievedReferences`), which is exactly
  `PartServerToolCall(kind, call_id, status, payload)`.
- Filter dialects fork four ways (JSON tree, AIP-160 string, OData string,
  SQL-like string). The canonical filter AST on the vector-stores page is
  the only honest meeting point; string dialects need a printer, tree
  dialects a mapper.

## Canonical proposal

1. **Server-tool retrieval stays in chat.** OpenAI `file_search`, Gemini
   `file_search`, Vertex `retrieval`, Pinecone Assistant chat, Cohere
   `documents` map to `PartServerToolCall(kind="file_search", ...)` with the
   provider payload verbatim, and citations to `Annotation` on `PartText`.
   Additive changes needed on `Annotation`: a source-side locator
   (`source_span` with a unit code `chars | pages | blocks`, mirroring
   Anthropic's `char_location`/`page_location`/`content_block_location`)
   and `score`. Both are optional fields; omit-absent `to_dict` keeps
   existing fixtures valid. Gemini's `document_uri`/`page_number` ride the
   existing `file` ref plus `source_span(unit="pages")`. Anything that
   cannot be re-anchored against decoded text rides a censused extension,
   per the §3 rule that a possibly misattributed span is never emitted.
2. **Vector store and file resources are separate capabilities with
   `ProviderRef` handles.** An OpenAI vector store id, a Gemini file search
   store name, a Bedrock knowledge base id and a Pinecone assistant name
   are provider-scoped refs (`RefScope.PROVIDER`, `kind="vector_store"` /
   `"knowledge_base"`); file ids are the H6 "files" refs. They cross
   `chat_completions`/`responses` unreported and are `UNSUPPORTED`-and-
   reported across providers. The tool config in a chat request carries
   them as refs, so a request that pins an OpenAI vector store and is
   routed to Anthropic fails honestly at the feature gate, not silently.
3. **Standalone retrieve endpoints are the `search` operation of the
   vectorstore capability** (Shape `("vectorstore","search.request")`,
   defined on the hybrid-and-fulltext page): OpenAI `/vector_stores/{id}/
   search`, Bedrock `Retrieve`, Vertex `retrieveContexts`, Vectara `query`
   without `generation`, Ragie `/retrievals`, Pinecone `context`. Their
   results are `QueryResult`s whose `record.content` is the chunk text and
   whose metadata carries `file`/`location`; `score` semantics are declared
   per edge (`SemanticShift`) because OpenAI's 0..1 ranker score, Bedrock's
   `score` and Vectara's `score` are not on one scale.
4. **"Retrieve and generate" bundles are facades, not edges.** Bedrock
   `RetrieveAndGenerate` and Vectara `generation` are one wire call that
   returns both retrieval and a completion; modelling them as a chat edge
   with `kind="knowledge_base"` server tool is honest (one call, one
   `CallResult`), and the platform can instead compose
   `search` + `chat` itself when it wants its own prompt and reranker.
5. **What the platform should do.** Use provider retrieval honestly when
   the data already lives there and the fidelity report says the citation
   mapping is EXACT; bypass it (own chunking, own embeddings, own
   vectorstore port, cite through Anthropic `search_result` or the
   `PartText` annotation lane) when portability across providers matters,
   because provider-side stores are the strongest lock-in surface in this
   survey: none of them export their chunk index. The kernel contributes
   the port, the refs and the report; the choice is a policy hook
   (`Decision`) the platform owns.

Priority: P0 OpenAI `file_search` + vector store search (largest installed
base, cleanest JSON filter, needed for the `/responses` migration proof);
P1 Anthropic citations + Files (no store to model, pure annotation
mapping, exercises `search_result`); P1 Bedrock `Retrieve` (enterprise
demand; filter dialect maps cleanly); P2 Gemini File Search (API still
moving between `generateContent` and Interactions); P2 Vertex RAG Engine,
Pinecone Assistant, Vectara; P3 Ragie, Graphlit, Azure On Your Data
(retired).

## Sources

All read 2026-11-10.

- https://developers.openai.com/api/docs/guides/tools-file-search
- https://developers.openai.com/api/docs/guides/retrieval
- https://developers.openai.com/api/docs/api-reference/vector-stores/create
- https://developers.openai.com/api/docs/api-reference/vector-stores/search
- https://aistudio.google.com/docs/file-search
- https://aistudio.google.com/docs/caching
- https://platform.claude.com/docs/en/build-with-claude/citations
- https://platform.claude.com/docs/en/build-with-claude/files
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_Retrieve.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_RetrieveAndGenerate.html
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/references/azure-search
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/rag-overview
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/rag-quickstart
- https://docs.cohere.com/reference/chat
- https://docs.pinecone.io/guides/assistant/overview
- https://docs.pinecone.io/guides/assistant/chat-with-assistant
- https://docs.pinecone.io/guides/assistant/retrieve-context-snippets
- https://docs.pinecone.io/guides/assistant/pricing-and-limits
- https://docs.vectara.com/docs/rest-api/query-corpus
- https://docs.vectara.com/docs/learn/metadata-search-filtering/filter-overview
- https://docs.ragie.ai/docs/retrievals-guide (TLS failure; OpenAPI example via search snippet)
- https://docs.graphlit.dev/
