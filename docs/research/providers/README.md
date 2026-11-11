# LLM Provider Capability Docs

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

Reference documentation for the LLM chat APIs `ocai` adapts: **OpenAI**, **Google
Gemini**, **Anthropic (Claude)**, and **Mistral**. These are written to inform the
design of the canonical IR (`docs/architecture.md` §3) and the per-interface plugins
(§7). They live under `docs/` so every coding agent and human finds them.

> Currency: researched June 2026 against each provider's live docs. Model IDs and a
> handful of fast-moving knobs (effort/thinking enums, cache minimums, exact model
> snapshots) drift — re-verify against each provider's `models` endpoint before relying
> on a specific string. Field/parameter names are stable.

## Contents

| Doc | What it covers |
|---|---|
| [openai.md](openai.md) | OpenAI Responses + Chat Completions API surface, params, tools, reasoning, caching |
| [google-gemini.md](google-gemini.md) | Gemini `generateContent`, `contents`/`parts`, thinking, grounding, Live API |
| [anthropic.md](anthropic.md) | Claude Messages API, adaptive thinking/effort, server tools, prompt caching |
| [mistral.md](mistral.md) | Mistral chat, FIM, OCR, Agents/Conversations, prefix messages |
| [feature-matrix.md](feature-matrix.md) | Side-by-side comparison of every capability across all four providers |
| [common-interface.md](common-interface.md) | How a provider-neutral interface should look, mapped onto `ocai`'s canonical IR |

Added 2026-11-10 (same 13-section skeleton, each with a Currency note, a
mapping section with lane assignments and a priority, and a Sources list):

| Doc | What it covers |
|---|---|
| [deepseek.md](deepseek.md) | DeepSeek V3/R1: OpenAI-shaped API, mandatory `reasoning_content` replay with tools, prefix/FIM, disk cache — **P0** |
| [qwen.md](qwen.md) | Alibaba Model Studio / DashScope: compat mode and native envelope, Qwen3 thinking, VL, Omni — P1 |
| [moonshot-kimi.md](moonshot-kimi.md) | Moonshot Kimi K2/K3: compat API, reasoning replay without anchors, fixed sampling knobs — P1 |
| [zhipu-glm.md](zhipu-glm.md) | Z.ai / Zhipu GLM: compat API, mid-stream errors in `finish_reason`, search tool — P2 |
| [xai-grok.md](xai-grok.md) | xAI Grok: chat completions (legacy) and Responses, encrypted reasoning, live search — P2 |
| [cohere.md](cohere.md) | Cohere v2 chat: non-OpenAI message/tool shapes, span citations, documents — P3 |
| [amazon-bedrock.md](amazon-bedrock.md) | Bedrock Converse + InvokeModel, SigV4, binary event stream, guardrails, compat routes — **P0** host |
| [azure-openai.md](azure-openai.md) | Azure OpenAI v1 surface, Entra auth, content-filter annotations — **P0** host |
| [google-vertex.md](google-vertex.md) | Vertex generateContent vs Gemini API, OAuth/ADC, partner models (Claude on Vertex) — P1 host |

The capability-level survey (embeddings, rerank, vector stores, image, speech,
documents, search, files, jobs, moderation, and the platform ecosystem) is
in [Capabilities](../capabilities/README.md).

## How to read these

Each provider doc follows the same skeleton so they can be diffed against one another:

1. **API surface / endpoints** — what calls exist
2. **Request & response model** — message/role/content shape
3. **Generation parameters** — sampling and limit knobs (with exact field names)
4. **Structured outputs** — JSON mode / schema enforcement
5. **Tool / function calling** — definitions, choice, parallelism, server-side tools
6. **Streaming** — wire format and event types
7. **Reasoning / thinking** — how extended reasoning is configured and exposed
8. **Prompt / context caching**
9. **Multimodal** — vision, audio, documents
10. **Models** — families and positioning
11. **Auth, limits, errors**
12. **Distinctive features** — what only this provider has
13. **Mapping to `ocai`** — IR/adapter implications

The recurring lesson across all four: the **request bodies are ~80% the same idea**
(an ordered list of role-tagged messages + sampling knobs + tool declarations) but
**diverge in naming and in the long tail** (reasoning, caching, server tools,
multimodal parts, structured-output placement). That long tail is exactly what the
canonical IR's `provider_options` / `extensions` escape hatches and the loss-weighted
conversion graph exist to absorb. See [common-interface.md](common-interface.md).
