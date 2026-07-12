# LLM Provider Capability Docs

Reference documentation for the LLM chat APIs `ocai` adapts: **OpenAI**, **Google
Gemini**, **Anthropic (Claude)**, and **Mistral**. These are written to inform the
design of the canonical IR and the provider adapters (`ocai.core.ports.ChatModel`).

> Currency: researched June 2026 against each provider's live docs. Model IDs and a
> handful of fast-moving knobs (effort/thinking enums, cache minimums, exact model
> snapshots) drift — re-verify against each provider's `models` endpoint before relying
> on a specific string. Field/parameter names are stable.

## Contents

| Doc | What it covers |
|---|---|
| [openai.md](./openai.md) | OpenAI Responses + Chat Completions API surface, params, tools, reasoning, caching |
| [google-gemini.md](./google-gemini.md) | Gemini `generateContent`, `contents`/`parts`, thinking, grounding, Live API |
| [anthropic.md](./anthropic.md) | Claude Messages API, adaptive thinking/effort, server tools, prompt caching |
| [mistral.md](./mistral.md) | Mistral chat, FIM, OCR, Agents/Conversations, prefix messages |
| [feature-matrix.md](./feature-matrix.md) | Side-by-side comparison of every capability across all four providers |
| [common-interface.md](./common-interface.md) | How a provider-neutral interface should look, mapped onto `ocai`'s canonical IR |

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
conversion graph exist to absorb. See [common-interface.md](./common-interface.md).
