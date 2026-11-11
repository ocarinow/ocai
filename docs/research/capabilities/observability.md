# Observability

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

**Currency:** researched 2026-11-10 against the OpenTelemetry
`semantic-conventions-genai` repository (status *Development*, no tagged
release as of the read date), the frozen GenAI pages of the main
`semantic-conventions` repository (latest release v1.45.0; GenAI moved out in
v1.42.0), and vendor documentation. Attribute names move between releases;
every name below is cited to the page it was read from. Anything not
confirmed is marked *unverified*.

**Status:** planned. The telemetry satellite is "Observer-driven export of
`Route`, `FidelityReport`, and `Usage` to tracing and metrics backends"
(platform README). The kernel ships the `Observer` protocol and three event
shapes [provisional]; no exporter exists.

## 1. Why this family matters to ocai

ocai's product is the ledger: `Route`, `FidelityReport`, `Usage`, and the
post-redaction wire exchange. A ledger nobody can see is worthless, and the
place enterprises already look is their tracing backend. The first satellite
therefore has one job — put every `CallResult` on an OpenTelemetry span with
the names the backends already understand — and one constraint: the things
that make ocai different (fidelity loss, catalog hash, route resolution) have
**no counterpart in any convention** and must be carried as custom
attributes without breaking the standard ones.

## 2. Landscape

### 2.1 Conventions

| Convention | Owner / status | Core vocabulary |
|---|---|---|
| OpenTelemetry GenAI semantic conventions | `open-telemetry/semantic-conventions-genai` (moved out of the main repo in v1.42.0; every document *Development*; no release) | Span name `{gen_ai.operation.name} {gen_ai.request.model}`; required `gen_ai.operation.name`, `gen_ai.provider.name` (renamed from `gen_ai.system` in v1.37.0); usage `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_write.input_tokens` (the frozen main-repo registry still spells it `cache_creation`), `gen_ai.usage.reasoning.output_tokens`; response `gen_ai.response.id`, `gen_ai.response.model`, `gen_ai.response.finish_reasons`; `gen_ai.conversation.id`; opt-in content `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.system_instructions`, `gen_ai.tool.definitions` (+ `*_ref` URI variants); event `gen_ai.client.inference.operation.details`; `execute_tool {gen_ai.tool.name}` spans; agent spans `invoke_agent`, `create_agent`; evaluation event `gen_ai.evaluation.result` |
| OpenInference | Arize (used by Phoenix) | `openinference.span.kind` ∈ `LLM, EMBEDDING, CHAIN, RETRIEVER, RERANKER, TOOL, AGENT, GUARDRAIL, EVALUATOR, PROMPT, DECISION`; `llm.model_name`, `llm.provider`, `llm.system`; `llm.token_count.{prompt,completion,total}`, `llm.token_count.prompt_details.{cache_read,cache_write}`, `llm.token_count.completion_details.reasoning`; `llm.cost.*` (USD); `llm.input_messages.{i}.message.*`, `input.value`/`output.value`; `session.id`, `user.id`, `metadata` |
| Langfuse native | Langfuse | trace → observations (`langfuse.observation.type` ∈ `span, generation, event, embedding, agent, tool, chain, retriever, guardrail, evaluator`); `langfuse.observation.usage_details`, `langfuse.observation.cost_details`, `langfuse.observation.model.name`, `langfuse.observation.prompt.name/.version`, `langfuse.session.id`, `langfuse.user.id` |
| Traceloop / OpenLLMetry | Traceloop | emits legacy `gen_ai.system`, `gen_ai.usage.prompt_tokens`, `gen_ai.prompt`/`gen_ai.completion` plus `llm.request.type`, `traceloop.span.kind`, `traceloop.entity.{name,input,output}`, `traceloop.association.properties.*`; switch to post-v1.37 names *unverified* |

### 2.2 Backends — what each ingests

| Backend | Ingest path | Conventions understood | Content / PII control |
|---|---|---|---|
| Langfuse (MIT outside `ee/`, self-hostable) | OTLP `POST {host}/api/public/otel` (HTTP/protobuf or JSON; no gRPC), Basic auth `public_key:secret_key`, header `x-langfuse-ingestion-version=4` | `gen_ai.*`, OpenInference, MLflow, OpenLLMetry, OpenLIT, Arize; precedence `langfuse.*` > generic; unmapped attributes land in `metadata.attributes` | `Langfuse(mask=fn)` / `LangfuseSpanProcessor({ mask })` |
| LangSmith | SDK (`@traceable`, `RunTree`) or OTLP at `{LANGSMITH_ENDPOINT}/otel` with `x-api-key`, `Langsmith-Project` | `gen_ai.*` (incl. `gen_ai.usage.cache_read.input_tokens` → `usage_metadata.input_token_details.cache_read`), OpenInference, Traceloop, own `langsmith.*` | `LANGSMITH_HIDE_INPUTS/OUTPUTS`, `Client(hide_inputs=fn, anonymizer=...)` |
| Arize Phoenix (ELv2, self-hosted) | OTLP HTTP `:6006/v1/traces`, gRPC `:4317` | OpenInference; raw `gen_ai.*` acceptance *unverified* | — |
| Datadog LLM Observability | `ddtrace` SDK (`LLMObs`), or OTLP with headers `dd-api-key`, `dd-otlp-source=llmobs`, `DD-LLMObs-Enabled=true` | "OpenTelemetry 1.37+ GenAI", OpenInference, OpenLLMetry, Langfuse-native; `gen_ai.operation.name` → span kind (`chat`→`llm`, `embeddings`→`embedding`, `execute_tool`→`tool`, `invoke_agent`→`agent`) | `LLMObs.enable(span_processor=fn)` |
| Honeycomb | generic OTLP | `gen_ai.*` directly; Agent Timeline **requires** `gen_ai.conversation.id`, `gen_ai.agent.name`, `gen_ai.operation.name` | Collector `transform` processor |
| Sentry AI Agents Insights | Sentry SDK spans | OTel names directly (`gen_ai.provider.name`, `gen_ai.input.messages`, `gen_ai.usage.cache_read.input_tokens`); own legacy names deprecated | `send_default_pii`, `data_collection={"gen_ai": {...}}` |
| New Relic AI monitoring | APM agents (Python, Node, Java, Go, Ruby, .NET) | own `Llm*` events (`LlmChatCompletionMessage`, `LlmEmbedding`, `LlmFeedbackMessage` confirmed; `LlmChatCompletionSummary` *unverified*) | `ai_monitoring.record_content.enabled` |
| Pydantic Logfire | OTel-native, `logfire.instrument_openai/anthropic()` | "semantic convention version 2"; scrubbing docs name `gen_ai.input.messages`, `gen_ai.output.messages` | `ScrubbingOptions`, `include_content=False` |
| Helicone | proxy (base-URL swap, `Helicone-Auth`) or async `POST /custom/v1/log` | own headers `Helicone-User-Id`, `Helicone-Session-Id`, `Helicone-Property-*`, `Helicone-Prompt-Id` | `Helicone-Omit-Request/Response` |

### 2.3 Content capture switches (OTel)

Instrumentations "SHOULD NOT capture inputs/outputs by default but SHOULD
offer an opt-in". Two variable names coexist: the spec repository defines
`OTEL_INSTRUMENTATION_GENAI_CAPTURE_CONTENT` ∈ `NO_CONTENT` (default),
`SPAN_ONLY`, `EVENT_ONLY`, `SPAN_AND_EVENT`; the Python contrib
instrumentations read `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` ∈
`true`, `span_only`, `event_only`, `span_and_event`, gated behind
`OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`.

### 2.4 Vocabulary comparison

| Concept | OTel `gen_ai` | OpenInference | Langfuse |
|---|---|---|---|
| Provider | `gen_ai.provider.name` | `llm.provider` + `llm.system` | metadata |
| Request / response model | `gen_ai.request.model` / `gen_ai.response.model` | `llm.model_name` (+ `llm.request.model_name`, `llm.response.model_name`) | `model` |
| Input / output tokens | `gen_ai.usage.input_tokens` / `.output_tokens` | `llm.token_count.prompt` / `.completion` | `usage_details.input` / `.output` |
| Cached tokens | `gen_ai.usage.cache_read.input_tokens`, `.cache_write.input_tokens` | `llm.token_count.prompt_details.cache_read` / `.cache_write` | `usage_details.<custom>` |
| Reasoning tokens | `gen_ai.usage.reasoning.output_tokens` | `llm.token_count.completion_details.reasoning` | `usage_details.<custom>` |
| Finish reasons | `gen_ai.response.finish_reasons` (string[]) | `llm.finish_reason` | — |
| Response id | `gen_ai.response.id` | — | — |
| Conversation / session | `gen_ai.conversation.id` | `session.id` | `langfuse.session.id` |
| User | — (general `user.id`, *unverified for GenAI pages*) | `user.id` | `langfuse.user.id` |
| Tool name | `gen_ai.tool.name` | `tool.name` | observation type `tool` |
| Content | `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.system_instructions` (opt-in) | `llm.input_messages.*`, `input.value` | observation `input`/`output` |
| Cost | **none** | `llm.cost.*` | `cost_details` |
| Prompt name / version | `gen_ai.prompt.name`, `gen_ai.prompt.version` | `llm.prompt_template.*` | `langfuse.observation.prompt.name/.version` |
| Error | `error.type` + span status | `exception.*` events | `level=ERROR`, `status_message` |

## 3. Current kernel integration (2026-11-11)

`ocai.runtime.observe` emits metadata-only `CallStarted`, `CallFinished` and
`WireExchanged` events for unary and streamed invocations. Events carry invocation
and physical-attempt identity and terminal accounting; they do not expose raw
request/response bodies, headers or error messages. Observer exceptions are
isolated, so required audit persistence belongs in enforceable middleware.

See the [current runtime reference](../../user/reference/ocai-runtime.md) and
`python/packages/ocai-core/tests/test_stream_middleware.py`. The exporter and
trace-carrier contracts remain separate satellite WUs; this is not a shipped OTel
exporter. The original G-04 correlation analysis predates the governed observer
implementation and must not be used as its current field layout.

## 4. Verdict: export via OTel GenAI conventions first, from the Observer

The satellite (`ocai-otel`) is an `Observer`. It depends on `ocai.core`,
`ocai.runtime` (for the event types) and the OpenTelemetry API only. It never
touches the wire, never sees a credential, and never changes a call.

### 4.1 Span model

One **inference span** per `CallStarted`/`CallFinished` pair, kind `CLIENT`
(or `INTERNAL` when `route.host == "in-process"`), named
`{gen_ai.operation.name} {gen_ai.request.model}`. One **child span per
`WireExchanged`** named `http.request` with `attempt` as an attribute —
retries become visible as siblings, which no instrumentation of a provider
SDK can show. Streams: the inference span stays open until `StreamEnd`; the
first chunk sets `gen_ai.response.time_to_first_chunk`.

### 4.2 Attribute mapping

| ocai source | OTel attribute | Notes |
|---|---|---|
| `CallStarted.capability` | `gen_ai.operation.name` | `chat` → `chat`; `embedding` → `embeddings`; rerank/others map to the registry values or fall back to the capability name |
| `Route.node.provider` | `gen_ai.provider.name` | map `openai`→`openai`, `anthropic`→`anthropic`, `gemini`→`gcp.gemini`; Vertex-hosted → `gcp.vertex_ai`, Bedrock-hosted → `aws.bedrock` (host-derived, from `Route.host`) |
| `EndpointSpec.resource` (the bound model name, via the facade) | `gen_ai.request.model` | the IR has no `model` field by design (§11.3); the satellite reads it from the route/binding, not the request |
| `ChatResponse` native model field, when present | `gen_ai.response.model` | |
| `ChatResponse.id` / provider response id | `gen_ai.response.id` | |
| `FinishInfo.reason` (+ `native`) | `gen_ai.response.finish_reasons` | canonical code; native value as `ocai.finish.native` |
| `Usage` consumptions, `source=input` (text, tokens) | `gen_ai.usage.input_tokens` | |
| `source=output` | `gen_ai.usage.output_tokens` | |
| `source=cached` | `gen_ai.usage.cache_read.input_tokens` | current GenAI-repo spelling; emit `cache_creation` alias only behind a compatibility flag |
| `source=cache_write` (proposed, see caching page) | `gen_ai.usage.cache_write.input_tokens` | |
| `source=reasoning` | `gen_ai.usage.reasoning.output_tokens` | |
| `ChatConfig.temperature`, `top_p`, `top_k`, `max_output_tokens`, `stop_sequences`, `seed`, `frequency_penalty`, `presence_penalty` | `gen_ai.request.temperature`, `.top_p`, `.top_k`, `.max_tokens`, `.stop_sequences`, `.seed`, `.frequency_penalty`, `.presence_penalty` | verbatim; out-of-range passthrough is *also* visible as an `APPROXIMATED` loss below |
| `ChatConfig.reasoning` effort | `gen_ai.request.reasoning.level` | |
| `ChatConfig.output` structured-output contract | `gen_ai.output.type` (`json`/`text`) | |
| streaming port method | `gen_ai.request.stream` | |
| `CallContext.tags["conversation_id"]` or a request anchor (G-01) | `gen_ai.conversation.id` | only when readily available; never synthesized (spec rule) |
| `CallContext.principal` | `user.id` (general semconv) | *attribute choice unverified for GenAI pages*; tenant has no counterpart |
| `CallContext.tenant`, `classification`, `tags` | `ocai.ctx.tenant`, `ocai.ctx.classification`, `ocai.ctx.tag.<key>` | custom |
| `ChatRequest.messages`, `ChatResponse.message` (canonical JSON) | `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.system_instructions`, `gen_ai.tool.definitions` | **opt-in only**, gated by the spec's `OTEL_INSTRUMENTATION_GENAI_CAPTURE_CONTENT`; the canonical IR serializes to the OTel message schema with a small adapter; large content goes to `*_ref` URIs pointing at the audit archive |
| `PartToolCall` executed client-side (agent runtime) | child span `execute_tool {gen_ai.tool.name}` with `gen_ai.tool.call.id`, `gen_ai.tool.type=function` | emitted by the agent runtime, not the chat satellite |
| `OcaiError` subclass name | `error.type` + span status `ERROR` | `RateLimitError`, `AuthError`, … are the taxonomy; `native` code as `ocai.error.native` |
| `WireExchanged.request.url` host/port, `attempt`, `duration_s` | `server.address`, `server.port`, `ocai.wire.attempt`, child span duration | |
| `WireExchanged.response.headers` rate-limit headers | `ocai.wire.ratelimit.remaining_requests`, `ocai.wire.ratelimit.remaining_tokens`, `ocai.wire.ratelimit.reset` | custom; normalized from `x-ratelimit-*` / `anthropic-ratelimit-*` |

### 4.3 What has no counterpart — the `ocai.` namespace

| ocai fact | Attribute(s) | Why custom |
|---|---|---|
| `Route.node` (interface, tag, shape) | `ocai.route.interface`, `ocai.route.tag`, `ocai.route.shape` | OTel has a provider and a model, not an *interface* or dated wire revision — the four-level identity is ocai's own |
| `Route.requested_interface`, `requested_tag`, `reason` | `ocai.route.requested_interface`, `ocai.route.requested_tag`, `ocai.route.reason` | the migration-with-no-code-change proof is only auditable if the pin and the resolution are on the span |
| `Route.catalog_hash` | `ocai.catalog.hash` | reproduces the exact conversion logic; nothing like it exists in any convention |
| `Route.host` | `ocai.route.host` | `in-process`, `direct`, `vertex`, … |
| canonical IR revision | `ocai.ir.revision` (`2026-07`) | |
| `FidelityReport.lossless` | `ocai.fidelity.lossless` (bool) | the one-glance honesty flag |
| per-edge loss counts | `ocai.fidelity.losses.<disposition>` (int per `DROPPED`, `APPROXIMATED`, `EMULATED`, `EXTENSIONS`, `UNSUPPORTED`, `RENAMED`), `ocai.fidelity.shifts` (int), `ocai.fidelity.max_severity` | low-cardinality, queryable: "show me every call that dropped a field" |
| full `FidelityReport` | span event `ocai.fidelity.report` with `ocai.fidelity.edge`, `ocai.fidelity.path`, `ocai.fidelity.disposition`, `ocai.fidelity.note` per record, or an `ocai.fidelity.report_ref` URI to the archive | the report can be large; events, not attributes |
| `WireExchanged` content address | `ocai.wire.exchange_ref` | links the span to the audit archive record (G-02) |
| `ocai.call_id` | `ocai.call_id` | the kernel correlation id, distinct from the OTel span id so logs and archives join without OTel |

Metrics (from the same events): the GenAI-repo counters
`gen_ai.client.inference.usage.{input_tokens, output_tokens,
cache_read.input_tokens, cache_write.input_tokens, reasoning.output_tokens}`
and histograms `gen_ai.client.inference.operation.{input,output}_tokens`,
plus `ocai.fidelity.lossy_calls` (counter) and `ocai.wire.attempts`
(histogram) as custom metrics. `gen_ai.client.token.usage` is kept behind a
compatibility flag for backends still on the v1.41 shape (Traceloop,
Langfuse mappings); its formal deprecation is *unverified*.

### 4.4 Content and secrets

Content is off by default and never inferred from `raw`. The satellite reads
the canonical IR from `CallResult.value`, never the provider body, so the
exported messages are the same canonical shape across providers. Credentials
are structurally absent (post-redaction events). `CallContext.extensions` is
never exported wholesale — only keys the deployment whitelists.

### 4.5 Interoperability targets, in order

1. Any OTLP collector (the primary target; zero vendor coupling).
2. Langfuse and LangSmith (both ingest `gen_ai.*` over OTLP and map cache
   and reasoning tokens correctly; unknown `ocai.*` attributes survive as
   metadata in both).
3. Datadog, Honeycomb, Sentry (consume `gen_ai.*` directly; Honeycomb needs
   `gen_ai.conversation.id` and `gen_ai.agent.name` for its agent view —
   supplied by the agent runtime, not the chat satellite).
4. Phoenix: an OpenInference *adapter* (second exporter mode emitting
   `openinference.span.kind=LLM`, `llm.token_count.*`, `llm.cost.*`) — only
   if demand appears; the `ocai.*` namespace is identical in both modes.
5. Cost: no OTel attribute exists; the cost interceptor's
   `Consumption(unit="currency")` is exported as `ocai.cost.total` plus the
   currency code, and additionally as OpenInference `llm.cost.total` in
   adapter mode.

## 5. Priority and sequencing

| Item | Priority | Depends on |
|---|---|---|
| Re-scope G-04: add stream events (`StreamChunkObserved` or a single `StreamEnded(call_id, usage, finish, report, first_chunk_s)`), a `CallContext` slot for inbound trace context (`traceparent`/`tracestate` in `extensions` under a reserved key, or a typed field), and a documented `call_id` format | **P0** (must precede the first satellite; §9 freezes observer events at v1.0 only after real exercise) | — |
| `ocai-otel` satellite: inference span + wire child spans + the attribute mapping above, `gen_ai.*` names from the GenAI repo, `ocai.*` custom namespace, content opt-in | **P0** (the first satellite) | G-04 re-scope |
| GenAI-repo token metrics + `ocai.fidelity.*` metrics | P1 | satellite |
| `ocai.fidelity.report_ref` / `ocai.wire.exchange_ref` once the archive exists | P1 | G-02 recorded-pair spec, audit satellite |
| OpenInference adapter mode | P2 | demand |
| Vendor cookbooks (Langfuse, LangSmith, Datadog, Honeycomb, Sentry) with recorded OTLP fixtures | P2 | satellite |

## 6. Open questions and unverified items

- The GenAI conventions have no tagged release; names such as
  `gen_ai.usage.cache_write.input_tokens` may still change. The satellite
  should pin the convention revision it emits (`ocai.otel.semconv` attribute)
  and offer a legacy mode for `gen_ai.system`, `cache_creation`, and
  `gen_ai.client.token.usage`.
- Whether `user.id` (general semconv) is the sanctioned carrier for the
  principal in GenAI spans is *unverified*.
- `gen_ai.content.prompt` / `gen_ai.content.completion` event names were not
  found in the changelog read; treat them as non-existent.
- Phoenix's acceptance of raw `gen_ai.*` spans without OpenInference kinds is
  *unverified*.
- New Relic `LlmChatCompletionSummary` and Logfire's exact v2 attribute set
  are *unverified*.
- Whether the full fidelity report belongs on the span (events) or only by
  reference is a deployment choice; the satellite should support both with
  a size threshold.

## Sources

- https://github.com/open-telemetry/semantic-conventions-genai (read 2026-11-10)
- https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/client-inference.md (read 2026-11-10)
- https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/execute-tool.md (read 2026-11-10)
- https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-events.md (read 2026-11-10)
- https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-token-metrics.md (read 2026-11-10)
- https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-spans.md (read 2026-11-10)
- https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/ (read 2026-11-10)
- https://raw.githubusercontent.com/open-telemetry/semantic-conventions/main/CHANGELOG.md (read 2026-11-10)
- https://github.com/open-telemetry/semantic-conventions/releases (read 2026-11-10)
- https://github.com/open-telemetry/opentelemetry-python-contrib/blob/main/instrumentation-genai/opentelemetry-instrumentation-openai-v2/README.rst (read 2026-11-10)
- https://raw.githubusercontent.com/Arize-ai/openinference/main/spec/semantic_conventions.md (read 2026-11-10)
- https://langfuse.com/integrations/native/opentelemetry (read 2026-11-10)
- https://langfuse.com/docs/observability/data-model (read 2026-11-10)
- https://langfuse.com/docs/observability/features/token-and-cost-tracking (read 2026-11-10)
- https://langfuse.com/docs/observability/features/masking (read 2026-11-10)
- https://docs.langchain.com/langsmith/trace-with-opentelemetry (read 2026-11-10)
- https://docs.langchain.com/langsmith/cost-tracking (read 2026-11-10)
- https://docs.langchain.com/langsmith/mask-inputs-outputs (read 2026-11-10)
- https://arize.com/docs/phoenix (read 2026-11-10)
- https://www.traceloop.com/docs/openllmetry/privacy/traces (read 2026-11-10)
- https://raw.githubusercontent.com/traceloop/openllmetry/main/packages/opentelemetry-semantic-conventions-ai/opentelemetry/semconv_ai/__init__.py (read 2026-11-10)
- https://docs.helicone.ai/helicone-headers/header-directory (read 2026-11-10)
- https://docs.datadoghq.com/llm_observability/instrumentation/otel_instrumentation/ (read 2026-11-10)
- https://docs.datadoghq.com/llm_observability/instrumentation/sdk/ (read 2026-11-10)
- https://docs.newrelic.com/docs/ai-monitoring/intro-to-ai-monitoring/ (read 2026-11-10)
- https://docs.honeycomb.io/send-data/use-cases/agents.md (read 2026-11-10)
- https://docs.sentry.io/platforms/python/agent-tracing/manual-instrumentation/ (read 2026-11-10)
- https://pydantic.dev/docs/logfire/integrations/llms/openai/ (read 2026-11-10)
- https://pydantic.dev/docs/logfire/how-to-guides/scrubbing/ (read 2026-11-10)
