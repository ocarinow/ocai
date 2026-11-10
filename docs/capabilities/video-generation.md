# Video generation — provider survey and canonical IR proposal

**Currency.** Researched 2026-11-10 against the official documentation
linked in Sources; field names are quoted as the pages print them. Marked
`unverified` where only third-party pages or truncated specs were
reachable. The 2026 churn is severe and is itself an input to the priority
call: OpenAI shut down the Sora 2 models and the whole Videos API on
2026-09-24 with "no one-to-one replacement"; Google shut down the Veo 3.1
preview models on the Gemini API on 2026-10-22 and now points developers
to `gemini-omni-1.2-flash` on the Interactions API; Luma replaced the Dream
Machine API with a new `agents.lumalabs.ai` API and model line; MiniMax
moved to a `/v2` content-array API for `MiniMax-H3`. Interface tags for
video will churn faster than for chat.

## 1. Scope

Text-to-video, image-to-video (first/last frame), reference-guided
generation (subject/character/style), extension, edit/remix, and
upscaling. Audio generation is a per-provider flag or default. Every
provider except Google Omni Flash is a long-running job; result URLs expire.

## 2. Providers

### 2.1 OpenAI Sora (historical — shut down 2026-09-24)

Recorded as a clean reference shape and for possible migration edges. `POST /v1/videos`
(`prompt` ≤32000, `model` `sora-2|sora-2-pro`, `seconds` `"4"|"8"|"12"`, `size`
`720x1280|1280x720|1024x1792|1792x1024`, `input_reference{image_url | file_id}` matching `size`,
faces rejected). Video object `{id, object:"video", model, status queued|in_progress|completed|
failed, progress, created_at, completed_at, expires_at, error{code, message}, prompt,
remixed_from_video_id, seconds, size}`. `GET /v1/videos/{id}/content?variant=video|thumbnail|
spritesheet` (URLs valid ≤1 hour); `POST /v1/videos/edits` (replaces remix), `POST
/v1/videos/extensions` (≤20 s per step, 6 steps, 120 s total), `POST /v1/videos/characters`;
webhooks `video.completed`/`video.failed`; polling every 10–20 s with backoff.

### 2.2 Google — Gemini Omni Flash (Interactions API) and Veo on Vertex

- Gemini API: `POST https://generativelanguage.googleapis.com/v1beta/
  interactions`, `x-goog-api-key`. `{model: "gemini-omni-1.2-flash", input:
  string | [{type:"text"} | {type:"image", data|uri, mime_type} |
  {type:"video", uri|data}], response_format: {type:"video", aspect_ratio
  "16:9"|"9:16", resolution "360p"|"720p"|"1080p"|"4k", duration "3s"…
  "15s", delivery: "uri"}, previous_interaction_id, generation_config:
  {video_config: {task: text_to_video|image_to_video|reference_to_video|
  edit|extend}}, background, store, stream}`. **Synchronous by default**
  (the guide recommends `background=false`, `store=false`, `stream=false`
  for fastest unary generation; no polling flow is documented for
  `background=true` — `unverified`). Response: `output_video.data`
  (base64) or `.uri` (a Files API resource; poll the file until `ACTIVE`
  then download), or REST `steps[]` with a `model_output` content block
  `{type:"video", mime_type:"video/mp4", data|uri}`; top-level `id`,
  `status`, `model`, `object`. `GET /v1beta/interactions/{id}` returns
  inline base64 even when created with `delivery:"uri"`.
- Limits: 3–15 s; extension adds 3–10 s per turn up to 30 s total using the
  last 10 s as context; up to 6 reference images (3 per character, 2
  characters), up to 3 reference videos of ≤3 s; first/last-frame
  interpolation at 3–10 s; edit/extend inputs ≤15 s. Native audio always
  generated, prompt-steered. No `negative_prompt`, `temperature`, system
  instructions. SynthID on every output. Stored/asynchronous interactions
  are retained 7 days (stated on the Vertex page).
- Pricing: $12/M video output tokens — about $0.023/s at 360p, $0.07/s at
  720p, $0.104/s at 1080p, $0.209/s at 4K; audio not priced separately.
- Vertex AI (the page also calls it Gemini Enterprise Agent Platform) Veo:
  `POST …/publishers/google/models/{veo-3.1-generate-001 |
  veo-3.1-fast-generate-001 | veo-3.1-lite-generate-001}:predictLongRunning`
  with `{instances:[{prompt}], parameters:{storageUri, sampleCount 1–4,
  aspectRatio "16:9"|"9:16", negativePrompt, personGeneration
  "allow_adult"|"disallow", resolution "720p"|"1080p"|"4k", seed
  0–4294967295}}` (duration 4/6/8 s, parameter name not printed on the
  reachable page; `image`, `lastFrame`, `referenceImages`, `generateAudio`
  exist per the reference index but their fields were not reachable —
  `unverified`). Returns an operation name; poll with `POST
  …:fetchPredictOperation {operationName}` → `{done, response{videos[]
  {gcsUri, mimeType}, raiMediaFilteredCount}}`. OAuth bearer, output to GCS.

### 2.3 Runway (tasks API)

- Base `https://api.dev.runwayml.com/v1`, `Authorization: Bearer`,
  **`X-Runway-Version: 2024-11-06` required on every request**.
- `POST /v1/image_to_video` (`model`, `promptImage` URL or data URI,
  `promptText`, `ratio` e.g. `1280:720`, `duration` e.g. `5`),
  `POST /v1/text_to_video`, `/v1/video_to_video`, `/v1/text_to_image`
  (`gen4_image`, `referenceImages[]{uri, tag}`), `/v1/character_performance`,
  `/v1/video_upscale`, plus sound, speech, music, dubbing endpoints.
  Optional `contentModeration.publicFigureThreshold: "low"` (default
  `auto`). Uploads: `POST /v1/uploads {filename, type:"ephemeral"}`.
- Models on the image-to-video page include `gen4.5`, `gen4_turbo`,
  `aleph2`, and **third-party models under the same API**: `veo3.1`,
  `veo3.1_fast`, `kling_4`, `seedance2`.
- `GET /v1/tasks/{id}` → `{id, status PENDING|THROTTLED|RUNNING|SUCCEEDED|
  FAILED|CANCELLED, output[] (URLs, SUCCEEDED only), failure, failureCode}`;
  `THROTTLED` is queued behind the tier rate limit, not an error.
  `DELETE /v1/tasks/{id}` cancels or deletes. Output URLs "temporary"
  (period not stated); mismatched input aspect ratios are auto-cropped.
- Pricing: 1 credit = $0.01; `gen4_turbo` 5 credits/s, `gen4.5` 12/s,
  `aleph2` 28/s (56 minimum), `veo3.1` 40/s with audio or 20 without,
  `veo3.1_fast` 15/10, `seedance2` 14/30/40/150 per second at
  480p/720p/1080p/4K; `gen4_image` 5 (720p) / 8 (1080p) credits per image.

### 2.4 Luma

- Legacy Dream Machine API: `https://api.lumalabs.ai/dream-machine/v1`,
  Bearer; `POST /generations {prompt, model ray-2|ray-flash-2, resolution
  540p|720p|1080p|4k, duration "5s", aspect_ratio, loop, keyframes{frame0,
  frame1: {type:"image", url} | {type:"generation", id}}, concepts[{key}],
  callback_url}`; `GET /generations/{id}` → `{id, state dreaming|completed|
  failed, failure_reason, assets{video}, created_at, request}`; callbacks
  POST the object (3 retries). The page now points to the new API.
- Current Luma Agents API: `https://agents.lumalabs.ai/v1`, Bearer
  (`LUMA_AGENTS_API_KEY`). `POST /v1/generations {model: "ray-3.2" |
  "uni-1" | "uni-1-max", type: video | image_edit | video_edit |
  video_reframe, aspect_ratio, video{resolution "720p", duration "5s",
  start_frame, end_frame (ImageRef)}, source{generation_id|url|data},
  user_id}`; `GET /v1/generations/{id}` → `{id, state … completed|failed,
  output[]{url}, failure_reason, failure_code, usage{credits_charged}}`
  (`credits_charged` may settle after completion). Rate-limit headers
  `X-RateLimit-*`. URL expiry and prices not stated.

### 2.5 Kling

The official reference (`kling.ai/document-api`) is a JavaScript application that returned no
text on 2026-11-10; everything here is third-party and `unverified`: base `https://api.klingai.com/
v1` (regional `api-singapore.klingai.com`), auth by **JWT (HS256) minted from an access-key/
secret-key pair** (`iss`, ~30-minute `exp`, `nbf`), `POST /v1/videos/text2video` and
`/v1/videos/image2video` → `data.task_id`, `GET /v1/videos/text2video/{task_id}` → `task_status
submitted|processing|succeed|failed`, `task_result.videos[]{id, url, duration}`; short-lived URLs.
Kling is also reachable as `kling_4` under Runway's documented tasks API.

### 2.6 Pika

No first-party developer documentation was located; sources conflict (a
"dev.pika.art" portal versus access only through fal.ai). Treat as
host-only (`fal-ai/pika/*`) — `unverified`.

### 2.7 MiniMax Hailuo

- v1 (Hailuo line): `GET https://api.minimax.io/v1/query/video_generation
  ?task_id=` → `{task_id, status Preparing|Queueing|Processing|Success|Fail,
  file_id, video_width, video_height, base_resp{status_code, status_msg}}`
  (`1026` input sensitive, `1027` output sensitive, `1002` rate limit,
  `1004` auth); `GET /v1/files/retrieve?file_id=` returns the download URL.
  The v1 create page (`POST /v1/video_generation` with `model`, `prompt`,
  `first_frame_image`, `last_frame_image`, `subject_reference`, `duration`,
  `resolution`, `prompt_optimizer`, `callback_url`) was 404 at read time —
  field list `unverified`.
- v2 (`MiniMax-H3`, pay-as-you-go only): `POST /v2/video_generation {model,
  content[]{type text|image_url|video_url|audio_url, role first_frame|
  last_frame|reference_image|reference_video|base_video}, duration 4–15,
  resolution 768P|2K, ratio (required for T2V)}` → `{task_id}`;
  `GET /v2/query/video_generation/{task_id}` → `task.status succeeded|
  failed|cancelled`, `content.url`. Bearer API key.

### 2.8 Alibaba Wan (Model Studio)

- `POST https://{WorkspaceId}.{region}.maas.aliyuncs.com/api/v1/services/
  aigc/video-generation/video-synthesis` with `Authorization: Bearer`,
  **`X-DashScope-Async: enable` required**; legacy hosts
  `dashscope.aliyuncs.com` / `dashscope-intl.aliyuncs.com`.
- wan2.7 (`wan2.7-t2v`): `input{prompt ≤5000, negative_prompt ≤500,
  audio_url (wav/mp3 2–30 s)}`, `parameters{resolution 720P|1080P, ratio
  16:9|9:16|1:1|4:3|3:4, duration 2–15, prompt_extend, watermark, seed}`.
  Legacy wan2.6 and earlier use `parameters.size` (`1280*720`) and fixed
  durations (wan2.5: 5 or 10; 2.1/2.2: 5).
- Response `{output{task_id, task_status PENDING}, request_id}`; `GET
  /api/v1/tasks/{task_id}` → `output{task_status PENDING|RUNNING|SUCCEEDED|
  FAILED|CANCELED|UNKNOWN, video_url, submit_time, scheduled_time,
  end_time, orig_prompt}, usage{duration, output_video_duration,
  video_count, ratio, SR}`. **Task ids and `video_url` expire after 24
  hours.** Billed per second by resolution. Poll ~15 s; 1–5 min typical.

### 2.9 Amazon Nova Reel (Bedrock)

- Async only: `StartAsyncInvoke(modelId "amazon.nova-reel-v1:1", modelInput,
  outputDataConfig{s3OutputDataConfig{s3Uri}})` → `invocationArn`;
  `GetAsyncInvoke` → `status InProgress|Completed|Failed`;
  `ListAsyncInvokes`. SigV4; `s3:PutObject` on the bucket.
- `modelInput`: `taskType TEXT_VIDEO {textToVideoParams{text 1–512,
  images[1]{format png|jpeg, source{bytes | s3Location{uri, bucketOwner}}}}}`
  (image must be exactly 1280x720, no transparency), `MULTI_SHOT_AUTOMATED
  {text ≤4000}` (12–120 s in multiples of 6), `MULTI_SHOT_MANUAL{shots[]
  {text, image}}`; `videoGenerationConfig{durationSeconds 6, fps 24,
  dimension "1280x720", seed 0–2147483646}` — all three fixed values.
- Output lands in S3: `manifest.json`, `video-generation-status.json`
  (`shots[]{status, location, failureType, failureMessage}`, `fullVideo`),
  `output.mp4`, `shot_NNNN.mp4`. Failure types include
  `RAI_VIOLATION_OUTPUT_VIDEO_DEFLECTION`. ~90 s for 6 s, 14–17 min for
  2 min. Content Credentials (C2PA) on outputs.

### 2.10 Hosts — fal.ai and Replicate

Same queue/prediction legs as the image page (`queue.fal.run` submit → `status_url` → result;
Replicate `POST /v1/predictions` → `GET` with `Prefer: wait`); video outputs are model-specific
(`video{url, content_type, file_size}` on most fal video apps — `unverified` per model). Replicate
removes outputs after one hour; fal media expiry follows account settings. fal hosts Kling, Pika,
MiniMax, Wan, Veo and Luma models behind one job shape, which matters for the priority call.

## 3. Comparison

| Provider / interface | Ops | Job shape | Inputs | Duration | Resolution / ratio | Audio | Output | Expiry | Cost unit |
|---|---|---|---|---|---|---|---|---|---|
| OpenAI Sora (shut down) | create, edit, extend, characters | create → poll `status` → `/content` | image first frame, `file_id` | 4/8/12 (+16/20) | 4 sizes incl. 1080p pro | yes | MP4 + thumbnail + spritesheet | 1 h download | per second by model/size |
| Google Omni Flash (`interactions`) | T2V, I2V, ref, edit, extend | **synchronous** (or `background`, undocumented) | ≤6 images, ≤3 videos | 3–15 s, +10 s/turn to 30 s | 360p–4K, 16:9/9:16 | always | base64 or Files API uri | 7 days (stored) | video tokens (~$0.07/s 720p) |
| Google Veo (Vertex) | T2V, I2V, ref, extend | `predictLongRunning` → `fetchPredictOperation` | base64 / gcsUri | 4/6/8 | 720p/1080p/4k, 16:9/9:16 | `generateAudio` (unverified) | GCS uri | GCS-owned | per second |
| Runway | I2V, T2V, V2V, upscale, 3rd-party models | create → `GET /tasks/{id}` | URL / data URI / ephemeral upload | 5/10 | `ratio` strings | model-dependent | URL | temporary | credits/s |
| Luma Agents | video, video_edit, reframe, image | `POST /generations` → `GET` | ImageRef start/end, source | `"5s"` etc. | 720p etc. | n/a | `output[].url` | unstated | credits (settle late) |
| Kling (`unverified`) | T2V, I2V, extend | create → `GET …/{task_id}` | url/base64 | 5/10 | ratio, std/pro | model-dependent | URL | short-lived | per video |
| MiniMax v1/v2 | T2V, I2V, S2V, regen | create → query → files/retrieve (v1) or `content.url` (v2) | first/last frame, refs | 6/10 (v1), 4–15 (v2) | 512P/768P/1080P/2K | n/a | URL via file id | unstated | per video |
| Wan | T2V, I2V, edit | create (`X-DashScope-Async`) → `GET /tasks/{id}` | URLs, audio_url | 2–15 | 720P/1080P + ratio | via `audio_url` or auto | `video_url` | **24 h** (task id too) | per second by resolution |
| Nova Reel | T2V, I2V, multi-shot | `StartAsyncInvoke` → `GetAsyncInvoke` → S3 | 1280x720 image, S3 | 6; 12–120 | fixed 1280x720@24 | no | S3 objects | S3-owned | per second |
| fal / Replicate | any | queue / prediction | URL / data URI | per model | per model | per model | URL | 1 h / setting | per model |

## 4. Canonical IR proposal — `ocai.video`

### 4.1 Identity and shapes

`Capability("video")` with shapes `("video","generate.request"/
"generate.response")` and `("video","extend.request")` (extend returns the
same `VideoResponse`). Edit/remix is `generate` with a `source_video`
reference and `mode="edit"`; first/last-frame, reference-to-video and
character consistency are all `generate` with typed references — the
providers themselves (Omni Flash `video_config.task`, MiniMax `content[]
.role`, Luma `type`) treat them as one request family. Upscale is deferred
until two providers expose it with congruent knobs (Runway
`/v1/video_upscale`, BFL video upscale — one interface each today).

### 4.2 Request

`VideoRequest(prompt, references: list[VideoReference], config:
VideoConfig)`; `VideoReference(source: Source, role: str, id: str | None)`
with open roles `first_frame | last_frame | asset | style | character |
source_video | audio`. Provider-hosted inputs are `SourceRef
(ProviderRef(kind="file"))` (Gemini Files API uri, OpenAI `file_id`, Runway
ephemeral upload uri), provider-scoped; `gs://` / `s3://` stay `SourceUrl`
verbatim and are UNSUPPORTED off their cloud. `VideoConfig(duration_seconds:
float | None, aspect_ratio, resolution, size: Size | None, fps, audio:
bool | None, n, seed, negative_prompt)`. Duration is a float in seconds in
the IR; a provider with an enumerated duration set gets `EXACT` when the
value is in the set and `UNSUPPORTED` otherwise (never rounded — Wan
2–15 integer, Omni `"3s"`–`"15s"` strings, Nova fixed 6, Sora `"4"|"8"|
"12"` strings all map by exact membership). `audio=None` means provider
default; `audio=False` on an always-audio provider (Omni Flash) is
`UNSUPPORTED`-and-reported; `audio=True` on a silent provider (Nova Reel)
likewise. Resolution follows the image page: open code `360p|480p|720p|
1080p|4k` with `native` lane, exact `size` only for providers that take
pixels (Sora, Nova), size→ratio derivation reported `APPROXIMATED`.

### 4.3 Response, usage, finish

`VideoResponse(videos: list[VideoOutput], finish: FinishInfo, usage: Usage,
info: ResponseInfo)`; `VideoOutput(source: Source, duration_seconds, width,
height, fps, mime_type, has_audio: bool | None, expires_at: str | None,
thumbnail: Source | None, seed, safety: MediaSafety(filtered, reason,
native))`. Omni Flash base64 is `SourceBase64`; every URL output is a
`SourceUrl` with `expires_at` filled from provider knowledge (Wan 24 h,
Sora 1 h, Replicate 1 h). A facade `materialize()` downloads into bytes.
Usage reuses core `Consumption` with the open unit `seconds` (modality
`video`, from Wan `usage.output_video_duration`, Runway credits/s, Google
video tokens → `tokens`), `credits` (Runway, Luma `credits_charged` —
which may arrive on a later poll; the facade merges it with a
`SemanticShift("usage_settled_late")`), and `requests`. Dropped or
filtered outputs (Veo `raiMediaFilteredCount`, Nova
`RAI_VIOLATION_OUTPUT_VIDEO_DEFLECTION`, MiniMax `1027`) become
`finish.reason="content_filter"` with the native code preserved, and a
`MediaSafety(filtered=True)` placeholder per missing sample.

### 4.4 The job pattern — the center of this capability

Every provider except Omni Flash is submit/poll/fetch, so `ocai.video` is
the capability that forces `ocai.jobs` (H6) into existence:

- `submit` → `CallResult[JobHandle]`, anchored by `ProviderRef(kind="job",
  scope=interface, id=…)`: Runway task id, Wan `task_id`, MiniMax
  `task_id`, Nova `invocationArn`, Vertex operation name, Luma generation
  id, Sora video id, fal `request_id`, Replicate prediction id. Interface-
  scoped: a Runway task id means nothing to fal even when both run Kling.
- `poll` → `CallResult[JobStatus(state, progress, native, expires_at,
  message)]`, open state `queued | running | succeeded | failed |
  moderated | cancelled | expired | unknown`. Decoders map Runway
  `THROTTLED` → `queued`, Wan `UNKNOWN` → `unknown`, Nova `InProgress` →
  `running`, each with the verbatim value in `native`. `progress` is
  optional (Sora `progress`, BFL `progress`; most providers have none).
- `fetch` → `CallResult[VideoResponse]`. Some providers deliver the result
  on the final poll (Runway `output[]`, Wan `video_url`), some need a
  second hop (MiniMax `file_id` → `/files/retrieve`, Sora `/content`,
  Vertex GCS, Nova S3). `fetch` is still a separate `Operation` returning
  its own `Route`; when the poll already carries the payload the codec's
  `fetch` is a pure projection with no wire call, which the `Route` says.
- `cancel` is an optional fourth operation (Runway `DELETE /tasks/{id}`,
  fal `PUT …/cancel`, Replicate `/cancel`, Adobe `cancelUrl`); providers
  without it declare it ABSENT.
- Expiry is first-class on both `JobHandle` and `VideoOutput`: Wan's
  24-hour task-id lifetime means a persisted handle can go `expired`, which
  is a state, not an exception.
- The facade `generate()` composes the legs with a backoff policy taken
  from provider traits (Sora 10–20 s, Wan 15 s, Stability ≤1/10 s), merges
  usage, and declares the fan-out `SemanticShift`. Webhooks (`callback_url`,
  `webhook_url`, `fal_webhook`, Sora events) pass through `provider_options`
  at v0; a serializable `JobHandle` lets a webhook receiver resume at
  `fetch`.
- Omni Flash's synchronous call is the degenerate case: `submit` returns a
  `JobHandle` whose status is already `succeeded` and whose `fetch` is a
  projection — the same port, no special path.

### 4.5 Streaming

No provider streams frames over its public API; Omni Flash's SSE delivers the whole video in the
terminal event. The capability ships no chunk type at v0 (recipe step 8 satisfied by declaring it
non-streaming); if progress previews appear, the law is fold-by-replacement as for images.

### 4.6 Extensions

Google: `video_config.task`, `thinking_level`, `delivery`, `store`,
`personGeneration`, `storageUri`, `enhancePrompt`. Runway:
`contentModeration.publicFigureThreshold`, `ratio` strings, model-specific
fields. Wan: `prompt_extend`, `watermark`, `audio_url`, `shot_type`
(legacy), `size` (legacy). MiniMax: `prompt_optimizer`,
`fast_pretreatment`, `aigc_watermark` (`unverified`), v2 `content[].role`
beyond the canonical roles. Nova: `taskType MULTI_SHOT_*`, S3 output config,
`bucketOwner`. Luma: `loop`, `concepts`, `type: video_reframe`. Kling:
`mode std|pro`, `cfg_scale`, `camera_control` (`unverified`). Hosts: the
whole model input schema under `provider_options`.

## 5. Priority — P2, argued

Video should be **P2 for the IR + two providers and P3 for breadth**, not
P0/P1, for four reasons:

1. **Interface volatility.** Of the ten surfaces surveyed, three were
   shut down or replaced in the last three months (Sora, Veo on the Gemini
   API, Dream Machine), one moved to a new major version (MiniMax), and two
   have no reachable official reference (Kling, Pika). ocai's value is
   certified, provenance-stamped conversion; certifying against tags that
   die in a quarter burns conformance effort without compounding the moat.
   Image interfaces, by contrast, have kept their grammar across model
   swaps (OpenAI, Stability, BFL).
2. **The job vocabulary must exist first.** Every video provider is a job;
   building video before `ocai.jobs` (H6) would mint a capability-local
   job clone, which §11 step 2 forbids. Image lands the job pattern on
   two or three providers at lower stakes (BFL, Stability async upscale),
   and video then inherits a tested vocabulary.
3. **Low conversion surface, high custody surface.** The knobs that
   convert are few (prompt, duration, ratio, resolution, references,
   audio); the engineering weight is custody — expiring URLs, cloud-bucket
   outputs, settle-late billing, 24-hour task-id lifetimes. Those are
   `ocai.jobs` + facade concerns, not new IR.
4. **Enterprise demand follows governance.** ocai's buyers need the auditable image/chat path
   first; video's recorded fixtures are also large and slow to curate.

Within P2, implement in this order:

| Provider | Priority | Effort (WUs) | Why |
|---|---|---|---|
| Google `interactions` (Omni Flash) | P2 | 2 | Codec shared with the image capability; synchronous, base64 — the IR and response shape without the job machinery; extension via `previous_interaction_id` exercises interface-scoped refs |
| Runway tasks API | P2 | 2 | One documented job shape fronting Runway, Veo 3.1, Kling 4 and Seedance 2: the cheapest multi-model coverage per edge, clean status enum, credits/s usage, versioned header |
| fal.ai host | P2 | 1 (after image host WU) | Reuses the queue legs; brings Kling, Pika, MiniMax, Wan, Luma as model schemas under `provider_options` |
| Alibaba Wan | P3 | 1 | Clean documented job API, `usage` block, 24 h expiry fixture |
| Vertex Veo | P3 | 2 | LRO + GCS custody, OAuth; reference fields partly unreachable |
| Amazon Nova Reel | P3 | 2 | SigV4 + S3 output custody; multi-shot is an extension |
| MiniMax (v2) | P3 | 1 | Content-array grammar close to the IR; v1 pages unstable |
| Luma Agents | P3 | 1 | New API; verify stability first |
| Kling direct, Pika | P3/none | — | No reachable official docs; reach them via Runway/fal |
| OpenAI Sora | none | — | Shut down; keep the recorded shape for migration edges only |

## 6. Unverified items

- Omni Flash `background=true` polling flow and status values; retention of unstored videos.
- Vertex Veo fields `image`, `lastFrame`, `referenceImages`, `generateAudio`, `durationSeconds`;
  `bytesBase64Encoded` output; `raiMediaFilteredReasons`.
- Runway output URL lifetime, data-URI size limit, 429 behaviour; Luma Agents pricing and URL life.
- Kling (official reference unreachable); Pika first-party API existence.
- MiniMax v1 create-task fields and file URL lifetime; fal per-model video output schemas.

## Sources (read 2026-11-10)

- https://developers.openai.com/api/docs/api-reference/videos
- https://developers.openai.com/api/docs/guides/video-generation
- https://aistudio.google.com/docs/video
- https://aistudio.google.com/docs/omni
- https://aistudio.google.com/docs/pricing
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos-from-text
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/veo-video-generation (redirected to the generic predict reference)
- https://docs.dev.runwayml.com/_llms-txt/core-api.txt
- https://docs.dev.runwayml.com/ai-context.md
- https://docs.dev.runwayml.com/guides/pricing.md
- https://docs.dev.runwayml.com/llms.txt
- https://docs.lumalabs.ai/docs/video-generation
- https://docs.agents.lumalabs.ai
- https://kling.ai/document-api/apiReference/model/videoGeneration (JavaScript-only; no text retrievable)
- https://www.skills.lc/supercent-io/skills-template/supercent-io-skills-template-agent-skills-utilities-kling-ai-skill-md (third-party; Kling auth and paths)
- https://apiframe.ai/guides/pika-labs-api-guide (third-party; Pika status)
- https://platform.minimax.io/docs/guides/video-generation.md
- https://platform.minimax.io/docs/api-reference/video-generation-query.md
- https://www.alibabacloud.com/help/en/model-studio/text-to-video-api-reference
- https://docs.aws.amazon.com/nova/latest/userguide/video-generation.html
- https://docs.aws.amazon.com/nova/latest/userguide/video-gen-access.html
- https://fal.ai/docs/model-endpoints/queue
- https://replicate.com/docs/reference/http
