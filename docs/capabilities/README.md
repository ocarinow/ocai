---
icon: lucide/map
---

# Capabilities and providers — integration roadmap

!!! note "Currency"

    Researched 2026-11-10 against each vendor's official documentation; every
    page lists its sources with the read date and marks anything it could not
    confirm as *unverified*. Model ids, prices, and shutdown dates move fast;
    field names and wire shapes are the durable part. Re-verify a specific
    string against the vendor before relying on it.

This section is the survey behind the roadmap: every provider and capability
family that is relevant to the ocai libraries and the platform, each judged by
the same rule — the [§11 scope litmus test](../architecture.md#11-adding-a-capability-normative-recipe).
A thing is a **kernel capability** only when providers expose it through
*different wire dialects for the same operation*, so that honest conversion
has something to report. Otherwise it is a **chat-IR extension** (the chat
capability lacks a shape), a **satellite** library built on the kernel's
contracts, a **platform module**, or **deferred**.

Priorities: **P0** next after the current program, **P1** this horizon, **P2**
after the jobs/files substrate exists, **P3** watch only. Effort is in work
units (WUs) by analogy with the Anthropic plugin (WU-13/14a/14b ≈ 3 WUs for
one chat interface with unary + streaming + certification).

## Priority matrix

| Area | Verdict | Priority | First target | Effort | Depends on |
|---|---|---|---|---|---|
| [Search tools inside chat](web-search-and-retrieval.md) (citations, server-tool replay anchors) | chat-IR extension | **P0** | OpenAI `web_search` + Anthropic web search/fetch + Gemini grounding | 1–2 WUs | none; needed for the H1 `/responses` proof |
| [DeepSeek](../providers/deepseek.md) | chat dialect (OpenAI-shaped + reasoning replay) | **P0** | DeepSeek chat + reasoner | 2.5 WUs | none |
| [Amazon Bedrock](../providers/amazon-bedrock.md) | host + Converse interface | **P0** | InvokeModel for Anthropic, then Converse | 3 WUs | SigV4 credential (stdlib), event-stream parser |
| [Azure OpenAI](../providers/azure-openai.md) | host (existing codec) | **P0** | v1 surface, content-filter census | 2 WUs | none |
| [vLLM, OpenRouter](hosting-and-aggregators.md) | hosts (existing codecs) | **P0** | vLLM then OpenRouter | 2.5 WUs | `DialectTraits` growth (below) |
| [Observability](observability.md) | satellite `ocai-otel` | **P0** | OTel GenAI conventions | 2 WUs | Observer events (G-04 rescoped) |
| [Model catalog](model-catalog.md) | data under `spec/` + profile gate | **P1** | Anthropic + OpenRouter descriptors | 1 WU | none |
| [Caching, cost, rate limits](caching-cost-and-rate-limits.md) | codec knobs + `RateLimitPolicy` + cost interceptor | **P1** | cache hints on the Anthropic edge; OpenAI/Anthropic headers | 2 WUs | `UsageSource.CACHE_WRITE` |
| [Embeddings](embeddings.md) | kernel capability (provisional today) | **P1** (H3) | OpenAI embeddings, then Voyage | 3 WUs + 1/provider | additive IR changes |
| [Rerank](rerank.md) | kernel capability (new) | **P1** (H6) | Cohere rerank | 2.5 WUs | `Document` hoisted to core |
| [Vector stores](vector-stores.md) | kernel capability (provisional today) | **P1** (H3) | FAISS in-process, then Qdrant | 3 WUs + 1/store | filter AST, `[**]` census |
| [Hybrid and full-text search](hybrid-and-fulltext-search.md) | vectorstore `search` operation | **P1** | Qdrant Query API | with vector stores | fusion as declared shift |
| [Qwen](../providers/qwen.md), [Moonshot Kimi](../providers/moonshot-kimi.md) | chat dialects (OpenAI-shaped) | **P1** | compat mode first; native DashScope P3 | 2 WUs each | DeepSeek's reasoning-dialect traits |
| [Google Vertex](../providers/google-vertex.md) | host (exists) + credentials | **P1** | Claude on Vertex with OAuth | 1 WU now, +2 with Gemini | Gemini dialect (H2) |
| [Groq, Ollama, Together, Fireworks](hosting-and-aggregators.md) | hosts | **P1** | Groq (negative fixtures, rate headers) | 0.5 WU each | none |
| [Agent frameworks](agent-frameworks.md) | satellite adapters | **P1** | `ocai-pydantic-ai`, `ocai-langchain` | 1 WU each | none |
| [Identity and secrets](identity-and-secrets.md) | credential satellites | **P1** | `ocai-gcp` OAuth; Bedrock bearer/SigV4 | 1 WU each | none |
| [Tools and MCP](tools-and-mcp.md) | `Tool.strict`/origin + strict-subset census now; MCP client capability later | **P1** / **P2** | strict census; then `mcp` interface | 1 WU; 3 WUs | ADR for G-05 |
| [Gateways and routers](gateways-and-routers.md) | platform service | **P1** readiness | canonical `ocai` wire API + compat listeners as inbound edges | per WU-21 | kernel stays one call |
| [Evaluation](evaluation.md) | satellite on the ledger | **P1** substrate, **P2** runner | recorded-pair spec (G-02), replay transport | 2 WUs + 2 | G-02, G-03 |
| [Prompt management](prompt-management.md) | platform registry | **P1** (tags convention), **P2** registry | `CallContext.tags` convention | 0.5 WU | none |
| [Image generation](image-generation.md) | kernel capability (new) | **P1** | OpenAI Images, then Google Interactions | 3 + 2 WUs | jobs for async providers |
| [Document understanding](document-understanding.md) | kernel capability (new) | **P1** | Mistral OCR, then Azure Document Intelligence, Docling local | 3 WUs | jobs for async providers |
| [Standalone web search](web-search-and-retrieval.md) | kernel capability (new, `search` + `fetch`) | **P1** | Tavily, then Brave, Exa | 2 WUs | none |
| [Speech synthesis](speech-synthesis.md) | kernel capability (new) | **P1** | ElevenLabs, then OpenAI (migration proof) | 3 WUs | `DeltaBlob` accumulator |
| [Speech recognition](speech-recognition.md) | kernel capability (new) | **P1** batch, **P2** streaming | Deepgram, then OpenAI | 5 WUs | duplex transport for streaming |
| [Zhipu GLM](../providers/zhipu-glm.md), [xAI Grok](../providers/xai-grok.md) | chat dialects | **P2** | GLM compat; xAI as a Responses host | 1 WU; 1.5 WUs | xAI needs the `/responses` codec |
| [Files and assets](files-and-assets.md) | kernel capability (H6) | **P2** | OpenAI Files, Anthropic Files | 2 WUs | `ProviderRef` qualifier rule |
| [Batch and jobs](batch-and-jobs.md) | kernel `ocai.jobs` (H6) | **P2** | OpenAI Batch, Anthropic Message Batches | 3 WUs | files |
| [Moderation and safety](moderation-and-safety.md) | kernel capability (H7) | **P2** | OpenAI moderation + Bedrock ApplyGuardrail | 2 WUs | none |
| [Guardrails and PII](guardrails-and-pii.md) | hooks/interceptors; `pii` capability later | **P2** / **P3** | local Presidio redaction interceptor | 1 WU | hook protocols |
| [Video generation](video-generation.md) | kernel capability (new) | **P2** IR + 2 providers | Google Interactions (Omni Flash), Runway | 2 + 2 WUs | jobs |
| [Managed RAG and file search](managed-rag-and-file-search.md) | chat server tools + provider-scoped refs | **P2** | OpenAI file_search annotations | with search tools | files |
| [Code execution sandboxes](code-execution-sandboxes.md) | platform execution port; provider tools are chat parts | **P2** | Docker local reference, then E2B | 2 WUs | agent runtime |
| [Realtime voice](realtime-voice.md) | kernel capability later; duplex transport first | **P3** / **P2** transport | OpenAI Realtime, then Gemini Live | 6 WUs | STT streaming |
| [Cohere](../providers/cohere.md) | own interface (non-OpenAI shapes) | **P3** | — | 3 WUs | two citation data points first |
| [Fine-tuning](fine-tuning.md) | front-door grammar note only | **P3** | — | 0 | market contracting |
| [Ingestion, chunking, memory](ingestion-chunking-and-memory.md) | platform / satellites | — | — | — | embeddings + vector stores |
| [Vision and classification](vision-and-classification.md) | deferred | **P3** | — | — | covered by multimodal chat |
| [Music and sound](music-and-sound.md) | deferred | **P3** | — | — | closed or incongruent APIs |

## Sequencing

1. **Chat completeness and hosts.** Citation annotations and server-tool
   replay anchors in the chat IR (the `/responses` proof is dishonest
   without them), the DeepSeek reasoning-replay dialect, Bedrock and Azure
   as hosts, vLLM and OpenRouter. This tier grows `DialectTraits` once, for
   every later host.
2. **Telemetry and catalog data.** The first satellite (`ocai-otel`) and the
   model-descriptor data that feeds the profile gate and cost metering.
   Both exercise hook protocols before they freeze.
3. **Retrieval (H3).** Embeddings and vector stores leave provisional
   status; rerank is the first capability added by the §11 recipe after the
   freeze; hybrid search rides the vectorstore `search` operation.
4. **New generation capabilities.** Image, document parsing, standalone
   search, speech synthesis and batch transcription — each synchronous first
   provider, so none waits on the jobs substrate.
5. **Jobs and files substrate (H6), then what needs it.** Batch APIs,
   video, async document and image providers, managed RAG handles,
   moderation with guardrail policies.
6. **Platform-tier.** MCP client capability after the G-05 ADR, agent
   framework adapters as soon as useful, sandboxes and realtime with the
   agent runtime.

## Kernel changes the research implies

Collected from the mapping sections; each becomes a WU or an ADR, none is
done yet.

- **`DialectTraits` and `Host` growth** (16 items in [hosting](hosting-and-aggregators.md)):
  per-host body-version maps, version vs feature headers, explicit
  `path_prefix`, static headers, query maps, a `profile_key(resource)` hook,
  `ApiKey(header=...)`, an explicit `NoCredential`, `EventStreamParser` for
  Bedrock's binary stream, dual decode of `reasoning` / `reasoning_content`.
- **Chat IR:** canonical `Annotation(kind="url_citation", …)` with span
  validation, `ServerTool` entries on `ChatRequest.tools`, replay lanes as
  `ProviderRef` anchors, a `search_requests` consumption dimension,
  first-class `Tool.strict` and a `Tool.origin` provenance stamp, cache
  hints (`config.cache` is censused DROPPED on both edges today).
- **Core vocabulary:** `Document` hoisted to `ocai.core` (rerank cannot
  import embedding), open `UsageUnit` codes (`pixels`, `images`,
  `search_units`, `pages`, `credits`, `samples`, `megapixels`,
  `cpu_seconds`), `UsageSource.CACHE_WRITE`, `CredentialRef(kind, locator)`,
  taxonomy additions `payment_required` and `PayloadTooLargeError`.
- **`ProviderRef`:** file-id validity is narrowed by *purpose* and *host*
  below the provider level; the crossing rule should compare
  `(provider, qualifier)` for file refs.
- **Jobs:** `Job`/`JobHandle` with open state codes and two distinct
  "expired" meanings (work expired vs never started), per-item results
  through the normal response edge so each carries its own report.
- **Vector stores:** typed filter AST with the reserved `[**]` census token,
  `score_kind` and `native_score`, sparse and named vectors, a `search`
  operation with lanes and declared fusion.
- **Streaming laws per capability:** fold-by-replacement for images, byte
  concatenation plus mark rebasing for speech, last-wins-by-id finals for
  transcription, frame log to transcript for realtime.
- **Runtime:** `DuplexTransport` beside the HTTP transport; stream events
  and inbound trace context on `CallContext` (G-04 rescoped: `call_id` and
  `attempt` already exist on the Observer events).

## Market changes worth knowing

Verified on official pages on the read date; they change what is worth
building: OpenAI shut down the Sora Videos API (2026-09-24), the Assistants
API (2026-08-26), `gpt-image-1` (2026-10-23), reusable prompt objects and the
Evals API (2026-11-30), and announced fine-tuning and unary TTS / Whisper
shutdowns for 2027; Google retired Imagen on both surfaces and the Veo
preview on the Gemini API in favour of the Interactions API; Bing Search API
retired 2025-08-11; Perplexity Sonar chat completions ended 2026-09-27;
Hugging Face TGI is archived; Mistral and Cohere deprecated fine-tuning;
Azure Content Safety retires several features 2027-04-30. Each page carries
the detail.

## Method and caveats

Nine research passes, one per family, each writing only its own pages from
official documentation read on 2026-11-10, with a shared skeleton: API
surface, request and response shapes with exact field names, streaming,
auth and errors, distinctive features, and a mapping section that assigns
every knob to a lane of the three-lane law and names the semantic shifts.
The shared web-search budget ran out part-way through several passes;
later claims rest on direct fetches of official pages, and anything that
could not be fetched is marked unverified rather than inferred. Nothing here
is implemented; the matrix is a plan, not a status.
