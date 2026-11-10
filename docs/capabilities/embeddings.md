# Embeddings — provider survey and canonical IR proposal

**Currency.** Researched 2026-11-10 against official provider documentation
(URLs in Sources). Provider APIs in this space move monthly: model ids,
dimension sets, and limits below are a snapshot, not a contract. Anything the
official page did not state verbatim is marked *unverified*.

**Scope.** This page informs H3 (graduating the provisional `ocai.embedding`
port by carrying `CallResult` in real use — see `docs/plans/horizon.md`) and
applies the architecture §11 recipe to embeddings. It covers remote providers,
OpenAI-compatible hosts for open weights, and the in-process local peer.

## 1. Provider survey

Conventions: field names are quoted exactly as the provider documents them.
"Batch" is inputs per wire call. Auth is the request header unless noted.

### 1.1 OpenAI — `POST /v1/embeddings`

| Aspect | Detail |
|---|---|
| Models | `text-embedding-3-small` (1536 default), `text-embedding-3-large` (3072 default), `text-embedding-ada-002` (dims not stated on the page; 1536 by common knowledge — *unverified on this read*) |
| Request | `input` (string, array of strings, array of tokens, array of token arrays), `model`, `encoding_format` (`float` default or `base64`), `dimensions` (int ≥ 1, "Only supported in `text-embedding-3` and later models"), `user` |
| `dimensions` semantics | Shortens by "remove some numbers from the end of the sequence"; manual truncation requires renormalization, server-side truncation does not |
| Modalities | Text only (plus pre-tokenized integer arrays — not portable) |
| Limits | 8192 tokens per input; arrays `maxItems: 2048`; "a maximum of 300,000 tokens summed across all inputs in a single request" |
| Response | `object: "list"`, `data[]{object: "embedding", embedding (floats or base64 string), index}`, `model`, `usage{prompt_tokens, total_tokens}` |
| Usage | `prompt_tokens == total_tokens` (no output tokens) |
| Errors | Standard OpenAI error envelope; 400 on empty string / over-limit; 429 rate limit |
| Auth | `Authorization: Bearer` |

### 1.2 Azure OpenAI — `POST {resource}/openai/v1/embeddings`

| Aspect | Detail |
|---|---|
| Interface | Same wire dialect as OpenAI; the v1 path takes `model` = **deployment name**. Older dated paths `/openai/deployments/{deployment-id}/embeddings?api-version=...` still exist |
| Limits | Identical: 8,192 tokens per input, 2,048 array size, 300,000 aggregate tokens (HTTP 400 above) |
| Auth | `api-key` header, or `Authorization: Bearer` with a Microsoft Entra token (recommended) |
| Errors | 401 token audience, 403 missing role, 404 wrong path or deployment, 400 body/limits |
| ocai mapping | A **host** of the `openai/embeddings` interface (`hosting` value + `DialectTraits`), not a new interface |

### 1.3 Voyage AI — `POST https://api.voyageai.com/v1/embeddings`

| Aspect | Detail |
|---|---|
| Models | `voyage-4-large`, `voyage-4`, `voyage-4-lite`, `voyage-3.5`, `voyage-3.5-lite`, `voyage-3-large`, `voyage-code-3`: 32,000-token context, 1024 default, `output_dimension` ∈ {256, 512, 1024, 2048}, dtypes float/int8/uint8/binary/ubinary. Legacy `voyage-3`: 1024 only, float only. "All embeddings created with the 4 series are compatible with each other" |
| Request | `input` (string or array), `model`, `input_type` (`null` default, `query`, `document` — prepends a retrieval prompt), `truncation` (bool, default `true`; `false` raises on overflow), `output_dimension`, `output_dtype` (`float` default, `int8`, `uint8`, `binary`, `ubinary`), `encoding_format` (`null` or `base64`) |
| Limits | 1,000 items per `input`; total tokens per request 1M (`voyage-4-lite`, `voyage-3.5-lite`), 320K (`voyage-4`, `voyage-3.5`), 120K (`voyage-4-large`, `voyage-3-large`, `voyage-code-3`) |
| Response | `object: "list"`, `data[]{object: "embedding", embedding (floats, or ints for non-float dtypes), index}`, `model`, `usage{total_tokens}` |
| Multimodal | `POST /v1/multimodalembeddings`: `inputs[].content[]` items of type `text`, `image_url`, `image_base64`, `video_url`, `video_base64`; `model` `voyage-multimodal-3.5` / `voyage-multimodal-3`; `input_type`; `truncation`; `output_encoding`. Limits: 1,000 inputs, 32,000 tokens per input, 320,000 total; images ≤ 16M pixels / 20 MB; 560 image pixels = 1 token, 1,120 video pixels = 1 token. Usage: `text_tokens`, `image_pixels`, `video_pixels`, `total_tokens` |
| Contextualized | `POST /v1/contextualizedembeddings`: `inputs` is a **list of lists** of chunk strings, `model` `voyage-context-3`, same `input_type`/`output_dimension`/`output_dtype`/`encoding_format`; response nests `data[]{index, data[]{embedding, index}}`; 1,000 inputs, 16K chunks, 120K tokens |
| Auth | `Authorization: Bearer` |

### 1.4 Cohere — `POST https://api.cohere.com/v2/embed`

| Aspect | Detail |
|---|---|
| Models | `embed-v5.0-pro`, `embed-v5.0-fast` (text/image/mixed, 128k context, dims {256, 512, 768, 1024, 1536, 2048 default}, Matryoshka, returned as float/int8/binary; Pro and Fast share one embedding space), `embed-v4.0` (128k, dims {256, 512, 1024, 1536 default}), `embed-english-v3.0` / `embed-multilingual-v3.0` (1024, 512 tokens), `-light-v3.0` variants (384) |
| Request | `model`, `input_type` (**required** for v3+: `search_document`, `search_query`, `classification`, `clustering`, `image`), `texts` (≤ 96), `images` (data URIs jpeg/png/webp/gif; v3: 1 per call ≤ 5 MB; v4+: no count limit; 20 MB combined), `inputs[]` (≤ 96; each `content[]` mixes `{type: "text", text}` and `{type: "image_url", image_url: {url}}`), `max_tokens`, `output_dimension` (v4+), `embedding_types` (list; `float` default, `int8`, `uint8`, `binary`, `ubinary`, `base64`), `truncate` (`NONE`, `START`, `END` default), `priority` |
| Response | `id`, `embeddings{float, int8, uint8, binary, ubinary, base64}` (each a list aligned to input order — **multiple encodings per input in one call**), `texts`, `images[]{width, height, format, bit_depth}`, `meta{billed_units{input_tokens, images}, warnings, api_version}` |
| Usage | `meta.billed_units.input_tokens` and `.images` (images billed as a count) |
| Errors | Standard Cohere JSON errors (codes not restated on the reference page) |
| Auth | `Authorization: Bearer`; optional `X-Client-Name` |

### 1.5 Jina AI — `POST https://api.jina.ai/v1/embeddings`

| Aspect | Detail |
|---|---|
| Models | `jina-embeddings-v3` (1024 default, 8,192 tokens, Matryoshka 32–1024, tasks `retrieval.query`, `retrieval.passage`, `separation`, `classification`, `text-matching`), `jina-embeddings-v4` (2048 default, Matryoshka {128, 256, 512, 1024, 2048}, 32K tokens, text/image/PDF, single-vector and multi-vector output, task adapters `retrieval`/`text-matching`/`code`; Qwen Research License, throughput throttled, "not suitable for production workloads"), v5 family (`jina-embeddings-v5-text-small` 1024 default, Matryoshka to 32; `-omni-*` variants) |
| Request | `model`, `input` (strings, or typed objects with an `image`, `audio`, `video`, or `pdf` key — the `text` object form is *unverified*), `task`, `dimensions`, `late_chunking` (bool), `embedding_type` (`float` default, `binary`, `base64`; `ubinary` *unverified*), `normalized`, `truncate` (bool; overflow errors unless `true`). Multi-vector selection is named `output_type` on the current page; earlier docs used `return_multivector` — *which is current is unverified* |
| Response | OpenAI-shaped `data[]{embedding, index}`, `usage` with "the exact token count" and an `image_tokens` breakdown for multimodal (exact field names *unverified* — the public page shows no schema) |
| Limits | Rate limits per key: free 100 RPM / 100K TPM, paid 500 RPM / 2M TPM, premium 5,000 RPM / 50M TPM; batch size not stated |
| Auth | `Authorization: Bearer` |

### 1.6 Google — Gemini API and Vertex AI

| Aspect | Gemini API | Vertex AI |
|---|---|---|
| Endpoint | `POST .../v1beta/models/{model}:embedContent`; `:batchEmbedContents` | `POST https://{region}-aiplatform.googleapis.com/v1/projects/{p}/locations/{r}/publishers/google/models/{model}:predict` |
| Models | `gemini-embedding-2` (multimodal; 3072 default, 128–3072, recommended 768/1536/3072, **auto-normalizes truncated vectors**; 8,192 tokens; ≤ 6 images, ≤ 180 s audio, ≤ 120 s video, 1 PDF ≤ 6 pages); `gemini-embedding-001` (text, 2,048 tokens, manual renormalization below 3072) | `text-embedding-005` (768, 2,048 tokens), `text-multilingual-embedding-002` (768), `gemini-embedding-001` (3072; "each request can only include a single input text") |
| Request | `content` (parts), `taskType` (only `gemini-embedding-001`: `RETRIEVAL_QUERY`, `RETRIEVAL_DOCUMENT`, `SEMANTIC_SIMILARITY`, `CLASSIFICATION`, `CLUSTERING`, `QUESTION_ANSWERING`, `FACT_VERIFICATION`, `CODE_RETRIEVAL_QUERY`; "You cannot use the `task_type` field" with `gemini-embedding-2` — task is expressed as a **text prefix** such as `task: search result \| query: {content}`), `title`, `outputDimensionality` | `instances[]{content, task_type (default RETRIEVAL_QUERY), title (RETRIEVAL_DOCUMENT only)}`, `parameters{outputDimensionality, autoTruncate (default true)}` |
| Response | `embedding{values}`, `usageMetadata{promptTokenCount}`; batch returns one `EmbedContentResponse` per request | `predictions[]{embeddings{values, statistics{token_count, truncated}}}` |
| Batch | Not stated; Batch API at 50% price | Older models: 5 instances; `gemini-embedding-001`: 1 |
| Auth | `x-goog-api-key` | OAuth `Authorization: Bearer` (ADC) |

### 1.7 Mistral — `POST https://api.mistral.ai/v1/embeddings`

| Aspect | Detail |
|---|---|
| Models | `mistral-embed` (1024 dims — *unverified on this read*), `codestral-embed` (`output_dimension` defaults to 1536, maximum 3072; "These dimensions are ordered by relevance", so prefix truncation is valid) |
| Request | `model`, `input` (string or array), `output_dimension`, `output_dtype` (`float`, `int8`, `uint8`, `binary`, `ubinary`), `encoding_format` (`float`, `base64`), `metadata` |
| Response | `id`, `object`, `data[]{embedding, index, object}`, `model`, `usage{prompt_tokens, completion_tokens, total_tokens, prompt_audio_seconds}` |
| Limits | Per-input token limit and batch size not stated on the reference page (*unverified*) |
| Auth | `Authorization: Bearer` |

### 1.8 Nomic — `POST https://api-atlas.nomic.ai/v1/embedding/text`

| Aspect | Detail |
|---|---|
| Models | `nomic-embed-text-v1`, `nomic-embed-text-v1.5` (hosted). `nomic-embed-text-v2-moe` is open weights (768 default, 512-token inputs, `search_query:`/`search_document:` prefixes); a hosted endpoint for it is *unverified* |
| Request | `texts` (array), `model`, `task_type` (`search_document` default, `search_query`, `classification`, `clustering`), `long_text_mode` (`truncate` or `mean`), `max_tokens_per_text` (default 8192), `dimensionality` (default 768, v1.5 only) |
| Response | `embeddings` (array of arrays), `usage{prompt_tokens, total_tokens}`, `model`; 422 on validation error |
| Auth | `Authorization: Bearer` |

### 1.9 Amazon Bedrock — Titan Text Embeddings V2 and Nova Multimodal Embeddings

| Aspect | Titan V2 (`amazon.titan-embed-text-v2:0`) | Nova (`amazon.nova-2-multimodal-embeddings-v1:0`) |
|---|---|---|
| Transport | `InvokeModel` body; SigV4 signing (the one sanctioned narrow signing dependency, rule 12) | `InvokeModel` (sync, `taskType: "SINGLE_EMBEDDING"`) or `StartAsyncInvoke` (`SEGMENTED_EMBEDDING`, S3 output) |
| Request | `inputText` (one string), `dimensions` ∈ {1024 default, 512, 256}, `normalize` (default `true`), `embeddingTypes` (`["float"]`, `["binary"]`, or both) | `schemaVersion: "nova-multimodal-embed-v1"`, `singleEmbeddingParams{embeddingPurpose (GENERIC_INDEX, GENERIC_RETRIEVAL, TEXT_RETRIEVAL, IMAGE_RETRIEVAL, VIDEO_RETRIEVAL, DOCUMENT_RETRIEVAL, AUDIO_RETRIEVAL, CLASSIFICATION, CLUSTERING), embeddingDimension ∈ {256, 384, 1024, 3072 default}, exactly one of text{truncationMode START\|END\|NONE, value ≤ 8192 chars \| source}, image{format, detailLevel, source}, audio{format, source}, video{format, source, embeddingMode}}` |
| Response | `embedding` (floats; absent if only `binary` requested), `embeddingsByType{float, binary}`, `inputTextTokenCount` | `embeddings[]{embeddingType (TEXT\|IMAGE\|VIDEO\|AUDIO\|AUDIO_VIDEO_COMBINED), embedding, truncatedCharLength}`; **no token usage field** |
| Limits | 8,192 tokens / 50,000 chars; **one input per call**; throttled by RPM not TPM | One input per call; 25 MB inline (post-base64); audio/video ≤ 30 s sync |
| Errors | `ValidationException` 400, `ThrottlingException` 429, `AccessDeniedException` 403 (Bedrock common errors) | Same, plus per-segment `failureReason` codes (`RAI_VIOLATION_INPUT_TEXT_DEFLECTION`, …) in async output |

### 1.10 Open-weights hosts

| Host | Endpoint and shape | Notes |
|---|---|---|
| Together | `POST https://api.together.ai/v1/embeddings`, `model` + `input`, OpenAI-shaped `data[].embedding` | Serverless embedding catalog is shrinking (several `BAAI/*`, `m2-bert`, `multilingual-e5-large-instruct` removed or scheduled 2026); `data[].index` *unverified* |
| Fireworks | `POST https://api.fireworks.ai/inference/v1/embeddings`: `model`, `input`, `dimensions` (v1.5+ models), `normalize` (default `false`), `prompt_template`, `return_logits`; response `object: "list"`, `data[]{embedding, index}`, `model`, `usage{prompt_tokens, total_tokens}` | OpenAI dialect plus two extension knobs |
| HF Inference Providers | `feature-extraction` task: `inputs` (string or array), `normalize`, `prompt_name` (key of the sentence-transformers `prompts` dict), `truncate`, `truncation_direction` (`left`/`right`); response "an array of arrays"; no usage | Routed to third-party providers; model availability varies |
| Ollama | Native `POST /api/embed`: `model`, `input` (string, list, or objects with `text`/`image`/`audio`), `truncate` (default `true`; error if `false` and over context), `dimensions`, `options`, `keep_alive`; response `model`, `embeddings`, `prompt_eval_count`, durations in ns. `/v1/embeddings` compat supports `model`, `input` (string/array), `dimensions`, `encoding_format`; not `user` | Legacy `/api/embeddings` (`prompt`, single `embedding`) superseded |
| vLLM | `/v1/embeddings` OpenAI-compatible ("Only applicable to embedding models"); `/pooling` for raw pooling output | Multimodal and `truncate_prompt_tokens` on embeddings *unverified* |
| TEI (HF text-embeddings-inference) | `/embed`: `inputs`, `normalize` (default `true`), `truncate`, `truncation_direction`, `prompt_name`, `dimensions`; `/v1/embeddings`: `input`, `model`, `encoding_format` (`float`/`base64`), `dimensions`, `user` → `object`, `data[]{object, embedding, index}`, `model`, `usage{prompt_tokens, total_tokens}`; `/embed_sparse` (SPLADE `index`/`value` pairs); `/embed_all` (token-level, no pooling) | 424 when the loaded model does not match the route |

### 1.11 Local in-process peer — sentence-transformers / ONNX

`SentenceTransformer.encode(inputs, prompt_name=None, prompt=None, batch_size=32,
output_value="sentence_embedding", precision="float32" | "int8" | "uint8" |
"binary" | "ubinary", convert_to_numpy=True, normalize_embeddings=False,
truncate_dim=None, ...)` plus `encode_query` (uses the `"query"` prompt and
routes task `"query"`) and `encode_document` (first of `"document"`, `"passage"`,
`"corpus"`). The constructor takes `backend` (torch / ONNX / OpenVINO),
`truncate_dim`, `prompts`, and `default_prompt_name`. No usage is produced. This
is the `route=None` / `host="in-process"` adapter that must return the same
`CallResult[EmbeddingResponse]` as the remote ones (§11 step 4).

## 2. Cross-provider comparison

| Provider / interface | Task hint | Dims knob | Allowed dims | Output dtypes | Multi-dtype per call | Normalize knob | Truncate knob | Modalities | Batch per call | Usage field |
|---|---|---|---|---|---|---|---|---|---|---|
| OpenAI `/v1/embeddings` | — | `dimensions` | any ≤ model | float (or base64 transport) | no | — (always unit norm) | — (400 on overflow) | text, token ids | 2048 / 300K tok | `usage.prompt_tokens` |
| Azure OpenAI | — | `dimensions` | same | same | no | — | — | text | 2048 / 300K | same |
| Voyage `/v1/embeddings` | `input_type` query/document | `output_dimension` | {256, 512, 1024, 2048} | float, int8, uint8, binary, ubinary | no | — | `truncation` bool | text | 1000 / 120K–1M tok | `usage.total_tokens` |
| Voyage multimodal | `input_type` | — | 1024 | float | no | — | `truncation` | text, image, video | 1000 / 320K | `text_tokens`, `image_pixels`, `video_pixels` |
| Cohere `/v2/embed` | `input_type` (required, 5 values) | `output_dimension` | {256, 512, (768), 1024, 1536, (2048)} | float, int8, uint8, binary, ubinary, base64 | **yes** (`embedding_types` list) | — | `truncate` NONE/START/END + `max_tokens` | text, image, mixed | 96 | `meta.billed_units.input_tokens`, `.images` |
| Jina `/v1/embeddings` | `task` (5 values / adapters) | `dimensions` | Matryoshka ≥ 32 | float, binary, base64 | no | `normalized` | `truncate` bool | text, image, audio, video, pdf (model-dependent) | not stated | `usage` (token counts) |
| Gemini `embedContent` | `taskType` (001 only; prefix text on v2) | `outputDimensionality` | 128–3072 | float | no | — (v2 auto-normalizes) | — | text (+ image/audio/video/pdf on v2) | 1 (batch route) | `usageMetadata.promptTokenCount` |
| Vertex `:predict` | `task_type` (8 values) | `outputDimensionality` | ≤ 768 / 3072 | float | no | — | `autoTruncate` bool | text | 5 (1 for gemini-embedding-001) | `statistics.token_count` per instance |
| Mistral | — | `output_dimension` | ≤ 3072 (codestral) | float, int8, uint8, binary, ubinary | no | — | — | text | not stated | `usage.prompt_tokens` |
| Nomic | `task_type` (4 values) | `dimensionality` | ≤ 768 (v1.5) | float | no | — | `long_text_mode` truncate/mean | text | not stated | `usage.prompt_tokens` |
| Titan V2 | — | `dimensions` | {256, 512, 1024} | float, binary | **yes** (`embeddingTypes`) | `normalize` | — | text | **1** | `inputTextTokenCount` |
| Nova | `embeddingPurpose` (9 values) | `embeddingDimension` | {256, 384, 1024, 3072} | float | no | — | `truncationMode` START/END/NONE | text, image, audio, video | **1** | none |
| TEI / HF `/embed` | `prompt_name` | `dimensions` | model | float | no | `normalize` | `truncate` + direction | text | list | none (`/v1/embeddings` adds `usage`) |
| Ollama `/api/embed` | — | `dimensions` | model | float | no | — | `truncate` bool | text (+image/audio objects) | list | `prompt_eval_count` |
| sentence-transformers | `prompt_name` / `encode_query` | `truncate_dim` | model | float32, int8, uint8, binary, ubinary | no | `normalize_embeddings` | model max_seq_length | text (+ image for CLIP-style) | in-process | none |

## 3. Canonical IR proposal

The existing provisional types are a good skeleton. The survey shows they are
missing four request knobs and one response law, all additive.

### 3.1 Request — what must be first-class (three-lane admission)

| Knob | Lane | Verdict and rationale |
|---|---|---|
| `inputs: list[Document]` | 1 (exists) | Keep. Widen `Document.content` to `str \| Source \| list[str \| Source]` (ordered parts) so Cohere `inputs[].content[]`, Voyage multimodal `content[]`, Gemini `parts`, and Jina typed objects map directly. Providers that accept exactly one part per input (Nova, Titan, OpenAI) report `UNSUPPORTED` on a multi-part document — never a silent concatenation. The `Source` union is reused as-is: `SourceBase64` → data URI / `image_base64`; `SourceUrl` → `image_url` / Nova `s3Location`; `SourceRef` → `UNSUPPORTED` on crossing (rule 5) |
| `dimensions: int \| None` | 1 (exists) | Keep. Passes verbatim. A value outside the provider's allowed set is **not** clamped: it passes through and the report carries `APPROXIMATED` with the allowed set in the note (the provider will 400 — the user sees why). Absent support (`voyage-3`, Titan G1, `ada-002`, v3 Cohere) → `UNSUPPORTED`. Client-side truncate-and-renormalize is a **facade** option only, declared `SemanticShift(kind="emulation")` with `EMULATED` disposition — never silent, and the report notes whether renormalization was applied (Gemini `001` requires it, `gemini-embedding-2` and OpenAI do not) |
| `task: str \| None` **(new)** | 1 | Open code with canonical constants `retrieval.query`, `retrieval.document`, `classification`, `clustering`, `similarity`, `code.query`, plus a `task_native` lane preserving the provider's verbatim value (rule 6). Present on Voyage, Cohere, Jina, Vertex, Gemini-001, Nomic, Nova, sentence-transformers (8 interfaces) — clears the ≥2–3 bar. Destinations without the knob (OpenAI, Mistral, Titan) report `UNSUPPORTED` when it is set. Gemini-2's prompt-prefix convention and sentence-transformers' `prompt_name` are `EMULATED` with a `SemanticShift` (the model sees different text). Cohere's required `input_type` means an unset `task` on a Cohere route is itself a `SemanticShift` (codec default `search_document`, declared) |
| `dtype: str \| None` **(new)** | 1 | Open code mirroring `Embedding.dtype` (`float32`, `int8`, `uint8`, `binary`, `ubinary`). Voyage, Cohere, Mistral, Titan, Jina, sentence-transformers. Singular on purpose — see 3.2 for multi-encoding |
| `normalize: bool \| None` **(new)** | 1 | Titan `normalize`, TEI `normalize`, Jina `normalized`, Fireworks `normalize`, sentence-transformers `normalize_embeddings`. Where the provider always normalizes (OpenAI, Gemini-2) the `CapabilityProfile` states it and the response's `Embedding.normalized=True` is `EXACT`; `normalize=False` there is `UNSUPPORTED` |
| `truncate: str \| None` **(new)** | 1 | Open code `none` / `end` / `start`. Cohere (3 values), Nova (3 values), Voyage/Vertex/Jina/Ollama/TEI (bool → `end`), Nomic (`truncate`/`mean`), TEI `truncation_direction`. `start` is `UNSUPPORTED` on bool providers. `None` means provider default; because defaults disagree (Voyage/Vertex truncate, OpenAI errors) the codec records the effective default as a `SemanticShift(kind="default")` so a migration from Voyage to OpenAI shows why overflow now fails |
| `encoding_format: base64` | codec-internal | Transport compression, not meaning. The codec may request base64 and decode to floats; `raw` keeps the wire body. Not an IR field |
| `embedding_types` as a list (Cohere), `embeddingTypes` (Titan) | 2 | Censused extensions `cohere.embed/embedding_types`, `bedrock.titan/embeddingTypes`. Promotion trigger: a third interface returning several encodings per call |
| `late_chunking` (Jina) | 2 | `jina.embeddings/late_chunking`. Voyage's contextualized endpoint has a different shape (list of lists) and is a **separate interface** `voyage/contextualized_embeddings` with shape `embedding.contextual.request` — deferred, not an extension |
| Multi-vector / ColBERT output (Jina v4 `output_type`, TEI `/embed_all`) | excluded | Does not fit `Vector = list[float]`. Recorded exclusion; promotion trigger: a second provider with a public multi-vector API and a consumer (a late-interaction vectorstore port) |
| `max_tokens` (Cohere), `long_text_mode: mean` (Nomic), `priority`, `metadata` (Mistral), `prompt_template`/`return_logits` (Fireworks), `detailLevel`/`embeddingMode` (Nova), `title` (Google) | 2 or 3 | Censused extensions where they alter output (`google.embed/title`, `nova.embed/detailLevel`, `nomic.embed/long_text_mode`); pure routing preferences (`priority`, `keep_alive`, `options`) ride `provider_options["<destination>"]` |
| Token-id inputs (OpenAI arrays of ints) | 3 | `provider_options["openai.embeddings"]` only; never portable |

### 3.2 Response — laws the current types need

1. **`(index, dtype)` is the unique key, not `index` alone.** Cohere and
   Titan return several encodings of one input in one call. Keep
   `EmbeddingResponse.embeddings: list[Embedding]` and relax the docstring
   from "one per input" to "one per (input, dtype)"; conformance asserts
   uniqueness of the pair. This is additive and keeps `Embedding` flat.
2. **`Embedding.dtype` default stays `float32`**; providers that return ints
   for `int8`/`binary` serialize ints (already documented). `binary`/`ubinary`
   vectors are bit-packed int8/uint8 arrays — the `dimensions` property then
   reports packed length, so add `Embedding.bit_width: int | None`
   (*additive*; `None` for float) or document the packing. Recommended:
   document the packing in the schema and leave the type alone until a
   consumer needs it.
3. **`Embedding.normalized`** stays; codecs fill it from profile facts
   (OpenAI, Gemini-2: `True`; Titan: `normalize` echo; others `None`).
4. **`EmbeddingResponse.model`** stays (every provider echoes or implies it).
5. **Nova's `embeddingType` and `truncatedCharLength`**, Vertex's
   `statistics.truncated`, Cohere's `images[]{width,…}` → `Embedding.extensions`
   under censused keys (`nova.embed/embedding_type`, `google.embed/truncated`,
   `cohere.embed/image_info`). Vertex `truncated=true` is also surfaced as a
   `SemanticShift(kind="truncation")` on the report, because the vector no
   longer represents the full input.

### 3.3 Usage through core `Consumption`

| Wire field | `Consumption` |
|---|---|
| OpenAI/Azure/Mistral/Nomic/Fireworks/TEI `usage.prompt_tokens` | `(modality=text, unit=tokens, source=input)`; `total_tokens` is derived and must equal it (normalization rule) |
| Voyage `usage.total_tokens` | same (Voyage has no output bucket) |
| Voyage multimodal `text_tokens`, `image_pixels`, `video_pixels` | three records: `(text, tokens, input)`, `(image, "pixels", input)`, `(video, "pixels", input)` — `pixels` is a new open `UsageUnit` code; the 560-px/token conversion is **not** applied by ocai (that would be a silent approximation) |
| Cohere `billed_units.input_tokens`, `billed_units.images` | `(text, tokens, input)` and `(image, "images", input)` |
| Gemini `usageMetadata.promptTokenCount`, Vertex `statistics.token_count` (per instance, summed by the codec with a note) | `(text, tokens, input)` |
| Titan `inputTextTokenCount`, Ollama `prompt_eval_count` | `(text, tokens, input)` |
| Nova, HF Inference, sentence-transformers | no record; `CallResult.usage=None` — honest absence, never a tokenizer estimate |

### 3.4 Semantic shifts to declare per edge

| Shift | Where |
|---|---|
| `task` rendered as a text prefix | Gemini `gemini-embedding-2`, sentence-transformers prompts, Nomic/v2-moe prefixes |
| Required `input_type` defaulted by codec | Cohere |
| Provider truncation default applied (`truncate=None`) | Voyage, Vertex, Cohere, Nova, Ollama, TEI |
| Client-side dimension truncation ± renormalization | facade option, any provider |
| Batch fan-out: 1 logical request → N wire calls (Titan/Nova/Gemini-001 single input; OpenAI 2048; Cohere 96; Voyage 1000) | facade (§11 step 11), merging `usage` and `report`; partial failure surfaces as one error with the completed indices in the report |
| Multi-part document flattened to one modality | never — `UNSUPPORTED` instead |

### 3.5 Does the provisional `ocai.embedding` fit? Additive changes needed

| Type | Change | Kind |
|---|---|---|
| `EmbeddingRequest` | add `task`, `task_native`, `dtype`, `normalize`, `truncate` (all `None` default) | additive fields |
| `Document` | widen `content` to `str \| Source \| list[str \| Source]`; `from_dict` decodes list items through `cast_source` | additive widening |
| `Embedding` | docstring/schema: `(index, dtype)` unique; document bit-packing for `binary`/`ubinary` | law + schema, no field change |
| `EmbeddingResponse` | none | — |
| `EmbeddingModel` port | none (`embed`/`aembed` with `ctx` already match §11 step 4) | — |
| Identity | mint `Capability("embedding")` shapes `embedding.request` / `embedding.response` at `ocai@<rev>`; a later `embedding.contextual.request` for Voyage contextualized | §11 step 1 and 5 |
| `spec/` | `embedding.request.schema.json`, `embedding.response.schema.json`, `document.schema.json`, extension schemas listed in 3.1, golden fixtures per edge | §11 step 10 |
| Core | new open codes only: `UsageUnit.PIXELS`, `UsageUnit.IMAGES` constants (open strings, no release needed) | additive constants |

The `Document` hoist-or-duplicate decision deferred in architecture §2.8 is
forced by rerank (see `rerank.md` §3): rerank needs the same `Document` and
cannot import `ocai.embedding`, so `Document` moves to `ocai.core` when
rerank lands; embeddings should anticipate that by not adding
embedding-specific fields to `Document`.

## 4. Priority, effort, and the H3 recommendation

| Provider / interface | Priority | Effort | Why |
|---|---|---|---|
| `openai/embeddings` (OpenAI + Azure host) | **P0** | 1 WU codec + fragment + recorded pairs + fixtures; Azure host 0.5 WU | H3's named target; native batching, one dtype, `dimensions`, clean `usage`; exercises catalog/driver capability-neutrality with the fewest new knobs |
| In-process sentence-transformers adapter | **P0** (same milestone) | 1 WU | The port-plane peer proof; also the only way to test `dtype`/`normalize`/`task` without live keys |
| IR revision (3.5 changes) + `spec/` schemas | **P0** (first) | 1 WU | Must precede the first edge so fixtures are born against the final shape |
| `voyage/embeddings` | P1 | 1 WU | Stress-tests `task`, `dtype`, `dimensions`, `truncate` in one small dialect; 4-series shared space is a nice profile fact |
| `cohere/embed` | P1 | 1.5 WU | Multi-encoding response law, multimodal `inputs`, required `input_type` shift, images billing |
| OpenAI-compatible hosts (Together, Fireworks, vLLM, TEI `/v1/embeddings`, Ollama `/v1/embeddings`) | P1 | 0.5 WU each (host + `DialectTraits` + one recorded pair) | Same codec; Fireworks' `normalize`/`prompt_template` become censused extensions |
| `google/embed_content` (Gemini) | P2 | 1 WU | `taskType` removal on `gemini-embedding-2` is a textbook interface-revision shift; multimodal parts |
| `google/vertex_predict` | P2 | 1 WU | Different envelope (`instances`/`predictions`), per-instance statistics, OAuth host |
| `mistral/embeddings` | P2 | 0.5 WU | OpenAI shape plus `output_dtype`/`output_dimension` |
| `jina/embeddings` | P2 | 1 WU | `task` adapters, `late_chunking` extension, multi-vector exclusion recorded; schema gaps need a recorded pair before fixtures |
| `bedrock/titan_embed` | P2 | 1 WU (+ SigV4 host) | Single-input fan-out, `embeddingsByType` multi-dtype, RPM throttling |
| `bedrock/nova_embed` | P2 | 1.5 WU | Four modalities, one-of input, no usage, async segmented path as a `jobs` candidate (H6) |
| `nomic/embed_text`, `ollama/embed` (native), `tei/embed` (native), HF Inference `feature-extraction` | P3 | 0.5 WU each | Small dialects; mostly local/dev value |
| Mixedbread embeddings | P3 / skip | — | Standalone embedding/rerank API reference pages withdrawn (see `rerank.md`); open weights served via TEI/vLLM instead |

**Recommended first remote interface for H3: `openai/embeddings`.** It is the
interface the horizon already names; it has the smallest honest surface (no
task, one dtype, native batching, exact usage) so the first `CallResult`
through the catalog/driver proves the harness is capability-neutral rather
than debugging knob conversion; the Azure host variant then proves hosting
composition for free; and every OpenAI-compatible open-weights host (Together,
Fireworks, vLLM, TEI, Ollama) reuses the codec, which makes the local-vs-remote
peer claim testable with recorded pairs only. Voyage should be second, because
it is the smallest dialect that exercises all four new request knobs.

## Sources

Read 2026-11-10.

- https://developers.openai.com/api/reference/resources/embeddings/methods/create
- https://developers.openai.com/api/docs/guides/embeddings
- https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/embeddings
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/reference
- https://docs.voyageai.com/reference/embeddings-api
- https://docs.voyageai.com/docs/embeddings
- https://docs.voyageai.com/reference/multimodal-embeddings-api
- https://docs.voyageai.com/reference/contextualized-embeddings-api
- https://docs.cohere.com/reference/embed
- https://docs.cohere.com/docs/cohere-embed
- https://jina.ai/embeddings
- https://jina.ai/models/jina-embeddings-v3/
- https://jina.ai/models/jina-embeddings-v4/
- https://jina.ai/models/jina-embeddings-v5-text-small/
- https://aistudio.google.com/docs/embeddings
- https://aistudio.google.com/api-reference/embeddings
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/text-embeddings-api
- https://docs.mistral.ai/api/endpoint/embeddings
- https://docs.mistral.ai/inference/embeddings/code_embeddings
- https://docs.nomic.ai/reference/api/embed-text-v-1-embedding-text-post
- https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe
- https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-titan-embed-text.html
- https://docs.aws.amazon.com/nova/latest/userguide/embeddings-schema.html
- https://docs.together.ai/reference/embeddings
- https://docs.fireworks.ai/api-reference/creates-an-embedding-vector-representing-the-input-text
- https://huggingface.co/docs/inference-providers/tasks/feature-extraction
- https://github.com/ollama/ollama/blob/main/docs/api.md
- https://docs.ollama.com/api/openai-compatibility
- https://docs.vllm.ai/en/latest/serving/online_serving/
- https://huggingface.github.io/text-embeddings-inference/openapi.json
- https://github.com/huggingface/text-embeddings-inference/blob/main/README.md
- https://sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html
