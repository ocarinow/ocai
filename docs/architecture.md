# ocai architecture

This document is the **structural contract** of the repository: the layers, every
load-bearing object, what each is for, and how they interact. Code is the
implementation of this document; when they disagree, fix one *in the same PR*.
The design was settled in July 2026 (multi-agent design review); the rationale
for each decision is summarized inline.

Status legend: **[frozen-candidate]** freezes additive-only at the next
release gate ([ADR 0005](decisions/0005-revised-freeze-gate.md)) ·
**[provisional]** may still change until exercised · **[stub]** structure only,
implementation pending.

**November 2026 update:** M1–M3 implement Python chat and streaming for OpenAI
Chat Completions and Anthropic Messages. The active IR remains `2026-07`.
[ADR 0005](decisions/0005-revised-freeze-gate.md) replaces the original freeze
assumption: ordered interaction items, replay, and independent plugins must be
exercised before the next contracts freeze, as sequenced in the
[core modernization plan](plans/core-modernization.md). Draft schemas under
`spec/proposals/` are not runtime support or registered graph nodes.
See the [feature matrix](provider-feature-matrix.md) for implementation gaps.

---

## 0. The one-paragraph model

Everything a user, plugin author, or auditor touches is a **frozen,
zero-dependency data contract** (`ocai.core` + the capability packages);
everything else is replaceable machinery behind it. Machinery splits along the
three things that change at different speeds: **meaning** (`ocai.convert` — the
conversion catalog), **movement** (`ocai.runtime` + `ocai.wire` — sans-io
drivers and the HTTP stack), and **policy** (hook protocols that enterprises
fill in). Providers publish **interfaces** (wire protocols), not just models;
the canonical IR is itself the interface named `ocai`; and every boundary
crossing pays its toll in a **FidelityReport** — visibly, never silently.

## 1. Layer map and dependency arrows

One distribution (`ocai`) with PEP 420 namespace packages. Layering is
enforced by import-linter in CI — an import against the arrows is a build
failure.

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ocai.core        CONTRACT LAYER — pure stdlib, zero deps, zero I/O         │
│                  identity · fidelity · errors · result · usage · finish ·  │
│                  credentials · refs · profile · ir · canonjson ·           │
│                  jsonschema · sources                                      │
├────────────────────────────────────────────────────────────────────────────┤
│ ocai.chat / ocai.embedding / ocai.vectorstore    CAPABILITY CONTRACTS      │
│                  port Protocol + canonical IR types    (→ core only)       │
├────────────────────────────────────────────────────────────────────────────┤
│ ocai.convert     MEANING — Catalog, planner, EdgeContract, transducers,    │
│                  conformance harness                    (→ core)           │
├────────────────────────────────────────────────────────────────────────────┤
│ ocai.runtime     MOVEMENT — SyncDriver/AsyncDriver, Decision hooks,        │
│                  CallInterceptor, Binding               (→ core, convert)  │
├────────────────────────────────────────────────────────────────────────────┤
│ ocai.wire        REMOTE TRANSPORT — HttpRequest/Response, SSE, transports, │
│                  hosts, wire policies    (→ runtime; httpx via extra)      │
└────────────────────────────────────────────────────────────────────────────┘
   ocai.chat.facade (the wire-backed facade) is the ONE chat module allowed to
   import convert/runtime/wire — the port and types never do. Convention: a
   facade module never shares the front-door factory's name, so the future
   ocai.chat.model() factory (§3.4) is never shadowed by a module.

 Plugin dists (ocai-openai, ocai-anthropic, …): one subpackage PER INTERFACE
 (ocai.openai.chat_completions, ocai.openai.responses). Depend on core+convert
 ONLY — never on wire/httpx, so an offline audit tool can re-convert archived
 traffic without the ability to make network calls.

 Local adapters (future ocai-faiss, ocai-llamacpp): implement a capability port
 directly, depend on core only. Local and remote are peers at the port plane.

 Enterprise satellites (future ocai-otel, ocai-archive-*, ocai-vault-*):
 implement core/runtime hook protocols. The kernel never grows an opinion.
```

The driver-to-wire exception remains narrow and deferred: HTTP/transport values
and, in WU-39, the optional host framing selector. The import-linter exception
names `runtime.drivers → wire.hosting`; plugins still cannot import wire.

## 2. `ocai.core` — the contract layer

Nothing in this package performs I/O, imports a third-party module, or knows
HTTP exists. It is the surface a bank audits once and the shapes the future
TS/Go ports mirror from `spec/`.

### 2.1 `identity.py` — who is speaking [frozen-candidate]

Four-level identity. Each level owns exactly one kind of change:

| Object | Purpose |
|---|---|
| `Capability` | The semantic job a user programs against: `"chat"`, `"embedding"`, `"vectorstore"`. One canonical IR + one port per capability. |
| `Shape` | A message schema role within a capability: `"chat.request"`, `"chat.response"`, `"chat.chunk"`. Graphs never mix shapes. |
| `NodeId` | **The graph node**: `(provider, interface, tag, shape, released, status)`. `interface` is the coordinate the old `SchemaVersion` was missing — `openai/chat_completions` and `openai/responses` are *concurrent sibling interfaces* of one capability, not versions of each other. `tag` is an opaque dated revision (never parsed; ordered by `released`). `status` ∈ `STABLE/PREVIEW/DEPRECATED/RETIRED` drives resolution. |
| `Origin` | Provenance stamp `(distribution, version)` carried by every node/edge a plugin registers; surfaces in reports and audit records. |

The canonical IR is **just another interface**, named `ocai`, with dated
revisions (`ocai@2026-07`). IR migration therefore *is* graph conversion
(§4.4) — no special case.

### 2.2 `fidelity.py` — what conversion cost [frozen-candidate]

| Object | Purpose |
|---|---|
| `Disposition` | Per-field outcome vocabulary: `EXACT, RENAMED, APPROXIMATED, EMULATED, EXTENSIONS, DROPPED, UNSUPPORTED`. |
| `FieldLoss` | One field-level record: path, disposition, severity, note. |
| `SemanticShift` | A *semantics*-level record distinct from field mapping: structural relocation (system role → `systemInstruction`), emulation (transcript replay), id regeneration, range pass-through. Field loss and semantic divergence are different kinds of honesty; conflating them understates what a migration cost. |
| `EdgeReport` | Losses + shifts for one edge traversal. |
| `FidelityReport` | The accumulated per-edge account for a whole conversion path; `lossless` is derived, never asserted. |
| `Route` | What ocai *decided*: capability, chosen `NodeId` (interface + tag), requested pin, resolution reason, catalog hash. The audit joint: a `Route` plus a catalog lockfile reconstructs exactly which conversion logic served a call. |

### 2.3 `result.py` — what every port returns [frozen-candidate]

```python
@dataclass(frozen=True, slots=True)
class CallResult(Generic[T]):
    value: T                        # ChatResponse, list[Embedding], ...
    route: Route | None             # None for local in-process adapters
    report: FidelityReport | None   # THE report home. Payloads stay pure.
    usage: Usage | None
    raw: Any | None                 # untouched provider body (never credentials)
```

Uniform on **every** port, local or remote — this is what makes governance,
cost, tracing, and fallback compose identically over FAISS and OpenAI, and it
structurally fixes the old embedding/vectorstore ports that had no channel for
usage or reports. The report lives **here and only here** (`ChatResponse` has
no `report` field; one home, not two).

`CallContext(tenant, principal, compartment, classification, deadline, tags,
call_id, parent_id, correlation_id)` is the
per-request governance carrier, threaded through ports as an optional keyword
— a policy like "PII-classified traffic may not go to provider X" needs the
classification *at call time*; without a sanctioned carrier, enterprises
smuggle it through bags.

The facade snapshots caller context and passes it to drivers; policies read
`HttpRequest.ctx` and `Outcome.ctx`. Trusted identity facts are established by
platform code, not authenticated by core. Context never enters provider bodies or
headers. `request.attempt` counts physical attempts (zero-based); `admission`
counts policy deferrals independently.

Aware deadlines become one monotonic budget before preparation. Admission,
retry waits, credential application and all physical attempts share it; an
impossible wait fails immediately. Drivers pass remaining timeout to transports,
reject late output, and cancel pending async operations. Sync transports must
honor timeout cooperatively: arbitrary blocking custom code cannot be forcibly
preempted. HTTPX timeouts bound I/O phases, not total execution; driver checks
reject output arriving after the whole-call deadline. Consumer pauses consume
the streaming budget. Local adapters remain responsible for their execution
budget; context transport does not claim automatic interruption of local code.

### 2.4 `refs.py` — provider-anchored state [frozen-candidate]

`ProviderRef(provider, interface, kind, id, replay, scope, qualifier)` names
state that lives on a provider's side: `previous_response_id`, file handles,
thought signatures, audio ids. The structural rule the graph enforces is
**scoped** by `scope` (open code, constants on `RefScope`):
**interface-scoped** refs (the default) are `UNSUPPORTED` crossing any other
`(provider, interface)` — reported, never silently dropped;
**provider-scoped** refs survive same-provider sibling-interface crossings
unreported (an OpenAI file id is valid across
`chat_completions`/`responses`/`batch`) and are `UNSUPPORTED` across
providers; **model-scoped** refs are additionally *breakage* when the bound
resource changes (Gemini `cachedContents`), with `qualifier` naming the bound
resource. `replay ∈ {OPTIONAL, REQUIRED}`: REQUIRED anchors (Gemini
`thoughtSignature`, Anthropic thinking signatures) are weighted as *breakage*
in planning, not mere loss — dropping them produces a 400, not degraded output.

### 2.5 `profile.py` — declared capability facts [provisional]

`CapabilityProfile` maps feature keys → `Support.NATIVE | EMULATED | ABSENT`,
keyed `(provider, interface, model_pattern)` — the model dimension is required
because support varies below interface level (Anthropic's newest models reject
`temperature`). Consulted by the feature gate *before* payload conversion:
strict mode refuses with a typed error; annotate mode records the loss.
Feature keys are namespaced open data, not a frozen taxonomy.
Hosts may supply an optional `profile_key(resource)` lookup alias (§6). The gate
and public inspection use the same key; codecs still bind the original resource.
Aliases do not establish qualification: undeclared feature coverage remains
unknown in inspection.

### 2.6 `ir.py` — the IR envelope and total decode [frozen-candidate]

| Object | Purpose |
|---|---|
| `IRObject` | Base for all IR dataclasses: `version` (canonical revision), `provider_options` (destination-scoped passthrough, §3.4), `extensions` (namespaced bag for unmapped-but-preserved data). **Omit-absent** `to_dict` (absent/None fields are not emitted — this is what makes "additive" real: adding an optional field never invalidates a fixture). **Tolerant** `from_dict` (unknown keys sweep into `extensions`, never raise). |
| `TagRegistry` | Open registration for tagged unions (parts, deltas, details). Decoding an unknown tag returns the registered *Unknown* fallback — **no decode path in the IR may ever raise on unknown input.** Plugin tags must be namespaced (`anthropic.mid_conv_system`); bare tags are reserved for core. |

Precedence rule (normative): unknown *envelope keys* sweep to `extensions`;
unknown *content tags* fall back to the Unknown type; a decoder never applies
both to the same bytes. Malformed citation offsets are retained as registered
`ocai.annotation_invalid_span` evidence, not coerced into positions. Standalone
`Span` decode retains malformed input under `ocai.invalid_span`; such a span
never passes contextual validation.

### 2.7 `canonjson.py` — the equality predicate [frozen-candidate]

Every conformance guarantee in this repo (fold fixtures, round-trips, the
drift alarm) depends on "semantic equality over canonical JSON" — so it is
defined **once, normatively**, here and in `spec/canonical-json.md`: key
ordering, number forms, unicode normalization, absent-vs-null, and the
parse-compare/preserve-verbatim rule for embedded JSON strings (`args_json`).
`canonical(obj) -> str` and `semantic_equal(a, b) -> bool`. TS/Go ports
implement the same spec; they cannot each invent their own. Citation offsets are
validated on the exact decoded text before any equality normalization. A
canonically equivalent Unicode string does not prove offset equivalence.

### 2.8 `usage.py` / `finish.py` — the cross-capability outcome vocabulary [frozen-candidate]

Hoisted from `ocai.chat` pre-freeze (the capability stress-test): the
dimensional `Consumption`/`Usage` model and `FinishInfo` with its detail
union describe what *any* capability's call consumed and why it stopped —
chat tokens, image generation seconds, vector-store read-units, an async
job's terminal state — so `CallResult.usage` is typed `Usage | None` in core
and every capability reports through the one vocabulary.
`ocai.chat.types.usage` / `ocai.chat.types.finish` remain as pure re-export
shims; their schemas (`usage.schema.json`, `finish.schema.json`) are **core
contracts**, capability-neutral, not chat-local. Deliberately NOT hoisted:
`Document`/`Vector` stay in `ocai.embedding` while it is provisional — the
first rerank/vectorstore implementation will force a hoist-or-duplicate
decision on them while both packages are still provisional, decided then
with real usage in hand.

### 2.9 `traits.py` and survivors

`DialectTraits` lives in the **contract layer**, not in `ocai.wire`: plugin
interface subpackages declare data; wire hosts consume it. WU-37 adds
`version_headers`, `feature_headers`, `host_body_versions` and
`host_feature_body_mappings` alongside the unchanged legacy constructor fields.
`HeaderBodyMapping(header, field, separator)` declares scalar preservation or
explicit list splitting; declaring a mapping never enables a feature.
`request_headers()` merges explicit groups over legacy headers case-insensitively;
`body_fields(host)` resolves that host's version and declared feature values.
An absent host entry falls back to `cloud_body_version`; explicit `None` disables
that fallback. Header role collisions, duplicate mapping sources/destinations and
version/feature body collisions fail at construction. Maps are copied on input;
returned headers/body values are detached. These declarations contain no secrets.
WU-38 composes non-secret headers in order: dialect, host, then binding, with
case-insensitive replacement; conflicting case aliases within one group fail.
Host-specific body relocation still resolves trait declarations, not later binding
overrides; concrete cloud hosts must qualify their relocation separately.
Plus the survivors: `errors.py` (the taxonomy — unchanged),
`credentials.py` (`Credential` protocol + `ApiKey`, explicit-only, redacted,
and additive `NoCredential()` for intentionally unauthenticated endpoints;
*application* stays at the driver leaf, §5), `jsonschema.py`,
`sources.py` (gains `SourceRef(ProviderRef)` for provider file handles),
`primitives.py`.

## 3. `ocai.chat` — the chat capability contract

Depends on `ocai.core` only (except `facade.py`, the designated facade).

### 3.1 `types/` — the canonical chat IR [frozen-candidate unless noted]

**`Message(role, parts: list[Part])`** — parts-only storage; the old
`Content = str | Part | list[Part]` union is gone. Strings are constructor
sugar normalized in `__post_init__`; `message.text` is a derived view. `Role`
is an open code with canonical constants `user|model|system|tool`, normalized
exactly once at the codec boundary; unknown roles are preserved verbatim.

**Part taxonomy** (`types/parts.py`; tagged union on `type`, open
`TagRegistry`). Every part carries `id: str | None` (stable identity — the
lesson of OpenAI's item model) and `anchor: ProviderRef | None`:

| Part | Purpose / key fields |
|---|---|
| `PartText` | `text`, `annotations: list[Annotation]` — citations are span-anchored here. Gemini grounding is re-anchored **only** when offsets validate against decoded text; otherwise it rides a censused extension. Never emit a possibly-misattributed span. |
| `PartImage/Audio/Video/Document` | Media family over the `Source` union (`base64 | url | SourceRef`). Video metadata (Gemini) and document title/context (Anthropic) are per-part optionals, ABSENT-reported elsewhere. |
| `PartReasoning` | ONE merged shape: `text`, `summary`, `signature: ProviderRef?`, `opaque: ProviderRef?` — a `/responses` reasoning item (summary + encrypted_content) is one part, never two correlated ones. Replay rules per §2.4. |
| `PartToolCall` | `call_id`, `name`, `args_json: str` (**the authoritative wire truth** — all interfaces stream string fragments), `args()` parse-on-read, `status` (open lifecycle code shared with streaming: `input_streaming → input_complete → executing → output_available | output_error`), `executed_by: client|provider`. |
| `PartToolResult` | Sibling of the call, correlated by `call_id`, never nested: `parts: list[Part]` (text/image/document nest), `is_error`. Cross-provider conversion regenerates call ids — recorded as `SemanticShift`, never silent. |
| `PartServerToolCall/Result` | Typed spine over built-in tools: open `kind` (`web_search`, `code_execution`, `mcp_call`, …), `call_id`, `status`, **verbatim byte-faithful `payload`**. Visible and reportable without freezing the industry's fastest-moving surface. |
| `PartRefusal` | Refusal text; pairs with `finish.reason == "refusal"`. |
| `PartOpaque` | *Deliberate* provider-unique content, census-registered (§7). |
| `PartUnknown` | *Future* canonical tags (decoder fallback) — strictly distinct from `PartOpaque`; upgradeable later via IR self-migration edges. |

**`types/annotations.py`** — `Annotation.kind` is an optional open string
(`url_citation` is canonical). `SourceResultRef(call_id, pointer)` names a local
server-tool result and JSON Pointer; it is never fetched implicitly and grants
no provider replay authority. Existing `url`, `document_index`, `file`, `title`,
`cited_text`, `opaque` and untagged annotation forms remain valid. Native metadata
uses registered extensions; malformed source references retain their original
value under `ocai.annotation_unparsed_source`.

`Span.valid_for(text, attributed_text=...)` checks integer code-point bounds
against the exact final decoded text. It does not guess byte/UTF-16 units,
normalize Unicode, or compare source quotation (`cited_text`) with output.
`Annotation.validated` returns detached data; an invalid span becomes
unpositioned with its verbatim evidence retained. `ChatResponse.from_dict` and
`validated_annotations()` apply this to final text. Accumulation validates at
part sealing/finalization, allowing citations to precede text deltas. Consumers
must treat delta positions as provisional until final text is available.
These canonical checks alone do not qualify any provider's offset convention
(ADR 0008).

**`types/tools.py`** — `ChatRequest.tools` accepts `ToolDefinition`, the union
of legacy untagged function `Tool`, `ServerTool(type="server", kind, allowed_domains,
blocked_domains, user_location)`, and preserving `ToolUnknown`. The common server
kind is open; unknown tags and non-object entries never become function tools.
`ServerToolLocation` carries approximate country/region/city/timezone data. Explicit
empty domain lists remain explicit intent; codecs qualify their semantics rather
than inferring a policy. Unparsed locations retain registered extension evidence.
No tool definition executes code, fetches a URL, or implies an MCP registry.

**`types/config.py` — `ChatConfig`, shipped FULL** (the empty-scaffold failure
is over). First-class by the three-lane law (§3.4): `temperature`, `top_p`,
`max_output_tokens`, `stop_sequences`, `seed`, `frequency_penalty`,
`presence_penalty`, `parallel_tool_calls`, profile-gated `top_k` and
`logprobs`, `modalities` + `audio: AudioOutputConfig` [provisional],
`reasoning: ReasoningConfig(effort, budget_tokens, include_thoughts)`,
`output: OutputFormat(mode: text|json|json_schema, name, schema, strict)`,
`cache: CacheConfig` [provisional] (+ per-part `cache_hint`). Out-of-range
values pass **verbatim with an APPROXIMATED report — never rescaled, never
clamped, never silent.**

**`types/finish.py`** — re-export shim; the vocabulary is core-owned (§2.8):
`FinishInfo(reason, native, detail)`: canonical open
code (`complete | max_tokens | stop_sequence | tool_call | content_filter |
refusal | recitation | paused | malformed | error | …`), `native` verbatim
provider value, `detail` a tagged union (`SafetyDetail(ratings, block_source)`,
`RefusalDetail(category, explanation)`, `IncompleteDetail`, `ErrorDetail`,
`DetailOpaque`). Unknown wire values decode to `reason="unknown"` with the
native lane preserved — enum growth is structurally crash-proof. Boundary
rule: mid-generation refusal is a *response*; pre-generation block (Gemini
`promptFeedback`) is a `ContentFilterError`.

**`types/usage.py`** — re-export shim; the vocabulary is core-owned (§2.8):
the dimensional `Consumption` model survives (it
generalizes across capabilities) with open-string dimensions, a
`cached`/`reasoning` source, a reserved `currency` unit for gateway-reported
cost (first-party cost stays middleware's job — stance on record), a
documented disjoint-bucket normalization rule per provider, and ergonomic
accessors (`usage.input_tokens`, …).

**`types/request.py` / `types/response.py`** —
`ChatRequest(messages, tools, tool_choice, config)` and
`ChatResponse(message, finish, usage, info, raw)`. **No `model` field on the
request**: the model name is provider-specific routing data, bound to the
model object at construction (§3.4) and injected into the wire payload by the
codec from `EndpointSpec.resource` at encode time (Vertex even carries it in
the URL). A `ChatRequest` is pure, portable conversation content. Response is
a *pure graph payload* — no report field (that's `CallResult`'s). In revision `2026-07`, one message:
`n` fails admission; decoded `choices[1:]` land in a censused extension with
reported loss. `ResponseInfo` carries id/model echo as `ProviderRef` anchors
(reusable as `previous_response_id`).

**`types/stream.py`** — `ChatChunk(type, seq, index, part, delta, usage,
finish, error, end, raw_event)`; `ChunkType` keeps the existing wire values +
terminal `streamStop` carrying **`StreamEnd(usage, finish, report)`** — the
authoritative usage/finish and the stream's FidelityReport. Typed `Delta`
union mirrors the part algebra (`DeltaText`, `DeltaToolArgs(fragment: str —
raw string, parsed once at PART_STOP)`, `DeltaReasoning`, `DeltaSignature`,
`DeltaAnnotation`, `DeltaRefusal`, `DeltaBlob`, `DeltaUnknown`).
`StreamAccumulator.fold(chunks) -> ChatResponse` is **normative law**:
`complete(request) == fold(stream(request))`, PART_STOP's final part MUST
equal the delta accumulation, aborted streams seal parts `incomplete`, and
**no new part type is admissible without its delta type, fold law, and paired
chunks/response fixtures in the same change** (the streaming-first ratchet).
`StreamEnd` stays per-capability (terminal envelopes are duck-typed on
`.usage`/`.finish`/`.report`; a premature generic `StreamEnd` would drag chat
chunk semantics into core).

### 3.2 `protocol.py` — the port

```python
class ChatModel(Protocol):
    def chat(self, request: ChatRequest, *, ctx: CallContext | None = None) -> CallResult[ChatResponse]: ...
    async def achat(...) -> CallResult[ChatResponse]: ...
    def stream(...) -> ChatStream: ...        # iterable of ChatChunk; .end after
    async def astream(...) -> AsyncChatStream: ...
```

Bare name = sync, `a`-prefix = async (repo-wide convention). The port is the
**only** contract; "wire-backed" is one implementation. In-process adapters
implement it directly and return the same `CallResult` (with
`route.host = "in-process"`).

### 3.3 `facade.py` — the wire-backed facade

`WireChatModel(codec, binding, catalog, model_name=...)` — the composition of
a dialect codec, a `Binding` (§5), and a `Catalog` (§4) behind the port, plus
the bound model name (§3.4 — the front doors pass it at construction; it
becomes `EndpointSpec.resource`, never a request field). The one chat module
that imports convert/runtime/wire. Encode via graph → inject the bound model
via the codec's `bind_resource` (edges stay model-agnostic; only the codec
knows where its wire carries the name) → driver executes → decode via graph →
assemble `CallResult`. Host profile aliases affect capability lookup only; the
configuration fingerprint includes the effective profile key as well as approved
wire fields, so changing an alias cannot silently reuse a prepared approval.
For streaming, preparation also pins a `StreamFraming` selection (§6); both the
live selection and its factory/options identity must still match before I/O.
Copying preparation copies configuration while preserving callable ownership.
No decoder is created during inspection or for an unconsumed stream.

### 3.4 The front doors — simple facade, switchable by data

The user-facing API is simple, pydantic-ai-shaped: build a model object once
(the provider-specific **model name is bound HERE, never carried in the
request**), then call it with pure conversation payloads.

```python
import ocai.chat
from ocai.core import ApiKey
from ocai.chat.types import ChatRequest, Message

chat = ocai.chat.model("openai/gpt-5", credentials=ApiKey.from_env("OPENAI_API_KEY"))
res = chat.chat(ChatRequest(messages=[Message.user("hello")]))
```

Two equivalent doors, neither forced:

1. **The core string door** — `ocai.chat.model(spec, *, credentials,
   host=None, catalog=None, transport=None, interceptors=())` where `spec` is
   the single string `"<provider>/<resource>"` (the LiteLLM/OpenRouter
   convention). Normative parse rule: **split on the FIRST slash only** — the
   resource may itself contain slashes (HuggingFace ids on vLLM hosts:
   `"openai/meta-llama/Llama-3.3-70B"`). The spec never carries an interface
   (pinning is an explicit kwarg), and internals keep provider and resource
   as separate typed coordinates — the string is front-door sugar, not a
   wire format. The factory resolves the provider against the discovered
   default catalog (or an explicit one), builds the codec from the fragment's
   registered component factory, composes the `Binding` internally (`Direct`
   host from the fragment's first-party endpoint data unless a host is
   passed). `host="name"` explicitly selects a `HostDescriptor` from that catalog
   and composes a `Custom` wire host. It never auto-selects a host or switches a
   conversion interface. The whole provider+model choice is ONE config value:
   `ocai.chat.model(os.environ["OCAI_MODEL"], ...)` — switching providers is
   a deployment change, zero code.
2. **The plugin helper** — a provider package MAY ship convenience sugar
   (`from ocai.openai import chat_model; chat_model("gpt-5",
   credentials=key)`). It must be a thin wrapper over the exact same
   fragment + facade machinery — sugar, never a separate code path.

Either way, installing a provider distribution has exactly one structural
effect: its `CatalogFragment` becomes discoverable and **augments the
conversion graph**. There is no framework container above the doors:
multi-tenant setups are plain Python (several models built with different
credentials/catalogs).

### 3.5 The three-lane knob law (normative)

1. **First-class typed field** — admitted by mechanical checklist: ≥2–3
   interfaces, congruent semantics after declared SemanticShifts, durable, an
   EdgeContract disposition definable for every dialect. *Exclusions are
   recorded* with pre-registered promotion triggers.
2. **Censused extension** — provider-unique but *schema-registered* in
   `spec/extensions/*.schema.json`; an unregistered key is a CI failure. The
   bags can never silently become the real schema.
3. **`provider_options` namespaced by destination** `("openai.chat_completions")`
   — a codec expands only its own namespace; foreign namespaces are never
   forwarded (kills cross-dialect leakage under a "lossless" report).

Citation kind and local result reference are first-class fields; provider-native
search controls and citation metadata remain censused extensions or scoped
options. Invalid position evidence is preserved in registered canonical
extensions rather than represented as a valid attribution. Server-tool kinds,
domain intent and approximate location are first-class; provider max-uses,
context-size and dynamic-search controls stay in registered/scoped lanes.

### Stream ownership and incomplete execution (WU-24)

`ChatStream.close()` / `AsyncChatStream.aclose()` and their context managers
own the upstream iterator. Exhaustion, early exit, consumer exceptions and async
cancellation close the facade, driver and transport chain. One owner consumes a
stream; to interrupt an active async consumer, cancel its task and await cleanup.
An unconsumed stream performs no provider I/O and becomes `closed` when explicitly
closed. Garbage collection is not a finalization or audit guarantee.

`.outcome: StreamOutcome` is separate from canonical `.end: StreamEnd` and records
`completed|closed|cancelled|failed|incomplete` exactly once. Missing usage remains
None. Available usage and flushed request/decode findings survive aborts without
buffering response content. Provider in-band ERROR chunks remain visible and
finalize as failed; EOF without a terminal is `StreamProtocolError`. Duplicate or
post-terminal content is malformed. No successful terminal is synthesized.
`on_termination` callbacks are passive and exception-isolated; enforceable policy
and required audit cannot be implemented by throwing from those callbacks.

## 4. `ocai.convert` — meaning

### Current fidelity and admission guarantees

Converters emit field records and semantic shifts; the graph aggregates them.
`lossless` is derived from emitted dispositions. It does not independently
detect unreported loss, and semantic shifts alone do not flip the flag.
Conformance tests compare independent expected outputs/records and check
declared bounds over fixture inputs. Catalog loading does not require a
certificate or prove correctness on arbitrary payloads. Reports are sparse,
not exhaustive field lineage; diagnostic cost is not a fidelity percentage.

Planning uses static declared grades, not the actual payload. Admission checks
endpoints against interfaces the fragment itself publishes: ownership is
self-declared, not authenticated. Python entry-point loading executes plugin
code. Catalog lock hashes describe declared metadata, not executable artifact
checksums. Applications needing controlled composition should pass explicit
catalogs; the default catalog discovers installed entry points once.

### Public execution inspection (WU-27)

`model.prepare(request, streaming=False)` returns a `PreparedChatCall` with
copied `.request` and `.inspection` views and `chat/achat/stream/astream` execution
faces. Preparation performs conversion and host shaping without authentication or
provider I/O. Execution uses the detached original snapshot, retains the same
port middleware and observers, and validates every physical attempt before auth.
Canonical mutations by admission middleware, approved body/URL/header changes,
or effective host/catalog/configuration changes raise `StalePreparationError`.
Explicit wire policies may add transport metadata headers, but cannot replace
approved fields. Credentials are deliberately excluded and may rotate per attempt.
Handles are in-process execution objects, not portable authorization tokens.

`Catalog.inspect` plans without executing converters or building transducers.
Inspection separates selected edge declarations, payload-specific request findings,
matched capability profiles, and packaged conformance resource pointers. Unknown
feature coverage is None; recognized keys do not exhaust the open feature universe
(`coverage_complete=False`). The legacy permissive gate remains compatible, but
its undeclared-means-native fallback is never proof of qualification. Inspection
never claims conformance was run (`conformance_evaluated=False`). Catalog/config
hashes identify declarations/effective configuration, not executable artifacts.
Response findings remain unknown until conversion occurs. ADR 0007 records why
public detached preparation replaces gateway dependence on private `_prepare`.

`FidelityPolicy` accepts explicit disposition/shift denials and pure predicates
on detached `FieldLoss` and `SemanticShift` records. It never treats `lossless`
as semantic acceptance. Prepared execution rechecks request policy before every
physical attempt; a rejection or raising predicate prevents I/O. Changing policy
identity invalidates preparation. Closures remain trusted application code.

Response policy runs after the conversion ledger is complete. A
`FidelityPolicyError` retains report, usage, route and phase without the rejected
payload/raw body. Streaming checks the completed ledger before delivering
`StreamEnd`; previous chunks cannot be retracted. A late rejection raises with
`partial` and `delivered_events`, and stream outcome retains available accounting
with failed status and no successful end. Aborts retain evidence under the
separate stream outcome contract; they never synthesize policy approval. Gateway
policies may independently enforce the ingress and client-egress leg reports.

### 4.1 `graph.py` [frozen-candidate mechanics]
The Dijkstra planner survives. `Edge(src: NodeId, dst: NodeId, fn, contract,
origin)`; planner cost is **derived** from the contract (§4.2), never
author-declared. `Converted(value, report)` named result. `StreamEdge` is a
*transducer factory* (`feed(event) -> events; flush() -> (events, EdgeReport)`)
so chunk-shape edges are planned by the same machinery — streaming conversion
joins the graph instead of bypassing it.

One graph admits one shape. Identical directed-edge registrations are idempotent;
competing functions/factories, contracts, origins, or notes on a directed pair
are rejected. A four-coordinate node cannot carry contradictory release/status
metadata. Unary and streaming planners break equal-grade ties by destination
coordinates, independently of registration order.

### 4.2 `contract.py` — EdgeContract

Request edges declare `tools[]` coverage independently from legacy function tools.
An unqualified server/unknown entry emits an `UNSUPPORTED` finding at its original
index, covering the whole intent. The prepared request retains the original data;
reports do not embed payloads. Fidelity policy can reject the finding before any
unary or streaming I/O; permissive execution omits the unsupported wire entry.

An edge's declared per-field disposition census. Core derives the planner
weight as a lexicographic `LossGrade` (unsupported+dropped, approximated,
emulated, hops) — impossible to game with a magic float. The conformance
harness certifies at build time that an edge's *runtime* `FieldLoss` never
exceeds its declaration: **an edge claiming lossless that drops a field cannot
ship.**

### 4.3 `catalog.py` — scoped, governed registries
The old process-global `GRAPHS/SCHEMAS/COMPONENTS` are gone. Plugins export a
frozen declarative `CatalogFragment` (nodes, edges, transducers, profiles,
traits, named host descriptors) with **no import-time mutation**. Applications compose
`Catalog.of(openai.FRAGMENT, ...)` — immutable, provenance-stamped;
`Catalog.discover()` (entry points) is an opt-in convenience. `TrustPolicy.
OWNED_ENDPOINTS` by default: a fragment may only register edges touching
interfaces it publishes or canonical — foreign bridging needs named opt-in.
`Catalog.lock()` emits a diffable lockfile whose hash lands in every `Route`.

WU-20 rejects conflicting nodes, directed edges, same-pattern profiles, and
component factories at composition. Builders snapshot declaration mappings;
failed additions leave the builder usable. Profiles sort by literal-prefix
specificity, then lexical pattern. Dates rank revisions within one interface;
multiple eligible sibling interfaces require an explicit `interface=` pin.
The chat front door applies this to serveable interfaces, excluding stubs.
WU-38 adds provisional `HostDescriptor` data in `ocai.convert.hosts`; plugins can
publish it through `CatalogFragment.hosts` without importing wire. Conflicting
same-name hosts fail admission; equal declarations are idempotent. `Catalog.host`
returns a detached descriptor. Hosts neither register graph nodes nor alter
interface identity. Descriptors contain only explicit, non-secret configuration.

Lock format `ocai.catalog-lock/2` includes structured node/endpoint metadata,
full contracts, traits, and optional conformance-resource locations. WU-37
snapshots every trait map at admission and on readback, and fingerprints all
host-specific versions, header groups and feature-body rules. Empty new trait
maps are omitted from lock serialization, preserving legacy-only hashes; adding
explicit declarations changes the fingerprint. Nonempty host declarations and
all their endpoint/profile/header/query data are included; an empty hosts map is
omitted to preserve existing hashes. Host maps are copied on input, admission and
readback. Reordering
the same declarations does not change the hash. The new format changes hashes
from the old format. Code, package artifacts, fixture contents, and schema
contents are not hashed: this is a declaration fingerprint, not proof of binary
reproducibility or certified behavior.

### 4.4 `migrate.py` — IR self-migration
When canonical revision `ocai@2027-01` ships, this module registers certified
`2026-07 ↔ 2027-01` edges — ordinary edges with contracts and fixtures. The
graph is the migration tool; archived transcripts convert forward through the
same honest machinery.

### 4.5 `conformance.py` — the moat as a product
Pure-stdlib harness plugins import: golden-fixture runner, EdgeContract-vs-
runtime-loss certifier, **fold triple** fixtures (wire event log → canonical
chunks → folded response, asserted with `canonjson.semantic_equal`), and
normative unknown-X fixtures every language port must pass. Canonical citation
triples additionally assert exact decoded Unicode text and offsets, including
combining sequences, malformed bounds and annotations arriving before text;
semantic JSON equality alone cannot establish position correctness.

`check_fragment` matches fixture coordinates, requires every payload edge to
have evidence, checks independent expected output/records, and certifies emitted
records against declarations. Streaming edges still need fold triples.
`resources.py` loads explicit `ConformanceResources` manifests from installed
packages through `importlib.resources`; it rejects missing/malformed resources
and conflicting extension schemas. The caller supplies a schema validator and
selects the canonical extension bags to validate. No validation dependency
enters runtime packages. Catalog discovery records locations without loading
schemas or executing tests.

## 5. `ocai.runtime` — movement

| Module | Objects & purpose |
|---|---|
| `decisions.py` | The sans-io policy vocabulary: hooks are objects returning `Proceed | Retry(after) | Fail(error) | Return(response)` — pure, debuggable, one implementation serving both drivers. Effectful backends (redis cache, distributed limiter) declare sync and/or async faces. |
| `drivers.py` | `SyncDriver` / `AsyncDriver` — the two thin executors of the one pipeline: encode (done by facade) → policy hooks → host envelope/endpoint → **credential.apply at the leaf, per attempt, after every hook has seen the request** (no hook, cache, or log can ever see a secret) → send → selected framing/transducer pump → decode. All logic that is not the physical I/O call is synchronous and shared. |
| `interceptors.py` | `CallInterceptor` — port-tier middleware operating on canonical IR calls: fallback, semantic cache, policy/governance, cost metering, tracing. Meaningful for local AND remote (that is the admission test for this tier). Wire-tier concerns live in `ocai.wire.policies`. |
| `binding.py` | `Binding(host, credentials, transport, headers)` — the reusable remote nucleus, normally composed *internally* by the `ocai.chat.model()` front door (§3.4); power users build it by hand. `Binding.validate()` checks the whole stack against the chosen sync/async mode at **composition time** (`CompositionError` naming the offender — the mid-request TypeError class dies). There is deliberately no `Workspace`/container object: per-tenant isolation is several models built from different credentials/catalogs — plain Python, not a framework concept. |
| `dual.py` | `from_sync(port)` / `from_async(port)` adapters (thread offload / portal) — visible composition decisions, never silent bridging. |
| `observe.py` | `Observer` protocol + provisional event shapes [provisional — freezes at v1.0 after real exercise]. |

The driver authenticates a detached transport-only `HttpRequest` per physical
attempt. Its mutable headers are copied, not shared with the safe post-hook
request. `Outcome.request` and references retained by admission hooks stay
unauthenticated for the lifetime of the call, including failures and retries
(ADR 0007, WU-22). This boundary applies to unary and streaming in both modes.
`Binding.extra_headers` snapshots caller data and overrides host/dialect headers
case-insensitively before hooks. Known authentication header names are rejected
in static maps; custom names remain the caller's responsibility to keep non-secret.
Use `ApiKey(header=..., scheme=...)` for custom authentication, or explicitly use
`NoCredential()` for a no-auth endpoint. Passing None still fails; nothing performs
ambient credential discovery.

Port middleware implements both `CallInterceptor` and `StreamInterceptor` to
govern all four call faces. Stream continuations return owned `SyncStream` or
`AsyncStream` protocols; runtime remains capability-neutral. `StreamOutcome`
lives in core result vocabulary and is re-exported by chat. Admission is eager,
with the same snapshotted CallContext. A unary-only interceptor causes streaming
to fail closed before invoking the inner port. Each stream continuation is
single-use, preventing accidental generation restart. If middleware raises after
acquiring a stream, composition closes it. Wrappers forward closure and terminal
evidence; they do not buffer the response. This applies equally to local ports
and wire-backed models (ADR 0007, WU-25).

`ocai.chat.model(..., observers=...)` composes `ObservedChatModel` outside the
entire admission chain and configures physical-attempt observers on its drivers.
Manual compositions use `ObservedChatModel(inner, observers)` for logical calls
and `WireChatModel(..., attempt_observers=...)` for remote attempts. Local ports
use the same outer wrapper with no wire events. No private methods are needed.

`CallStarted` is eager, before admission and stream consumption. `CallFinished`
is emitted exactly once on result, rejection, failure, cancellation or stream
closure. Lazy unconsumed streams have no physical attempt and remain pending
until explicitly closed. `WireStarted`/`WireExchanged` bracket actual transport
attempts; admission retries emit neither. Framing decoder construction happens
before authentication and before a physical-attempt event; construction failure
therefore produces only the logical failure. All events share the logical call id;
caller-supplied parent/correlation ids travel in the start context. Standalone
drivers can receive a CallContext with an explicit call id for correlation.

Events omit payloads, headers, raw errors, exception messages, context tags and
extension bags. Registered observers receive independent snapshots of trusted
identity facts, route (when available), usage and fidelity records. Exporters
must allowlist identities and redact report notes/paths as needed; registration
is the application's observer authorization boundary. Callback failures and
mutations cannot alter results. Required durable audit is an enforceable
middleware responsibility, never an exception thrown from a passive observer.

## 6. `ocai.wire` — remote transport

`http.py` (`HttpRequest/HttpResponse` value objects — also the audit-archive
contract shape), `sse.py` (`SSEParser`, sans-io — survives), `transport.py`
(`Transport`/`SyncTransport` twin ports + `HttpxTransport`; httpx imported
lazily, behind the `[http]` extra), `hosting.py` (`EndpointSpec`, `Host`
protocol, `Direct`/`Custom`/`Vertex` values — dialect-agnostic, reading
`DialectTraits` from `ocai.core.traits` as data, no CloudProvider class —
survives), and
`policies.py` (Decision-based `RetryPolicy`, `RateLimitPolicy` [stub],
`WireTap` audit hook [stub] — feeds content-addressed archive satellites).

WU-37 makes Direct/Custom consume resolved trait headers. Vertex consumes
`body_fields("vertex")`, removes model/stream as before, and keeps the legacy
`setdefault` behavior for legacy-only traits. Explicit declarations that conflict
with a payload field fail before I/O rather than silently selecting a value.
Vertex forwards explicit feature headers unless a Vertex trait mapping relocates
them into the body; version headers are omitted. Its default Anthropic wire body
is unchanged. This is not a Bedrock host implementation.

WU-38 extends `Custom(base_url, paths, ...)` without changing its first two
constructor arguments. `streaming_paths` overrides `paths` for streaming; absent
entries use the codec's native path. The base path, explicit `path_prefix`, and
selected local path compose deterministically, preserving a terminal slash.
Only `{resource}` interpolation is supported; resources are encoded as a single
path segment, including slashes, ARN punctuation, percent signs and whole dot
segments. Templates cannot inject another origin, query, fragment or dot segments.
Query values come from the separate `query` map and are sorted/URL-encoded.
Base URLs cannot carry userinfo, query or fragment; known secret query keys and
static authentication headers fail composition. These checks are guardrails,
not automatic secret detection; all descriptor values must be non-secret.

`static_headers` overrides dialect defaults, then binding headers override it.
`profile_aliases` uses exact resource matches first; otherwise `profile_suffixes`
removes the longest explicitly declared suffix once. Unknown suffixes are retained.
No wire model name changes. `ProfileHost` is an optional structural protocol;
existing `Host` implementations without it retain exact-resource lookup. Input
maps are detached; changing effective configuration invalidates prepared calls.
These generic recordings qualify composition, not any named cloud provider.

WU-39 adds optional `FramingHost.stream_framing(spec) → StreamFraming`; legacy
hosts keep SSE without implementing another method. `StreamFraming(name, factory,
options)` carries detached, non-secret JSON configuration and a trusted factory
that creates a fresh `StreamDecoder` per admitted physical stream. The factory
receives another options copy; it must not depend on hidden mutable configuration
or ambient discovery. Preparation identity hashes name/options and in-process
callable identity (including bound-method owner), not executable artifacts.
Factories are preserved, not cloned, across preparation snapshots. Replacing a
factory or changing effective options invalidates approval even if HTTP is identical.

The decoder owns `feed(bytes)`, `finish()` and `close()`. It removes transport
framing and host envelopes, emitting the existing plugin input event representation.
It never creates canonical parts or performs provider field mapping. Normal byte
EOF invokes `finish` once, feeds its tail through the same graph, then closes the
decoder and transport and flushes conversion evidence. Failure, explicit close,
consumer cancellation and deadline expiry skip `finish`, close both resources and
retain available pipeline accounting. Cleanup never replaces a primary execution
error; a cleanup error on an otherwise normal path fails that stream. Closing an
unconsumed stream allocates neither decoder nor provider attempt. No retries after
I/O starts; admission retries do not allocate decoder state.

SSE remains the default, with incremental UTF-8 decoding across byte boundaries;
legacy SSE field/event dispatch rules remain in `SSEParser`. Semantic terminal
validation remains in codecs/facade, so raw EOF or a framing tail cannot manufacture
successful completion. Framing errors can invalidate a previously seen semantic
terminal event before `StreamEnd` is released. Async pending reads are bounded by
the remaining deadline; sync reads cooperate through timeouts and checks, without
claiming preemption of arbitrary blocking code. Both check deadlines before
accepting decoder output. The test-only length-prefixed envelope qualifies this
seam, not AWS EventStream; no canonical shape or conversion edge changed.
See [ADR 0014](decisions/0014-host-selected-stream-framing.md).

## 7. Plugins — one subpackage per interface

WU-41 qualifies safe fallback for server-tool request intent on Chat Completions
and Anthropic Messages: only functions use the existing mapping; whole server or
unknown entries are reported unsupported. No server-search version is claimed
until its provider-specific WU qualifies mappings and replay. Request census and
golden fixtures cover these exclusions; recorded unary/SSE pairs preserve the
existing response fold law with the supported function lane intact.


```
ocai-openai/src/ocai/openai/
  __init__.py            FRAGMENT (CatalogFragment) + model prefill helpers
  chat_completions/      wire.py (msgspec structs) · codec.py (encode/decode/
                         decode_event/map_error) · edges + EdgeContract +
                         CapabilityProfile + DialectTraits
  responses/             same shape for the /responses interface [stub]
ocai-anthropic/src/ocai/anthropic/
  messages/              same shape
```

Rules: depend on core+convert only (no httpx); msgspec only at the wire-decode
boundary; every extension key census-registered; every edge ships fixtures;
no import-time global mutation; `py.typed` shipped; pyproject pins
`ocai>=0.x,<0.y`. **A plugin's only structural effect is data**: installing it
makes its fragment discoverable, adding interfaces and edges to the graph
(§3.4). First-party endpoint data (base URL, native paths) rides the fragment
so the core front door composes a `Direct` binding without importing the
plugin. A plugin MAY additionally ship a convenience helper
(`ocai.openai.chat_model(...)`) — a thin wrapper over the same fragment +
facade machinery, never a separate code path, and never required: the core
string door must always work without it.

Anthropic's WU-37 traits declare separate Vertex and Bedrock body versions and
a Bedrock `anthropic-beta` → `anthropic_beta` list mapping. Feature values remain
empty until explicitly supplied; no beta is enabled by installing the plugin.
The legacy Vertex tuple and first-party version header remain available.

WU-29 qualifies the Chat Completions client request decoder for the gateway
matrix in `plans/gateway-readiness.md`. Function tool identity/order and named
choice survive; JSON Schema output intent round-trips to OpenAI and maps to
Anthropic output_config with name/strict losses reported. Function-tool strict,
message names, unknown nested fields and conflicting legacy token limits are
preserved by source path in `openai.request_unmapped`, never silently replayed.
Multi-choice `n != 1` is explicitly UNSUPPORTED and retained as `openai.n`.
Non-text request content remains opaque and reported; file/media execution and
strict function-tool enforcement are excluded from the qualified client surface.
Existing scoped-reference guards still prohibit cross-provider replay.

WU-30 registers canonical response → Chat Completions response. Text, refusal,
function identity/argument strings, finish and measured usage have client lanes.
Grouping ordered parts into message lanes is a relocation finding. Unsupported
parts, annotations, extensions and scoped identities remain reported. Unknown
finish codes preserve their native string with UNSUPPORTED evidence. No raw body
is copied to client output. `chat_completions.client.ClientMetadata.bind` supplies
explicit gateway id/model/created after conversion; graph output omits unavailable
identity. A foreign response id is not laundered into an OpenAI reference.
OpenAI decode subtracts cache/reasoning subsets from prompt/completion totals;
client encode adds them back. Missing measurements remain absent, never zero.

WU-31 registers canonical chunks → client JSON events. A fresh transducer keeps
part identities, rolling checksums, usage and finish, without accumulating text or
arguments. Final-part mismatches fail; part starts must follow canonical order.
Successful finish/usage events require StreamEnd; errors and incomplete flushes
never synthesize completion. Flush yields a separate egress report, without
merging upstream StreamEnd.report. Gateways bind ClientMetadata, frame SSE, and
emit DONE only after accepting upstream outcome and egress report. Streaming
refusal has its own sparse decode slot after text/tools, preventing text/refusal
collisions; reverse fold triples qualify the mixed-content case.

WU-32 qualifies the complete client → canonical → provider → canonical → client
path with recorded OpenAI and Anthropic text/tool HTTP/SSE pairs on all four call
faces. `examples/governed_gateway.py` and `docs/gateway-integration.md` demonstrate
public preparation, admission, policy enforcement, serving metadata and ownership.
The combined ledger contains ingress + execution's two legs + egress exactly once.
Client egress policy may fail after the kernel invocation succeeds; gateway
serving outcome is distinct from kernel lifecycle and retains its own evidence.
Authentication, compartments, deployment selection, budgets, persistence and HTTP
serving remain satellite responsibilities. Qualification does not promote a new
canonical revision or alter the ADR 0005 freeze gate.

## 8. Request lifecycle (how it all interacts)

The merged [governed gateway program](plans/gateway-readiness.md) implements
ADR 0007. The proposed [tier 1–2 integration program](plans/integration-program.md)
sequences subsequent host, chat, provider and satellite work; its unchecked WUs
are not shipped capabilities. A gateway remains a satellite owning authentication,
compartments, deployment selection, budgets, persistence and HTTP serving.
Canonical 2026-07 remains active; integration proposals do not change the §9 gate.


```
user code
  └─ ChatModel port (ocai.chat.protocol)              CallContext rides along
       └─ CallInterceptor chain (runtime)             fallback · policy · cost · cache · tracing
            └─ WireChatModel facade (ocai.chat.facade)
                 ├─ Catalog.resolve(capability, provider, pins) → Route(NodeId, reason, catalog hash)
                 ├─ ConversionGraph.convert(request, ocai@rev → target NodeId)
                 │      └─ per-edge: EdgeContract-checked fn → FieldLoss/SemanticShift
                 ├─ Driver (sync or async — same pipeline)
                 │      ├─ Decision hooks (wire policies: retry, rate-limit, wiretap)
                 │      ├─ Host.envelope/endpoint/headers (ocai.wire.hosting)
                 │      ├─ Credential.apply — at the leaf, per attempt
                 │      └─ Transport.send / stream → selected framing/envelope decoder → transducer chain
                 ├─ ConversionGraph.convert(wire response → ocai@rev)
                 └─ CallResult(value, route, report, usage, raw)
streaming: chunks flow through StreamEdge transducers; the stream ends with
StreamEnd(usage, finish, report); StreamAccumulator.fold(chunks) == ChatResponse.
local adapters: implement the port directly — same CallResult, no wire/runtime.
```

## 9. Stability domains & freeze staging

Freeze is **earned**. The gate is defined by
[ADR 0005](decisions/0005-revised-freeze-gate.md) and sequenced by the
[core modernization plan](plans/core-modernization.md): data contracts
(`ocai.core` vocabulary, chat port + chat IR, their `spec/` schemas) freeze
additive-only at the first release after the modernization qualification —
ordered-item migration evidence (ADR 0003), item-addressed streaming with
fold parity, an independently packaged plugin passing conformance, and the
`/responses` interface with its migration proof (H1), which remains required
but is no longer sufficient on its own. `ocai.embedding` /
`ocai.vectorstore` stay provisional until they carry `CallResult` in anger.
Hook protocols, plugin ABI (`CatalogFragment`), profile keys, and observer
events freeze at v1.0 **only after** the `/responses` migration and one real
cross-provider failover have been exercised through them. A gate never
changes without an ADR; a plan file sequences work toward a gate and never
redefines one. Three version axes, never conflated: interface **tag**
(provider wire), canonical **revision** (`ocai@YYYY-MM`), library
**semver** — the freeze is a release gate, not a version number.

## 10. spec/ — the language-neutral truth

`spec/canonical-json.md` (the equality predicate — write FIRST),
`spec/schema/` (JSON Schema per core contract + capability IR),
`spec/fixtures/` (golden conversion fixtures per edge; fold triples per
streaming edge), `spec/extensions/` (censused extension schemas),
`spec/interfaces/` (catalog descriptors as data). CI re-runs every language
suite on `spec/**` changes; fixtures are validated against schemas so
spec-vs-code contradictions are structurally detectable. WU-40 adds canonical
citation triples and registered invalid-evidence extensions under ADR 0008;
these qualify the existing canonical revision without registering a new node.
WU-41 extends the request schema with a tool union and location definition, plus
canonical round-trip and provider fallback fixtures; legacy function schemas
remain valid and no canonical revision is registered.

## 11. Adding a capability (normative recipe)

Any new capability — rerank, image, transcription, realtime, files, jobs — is
added by this recipe. Every step is additive; none touches a frozen surface.

1. **Mint identity as data.** Define `Capability("<name>")` and one `Shape`
   per message role per operation (`("rerank","request")`, or
   `("vectorstore","query.request")` for multi-op ports). `Capability`,
   `Shape`, and `NodeId` are open value objects; graphs never mix shapes, so
   the new capability's conversion graphs are born partitioned from every
   existing one. Zero core changes.
2. **Write the canonical IR in a new capability package** (`ocai.<name>`)
   that imports `ocai.core` **only** (import-linter enforced). Named
   request/response dataclasses extend `IRObject` (omit-absent `to_dict`,
   tolerant `from_dict`); enums are open codes with canonical constants;
   unions are tagged through `TagRegistry` with an Unknown fallback. **Reuse
   core vocabulary — `Usage`, `FinishInfo`, `ProviderRef`/`SourceRef`, the
   `Source` union — never mint capability-local clones.**
3. **No routing data in the request.** The model/index/voice name is bound at
   the front door and injected by the codec from `EndpointSpec.resource`; a
   request IR carrying a `model` field fails review. Requests are pure,
   portable graph payloads.
4. **Define the port.** A `Protocol` whose every method returns
   `CallResult[NamedResult]` and accepts optional `ctx: CallContext`;
   bare-name sync plus `a`-prefixed async twins; multi-op capabilities get
   one method per operation. Local in-process adapters implement the port
   directly and return the same `CallResult` (`route=None` or
   `host="in-process"`) — local and remote are peers.
5. **Publish canonical nodes.** The capability's canonical IR is the
   interface named `ocai`: register a `NodeId` per shape at the current
   canonical revision, and at least one request-role shape per operation
   (the resolution anchor).
6. **Contribute provider support as fragment data.** Each provider interface
   adds, via its `CatalogFragment`: nodes, edges with `EdgeContract`s (full
   census + declared `SemanticShift`s), a `CapabilityProfile`,
   `DialectTraits`, and endpoint data (`Operation` kinds, native paths,
   resource pattern). A `ProviderRef` leaving its validity scope is
   `UNSUPPORTED`-and-reported; asynchronous execution (submit/poll/fetch) is
   modeled as separate `Operation`s, each returning its own `CallResult` and
   `Route`, anchored by `ProviderRef(kind="job")`.
7. **Admit knobs by the three-lane law (§3.5).** First-class fields require
   ≥2–3 interfaces with congruent semantics; provider-unique keys are
   censused extensions in `spec/extensions/`; destination-scoped passthrough
   rides `provider_options`. Exclusions are recorded with promotion triggers.
8. **If the capability streams, ship the streaming ratchet with it.** One
   canonical chunk union per streaming shape, a `Delta` type per
   part/fragment kind, and a capability-defined fold law with fold-triple
   fixtures — the law itself is per-capability (chat folds by concatenation;
   image previews fold by replacement; duplex sessions fold a frame log into
   a transcript). No event type is admissible without its delta, fold law,
   and paired fixtures in the same change.
9. **Map failures and consumption through core.** Wire errors go through the
   shared taxonomy with codec `map_error` refinement; consumption is
   reported as core `Consumption` records — new modalities/units (`seconds`,
   `read_units`, `search_units`) are open-code data, never releases.
10. **Land schemas and fixtures in `spec/` in the same change.** JSON Schema
    per shape, golden fixtures per edge, fold triples per streaming edge,
    censused extension schemas. The cross-language drift alarm covers the
    capability from its first commit.
11. **Build the front door last, on the same grammar.**
    `ocai.<name>.<factory>("<provider>/<resource>", *, credentials,
    host=None, catalog=None, ...)` — one spec string, split on the FIRST
    slash (`"pinecone/my-index"`, `"voyage/voyage-4-large"`; the resource may
    contain slashes) — composes codec + `Binding` + `Catalog` behind the
    port; the facade module must not share the factory's name. The facade —
    never an edge, never a driver — owns any 1-logical-call→N-wire-calls
    fan-out (batch splitting, job polling legs, resumable uploads), merging
    usage and reports and declaring the fan-out as a `SemanticShift`.
12. **Certify before shipping; freeze only when earned.** Run the
    conformance harness: round-trips under `canonjson.semantic_equal`,
    EdgeContract certification (runtime loss never exceeds declaration),
    unknown-X totality fixtures. The package stays [provisional] until it
    has carried `CallResult` in real use, then freezes additive-only.

The scope litmus test: a thing with provider-varying wire dialects is a
capability (rerank, moderation, files); a thing with no wire dialect
(chunking, prompt management, LLM judges, eval orchestration, application
memory) is built ON ocai — the kernel contributes substrate (pure-data IR,
canonical JSON, `CallContext`, the ledger), never the feature. Recorded
doctrine: the conversion graph never registers vector-space edges (embeddings
from different models do not "convert"); batch fan-out lives in facades;
`Job`/`JobHandle` is the reserved name for the async-job vocabulary (never
`Operation`); `Catalog.resolve` gains a `role=` kwarg when the first multi-op
capability lands.

## 12. Platform product boundary

The accepted repository layout is recorded in
[ADR 0006](decisions/0006-platform-product-layout.md). Top-level `python/`,
`typescript/`, and `go/` hold independently distributed libraries. Deployable
products belong under `platform/`: backend services in `services/`, user-facing
applications in `apps/`, and internal reusable code in `packages/`. The gateway's
target location is `platform/services/gateway/`; these locations do not imply
that platform services are implemented yet.

Platform products depend on public ocai libraries; those libraries never depend
on platform implementation code. Independently usable satellite libraries may
live under the language directories, while their consuming services remain under
`platform/`. Provider conversion stays in plugins, and product administration,
storage, authorization, and orchestration stay outside the kernel.

Root `spec/` remains the canonical kernel contract source. Platform APIs, events,
and configuration contracts live in `platform/spec/` and reference kernel
contracts where needed. Platform dependency environments and lockfiles are
separate from library development. The scaffolding WU must add the corresponding
boundary and integration checks to repository verification. The broader product
direction is documented in [the platform overview](platform/README.md).

### 12.1 Initial platform foundation [provisional]

[ADR 0009](decisions/0009-platform-foundation.md) records the implemented first
slice. `platform/services/gateway/app/` is a non-distributed FastAPI application
with its own uv environment/lock. Reusable ASGI middleware stays inside the
service until another backend needs it. It generates request IDs, sanitizes
errors, forwards streamed bodies without accumulation, and emits allowlisted
completion diagnostics. Diagnostic observers do not provide durable audit.

The console extends the `nuxt-platform` shell layer, which extends `nuxt-ui`.
Product navigation and pages belong to the console. The UI layer contains the
complete shadcn-vue UI registry snapshot, neutral semantic tokens, and on-demand
`Ui*` registration through `shadcn-nuxt`; Ocarinow token overrides belong to the
higher platform layer. Tailwind scans every consuming layer without hardcoded
app paths. Component types/composables use explicit package subpath imports.
[ADR 0012](decisions/0012-shadcn-component-layer.md) records this boundary. A framework-independent management client uses
generated OpenAPI types and validates its status response at runtime. The
console server exposes a fixed status proxy with no caller credential forwarding.

Only non-sensitive health and foundation status are served. Readiness returns
503; identity, OpenFGA enforcement, PostgreSQL state, inference, durable audit,
and accounting are not implemented in this slice. Root verification includes
platform typing, API drift, boundary/HTTP tests, production build, and a browser
integration test against the real service.

### 12.2 Identity boundaries [direction; not implemented]

[ADR 0013](decisions/0013-platform-identity.md) records the next identity boundary.
Keycloak is the reference separately deployed provider for local accounts and
OIDC/SAML federation; qualified customer OIDC providers remain possible. Nuxt's
server layer owns console sessions and keeps tokens server-side. FastAPI validates
API credentials and enforces resource permissions using trusted platform context
and OpenFGA decisions. Platform principal IDs, memberships, service accounts,
credential scopes and audit semantics remain provider-independent.

Identity integration stays in modular gateway application code until another
backend consumer warrants extraction. Future services validate their own audience
and permissions; machine authority and human-delegated authority stay distinct.
These requirements do not change §12.1's implemented public status surface.
See [identity and access](platform/identity.md) for protocol boundaries, frontend
reuse, non-human identities, qualification gates and operational responsibilities.

The [authenticated console program](plans/platform-identity.md) sequences the
first implementation; [ADR 0011](decisions/0011-authenticated-console-contract.md)
proposes its persistence/session policy, operator bootstrap and transactional
audit plus OpenFGA synchronization contract. These remain design requirements;
subsequent WUs add the corresponding runtime evidence and update this section.

### 12.3 Platform identity persistence [provisional]

WU-73 adds internal `app/storage/` with explicit PostgreSQL connection settings,
SQLAlchemy async transactions and reviewed Alembic migrations. Operator role
bootstrap owns the `platform` schema separately from `ocai_gateway` runtime
access. Opening storage verifies the exact schema revision and runtime privilege
profile; migration ownership, audit mutation privileges or missing required grants
are rejected. There is no import-time connection or automatic HTTP-startup migration.

Stable principal IDs have unique exact issuer/subject bindings. Organization IDs
scope memberships, audit reads and authorization-outbox reads; a composite foreign
key prevents outbox entries referring to a membership in another organization.
Repository results are immutable records, not mutable ORM entities. Organization
creation/rename and membership grants include fixed-schema audit events in their
transaction; failure rolls back state, evidence and any authorization intent.
Organization versioning prevents stale overwrites; grants serialize on the
organization row to assign ordered desired revisions. WU-73 leaves applied revision zero; §12.5 adds the confirmed OpenFGA projection.

The runtime can append/read audit rows but cannot update/delete/truncate/alter
them. These grants do not establish immutable-storage guarantees against database
administrators. Repositories require authorized scope from a future application
service; this storage WU does not implement RLS, authentication, protected HTTP
endpoints or permission enforcement. Public foundation status/readiness is unchanged.

The platform gate provisions a disposable digest-pinned PostgreSQL container and
tests real migrations, restart persistence, concurrent transactions, audit rollback,
constraint isolation and role enforcement. Missing Docker fails verification.
See [platform operations](../platform/README.md) for bootstrap, migration and
explicit connection configuration.

### 12.4 Reference issuer authentication [provisional]

WU-74 adds `app/identity/`: explicit issuer/audience/client configuration, bounded
same-origin OIDC discovery and JWKS retrieval, and `joserfc` RS256 verification.
Only the configured Keycloak access-token profile yields an `ExternalIdentity`:
exact issuer, API audience, console authorized party, Bearer token type, bounded
subject, expiration/issued-at and maximum five-minute lifetime. ID tokens and
caller-supplied identity headers never establish API identity. The FastAPI
`authenticated_identity` dependency requires one bearer credential; no new public
identity/debug endpoint is introduced.

Each application lifespan owns its HTTP client and key cache. Network calls ignore
ambient proxies, disallow redirects and enforce time/document/key-count bounds.
Untrusted JWT headers never choose a network endpoint. Cached keys are fresh for
at most five minutes; refresh is single-flight and limited to once per five
seconds. Fresh known keys remain usable during issuer outage; unknown/stale keys
fail closed. Invalid credentials receive sanitized 401 with a Bearer challenge;
unavailable verification infrastructure receives sanitized 503.

Authentication establishes external identity only. Binding to an active platform
principal, current membership and OpenFGA enforcement are described in §12.5;
successful login never provisions membership or grants access by itself. Existing
foundation status and readiness retain their earlier meaning.

Local `serve:*` tasks explicitly create isolated PostgreSQL/Keycloak infrastructure,
generate private development credentials and install app dependencies. Production
requires HTTPS; the separate loopback development profile is not production
qualification. Tests exercise Authorization Code with PKCE against digest-pinned
Keycloak and adversarial signed credentials, key rotation, outage and forged
headers. See [platform operations](../platform/README.md).


### 12.5 Bootstrap and authorization [provisional]

WU-75 adds a migrated singleton installation identity, consumed by explicit
operator bootstrap. First-owner identity, organization, membership, audit and
outbox intent commit together. The consumed state pins the OpenFGA store/model;
replays and concurrent claims cannot create another bootstrap owner. There is
no bootstrap HTTP endpoint or first-login provisioning path.

The authorization adapter validates the reviewed immutable owner/viewer model,
uses explicit authenticated HTTP and requests higher-consistency checks. PostgreSQL
remains authoritative: active principal/membership and matching desired/applied
revisions are required before a permission can be used. Organization and principal
locks remain held through the authorized operation and its audit commit.

Projection serializes on the organization row, writes one idempotent tuple change
at a time and advances applied revision only after confirmation. A crash between
tuple write and acknowledgement leaves requests blocked and retries the same
revision. Revocation marks membership inactive transactionally before projection.
A bounded maintenance worker discovers pending organization IDs, processes up to
ten revisions for each of ten organizations per pass, and retries unavailable
projection after two seconds. Its structured records report progress/failure
without credentials or raw relationship payloads. This maintenance scan is not a
tenant read API. Multiple workers serialize through the same row locks.

Operator commands inspect installation state, consume bootstrap explicitly or
reconcile one organization. Local setup separately provisions OpenFGA's PostgreSQL
role/database, applies its migrations and creates/verifies the pinned model.
Starting applications does not run platform or OpenFGA migrations. Production
uses explicit HTTPS service configuration and an authenticated, private OpenFGA
endpoint; the console never receives its credentials.

The transaction wrapper is for short management operations, not for holding
organization locks across model generation or agent execution. Data-plane admission
and in-flight execution policies require their own qualification. Tests cover real
PostgreSQL/OpenFGA bootstrap races, crash recovery, permission isolation, suspension,
model rejection, provisioning and mutation/revocation serialization. See
[platform operations](../platform/README.md) for configuration and recovery limits.
