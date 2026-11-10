# Rerank — provider survey and canonical IR proposal

**Currency.** Researched 2026-11-10 against official provider documentation
(URLs in Sources). Rerank APIs churned heavily in 2025–2026 (Cohere v2 dropped
object documents and `return_documents`; Mixedbread withdrew its standalone
endpoint; Pinecone and Azure now mostly front Cohere models). Treat model ids
and limits as a snapshot. Anything not stated verbatim by the provider is
marked *unverified*.

**Scope.** `docs/plans/horizon.md` H6 names rerank "the first multi-provider
capability added after the freeze, so it is the recipe's proof". This page
applies architecture §11 to rerank: identity as data, `ocai.rerank` importing
core only, a port returning `CallResult[RerankResponse]`, canonical nodes,
provider fragments, three-lane knobs, errors and consumption through core.

## 1. Provider survey

### 1.1 Cohere — `POST https://api.cohere.com/v2/rerank`

| Aspect | Detail |
|---|---|
| Models | `rerank-v5.0-pro`, `rerank-v5.0-fast` (32,768 tokens "query and document combined"; 100+ languages; over-long documents are chunked and processed in multiple inferences), `rerank-v4.0-pro`, `rerank-v4.0-fast` (32k), `rerank-v3.5` (4k), `rerank-english-v3.0`, `rerank-multilingual-v3.0` (4k) |
| Request | `model`, `query`, `documents` (**list of strings** — "structured data should be formatted as YAML strings"), `top_n`, `max_tokens_per_doc` (default `4096`), `relevant_spans{mode: enabled\|disabled, threshold (0.1 default), max_spans}` (v5+), `priority`; header `X-Client-Name` |
| Not in v2 | `return_documents`, object documents, `rank_fields` — none appear on the v2 reference page. They were v1 features; v2 results carry no `document` field (*v1 status unverified on this read*) |
| Limits | "recommend against sending more than 1,000 documents in a single request" (guidance, not hard); query token limit not stated |
| Response | `id`, `results[]{index, relevance_score, relevant_spans[]{start, end, score}}`, `meta{billed_units{search_units}}` |
| Scores | "normalized to be in the range `[0, 1]`"; "It is not accurate to assume a score of 0.9 means the document is 2x more relevant"; v5 described as "a calibrated score between 0 and 1" |
| Usage | `meta.billed_units.search_units` (the billing unit; token→unit formula not restated on the page) |
| Auth | `Authorization: Bearer` |

### 1.2 Voyage AI — `POST https://api.voyageai.com/v1/rerank`

| Aspect | Detail |
|---|---|
| Models | `rerank-2.5`, `rerank-2.5-lite` (32,000 context, 8,000 query tokens, optional instructions appended/prepended to the query), `rerank-2` (16,000 / 4,000), `rerank-2-lite` (8,000 / 2,000); all 600K total-token budget = query tokens × documents + sum of document tokens |
| Request | `query`, `documents` (array of strings, ≤ 1,000), `model`, `top_k` (default `null` = all), `return_documents` (default `false`), `truncation` (default `true`; `false` errors) |
| Response | `object: "list"`, `data[]{index, relevance_score, document (when requested)}` sorted descending, `model`, `usage{total_tokens}` |
| Scores | "The relevance score of the document with respect to the query" — no range stated; example values ≈ 0.44–0.46 |
| Auth | `Authorization: Bearer` |

### 1.3 Jina AI — `POST https://api.jina.ai/v1/rerank`

| Aspect | Detail |
|---|---|
| Models | `jina-reranker-v3.5` (131,072 tokens query + all documents, auto-truncated; "drop-in replacement" for v3; CC-BY-NC-4.0 weights), `jina-reranker-v3` (131K, **listwise** — "relevance is often relative to what else is in the candidate set"), `jina-reranker-m0` (multimodal, 10K tokens, ≤ 768 tokens per image; accepts "text strings, base64 images, or image URLs"), `jina-reranker-v2-base-multilingual` (1,024 tokens, pointwise cross-encoder, auto-chunking), `jina-colbert-v2` (8,192) |
| Request | `model`, `query`, `documents`, `top_n`, `return_documents`; `return_embeddings` on v3.5 (document embeddings). Object form for multimodal documents (`text`/`image` keys) is shown only by third-party docs — *unverified* |
| Limits | "There is no hard limit on the number of documents per request" |
| Response | `results[]{index, relevance_score, document}`, `usage{total_tokens}` — field names confirmed by the Hugging Face model card example, not by an API reference page (*schema unverified*) |
| Scores | Not defined as a range; v3 scores are listwise, so they depend on the candidate set |
| Auth | `Authorization: Bearer` |

### 1.4 Mixedbread — `POST /v1/reranking` (legacy)

| Aspect | Detail |
|---|---|
| Status | The API reference index states the standalone embedding/reranking reference pages "are no longer part of the current documentation"; reranking is now an option inside Stores search. Integrations on `POST /v1/reranking` are told to contact support for migration |
| Models | `mxbai-rerank-*-v1`, `mxbai-rerank-*-v2` families; `mxbai-rerank-large-v2` (Apache-2.0 weights, ≈1.5B, 8K/32K context) is served elsewhere (Together dedicated, TEI/vLLM self-host) |
| Legacy fields | `model`, `query`, `input`, `rank_fields`, `top_k`, `return_input`; response `data[]{index, score, input}`, `usage{prompt_tokens, total_tokens}` — *unverified* (page withdrawn) |
| ocai stance | Do not build a `mixedbread/reranking` interface; cover the model through hosted open-weights interfaces |

### 1.5 Pinecone Inference — `POST https://api.pinecone.io/rerank`

| Aspect | Detail |
|---|---|
| Headers | `Api-Key`; `X-Pinecone-Api-Version` (required, date-based, default `2026-07`) |
| Models | `cohere-rerank-4-fast` (multiple `rank_fields`, "ranked based on the order of the fields specified"), `bge-reranker-v2-m3` (single field), `pinecone-rerank-v0` (deprecated). `cohere-rerank-3.5` is not on the current page |
| Request | `model`, `query`, `documents` (**array of objects**, e.g. `{id, text, title, url}`, additional properties allowed), `top_n` (default = number of inputs), `return_documents` (default `true`), `rank_fields` (default `["text"]`), `parameters` (model-specific, e.g. `truncate: "END"` / `"NONE"` → error on overflow) |
| Response | `model`, `data[]{index, score, document}`, `usage{rerank_units}` |
| Scores | "normalized between 0 and 1, with scores closer to 1 indicating higher relevance" |
| Errors | 400 invalid parameters, 401 invalid key, 500; `ErrorResponse` envelope |

### 1.6 Amazon Bedrock — `Rerank` (bedrock-agent-runtime, `POST /rerank`)

| Aspect | Detail |
|---|---|
| Models | `amazon.rerank-v1:0` (not in us-east-1), `cohere.rerank-v3-5:0`; referenced by `modelArn` |
| Request | `queries[]` (fixed 1 item: `{type: "TEXT", textQuery{text}}`), `sources[]` (1–1,000: `{type: "INLINE", inlineDocumentSource{type: "TEXT" \| "JSON", textDocument{text} \| jsonDocument}}`), `rerankingConfiguration{type: "BEDROCK_RERANKING_MODEL", bedrockRerankingConfiguration{modelConfiguration{modelArn, additionalModelRequestFields{…}}, numberOfResults}}`, `nextToken` |
| Response | `results[]{index, relevanceScore, document{type, textDocument \| jsonDocument}}`, `nextToken` (paginated results) |
| Usage | None in the response (billed per Bedrock pricing) |
| Errors | `ValidationException` 400, `ThrottlingException` 429, `AccessDeniedException` 403, `ResourceNotFoundException` 404, `ServiceQuotaExceededException` 400, `InternalServerException` 500, `BadGatewayException` 502, `DependencyFailedException` 424 |
| Auth | SigV4 (narrow signing dependency, rule 12). Direct `InvokeModel` bodies for the Cohere rerank model exist but the parameter page could not be read — *unverified* |
| Note | Text only ("You can use reranking for only textual data") |

### 1.7 Azure — semantic ranker (Azure AI Search) and Cohere on Microsoft Foundry

| Aspect | Semantic ranker | Cohere rerank on Foundry |
|---|---|---|
| What it is | A query-side L2 reranker inside an Azure AI Search index: `queryType=semantic` + a semantic configuration; reranks only the top 50 BM25/RRF results; per-document summary ≤ 2,048 tokens (`title` 128, `keywords` 128, `content` remainder) | Serverless deployment of `rerank-v5.0-pro` (page) / v4.0 / v3.5 behind a per-deployment base URL such as `https://cohere-rerank-v5-pro-xyz.eastus.models.ai.azure.com/`; called with the Cohere v2 client (`model` is "a dummy string") |
| Output | `@search.rerankerScore` **0–4** ordinal scale (4 = fully answers, 0 = irrelevant), captions, answers; distributions "can exhibit slight variations" | Cohere v2 response (`results[]{index, relevance_score}`) |
| Standalone API? | **No** — it cannot rerank caller-supplied documents; the scope litmus test (§11) puts it outside the rerank capability (it is a search-index feature) | Yes — a **host** of the `cohere/rerank` interface; exact path (`/v2/rerank` vs `/v1/rerank` for v3 deployments) is *unverified* from official pages |

### 1.8 ZeroEntropy — `POST https://api.zeroentropy.dev/v1/models/rerank`

| Aspect | Detail |
|---|---|
| Models | `zerank-2`, `zerank-1`, `zerank-1-small`; EU host `eu-api.zeroentropy.dev` |
| Request | `model`, `query`, `documents` (strings), `top_n`, `latency` (`fast`, `slow`, or null) |
| Response | `results[]{index, relevance_score}` descending, `total_bytes` (rate limiting), `total_tokens` (billing), `actual_latency_mode`, `e2e_latency`, `inference_latency` |
| Scores | 0.0–1.0; "depends only on the query and that document, not on other documents" (pointwise); deterministic up to float error |
| Limits | 500,000 bytes/min and 1,000 RPM default; 5,000,000 bytes per request; bytes = Σ(150 + query + document) |
| Auth | `Authorization: Bearer` |

### 1.9 Hosted open weights — Together, TEI, vLLM

| Host | Shape |
|---|---|
| Together `POST https://api.together.ai/v1/rerank` | `model`, `query`, `documents` (strings **or objects**), `top_n`, `return_documents`, `rank_fields` (default all keys); response `object: "rerank"`, `id`, `model`, `results[]{index, relevance_score, document{text}}`, `usage{prompt_tokens, completion_tokens, total_tokens}`; models `Salesforce/Llama-Rank-V1`, `mixedbread-ai/mxbai-rerank-large-v2` (dedicated) |
| TEI `POST /rerank` | `query`, `texts` (required), `raw_scores`, `return_text`, `truncate`, `truncation_direction`; response array of `{index, score, text}`; 424 if the model is not a sequence-classification cross-encoder; supports `BAAI/bge-reranker-base/large`, `Alibaba-NLP/gte-*-reranker*`. `raw_scores=false` applies the model's activation (sigmoid), `true` returns logits |
| vLLM | `/rerank`, `/v1/rerank`, `/v2/rerank` — "Implements Jina AI's v1 rerank API", "compatible with Cohere's v1 & v2 rerank APIs": `query`, `documents`, `top_n` → `results[]{index, document, relevance_score}`; `/score` and `/v1/score`: `text_1`, `text_2` (string or list) → `data[]{score}` for cross-encoder, bi-encoder, and late-interaction models; `truncate_prompt_tokens` on the request (*current version unverified*) |

### 1.10 Local in-process peer — sentence-transformers `CrossEncoder`

`CrossEncoder.rank(query, documents, top_k=None, return_documents=False,
prompt_name=None, prompt=None, batch_size=32, activation_fn=None, ...)` returns
"A sorted list with the `corpus_id`, `score`, and optionally `text`";
`query` may be "a string, image, or multimodal dict" and documents likewise.
`predict(inputs, activation_fn=None, apply_softmax=False, ...)` returns raw
pair scores. Default scores are model logits (the docs example shows
`8.40` and `-4.32`), so `activation_fn` (sigmoid) decides whether the scale is
`[0, 1]`. No usage. This is the `route=None` / `host="in-process"` adapter.

## 2. Cross-provider comparison

| Provider | Documents | Object docs / `rank_fields` | Top-n knob | Return docs | Truncation knob | Multimodal | Max docs | Score scale | Pointwise? | Usage |
|---|---|---|---|---|---|---|---|---|---|---|
| Cohere v2 | strings (YAML for structured) | no (v2) | `top_n` | no (index only) | `max_tokens_per_doc` | no | ~1,000 guidance | [0, 1] "calibrated" | yes (chunked long docs) | `search_units` |
| Voyage | strings | no | `top_k` | `return_documents` | `truncation` bool | no | 1,000 | unspecified | yes | `total_tokens` |
| Jina | strings (+ image objects on m0, *unverified*) | no | `top_n` | `return_documents` | auto | m0 | none | unspecified; v3/v3.5 **listwise** | no (v3) | `total_tokens` |
| Pinecone | **objects** | `rank_fields` | `top_n` | `return_documents` | `parameters.truncate` | no | model-specific | [0, 1] normalized | model-dependent | `rerank_units` |
| Bedrock Rerank | TEXT or JSON | JSON documents | `numberOfResults` | always | via `additionalModelRequestFields` | no | 1,000 | model-dependent (Cohere-backed) | yes | none |
| Azure semantic ranker | index only | n/a | top 50 fixed | n/a | 2,048-token summaries | no | 50 | **0–4** ordinal | yes | n/a |
| ZeroEntropy | strings | no | `top_n` | no | none | no | 5 MB payload | [0, 1] pointwise | yes (explicit) | `total_tokens`, `total_bytes` |
| Together | strings or objects | `rank_fields` | `top_n` | `return_documents` | none stated | no | not stated | unspecified | model-dependent | `prompt_tokens` |
| TEI `/rerank` | strings | no | none (client slice) | `return_text` | `truncate` + direction | no | none | logits or activation (`raw_scores`) | yes | none |
| vLLM `/v1/rerank` | strings | no | `top_n` | yes | `truncate_prompt_tokens` | model-dependent | none | model-dependent | yes | OpenAI-style usage |
| CrossEncoder | strings / images / dicts | no | `top_k` | `return_documents` | model max length | yes | in-process | logits unless `activation_fn` | yes | none |

## 3. Canonical IR proposal (`ocai.rerank`)

### 3.1 Identity and port

- `Capability("rerank")`, shapes `rerank.request` and `rerank.response`;
  canonical nodes at the current `ocai@<rev>`.
- Port `Reranker` with `rerank(request, *, ctx) -> CallResult[RerankResponse]`
  and `arerank`. No `model` in the request (§11 step 3).
- Local peer: the `CrossEncoder` adapter implements the port directly.

### 3.2 Request

| Field | Lane | Rationale |
|---|---|---|
| `query: Document` | 1 | A `Document` (string sugar in the constructor) so Jina-m0 and `CrossEncoder` multimodal queries fit; string-only providers report `UNSUPPORTED` for non-text query content |
| `documents: list[Document]` | 1 | Reuses the embedding `Document` (`id`, `content`, `metadata`). String-only providers receive `content`; object-accepting providers (Pinecone, Together, Bedrock JSON) receive `content` under their text field plus `metadata` keys. Result `index` aligns to this list |
| `top_n: int \| None` | 1 | Universal (`top_n`, `top_k`, `numberOfResults`). TEI lacks it → `EMULATED` client-side slice, declared |
| `return_documents: bool \| None` | 1 | Voyage, Jina, Pinecone, Together, TEI, CrossEncoder. Cohere v2 and ZeroEntropy cannot → the **facade** re-attaches documents from the request and reports `EMULATED`; Bedrock always returns them (`EXACT`, extra data ignored is not loss) |
| `truncate: str \| None` | 1 | Same open code as embeddings (`none`/`end`/`start`); Cohere `max_tokens_per_doc` is a different axis → keep as censused extension `cohere.rerank/max_tokens_per_doc` with a promotion trigger (a second provider with a per-document token cap) |
| `rank_fields: list[str] \| None` | 2 | Pinecone, Together (and Cohere v1 historically). Fewer than three current interfaces with congruent semantics (Pinecone ranks by field order, Together by all keys) → censused extension `rerank/rank_fields` shared by both fragments; promotion trigger: Cohere or Jina re-adding object documents |
| `instruction: str \| None` | excluded | Voyage 2.5 appends instructions to the query text; this is query content, not a knob — users put it in `query`. Recorded exclusion |
| `relevant_spans` (Cohere v5), `return_embeddings` (Jina), `latency` (ZeroEntropy), `raw_scores` (TEI), `priority` | 2 / 3 | Output-altering ones are censused extensions (`cohere.rerank/relevant_spans`, `jina.rerank/return_embeddings`, `tei.rerank/raw_scores`); scheduling preferences ride `provider_options["<destination>"]` |

### 3.3 Response and the score question

```
RerankResult(index: int, score: float, document: Document | None)
RerankResponse(results: list[RerankResult], score_scale: str, usage: Usage | None, model: str | None)
```

- `results` are **sorted descending by `score`**; the order is the portable
  contract. Conformance asserts sortedness and that every `index` is unique and
  within `len(request.documents)`.
- **Scores are not comparable across providers**, and ocai must say so
  structurally rather than normalize. `score_scale` is an open code filled by
  the codec from the profile: `unit_interval` (Cohere, Pinecone, ZeroEntropy,
  TEI with activation, CrossEncoder with sigmoid), `logit` (TEI `raw_scores`,
  CrossEncoder default), `ordinal_0_4` (Azure semantic ranker, if ever
  wrapped), `unknown` (Voyage, Jina, Together, vLLM where undocumented), with a
  `score_scale_native` lane preserving the provider's own wording.
- Any rescaling ocai performs (sigmoid over logits, min-max over a result
  set) is a facade option declared as `SemanticShift(kind="score_normalization")`
  with `APPROXIMATED` disposition on `results[].score` — the exact rule 5
  case: out-of-range values pass verbatim unless the user asked for a
  declared transform.
- **Listwise vs pointwise is a profile fact** (`scores_pointwise: bool`). It
  matters because facade fan-out over a document limit (Voyage/Bedrock
  1,000) changes listwise scores: on a listwise model the fan-out is a
  `SemanticShift` of high severity; on a pointwise model it is lossless for
  ranking.
- Bedrock `nextToken` pagination is a facade fan-in (N wire calls → one
  response), declared like batch fan-out in embeddings.
- `document` is populated only when returned or re-attached (see
  `return_documents`); Bedrock JSON documents decode into `Document.metadata`
  with `content` from the ranked text field.
- Extensions on a result: `cohere.rerank/relevant_spans[]{start, end, score}`,
  `jina.rerank/embedding`.

### 3.4 Usage through core `Consumption`

| Wire | `Consumption` |
|---|---|
| Cohere `meta.billed_units.search_units` | `(modality=text, unit="search_units", source=input)` — new open unit code, never converted to tokens |
| Pinecone `usage.rerank_units` | `(text, "rerank_units", input)` |
| Voyage, Jina, ZeroEntropy `total_tokens` | `(text, tokens, input)` |
| ZeroEntropy `total_bytes` | `(text, "bytes", input)` (rate-limit accounting, kept because the provider reports it) |
| Together `prompt_tokens` | `(text, tokens, input)` |
| Bedrock, TEI, CrossEncoder | `usage=None` |

Latency fields (ZeroEntropy `e2e_latency`, `inference_latency`) are not
consumption; they ride `EmbeddingResponse`-style `extensions` on the response
under `zeroentropy.rerank/latency`.

### 3.5 Errors

All map through the shared taxonomy: 429 / `ThrottlingException` /
ZeroEntropy BPM overflow → `RateLimitError`; 401/403 → `AuthError`; Voyage
`truncation=false` overflow, Pinecone `truncate: NONE` overflow, Cohere
context overflow → `ContextLengthError`; 5xx / `BadGatewayException` /
`DependencyFailedException` → `TransientError`; TEI 424 (wrong model class)
and Pinecone 400 → the generic invalid-request error with the native code
preserved. Rerank does not stream (no streaming ratchet needed; §11 step 8
does not apply).

### 3.6 The `Document` hoist decision (architecture §2.8)

`ocai.rerank` may import only `ocai.core`, yet it needs the same `Document`
that `ocai.embedding` defines. Duplicating it would create two `document`
IR objects with one meaning — a conversion lie waiting to happen. Recommended:
hoist `Document` (and the `Embeddable`-style sugar) to `ocai.core.documents`
in the rerank WU, leave `ocai.embedding.types.document` as a pure re-export
shim (the same pattern used for `usage`/`finish`), and keep `Vector`/`Embedding`
in `ocai.embedding`. The truncation open code (`none`/`end`/`start`) should
land beside it in core so both capabilities share one vocabulary.

## 4. Priority, effort, and the first-provider recommendation

| Provider / interface | Priority | Effort | Why |
|---|---|---|---|
| IR + identity + port + `spec/` schemas + `Document` hoist + `CrossEncoder` local peer | **P0** (first) | 1 WU | The recipe's proof starts with the data; the local peer lets conformance run with no keys |
| `cohere/rerank` (v2) | **P0** | 1 WU | See recommendation below |
| Front door `ocai.rerank.model("cohere/rerank-v3.5", ...)` with fan-out, `return_documents` emulation, `nextToken` fan-in | P0 | 0.5 WU | §11 step 11, last |
| `voyage/rerank` | P1 | 0.5 WU | Second dialect: `top_k` naming, `return_documents`, `truncation` → `ContextLengthError`, 600K budget as a profile fact |
| `jina/rerank` (also the vLLM dialect) | P1 | 1 WU | Listwise models force the `scores_pointwise` profile fact; needs a recorded pair before fixtures because the public schema is thin |
| TEI `/rerank` (hosted bge-reranker) | P1 | 0.5 WU | Logit scale (`score_scale=logit`), no `top_n` → first `EMULATED` slice, `raw_scores` extension |
| Cohere hosts: Microsoft Foundry, Bedrock (`cohere.rerank-v3-5:0` via `Rerank`) | P2 | 0.5 WU each | Bedrock is a different envelope (`sources`, `relevanceScore`, pagination, SigV4) — closer to 1 WU; Foundry is a host of `cohere/rerank` once the path is verified |
| `pinecone/rerank` | P2 | 1 WU | Object documents + `rank_fields` extension, `rerank_units`, date-versioned header as `DialectTraits` |
| `together/rerank`, `zeroentropy/rerank`, vLLM `/score` | P2–P3 | 0.5 WU each | Small dialects; vLLM `/score` is pairwise scoring rather than ranking (a `score` operation on the same port, or excluded) |
| Azure AI Search semantic ranker | P3 / out of scope | — | Not a caller-supplied-documents API; belongs to a future search/vectorstore query path, not the rerank capability |
| Mixedbread standalone API | skip | — | Withdrawn; serve the weights via TEI/vLLM |

**Recommended first rerank provider: Cohere `/v2/rerank`.** Its request and
response shape (`query`, `documents`, `top_n` → `results[]{index,
relevance_score}`) is the dialect that vLLM, Together, Pinecone (as `score`),
Bedrock (as `relevanceScore`), and Microsoft Foundry re-implement or front, so
one codec and one census seed four more fragments at host-variant cost — which
is exactly what "the first multi-provider capability" needs to prove. It also
hits every honesty mechanism in one small edge: `search_units` exercises the
open `UsageUnit` code, the missing `return_documents` is a clean first
`EMULATED` disposition in the facade, `[0, 1]` calibrated scores give the
`score_scale` lane an unambiguous first value, and `relevant_spans` is a
real censused extension from day one. Voyage is the natural second (same
vendor as the P1 embedding interface, tiny dialect); Jina third because its
listwise scores are what make `scores_pointwise` and fan-out severity real.

## Sources

Read 2026-11-10.

- https://docs.cohere.com/reference/rerank
- https://docs.cohere.com/docs/rerank
- https://docs.cohere.com/docs/cohere-on-azure/azure-ai-reranking
- https://docs.voyageai.com/reference/reranker-api
- https://docs.voyageai.com/docs/reranker
- https://jina.ai/reranker
- https://jina.ai/models/jina-reranker-v3.5/
- https://jina.ai/models/jina-reranker-m0/
- https://huggingface.co/jinaai/jina-reranker-m0
- https://www.mixedbread.com/api-reference/endpoints/reranking
- https://mixedbread.com/api-reference/endpoints/reranking/rerank-documents
- https://docs.pinecone.io/reference/api/latest/inference/rerank
- https://docs.pinecone.io/guides/search/rerank-results
- https://docs.aws.amazon.com/bedrock/latest/userguide/rerank.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/rerank-supported.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/rerank-use.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_Rerank.html
- https://learn.microsoft.com/en-us/azure/search/semantic-search-overview
- https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-models-cohere-rerank
- https://docs.zeroentropy.dev/api-reference/models/rerank
- https://docs.together.ai/reference/rerank
- https://huggingface.github.io/text-embeddings-inference/openapi.json
- https://github.com/huggingface/text-embeddings-inference/blob/main/README.md
- https://docs.vllm.ai/en/latest/serving/online_serving/
- https://docs.vllm.ai/projects/recipes/en/latest/Jina/Jina-reranker-m0.html
- https://sbert.net/docs/package_reference/cross_encoder/cross_encoder.html
