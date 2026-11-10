# Ingestion, chunking, and memory

Currency: researched against official documentation and repositories on
2026-11-10. Library class names were read from the pages under Sources on that
date; where a page did not show a name we expected, it is marked unverified
rather than assumed. This page argues a scope verdict; it is not a WU.

## Verdict first

Chunking, loaders, contextual retrieval, graph RAG and agent memory are
**platform or satellite concerns built on ocai**, not kernel capabilities.
Architecture §11's litmus test is the whole argument: *a thing with
provider-varying wire dialects is a capability; a thing with no wire dialect
is built on ocai.* A `RecursiveCharacterTextSplitter` has no wire. Microsoft
GraphRAG is an indexing pipeline over an LLM and an embedding model. Mem0,
Zep and Letta do have wires, but each wire is a *product API*, not a dialect
of one shared semantic job: there is no "memory request" that converts
between Mem0 and Zep with a declarable field census, because the two disagree
on what a memory even is (a fact string vs a temporal graph edge). §11 names
"application memory" and "chunking" explicitly as built-on, and nothing found
today moves them.

What the kernel owes these layers is substrate, listed at the end.

## Chunking strategies

| Strategy | Mechanism | Tradeoff | Where it lives |
|---|---|---|---|
| Fixed-size | Split every N tokens or characters, optional overlap | Cheap, deterministic; cuts sentences; overlap duplicates tokens | all libraries |
| Recursive | Try separators in order (`\n\n`, `\n`, space, char) until pieces fit | Respects structure when present; still size-driven | LangChain, Chonkie, LlamaIndex |
| Document-structure | Split on Markdown/HTML headers or code AST | Preserves headings as metadata; chunks vary wildly in size | LangChain header splitters, LlamaIndex Markdown/Code parsers, Docling |
| Sentence window | One sentence per node; neighbours attached as metadata for the LLM | Precise retrieval, wider generation context | LlamaIndex `SentenceWindowNodeParser` |
| Hierarchical / parent-document | Multiple chunk sizes; retrieve small, return parent | Better context, more storage and bookkeeping | LlamaIndex `HierarchicalNodeParser` |
| Semantic | Embed sentences, break where adjacent similarity drops below a threshold | Topic-coherent chunks; one embedding call per sentence | LlamaIndex `SemanticSplitterNodeParser`, Chonkie `SemanticChunker`, LangChain `SemanticChunker` (unverified today) |
| Late chunking | Embed the whole document with a long-context model, then pool token embeddings per chunk | Chunk vectors see document context; requires a model that exposes token embeddings | Chonkie `LateChunker` |
| Contextual (Anthropic) | Prepend an LLM-written situating sentence to each chunk before embedding and BM25 | Large retrieval gains; one LLM pass over the corpus | technique, see below |
| Neural / agentic | A trained boundary model or an LLM picks split points | Best boundaries; slowest and priciest | Chonkie `NeuralChunker`, `SlumberChunker` |

Chunk size is a *retrieval* knob, not an *embedding* one: Anthropic's own
experiments used 800-token chunks and found passing the top 20 chunks beat
top 10 or top 5.

## Chunking libraries

| Library | Classes verified today | Strategies | Tokenizer-aware | Metadata propagation |
|---|---|---|---|---|
| `langchain-text-splitters` | `CharacterTextSplitter` (incl. `.from_tiktoken_encoder`), `RecursiveCharacterTextSplitter(chunk_size, chunk_overlap)`; Markdown-header and recursive-JSON splitters exist by page title, class names unverified; `TokenTextSplitter`, `HTMLHeaderTextSplitter`, `SemanticChunker` unverified today | fixed, recursive, structure, (semantic) | via tiktoken constructor | `Document.metadata` carried through |
| LlamaIndex node parsers | `SentenceSplitter(chunk_size, chunk_overlap)`, `TokenTextSplitter(chunk_size, chunk_overlap, separator)`, `SentenceWindowNodeParser(window_size, window_metadata_key, original_text_metadata_key)`, `SemanticSplitterNodeParser(buffer_size, breakpoint_percentile_threshold, embed_model)`, `HierarchicalNodeParser(chunk_sizes)`, `MarkdownNodeParser`, `HTMLNodeParser(tags)`, `JSONNodeParser`, `CodeSplitter(language, chunk_lines, chunk_lines_overlap, max_chars)`, `LangchainNodeParser`, `SimpleFileNodeParser`, `Chunker` (wraps Chonkie); `SemanticDoubleMergingSplitterNodeParser`, `MarkdownElementNodeParser`, `DoclingNodeParser`, `TopicNodeParser` not on the modules page today | all of the above | tokenizer per splitter | node `metadata` + parent/child relationships |
| Chonkie | `TokenChunker`, `SentenceChunker`, `RecursiveChunker`, `SemanticChunker`, `LateChunker`, `CodeChunker`, `NeuralChunker`, `SlumberChunker` (aka AgenticChunker), `TableChunker`; refineries `OverlapRefinery`, `EmbeddingsRefinery`; chefs `TextChef`, `MarkdownChef`, `TableChef`, `MistralOCR`; porters `JSONPorter`, `DatasetsPorter`; handshakes for Chroma, Elasticsearch, MongoDB, pgvector, Pinecone, Qdrant, Turbopuffer, Weaviate, LanceDB, Milvus. `SDPMChunker` not in README today (unverified) | fixed through agentic, late | yes | handshakes write chunks straight into stores |
| Unstructured | `chunk_elements` (`basic`), `chunk_by_title` (`by_title`); params `max_characters` 500 default, `new_after_n_chars`, `combine_text_under_n_chars`, `overlap` 0, `overlap_all` False, `multipage_sections` True; emits `CompositeElement`, `Table`, `TableChunk`; or `partition(..., chunking_strategy=...)` | element-based | characters, not tokens | element metadata (page, coordinates) kept |
| Docling | `BaseChunker.chunk(dl_doc) -> Iterator[BaseChunk]`, `contextualize(chunk) -> str`; `HierarchicalChunker` (one chunk per element, `merge_list_items`); `HybridChunker` (tokenizer-bounded refinement, `merge_peers` True, `repeat_table_header`, `omit_header_on_overflow`) | structure then token-bound | yes (user-supplied tokenizer) | headings and captions attached; `max_tokens` param name unverified |

## Loaders and parsers

| Tool | Input | Output | Hosted / local | Pricing unit |
|---|---|---|---|---|
| Unstructured `partition_*` + API | PDF, Office, HTML, images, email | typed elements (`Title`, `NarrativeText`, `Table`, ...) with metadata | both | per page (hosted; figure unverified) |
| Docling | PDF, DOCX, PPTX, HTML, images | `DoclingDocument` (layout, tables, reading order) → Markdown/JSON | local | free |
| LlamaParse | PDF and many office formats | Markdown / JSON nodes | hosted | per page (unverified) |
| LangChain document loaders | hundreds of sources | `Document(page_content, metadata)` | local wrappers | n/a |
| Azure Document Intelligence, AWS Textract, Mistral OCR, Reducto, Chunkr, Apache Tika | PDF/images → text, tables, layout | JSON/Markdown | hosted (Tika local) | per page (not re-verified today) |
| Model-native PDF input (OpenAI `input_file`, Gemini Files, Anthropic `document`) | PDF | tokens in the prompt | hosted | input tokens |

The ocai angle: loaders produce `Source` payloads (`SourceBase64`,
`SourceUrl`, `SourceRef`) the chat and embedding ports already accept; a
loader never needs a kernel type of its own.

## Contextual retrieval (Anthropic, September 2024)

Mechanism: for each chunk, ask the model (the post used Claude 3 Haiku) for
"a short succinct context to situate this chunk within the overall
document", with the whole document in the prompt under prompt caching so
the document is paid for once; prepend that context to the chunk before
both embedding and BM25 indexing. Reported on a top-20 retrieval failure
rate baseline of 5.7%: contextual embeddings 3.7% (35% fewer failures),
plus contextual BM25 2.9% (49%), plus a reranker (Cohere was tested) over
the top 150 then top 20 to the model 1.9% (67%). Cost: $1.02 per million
document tokens one-time, assuming 800-token chunks, 8k-token documents,
50-token instruction, 100-token context. Kernel relevance: it is a
*workflow* over `chat` (with cache-read usage in `UsageSource.CACHED`),
`embedding` and a hybrid `search`; the ledger must attribute the
contextualisation tokens to ingestion, which is a `CallContext.tags`
concern, not a new field.

## Graph RAG

| System | Indexing | Query modes | Storage | Notes |
|---|---|---|---|---|
| Microsoft GraphRAG | TextUnits → entity/relationship/claim extraction → Leiden community detection → community summaries | Global, Local, DRIFT, Basic | parquet + any vector store | CLI `graphrag init --root <path>`; LazyGraphRAG not on the docs landing page today |
| `neo4j-graphrag` | `SimpleKGPipeline` (page not read today; unverified) | `VectorRetriever(driver, index_name, embedder).search(query_text, top_k)`; `create_vector_index(driver, name, label, embedding_property, dimensions, similarity_fn)`; extras `weaviate`, `pinecone`, `qdrant` | Neo4j + optional external vector store | hybrid/Cypher retrievers listed in API docs, names unverified today |
| LightRAG | dual-layer KG + vector embeddings | `local`, `global`, `hybrid`, `naive`, `mix` (default) | in-memory defaults (JsonKV, NanoVectorDB, NetworkX); PostgreSQL recommended for production; MongoDB, OpenSearch; Milvus/Qdrant vectors, Neo4j/Memgraph graphs | `lightrag-server` REST + UI; RAG-Anything for multimodal |
| Bedrock KB with Neptune Analytics | GraphRAG as a knowledge-base option | through `Retrieve` | Neptune Analytics | not re-verified today |

All of these are LLM + embedding + store pipelines; the graph store is one
more vectorstore-port peer at most (Neo4j vector index), never a conversion
edge.

## Agent memory APIs

| Product | API surface (verified today) | Scoping keys | Storage model | Pricing unit |
|---|---|---|---|---|
| Mem0 Platform | `POST /v3/memories/add/` (`messages[]`, `metadata`, `infer`, `expiration_date`, `custom_categories`, `enable_graph`, async `event_id`/`status`), `POST /v3/memories/search/` (`query`, `filters` with `AND`/`OR`/`NOT`, `in`, `gte`, `lte`, `gt`, `lt`, `ne`, `contains`, `icontains`, `*`; `top_k` 1–1000, `threshold`, `rerank`, `reference_date`); response `results[] {id, memory, user_id, agent_id, app_id, run_id, metadata, categories, score, score_breakdown {semantic, bm25, entity}, expiration_date}`; `Authorization: Token <key>` | `user_id`, `agent_id`, `app_id`, `run_id` (at least one) | extracted fact strings + optional graph | per memory operation (unverified) |
| Zep | `thread.add_messages`, `graph.episode.add` (text, json, message), `thread.get_context` (context block), `graph.search_edges` / `search_nodes` / `search_episodes` / `search_observations` / `search_thread_summaries`; facts record when they became invalid; custom entity/edge types; `document_id` provenance | user graph, shared `graph_uuid` | temporal knowledge graph (Graphiti) | unverified |
| Letta (f.k.a. MemGPT) | memory blocks `{label, description, value, limit, read_only}` via `client.blocks.create`, attached with `memory_blocks` / `block_ids` or `client.agents.blocks.attach/detach`; all messages persisted and retrievable after eviction; `letta server` self-host, Letta Cloud | agent; shared blocks across agents | in-context blocks + archival/recall stores (tool names unverified today) | unverified |
| Supermemory | docs site unreachable from our fetcher today; endpoint and field names unverified | container tags (unverified) | unverified | unverified |
| Anthropic memory tool | tool `{type: "memory_20250818", name: "memory"}`, commands `view` (`path`, `view_range`), `create` (`path`, `file_text`), `str_replace` (`path`, `old_str`, `new_str`), `insert` (`path`, `insert_line`, `insert_text`), `delete` (`path`), `rename` (`old_path`, `new_path`), rooted at `/memories`; **client-side**: your handler stores the files; no beta header needed; pairs with context editing and compaction | whatever your handler maps the path to | files you own | ordinary tokens |
| OpenAI | no cross-session memory API; `previous_response_id` and Conversations objects are provider-scoped `ProviderRef`s, already modelled | n/a | n/a | n/a |
| Vertex AI Agent Engine Memory Bank | generate / fetch memories from sessions, memory profiles, revisions; VPC-SC, CMEK, data residency | user-level scope (dict shape unverified) | LLM-extracted memories | unverified |
| Bedrock AgentCore Memory | `CreateMemory` / `UpdateMemory` with strategies; events via `CreateEvent`; short-term (session turns) vs long-term (extracted); built-in strategies, built-in overrides (your prompts, Bedrock models in your account), self-managed strategies | actor / session (names from navigation; field names unverified) | managed store | storage higher for built-ins (relative only) |

The memory landscape confirms the verdict: Anthropic's design puts memory
*in the client*; Mem0 and Zep sell *extraction* and *search*; Letta sells
*an agent runtime*. Nothing here is one semantic job with several dialects.

## What the kernel must provide (substrate)

- `Source` refs for ingestion inputs and `SourceRef(ProviderRef)` for
  uploaded files (exists; H6 "files" makes the handles first-class).
- `Usage` dimensions for the costs these layers incur: embedding tokens,
  cache reads for contextual retrieval, and the open-code units
  (`read_units`, `search_units`, `storage_bytes`) that the vectorstore
  capability brings in. `Consumption.source` gains nothing; new units are
  data (§11 step 9).
- `CallContext.tags` for attributing ingestion vs query traffic in the
  ledger, and `tenant` for the per-user scoping every memory product keys
  on.
- The vectorstore `search` operation and canonical filter AST (hybrid page),
  because every memory product above is a filtered hybrid search over a
  private store, and a platform memory module built on the port inherits
  governance for free.
- Pure-data IR for chunks: a chunk is a `Record(id, vector, metadata,
  content)` already; `metadata` carries parent id, offsets and headings.
  No `Chunk` type in core.

Nothing above requires a change to `ocai.core`; the two additive needs
(`Usage` unit codes, vectorstore `search`) are owned by the vectorstore
capability.

## Sources

All read 2026-11-10.

- https://www.anthropic.com/news/contextual-retrieval
- https://docs.langchain.com/oss/python/integrations/splitters
- https://developers.llamaindex.ai/python/framework/module_guides/loading/node_parsers/modules/
- https://github.com/chonkie-inc/chonkie
- https://docs.unstructured.io/open-source/core-functionality/chunking
- https://docling-project.github.io/docling/concepts/chunking/
- https://microsoft.github.io/graphrag/
- https://neo4j.com/docs/neo4j-graphrag-python/current/
- https://github.com/HKUDS/LightRAG
- https://docs.mem0.ai/api-reference/memory/add-memories
- https://docs.mem0.ai/api-reference/memory/v2-search-memories (served the v3 search reference)
- https://help.getzep.com/concepts
- https://github.com/letta-ai/letta
- https://docs.letta.com/concepts/memory
- https://docs.letta.com/guides/agents/memory-blocks
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/memory-bank/overview
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-strategies.html
- https://supermemory.ai/docs/api-reference/memories/add-memory (404 today)
