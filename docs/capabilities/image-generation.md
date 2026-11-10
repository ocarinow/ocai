# Image generation and editing — provider survey and canonical IR proposal

**Currency.** Researched 2026-11-10 against the official documentation in Sources; field names
are quoted as the pages print them. Marked `unverified` where only a third-party page or a
truncated spec was reachable. This market moves monthly: in 2026 OpenAI retired `gpt-image-1`
(2026-10-23) and `/v1/images/variations`, Google shut Imagen down on the Gemini API and listed
every Imagen 3/4 id on Vertex as discontinued (replacement `gemini-2.5-flash-image`), and Azure
retired `dall-e-3` (2026-03-04). Treat every model id below as an interface `tag` candidate.

**Scope.** Text-to-image, editing (inpaint/outpaint/instruction), variation and remix, upscale,
and native image output of chat models. Vector and GIF output are out of scope at v0.

## 2. Providers

### 2.1 OpenAI Images API and the Responses `image_generation` tool

- Endpoints: `POST /v1/images/generations` (JSON), `POST /v1/images/edits` (multipart in examples,
  field `image[]`; JSON schema field `images`, 1–16 `{file_id, image_url}`); `/v1/images/variations`
  is retired. Auth `Authorization: Bearer`.
- Models (2026-11-10): `gpt-image-2.5-sunburst` (edits default), `gpt-image-2.5-flare`,
  `gpt-image-2.6-sunburst|flare`, `gpt-image-2`, `gpt-image-1.5`, `gpt-image-1-mini`,
  `chatgpt-image-latest`; `dall-e-2`/`dall-e-3` remain in the enum.
- Knobs: `prompt` ≤32000; `n` 1–10; `size` `auto`, `1024x1024`, `1536x1024`, `1024x1536`, or any
  `WIDTHxHEIGHT` (sides multiples of 16, ratio 1:3–3:1, max edge 3840, 655,360–8,294,400 px; above
  2560x1440 experimental); `quality` `auto|low|medium|high` (+ `xhigh|max` on 2.5); `background`
  `auto|transparent|opaque` (transparent needs `png`/`webp`); `output_format` `png|jpeg|webp|gif|svg`;
  `output_compression` 0–100; `moderation` `auto|low`; `stream` + `partial_images` 0–3;
  `safety_identifier` (replaces `user`); `complexity` `low|medium|high` (2.6); GIF `frame_count`
  2–16, `frame_duration_ms`; `svg{model, reasoning{effort}}` (`n=1`, no streaming). Edits add
  `mask{file_id|image_url}` (alpha = edit area, same size as the first image, <50 MB), `markup`
  (transparent PNG annotation layer, exclusive with `mask`), `input_fidelity` `high|low` (1.5
  only). Legacy `response_format` `url|b64_json` and `style` `vivid|natural` are DALL-E-only.
- Response: `created`, `data[].b64_json` (`url` only for DALL-E, valid 60 minutes),
  `data[].revised_prompt` (DALL-E only), `background`, `output_format`, `quality`, `size`,
  `usage{input_tokens, output_tokens, total_tokens, input_tokens_details{image_tokens,
  text_tokens}, output_tokens_details}`, optional `svg_usage`.
- Streaming (GPT image models): SSE `image_generation.partial_image` / `image_edit.partial_image`
  (`b64_json`, `partial_image_index` 0-based, `background`, `created_at`, `output_format`,
  `quality`, `size`) then `image_generation.completed` / `image_edit.completed` (same + `usage`);
  100 image output tokens per partial.
- Responses tool: `{"type":"image_generation", model, action auto|generate|edit, size, quality,
  background, output_format, partial_images, input_image_mask{file_id}}`; output item
  `image_generation_call{id, status, result (base64), revised_prompt}`; event `response.
  image_generation_call.partial_image{partial_image_index, partial_image_b64}`; multi-turn edit
  via `previous_response_id` or by replaying the item.
- Moderation: `error.code = "moderation_blocked"` with optional `moderation_details
  {moderation_stage input|output|unknown, categories}`. Pricing is token-based (2.5: $8/M image
  input, $2/M cached, $30/M image output) and observable in `usage`.

### 2.2 Google — Gemini native image output ("Nano Banana"); Imagen discontinued

- Imagen is shut down on the Gemini API; Vertex lists `imagen-3.0-*` and `imagen-4.0-*` as
  discontinued (deadline printed 2026-06-30). The `:predict` grammar is kept for migration edges
  only: `instances[].prompt`, `parameters{sampleCount 1–4, aspectRatio 1:1|3:4|4:3|16:9|9:16,
  addWatermark, seed, enhancePrompt, personGeneration allow_all|allow_adult|dont_allow,
  safetySetting, outputOptions{mimeType, compressionQuality}, storageUri, includeRaiReason}`;
  response `predictions[]{bytesBase64Encoded, mimeType, prompt}`. Edit/upscale reference
  (`referenceImages`, `editMode`, `upscaleConfig`) unreachable — `unverified`.
- Current models: `gemini-nano-banana-2.1` (recommended), `gemini-3.1-flash-image`,
  `gemini-3.1-flash-lite-image`, `gemini-3-pro-image`, `gemini-2.5-flash-image` (shutdown
  2027-03-15).
- Documented front door is the **Interactions API**: `POST https://generativelanguage.googleapis.
  com/v1beta/interactions`, `x-goog-api-key` (examples add `Api-Revision: 2026-05-20`). Request
  `{model, input: string | [{type:"text"} | {type:"image", data, mime_type} | {type:"video", uri}],
  response_format{type:"image", mime_type?, aspect_ratio?, image_size?}, tools[{type:
  "google_search", search_types?}], generation_config{thinking_level minimal|medium|high},
  previous_interaction_id}`. Response: `output_image.data` (base64) and `output_text`, or `steps[]`
  with `model_output` steps holding `content[]` blocks `type: text|image` plus `thought` steps.
  Multi-turn editing is by `previous_interaction_id` — a `ProviderRef(kind="interaction")`.
- `generateContent` still documents `generationConfig.responseModalities` (`TEXT|IMAGE|AUDIO`) and
  `imageConfig{aspectRatio, imageSize}` (`1:1, 1:4, 4:1, 1:8, 8:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4,
  9:16, 16:9, 21:9`; `512|1K|2K|4K`, uppercase K), images as `candidates[].content.parts[].
  inlineData{mimeType, data}` — but only under the Live setup schema; whether `generateContent`
  image output is still a recommended path is `unverified`.
- Up to 14 reference images (2.1/3.1 Flash: 10 object + 4 character; Pro: 6/5/3 style). Thinking
  cannot be disabled on Gemini 3 image models and is billed. SynthID on every image. "May not
  match the exact number of images requested." Tokens per image are fixed per size (2.1: 1120 @1K,
  1680 @2K, 2520 @4K; 2.5-flash-image: 1290); $30/M image output tokens for 2.1, $60/M for 3.1
  Flash, $120/M for 3 Pro. No documented partial-image event — `unverified`.

### 2.3 Stability AI v2beta

- Base `https://api.stability.ai`, `Authorization: Bearer`, multipart; `accept: image/*` returns
  bytes (headers `finish-reason`, `seed`, `x-request-id`), `accept: application/json` returns
  `{image (base64), seed, finish_reason}`. 150 req/10 s.
- Generate `/v2beta/stable-image/generate/{core|sd3|ultra}`: `prompt` 1–10000 (`(word:weight)`),
  `aspect_ratio` `21:9|16:9|3:2|5:4|1:1|4:5|2:3|9:16|9:21`, `negative_prompt`, `seed` 0–4294967294,
  `style_preset` (17 values), `output_format` `png|jpeg|webp`; core is 1.5 MP, 3 credits.
- Edit `/v2beta/stable-image/edit/{inpaint|outpaint|erase|search-and-replace|search-and-recolor|
  remove-background|replace-background-and-relight}`. Inpaint: `image`, `prompt`, `mask` (white =
  full strength, black = untouched; auto-resized; falls back to alpha, transparent = inpaint),
  `grow_mask` 0–100; input ≥64 px/side, 4,096–9,437,184 px, 10 MiB; 5 credits. Outpaint:
  `left|right|up|down` 0–2000, `creativity`; 4 credits.
- Upscale `/upscale/{fast|conservative|creative}`; creative and relight are **async**: 200
  `{id}`, then `GET /v2beta/results/{id}` → 202 `{id, status:"in-progress"}` or 200 with the image;
  kept 24 h, same key required; 60 credits. Control `/control/{sketch|structure|style|style-transfer}`.
- Safety: `finish_reason` `SUCCESS|CONTENT_FILTERED` (filtered outputs are **blurred**, not
  withheld); 403 `content_moderation`; 422 `invalid_language`/`public_figure`. 1 credit = $0.01.

### 2.4 Black Forest Labs FLUX API

- Hosts `api.bfl.ai`, `api.eu.bfl.ai`, `api.us.bfl.ai`; header `x-key`. **All async**: `POST
  /v1/{model}` → `{id, polling_url, cost?, input_mp?, output_mp?}` (or `{id, status, webhook_url}`);
  `GET polling_url` / `GET /v1/get_result?id=` → `{id, status, result, progress, details, preview,
  cost}`, `status` ∈ `Task not found | Pending | Reasoning | Generating | Request Moderated |
  Content Moderated | No Card Generated | Ready | Error`. `result.sample` is a signed URL on
  `delivery.*.bfl.ai`, **valid 10 minutes**, no CORS. Use the returned `polling_url` (regional).
  24 active tasks/account (6 for kontext-max), 429 beyond; 402 when out of credits.
- Models: `/v1/flux-2-max|pro|flex|klein-*`, `/v1/flux-kontext-pro|max`, `/v1/flux-pro-1.1`,
  `/v1/flux-pro-1.1-ultra`, `/v1/flux-pro`, `/v1/flux-dev`, `/v1/flux-pro-1.0-fill`, `-expand`;
  canny/depth pages not located (`unverified`).
- `flux-2-pro`: `prompt`, `input_image`…`input_image_8` (multi-reference editing), `width`/`height`
  (min 64), `seed`, `safety_tolerance` 0–7 (org-approved max, 422 otherwise), `output_format`
  `jpeg|png|webp`, `disable_pup`, `webhook_url`, `webhook_secret`, `user`. Kontext: `aspect_ratio`
  3:7–7:3 (~1 MP), `prompt_upsampling`. Fill: `image` (base64, may carry alpha), `mask` (same size,
  white = inpaint), `prompt`, `steps` 15–50, `guidance` 1.5–100, `safety_tolerance` 0–6.
- Pricing: 1 credit = $0.01, FLUX.2 billed per output megapixel (figures not rendered —
  `unverified`); the submit response `cost` is authoritative.

### 2.5 Ideogram

- `https://api.ideogram.ai`, header `Api-Key`, multipart. v2: `POST /v2/image/generate/ideogram-3`
  (+ `-character|-custom-model|-transparent`), `/v2/image/inpaint/ideogram-3`, `/remix/`,
  `/reframe/`, `/replace-background/`, `/describe/`, `/layerize/`, `GET /v2/generations/{id}`.
  v1 `/v1/ideogram-v3/*` is legacy.
- Generate: `prompt`, `negative_prompt`, `seed`, `resolution`, `aspect_ratio`, `rendering_speed`,
  `magic_prompt` (default `auto`), `num_images`, `color_palette`, `style_codes`, `style_type`
  (`AUTO|GENERAL|REALISTIC|DESIGN|FICTION`), `style_preset`, `style_reference_images` (≤10, ≤25 MB),
  `character_reference_images` (1), `enable_copyright_detection`, `async` (default false),
  `webhook_url` (HTTPS, Ed25519-signed), query `dry_run` → `PriceQuote`; enum lists not printed —
  `unverified`. Inpaint mask: black-and-white, same size, **black = edit**. Response
  `{generation_id, seed, data[]{url, prompt, resolution, is_image_safe, seed}}`; `url` empty when
  unsafe; URLs "temporary"; 400/401/422 (safety)/429, with `reject_reason` on 402/429.

### 2.6 Recraft

- `https://external.api.recraft.ai/v1`, Bearer; OpenAI-SDK compatible `POST /images/generations`
  (+ `/raster`, `/vector`); tools `/images/imageToImage|inpaint|outpaint|replaceBackground|
  generateBackground|vectorize|removeBackground|eraseRegion|crispUpscale|creativeUpscale|enhance|
  variateImage`, `/prompts/enhance`, `/styles`, `GET /users/me` (credits).
- Generate: `prompt`, `n` 1–6, `model` (default `recraftv4_1`; `recraftv4_1_vector`,
  `recraftv4_styles`, `recraftv3`…), `size` (`WxH` or `w:h`; list unreachable), `style`,
  `style_id`, `style_match`, `style_references`/`style_reference_urls`, `negative_prompt` (V2/V3),
  `random_seed`, `response_format` `url|b64_json|multipart`, `image_format` `webp|png`,
  `text_layout`, `controls{colors[], background_color, artistic_level, no_text}`.
- Response `{created, credits, data[]{url, image_id}}`; vector is SVG; URLs ~24 h. $0.007–$0.04
  per image; tools priced per call (inpaint $0.04/$0.08, vectorize $0.01, creative upscale $0.25).

### 2.7 Midjourney

No official API; 2026-10 third-party guides report no developer program, and the terms prohibit
automated access. Out of scope.

### 2.8 Adobe Firefly API

`https://firefly-api.adobe.io`; `x-api-key` + `Authorization: Bearer` (OAuth server-to-server
`client_credentials`, scopes `openid,AdobeID,read_organizations,firefly_enterprise,firefly_api,
ff_apis`). Sync v3 endpoints were removed; async `POST /v3/images/generate-async`, `expand-async`,
fill/generate-similar/object-composite async, plus `/v4/images/generate-async` for Image Model 5
(`unverified`; reference pages 404). Submit → `{jobId (urn:ff:jobs:…), statusUrl, cancelUrl}`;
`GET statusUrl` → `{status running|succeeded|failed, result{size{width,height}, outputs[]{seed,
image{url}}, contentClass, altText}}`; pre-signed S3 URLs (expiry unstated). Request (OpenAPI,
truncated): `numVariations` 1–4, `seeds`, `size` (fixed list: 2048x2048, 2304x1792, 1792x2304…),
`contentClass photo|art`, `prompt`/`negativePrompt` ≤1024, references by `uploadId` (`POST
/v2/storage/image`) or `url`; fill takes `image` + mask (`mask{source}` seen on expand only).

### 2.9 Amazon Nova Canvas (Bedrock)

`InvokeModel`, `modelId amazon.nova-canvas-v1:0`, SigV4, synchronous (raise read timeout to
~300 s). Body `{taskType, <task>Params, imageGenerationConfig{width, height, quality standard|
premium, cfgScale 1.1–10, seed, numberOfImages}}`. Tasks: `TEXT_IMAGE` (`text` 1–1024,
`negativeText`, `style`, `conditionImage` + `controlMode CANNY_EDGE|SEGMENTATION` +
`controlStrength`), `COLOR_GUIDED_GENERATION` (`colors[]` ≤10, `referenceImage`), `IMAGE_VARIATION`
(`images[]` 1–5, `similarityStrength` 0.2–1.0), `INPAINTING`/`OUTPAINTING` (`image`, `maskPrompt`
xor `maskImage`; **inpaint black = edit, outpaint white = edit**; `outPaintingMode`),
`BACKGROUND_REMOVAL`, `VIRTUAL_TRY_ON`. Sides 320–4096, ÷16, ratio 1:4–4:1, <4,194,304 px.
Response `{images[] (base64), maskImage?, error?}` — RAI-blocked images are dropped, `error` set.

### 2.10 Azure OpenAI images

`POST https://{resource}.openai.azure.com/openai/deployments/{deployment}/images/generations
?api-version=2025-04-01-preview` or `/openai/v1/images/generations?api-version=preview` with
`model` in the body; `api-key` or Entra bearer. OpenAI grammar (`output_format` PNG/JPEG only),
base64 only, `dall-e-3` retired. Content-filter failures: `{created, error{code:"contentFilter",
message}}`; 5 images/min default quota. A hosting variant of the OpenAI interface (`Custom` host +
`DialectTraits`), not a new codec.

### 2.11 Hosts — Replicate and fal.ai

- Replicate: `POST /v1/predictions` (`version`, `input`, `webhook`, `webhook_events_filter`) or
  `/v1/models/{owner}/{name}/predictions`; `Prefer: wait=1..60`; `GET /v1/predictions/{id}` →
  `{id, status starting|processing|succeeded|failed|canceled, output, error, logs, metrics
  {predict_time}, urls{get, cancel, stream?}, data_removed}`; outputs on `replicate.delivery` need
  the auth header and are **removed after one hour**; inputs as URLs or data URLs; 600 creates/min.
- fal.ai: `POST https://queue.fal.run/{owner}/{app}`, `Authorization: Key …` → `{request_id,
  response_url, status_url, cancel_url, queue_position}`; `GET …/requests/{id}/status` →
  `IN_QUEUE|IN_PROGRESS|COMPLETED` (+ `metrics.inference_time`, `error`); `GET …/requests/{id}`
  for the model-specific output (`fal-ai/flux/dev`: `images[]{url, width, height, content_type},
  seed, has_nsfw_concepts[], prompt`); `?fal_webhook=`; `/status/stream` SSE; expiry per account.

### 2.12 Local — diffusers (in-process peer)

`FluxPipeline`, `FluxImg2ImgPipeline`, `FluxInpaintPipeline`, `FluxControlPipeline` share
`__call__(prompt, prompt_2, negative_prompt, height, width, num_inference_steps, guidance_scale,
num_images_per_prompt, generator, max_sequence_length, output_type="pil", callback_on_step_end)`;
img2img/inpaint add `image`, `mask_image`, `strength`; control adds `control_image`; output
`FluxPipelineOutput.images` (PIL). The in-process adapter implements the port directly
(`route=None`) and maps `callback_on_step_end` to preview chunks — the second fold-law implementation.

## 3. Comparison

| Provider / interface | Ops | Sync/async | Inputs | Mask polarity | Size knob | Output | URL expiry | Usage unit | Moderation signal |
|---|---|---|---|---|---|---|---|---|---|
| OpenAI `images` | generate, edit | sync + SSE partials | data URL, https URL, `file_id` (≤16) | alpha = edit | exact WxH (÷16) or presets | base64 | n/a (DALL-E 60 min) | image tokens | `moderation_blocked`, `moderation` knob |
| OpenAI `responses` tool | generate, edit (multi-turn) | sync + SSE partials | context items, `input_image_mask.file_id` | alpha = edit | presets | base64 item | n/a | tokens | same |
| Google `interactions` | generate, edit by turn | sync (SSE) | base64 parts, video uri | none (prompt) | ratio + 512/1K/2K/4K | base64 | n/a | fixed tokens per size | blocked (details unverified) |
| Google Vertex Imagen | generate/edit/upscale | sync | base64, gcsUri | mask modes | ratio + 1K/2K | base64 or GCS | n/a | per image | `raiFilteredReason` — **discontinued** |
| Stability v2beta | generate, 7 edits, 3 upscales, 4 controls | sync; creative upscale + relight async | multipart | white = edit | ratio enum / fixed MP | bytes or base64 | async 24 h | credits | `CONTENT_FILTERED` (blurred), 403/422 |
| BFL FLUX | generate, multi-ref edit, fill, expand | async (poll/webhook) | base64 (≤8 refs) | white = edit | WxH or ratio | signed URL | **10 min** | credits / MP | `Request|Content Moderated` statuses |
| Ideogram v2 | generate, inpaint, remix, reframe, replace-bg | sync; `async` + webhook | multipart | black = edit | ratio/resolution enums | URL | temporary | per image (`dry_run`) | `is_image_safe=false`, 422 |
| Recraft | generate (raster/vector), 12 tools | sync | multipart / URLs | n/a | WxH or ratio | URL / b64 / multipart | ~24 h | credits | undocumented |
| Adobe Firefly | generate, expand, fill, similar, composite | async job | `uploadId` or URL | mask by source | fixed size list | pre-signed URL | unstated | generative credits | 422 |
| Nova Canvas | 8 task types | sync (long) | base64 | **inpaint black / outpaint white** | WxH (÷16, ≤4.19 MP) | base64 | n/a | per image | dropped + `error` |
| Azure OpenAI | as OpenAI | as OpenAI | as OpenAI | alpha | as OpenAI (no WebP) | base64 | n/a | tokens | `contentFilter` body |
| Replicate / fal | any | job (sync-wait option) | URL / data URL | per model | per model | URL | 1 h / setting | predict seconds / per model | per model |
| diffusers | generate, img2img, inpaint, control | in-process | PIL | white = edit | WxH | PIL | n/a | none | optional checker |

## 4. Canonical IR proposal — `ocai.image`

### 4.1 Identity and shapes

`Capability("image")` with **three operations as separate shapes**: `("image","generate.request"
/"generate.response")`, `("image","edit.request"/"edit.response")`, `("image","upscale.request"/
"upscale.response")`. One `ImageResponse` dataclass is registered under all three response roles so
graphs stay partitioned per operation while codecs share a decoder. **Variation is not a fourth
shape**: OpenAI retired `/variations`, and every surviving provider expresses it as an edit without
a mask (Nova `IMAGE_VARIATION` + `similarityStrength`, Recraft `variateImage`, Ideogram remix,
diffusers `strength`). It is `ImageEditRequest(mode="variation")` with open `EditMode` codes
`inpaint | outpaint | variation | instruct | remove_background | replace_background | control`.
Outpaint directions ride `ImageEditRequest.expand: Expand(left, right, up, down)`; providers that
only take a target size get an APPROXIMATED derivation.

### 4.2 Reference images and masks over the `Source` union

- `ImageReference(source: Source, role: str, id: str | None)`, open roles `input | subject | style
  | character | control | markup`. `SourceBase64`/`SourceUrl` map 1:1; provider file handles are
  `SourceRef(ProviderRef(kind="file"))` (OpenAI `file_id`, Adobe `uploadId`, Gemini Files API uri),
  **provider-scoped**: an OpenAI file id crosses `images` ↔ `responses` unreported and is
  `UNSUPPORTED` across providers. `gs://`/`s3://` stay `SourceUrl` verbatim, censused UNSUPPORTED
  on edges whose provider cannot fetch them.
- `Mask(source: Source | None, prompt: str | None, polarity: str)`, open polarity `edit_white |
  edit_black | edit_transparent`. Polarity is **declared by the caller and never converted by an
  edge**: a provider with a different convention declares the mismatch `UNSUPPORTED` in its
  `EdgeContract`; the facade may offer an explicit `invert_mask()` that rewrites bytes and records
  `SemanticShift("mask_polarity_inverted")`. Mask-by-prompt (Nova `maskPrompt`, Stability
  `search_prompt`) is the same object with `source` absent. Nova's inpaint/outpaint flip is a
  per-mode trait in the Nova fragment, not an IR concept.

### 4.3 Size, aspect, quality — APPROXIMATED vs UNSUPPORTED

`ImageConfig(size: Size | None, aspect_ratio: str | None, resolution: str | None, quality: str, n,
seed, negative_prompt, output: OutputSpec(mime_type, compression, background), safety:
SafetySpec(level, person_generation))`; only one of `size`/`aspect_ratio` per request.

- Exact `size` to a provider accepting arbitrary WxH (OpenAI, Nova, Recraft, FLUX.2): `EXACT`; a
  value outside its divisibility/pixel budget passes **verbatim**, reported `APPROXIMATED` (the
  provider's 4xx becomes a mapped error, never a silent clamp).
- Exact `size` to an aspect-ratio-only provider (Stability, Kontext, Ideogram, Gemini): the edge
  derives the ratio only when it is exactly one of the provider's enumerated ratios, records
  `SemanticShift("size_to_aspect_ratio")` and reports `APPROXIMATED`; any other ratio is
  `UNSUPPORTED`. The response always carries actual `width`/`height`, so loss is observable.
- `resolution` tiers (`1K|2K|4K`) and `quality` (`auto|low|medium|high`) are open codes with the
  verbatim value in a `native` lane (Nova `standard|premium`, OpenAI `xhigh|max`), `ABSENT` where
  a provider has neither; Ideogram `rendering_speed` is an extension.

### 4.4 Response, usage, finish

`ImageResponse(images: list[ImageOutput], finish: FinishInfo, usage: Usage, info: ResponseInfo)`;
`ImageOutput(source: Source, width, height, mime_type, seed, revised_prompt, expires_at: str |
None, safety: ImageSafety(filtered: bool, reason: str, native))`. URL outputs are `SourceUrl` with
`expires_at` from provider knowledge (BFL 10 min, Replicate 1 h, Recraft ~24 h, DALL-E 60 min); a
facade `materialize()` downloads to `SourceBase64` and declares the extra wire call as a
`SemanticShift`. Dropped outputs (Nova, Gemini) become an `ImageSafety(filtered=True)` placeholder
per missing slot plus `finish.reason="content_filter"` — never a shorter list; blurred outputs
(Stability) are returned with `filtered=True` and bytes intact. Usage reuses core `Consumption`
with open units `tokens` (OpenAI, Gemini; modality `image`), `credits` (Stability, BFL, Recraft),
`samples` (per-image pricing), `megapixels` (BFL `output_mp`).

### 4.5 The job pattern for async providers

BFL, Stability creative upscale/relight, Adobe, Ideogram `async`, Replicate and fal follow
architecture §11 step 6 — three `Operation`s: `submit` → `CallResult[JobHandle]` anchored by
`ProviderRef(kind="job", scope=interface, id=<task id>)`; `poll` → `CallResult[JobStatus(state,
progress, native, expires_at)]` with open state `queued | running | succeeded | failed | moderated
| expired | cancelled` (BFL's nine statuses, fal's three, Replicate's five decode with the verbatim
value in `native`); `fetch` → `CallResult[ImageResponse]`. The front door `generate()` is the
facade (step 11) composing the legs, merging usage (BFL settled `cost` lands on the final poll)
and declaring the fan-out. Webhooks are not an operation at v0: `webhook_url`/`webhook_secret`
pass through `provider_options`; `JobHandle` is serializable so a webhook consumer resumes at
`fetch`. The vocabulary (`Job`/`JobHandle`, never `Operation`) is H6 `ocai.jobs`.

### 4.6 Streaming partials and the fold-by-replacement law

`ImageChunk(type, seq, index, partial: ImageOutput | None, end: StreamEnd | None)` with
`ChunkType` `imagePartial`, `imageStop`, `streamStop`; delta type `DeltaImageReplace(source)`.
Law: **fold keeps, per `index`, only the last `imagePartial` and replaces it with the `imageStop`
payload**; `fold(stream(request)) == complete(request)` holds because the terminal event carries
the full image and `StreamEnd(usage, finish, report)` the authoritative usage — OpenAI's +100
tokens per partial must appear in the fold-triple fixture and the report must say partials were
billed. An aborted stream seals the last partial `incomplete`. Fixtures: OpenAI
`image_generation.partial_image` ×N + `completed`, and the diffusers `callback_on_step_end` pair.

### 4.7 What rides extensions (censused in `spec/extensions/`)

OpenAI `moderation`, `input_fidelity`, `complexity`, `safety_identifier`, `markup`, `svg`, GIF
frame knobs. Google `thinking_level`, `tools`, `person_generation`, `add_watermark`,
`enhance_prompt`. Stability `style_preset`, `grow_mask`, `creativity`, `cfg_scale`,
`search_prompt`. BFL `safety_tolerance`, `prompt_upsampling`/`disable_pup`, `steps`, `guidance`,
`webhook_*`. Ideogram `magic_prompt`, `rendering_speed`, `style_codes`, `color_palette`,
`enable_copyright_detection`. Recraft `controls`, `text_layout`, `style_id`. Nova `cfgScale`,
`controlMode`, `controlStrength`, `style`, `similarityStrength`, `outPaintingMode`. Adobe
`contentClass`, `visualIntensity`, `promptBiasingLocaleCode`. Hosts: the model input schema under
`provider_options`. `negative_prompt` and `seed` clear the ≥3-interface bar and are first-class.

## 5. Priorities, effort, order

| Provider | Priority | Effort (WUs) | Rationale |
|---|---|---|---|
| OpenAI `images` (gpt-image-2.5) | P0 | 3 (IR + generate; edit + mask + file refs; streaming fold triples) | Sync, base64, token usage, the only partial-image stream — proves the fold-by-replacement ratchet |
| Google `interactions` (Nano Banana) | P0 | 2 | Second generate/edit interface for the three-lane law; `previous_interaction_id` exercises interface-scoped refs; codec later serves video |
| Stability v2beta | P1 | 3 (generate; edit family; async upscale) | Widest edit/upscale/control surface; first async leg on a sync provider |
| BFL FLUX | P1 | 2 | Pure job pattern; 10-minute URL expiry forces `expires_at` + `materialize()` |
| Azure OpenAI | P1 | 1 | `Custom` host + `DialectTraits` over the OpenAI codec |
| OpenAI `responses` image tool | P1 | 1 | Sibling-interface migration proof reused from chat |
| fal.ai / Replicate hosts | P2 | 2 | Job legs + `provider_options` schemas (Flux dev, SDXL) |
| diffusers in-process | P2 | 1 | Local/remote parity; second fold-law implementation |
| Amazon Nova Canvas | P2 | 2 | SigV4 plugin, mask-polarity census, dropped-output honesty |
| Ideogram v2 | P2 | 1 | Sync + optional async; black-mask fixture |
| Recraft | P2 | 1 | OpenAI-compatible grammar; vector output extension |
| Adobe Firefly | P3 | 2 | OAuth S2S, async-only, unstable reference pages |
| Vertex Imagen | none | — | Discontinued; migration edges only on request |
| Midjourney | none | — | No API |

**Implement first: OpenAI Images.** Synchronous and base64 (no expiry machinery), it covers
generate + edit + mask + multi-reference + file-id `SourceRef` in one interface, reports usage in
tokens, and is the only provider with partial-image streaming — so the streaming ratchet ships with
the first edge instead of being retrofitted. Second: Google Interactions (codec shared with video,
second data point per knob). Third: Stability, whose async creative upscale lands the job pattern
on a provider already in the catalog; define the `ocai.jobs` vocabulary before that WU.

## 6. Unverified items

- Gemini: `generateContent` image output beside Interactions; partial-image SSE events.
- Vertex Imagen edit/upscale reference and exact discontinuation dates (pages redirected).
- BFL canny/depth pages, per-megapixel prices, `result.*` fields beyond `sample`.
- Ideogram enum values and URL lifetime; Recraft size list and tool-endpoint schemas.
- Adobe v3/v4 async reference pages (404), mask field on fill, presigned URL lifetime.
- Midjourney status rests on third-party reporting only.

## Sources (read 2026-11-10)

- https://developers.openai.com/api/docs/api-reference/images
- https://developers.openai.com/api/docs/guides/image-generation
- https://aistudio.google.com/docs/image-generation
- https://aistudio.google.com/docs/imagen
- https://aistudio.google.com/docs/pricing
- https://aistudio.google.com/api-reference/generate-content
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/image/generate-images
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/imagen-api (redirects to the generic predict reference)
- https://docs.stability.ai/api-reference
- https://docs.stability.ai/api-reference/generate/stable-image-core.md
- https://docs.stability.ai/api-reference/edit/inpaint.md
- https://docs.stability.ai/api-reference/edit/outpaint.md
- https://docs.stability.ai/api-reference/upscale/creative-upscale-async.md
- https://docs.stability.ai/api-reference/results/fetch-async-generation-result.md
- https://docs.stability.ai/pricing.md
- https://docs.bfl.ai/quick_start/generating_images
- https://docs.bfl.ai/kontext/kontext_text_to_image
- https://docs.bfl.ai/integration_guidelines
- https://docs.bfl.ml/api-reference/models/generate-or-edit-an-image-with-flux2-[pro].md
- https://docs.bfl.ml/api-reference/models/inpaint-an-image-with-flux1-fill-[pro]-using-an-input-image-and-mask.md
- https://docs.bfl.ml/api-reference/utility/get-result.md
- https://docs.bfl.ml/flux_2/flux2_image_editing.md
- https://docs.bfl.ml/quick_start/pricing.md
- https://developer.ideogram.ai/v2/llms.txt
- https://developer.ideogram.ai/v2/api-reference/images/generate/ideogram-3.md
- https://developer.ideogram.ai/api-reference/api-reference/generate-v3
- https://developer.ideogram.ai/api-reference/api-reference/edit-v3
- https://www.recraft.ai/docs
- https://www.recraft.ai/docs/api-reference/endpoints.md
- https://www.myarchitectai.com/blog/midjourney-apis (third-party; Midjourney publishes no API docs)
- https://developer.adobe.com/firefly-services/docs/firefly-api/guides/how-tos/using-async-apis
- https://cdn.jsdelivr.net/npm/@adobe/firefly-apis@2.0.1/oas/FFApiOpenApi3.json
- https://docs.aws.amazon.com/nova/latest/userguide/image-gen-req-resp-structure.html
- https://docs.aws.amazon.com/nova/latest/userguide/image-gen-access.html
- https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/dall-e
- https://replicate.com/docs/reference/http
- https://fal.ai/docs/model-endpoints/queue
- https://fal.ai/models/fal-ai/flux/dev/api
- https://huggingface.co/docs/diffusers/api/pipelines/flux
