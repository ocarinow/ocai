# Tools and MCP

**Currency:** researched 2026-11-10 against modelcontextprotocol.io, the
MCP registry repository, and provider documentation as published that day.
The current MCP specification revision is `2026-07-28`; prior revisions
`2025-11-25`, `2025-06-18`, `2025-03-26`, `2024-11-05` are cited where
provider connectors still speak them. Anything not confirmed from an official
page is marked *unverified*.

**Status:** planned. The kernel ships `Tool(name, parameters, description,
output)`, `ToolChoice(mode, name)`, `PartToolCall` (client-executed) and
`PartServerToolCall(kind, call_id, status, payload)` (provider-executed,
payload verbatim). No MCP client, no registry, no tool execution exists.

## 1. Why this family matters to ocai

Tools are where provider dialects diverge fastest: four tool-definition
shapes, four JSON-Schema subsets, three `tool_choice` vocabularies, and now
four provider-side MCP connector shapes — each changing monthly. The kernel
already made the structural call (`PartServerToolCall` types only the spine
and keeps the payload byte-faithful). The open decisions are: whether an MCP
*client* is a §11 capability or a satellite (gap G-05), where provider-side
MCP knobs sit under the three-lane law, and what substrate a tool/skill
registry needs from the kernel.

## 2. Landscape

### 2.1 MCP specification (`2026-07-28`)

- **Base**: JSON-RPC 2.0; request `id` string or integer, never null; result
  `resultType` ∈ `"complete"` | `"input_required"`; error codes `-32020
  HeaderMismatch`, `-32021 MissingRequiredClientCapability`, `-32022
  UnsupportedProtocolVersion`; JSON Schema 2020-12 by default; network `$ref`
  must not be auto-dereferenced.
- **Lifecycle (stateless redesign)**: `initialize`/`notifications/initialized`
  and the `Mcp-Session-Id` header are *removed*; every request carries
  `_meta["io.modelcontextprotocol/protocolVersion"]` and
  `_meta["io.modelcontextprotocol/clientCapabilities"]`; servers must
  implement `server/discover` (→ `supportedVersions`, `capabilities`,
  `instructions`, `ttlMs`, `cacheScope`). Deprecated: Roots, Sampling,
  Logging, HTTP+SSE, RFC 7591 dynamic client registration. A feature
  lifecycle policy (Active/Deprecated/Removed, 12-month window) governs
  removals.
- **Transports**: stdio (newline-delimited); Streamable HTTP as a POST-only
  single endpoint with headers `MCP-Protocol-Version`, `Mcp-Method`,
  `Mcp-Name`, request-scoped SSE, and `subscriptions/listen` for
  `notifications/*/list_changed`. Legacy Streamable HTTP (`2025-03-26` to
  `2025-11-25`) used POST+GET+DELETE, `Mcp-Session-Id`, and `Last-Event-ID`
  resumability — still spoken by several provider connectors.
- **Server primitives**: tools (`tools/list`, `tools/call{name, arguments}`;
  fields `name, title, description, icons, inputSchema, outputSchema,
  annotations{readOnlyHint, destructiveHint, idempotentHint, openWorldHint}`;
  results `content[]`, `structuredContent`, `isError`); resources
  (`resources/list`, `resources/read`, `resources/templates/list`); prompts
  (`prompts/list`, `prompts/get{name, arguments}` → `messages[]`).
- **Client primitives**: replaced by Multi Round-Trip Requests — a
  `tools/call` may return `resultType: "input_required"` with
  `inputRequests` (`elicitation/create`, deprecated `sampling/createMessage`,
  `roots/list`) that the client answers via `inputResponses` + echoed
  `requestState`. Elicitation has `mode: "form"|"url"`, a flat
  `requestedSchema`, and `action: accept|decline|cancel`.
- **Authorization**: OAuth 2.1; servers and clients MUST support RFC 9728
  protected-resource metadata; RFC 8414 or OIDC discovery; RFC 8707
  `resource` indicators; `Authorization: Bearer` only, never query string; no
  token passthrough. Extensions: `io.modelcontextprotocol/oauth-client-credentials`,
  Enterprise-Managed Authorization (Stable).
- **Registry** (`https://registry.modelcontextprotocol.io`): **preview**;
  `GET /v0.1/servers`, `/v0.1/servers/{serverName}/versions`, `/v0.1/validate`;
  `server.json` schema `2025-12-11`; `name` matches
  `^[a-zA-Z0-9.-]+/[a-zA-Z0-9._-]+$`; fields `packages[{registryType,
  identifier, version, transport{type: stdio|streamable-http|sse}}]`,
  `remotes[{type, url, headers}]`.
- **Governance**: donated to the Agentic AI Foundation (Linux Foundation) on
  2025-12-09; SDK tiers — Tier 1 TypeScript, Python, C#, Go, Rust, Ruby.

### 2.2 Provider-side MCP connectors

| Provider | Request shape | Output items | Protocol spoken |
|---|---|---|---|
| OpenAI Responses | `tools: [{type: "mcp", server_label, server_url, server_description, connector_id, tunnel_id, authorization, allowed_tools: [...], require_approval: "always"\|"never"\|{never: {tool_names}}, defer_loading}]`; `headers` *unverified*; `connector_id` deprecated for models after 2026-09-01 | `mcp_list_tools`, `mcp_call{name, arguments, output, error, server_label, approval_request_id}`, `mcp_approval_request{id, name, arguments, server_label}`; input `mcp_approval_response{approval_request_id, approve}` | Streamable HTTP or HTTP+SSE |
| Anthropic Messages (beta `mcp-client-2025-11-20`, `mcp-client-2026-09-15`; `mcp-client-2025-04-04` deprecated) | `mcp_servers: [{type: "url", url, name, authorization_token}]` plus `tools: [{type: "mcp_toolset", mcp_server_name, default_config{enabled, defer_loading}, configs, cache_control, tools}]` | `mcp_tool_use{id, name, server_name, input}`, `mcp_tool_result{tool_use_id, is_error, content[]}`, `mcp_tool_listing` | Streamable HTTP and SSE; tools only; no stdio |
| Gemini `generateContent` | `tools[].mcpServers[{name, transport: {streamableHttpTransport: {url, headers, timeout, sseReadTimeout, terminateOnClose}}}]`; Agents API `{type: "mcp_server", name, url, headers, allowed_tools: [{mode, tools}]}` | server-executed | Streamable HTTP |
| Bedrock Responses API | `{type: "mcp", server_label, connector_id: <Lambda ARN \| AgentCore Gateway ARN>, require_approval: "never"}` | OpenAI-shaped items | via AgentCore Gateway (GA 2025-10-13; speaks `2026-07-28`, `2025-11-25`, `2025-06-18`, `2025-03-26`) |

### 2.3 Tool-definition formats

| | OpenAI Chat Completions | OpenAI Responses | Anthropic | Gemini | Bedrock Converse |
|---|---|---|---|---|---|
| Definition | `tools[].type: "function"`, `tools[].function.{name, description, parameters, strict}` | `{type: "function", name, description, parameters, strict}`; also `{type: "custom", name, format: {type: "grammar", syntax: "lark"\|"regex", definition}}` | `{name, description, input_schema, input_examples, cache_control, strict, defer_loading, allowed_callers, eager_input_streaming}` | `functionDeclarations[{name, description, behavior: BLOCKING\|NON_BLOCKING, parameters (OpenAPI-style Schema), parametersJsonSchema, response, responseJsonSchema}]` | `toolConfig.tools[{toolSpec: {name, description, inputSchema: {json}}}]` |
| Choice | `none\|auto\|required\|{type: "function", function: {name}}` | `auto\|required\|none\|{type: "function", name}\|{type: "allowed_tools", mode, tools}` | `tool_choice: {type: auto\|any\|tool\|none, name, disable_parallel_tool_use}` (`any`/`tool` rejected by several 5.x models) | `toolConfig.functionCallingConfig: {mode: AUTO\|ANY\|NONE\|VALIDATED, allowedFunctionNames[]}` | `toolChoice: {auto: {}}\|{any: {}}\|{tool: {name}}` (model-dependent) |
| Call / result | `tool_calls[{id, type, function: {name, arguments}}]` | `function_call{id, call_id, name, arguments}`, `function_call_output{call_id, output}` | `tool_use{id, name, input}`, `tool_result{tool_use_id, content, is_error}` | `functionCall{name, args}`, `functionResponse{name, response}` | `toolUse{toolUseId, name, input}`, `toolResult{toolUseId, content[], status}` |

### 2.4 JSON-Schema subset divergences (strict modes)

| Keyword | OpenAI strict | Anthropic strict | Gemini `parameters` Schema | Gemini `parametersJsonSchema` |
|---|---|---|---|---|
| `additionalProperties: false` | required everywhere | supported, expected | n/a (closed by construction) | per JSON Schema |
| all properties `required` | required (null unions for optionals) | not required; limits 24 optional params | `required[]` | per JSON Schema |
| `$ref`/`$defs` | supported incl. recursion (`"$ref": "#"`) | `$ref`, `$def`, `definitions` supported; recursion and external refs unsupported | no | *unverified* |
| `anyOf` | supported (not at root) | supported; 16 union params max | `anyOf` field exists | yes |
| `allOf`, `not`, `if/then/else`, `dependent*` | unsupported | `allOf` supported | no | *unverified* |
| `enum`, `const` | yes | yes | `enum` | yes |
| `format` | `date-time, time, date, duration, email, hostname, ipv4, ipv6, uuid` | `date-time, time, date, duration, email, hostname, uri, ipv4, ipv6, uuid` | `format` field | yes |
| `pattern`, `minLength/maxLength` | supported (some only on fine-tuned models) | simple `pattern` only; `minLength/maxLength` unsupported | `pattern`, `minLength`, `maxLength` | yes |
| `minimum/maximum/multipleOf` | supported | unsupported | `minimum`, `maximum` | yes |
| `minItems/maxItems` | supported | `minItems` 0 or 1 | both | yes |
| `nullable` | via type unions with `null` | type unions | `nullable` field, `NULL` type | `null` type |
| Limits | depth 10, 5,000 properties, 1,000 enum values, 120k chars | 20 strict tools | — | — |

Every cell that differs is a `FieldLoss` the edge must declare: a strict
schema that uses `minimum` converts to Anthropic with `DROPPED` on that
keyword, never silently.

### 2.5 Computer use, browsers, OpenAPI, skills

- **OpenAI**: `{type: "computer"}` tool with `computer_call{call_id, status,
  actions[], pending_safety_checks}` and `computer_call_output{call_id,
  output: {type: "computer_screenshot", image_url}}`; legacy
  `computer_use_preview` with `display_width/height`, `environment`,
  `truncation: "auto"`.
- **Anthropic**: `computer_toolset_20260801` (no beta header); earlier
  `computer_20251124`/`computer_20250124` with `display_width_px`,
  `display_height_px`, `display_number`; `text_editor_20250728`
  (`str_replace_based_edit_tool`), `bash_20250124`, `browser_toolset_20260801`.
- **Browser providers**: Browserbase/Stagehand (`act`/`extract`/`observe`;
  hosted MCP at `mcp.browserbase.com/mcp`, repo archived), Browser Use (MIT;
  Cloud API `POST /api/v4/runs`; MCP via `browser-use --cli-mcp`), Playwright
  MCP (`@playwright/mcp`, Apache-2.0).
- **OpenAPI-to-tool**: GPT Actions consume OpenAPI with
  `x-openai-isConsequential`; Gemini accepts OpenAPI-style `Schema`; FastMCP
  `FastMCP.from_openapi(openapi_spec, client, route_maps, ...)`; AgentCore
  Gateway targets OpenAPI/Smithy/Lambda/MCP with names `targetName___toolName`;
  Anthropic has no native OpenAPI import (MCP or `input_schema`).
- **Agent Skills** (agentskills.io): `SKILL.md` with frontmatter `name`
  (1–64, `[a-z0-9-]`, equals directory name), `description` (1–1024),
  optional `license`, `compatibility`, `metadata`, `allowed-tools`
  (experimental); optional `scripts/`, `references/`, `assets/`; progressive
  disclosure. Anthropic Skills API (stable): `POST/GET /v1/skills`,
  `/v1/skills/{skill_id}/versions`, Messages `container: {skills: [{type:
  "anthropic"|"custom", skill_id, version}]}` with the
  `code_execution_20250825` tool, max 20. Claude Agent SDK loads
  `.claude/skills/` by `setting_sources`. Adopter list *unverified*
  (showcase page not readable).

## 3. What the kernel has today

- `Tool(name, parameters: JsonSchema, description, output)` — pure data, no
  callable, no `strict` field, no annotations (read-only/destructive hints),
  no provenance.
- `ToolChoice(mode ∈ auto|none|required|named, name)`.
- `PartToolCall(call_id, name, args_json, status, executed_by)` with the
  lifecycle `input_streaming → input_complete → executing → output_available
  | output_error`.
- `PartServerToolCall(kind, call_id, status, payload)` — `kind="mcp_call"`
  covers provider-executed MCP with the payload verbatim; `PartServerToolResult`
  is its sibling.
- `ProviderRef` for provider-side handles; `SemanticShift` for emulation.
- The scope litmus test (§11): "a thing with provider-varying wire dialects
  is a capability; a thing with no wire dialect is built ON ocai".

## 4. Verdicts

### 4.1 G-05: MCP client — a §11 capability with interface `mcp`, scoped narrowly

**Recommendation: yes, MCP client is a kernel capability — but a transport
and codec capability, not an execution engine.**

The litmus test is met on its face: MCP is a versioned wire protocol with
dated revisions (`2024-11-05` … `2026-07-28`), two transports, and a
breaking redesign already on record (stateless `2026-07-28` versus
session-based `2025-11-25`). That is exactly the "interface with dated tags"
shape the four-level identity exists for: `NodeId(provider="mcp",
interface="mcp", tag="2026-07-28", shape=("mcp", "tools.list.response"))`.
The kernel contribution is:

1. **Codec and shapes** — `mcp.tools.list`, `mcp.tools.call`,
   `mcp.resources.read`, `mcp.prompts.get` as IR shapes; `tools/list`
   results decode to the kernel `Tool` (`inputSchema` → `parameters`,
   `outputSchema` → `output`) with the JSON Schema 2020-12 default and
   total-decode tolerance for unknown fields; `tools/call` results decode to
   `PartToolResult`-compatible content (`text`, `image`, `audio`,
   `resource_link`, `resource`, `structuredContent`, `isError`).
2. **Migration edges between revisions** — `2025-11-25 → 2026-07-28` is a
   real conversion with real loss (session semantics, server-initiated
   requests → MRTR, `resources/subscribe` → `subscriptions/listen`) and
   belongs in the catalog with an `EdgeContract`, the same way
   `openai/chat_completions → openai/responses` does.
3. **Sans-io protocol state** — the request/response pairing, MRTR
   continuation (`requestState` echo), and `server/discover` caching are
   pure state machines; the drivers already own the physical I/O.
   Streamable HTTP rides `ocai.wire` (`HttpxTransport` + `SSEParser`);
   stdio needs a `ProcessTransport` twin — the one new wire piece.
4. **Authorization** — OAuth 2.1 token acquisition is a `Credential`
   satellite concern (identity page); the kernel applies the bearer at the
   leaf and honors the "no token passthrough" rule structurally.

What stays **out** of the kernel: the agent loop that decides to call a tool,
approval gates (`Decision` vocabulary reused by the agent runtime), tool
*execution* of local functions, registry lookup, and sampling (deprecated in
the spec anyway). Those are the agent-runtime and registry platform modules.

Why not a satellite: a satellite would re-implement total decode, dated
tags, and migration edges outside the conformance harness, and the first
protocol revision bump would land on users without a `FidelityReport`. The
cost of the capability route is one more interface in the catalog and a
`ProcessTransport`; it is the cheaper option over two revisions.

Promotion trigger to record: the capability is admitted when a second
*consumer* of the shapes exists (the agent runtime and the registry both
need `Tool` decoded from `tools/list`), which is already true on paper.

### 4.2 Provider-side MCP connectors — censused extension, with one first-class seed

Apply the three-lane law:

- **Not first-class today.** The request shapes are not congruent: OpenAI
  nests everything in one `mcp` tool with `require_approval`; Anthropic
  splits `mcp_servers` from an `mcp_toolset` tool entry; Gemini nests a
  transport object; Bedrock routes through a connector ARN. Approval
  semantics exist only on OpenAI (and Bedrock as `"never"`). The checklist
  (≥2–3 interfaces with congruent semantics after declared shifts) fails on
  the approval and auth fields.
- **Censused extension** (`spec/extensions/openai.responses.mcp.schema.json`,
  `anthropic.messages.mcp.schema.json`, `gemini.generate_content.mcp.schema.json`)
  for the full provider shape, on the request's `extensions`.
- **One congruent seed is first-class**: the *server reference* `(name, url,
  allowed_tools)` is present on all four and has the same meaning. Propose
  `ChatRequest.tools` accepting a `RemoteToolset(name, url, allowed_tools,
  auth: CredentialRef | None)` entry alongside `Tool`, with each edge
  emitting its native shape and declaring `EXTENSIONS`/`DROPPED` for
  `require_approval`, `defer_loading`, `headers`, `transport` options. The
  authorization token is never an IR field: it is a `CredentialRef`
  resolved at the driver leaf (rule 13), and crossing to a provider that
  cannot carry it is `UNSUPPORTED`-and-reported.
- **`provider_options`** for everything destination-only (`tunnel_id`,
  `connector_id`, Bedrock ARNs).
- Responses stay as they are: `PartServerToolCall(kind="mcp_call")` with the
  verbatim payload, plus `mcp_list_tools`/`mcp_tool_listing` items decoded
  as `PartServerToolResult` with kind `mcp_list_tools`; approval requests
  (`mcp_approval_request`) decode to `PartServerToolCall` with
  `status="input_required"`-class lifecycle so the agent runtime can answer
  them through its `Decision` gate.

### 4.3 Tool and skill registries are platform modules; the kernel supplies provenance

The registries (tools, skills, MCP servers) have no wire dialect and are
"typed, versioned registries" by the platform README. Kernel substrate they
need:

| Need | Proposal |
|---|---|
| Tool provenance | `Tool.origin: Origin \| None` — a small pure-data stamp `(source_kind ∈ local\|mcp\|openapi\|skill\|provider, source_id, version, content_hash)`; modeled on the existing `Origin`/`SourceRef` idea for parts. A registry stamps it; the ledger carries it; an audit answers "which server, which version, which schema hash did this call see" |
| Strict-schema divergence census | one `spec/extensions/` or `spec/schema/tool-schema-subsets.json` document listing per-interface supported keywords (the §2.4 table as data), consumed by edges to emit `DROPPED`/`APPROXIMATED` per keyword and by a registry to validate a tool against its target interfaces *before* a run |
| Tool annotations | `Tool.annotations: dict[str, Any]` censused (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint` from MCP) — needed by approval gates; keep it a censused bag until a second non-MCP source defines them |
| `Tool.strict` | first-class boolean: OpenAI and Anthropic both ship `strict`; Gemini `VALIDATED` mode is a congruent choice-level knob; passes the ≥2 test |
| Skill identity | `SKILL.md` frontmatter `(name, description, version?)` + `content_hash` as the registry key; the kernel adds nothing — skills are prompts plus files and have no wire dialect; the Anthropic Skills API `container.skills` is a Messages-level censused extension |
| Computer-use tools | provider-executed loops: `PartServerToolCall` kinds `computer_call` etc. with verbatim payload; the browser providers are agent-runtime tools, not kernel |

## 5. Priority and sequencing

| Item | Priority | Depends on |
|---|---|---|
| `Tool.strict` first-class + strict-subset census as data + edges emitting per-keyword losses | **P1** (every tool call through the facade is exposed to silent subset loss today) | — |
| `Tool.origin` provenance stamp + `Tool.annotations` censused | P1 (registry prerequisite) | — |
| `RemoteToolset` seed + per-provider MCP connector extensions; `mcp_approval_request` decode | P2 (lands with H1 `/responses` and the Anthropic connector beta) | H1 |
| MCP client capability: `mcp` interface at `2026-07-28` (tools/list, tools/call, resources/read, prompts/get), Streamable HTTP over `ocai.wire`, `ProcessTransport` for stdio, conformance fixtures from the spec's examples | P2 (first non-chat capability; also the §11 recipe's first real exercise) | wire `ProcessTransport`; a `Credential` satellite for OAuth 2.1 |
| `2025-11-25 → 2026-07-28` migration edge with `EdgeContract` | P3 | MCP capability |
| Registry modules (tools, skills, MCP servers) with `server.json` import from the MCP registry | platform, after the kernel substrate | `Tool.origin` |

## 6. Open questions and unverified items

- OpenAI Chat Completions nested function-tool shape was confirmed only via
  AWS's OpenAI-SDK page (OpenAI reference pages returned 404 on the read
  date); OpenAI `headers` on the `mcp` tool is *unverified*.
- Gemini SDK client-side `ClientSession`-as-tool pattern and Vertex MCP
  support are *unverified*; `parametersJsonSchema` keyword coverage is
  *unverified*.
- Agent Skills adopter list and the LangChain OpenAPI toolkit are
  *unverified*.
- Whether `RemoteToolset` belongs in `ChatRequest.tools` or a sibling
  `ChatRequest.toolsets` field is a freeze-review decision; the former keeps
  one list the model sees, the latter keeps `Tool` pure.
- Stdio servers execute code on the host; the admission posture WU-20 took
  for plugins ("entry-point loading executes Python; admission is not
  publisher authentication") applies verbatim and should be written into the
  registry's README.

## Sources

- https://modelcontextprotocol.io/specification/latest (read 2026-11-10)
- https://modelcontextprotocol.io/specification/latest/changelog (read 2026-11-10)
- https://modelcontextprotocol.io/specification/versioning (read 2026-11-10)
- https://modelcontextprotocol.io/specification/2026-07-28/basic (read 2026-11-10)
- https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http (read 2026-11-10)
- https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio (read 2026-11-10)
- https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr (read 2026-11-10)
- https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization (read 2026-11-10)
- https://modelcontextprotocol.io/specification/2026-07-28/server/discover (read 2026-11-10)
- https://modelcontextprotocol.io/specification/2026-07-28/server/tools (read 2026-11-10)
- https://modelcontextprotocol.io/specification/2026-07-28/server/resources (read 2026-11-10)
- https://modelcontextprotocol.io/specification/2026-07-28/server/prompts (read 2026-11-10)
- https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation (read 2026-11-10)
- https://modelcontextprotocol.io/specification/2025-11-25/changelog (read 2026-11-10)
- https://modelcontextprotocol.io/specification/2025-06-18/basic/transports (read 2026-11-10)
- https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle (read 2026-11-10)
- https://modelcontextprotocol.io/extensions/overview (read 2026-11-10)
- https://modelcontextprotocol.io/registry (read 2026-11-10)
- https://modelcontextprotocol.io/community/governance (read 2026-11-10)
- https://modelcontextprotocol.io/docs/sdk (read 2026-11-10)
- https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/official-registry-api.md (read 2026-11-10)
- https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/generic-server-json.md (read 2026-11-10)
- https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json (read 2026-11-10)
- https://blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation/ (read 2026-11-10)
- https://developers.openai.com/api/docs/guides/tools-connectors-mcp (read 2026-11-10)
- https://developers.openai.com/api/docs/guides/function-calling (read 2026-11-10)
- https://developers.openai.com/api/docs/guides/structured-outputs (read 2026-11-10)
- https://developers.openai.com/api/docs/guides/tools-computer-use (read 2026-11-10)
- https://developers.openai.com/api/docs/actions/getting-started (read 2026-11-10)
- https://platform.claude.com/docs/en/agents-and-tools/mcp-connector (read 2026-11-10)
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview (read 2026-11-10)
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools (read 2026-11-10)
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-reference (read 2026-11-10)
- https://platform.claude.com/docs/en/build-with-claude/structured-outputs (read 2026-11-10)
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool (read 2026-11-10)
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview (read 2026-11-10)
- https://platform.claude.com/docs/en/build-with-claude/skills-guide (read 2026-11-10)
- https://aistudio.google.com/docs/function-calling (read 2026-11-10)
- https://aistudio.google.com/docs/api-reference/generate-content (read 2026-11-10)
- https://aistudio.google.com/api-reference/agents (read 2026-11-10)
- https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use-client-side.html (read 2026-11-10)
- https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use-server-side.html (read 2026-11-10)
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html (read 2026-11-10)
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-MCPservers.html (read 2026-11-10)
- https://agentskills.io/specification (read 2026-11-10)
- https://code.claude.com/docs/en/mcp (read 2026-11-10)
- https://code.claude.com/docs/en/agent-sdk/skills (read 2026-11-10)
- https://gofastmcp.com/integrations/openapi (read 2026-11-10)
- https://docs.stagehand.dev/ (read 2026-11-10)
- https://docs.browser-use.com/ (read 2026-11-10)
- https://github.com/browserbase/mcp-server-browserbase (read 2026-11-10)
- https://github.com/microsoft/playwright-mcp (read 2026-11-10)
