# Document understanding / OCR — capability research

**Currency:** researched 2026-11-10 against official documentation; vendor
pricing and limits move monthly, so every number below is a snapshot. Items
marked *unverified* were seen only in third-party sources or were not
re-confirmed on the vendor page on the read date.

## 1. Scope and the baseline that is *not* a capability

Two things get called "document understanding":

1. **Provider-native document ingestion inside chat** — a PDF (or Office
   file) is a `PartDocument` in a chat request and the model reads it. This is
   already the chat capability (architecture §3.1, `PartImage/Audio/Video/
   Document` over the `Source` union). Only edge census work is needed; the
   three big chat interfaces differ in part shape and limits:

   | Interface | Part shape | Limits (read date) | Notes |
   |---|---|---|---|
   | OpenAI `/responses` | `input_file` with `file_id` \| `file_data` (data URL) \| `file_url`, `filename`, `detail: auto\|low\|high` | each file and request total under 50 MB; no page-count limit stated | Chat Completions accepts a `file` part, PDF only, no `file_url`. Text and page images are both fed to vision-capable models. |
   | Anthropic Messages | `{"type":"document","source":{"type":"base64"\|"url"\|"file","media_type":"application/pdf",...},"title","context","citations":{"enabled":bool}}` | 600 pages per request (100 when the context window is under 1M tokens); each page costs roughly 1,500–3,000 text tokens plus the page image | `file_id` sources need the Files API; Bedrock and Google-managed hosting accept base64 only. |
   | Gemini | `document` block with `data` (base64) or `uri` (Files API) and `mime_type` | up to 50 MB or 1,000 pages per PDF, inline or via Files API; 258 tokens per page; Files kept 48 hours | Office/OpenDocument types accepted; TXT/MD/HTML are text-extracted only. The read-date page documents the Interactions API `document` block; the older `inline_data`/`file_data` names were not on it (*unverified* whether both remain). |

2. **Standalone parse/OCR services** — an endpoint returns structure
   (markdown, blocks, tables, figures, bboxes) with no generation step. This
   is the candidate capability and the subject of the rest of the page.

## 2. Provider-by-provider

### 2.1 Mistral OCR (`POST /v1/ocr`)

- **Auth:** `Authorization: Bearer`. **Model:** `mistral-ocr-latest` (alias);
  dated models e.g. `mistral-ocr-2512` (OCR 3); OCR 4 and 4.1 shipped mid-2026
  and gate newer fields (`include_blocks` needs OCR 4+, `table_format` and
  `extract_header/footer` need OCR 2512+).
- **Input:** `document` is a tagged object: `{"type":"document_url","document_url":...}`
  or `{"type":"image_url","image_url":...}`; the reference also names a
  `FileChunk` variant for uploaded files (fields *unverified*). Formats: PDF,
  PPTX, DOCX, PNG, JPEG, AVIF and more.
- **Sync** single call. `pages` selects pages (0-based, `"0,2-4"` or array).
- **Knobs:** `include_image_base64`, `image_limit`, `image_min_size`,
  `table_format: markdown|html`, `extract_header`, `extract_footer`,
  `include_blocks`, `confidence_scores_granularity: word|page|block`,
  `bbox_annotation_format` / `document_annotation_format` (JSON-schema
  formats; a vision LLM annotates each figure bbox, and the document
  annotation sees the markdown plus the first eight image bboxes),
  `document_annotation_prompt`.
- **Output:** `pages[] {index, markdown, images[] {id, top_left_x, top_left_y,
  bottom_right_x, bottom_right_y, image_base64}, dimensions {dpi, height,
  width}, tables, hyperlinks, header, footer, confidence_scores, blocks[]
  {type, top_left_x, top_left_y, bottom_right_x, bottom_right_y, content}}`,
  `model`, `document_annotation` (JSON string), `usage_info {pages_processed,
  doc_size_bytes}`. Images are placeholders `![img-0.jpeg](img-0.jpeg)` in
  markdown. Coordinates are pixel corners against `dimensions`.
- **Pricing unit:** pages. OCR 3 model card: $2 / 1,000 pages, $3 / 1,000
  annotated pages; OCR 4 ≈ $4 / 1,000 (third-party, *unverified*). Batch via
  `/v1/batch`. No OCR-specific error vocabulary; page/size caps not stated.

### 2.2 Azure Document Intelligence (`prebuilt-layout`, `prebuilt-read`)

- **Endpoint:** `POST {endpoint}/documentintelligence/documentModels/{modelId}:analyze?_overload=analyzeDocument&api-version=2024-11-30`
  with query `pages` ("1-3,5"), `locale`, `stringIndexType`
  (`textElements|unicodeCodePoint|utf16CodeUnit`), `features[]`
  (`ocrHighResolution, languages, barcodes, formulas, keyValuePairs, styleFont,
  queryFields`), `queryFields`, `outputContentFormat: text|markdown`,
  `output: pdf|figures`.
- **Auth:** `Ocp-Apim-Subscription-Key` or OAuth2 bearer.
- **Input:** JSON body `{"urlSource": ...}` or `{"base64Source": ...}`.
- **Async job:** `202 Accepted` + `Operation-Location` + `Retry-After`; poll the
  `.../analyzeResults/{resultId}?api-version=...` URL (status vocabulary
  `notStarted|running|succeeded|failed` — *unverified* on the read date).
  Cropped figures at `/analyzeResults/{resultId}/figures/{figureId}` when
  `output=figures`.
- **Output (`analyzeResult`):** top-level `content` (plain text or markdown;
  v4.0 markdown renders tables as HTML and selection marks as ☒/☐),
  `pages[] {pageNumber, angle, width, height, unit, words, lines,
  selectionMarks, spans}`, `paragraphs[] {role, content, boundingRegions[]
  {pageNumber, polygon}, spans[] {offset, length}}` (roles: title,
  sectionHeading, pageHeader, pageFooter, pageNumber, footnote, formulaBlock),
  `tables[] {rowCount, columnCount, cells[] {kind, rowIndex, columnIndex,
  rowSpan, columnSpan, content, boundingRegions, spans}}`, `figures[] {id,
  boundingRegions, spans, elements, caption}`, `sections[] {spans, elements}`,
  `keyValuePairs`. Every element points back into `content` by span.
- **Limits:** PDFs/TIFFs up to 2,000 pages; 500 MB (S0) / 4 MB (F0); free tier
  processes only the first two pages. DOCX/HTML count one page unit per 3,000
  characters.
- **Pricing unit:** pages. Third-party trackers: Read ≈ $1.50 / 1,000, Layout
  ≈ $10 / 1,000 (*unverified*; the official pricing page rendered without
  figures on the read date).
- **Errors:** `DocumentIntelligenceErrorResponse {error {code, message,
  target, details[], innererror}}`.

### 2.3 Google Document AI — Layout Parser

- **Endpoint:** `projects/{p}/locations/{l}/processors/{id}:process` and
  `:batchProcess` (GCS in/out) — path *unverified* on the read date. Versions
  `pretrained-layout-parser-v1.0-2024-06-03` (stable) to `v3.1-lite` preview.
- **Input:** `rawDocument {content, mimeType}` or `gcsDocument`; online limit
  20 MB and 15 pages per PDF; batch 1 GB and 500 pages. MIME: PDF, HTML, DOCX,
  PPTX, XLSX, XLSM.
- **Chunking is a request option:** `processOptions.layoutConfig.chunkingConfig
  {chunkSize, includeAncestorHeadings}` (field names from the reference,
  *unverified* on the read date).
- **Output (`Document` proto):** `documentLayout.blocks[] {blockId, pageSpan
  {pageStart, pageEnd}, boundingBox, textBlock {text, type, blocks, annotations}
  | tableBlock {headerRows, bodyRows, caption, annotations} | listBlock
  {listEntries, type} | imageBlock}` — a *tree* (text blocks nest), and
  `chunkedDocument.chunks[] {chunkId, sourceBlockIds, content, pageSpan,
  pageHeaders, pageFooters, chunkFields}`. OCR processors instead fill
  `pages[] {pageNumber, dimension, layout {textAnchor, confidence, boundingPoly
  {vertices, normalizedVertices}, orientation}, blocks, paragraphs, lines,
  tokens, tables {headerRows, bodyRows}, formFields, visualElements}` anchored
  into the flat `text`.
- **Pricing unit:** pages. Layout Parser $10 / 1,000 pages (includes
  chunking); Enterprise Document OCR $1.50 / 1,000 for the first 5M then
  $0.60 (localized official pages; *unverified* on the English page).
- **Async:** `:batchProcess` returns a long-running operation to poll.

### 2.4 AWS Textract

- **Sync:** `AnalyzeDocument` (`FeatureTypes: TABLES|FORMS|QUERIES|SIGNATURES|LAYOUT`,
  `QueriesConfig.Queries[] {Text, Alias, Pages}`), `DetectDocumentText`.
  **Async:** `StartDocumentAnalysis` → `JobId`, `GetDocumentAnalysis` paginated
  by `NextToken` (shape not re-read; *unverified*).
- **Input:** `Document {Bytes | S3Object {Bucket, Name, Version}}`; JPEG, PNG,
  PDF, TIFF; 10 MB sync, 500 MB PDF async. Auth: SigV4.
- **Output:** flat `Blocks[] {BlockType, Id, Page, Text, Confidence,
  Geometry {BoundingBox {Left, Top, Width, Height}, Polygon[] {X, Y}},
  Relationships[] {Type, Ids[]}, RowIndex, ColumnIndex, RowSpan, ColumnSpan,
  EntityTypes, SelectionStatus, Query}`; BlockTypes `PAGE, LINE, WORD, TABLE,
  CELL, KEY_VALUE_SET, SELECTION_ELEMENT, SIGNATURE, QUERY, QUERY_RESULT,
  LAYOUT_*`; `DocumentMetadata.Pages`. Coordinates are page-size ratios. No
  markdown; reading order only via `LAYOUT`.
- **Errors (typed):** `BadDocumentException`, `DocumentTooLargeException`,
  `UnsupportedDocumentException`, `InvalidParameterException`,
  `ProvisionedThroughputExceededException` (400), `ThrottlingException` (500).
- **Pricing unit:** pages per feature; third-party figures conflict 3×
  (*unverified*).

### 2.5 Reducto (`POST https://platform.reducto.ai/parse`)

- **Auth:** bearer. **Input:** `input` = public/presigned URL, `reducto://`
  upload id, `jobid://` reference, or list of URLs (v3).
- **Options:** `settings.model: r-1|r-1-mini|legacy` (r-1 default from
  2026-12-07), `retrieval.chunking {chunk_mode, chunk_size, chunk_overlap}`,
  `formatting.table_output_format: dynamic|html|json|md|jsonbbox|csv`,
  `page_range`, `return_images`, `return_citations`, `timeout`. Async: same
  body with `async {webhook, priority}` → `{job_id}`; otherwise sync.
- **Output:** `result.type: full|url` (url + `result_id` when too large);
  `chunks[] {content, embed, enriched, blocks[] {type: Header|Footer|Title|
  Section Header|Page Number|List Item|Figure|Table|Key Value|Text|Comment|
  Signature, bbox {left, top, width, height, page, original_page}, content,
  confidence: low|high, image_url, chart_data}}`; `usage {num_pages, credits}`,
  `credit_breakdown`, `document_properties`.
- **Pricing:** $10 / 1,000 pages r-1 Parse, $1 / 1,000 r-1 mini, $20 / 1,000
  Extract (official pricing page; effective date not stated).
- **Errors:** 422 validation `{detail[] {loc, msg, type}}`; others undocumented.

### 2.6 LlamaParse (LlamaCloud, API v2)

- `POST /api/v2/parse/upload` (multipart `file` + `configuration` JSON),
  `POST /api/v2/parse` (`file_id` | `source_url`, `tier`, `version`,
  `page_ranges`, `output_options`), `GET /api/v2/parse/{job_id}?expand=
  markdown,text,items,metadata,forms,usage,markdown_full,…`; bearer auth.
- **Job:** `job.status` `PENDING|RUNNING|COMPLETED|FAILED|CANCELLED`;
  `job.usage.credits` (null until billed). Tiers `fast` (text only on older
  versions), `cost_effective`, `agentic`, `agentic_plus` = 1 / 3 / 10 / 45
  credits per page; ≈ $1.25 per 1,000 credits (third-party, *unverified*).
- **Output:** per-page markdown objects plus a full-document string, `items`
  (typed blocks with bounding boxes; schema *unverified*), `metadata`
  (per-page confidence). v1 `/api/parsing/job/{id}/result/*` is legacy.

### 2.7 Unstructured Partition API (legacy endpoint)

- `POST https://api.unstructuredapp.io/general/v0/general`, header
  `unstructured-api-key`, multipart `files`, `strategy` (`auto|fast|hi_res|
  ocr_only|vlm`), `vlm_model_provider`, `vlm_model`, `output_format`,
  chunking/coordinates flags. Sync; the vendor now steers users to Pipelines.
- **Output:** flat `[{type, element_id, text, metadata {page_number,
  coordinates {points, system}, text_as_html, parent_id, filetype, languages,
  image_base64, image_mime_type, detection_class_prob}}]`; types `Title,
  NarrativeText, Table, Image, ListItem, Header, Footer, PageBreak,
  FigureCaption, Formula, Address, EmailAddress, CodeSnippet,
  UncategorizedText, PageNumber, CompositeElement`. Polygon points run
  counter-clockwise from top-left. Billed per page (other files per 100 KB).

### 2.8 Upstage Document Parse

- **Endpoint:** `POST https://api.upstage.ai/v1/document-digitization`, bearer
  auth, multipart `document`, `model: document-parse`, `mode: standard|
  enhanced|auto`, `ocr: auto|force`, `output_formats: ["html","markdown","text"]`,
  `coordinates` (default true), `base64_encoding: ["table", ...]`,
  `chart_recognition`, `merge_multipage_tables`, `words`, `dpi`.
- Sync up to 100 pages; async API up to 2,000 pages via a request id (path
  *unverified*).
- **Output:** `api`, `model`, `content {html, markdown, text}`, `elements[]
  {id, page, category (heading1, paragraph, list, table, figure, chart,
  caption, equation, header, footer, footnote, index), coordinates[] {x, y}
  (normalized 0–1), content {html, markdown, text}, base64_encoding}`,
  `usage {pages, standard[], enhanced[]}`.
- **Pricing:** $0.01 / page standard, $0.03 / page enhanced (third-party and
  marketplace listings; *unverified*).

### 2.9 Datalab (Marker) — `POST https://www.datalab.to/api/v1/convert`

- **Auth:** `X-API-Key`. Multipart `file` or `file_url`; `mode: lite|fast|
  balanced|accurate`; `output_format: markdown|html|json|chunks`; `paginate`,
  `max_pages`, `page_range`, `disable_image_extraction`, `add_block_ids`,
  `word_bboxes`, `merge_cross_page` (≈ $0.50/document surcharge),
  `webhook_url`. `/api/v1/marker` is deprecated in favour of `/convert`.
- **Job:** returns `{request_id, request_check_url, success, error}`; poll
  `GET /api/v1/marker/{request_id}` → `status` ("complete"), `progress_percent`,
  `markdown|html|json`, `images` (filename → base64), `metadata`,
  `page_count`, `result_url` + `expires_in`, `cost_breakdown`.
- **Pricing:** per page; older third-party figures $4–$6 / 1,000 (*unverified*).

### 2.10 Chunkr — `POST https://api.chunkr.ai/tasks/parse`

- The docs show both `/tasks/parse` and `/api/v1/tasks/parse` (*unverified*
  which is canonical). Auth header `Authorization` (raw API key).
- **Input:** `file` = `ch://files/{file_id}`, URL, or base64;
  `chunk_processing {target_length, tokenizer}`, `segment_processing` per
  segment type `{format: Html|Markdown, strategy: LLM|Auto|Ignore, crop_image:
  All|Auto}`, `ocr_strategy: All|Auto`, `segmentation_strategy:
  LayoutAnalysis|Page`, `error_handling: Fail|Continue`, `expires_in`.
- **Job:** `task_id`, `status: Starting|Processing|Succeeded|Failed|Cancelled`,
  `completed`, `file_info {page_count, mime_type}`; poll the task.
- **Output:** `chunks[] {chunk_id, content, embed, segments[] {segment_id,
  segment_type (Title, SectionHeader, Text, Table, Picture, Caption, Formula,
  Footnote, ListItem, Page, PageHeader, PageFooter, PageNumber, FormRegion,
  GraphicalItem, Legend, LineNumber, Unknown), bbox {left, top, width,
  height}, page_number (1-based), page_width, page_height, content, image,
  confidence, ocr[]}}`, `pages[] {image, page_number, page_width,
  page_height, dpi}`. Errors 400/401/429/500; price per page or credit
  (*unverified*).

### 2.11 Docling (local, in-process peer) and docling-serve

- `DoclingDocument` (pydantic, `docling_core.types.doc`): `texts[]`,
  `tables[]`, `pictures[]`, `key_value_items[]` as `DocItem`s referenced by
  JSON pointer (`#/texts/1`); `body`/`furniture` trees give reading order;
  items carry `prov[] {page_no, bbox {l, t, r, b}, coord_origin, charspan}`
  (names from `docling_core`, *unverified* on the read date). Exports:
  markdown, dict, HTML, doctags.
- **docling-serve:** `POST /v1/convert/source|file` (+ `/async` twins),
  `GET /v1/status/poll/{task_id}`, `GET /v1/result/{task_id}`; `to_formats
  [md, json, html, text, doctags]`, `do_ocr`, `image_export_mode`,
  `table_mode: fast|accurate`; response `document {md_content, json_content,
  html_content, …}`, `status: success|partial_success|skipped|failure`.
- In-process it has no wire dialect: the §11 step 4 "local and remote are
  peers" case (`route=None` / `host="in-process"`).

## 3. Comparison

| Provider | Input | Sync / job | Markdown | Blocks + bbox | Tables | Figures | Reading order | Billing unit |
|---|---|---|---|---|---|---|---|---|
| Mistral OCR | url, image url, file id | sync | yes (per page) | `blocks[]` pixel corners (OCR 4+) | md/html in markdown; `tables` field | base64 crops + bbox | page markdown order | pages |
| Azure DI | url, base64 | job (202 + Operation-Location) | yes (`outputContentFormat`) | `paragraphs[]` polygons + spans | structured cells | `figures[]` + crops | `sections[]` tree + spans | pages |
| Google Doc AI Layout | raw bytes, GCS | sync ≤15 pp, batch ≤500 pp | no (blocks tree) | `documentLayout.blocks[]` tree | `tableBlock` rows | `imageBlock` | tree order | pages |
| AWS Textract | bytes, S3 | sync ≤10 MB, async job | no | flat `Blocks[]` ratios | `TABLE/CELL` blocks | no (LAYOUT_FIGURE only) | only with LAYOUT | pages × feature |
| Reducto | url, upload id | sync or async (webhook) | per block `content` | `blocks[]` bbox + page | md/html/json/csv | `image_url`, chart data | chunk order | pages / credits |
| LlamaParse v2 | upload, file id, url | job | yes | `items` (bbox) | md/html | images via expand | page order | credits per page × tier |
| Unstructured | multipart | sync (legacy) | no (elements) | elements + polygon points | `text_as_html` | base64 | element order | pages |
| Upstage | multipart | sync ≤100 pp, async ≤2,000 pp | yes (+html, text) | elements + normalized coords | html per element | base64 crops | element order | pages × mode |
| Datalab | multipart, url | job | yes (+html, json, chunks) | json blocks / `word_bboxes` | in markdown/html | base64 map | document order | pages |
| Chunkr | file ref, url, base64 | job | per segment (`format`) | segments + bbox + page size | html/markdown | crops | chunk/segment order | pages / credits |
| Docling | local file / docling-serve | in-process or job | yes | `prov[]` bbox | structured cells | pictures | `body` tree | none |

Dialects differ on every axis: input addressing, job vs sync, coordinate
system, block taxonomy, table representation, figure delivery, billing unit.

## 4. Canonical IR proposal — `document.parse`

**Identity.** `Capability("document")`, one operation `parse`, shapes
`("document", "parse.request")` and `("document", "parse.response")`; async
legs reuse the H6 `ocai.jobs` vocabulary (`Job`/`JobHandle`, one `Operation`
per leg, anchored by `ProviderRef(kind="job")`). Package `ocai.document`
imports `ocai.core` only.

**Request** (pure; no model/processor name — bound at the front door and
injected from `EndpointSpec.resource`, e.g. `"azure/prebuilt-layout"`,
`"mistral/mistral-ocr-latest"`, `"google/projects/p/locations/us/processors/x"`):

- `source: Source` — the core `base64 | url | SourceRef` union; provider file
  ids (Mistral, Chunkr `ch://`, Reducto `reducto://`) are `SourceRef`s scoped
  to `(provider, interface)`, `UNSUPPORTED`-and-reported on crossing.
- `pages: PageSelector | None` — 1-based ranges; codecs convert to 0-based
  (Mistral) or `"1-3,5"` strings (Azure) and declare the shift.
- `options: ParseOptions` — first-class by the three-lane law only where ≥3
  dialects agree: `ocr: auto|force|off`, `tables: structured|markdown|html`,
  `images: none|crop|page`, `want: {blocks, markdown, text}`. Everything
  else (`mode`/`tier`, chunking configs, annotation schemas, LLM enrichment,
  `dpi`, chart agents) rides `provider_options` or censused extensions.
  Chunking is explicitly *not* IR: by the §11 litmus it is built on ocai.

**Response `ParsedDocument`:**

- `pages[]: PageInfo(index, width, height, unit: pixel|point|normalized,
  rotation, dpi?)`.
- `blocks[]: Block(id, kind, text, native, prov[], parent_id?, confidence?,
  extensions)` in reading order. `kind` is an open code with canonical
  constants `title | section_header | paragraph | list_item | table | figure |
  caption | formula | header | footer | page_number | footnote | key_value |
  signature | unknown`; the provider's verbatim label rides `native`
  (Textract `LAYOUT_TITLE`, Azure `sectionHeading`, Unstructured
  `NarrativeText`, Chunkr `SectionHeader`, Reducto `"Section Header"`).
- `prov[]: Provenance(page, bbox: BBox(x0, y0, x1, y1, unit, origin:
  top_left|bottom_left), span: (offset, length)?)` — **coordinates pass
  verbatim** in the provider's unit and origin; `BBox.normalized(page)` is a
  read-side helper, never a codec rescale (rule 5). Polygons (Azure,
  Unstructured) collapse to their enclosing box with the polygon preserved in
  an extension; reported `APPROXIMATED`.
- `tables[]: Table(block_id, rows, cols, cells[] {row, col, row_span, col_span,
  text, is_header, bbox?}, markdown?, html?)`. Providers that only emit HTML
  (Upstage, Unstructured) yield `cells` as `ABSENT` and keep `html`; a cell
  grid parsed from HTML is an opt-in facade step reported `APPROXIMATED`.
- `figures[]: Figure(block_id, image: Source | None, caption?, description?)`
  — crops are `Source` (base64 or a provider `SourceRef`), never bespoke.
- `markdown: str | None`, `text: str | None` — provider-rendered whole-document
  views when offered; absence is reported, never synthesized silently.
- `extensions` — censused per provider (`document_annotation`, Chunkr chunks,
  Google `chunkedDocument`, Reducto `chart_data`, Azure `keyValuePairs`,
  Textract `QUERY_RESULT`).

`CallResult(value=ParsedDocument, route, report, usage=Consumption(pages=…,
credits=…), raw)`. Consumption dimension `pages` is an open-code unit per
§11 step 9; providers that bill credits report both.

**Declared loss (what the census will say):** block taxonomy mapping is a
`SemanticShift` per edge; confidence is `APPROXIMATED` where granularity
differs (page vs block vs word); hierarchy (`parent_id`) is `ABSENT` on flat
providers (Textract, Unstructured without chunking, Mistral); reading order is
`APPROXIMATED` on Textract without `LAYOUT`; Azure's 3,000-character DOCX
"page" is a `SemanticShift` on `pages`.

**Job pattern.** Azure, LlamaParse, Datalab, Chunkr, Textract-async, Reducto-
async, Upstage-async and docling-serve-async all follow submit → poll → fetch
with provider-specific status vocabularies. Each leg is its own `Operation`
returning its own `CallResult`/`Route`; the facade owns the polling fan-out and
declares it as a `SemanticShift`; `JobHandle` is a `ProviderRef(kind="job")`
with `Retry-After` honoured as data. Mistral and Unstructured are single-leg.

**Errors.** Size/page-cap overruns need a canonical code — `ContextLengthError`
is a token budget, the wrong shape — so propose an additive
`PayloadTooLargeError`. Throttling → `RateLimitError`; `Unsupported*`/422 →
`InvalidRequestError`; 5xx → `TransientError`.

## 5. Verdict, provider order, priority

- **Kernel capability: yes.** Eleven interfaces, one semantic operation,
  provider-varying request and response dialects with real conversion loss to
  report. The local peer (Docling) proves the in-process rule for free.
- **First provider: Mistral OCR** — single sync JSON call, bearer auth,
  markdown + blocks + bbox + image crops in one response, trivially recorded
  as a wire pair. **Second: Azure Document Intelligence** — exercises the job
  pattern, spans-into-content provenance, structured tables and figure crops,
  and is the enterprise default. **Third: Docling** as the in-process peer.
  Google Document AI and Textract follow (both add polygon/ratio coordinate
  variants and SigV4/OAuth hosting).
- **Priority: P1**, sequenced after H6 `ocai.jobs` and `files` land, because
  more than half the dialects are job-shaped and file-id-addressed. Do the
  Mistral edge first regardless (it needs neither).
- **Effort:** M for IR + Mistral + Docling; L through Azure, Google, Textract.

## 6. Unverified / open

Mistral OCR 4 price, page caps and `FileChunk` fields; Azure job status
vocabulary and list prices; Google `:process` path and `chunkingConfig`
names; Textract async shape and prices; LlamaParse `items` schema and credit
price; Chunkr canonical path and price; Datalab, Upstage, Unstructured list
prices; Docling `prov` field names.

## Sources (read 2026-11-10)

- https://docs.mistral.ai/api/endpoint/ocr
- https://docs.mistral.ai/capabilities/OCR/basic_ocr
- https://docs.mistral.ai/capabilities/OCR/annotations
- https://docs.mistral.ai/models/model-cards/ocr-3-25-12
- https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/layout
- https://learn.microsoft.com/en-us/rest/api/aiservices/document-models/analyze-document?view=rest-aiservices-v4.0%20(2024-11-30)
- https://docs.cloud.google.com/document-ai/docs/layout-parse-chunk
- https://docs.cloud.google.com/document-ai/docs/reference/rest/v1/Document
- https://cloud.google.com/document-ai/pricing
- https://docs.aws.amazon.com/textract/latest/dg/API_AnalyzeDocument.html
- https://docs.reducto.ai/api-reference/parse
- https://reducto.ai/pricing
- https://developers.llamaindex.ai/llamaparse/parse/guides/api-reference/
- https://developers.llamaindex.ai/llamaparse/general/pricing/
- https://docs.unstructured.io/api-reference/partition/overview
- https://docs.unstructured.io/api-reference/partition/document-elements
- https://console.upstage.ai/docs/capabilities/document-digitization/document-parsing
- https://console.upstage.ai/api/document-digitization/document-parsing
- https://documentation.datalab.to/api-reference/convert-document
- https://documentation.datalab.to/api-reference/marker-result-check
- https://docs.chunkr.ai/api-references/tasks/create-parse-task
- https://docling-project.github.io/docling/concepts/docling_document/
- https://github.com/docling-project/docling-serve/blob/main/docs/usage.md
- https://developers.openai.com/api/docs/guides/pdf-files
- https://platform.claude.com/docs/en/build-with-claude/pdf-support
- https://aistudio.google.com/docs/document-processing
