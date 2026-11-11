# Files and assets

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

**Currency.** Researched 2026-11-10 against the providers' current public
documentation (URLs in Sources). Provider file APIs change their limits and
retention rules often; every number below carries the date it was read.
Statements marked *unverified* could not be confirmed from an official page
during this pass and must be re-checked before an `EdgeContract` or fixture
relies on them.

**Scope.** Provider-hosted file storage whose handles are later referenced by
other capabilities (chat, embedding, batch, fine-tuning, OCR). This page does
not cover vector stores, container filesystems, or signed-download CDNs except
where they are the only way to get bytes back.

## Why this is a capability

`docs/architecture.md` §11 scope litmus: a thing with provider-varying wire
dialects is a capability. File upload has at least four dialects (OpenAI
multipart with `purpose`; Anthropic multipart with `expires_in_seconds`;
Gemini resumable upload with `X-Goog-Upload-*` headers; Mistral multipart
with `purpose` plus signed URLs) and two "no upload at all" models (Bedrock
and Vertex read object-store URIs). H6 lists files as the second
next-after-freeze capability, with the design rule already fixed: *upload
once, and the provider-scoped handle rides chat, embedding, or batch requests
under the scoped crossing rule* (§2.4).

## Provider survey

### OpenAI Files API and Uploads API

| Aspect | Observed (2026-11-10) |
|---|---|
| Upload | `POST /files`, `multipart/form-data` with `file`, `purpose`, optional `expires_after` (`anchor` = `created_at` only, `seconds` 3600–2592000) |
| Purposes accepted | `assistants`, `batch`, `fine-tune`, `vision`, `user_data`, `evals`; server-minted purposes seen on objects: `assistants_output`, `batch_output`, `fine-tune-results` |
| Id | string, `file-` prefix in all examples (format not contractually specified) |
| Limits | 512 MB per file; 2.5 TB per project; no org-wide cap; batch `.jsonl` input ≤ 200 MB; upload rate limit 1000 req/min per user |
| Expiry | `batch` files default to 30 days; other purposes persist until deleted; `expires_after` makes any file expire (1 h to 30 d) |
| Read back | `GET /files/{file_id}/content`; `DELETE /files/{file_id}` also removes the file from every vector store |
| Large files | Uploads API: `POST /uploads` (`bytes`, `filename`, `mime_type`, `purpose`, `expires_after`), `POST /uploads/{upload_id}/parts` (`data`, ≤ 64 MB per part, parallel allowed), `POST /uploads/{upload_id}/complete` (`part_ids`, optional `md5`), `POST /uploads/{upload_id}/cancel`; ≤ 8 GB total; an upload expires one hour after creation; statuses `pending`, `completed`, `cancelled`, `expired`; completion yields an ordinary file object (`status` `uploaded`/`processed`/`error`) |
| Consumption in chat | Responses API `input_file` item: `file_id` or `file_url` or inline `file_data` (data URL) + `filename`, optional `detail`; docs recommend `purpose=user_data`; 50 MB per file and per request. Chat Completions accepts a `file` content part with `file_id`/`file_data` for PDFs only, no `file_url`, no `detail` |
| Consumption elsewhere | batch input (`input_file_id`), fine-tuning (`training_file`, `validation_file`), vision fine-tuning images, evals |
| Deprecation signal | the Assistants API shuts down 2026-08-26 (already past); `purpose=assistants` survives only for file search/vector stores — treat as legacy |

Azure OpenAI exposes the same shape under its v1 data plane
(`POST {endpoint}/openai/v1/files`, `purpose=fine-tune` or `batch`), with
Azure-specific caps: 200 MB batch input (1 GB with bring-your-own Blob
Storage), 500 stored batch input files without expiration or 10,000 with
expiration, 100,000 requests per file. An Azure file id is a different
resource from an OpenAI file id even when the string looks alike; they never
cross. An import-from-URL variant exists in older Azure versions
(*unverified* for the v1 surface).

### Anthropic Files API

| Aspect | Observed (2026-11-10) |
|---|---|
| Status | out of beta; `anthropic-beta: files-api-2025-04-14` is optional and keeps the old list shape (`has_more`/`first_id`/`last_id`, `before_id`/`after_id`); without it the list is `{data, next_page}` with a `page` cursor or up to 100 `ids[]` |
| Upload | `POST /v1/files` multipart `file`, optional `expires_in_seconds` (3600 to 7,776,000 = 90 days, set once) |
| Id | `file_011CNha8iCJcU1wXNR6q4V8w` style |
| Object | `id`, `type: "file"`, `filename`, `mime_type`, `size_bytes`, `created_at`, `downloadable`, `expires_at` (`null` = never) |
| Limits | 500 MB per file; 1 TB per organization; ~500 file requests/min |
| Scope | **workspace**-scoped: any key with access to the workspace can read any file; the docs tell integrators to treat ids as server-side references and never accept them from end users |
| Read back | `GET /v1/files/{file_id}/content` only when `downloadable: true`, which is true only for files created by skills or the code execution tool; downloading an upload returns 400 |
| Expiry | after `expires_at`: content 404, Messages requests referencing it fail before inference, metadata stays listable for up to 30 days |
| Consumption in chat | `document` block with `source: {type: "file", file_id}` (PDF, `text/plain`), `image` block with the same source shape, `container_upload` block `{type: "container_upload", file_id}` for the code execution sandbox; generated files appear in `bash_code_execution_tool_result` blocks |
| Consumption elsewhere | Message Batches (each `params` is a Messages request, so file ids ride through); Managed Agents mount uploads at `/mnt/session/uploads` |
| Hosts | listed as available on the Claude API, Claude Platform on AWS, Claude Models on Google Cloud (Anthropic managed), and Microsoft Foundry (hosted on Anthropic). Whether one `file_id` is valid across those hosts is *unverified*; Bedrock-native and Google-managed Vertex deployments are not listed |
| Pricing | all file operations free; file content billed as input tokens when used |

### Gemini API Files API

| Aspect | Observed (2026-11-10) |
|---|---|
| Upload | resumable protocol: start with `X-Goog-Upload-Protocol: resumable`, `X-Goog-Upload-Command: start`, then `upload, finalize`; SDKs wrap it as `files.upload` |
| Resource | `name` = `files/{id}` (id ≤ 40 chars, lowercase alphanumerics and dashes); `displayName` ≤ 512; output-only `mimeType`, `sizeBytes`, `createTime`, `updateTime`, `expirationTime`, `sha256Hash`, `uri`, `downloadUri`, `state`, `source`, `error`, video metadata |
| States | `STATE_UNSPECIFIED`, `PROCESSING` (not usable yet), `ACTIVE`, `FAILED` — clients must poll until `ACTIVE` |
| Source | `UPLOADED`, `GENERATED`, `REGISTERED` (a Google Cloud Storage object registered via `POST /v1beta/files:register`) |
| Methods | `GET /v1beta/files/{file}`, `GET /v1beta/files` (`files[]`, `nextPageToken`), `DELETE /v1beta/files/{file}`, `POST /v1beta/files`, `files:register`; a download path exists for generated files (`files.download` in SDKs); user uploads cannot be downloaded |
| Limits | 2 GB per file; 20 GB per project; files auto-delete after 48 hours; free |
| When to use | docs say always use the Files API when total request size exceeds 100 MB; PDF limit 50 MB |
| Consumption | generation requests reference `uri` (`fileData {mimeType, fileUri}` in `generateContent`; the newer Interactions-style docs show `{type: "audio", uri, mime_type}` parts); batch mode accepts a JSONL input file uploaded through this API and writes output files |
| Vertex | the Vertex `generateContent` reference accepts `fileData.fileUri` as a `gs://` URI (publicly readable or same project), an `https://` URL ≤ 15 MiB, or a YouTube URL; inline parts up to 256 MB on Gemini 3+ (30/50/7 MiB on non-migrated 2.5 endpoints); whole request ≤ 500 MiB. Gemini API `files/…` URIs are not listed as accepted on Vertex (*unverified*, treat as not crossing) |

### Mistral Files API

| Aspect | Observed (2026-11-10) |
|---|---|
| Endpoints | `GET /v1/files`, `POST /v1/files`, `GET /v1/files/{file_id}`, `DELETE /v1/files/{file_id}`, `GET /v1/files/{file_id}/content`, `GET /v1/files/{file_id}/url` (signed URL, `expiry` 1–168 hours, default 24) |
| Purposes | `fine-tune`, `batch`, `ocr`, `agentic_safety` |
| Id | UUID-style in examples (`e85980c9-409e-4a46-9304-36588f6292b0`); format not stated |
| Object | `bytes`, `created_at`, `filename`, `mimetype`, `num_lines`, `sample_type` (`pretrain`, `instruct`, `batch_request`, `batch_result`, `batch_error`), `source` (`upload`, `repository`, `mistral`), `visibility` (`workspace`, `user`), `signature`, `expires_at`, `deleted` |
| Limits | 512 MB per file; fine-tuning accepts `.jsonl` only |
| Expiry | upload accepts `expiry`; `expires_at` returned; semantics beyond the signed URL are not documented (*unverified*) |

### Bedrock (no files API)

Bedrock has no provider file store. Converse `image`, `document` and `video`
blocks take `source.bytes` or `source.s3Location {uri, bucketOwner}`; the
caller's role needs `s3:GetObject`; `bucketOwner` is required when the bucket
belongs to another account; `format` is mandatory for documents; citations
disallow `s3Location` for documents. Batch inference and model customization
read `.jsonl` and referenced media from S3 as well (all linked resources must
sit under the configured input prefix). Per-modality size limits for S3
sources were not extracted on this pass (*unverified*).

### Summary table

| Provider | Upload style | Id form | Hard limits | Retention | Download of uploads |
|---|---|---|---|---|---|
| OpenAI | multipart; multipart Uploads API for > 512 MB (≤ 8 GB) | `file-…` | 512 MB/file, 2.5 TB/project | batch 30 d default; others until deleted; `expires_after` | yes (`/content`) |
| Azure OpenAI | multipart (v1) or BYOS Blob | `file-…` (separate namespace) | 200 MB batch (1 GB BYOS); 100k requests/file | per-file expiration | yes |
| Anthropic | multipart | `file_…` | 500 MB/file, 1 TB/org | until deleted or `expires_at` (1 h–90 d) | no (uploads 400); generated only |
| Gemini API | resumable | `files/{id}` + `uri` | 2 GB/file, 20 GB/project | 48 h fixed | no; generated only |
| Vertex | none (GCS) | `gs://…` | request 500 MiB; part 256 MB | GCS lifecycle | n/a |
| Mistral | multipart | UUID | 512 MB | `expires_at` (semantics unverified) | yes + signed URL |
| Bedrock | none (S3) | `s3://…` + `bucketOwner` | unverified | S3 lifecycle | n/a |

## ProviderRef scope table (which ids cross which capabilities)

This is the table that decides `ProviderRef.scope` (§2.4) for file handles.
"Yes" means the provider documents that capability consuming the id.

| Id | chat / generate | embedding | batch | fine-tune | OCR / other | Sibling interface (same provider) | Other host of same provider | Other provider |
|---|---|---|---|---|---|---|---|---|
| OpenAI `file-…` | Responses `input_file`; Chat Completions PDF part | no documented path | `input_file_id` (purpose `batch`) | `training_file` (purpose `fine-tune`), `vision` images | evals, vector stores | survives (`chat_completions` ↔ `responses` ↔ `batch`) — but **purpose gates use**: a `fine-tune` file is not accepted as `user_data` input (*unverified* whether rejected or tolerated) | Azure OpenAI: **no** | no |
| Anthropic `file_…` | `document`/`image`/`container_upload` | no | yes (via Messages params) | no fine-tuning product | code execution, Managed Agents | survives (`messages` ↔ `batches`) | Claude API ↔ Claude Platform on AWS / Foundry-hosted: *unverified* | no |
| Gemini `files/…` | `fileData.fileUri` | not documented | JSONL input/output file | tuning uses GCS, not Files API | video/audio understanding | survives (`generateContent` ↔ `batchGenerateContent`) | Vertex: **no** (GCS only) | no |
| Vertex `gs://` | `fileData.fileUri` | batch embeddings input | GCS JSONL | `trainingDatasetUri` | | survives across Vertex interfaces | Gemini API: only via `files:register` (REGISTERED source) | Bedrock `s3://`: no |
| Mistral UUID | no (chat uses `document_url`, so via signed URL) | no | `input_files` (purpose `batch`) | `training_files` (purpose `fine-tune`) | `ocr` purpose, `agentic_safety` | purpose-gated like OpenAI | n/a | no |
| Bedrock `s3://` | Converse blocks | no | batch input | customization datasets | | survives (`converse` ↔ `invoke_model` ↔ batch) | Bedrock in another region: same URI, IAM permitting | no |

Reading of the table:

1. Every provider file handle is **provider-scoped** (`RefScope.PROVIDER`),
   never interface-scoped: the same id is accepted by the chat interface and
   the batch interface of the same provider. This confirms the §2.4 example.
2. Two refinements §2.4 does not yet name. **Purpose** (OpenAI, Mistral) and
   **host** (Gemini API vs Vertex; Claude API vs cloud-hosted Claude) narrow
   validity below the provider. The existing `qualifier` field can carry
   both without a new scope constant: `qualifier="purpose=batch"` or
   `qualifier="host=vertex"`. The crossing check must then compare
   `(provider, qualifier)` for file refs, not `provider` alone. Decide this
   in the files WU, not later: it changes `EdgeContract` declarations.
3. Object-store URIs (`gs://`, `s3://`) are not file *handles*; they are
   `Source` values of a URI kind with a cloud scheme. They should decode to
   `SourceRef` with `provider="google-vertex"`/`"bedrock"` and the same
   provider scope; crossing to any other provider is `UNSUPPORTED`.

## Canonical proposal

Following the §11 recipe:

- **Identity.** `Capability("files")`, shapes `("files","upload.request")`,
  `("files","upload.response")`, `("files","get.request")`,
  `("files","get.response")`, `("files","delete.request")`,
  `("files","delete.response")`, `("files","list.request")`,
  `("files","list.response")`, and optionally `("files","download.request")`
  / `("files","download.response")` as a separate operation because three
  providers refuse it for uploads.
- **IR (`ocai.files`, imports core only).** `FileUpload(content: Source,
  filename, mime_type, purpose: str | None (open code), expires_in: int |
  None)`; `FileInfo(ref: SourceRef, filename, mime_type, size_bytes,
  created_at, expires_at, state: open code with canonical constants
  `PROCESSING`/`ACTIVE`/`FAILED` plus `native`, downloadable: bool | None,
  purpose, extensions)`. `FileInfo.ref` is the only output that other
  capabilities consume. No `model` field anywhere (§11 step 3).
- **Port.** `upload`, `get`, `delete`, `list`, `download`, each returning
  `CallResult[FileInfo | FileList | FileBytes | Deleted]` with `route`,
  `report`, `usage` (always `None` or zero-cost consumption: all surveyed
  providers bill nothing for file operations), `raw`.
- **Profile keys.** `files.upload`, `files.download.uploaded` (ABSENT on
  Anthropic and Gemini), `files.download.generated`, `files.expiry.custom`
  (NATIVE on OpenAI, Anthropic, Mistral; ABSENT on Gemini which is fixed
  48 h), `files.purpose` (NATIVE on OpenAI/Mistral; ABSENT elsewhere —
  purpose is then recorded as a `DROPPED` field in the report, never
  silently), `files.resumable` (NATIVE on Gemini and OpenAI Uploads).
- **Facade fan-out.** Resumable and multipart uploads are 1-logical-call →
  N-wire-calls; the facade owns it and declares the fan-out as a
  `SemanticShift` (§11 step 11). Gemini's `PROCESSING` → `ACTIVE` wait is a
  polling leg; model it through `ocai.jobs` (see batch-and-jobs.md) rather
  than a hidden sleep loop.
- **Honesty on crossing.** A `SourceRef` from provider A inside a chat
  request routed to provider B is `UNSUPPORTED`-and-reported; the facade
  may offer an explicit `rehost` helper (download + re-upload) but only when
  `files.download.uploaded` is NATIVE at A — which excludes Anthropic and
  Gemini uploads. That asymmetry is a product fact worth surfacing in the
  report text, not hiding.
- **Expiry as data.** `expires_at` rides `FileInfo` and is copied into the
  `SourceRef` (`qualifier` or a sibling field) so the planner can refuse to
  build a batch whose input file will expire before the 24 h window closes.
- **Spec.** `spec/schema/files.*.schema.json`, golden fixtures per provider
  edge, and one recorded multipart pair per provider (rule 10). Multipart
  bodies need a fixture convention (`record-wire-pair` skill) because the
  current recorded pairs are JSON-only.

## What is honestly UNSUPPORTED

- Any cross-provider or cross-host file reference (table above).
- Downloading user uploads on Anthropic and Gemini.
- Custom expiry on Gemini; purposes on Anthropic/Gemini.
- Converting an OpenAI `file_url` input into an Anthropic `document` block:
  Anthropic has a `url` source for documents but the fetch happens at
  Anthropic, so the conversion is a `SemanticShift` (who fetches, when), not
  a lossless mapping.
- Bedrock/Vertex object-store URIs cannot be "uploaded" by ocai at all
  without a cloud SDK; the plugin may only validate and pass them through.

## Priority and effort

**P2 — next after the data-contract freeze**, exactly as H6 states, and
before `ocai.jobs` lands fully because batch needs file handles on four of
the seven providers (OpenAI, Azure, Gemini, Mistral). Effort: roughly one WU
for the IR + OpenAI + Anthropic edges with multipart fixtures, one WU for
Gemini resumable + Mistral, and a small WU to extend the `ProviderRef`
crossing check with the `qualifier` comparison. The Bedrock/Vertex URI pass-
through is a sub-task of their chat plugins, not of this capability.

## Open questions for the WU

1. `qualifier` grammar for purpose/host narrowing (free string vs. two
   fields). Recommendation: two namespaced keys in one string, parsed by the
   crossing rule, to avoid a `ProviderRef` shape change on a frozen-candidate
   type.
2. Whether `FileInfo.state` needs a fold law for streaming upload progress
   (no provider streams upload progress on the wire; recommend no streaming
   shape at all in v1).
3. Which provider becomes the "generated file" fixture source (Anthropic
   code execution is the only one with a documented `downloadable` flag).

## Sources (read 2026-11-10)

- https://developers.openai.com/api/docs/api-reference/files
- https://developers.openai.com/api/reference/resources/uploads
- https://developers.openai.com/api/docs/guides/pdf-files
- https://developers.openai.com/api/docs/deprecations
- https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/batch (batch limits, Files v1 path)
- https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/fine-tuning (`/openai/v1/files`, `purpose=fine-tune`)
- https://platform.claude.com/docs/en/build-with-claude/files
- https://aistudio.google.com/docs/files
- https://aistudio.google.com/api-reference/files
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference
- https://docs.mistral.ai/api/endpoint/files
- https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference-data.html
