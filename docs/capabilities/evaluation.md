# Evaluation

**Currency:** researched 2026-11-10 against official documentation as
published that day. This market is contracting: three of the fourteen
platforms surveyed are sunset, retired, or scheduled to shut down within the
month. Anything not confirmed from an official page is marked *unverified*.

**Status:** planned. The eval module is "reproducible evaluation runs keyed by
`Route` + catalog lock hash + `FidelityReport`" (platform README; horizon
H7). Nothing is implemented.

## 1. Why this family matters to ocai

Horizon H7 states the thesis: *a regression is attributable to the prompt, the
provider revision, or the conversion — not smeared across all three.* Every
eval product below records a model name and some config metadata next to a
score. None records the *interface* and *dated revision* the call went
through, the hash of the conversion logic, or what that conversion dropped.
ocai's ledger is exactly that missing column. The eval satellite's value is
not a new scorer; it is the join between a score and a `Route`.

## 2. Landscape

### 2.1 What an eval run consists of (common model)

Every surviving platform reduces to the same record:

```
{example_id, input, expected?, output,
 scores[{name, value (number | label), rationale?, source?}],
 run_id, trace_id?, metadata{model, config, ...}}
```

- **Dataset / examples** — Braintrust `EvalCase(input, expected, metadata,
  tags, id)`; LangSmith examples `(inputs, outputs, metadata, split)`;
  Langfuse `DatasetItem(input, expectedOutput, metadata, sourceTraceId)`;
  Phoenix examples `(input, output, metadata)`; DeepEval `Golden(...)`; Ragas
  `SingleTurnSample(user_input, retrieved_contexts, response, reference)`;
  promptfoo `tests[].vars`; Vertex `prompt`/`reference` columns; Bedrock JSONL
  `{"prompt", "referenceResponse", "category"}`.
- **Task / target** — a callable over the example (`task`, `target`,
  `function`), or a prompt template plus a model for the hosted services.
- **Scorers** — code, LLM-as-judge, human, pairwise. Judge output is a value
  plus a rationale everywhere (`EvaluationResult(score, label, explanation)`
  in Phoenix, `score` + `reason` in DeepEval, `{key, score, comment}` in
  LangSmith, `Evaluation(name, value, comment)` in Langfuse).
- **Experiment comparison** — immutable run snapshots compared against a
  baseline (Braintrust `base_experiment_name`, `ScoreSummary{improvements,
  regressions, diff}`; LangSmith pairwise `evaluate(target=[exp_a, exp_b])`;
  Langfuse `DatasetRun`; Weave Compare view; Vertex `baseline_model_response_column_name`).
- **Trace link** — one trace or span per example on Braintrust, LangSmith,
  Langfuse (`DatasetRunItem.traceId/observationId`), Phoenix (OTel), Weave,
  Galileo; none on OpenAI Evals, Vertex, Bedrock.

### 2.2 Platforms

| Platform | Run model / SDK shape | License / hosting | Export / import | Status |
|---|---|---|---|---|
| Braintrust | `Eval(name, data, task, scores, experiment_name, base_experiment_name, trial_count, ...)`; `POST /v1/experiment/{id}/insert` | hosted; `autoevals` MIT | CSV/JSON export; `as_dataset()` | live |
| LangSmith | `evaluate(target, data, evaluators, experiment_prefix, ...)`; pairwise `evaluate_comparative`; `openevals` MIT | hosted / self-hosted enterprise | JSONL `GET /api/v1/datasets/{id}/jsonl`; CSV; OpenAI Evals JSONL download | live |
| Langfuse | `run_experiment(name, data, task, evaluators, run_evaluators)`; scores `POST /api/public/scores` (`dataType` ∈ NUMERIC, CATEGORICAL, BOOLEAN, TEXT; `source` ∈ API, EVAL, ANNOTATION) | MIT outside `ee/`; self-hostable | CSV import; scheduled Parquet/CSV/JSON/JSONL export to blob storage | live |
| Arize Phoenix | `run_experiment(dataset, task, evaluators)`; evaluator traced via OTel; OpenInference `EVALUATOR` span kind and `evaluation.*`/`annotation.*` lanes | ELv2 (source-available) | CSV; CLI JSON; OpenAI fine-tuning and Evals JSONL | live |
| W&B Weave | `weave.Evaluation(dataset, scorers, trials).evaluate(model)`; `EvaluationLogger` imperative path | SDK Apache-2.0; hosted | *unverified* | live |
| DeepEval | `LLMTestCase(input, actual_output, expected_output, context, retrieval_context, tools_called, ...)`; `GEval(name, criteria, evaluation_params, rubric, threshold)`; pytest `assert_test` | Apache-2.0; Confident AI hosted | JSON/CSV goldens | live |
| Ragas | `SingleTurnSample`/`MultiTurnSample`; `evaluate()` marked deprecated in favour of `DiscreteMetric`/`ascore` | Apache-2.0 | HF Datasets in, pandas out | live |
| promptfoo | `promptfooconfig.yaml` with `prompts` × `providers` × `tests[{vars, assert[{type, value, threshold, weight, metric}]}]`; graders `llm-rubric`, `g-eval`, `factuality`, `context-faithfulness`, …; red-team plugins | MIT | YAML/JSON/JSONL/CSV in; HTML/JSON/CSV/JSONL/JUnit out | live; OpenAI names it as the migration target |
| OpenAI Evals API | eval = `data_source_config` + `testing_criteria` (graders `string_check`, `text_similarity`, `label_model`, `score_model`, `python`); run `data_source` ∈ `jsonl`, `completions`, `responses`; templates over `item.*` and `sample.*` | hosted | JSONL `{"item": {...}}` | **read-only since 2026-10-31; shutdown 2026-11-30** |
| Vertex Gen AI evaluation | GenAI client `client.evals.run_inference(model, src)` → `client.evals.evaluate(dataset, metrics)`; adaptive rubrics (`GENERAL_QUALITY`, `INSTRUCTION_FOLLOWING`, …), static (`GROUNDING`, `SAFETY`), computed (`rouge_l`, `bleu`, `exact_match`); legacy `EvalTask(dataset, metrics, experiment)` with `PointwiseMetric`/`PairwiseMetric` | hosted | DataFrame / GCS JSONL | live |
| Bedrock model evaluation | `CreateEvaluationJob{applicationType ModelEvaluation\|RagEvaluation, evaluationConfig{automated{datasetMetricConfigs, evaluatorModelConfig}}, inferenceConfig, outputDataConfig{s3Uri}}`; judge metrics `Builtin.Correctness`, `Builtin.Completeness`, `Builtin.Faithfulness`, … | hosted | JSONL in S3 (≤ 1000 prompts) | live |
| Humanloop | — | — | — | **sunset 2025-09-08** (team joined Anthropic) |
| Patronus AI | — | — | — | **evaluation platform retired**; Lynx/GLIDER remain as research artifacts |
| Galileo | `run_experiment(experiment_name, dataset, function\|prompt_template, metrics)`; Luna-2 small-model metrics (enterprise) | hosted / self-hosted enterprise | *unverified* | live |

### 2.3 Open and shared formats

- **No cross-vendor eval-case standard exists.** The OpenAI `{"item": …}`
  JSONL survives only as an interchange shape exported by LangSmith and
  Phoenix; its consuming API shuts down 2026-11-30.
- **promptfoo YAML** is the most widely consumed declarative config and the
  one OpenAI points migrating users at.
- **OTel GenAI** defines evaluation *results*: `gen_ai.evaluation.name`,
  `gen_ai.evaluation.score.value`, `gen_ai.evaluation.score.label`,
  `gen_ai.evaluation.explanation`, correlated by `gen_ai.response.id` /
  `gen_ai.conversation.id`, carried on the `gen_ai.evaluation.result` event
  (status *Development*, now in the `semantic-conventions-genai` repository).
- **OpenInference** defines `openinference.span.kind=EVALUATOR` and the
  `evaluation.*` / `annotation.*` attribute lanes.
- **Inspect AI** `Sample(input, target, id, choices, metadata, files, setup,
  sandbox)` with `FieldSpec` mapping is the most explicit open per-case
  schema; "Every Eval Ever" (IBM/HF/TUM) standardizes *results* reporting
  across HELM, lm-eval-harness, and Inspect.

## 3. What the kernel has today

- The ledger per call: `Route(capability, node, requested_interface,
  requested_tag, reason, catalog_hash, host)`, `FidelityReport` (per-edge
  `FieldLoss`/`SemanticShift`, derived `lossless`), `Usage`, `raw`.
- `Catalog.lock()` — the hash that makes a run's conversion logic
  reproducible; pinning by `(interface, tag)` makes the provider wire revision
  explicit.
- `canonjson.semantic_equal` — the equality predicate; `canonjson` bytes are
  the natural key for "same request" and the content address for an
  archived exchange.
- Recorded HTTP/SSE pairs under `python/packages/*/tests/http/` (rule 10) —
  the de facto replay format, Python-only, not yet in `spec/` (**gap G-02**).
- Per-edge golden fixtures, unknown-X vectors, and fold triples in
  `spec/fixtures/`; no fixture proves a whole multi-turn transcript
  round-trips (**gap G-03**).
- `CallContext(tags)` — the slot an eval run uses to stamp `run_id` and
  `example_id` onto every call it makes.
- `ChatConfig.seed` (best-effort determinism) — exists, but determinism in
  this family comes from *replay*, not from seeds.

## 4. Verdict (H7): eval is a satellite on the ledger

### 4.1 What the satellite is

`ocai-eval` is a thin runner, not a scorer library. Its one invariant: every
model call made during a run goes through an ocai port, so every output row
carries `Route`, `catalog_hash`, and `FidelityReport` — the three columns no
incumbent has. It does not compete on judges (the market has `autoevals`,
`openevals`, DeepEval, Ragas, promptfoo graders — all permissively licensed
and all callable from a task function); it competes on *attribution*.

Record shape (additive over the common denominator in §2.1):

```
{example_id, input, expected?, output,
 scores[...], run_id, trace_id?,
 ocai: {route: Route, catalog_hash, ir_revision, report: FidelityReport,
        usage: Usage, exchange_ref?}}
```

Three regressions become separable by sorting on three columns: same
`catalog_hash` and `route.node` but a different prompt → the prompt; same
prompt and `catalog_hash` but a different `route.node.tag` → the provider
revision; same prompt and `route.node` but a different `catalog_hash` or a
changed loss census → the conversion.

### 4.2 Deterministic replay

The second thing no incumbent has: an eval run can be re-executed *without
the provider* by replaying recorded exchanges. The kernel's `Transport` is a
port; a `ReplayTransport` that serves recorded pairs keyed by the canonical
request bytes turns any run into a deterministic offline run — the same
mechanism rule 10 tests already use. For that to be a product feature and not
a test trick, the recorded-pair format must be a `spec/` artifact.

### 4.3 Kernel substrate the satellite needs

| Need | Gap | Kernel change |
|---|---|---|
| A normative recorded-pair format: `HttpRequest`/`HttpResponse` (post-redaction), SSE frames in order, timing, a content address, and the `Route` that produced it | **G-02** | Promote the shape to `spec/recorded-pair.schema.json`; the archive satellite writes it, the eval satellite replays it, every language port shares it |
| A transcript fixture class proving a whole multi-turn conversation (tool calls, reasoning signatures, server-tool payloads) survives encode → decode → canonical JSON unchanged | **G-03** | `transcript` fixture kind in `spec/fixtures/canonical/` plus a conformance check; an eval over agent runs is meaningless if the transcript it scores is not the transcript that ran |
| Run identity on the ledger | — | Convention, not a type: `CallContext.tags["ocai.eval.run_id"]`, `["ocai.eval.example_id"]`, `["ocai.eval.trial"]`; the telemetry satellite exports them as `ocai.ctx.tag.*`, which is how a Langfuse/LangSmith trace is joined back to a run |
| A `ReplayTransport` in `ocai.wire` (or a satellite) keyed on canonical request bytes with miss → `TransientError`-class failure, never a silent live call | — | small, additive; its tests are the existing recorded pairs |
| Score vocabulary | — | none in the kernel; scores are satellite data. If the kernel ever hosts a *decision* capability (modernization step 7: evidence, typed questions, scores, distributions), the eval satellite reuses that vocabulary rather than minting one |

### 4.4 Integrate first, build second

| Integration | Direction | Why first |
|---|---|---|
| OTel `gen_ai.evaluation.result` event with `ocai.*` attributes | export | one event, every OTLP backend (Langfuse, LangSmith, Datadog, Honeycomb) ingests it; the telemetry satellite already carries the span |
| promptfoo | export a provider + import YAML tests | the migration target OpenAI names; an ocai *provider* for promptfoo (a Python/JS provider that calls an ocai port) makes every promptfoo run ledger-attributed with no new runner |
| Langfuse datasets and scores API | export | MIT, self-hostable, `DatasetRunItem` links a run row to a trace the telemetry satellite already produced |
| LangSmith `evaluate()` target | adapter | enterprises on LangSmith keep their datasets; the ocai port is the `target` |
| Phoenix | export via OpenInference `EVALUATOR` spans | only if the OpenInference adapter mode of the telemetry satellite exists |
| Scorer libraries (`autoevals`, `openevals`, DeepEval, Ragas) | consume | call them from a task; never vendor them |

Do not build: a judge library, a dataset UI, a red-team suite. Do build: the
runner, the replay transport, the ledger join, the export writers.

## 5. Priority and sequencing

| Item | Priority | Depends on |
|---|---|---|
| G-02: recorded-pair schema in `spec/`, with the existing Python fixtures migrated to it | **P1** (prerequisite for audit *and* eval; the gateway's log is the same format) | — |
| `ReplayTransport` over the G-02 format | P1 | G-02 |
| G-03: transcript fixture kind + conformance check | P1 (needed before any agent-run eval; also a freeze-gate input per ADR 0005 step 3) | ordered-item work (ADR 0003) for the richest cases |
| `ocai-eval` runner: dataset → task over an ocai port → scorers → records with the `ocai` block; `CallContext.tags` run identity | P2 | telemetry satellite (for trace links) |
| Exporters: OTel evaluation event, promptfoo provider, Langfuse scores/datasets | P2 | runner |
| LangSmith / Phoenix adapters | P3 | demand |

## 6. Open questions and unverified items

- Whether `Route` should carry the *request* canonical hash as well (today
  the `WireExchanged` request is the only place the sent bytes exist) — the
  replay key proposal above assumes it is computable from the archived pair.
- OpenAI output-item exact fields, Langfuse OTel experiment attribute names,
  Galileo and Weave export endpoints, Phoenix OTLP ports, and Bedrock's full
  judge-metric identifier list are *unverified*.
- Whether eval records belong in the audit archive (same content-addressed
  store) or a separate store: recommendation is the same store, because a
  score without its exchange is not evidence (modernization plan: "sampled
  traces are not durable audit evidence").

## Sources

- https://docs.braintrust.dev/guides/evals/write (read 2026-11-10)
- https://docs.braintrust.dev/reference/libs/python (read 2026-11-10)
- https://github.com/braintrustdata/autoevals (read 2026-11-10)
- https://docs.langchain.com/langsmith/evaluate-llm-application (read 2026-11-10)
- https://docs.langchain.com/langsmith/evaluate-pairwise (read 2026-11-10)
- https://docs.langchain.com/langsmith/evaluation-concepts (read 2026-11-10)
- https://github.com/langchain-ai/openevals (read 2026-11-10)
- https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk (read 2026-11-10)
- https://langfuse.com/docs/evaluation/experiments/data-model (read 2026-11-10)
- https://langfuse.com/docs/evaluation/evaluation-methods/data-model (read 2026-11-10)
- https://langfuse.com/docs/open-source (read 2026-11-10)
- https://langfuse.com/docs/api-and-data-platform/features/export-to-blob-storage (read 2026-11-10)
- https://arize.com/docs/phoenix/datasets-and-experiments/how-to-experiments/running-experiments (read 2026-11-10)
- https://github.com/Arize-ai/phoenix (read 2026-11-10)
- https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md (read 2026-11-10)
- https://docs.coreweave.com/weave/guides/core-types/evaluations (read 2026-11-10)
- https://docs.coreweave.com/weave/guides/evaluation/scorers (read 2026-11-10)
- https://deepeval.com/docs/evaluation-test-cases (read 2026-11-10)
- https://deepeval.com/docs/metrics-llm-evals (read 2026-11-10)
- https://docs.ragas.io/en/stable/concepts/components/eval_sample/ (read 2026-11-10)
- https://docs.ragas.io/en/stable/references/evaluate/ (read 2026-11-10)
- https://www.promptfoo.dev/docs/configuration/reference/ (read 2026-11-10)
- https://www.promptfoo.dev/docs/configuration/expected-outputs/ (read 2026-11-10)
- https://www.promptfoo.dev/docs/configuration/outputs/ (read 2026-11-10)
- https://developers.openai.com/api/reference/resources/evals (read 2026-11-10)
- https://developers.openai.com/api/docs/guides/graders (read 2026-11-10)
- https://developers.openai.com/api/docs/deprecations (read 2026-11-10)
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-overview (read 2026-11-10)
- https://docs.cloud.google.com/python/docs/reference/vertexai/latest/vertexai.evaluation.EvalTask (read 2026-11-10)
- https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-prompt-datasets-judge.html (read 2026-11-10)
- https://docs.aws.amazon.com/bedrock/latest/userguide/evaluation-kb-metrics.html (read 2026-11-10)
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_CreateEvaluationJob.html (read 2026-11-10)
- https://humanloop.com/docs/changelog (read 2026-11-10)
- https://docs.patronus.ai/ (read 2026-11-10)
- https://docs.galileo.ai/concepts/metrics/overview (read 2026-11-10)
- https://docs.galileo.ai/sdk-api/python/reference/experiments (read 2026-11-10)
- https://opentelemetry.io/docs/specs/semconv/attributes-registry/gen-ai/ (read 2026-11-10)
- https://inspect.aisi.org.uk/datasets.html (read 2026-11-10)
- https://research.ibm.com/blog/every-evaluation-ever (read 2026-11-10)
