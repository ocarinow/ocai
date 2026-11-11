# Batch and long-running jobs

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

**Currency.** Researched 2026-11-10 against current provider documentation
(URLs in Sources). Batch windows, discounts and limits are the fields
providers change most often; treat every number as dated. *Unverified* marks
claims not confirmed from an official page on this pass. Two generation APIs
cited by the task brief have been shut down since it was written: OpenAI's
Sora Videos API (2026-09-24) and the Veo preview models in the Gemini API
(2026-10-22); they are kept below as historical lifecycle evidence only.

**Scope.** Asynchronous execution of many requests (batch APIs) and of single
long-running operations (background responses, video generation, tuning
jobs, file processing), and the `ocai.jobs` vocabulary H6 reserves for them.

## Provider survey: batch APIs

### OpenAI Batch API

- Input: a JSONL file uploaded with `purpose=batch`; each line `{custom_id,
  method, url, body}`; one model per file. Supported `url` values:
  `/v1/responses`, `/v1/chat/completions`, `/v1/embeddings`,
  `/v1/completions`, `/v1/moderations`, `/v1/images/generations`,
  `/v1/images/edits`.
- `POST /batches` with `input_file_id`, `endpoint`, `completion_window`
  (only `"24h"` accepted), optional `metadata`, optional
  `output_expires_after {anchor: "created_at", seconds 3600–2592000}`.
- Batch object: `status` ∈ `validating`, `failed`, `in_progress`,
  `finalizing`, `completed`, `expired`, `cancelling`, `cancelled`;
  `output_file_id`, `error_file_id`; nullable timestamps `created_at`,
  `in_progress_at`, `finalizing_at`, `completed_at`, `failed_at`,
  `expired_at`, `expires_at`, `cancelling_at`, `cancelled_at`;
  `request_counts {total, completed, failed}`; `errors`; `usage` (populated
  for batches created after 2025-09-07).
- Limits: 50,000 requests per batch; 200 MB input; embeddings capped at
  50,000 inputs; 2,000 batches created per hour; per-model enqueued-token
  quota; batch rate limits are separate from synchronous limits.
- Cost: 50% of synchronous price. Expired batches: completed lines are
  billed, unfinished ones appear in the error file with code `batch_expired`.
- Retention: output file auto-deleted 30 days after completion. Output order
  is not input order; join on `custom_id`.
- Cancel: `POST /batches/{batch_id}/cancel` → `cancelling` for up to 10
  minutes → `cancelled` with partial output.
- Notification: webhooks `batch.completed`, `batch.failed`, `batch.expired`,
  `batch.cancelled` (Standard Webhooks headers `webhook-id`,
  `webhook-timestamp`, `webhook-signature`; payload `{object: "event", id,
  type, created_at, data: {id}}`).

Azure OpenAI mirrors this under `/openai/v1/batches` with `GlobalBatch` and
`DataZoneBatch` deployment types, a separate enqueued-token quota, 200 MB
input (1 GB with Blob Storage), 100,000 requests per file, and one documented
difference: it does **not** expire jobs that overrun 24 hours.

### Anthropic Message Batches

- `POST /v1/messages/batches` with `requests[]`, each `{custom_id, params}`;
  `custom_id` matches `^[a-zA-Z0-9_-]{1,64}$`; `params` is a full Messages
  request. No input file.
- Limits: 100,000 requests or 256 MB, whichever first. Most batches finish
  within 1 hour; results are available when all requests finish or after 24
  hours; the batch expires if processing does not complete within 24 hours.
- `processing_status`: `in_progress` → `ended` (and `canceling` after a
  cancel; canceled batches also end at `ended`). `request_counts` tallies
  processing plus each result type.
- Results: `results_url` serving JSONL; per-line `result.type` ∈
  `succeeded`, `errored`, `canceled`, `expired`; `errored` lines carry the
  standard error shape; only `succeeded` lines are billed. Results are kept
  29 days; results use the API version of the creating request. Order is not
  guaranteed; join on `custom_id`.
- Unsupported inside a batch (validation error): `stream: true`, `speed`
  (fast mode), `fallbacks` (server-side fallback), `max_tokens: 0`.
- Supported: vision, all server tools (the batch worker runs the same
  server-side agentic loop and may return `stop_reason: "pause_turn"`),
  extended thinking, prompt caching (stacking discounts; 30–98% hit rates,
  best effort), the `output-300k-2026-03-24` beta raising `max_tokens` to
  300,000 (batch only).
- Cost: 50% of standard prices. Workspace-scoped. Rate limits apply to both
  HTTP calls and queued requests.

### Gemini API batch mode

- `POST models/{model}:batchGenerateContent`; SDK `batches.create` and
  `batches.create_embeddings` (embeddings supported with
  `gemini-embedding-2`).
- Input: inline `GenerateContentRequest` list (keep total under 20 MB) or a
  JSONL file uploaded through the Files API (each line `{key, request}`;
  2 GB per file).
- Name `batches/{id}`. States: `JOB_STATE_PENDING`, `JOB_STATE_RUNNING`,
  `JOB_STATE_SUCCEEDED`, `JOB_STATE_FAILED`, `JOB_STATE_CANCELLED`,
  `JOB_STATE_EXPIRED` (pending or running for more than 48 hours).
- Output: `inlinedResponses` (or `inlinedEmbedContentResponses`) for inline
  input; a JSONL output file (`dest.fileName`; one REST sample says
  `responsesFile`) for file input, each line a `GenerateContentResponse` or a
  status object. `batchStats.failedRequestCount` is referenced but not
  defined on the page.
- Target turnaround 24 hours; 50% of interactive price; `cached_content`
  honored per request; creation is **not idempotent**.

### Vertex AI batch prediction (Gemini)

- `POST /v1/projects/{project}/locations/{location}/batchPredictionJobs`;
  methods `get`, `list`, `cancel`, `delete`. Resource name
  `projects/{p}/locations/{l}/batchPredictionJobs/{id}`.
- Input: Cloud Storage JSONL (1 GB file limit) or BigQuery `bq://` table in
  the same region as the job; output to Cloud Storage or BigQuery.
- Limits: 200,000 requests per job; 1,000,000 rows for Gemini embedding
  models; 10,000 concurrent queued jobs per project for embeddings.
- Lifecycle: a job may wait in queue up to 72 hours, then expires; once
  running, incomplete work is cancelled 24 hours after start; completed
  requests are billed. States observed in docs and samples:
  `JOB_STATE_PENDING`, `JOB_STATE_RUNNING`, `JOB_STATE_SUCCEEDED`,
  `JOB_STATE_FAILED`, `JOB_STATE_CANCELLED`, `JOB_STATE_PAUSED`; the full
  `JobState` enum (which also has `QUEUED`, `CANCELLING`, `EXPIRED`,
  `UPDATING`, `PARTIALLY_SUCCEEDED` in the generic Vertex API) could not be
  read from the reference page on this pass (*unverified* for batch).
- Cost: 50% of real-time; cached-input discounts stack (90%, or 95% total on
  Gemini 3 and later).

### Bedrock batch inference

- `CreateModelInvocationJob` with `jobName`, `roleArn`, `modelId`,
  `inputDataConfig` (S3 prefix holding `.jsonl` plus referenced media),
  `outputDataConfig` (S3), optional `modelInvocationType` ∈ `InvokeModel`
  (default, native body) | `Converse`, `timeoutDurationInHours` (24–168,
  default 24), `clientRequestToken` (idempotency), `vpcConfig`, `tags`.
  Returns `jobArn` (`…:model-invocation-job/[a-z0-9]{12}`).
- Records: `{recordId, modelInput}`; output order not guaranteed;
  `manifest.json.out` summarises counts.
- Status: `Submitted`, `Validating`, `Scheduled`, `Expired` (timed out
  before starting), `InProgress`, `Completed`, `PartiallyCompleted`,
  `Failed`, `Stopping`, `Stopped`. Progress counters `totalRecordCount`,
  `processedRecordCount`, `successRecordCount`, `errorRecordCount` (may lag
  up to 1 minute).
- Notification: EventBridge job-state events instead of polling.
- Restrictions: not supported for provisioned models; `Converse`-type jobs
  reject `toolConfig` with 400 (use `InvokeModel` native format for tools);
  structured outputs supported on both. Record and file-size quotas live in
  Service Quotas (numbers not on the page). Pricing on the pricing page; the
  50% figure was not confirmed from the fetched text (*unverified*). An
  OpenAI-compatible Batch API surface also exists on Bedrock (page title
  only; *unverified* details).

### Mistral batch

- SDK `client.batch.jobs.create(input_files | requests, model, endpoint,
  metadata)`; file batching up to 1,000,000 requests, inline batching for
  under 10,000. The REST path is not shown on the capability page
  (`/v1/batch/jobs` *unverified*).
- JSONL lines `{custom_id, body}`; `body.model` optional when set on the job.
- `endpoint` ∈ `/v1/embeddings`, `/v1/chat/completions`,
  `/v1/fim/completions`, `/v1/moderations`, `/v1/chat/moderations`,
  `/v1/ocr`, `/v1/classifications`, `/v1/conversations`,
  `/v1/audio/transcriptions`.
- Status: `QUEUED`, `RUNNING`, `SUCCESS`, `FAILED`, `TIMEOUT_EXCEEDED`,
  `CANCELLATION_REQUESTED`, `CANCELLED`. Results in `output_file` and
  `error_file` (download through the Files API). 50% discount.

### Groq batch

- OpenAI-shaped: `POST /openai/v1/files` (`purpose=batch`),
  `POST /openai/v1/batches` (`input_file_id`, `endpoint`,
  `completion_window` from `24h` to `7d`), `GET /openai/v1/batches/{id}`,
  list with `cursor`/`paging.next_cursor`, multi-get up to 200 ids.
- Same eight statuses as OpenAI. Endpoints `/v1/chat/completions`,
  `/v1/audio/transcriptions`, `/v1/audio/translations`; `POST` only.
- 50,000 lines and 200 MB per file; 50% discount (does not stack with prompt
  caching); only completed requests billed; files and results kept 30 days.

### Together batch

- `/v1/batches` surface driven by the `tg batches` CLI in docs; `custom_id`
  join key; every `body.model` identical. Statuses shown: `VALIDATING`,
  `IN_PROGRESS`, `COMPLETED`; per-request errors do not change batch status;
  other terminal states *unverified*.
- 50,000 requests and 100 MB per file; 10 MB per line; 30B enqueued tokens
  per model; window fixed at `24h` best effort; "up to 50% off" serverless
  rates, no discount on dedicated endpoints.

## Provider survey: generic long-running operations

| Pattern | Shape | Notes (2026-11-10) |
|---|---|---|
| OpenAI Responses background mode | `POST /v1/responses` with `background: true`; `GET /v1/responses/{id}` while `queued`/`in_progress`; `POST /v1/responses/{id}/cancel` (idempotent); resume a stream with `?stream=true&starting_after={sequence_number}` | `store=false` allowed; under ZDR data is kept about 10 minutes; webhooks `response.completed`/`failed`/`cancelled`/`incomplete` |
| OpenAI webhooks (cross-cutting) | 27 event types incl. `batch.*`, `fine_tuning.job.*`, `response.*`, `eval.run.*`, `video.*`, `realtime.call.incoming`, `agent.environment.*`, `agent.session.*`, `safety.alert.created` | signature verification headers above; payload carries only `data.id` — the client still fetches the object |
| OpenAI Videos API (historical) | `POST /videos` → `video_…` with `status` `queued`/`in_progress`/`completed`/`failed`, `progress` percent; `GET /videos/{id}/content`; download URLs valid 1 hour; batch-generated videos 24 hours | shut down 2026-09-24, no replacement API |
| Gemini API Veo (historical) | `predictLongRunning` returning an operation | Veo 3.1 preview models shut down in the Gemini API 2026-10-22; video generation moved to `gemini-omni-1.2-flash` through the Interactions API (background interactions with `status: failed` on block) |
| Vertex Veo | `publishers/google/models/{model}:predictLongRunning`, poll with `:fetchPredictOperation`; optional `storageUri` (else bytes in response) | operation name format and retention *unverified* |
| Vertex long-running operations | `google.longrunning.Operation`; `GET /v1/{name}`, `GET /v1/{name}/operations`, `POST /v1/{name}:cancel`, `DELETE /v1/{name}`, `POST /v1/{name}:wait` | `wait` is a server-side blocking poll with timeout |
| Gemini Files processing | `File.state` `PROCESSING` → `ACTIVE`/`FAILED` | a job without a job endpoint; see files-and-assets.md |
| Fine-tuning jobs | see fine-tuning.md | state vocabularies differ per provider |

## Lifecycle table

| Provider | Submit object | Non-terminal states | Terminal states | Partial success | Expiry / window | Signal | Result retention | Cost |
|---|---|---|---|---|---|---|---|---|
| OpenAI Batch | file + `POST /batches` | `validating`, `in_progress`, `finalizing`, `cancelling` | `completed`, `failed`, `expired`, `cancelled` | yes (`error_file_id`, `request_counts.failed`) | `24h` only | poll or webhook | output file 30 d | 50% |
| Azure OpenAI Batch | same | same | same | yes | 24 h target, no expiry | poll | per file expiration | 50% |
| Anthropic Batches | inline `requests[]` | `in_progress`, `canceling` | `ended` (per-line `succeeded`/`errored`/`canceled`/`expired`) | yes (per line) | 24 h | poll | 29 d | 50% |
| Gemini API | inline or Files JSONL | `JOB_STATE_PENDING`, `JOB_STATE_RUNNING` | `SUCCEEDED`, `FAILED`, `CANCELLED`, `EXPIRED` | yes (status lines in output) | 24 h target; expire after 48 h | poll | not stated | 50% |
| Vertex batch | GCS/BigQuery | `PENDING` (≤ 72 h queue), `RUNNING` | `SUCCEEDED`, `FAILED`, `CANCELLED`, `PAUSED` (+ enum *unverified*) | yes | 24 h after start | poll | your storage | 50% |
| Bedrock | S3 + `CreateModelInvocationJob` | `Submitted`, `Validating`, `Scheduled`, `InProgress`, `Stopping` | `Completed`, `PartiallyCompleted`, `Failed`, `Stopped`, `Expired` | yes (`PartiallyCompleted`) | 24–168 h | poll or EventBridge | your S3 | pricing page |
| Mistral | file or inline | `QUEUED`, `RUNNING`, `CANCELLATION_REQUESTED` | `SUCCESS`, `FAILED`, `TIMEOUT_EXCEEDED`, `CANCELLED` | yes (`error_file`) | timeout (hours not on page) | poll | Files API | 50% |
| Groq | file + `/batches` | as OpenAI | as OpenAI | yes | `24h`–`7d` | poll | 30 d | 50% |
| Together | file + `/batches` | `VALIDATING`, `IN_PROGRESS` | `COMPLETED` (+ *unverified*) | yes | `24h` best effort | poll | not stated | up to 50% |
| OpenAI background response | `background: true` | `queued`, `in_progress` | `completed`, `failed`, `cancelled`, `incomplete` (*names from webhook list*) | n/a | none | poll, stream-resume, webhook | ~10 min under ZDR | normal |

Two structural observations the lifecycle table makes visible:

1. **Partial success is universal.** Every batch surface can end with some
   items succeeded and some failed, and the batch-level status says little
   about item outcomes (Together states it explicitly; Anthropic encodes it
   per line). Item results, not batch status, must carry the honesty.
2. **"Expired" has two meanings.** OpenAI/Anthropic/Gemini expire *work*
   (the window elapsed); Bedrock and Vertex expire *queueing* (never
   started). The canonical state vocabulary needs both or the native lane
   must disambiguate.

## Canonical proposal: `ocai.jobs`

H6 fixes the vocabulary: `Job` and `JobHandle`, never `Operation` (that word
is the catalog's endpoint-kind). §11 step 6 fixes the shape: submit, poll,
cancel and fetch are **separate `Operation`s, each returning its own
`CallResult` and `Route`**, anchored by `ProviderRef(kind="job")`.

- **Where it lives.** Runtime tier (`ocai.runtime.jobs` or `ocai.jobs`
  importing core + convert), capability-neutral: batch chat, batch
  embeddings, video generation and tuning all compose over it in their
  facades. It is machinery, not a frozen contract.
- **`Job` (pure data, core vocabulary).** `ref: ProviderRef(kind="job",
  scope=PROVIDER)`; `state: str` open code with canonical constants
  `QUEUED`, `RUNNING`, `FINALIZING`, `SUCCEEDED`, `PARTIAL`, `FAILED`,
  `CANCELLING`, `CANCELLED`, `EXPIRED_UNSTARTED`, `EXPIRED_INCOMPLETE`;
  `native_state: str` verbatim; `counts: JobCounts(total, completed,
  failed, pending)` all optional; timestamps `created_at`, `started_at`,
  `ended_at`, `expires_at`; `outputs: list[SourceRef]` (output and error
  files, or inline-result marker); `extensions`. Decoding an unknown native
  state never raises: it maps to the open code `UNKNOWN` with the native
  value preserved (rule 6).
- **`JobHandle` (runtime object).** Binds a `Job` to the port and catalog
  that created it; exposes `poll()`, `cancel()`, `fetch()` each performing
  exactly one wire call and returning `CallResult[Job]` or
  `CallResult[JobResults]`. A convenience `wait(policy)` loops `poll()` and
  is the *only* place sleeping happens; it is a facade helper, never a
  driver behaviour, and it declares its polling as observer events, not as
  a conversion loss.
- **Submit.** A capability facade (for example `ocai.chat` batch) converts
  N `ChatRequest`s through the normal request edge of the destination
  interface — the same codec the synchronous path uses — and the jobs layer
  wraps them in the provider's batch envelope (JSONL lines with `custom_id`,
  or inline `requests[]`). The envelope is a dialect; the per-item body is
  ordinary conversion with an ordinary `FidelityReport`. The facade merges N
  item reports into the submit `CallResult.report` (fan-out declared as a
  `SemanticShift`, §11 step 11).
- **Fetch → per-item `CallResult`s.** `fetch()` downloads the output and
  error artifacts and yields `JobResults: list[ItemResult]` where each
  `ItemResult(key, result: CallResult[ChatResponse] | None, error:
  OcaiError | None)`. The response of each successful line runs through the
  interface's response edge, so every item gets its own `FidelityReport`,
  `Usage` and `Route` (same `Route` object, item index as a sub-key). Errors
  map through the shared taxonomy (rule 8): `batch_expired` →
  `TransientError` with `retryable=True`; Anthropic `errored` lines carry
  the standard error shape and map like a synchronous error. Anthropic's
  `pause_turn` is a `FinishInfo` detail, not an error.
- **Keys.** `custom_id`/`key`/`recordId` are generated by the facade from a
  stable index and stored in the submit `CallResult.raw`; user-supplied keys
  must satisfy the strictest grammar (Anthropic's `^[a-zA-Z0-9_-]{1,64}$`)
  or are hashed, with the mapping reported.
- **Consumption.** `Usage` gains no new field; batch pricing is a
  `Consumption` dimension (`tier="batch"`, open code) so the cost
  interceptor can apply the provider's discount from catalog data (see
  model-catalog.md) without the IR knowing prices.
- **Notifications.** Webhooks and EventBridge are *inputs* to `poll()`
  (an external signal that a poll is worth doing). The kernel ships no
  webhook receiver; verifying `webhook-signature` is a platform concern. A
  `JobEvent` observer type lets platforms feed signals in.
- **Profile keys.** `jobs.batch.window.24h` (all), `jobs.batch.window.custom`
  (Groq, Bedrock), `jobs.batch.inline_input` (Anthropic, Gemini, Mistral,
  Vertex via BigQuery), `jobs.batch.file_input` (OpenAI, Azure, Gemini,
  Mistral, Groq, Together, Bedrock, Vertex), `jobs.batch.tools` (ABSENT on
  Bedrock `Converse` type), `jobs.batch.embeddings` (OpenAI, Gemini,
  Vertex, Mistral), `jobs.cancel` (all surveyed), `jobs.idempotent_submit`
  (NATIVE only on Bedrock via `clientRequestToken`; Gemini explicitly not).

## What is honestly UNSUPPORTED

- **Streaming inside batches.** No provider streams batch items; Anthropic
  rejects `stream: true`. A `ChatRequest` marked for streaming routed to a
  batch is `UNSUPPORTED`-and-reported, never silently downgraded.
- Anthropic `speed`, `fallbacks`, `max_tokens: 0` in batches.
- Tool calling in Bedrock `Converse`-type batch jobs.
- Completion windows other than 24 h on OpenAI, Azure, Anthropic, Together.
- Preserving input order: every provider says results may arrive out of
  order; the jobs layer restores order by key and reports nothing because
  nothing is lost — but it must never assume order.
- Exactly-once submission on Gemini (not idempotent) and on any provider
  without a client token: the facade may dedupe by `metadata`, as a declared
  heuristic.
- Cross-provider job handles: a `ProviderRef(kind="job")` is provider-scoped
  and host-bound; moving a running job is meaningless and `UNSUPPORTED`.

## Priority and effort

**P2, after files.** Batch is the most-requested enterprise cost lever (50%
across the board) and the first place `ocai.jobs` earns its keep; it also
gives the cost interceptor its first non-synchronous tier. Effort: one WU for
`Job`/`JobHandle` + OpenAI Batch (file input, JSONL fixtures, error file) +
Anthropic Batches (inline input, `results_url` streaming) — the two shapes
are different enough to prove the abstraction; a second WU for Gemini and
Vertex (states, 72 h queue) and the generic `Operation` poller; Bedrock,
Mistral, Groq, Together follow as plugin work. Background responses ride the
same `JobHandle` with one wire call per leg and fold the resumed stream
through the existing chat fold law.

## Sources (read 2026-11-10)

- https://developers.openai.com/api/docs/guides/batch
- https://developers.openai.com/api/reference/resources/batches
- https://developers.openai.com/api/docs/guides/background
- https://developers.openai.com/api/docs/guides/webhooks
- https://developers.openai.com/api/reference/resources/webhooks/methods/create
- https://developers.openai.com/api/docs/guides/video-generation (shutdown notice)
- https://developers.openai.com/api/docs/deprecations
- https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/batch
- https://platform.claude.com/docs/en/build-with-claude/batch-processing
- https://aistudio.google.com/docs/batch-api
- https://aistudio.google.com/docs/video (Veo shutdown notice)
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/batch-prediction-gemini
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/samples/googlegenaisdk-batchpredict-with-bq
- https://docs.cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.batchPredictionJobs
- https://docs.cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.operations
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/veo-video-generation
- https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference-create.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference-monitor.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference-data.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_ModelInvocationJobSummary.html
- https://docs.mistral.ai/capabilities/batch/
- https://console.groq.com/docs/batch
- https://docs.together.ai/docs/batch-inference
