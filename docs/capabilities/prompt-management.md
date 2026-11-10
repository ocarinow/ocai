# Prompt management

**Currency:** researched 2026-11-10 against vendor documentation as published
that day. Two of the three first-party provider offerings in this family are
gone or going: OpenAI reusable prompt objects shut down 2026-11-30 and
Anthropic's experimental prompt tools were retired 2026-08-17. Anything not
confirmed from an official page is marked *unverified*.

**Status:** planned. The registries module is "typed, versioned registries
of tools, skills, and MCP servers" (platform README); prompts are the fourth
asset kind and are not yet listed there. The kernel contributes substrate
only.

## 1. Why this family matters to ocai

A prompt version is the first of the three suspects in H7's attribution
thesis (prompt, provider revision, conversion). If the platform cannot name
*which* prompt version a call ran, the ledger's other two columns lose half
their value. The scope litmus test (§11) is explicit that prompt management
"has no wire dialect" and is built ON ocai — so the question is only what
the kernel must offer so a registry can hash, version, and link a prompt to
a `CallResult`.

## 2. Landscape

### 2.1 Products

| Product | Version model | Labels / environments | Templating | Bound config | SDK caching | Trace linkage | Hosting |
|---|---|---|---|---|---|---|---|
| Langfuse | immutable integer `version` per `name`; `type` ∈ `text`/`chat` | `production` (runtime default), `latest` (reserved), custom; protected labels (Enterprise) | `{{var}}`; chat placeholders `{"type": "placeholder", "name": ...}`; composability `@@@langfusePrompt:name=…\|version=…@@@` | `config` JSON versioned with the prompt (`model`, `temperature`, `tools`, `response_format`) | in-memory, default TTL 60 s, stale-while-revalidate, `fallback` | `prompt=` on generations; `langfuse.observation.prompt.name/.version` in OTel | MIT core; self-hostable |
| LangSmith Hub | commit hash per save; `"name:hash"`, `"name:tag"` | movable tags; `staging`, `production` reserved for Environments | `f-string` (`{var}`) or `mustache` | model + tools + schema saved with the prompt (`include_model=True`) | `skip_cache` | *unverified* | hosted / self-hosted enterprise |
| PromptLayer | integer versions with commit messages | release labels; dynamic labels with percentage splits | `f-string` or Jinja2 | `llm_kwargs` ("may change without notice") | invalidated on publish | logs per version | hosted |
| Braintrust | transaction id per save; latest default | environments (Pro/Enterprise); `bt prompts assign … --environment` | Mustache | model + params + tools ("deployed with functions") | memory + disk; version/environment loads never fall back | `metadata.prompt` on the LLM span | hosted |
| Portkey | immutable versions; publish sets default; `prompt_id@latest`, `@12`, `@label` | `production`, `staging`, `development` fixed + custom | Mustache + partials | `parameters` | *unverified* | logs | hosted; gateway OSS |
| W&B Weave | `weave.publish` → immutable `:v0…`; refs `name:production`, `:latest` | aliases + tags | `{var}` format strings | no | — | tracked objects | SDK Apache-2.0 |
| Vertex AI prompts | `client.prompts.create` / `create_version` / `get_version` / `list_versions` / `restore_version`; GA in `google-cloud-aiplatform` 1.119.0+ | none documented | `{name}` with `Part` values | `PromptData(model, contents, generation_config, tools, system_instruction, variables)` | — | — | GCP |
| OpenAI prompt objects | `prompt: {id, version, variables}` on Responses | none | dashboard variables (strings or input items) | yes | — | — | **`v1/prompts` shuts down 2026-11-30**; migration guide says move prompt text into code |
| Anthropic | none server-side; `{{var}}` is a Console convention | none | client-side | — | — | — | prompt tools API retired 2026-08-17 with the legacy Workbench; the playground has no saved prompts or versions |
| Humanloop | — | — | — | — | — | — | **sunset 2025-09-08** |
| Vellum, Latitude, PromptHub, Agenta, Pezzo | release tags / draft-published / branches+commits / *unverified* / *unverified* | environments / live vs `versionUuid` / branches | typed inputs / PromptL / `{{var}}` | yes / yes / `formatted_request` | — | — | SaaS / MIT / SaaS / MIT / Apache-2.0 |

### 2.2 Common denominator — the portable prompt asset

Every live product converges on:

- `name` — stable id, optionally path-like (`folder/name`).
- `version` — an immutable per-revision id (integer, commit hash,
  transaction id); never edited in place.
- `labels` — mutable pointers (`production`, `staging`, custom; `latest`
  reserved). Resolution rule everywhere: an explicit version beats a label;
  an unresolvable label is an error. Langfuse states it "never silently falls
  back to `production` or `latest`"; Braintrust loads with
  `version`/`environment` "never fall back".
- `content` — a text template or ordered `{role, content}` messages, with
  optional message placeholders.
- `template_syntax` — declared per asset (`mustache`, `f-string`, `jinja2`,
  `promptl`).
- `variables` — name → type; mostly untyped strings; Vellum and legacy OpenAI
  allow typed/multimodal inputs; Langfuse placeholders take message lists.
- `config` — bound invocation parameters (model, temperature, tools, output
  schema) as opaque JSON.
- a `hash` of (content, config, variables) so a call can record exactly what
  ran even if the registry is unreachable.

Runtime linkage everywhere reduces to `{name, version, label_used, hash}` on
the trace — the OTel GenAI conventions carry it as `gen_ai.prompt.name` and
`gen_ai.prompt.version` (plus opt-in `gen_ai.prompt.variable`), Langfuse as
`langfuse.observation.prompt.*`, OpenInference as `llm.prompt_template.*`.

## 3. What the kernel has today

- A pure-data chat IR: `Message(role, parts)`, `ChatRequest(messages, tools,
  config, ...)`, `ChatConfig` — serializable, language-neutral, with JSON
  Schema in `spec/`. A rendered prompt *is* a `ChatRequest` minus the
  variables.
- `canonjson` — the equality predicate and the content address: two renders
  of the same prompt version with the same variables produce identical
  canonical bytes, so a hash of the canonical request identifies "what ran".
- `ChatConfig` carries the config a prompt binds (`temperature`,
  `max_output_tokens`, `reasoning`, `output`, `cache`) with every knob
  honest under the three-lane law — a bound config that names a knob the
  target interface lacks produces a `FieldLoss`, not a silent drop.
- No `model` in the request (§11.3): a prompt asset that binds a model binds
  it at the *front door* (`ocai.chat.model("provider/resource")`), which is
  exactly where the platform's label-to-deployment mapping belongs.
- `CallContext.tags` — the carrier for `prompt.name`, `prompt.version`,
  `prompt.hash` on every call, exported by the telemetry satellite as
  `gen_ai.prompt.name`/`gen_ai.prompt.version` and `ocai.ctx.tag.*`.
- Nothing for templating, variables, labels, or storage — correctly, since
  none of those has a wire dialect.

## 4. Verdict: platform registry territory; the kernel contributes three things

### 4.1 The registry module

A prompt registry is the fourth typed, versioned asset in the registries
module, sharing infrastructure with tools, skills, and MCP servers ("registry
infrastructure may be shared while agent, skill, tool, and MCP asset
contracts remain distinct" — modernization plan). Its asset contract is the
§2.2 denominator, with content stored as a **canonical chat IR template**:
`messages` in the kernel's `Message` shape with variable slots, `config` as a
`ChatConfig`, `tools` as kernel `Tool`s, `template_syntax` declared.
Rendering produces a `ChatRequest`; nothing else in the platform needs to
know a prompt existed.

### 4.2 What the kernel contributes

1. **Pure-data IR as the storage shape.** No new type. A prompt version is a
   `ChatRequest`-shaped document with `variables` declared; the
   `spec/schema/chat.request.schema.json` already validates the rendered
   form. A `PromptTemplate` schema in the registry's own `spec/` extends it
   with `variables` and `template_syntax` — registry-owned, not kernel-owned.
2. **Canonical JSON for hashing a version.** `canonjson` bytes over the
   stored template give `content_hash`; `canonjson` over the rendered
   `ChatRequest` gives `request_hash`. The pair (`content_hash`,
   `request_hash`) is what the eval satellite joins on and what makes
   "same prompt, different provider revision" a one-line query.
3. **A reserved tag convention on `CallContext`.** `tags["ocai.prompt.name"]`,
   `["ocai.prompt.version"]`, `["ocai.prompt.label"]`, `["ocai.prompt.hash"]`
   — documented in the kernel so every satellite (telemetry, eval, audit,
   gateway) reads the same keys. This is a convention, not a type; it costs
   nothing and freezes nothing.

### 4.3 What the kernel must not grow

- No templating engine, no variable typing, no label resolution in
  `ocai.core` or `ocai.chat` — three products use three syntaxes and the
  registry declares which one an asset uses.
- No `prompt` field on `ChatRequest` mirroring OpenAI's
  `prompt: {id, version, variables}`: that object is being shut down on
  2026-11-30 and has one interface; it fails the three-lane checklist and the
  market. Were a provider to revive server-side prompt references, they ride
  `provider_options` or a censused extension.
- No provider-side prompt storage integration (Vertex `client.prompts.*`,
  Bedrock Prompt management) in the kernel: those are registry *backends*
  the platform may sync to, with `ProviderRef`-style scoping.

### 4.4 Interoperate first

| Target | How | Why first |
|---|---|---|
| Langfuse prompts | registry backend adapter: `get_prompt(name, label\|version)` → kernel template; write-back of `langfuse.observation.prompt.name/.version` via the telemetry satellite | MIT, self-hostable, the only one with an explicit no-silent-fallback rule and OTel linkage |
| LangSmith Hub | `pull_prompt("name:tag", include_model=True)` → kernel template | enterprises already there |
| OTel `gen_ai.prompt.name/.version` | emitted from `CallContext.tags` | every backend |
| Vertex `client.prompts.*`, Bedrock Prompt management | optional sync backends | cloud-native shops |
| Portkey, Braintrust, PromptLayer, Weave | adapters on demand | — |

## 5. Priority and sequencing

| Item | Priority | Depends on |
|---|---|---|
| Reserved `CallContext.tags` keys for prompt identity, documented in the kernel and emitted by the telemetry satellite | **P1** (zero cost; makes every trace prompt-attributable before any registry exists) | telemetry satellite |
| `PromptTemplate` schema in the registries module (`ChatRequest` + `variables` + `template_syntax`), with `content_hash`/`request_hash` via `canonjson` | P2 | registries module skeleton |
| Langfuse and LangSmith backend adapters | P2 | `PromptTemplate` |
| Label resolution, environments, A/B via labels in the registry | P3 | registry |
| Provider sync backends (Vertex, Bedrock) | P3 | — |

## 6. Open questions and unverified items

- OpenAI `input_image`/`input_file` variable payloads for the legacy prompt
  object, the Anthropic `prompt-tools-2025-04-02` beta header, and
  LangSmith's prompt-to-trace linkage are *unverified*; none affects the
  verdict.
- Vertex `vertexai.preview.prompts` deprecation status is *unverified*; the
  GA path is `vertexai.Client().prompts`.
- Whether the registry stores prompts as ordered interaction items (ADR
  0003) or `2026-07` single-message shape: store at the active canonical
  revision and migrate through `migrate.py` like any other IR document —
  prompts are the first *stored* IR documents and will exercise the
  migration edges.
- Whether `request_hash` should exclude `CallContext`-derived fields
  (deadline, tenant) — yes; it hashes the `ChatRequest` only.

## Sources

- https://langfuse.com/docs/prompt-management/get-started (read 2026-11-10)
- https://langfuse.com/docs/prompt-management/features/caching (read 2026-11-10)
- https://langfuse.com/docs/prompt-management/features/prompt-version-control (read 2026-11-10)
- https://langfuse.com/docs/prompt-management/features/link-to-traces (read 2026-11-10)
- https://langfuse.com/docs/prompt-management/features/config (read 2026-11-10)
- https://langfuse.com/docs/prompt-management/features/composability (read 2026-11-10)
- https://cloud.langfuse.com/generated/api/openapi.yml (read 2026-11-10)
- https://docs.langchain.com/langsmith/manage-prompts-programmatically (read 2026-11-10)
- https://docs.langchain.com/langsmith/prompt-engineering-concepts (read 2026-11-10)
- https://docs.langchain.com/langsmith/smith-api/commits/get-a-commit.md (read 2026-11-10)
- https://docs.promptlayer.com/features/prompt-registry/overview (read 2026-11-10)
- https://docs.promptlayer.com/features/prompt-registry/release-labels (read 2026-11-10)
- https://docs.promptlayer.com/reference/templates-get (read 2026-11-10)
- https://humanloop.com/docs/changelog (read 2026-11-10)
- https://docs.braintrust.dev/guides/functions/prompts (read 2026-11-10)
- https://docs.braintrust.dev/evaluate/prompts/versions.md (read 2026-11-10)
- https://docs.braintrust.dev/deploy/environments.md (read 2026-11-10)
- https://docs.braintrust.dev/kb/link-prompt-versions-to-traces-from-code.md (read 2026-11-10)
- https://portkey.ai/docs/product/prompt-library (read 2026-11-10)
- https://portkey.ai/docs/product/prompt-engineering-studio/prompt-api (read 2026-11-10)
- https://portkey.ai/docs/product/prompt-engineering-studio/prompt-versioning.md (read 2026-11-10)
- https://developers.openai.com/api/docs/deprecations (read 2026-11-10)
- https://developers.openai.com/api/docs/guides/prompting/migrate-from-prompt-object (read 2026-11-10)
- https://developers.openai.com/api/reference/cli/resources/responses/methods/create/index.md (read 2026-11-10)
- https://platform.claude.com/docs/en/release-notes/overview (read 2026-11-10)
- https://support.claude.com/en/articles/8606378-how-do-i-use-the-playground (read 2026-11-10)
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/prompt-classes (read 2026-11-10)
- https://docs.cloud.google.com/python/docs/reference/vertexai/latest/vertexai._genai.prompts.Prompts (read 2026-11-10)
- https://docs.cloud.google.com/python/docs/reference/aiplatform/latest/changelog (read 2026-11-10)
- https://docs.coreweave.com/weave/guides/core-types/prompts/ (read 2026-11-10)
- https://docs.vellum.ai/api-reference/prompts/execute-prompt (read 2026-11-10)
- https://docs.latitude.so/ (read 2026-11-10)
- https://prompthub.us/blog/prompthub-anthropic-integration-guide (read 2026-11-10)
- https://agenta.ai/docs/ (read 2026-11-10)
- https://github.com/pezzolabs/pezzo (read 2026-11-10)
