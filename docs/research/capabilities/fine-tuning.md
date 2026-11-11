# Fine-tuning

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

**Currency.** Researched 2026-11-10 against current provider documentation
(URLs in Sources). This family is contracting: OpenAI is winding its
fine-tuning platform down (no new jobs after 2027-01-06), Mistral marks
fine-tuning "deprecated and no longer actively supported", Cohere deprecated
it on 2025-09-15, and the only Claude model ever fine-tunable (Claude 3 Haiku
on Bedrock) has reached end of life per an AWS blog notice (*unverified*
against the Bedrock table, which still lists it). Numbers and states are
dated; *unverified* marks claims not confirmed from an official page.

**Scope.** Provider-hosted training jobs that produce a new model id, their
dataset formats, lifecycle, evaluation hooks, and how the resulting model id
enters ocai's routing grammar.

## Provider survey

### OpenAI

- **Availability.** Wind-down announced 2026-05-07: organizations that never
  fine-tuned cannot start; job creation ended 2026-07-02 for organizations
  without fine-tuned-model inference in the prior 60 days; 2027-01-06 ends
  job creation for everyone. Inference on fine-tuned models continues until
  the base model is deprecated (`gpt-4.1-nano-2025-04-14` shut down
  2026-10-23; `gpt-4.1-2025-04-14` and `gpt-4.1-mini-2025-04-14` shut down
  2027-01-14).
- **Methods.** `method.type` ∈ `supervised`, `dpo`, `reinforcement`.
  - SFT: JSONL lines `{messages: [{role, content}…], tools?,
    parallel_tool_calls?}`; assistant turns may carry `tool_calls`; at
    least 10 lines; hyperparameters `n_epochs`, `batch_size`,
    `learning_rate_multiplier` under `method.supervised.hyperparameters`.
  - Vision SFT on `gpt-4o-2024-08-06` (image inputs in messages).
  - DPO: lines `{input: {messages, tools?, parallel_tool_calls?},
    preferred_output, non_preferred_output}`; one-turn only;
    `method.dpo.hyperparameters.beta` in (0, 2], default `"auto"`.
  - RFT: graders `StringCheckGrader`, `TextSimilarityGrader`,
    `PythonGrader`, `ScoreModelGrader`, `MultiGrader` under
    `method.reinforcement.grader`; hyperparameters `reasoning_effort`
    (`default`/`low`/`medium`/`high`), `compute_multiplier`,
    `eval_interval`, `eval_samples`, plus the usual three.
- **Job object.** `status` ∈ `validating_files`, `queued`, `running`,
  `pausing`, `paused`, `succeeded`, `failed`, `cancelled`;
  `fine_tuned_model` (null until done), `result_files`, `trained_tokens`,
  `error {code, message, param}`, `training_file`, `validation_file`,
  `seed`, `metadata` (≤ 16 pairs), `integrations[]` (`type: "wandb"` with
  `project`, `entity`, `name`, `tags`), `estimated_finish`.
- **Sub-resources.** Checkpoints (`fine_tuned_model_checkpoint`,
  `step_number`, `metrics`; only the last three epochs retained), events
  (type `moderation_checks` reports category results), cancel
  `POST /fine_tuning/jobs/{id}/cancel`; pause/resume endpoints exist in the
  reference (not read on this pass, *unverified*).
- **Resulting id.** `ft:gpt-4.1-nano-2025-04-14:openai::BTz2REMH`;
  checkpoints `ft:{base}:{org}:{suffix}:{id}:ckpt-step-{n}`. Deleting needs
  the Owner role (`DELETE /models/{model}`). The model object carries
  `shutdown_date`.
- **Notification.** webhooks `fine_tuning.job.succeeded`, `.failed`,
  `.cancelled`.

### Azure OpenAI (Microsoft Foundry)

- `POST {endpoint}/openai/v1/fine_tuning/jobs` with `model`,
  `training_file`, `validation_file` (uploaded with `purpose=fine-tune`),
  `suffix`, `method.supervised.hyperparameters` (`batch_size`,
  `learning_rate_multiplier`, `n_epochs`, each integer/number or `"auto"`),
  and an Azure-only `trainingType` (for example `GlobalStandard`).
- Monitoring: `GET …/fine_tuning/jobs/{id}`, `/events`, `/checkpoints`;
  `result_files` may include a CSV of `train_loss`, `full_valid_loss`,
  `train_mean_token_accuracy`, `full_valid_mean_token_accuracy`.
- Lifecycle extras: pause/resume/cancel through the `azd ai finetuning`
  extension; the fine-tuned model must be **deployed** in the Foundry portal
  before inference and deployments bill independently of training.
- Methods beyond SFT (DPO, RFT) are referenced from the overview but were
  not read on this pass (*unverified*).

### Google Vertex AI (Gemini tuning)

- `POST https://{region}-aiplatform.googleapis.com/v1/projects/{p}/locations/{l}/tuningJobs`
  (Gemini 3+ use the `us`/`eu` multi-region endpoint) with `baseModel`,
  `tunedModelDisplayName` (≤ 128 chars), `supervisedTuningSpec
  {trainingDatasetUri (GCS JSONL), validationDatasetUri,
  hyperParameters {epochCount, learningRateMultiplier, adapterSize ∈
  ADAPTER_SIZE_ONE | TWO | FOUR | EIGHT | SIXTEEN}}`, optional
  `exportLastCheckpointOnly`, `encryptionSpec.kmsKeyName`, `serviceAccount`,
  `evaluationConfig`.
- Dataset: JSONL; the reference page recommends 100–500 examples minimum;
  the per-line schema (`contents` with `user`/`model` roles,
  `systemInstruction`) was not shown on the fetched page (*unverified*).
- States: samples poll while `JOB_STATE_PENDING` or `JOB_STATE_RUNNING`;
  terminal names not listed on the page (generic Vertex `JobState` applies;
  *unverified* for tuning).
- Output: `tunedModel.model` = `projects/…/locations/…/models/{MODEL_ID}`,
  `tunedModel.endpoint` = `projects/…/locations/…/endpoints/{ENDPOINT_ID}`,
  `tunedModel.checkpoints[]` (id, epoch, step, endpoint), `experiment`.
  Methods `tuningJobs.list`, `.get`, `.cancel`.
- Base models (2026-11-10): Gemini 3.5 Flash-Lite, 3.5 Flash, 3.1
  Flash-Lite, 2.5 Pro, 2.5 Flash-Lite, 2.5 Flash, `translation-llm-002`;
  reinforcement tuning (`reinforcementTuningSpec`, `v1beta1`) on 3.5 Flash
  and 3.1 Flash-Lite; preference tuning documented on its own page.

### Anthropic

- No fine-tuning product on the Claude API; the Claude Platform on AWS page
  lists Files, Skills and identical model ids but nothing about
  customization.
- Bedrock's fine-tuning table lists exactly one Claude model:
  `anthropic.claude-3-haiku-20240307-v1:0:200k` (us-west-2), dataset format
  `{"system": …, "messages": [{role: user|assistant, content}]}` single- or
  multi-turn, quotas: minimum 32 records, 10,000 training / 1,000 validation
  records, 32,000 tokens, 10 GB training / 1 GB validation files. An AWS blog
  notice says Claude 3 Haiku reached end of life on 2026-09-10 (*unverified*
  against the Bedrock table). Practical status: **no currently fine-tunable
  Claude model** should be assumed.

### Mistral

- Capability page: "This feature is deprecated and is no longer actively
  supported." Pricing floor $4 per job and $2 per model per month remain
  listed. SFT (text and vision) and a "Classifier Factory" are the two
  services. The API reference moved under a "Deprecated" section; job
  fields and status enums were not reachable on this pass (*unverified*).
  Fine-tuned models appear in `GET /v1/models` as `FTModelCard` with
  `root`, `job`, `archived`, and can be renamed, archived and deleted via
  `/v1/fine_tuning/models/{model_id}`.

### Together

- `POST /v1/fine-tunes`: required `training_file`, `model`; data options
  `validation_file`, `packing`, `max_seq_length`; training `n_epochs`,
  `n_checkpoints` (≤ 10), `n_evals`, `batch_size` (int or `"max"`),
  `learning_rate`, `warmup_ratio`, `weight_decay`, `lr_scheduler`, early
  stopping fields; `training_method {method: "sft", train_on_inputs}` or
  `{method: "dpo", dpo_beta, rpo_alpha, dpo_normalize_logratios_by_length,
  dpo_reference_free, simpo_gamma}`; `training_type {type: "Full"}` or
  `{type: "Lora", lora_r, lora_alpha, lora_dropout,
  lora_trainable_modules}`; `from_checkpoint`; W&B fields; HF import/export.
- Status: `pending`, `queued`, `running`, `compressing`, `uploading`,
  `cancel_requested`, `cancelled`, `error`, `completed`. Response carries
  `model_output_name`, `total_price`, `token_count`, `events`, `progress`.
- Serving: dedicated endpoint or download; serverless not mentioned.

### Fireworks

- Datasets: `POST /datasets` then `POST /datasets/{id}:upload`; JSONL with
  `messages` (roles `system`/`user`/`assistant`/`tool`, `weight: 0` excludes
  a turn from loss) and optional `tools`; 3 to 3,000,000 lines.
- `POST /v1/accounts/{account_id}/supervisedFineTuningJobs` with
  `baseModel` (or `warmStartFrom`), `dataset`, `outputModel`, `epochs`,
  `learningRate`, `loraRank` (default 8 via CLI, max 128, 0 = full
  parameter), `batchSizeSamples`, `maxContextLength`, `evaluationDataset`,
  `wandbConfig`.
- `JobState` has 20 values including `JOB_STATE_CREATING`, `_VALIDATING`,
  `_PENDING`, `_RUNNING`, `_WRITING_RESULTS`, `_COMPLETED`, `_FAILED`,
  `_CANCELLING`, `_CANCELLED`, `_EXPIRED`, `_RE_QUEUEING`, `_IDLE`,
  `_EARLY_STOPPED`, `_PAUSED`, `_DELETED`, `_ARCHIVED`.
- Output model `accounts/{account}/models/{id}`; on-demand (dedicated)
  deployment is "the only supported method for serving trained models";
  DPO/ORPO share the SFT settings; reinforcement fine-tuning endpoints
  exist (`reinforcementFineTuningJobs`, not read in depth).

### Bedrock custom models

- `CreateModelCustomizationJob`; `customizationType` ∈ `FINE_TUNING`,
  `CONTINUED_PRE_TRAINING`, `DISTILLATION`, `REINFORCEMENT_FINE_TUNING`,
  `IMPORTED`; job `status` ∈ `InProgress`, `Completed`, `Failed`,
  `Stopping`, `Stopped`; outputs `customModelArn`
  (`arn:aws…:custom-model/{base}/{id}`), `customModelName`.
- Dataset formats: `{"prompt","completion"}` for non-conversational models
  (Titan, Cohere Command, Llama 3.1); Converse format
  `{"schemaVersion": "bedrock-conversation-2024", "system": [...],
  "messages": [{role, content: [{text}|{image: {format, source:
  {s3Location}}}]}]}` for Llama 3.2/3.3 and Nova; Claude 3 Haiku format
  above; `{"image-ref","caption"}` for image models. Quotas per model
  (for example Llama 3.1: 100–10,000 records, 16,000 tokens).
- Fine-tunable models (2026-11-10): Nova 2 Lite, Nova Canvas/Lite/Micro/Pro,
  Titan Image Generator v2, Titan Multimodal Embeddings, Claude 3 Haiku,
  Llama 3.1 8B/70B, Llama 3.2 1B/3B/11B/90B, Llama 3.3 70B. Billing: tokens
  × epochs plus monthly model storage. Inference requires provisioned
  throughput or on-demand custom-model deployment (*unverified* detail on
  this pass).

### Cohere

Fine-tuning deprecated 2025-09-15 (chat, classify, rerank variants). Not
surveyed further.

## Dataset format divergences (the honesty problem)

| Provider | Line schema | System prompt | Tools | Preference pairs | Weighting |
|---|---|---|---|---|---|
| OpenAI SFT | `{messages}` | as a `system` message | `tools`, `parallel_tool_calls`, `tool_calls` | DPO: `input`/`preferred_output`/`non_preferred_output` | `weight` not shown on current page |
| Azure OpenAI | same as OpenAI | same | same | same | same |
| Vertex | JSONL (schema *unverified*) | `systemInstruction` (*unverified*) | *unverified* | preference tuning page | n/a |
| Bedrock Converse | `schemaVersion` + `system[]` + `messages[].content[]` | `system[].text` | not in format | no | no |
| Bedrock Claude 3 Haiku | `{system, messages}` with string content | `system` string | no | no | no |
| Bedrock legacy | `{prompt, completion}` | none | no | no | no |
| Together | JSONL/Parquet; conversational, instruction, preference | per schema | per schema | DPO | `train_on_inputs` |
| Fireworks | `{messages, tools?}` | `system` role | OpenAI function definitions | DPO/ORPO | `weight: 0` per message |

A canonical dataset IR would have to carry chat-shaped examples (already the
`ocai.chat` request/response IR), tool definitions (already in the IR),
preference pairs (new), and per-turn loss weights (new). The conversion is
total only toward OpenAI-shaped targets; toward Bedrock legacy or Claude 3
Haiku it drops tools and content parts (`DROPPED`, reportable).

## Resulting model ids as routing resources

The front door grammar (§11 step 11) is `"<provider>/<resource>"`, split on
the first slash, resource may contain slashes. Fine-tuned ids fit without
change:

| Provider | Resource string | Note |
|---|---|---|
| OpenAI | `openai/ft:gpt-4.1-mini-2025-04-14:acme:support:AbC123` | colons are legal in the resource |
| Azure OpenAI | `azure-openai/<deployment-name>` | the deployment, not the model id, is the routing key |
| Vertex | `google-vertex/projects/…/locations/…/endpoints/<ENDPOINT_ID>` | resource contains slashes — allowed by the grammar |
| Bedrock | `bedrock/arn:aws:bedrock:…:custom-model/…` | ARN as resource; or a provisioned-throughput ARN |
| Together | `together/<model_output_name>` | dedicated endpoint required |
| Fireworks | `fireworks/accounts/<account>/models/<id>` | slashes again |

A fine-tuned model name is therefore a `ProviderRef(kind="model",
scope=PROVIDER)` when it appears as *data* (in a job result) and an
`EndpointSpec.resource` when it appears as *routing*. It must never be a
field in a request IR (§11 step 3). `CapabilityProfile` keys are matched on
`model_pattern`; a profile for `ft:gpt-4.1-mini-2025-04-14:*` inheriting the
base model's facts is the natural pattern and already expressible.

## Canonical proposal (if and when built)

- `Capability("tuning")` with shapes `tuning.create.request/response`,
  `tuning.get`, `tuning.cancel`, `tuning.list`, plus `tuning.dataset` as a
  file-shaped payload consumed through the files capability. Jobs compose
  over `ocai.jobs` (`ProviderRef(kind="job")`, one `CallResult` per leg);
  the terminal result is `TunedModel(ref: ProviderRef(kind="model"),
  checkpoints: list[ProviderRef], metrics: extensions)`.
- Method as open code (`supervised`, `dpo`, `reinforcement`, `distillation`,
  `continued_pretraining`) with the provider's native method preserved;
  hyperparameters as a censused extension bag per provider (`spec/extensions/
  tuning.<provider>.schema.json`) because no two providers share names
  (`n_epochs` vs `epochCount` vs `epochs`; `learning_rate_multiplier` vs
  `learningRateMultiplier` vs absolute `learning_rate`).
- Graders (OpenAI RFT) and reward Lambdas (Bedrock RFT) have no common
  shape; they stay in `provider_options`.
- Evaluation hooks: OpenAI `result_files`/W&B, Azure CSV metrics, Vertex
  `evaluationConfig`, Together `n_evals`, Fireworks `evaluationDataset` —
  all provider-local; the eval satellite (H7) consumes them through the
  ledger, the kernel only preserves them.

## Priority: P3 for the kernel, platform-tier if at all

Arguments:

1. **The market is shrinking.** OpenAI ends new jobs in January 2027,
   Mistral and Cohere have deprecated, Anthropic never offered it, and the
   remaining surfaces (Vertex, Bedrock, Together, Fireworks, Azure) all
   require a *deployment* step outside the training API before the model
   can be called. A provider-neutral training port would abstract four very
   different control planes for a feature enterprises use rarely.
2. **No conversion graph is needed for the valuable part.** What enterprises
   need from ocai is to *route to* a fine-tuned model with the same honesty
   as to a base model. That is already covered by the front-door grammar and
   `CapabilityProfile` patterns above; it costs one documentation rule, not
   a capability.
3. **Dataset conversion is lossy toward every non-OpenAI target** and the
   formats are moving (Bedrock has three). The honesty machinery would spend
   most of its reports saying `DROPPED`.
4. **The scope litmus still admits it** (wire dialects vary), so when a
   product needs it, build it as a platform-tier package over `ocai.jobs`
   and the files capability, after both exist. Do not touch `ocai.core`.

Effort if pursued: one WU for `TunedModel`/method codes + Vertex + Bedrock
(the two non-deprecated hyperscaler surfaces), one for Together + Fireworks.
Recommended now: a two-line note in `docs/architecture.md` §3.4 stating that
fine-tuned ids are ordinary resources, and nothing else.

## Sources (read 2026-11-10)

- https://developers.openai.com/api/docs/guides/model-optimization
- https://developers.openai.com/api/docs/guides/supervised-fine-tuning
- https://developers.openai.com/api/docs/guides/direct-preference-optimization
- https://developers.openai.com/api/reference/resources/fine_tuning
- https://developers.openai.com/api/reference/resources/models
- https://developers.openai.com/api/docs/deprecations
- https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/fine-tuning
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/tuning
- https://platform.claude.com/docs/en/build-with-claude/claude-platform-on-aws
- https://docs.aws.amazon.com/bedrock/latest/userguide/custom-models.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/custom-model-fine-tuning.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/model-customization-prepare.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_ModelCustomizationJobSummary.html
- https://docs.mistral.ai/capabilities/finetuning/
- https://docs.mistral.ai/api/endpoint/models
- https://docs.together.ai/docs/fine-tuning-overview
- https://docs.together.ai/reference/post-fine-tunes
- https://docs.fireworks.ai/fine-tuning/fine-tuning-models
- https://docs.fireworks.ai/api-reference/create-supervised-fine-tuning-job
- https://docs.cohere.com/docs/fine-tuning
- https://aws.amazon.com/blogs/machine-learning/fine-tune-anthropics-claude-3-haiku-in-amazon-bedrock-to-boost-model-accuracy-and-quality/ (EOL notice, via search snippet)
