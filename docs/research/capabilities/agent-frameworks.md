# Agent frameworks

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

**Currency:** researched 2026-11-10 against official documentation, package
registries (PyPI/npm JSON on that date), and primary source files. Framework
APIs change monthly; version numbers are the registry values on the read
date. Anything not confirmed from an official page is marked *unverified*.

**Status:** planned. The agent runtime is "durable tool-calling loops with
checkpoints, approvals, and honest mid-run provider failover" (platform
README). No adapter to any framework exists.

## 1. Why this family matters to ocai

Every agent framework needs a model layer with the same five things:
one non-streaming call, one streaming call, tool declarations in, tool calls
out, and a usage object back. The frameworks differ in *shape*, not in
substance — three streaming grammars, four tool-call dicts, five usage
objects. ocai's chat port already is such a layer, with two properties none
of the frameworks' own model classes have: a fidelity report per call and a
provider-neutral transcript that survives provider switches. The question is
whether the platform's agent runtime should compete with these frameworks or
make ocai the model behind them.

## 2. Landscape

### 2.1 What each framework needs from a model layer

| Framework (version) | Model abstraction a third party implements | Streaming shape | Tool-call shape | Structured output | Usage object |
|---|---|---|---|---|---|
| OpenAI Agents SDK (`openai-agents` 0.24.0; JS `@openai/agents` 0.21.0) | `Model.get_response(...)` / `stream_response(...)`; `ModelProvider.get_model(model_name)`; inputs `system_instructions`, `input`, `model_settings`, `tools`, `output_schema`, `handoffs`, `tracing`, `previous_response_id`, `conversation_id`, `prompt` | OpenAI Responses API events wrapped in `RawResponsesStreamEvent`; a custom model must emit Responses-shaped events | Responses output items (`ToolCallItem`, `ToolCallOutputItem`, `HandoffCallItem`, `MCPApprovalRequestItem`) | `output_schema: AgentOutputSchemaBase` | `Usage(requests, input_tokens, output_tokens, input_tokens_details, output_tokens_details.reasoning_tokens, total_tokens)` |
| Anthropic Claude Agent SDK (`claude-agent-sdk` 0.2.180) | none — runs the Claude Code binary; `ClaudeAgentOptions.model` is a Claude alias; routing by environment (Bedrock, Vertex, Foundry, `ANTHROPIC_BASE_URL`) | raw API `StreamEvent` (opt-in) | `ToolUseBlock`/`ToolResultBlock`; custom tools via in-process MCP `create_sdk_mcp_server` | `output_format` | `ResultMessage.usage` (`cache_creation_input_tokens`, `cache_read_input_tokens`), `total_cost_usd` |
| Google ADK (`google-adk` 2.14.0) | `BaseLlm` with `supported_models()` regex and `generate_content_async(llm_request, stream) -> AsyncGenerator[LlmResponse]`; `LLMRegistry.register`/`resolve` (LiteLLM fallback for names containing `/`) | `LlmResponse(partial=True)` chunks then a final `partial=False` aggregate | Gemini `Content`/`Part.function_call` | Gemini config | Gemini `usage_metadata` |
| LangChain / LangGraph (`langchain` 1.4.10, `langgraph` 1.2.20) | `BaseChatModel._generate(messages, stop, run_manager) -> ChatResult`, `_llm_type`, optional `_stream`/`_astream`, `bind_tools(tools, tool_choice)`, `with_structured_output(schema)`, `profile: ModelProfile` | `AIMessageChunk` with `tool_call_chunks`, summed with `+` | `AIMessage.tool_calls: [{name, args, id}]`, `ToolMessage(tool_call_id)`; standard content blocks (`text`, `reasoning`, `server_tool_call`, …) | methods `json_schema`, `function_calling`, `json_mode`; `ModelRefusalError` | `UsageMetadata(input_tokens, output_tokens, total_tokens, input_token_details{audio, cache_read}, output_token_details{audio, reasoning})` |
| CrewAI (`crewai` 1.15.39) | `BaseLLM.call(messages, tools, callbacks, available_functions) -> str \| Any`; optional `supports_function_calling()`, `get_context_window_size()`; native SDKs for OpenAI/Anthropic/Gemini/Azure/Bedrock, LiteLLM for the rest | not documented for custom `BaseLLM` | OpenAI-format `tool_calls` dicts | `response_format` (Pydantic) | none documented on the custom path |
| Pydantic AI (`pydantic-ai` 2.66.0) | `Model.request(messages, model_settings, model_request_parameters) -> ModelResponse`, `request_stream(...) -> StreamedResponse`, `count_tokens`, `customize_request_parameters`; attributes `model_name`, `system`, `profile` | `PartStartEvent \| PartDeltaEvent \| PartEndEvent \| FinalResultEvent`; deltas `TextPartDelta`, `ThinkingPartDelta(content_delta, signature_delta)`, `ToolCallPartDelta(tool_name_delta, args_delta, tool_call_id)` | `ToolCallPart`; `NativeToolCallPart` (`builtin-tool-call`) | `ToolOutput` (default), `NativeOutput`, `PromptedOutput`, `TextOutput` | `RequestUsage`/`RunUsage(input_tokens, output_tokens, cache_write_tokens, cache_read_tokens, details)`, `UsageLimits` |
| Microsoft Agent Framework (`agent-framework` 1.25.0; .NET `Microsoft.Extensions.AI` 10.10.1) | .NET `IChatClient.GetResponseAsync/GetStreamingResponseAsync`; Python `BaseChatClient._inner_get_response()` / `_inner_get_streaming_response()` | `ChatResponseUpdate` | `FunctionCallContent` (.NET), contents list (Python) | `response_format: type[BaseModel]`, `GetResponseAsync<T>` | per provider (*unverified*) |
| smolagents (`smolagents` 1.26.0) | `Model.generate(messages, stop_sequences, response_format, tools_to_call_from) -> ChatMessage`; `generate_stream` per subclass | `ChatMessageStreamDelta(content, tool_calls, token_usage)` | `ChatMessageToolCall(function{name, arguments}, id, type)` | `response_format` dict / code | `TokenUsage(input_tokens, output_tokens)` |
| Mastra (`@mastra/core` 1.82.0) | AI SDK `LanguageModelV*` objects or `provider/model` strings via its router | AI SDK streams | AI SDK tool calls | `structuredOutput: {schema, errorStrategy}` | AI SDK `usage` |
| Vercel AI SDK (`ai` 7.0.168; `@ai-sdk/provider` 4.0.37) | `LanguageModelV4` (`specificationVersion: 'v4'`, `doGenerate`, `doStream`, `supportedUrls`); `ProviderV4` | provider stream parts `stream-start`, `response-metadata`, `text`, `reasoning`, `tool-call`, `tool-call-delta`, `finish`, …; UI message stream (`text-start`/`-delta`/`-end`, `tool-input-*`, `tool-approval-request`, `data-*`) | `tool-call` parts; `tool({inputSchema, execute, strict})` | `Output.object/array/choice/json/text` | `LanguageModelUsage` (totals all steps in v7) |
| LlamaIndex (`llama-index-workflows` 2.26.1) | `CustomLLM`/`LLM` (`metadata`, `complete`, `stream_complete`); `FunctionCallingLLM._prepare_chat_with_tools`, `get_tool_calls_from_response -> ToolSelection(tool_id, tool_name, tool_kwargs)` | `CompletionResponse(text, delta)` / chat deltas | `ToolSelection` | `structured_predict`, `as_structured_llm` | `raw`/`additional_kwargs` (no standard object verified) |

Reading across: three streaming grammars dominate — Responses-API events
(OpenAI SDK), part start/delta/end (Pydantic AI, AG-UI, Vercel UI stream),
and whole-message partials (ADK, LangChain chunks, MAF updates). ocai's
`ChatChunk` with per-part deltas and `StreamEnd` is the second grammar and
folds to the third; the first is a wire dialect ocai already decodes.

### 2.2 State, durability, and interrupts

| Framework | Checkpoint / durability primitive | Human-in-the-loop | Multi-agent | Tracing |
|---|---|---|---|---|
| OpenAI Agents SDK | `Session` protocol (`get_items`, `add_items`, `pop_item`, `clear_session`) with SQLite, Redis, SQLAlchemy, Dapr, MongoDB, encrypted backends; Temporal plugin (`temporalio-openai-agents` 1.1.0; model calls are Activities) | MCP `require_approval`, `ToolApprovalItem` | handoffs `transfer_to_<agent>`, `Agent.as_tool()` | built-in spans (`agent_span`, `generation_span`, `function_span`, …), `TracingProcessor`; 31 external processors |
| Claude Agent SDK | `.jsonl` session transcripts; `resume`, `fork_session`, `session_store`; Temporal `TemporalTransport` | hooks (`PreToolUse` → `permissionDecision` ∈ `allow\|deny\|ask\|defer`) | `agents` subagents | hooks only |
| Google ADK | `SessionService` (InMemory, Database, VertexAi); `MemoryService`; Temporal `GoogleAdkPlugin` | long-running tools | Sequential/Parallel/Loop, graph workflows (2.0) | `before_model_callback`/`after_model_callback` (returning an `LlmResponse` skips the model) |
| LangGraph | `BaseCheckpointSaver` (`put`, `put_writes`, `get_tuple`, `list`, `delete_thread`) with `Checkpoint(id, channel_values, channel_versions, versions_seen)`; Postgres/SQLite/Mongo/Cosmos; `@entrypoint`/`@task` functional API; Temporal `temporalio-langgraph` (preview) | `interrupt(value)` + `Command(resume=...)`; node re-runs from its start on resume | subgraphs, `Command` routing, `create_agent` middleware | LangSmith callbacks |
| CrewAI | Flows `@persist` (SQLite default), `kickoff(inputs={"id"})`, `restore_from_state_id` | `@human_feedback` (≥ 1.8.0) | Crew roles, Flows | external integrations |
| Pydantic AI | nine durability engines (Temporal `TemporalDurability`, DBOS, Prefect, Restate, …); model requests, I/O tools, MCP calls run as activities | `requires_approval=True`, `DeferredToolRequests`, resume with `message_history=` + `deferred_tool_results=` | delegation, hand-off, `pydantic-graph` | OTel GenAI conventions 1.37.0 via `InstrumentationSettings`, Logfire |
| Microsoft Agent Framework | `AgentSession.to_dict()`; workflow `CheckpointStorage` (InMemory, File, Cosmos) at superstep boundaries | `ctx.request_info()` + `@response_handler`; `function_approval_request` content | Sequential, Concurrent, GroupChat, Handoff, Magentic | OpenTelemetry |
| smolagents | none (in-memory `AgentMemory`) | none | `managed_agents` | `step_callbacks` |
| Mastra | workflow snapshots in storage; `suspend()`/`run.resume()` | `suspend`/`resume`, `tool-call-approval` chunks | supervisor + `delegation` hooks | `Observability` exporters (Langfuse, Arize) |
| Vercel AI SDK | none built in | `toolApproval` request/response parts | `ToolLoopAgent`, agents as tools | `@ai-sdk/otel` |
| LlamaIndex | `Context.to_dict()`/`from_dict()`; DBOS runtime | `InputRequiredEvent`/`HumanResponseEvent` | `AgentWorkflow` | callbacks |
| Temporal (cross-cutting) | integrations as standalone packages: OpenAI Agents, Pydantic AI, LangGraph, ADK, Claude Agent SDK; "the model call is the Activity boundary" — the adapter must be invocable from an Activity with serializable inputs/outputs | — | — | — |

### 2.3 Protocols

- **A2A** — spec 1.0.0 (Linux Foundation; now under the Agentic AI
  Foundation); `A2A-Version` header; `a2a.proto` normative; Agent Card at
  `/.well-known/agent-card.json`; PascalCase operations `SendMessage`,
  `SendStreamingMessage`, `GetTask`, `CancelTask`, `SubscribeToTask`, push
  notification configs; objects `Task`, `Message`, `Part` (`text`, `raw`,
  `url`, `data`), `Artifact`; `TaskState` ∈ `TASK_STATE_SUBMITTED`, `_WORKING`,
  `_COMPLETED`, `_FAILED`, `_CANCELED`, `_INPUT_REQUIRED`, `_REJECTED`,
  `_AUTH_REQUIRED`; SSE `StreamResponse` (`task`, `statusUpdate`,
  `artifactUpdate`). "MCP is for agent-to-tool communication; A2A is for
  agent-to-agent communication."
- **AG-UI** (CopilotKit; `ag-ui-protocol` 1.0.0) — events `RUN_STARTED`,
  `RUN_FINISHED`, `RUN_ERROR`, `STEP_STARTED/FINISHED`, `TEXT_MESSAGE_START`,
  `TEXT_MESSAGE_CONTENT(message_id, delta)`, `TEXT_MESSAGE_END`,
  `TOOL_CALL_START(tool_call_id, tool_call_name, parent_message_id)`,
  `TOOL_CALL_ARGS(delta)`, `TOOL_CALL_END`, `TOOL_CALL_RESULT`,
  `REASONING_*`, `STATE_SNAPSHOT`, `STATE_DELTA` (RFC 6902), `MESSAGES_SNAPSHOT`,
  `SUBAGENT_*`, `RAW`, `CUSTOM`; HTTP SSE or binary. Adopted first-party by
  Microsoft Agent Framework, ADK, Mastra, Pydantic AI, LlamaIndex, AG2;
  LangGraph and CrewAI by partnership; OpenAI Agents SDK by community.
- **ACP** (IBM/BeeAI) — merged into A2A; repository archived 2025-08-27.
- **MCP** — the tool protocol in every framework above (see the tools page).

## 3. What the kernel already provides a durable runtime

- **Checkpoint = canonical transcript.** `ChatRequest.messages` is pure,
  serializable data with JSON Schema in `spec/`; `canonjson` gives it a
  content address. A LangGraph `Checkpoint.channel_values`, an OpenAI
  `Session.get_items()`, an MAF `AgentSession.to_dict()` and a Temporal
  Activity input are all "a list of messages plus state"; ocai's is the only
  one that is provider-neutral *and* round-trips through provider wire
  formats with a loss census (once G-03 lands).
- **Provider-side state is anchored, not assumed.** `ProviderRef` on parts
  (`PartReasoning.signature`/`opaque`, `anchor`) carries the handles the
  frameworks hide in `previous_response_id`/`conversation_id`; crossing a
  `(provider, interface)` boundary is `UNSUPPORTED`-and-reported — the
  "honest mid-run provider failover" the platform README promises is a
  kernel property.
- **Approval gates reuse `Decision`.** `Proceed | Retry | Fail | Return` is
  the vocabulary an approval or budget gate returns; `PartToolCall.status`
  already models `input_complete → executing → output_available |
  output_error`, and the tools page proposes an `input_required`-class
  status for provider approval requests.
- **Tool calls are data.** `Tool(name, parameters, description, output)` has
  no callable; `PartToolCall.args_json` is the authoritative wire truth with
  `args()` parse-on-read; `executed_by: client|provider` separates the two
  loops.
- **Governance rides along.** `CallContext(tenant, principal, classification,
  deadline, tags)` is threaded through every port, so an agent run's identity
  (run id, step, parent) is one tag convention away.
- **Streams fold.** `fold(stream) == complete` is normative; a runtime that
  checkpoints after every step can store the folded `ChatResponse` and
  replay the stream for a UI without re-calling the provider.

Gaps the runtime exposes: request-side continuation anchors (**G-01**,
`ChatRequest.anchors`), a transcript fixture class (**G-03**), and ordered
interaction items (ADR 0003) for multi-step transcripts with tool results
interleaved.

## 4. Verdict: interoperate first — ocai as the model behind every framework

### 4.1 Adapters, not a competitor

The platform's agent runtime must not start as an eleventh framework. The
first deliverable is a set of **model adapters** that make an ocai port the
model inside the frameworks enterprises already run, so every agent call
gains a `Route`, a `FidelityReport`, and a canonical transcript with no
framework change. Each adapter is a satellite distribution depending on
`ocai` and the framework, never the reverse.

| Adapter (satellite) | Implements | Mapping notes | Priority |
|---|---|---|---|
| `ocai-pydantic-ai` | `pydantic_ai.models.Model` (`request`, `request_stream`, `count_tokens`, `model_name`, `system`, `profile`) | Closest match: part-level deltas map 1:1 to `ChatChunk` part deltas; `ToolCallPart` ↔ `PartToolCall`; `ThinkingPart` ↔ `PartReasoning` (signature preserved via `ProviderRef`); `RequestUsage.cache_read_tokens`/`cache_write_tokens` ↔ `UsageSource.CACHED`/`CACHE_WRITE`; `provider_response_id` ↔ `ProviderRef`; the `provider:model` string convention mirrors ocai's `provider/resource` front door; `ModelRequestParameters` field names *partially unverified* | **P1** |
| `ocai-langchain` | `BaseChatModel` (`_generate`, `_stream`, `_astream`, `bind_tools`, `with_structured_output`, `_llm_type`, `profile`) | `AIMessage.tool_calls {name, args, id}` ↔ `PartToolCall`; `UsageMetadata.input_token_details.cache_read` ↔ `CACHED`; standard content blocks (`reasoning`, `server_tool_call`) ↔ `PartReasoning`, `PartServerToolCall`; `with_structured_output(method="json_schema")` ↔ `ChatConfig.output`; LangGraph checkpointers then store ocai-produced messages unchanged | **P1** |
| `ocai-openai-agents` | `Model` + `ModelProvider` | The SDK's stream contract *is* the Responses event dialect; the adapter re-encodes `ChatChunk` through the `ocai → openai/responses` chunk edge (H1), which makes the adapter nearly free once H1 lands and gives non-OpenAI providers a Responses-shaped stream with a report | P2 (after H1) |
| `ocai-adk` | `BaseLlm` + `LLMRegistry.register` | `LlmResponse(partial=True)` chunks from folded prefixes; Gemini `Content`/`Part` ↔ IR via the H2 Gemini edge | P2 (after H2) |
| `ocai-agent-framework` | Python `BaseChatClient._inner_get_response/_inner_get_streaming_response`; .NET `IChatClient` when a .NET port exists | `ChatResponseUpdate` whole-message partials from folds | P3 |
| `ocai-crewai` | `BaseLLM.call` | returns a string or OpenAI-format `tool_calls`; no streaming contract documented, no usage slot — the adapter reports usage through `CallContext`/observer only | P3 |
| `ocai-smolagents`, `ocai-llamaindex` | `Model.generate`; `FunctionCallingLLM` | thin | P3 |
| TypeScript (`ai` `LanguageModelV4`, Mastra via AI SDK objects) | `doGenerate`/`doStream` | blocked on the TypeScript port (H5); the spec is `spec/`-driven so the adapter is mechanical once the port exists | after H5 |

Adapter conformance is testable without live keys: the kernel's recorded
wire pairs drive the port, and each adapter's tests assert the framework-side
message equals the fold of the framework-side stream (the fold law restated
in the framework's own types).

### 4.2 What the runtime builds later, on the adapters

Once adapters exist, the platform's own runtime is justified only by what
the frameworks cannot do: **honest failover mid-run** (switch provider
between steps with the transcript migrated through certified edges and the
cost reported), **catalog-locked replay** (re-run a checkpointed agent
against the same `catalog_hash` offline through the replay transport), and
**ledger-native audit** (every step's `Route` in the checkpoint). Its
checkpoint format is the canonical transcript plus a small envelope
`(run_id, step, parent_run_id, agent_definition_ref, catalog_hash,
credential_refs)` — the modernization plan's "agent definition, deployment,
and run have distinct identities".

Durability engine: do not build one. Temporal's integrations already
establish the pattern "model call = Activity"; an ocai port is exactly that
Activity, and `CallResult` is a serializable Activity result. The runtime's
first durability backend is Temporal via the Pydantic AI or OpenAI Agents
integrations, which the adapters make available for free.

### 4.3 Protocols

- **A2A** is agent-to-agent transport with its own versioned wire (1.0.0,
  `A2A-Version` header, proto-normative) — it passes the §11 litmus test as
  a *capability* the same way MCP does (tools page), but there is no demand
  signal yet; record it as a horizon capability (`a2a` interface, dated
  tags), not a near-term WU.
- **AG-UI** is a UI event stream; the ocai `ChatChunk` grammar maps to
  `TEXT_MESSAGE_*`/`TOOL_CALL_*`/`REASONING_*` events trivially and
  `StreamEnd` to `RUN_FINISHED`. An `ocai-agui` encoder is a small satellite
  after the runtime exists; the gateway may expose it as a second streaming
  format.

## 5. Priority and sequencing

| Item | Priority | Depends on |
|---|---|---|
| `ocai-pydantic-ai` and `ocai-langchain` adapters with fold-law conformance tests on recorded pairs | **P1** (the cheapest path to every enterprise agent stack; also the first external consumers of the port, which is what §9 wants before freezing hook protocols) | G-01 anchors for multi-turn with `previous_response_id`-style providers |
| Run-identity tag convention on `CallContext` (`ocai.run.id`, `ocai.run.step`, `ocai.run.parent`) shared with telemetry and eval | P1 | — |
| `ocai-openai-agents` over the Responses chunk edge | P2 | H1 |
| `ocai-adk` | P2 | H2 |
| Agent runtime: checkpoint envelope over the canonical transcript, approval gate on `Decision`, Temporal as the first durability backend through the adapters | P2 | G-03 transcript fixtures, ADR 0003 ordered items |
| MAF, CrewAI, smolagents, LlamaIndex adapters | P3 | demand |
| AG-UI encoder; A2A as a horizon capability | P3 | runtime |
| TypeScript adapters (`LanguageModelV4`, Mastra) | after H5 | TypeScript port |

## 6. Open questions and unverified items

- LangGraph `durability` parameter values, ADK workflow-agent import paths,
  Pydantic AI legacy `ModelRequestParameters` field names, CrewAI built-in
  event-bus tracing, the MAF usage object, and Vercel's "eve" durability
  reference are *unverified*.
- Microsoft Agent Framework 1.0 GA (April 2026) is from secondary sources.
- Whether adapters should expose the `FidelityReport` through the
  framework's own extension slot (`ModelResponse.provider_details` in
  Pydantic AI, `AIMessage.response_metadata` in LangChain,
  `ModelResponse.providerData` in the OpenAI JS SDK) or only through the
  observer: recommendation is both — the slot for developers, the observer
  for the platform.
- Whether the Claude Agent SDK can ever run on an ocai port: it is
  Claude-only by design and routes by `ANTHROPIC_BASE_URL`; the only
  integration is pointing it at the ocai gateway's Anthropic-compatible
  listener (gateways page §4.3).

## Sources

- https://openai.github.io/openai-agents-python/ref/models/interface/ (read 2026-11-10)
- https://openai.github.io/openai-agents-python/models/ (read 2026-11-10)
- https://openai.github.io/openai-agents-python/sessions/ (read 2026-11-10)
- https://openai.github.io/openai-agents-python/streaming/ (read 2026-11-10)
- https://openai.github.io/openai-agents-python/ref/usage/ (read 2026-11-10)
- https://openai.github.io/openai-agents-python/handoffs/ (read 2026-11-10)
- https://openai.github.io/openai-agents-python/tracing/ (read 2026-11-10)
- https://openai.github.io/openai-agents-js/extensions/ai-sdk/ (read 2026-11-10)
- https://code.claude.com/docs/en/agent-sdk/python.md (read 2026-11-10)
- https://code.claude.com/docs/en/agent-sdk/hooks.md (read 2026-11-10)
- https://code.claude.com/docs/en/agent-sdk/sessions.md (read 2026-11-10)
- https://code.claude.com/docs/en/agent-sdk/model-config.md (read 2026-11-10)
- https://adk.dev/agents/models/ (read 2026-11-10)
- https://adk.dev/sessions/session/ (read 2026-11-10)
- https://adk.dev/callbacks/ (read 2026-11-10)
- https://adk.dev/a2a/quickstart-exposing/ (read 2026-11-10)
- https://docs.langchain.com/oss/python/langchain/models (read 2026-11-10)
- https://docs.langchain.com/oss/python/langchain/agents (read 2026-11-10)
- https://docs.langchain.com/oss/python/langgraph/checkpointers (read 2026-11-10)
- https://docs.langchain.com/oss/python/langgraph/interrupts (read 2026-11-10)
- https://docs.langchain.com/oss/python/langgraph/functional-api (read 2026-11-10)
- https://docs.langchain.com/langsmith/deployments (read 2026-11-10)
- https://docs.crewai.com/en/learn/custom-llm.md (read 2026-11-10)
- https://docs.crewai.com/en/concepts/llms.md (read 2026-11-10)
- https://docs.crewai.com/en/concepts/flows.md (read 2026-11-10)
- https://pydantic.dev/docs/ai/api/models/base/index.md (read 2026-11-10)
- https://pydantic.dev/docs/ai/api/messages/index.md (read 2026-11-10)
- https://pydantic.dev/docs/ai/api/usage/index.md (read 2026-11-10)
- https://pydantic.dev/docs/ai/output/index.md (read 2026-11-10)
- https://pydantic.dev/docs/ai/deferred-tools/index.md (read 2026-11-10)
- https://pydantic.dev/docs/ai/durable_execution/overview/index.md (read 2026-11-10)
- https://pydantic.dev/docs/ai/capabilities/durable_execution/temporal/index.md (read 2026-11-10)
- https://pydantic.dev/docs/ai/ui/overview/index.md (read 2026-11-10)
- https://pydantic.dev/docs/ai/logfire/ (read 2026-11-10)
- https://github.com/datalayer/fasta2a (read 2026-11-10)
- https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview (read 2026-11-10)
- https://learn.microsoft.com/en-us/python/api/agent-framework-core/agent_framework.basechatclient (read 2026-11-10)
- https://learn.microsoft.com/en-us/dotnet/api/microsoft.extensions.ai.ichatclient (read 2026-11-10)
- https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints (read 2026-11-10)
- https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop (read 2026-11-10)
- https://learn.microsoft.com/en-us/agent-framework/integrations/by-component/agent-services/a2a (read 2026-11-10)
- https://huggingface.co/docs/smolagents/reference/models.md (read 2026-11-10)
- https://huggingface.co/docs/smolagents/main/en/reference/agents (read 2026-11-10)
- https://mastra.ai/docs/agents/overview (read 2026-11-10)
- https://mastra.ai/models (read 2026-11-10)
- https://mastra.ai/docs/workflows/suspend-and-resume (read 2026-11-10)
- https://ai-sdk.dev/providers/community-providers/custom-providers (read 2026-11-10)
- https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol (read 2026-11-10)
- https://ai-sdk.dev/docs/migration-guides/migration-guide-7-0 (read 2026-11-10)
- https://ai-sdk.dev/docs/agents/overview (read 2026-11-10)
- https://developers.llamaindex.ai/python/framework/module_guides/models/llms/usage_custom/ (read 2026-11-10)
- https://developers.llamaindex.ai/python/llamaagents/workflows/durable_workflows/ (read 2026-11-10)
- https://developers.llamaindex.ai/python/llamaagents/workflows/human_in_the_loop/ (read 2026-11-10)
- https://docs.temporal.io/develop/python/integrations (read 2026-11-10)
- https://docs.temporal.io/develop/python/integrations/openai-agents (read 2026-11-10)
- https://docs.temporal.io/develop/python/integrations/langgraph (read 2026-11-10)
- https://docs.temporal.io/develop/python/integrations/google-adk (read 2026-11-10)
- https://docs.temporal.io/develop/python/integrations/claude-agent-sdk (read 2026-11-10)
- https://a2a-protocol.org/latest/specification/ (read 2026-11-10)
- https://docs.ag-ui.com/concepts/events (read 2026-11-10)
- https://docs.ag-ui.com/introduction (read 2026-11-10)
- https://research.ibm.com/projects/agent-communication-protocol (read 2026-11-10)
- https://github.com/i-am-bee/acp (read 2026-11-10)
- https://pypi.org/project/openai-agents/ (read 2026-11-10)
- https://pypi.org/project/google-adk/ (read 2026-11-10)
- https://pypi.org/project/langgraph/ (read 2026-11-10)
- https://pypi.org/project/crewai/ (read 2026-11-10)
- https://pypi.org/pypi/pydantic-ai/json (read 2026-11-10)
- https://pypi.org/project/agent-framework/ (read 2026-11-10)
- https://pypi.org/pypi/smolagents/json (read 2026-11-10)
- https://pypi.org/project/llama-index-workflows/ (read 2026-11-10)
- https://registry.npmjs.org/ai/latest (read 2026-11-10)
- https://registry.npmjs.org/@mastra%2Fcore/latest (read 2026-11-10)
