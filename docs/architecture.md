# ocai architecture

This document is the **structural contract** of the repository: the layers, every
load-bearing object, what each is for, and how they interact. Code is the
implementation of this document; when they disagree, fix one *in the same PR*.
The design was settled in July 2026 (multi-agent design review); the rationale
for each decision is summarized inline.

Status legend: **[frozen-candidate]** freezes additive-only at v0.2 ·
**[provisional]** may still change until exercised · **[stub]** structure only,
implementation pending.

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
│                  identity · fidelity · errors · result · credentials ·     │
│                  refs · profile · ir · canonjson · jsonschema · sources    │
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
   ocai.chat.model (the wire-backed facade) is the ONE chat module allowed to
   import convert/runtime/wire — the port and types never do.

 Plugin dists (ocai-openai, ocai-anthropic, …): one subpackage PER INTERFACE
 (ocai.openai.chat_completions, ocai.openai.responses). Depend on core+convert
 ONLY — never on wire/httpx, so an offline audit tool can re-convert archived
 traffic without the ability to make network calls.

 Local adapters (future ocai-faiss, ocai-llamacpp): implement a capability port
 directly, depend on core only. Local and remote are peers at the port plane.

 Enterprise satellites (future ocai-otel, ocai-archive-*, ocai-vault-*):
 implement core/runtime hook protocols. The kernel never grows an opinion.
```

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

`CallContext(tenant, principal, classification, deadline, tags)` is the
per-request governance carrier, threaded through ports as an optional keyword
— a policy like "PII-classified traffic may not go to provider X" needs the
classification *at call time*; without a sanctioned carrier, enterprises
smuggle it through bags.

### 2.4 `refs.py` — provider-anchored state [frozen-candidate]

`ProviderRef(provider, interface, kind, id, replay)` names state that lives on
a provider's side: `previous_response_id`, file handles, thought signatures,
audio ids. Structural rule enforced by the graph: **a `ProviderRef` crossing
any other `(provider, interface)` is `UNSUPPORTED` — reported, never silently
dropped.** `replay ∈ {OPTIONAL, REQUIRED}`: REQUIRED anchors (Gemini
`thoughtSignature`, Anthropic thinking signatures) are weighted as *breakage*
in planning, not mere loss — dropping them produces a 400, not degraded output.

### 2.5 `profile.py` — declared capability facts [provisional]

`CapabilityProfile` maps feature keys → `Support.NATIVE | EMULATED | ABSENT`,
keyed `(provider, interface, model_pattern)` — the model dimension is required
because support varies below interface level (Anthropic's newest models reject
`temperature`). Consulted by the feature gate *before* payload conversion:
strict mode refuses with a typed error; annotate mode records the loss.
Feature keys are namespaced open data, not a frozen taxonomy.

### 2.6 `ir.py` — the IR envelope and total decode [frozen-candidate]

| Object | Purpose |
|---|---|
| `IRObject` | Base for all IR dataclasses: `version` (canonical revision), `provider_options` (destination-scoped passthrough, §3.4), `extensions` (namespaced bag for unmapped-but-preserved data). **Omit-absent** `to_dict` (absent/None fields are not emitted — this is what makes "additive" real: adding an optional field never invalidates a fixture). **Tolerant** `from_dict` (unknown keys sweep into `extensions`, never raise). |
| `TagRegistry` | Open registration for tagged unions (parts, deltas, details). Decoding an unknown tag returns the registered *Unknown* fallback — **no decode path in the IR may ever raise on unknown input.** Plugin tags must be namespaced (`anthropic.mid_conv_system`); bare tags are reserved for core. |

Precedence rule (normative): unknown *envelope keys* sweep to `extensions`;
unknown *content tags* fall back to the Unknown type; a decoder never applies
both to the same bytes.

### 2.7 `canonjson.py` — the equality predicate [frozen-candidate]

Every conformance guarantee in this repo (fold fixtures, round-trips, the
drift alarm) depends on "semantic equality over canonical JSON" — so it is
defined **once, normatively**, here and in `spec/canonical-json.md`: key
ordering, number forms, unicode normalization, absent-vs-null, and the
parse-compare/preserve-verbatim rule for embedded JSON strings (`args_json`).
`canonical(obj) -> str` and `semantic_equal(a, b) -> bool`. TS/Go ports
implement the same spec; they cannot each invent their own.

### 2.8 `traits.py` and survivors

`DialectTraits` (vendor, first-party headers, cloud body version) lives in the
**contract layer**, not in `ocai.wire`: it is *declared* by plugin interface
subpackages (which may only import core+convert) and merely *read* by wire
hosts. Plus the survivors: `errors.py` (the taxonomy — unchanged),
`credentials.py` (`Credential` protocol + `ApiKey`, explicit-only, redacted —
unchanged; *application* moved to the driver leaf, §5), `jsonschema.py`,
`sources.py` (gains `SourceRef(ProviderRef)` for provider file handles),
`primitives.py`.

## 3. `ocai.chat` — the chat capability contract

Depends on `ocai.core` only (except `model.py`, the designated facade).

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

**`types/finish.py`** — `FinishInfo(reason, native, detail)`: canonical open
code (`complete | max_tokens | stop_sequence | tool_call | content_filter |
refusal | recitation | paused | malformed | error | …`), `native` verbatim
provider value, `detail` a tagged union (`SafetyDetail(ratings, block_source)`,
`RefusalDetail(category, explanation)`, `IncompleteDetail`, `ErrorDetail`,
`DetailOpaque`). Unknown wire values decode to `reason="unknown"` with the
native lane preserved — enum growth is structurally crash-proof. Boundary
rule: mid-generation refusal is a *response*; pre-generation block (Gemini
`promptFeedback`) is a `ContentFilterError`.

**`types/usage.py`** — the dimensional `Consumption` model survives (it
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
a *pure graph payload* — no report field (that's `CallResult`'s). Single message forever:
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

### 3.3 `model.py` — the wire-backed facade

`WireChatModel(codec, binding, catalog, model_name=...)` — the composition of
a dialect codec, a `Binding` (§5), and a `Catalog` (§4) behind the port, plus
the bound model name (§3.4 — the front doors pass it at construction; it
becomes `EndpointSpec.resource`, never a request field). The one chat module
that imports convert/runtime/wire. Encode via graph → inject the bound model
via the codec's `bind_resource` (edges stay model-agnostic; only the codec
knows where its wire carries the name) → driver executes → decode via graph →
assemble `CallResult`.

### 3.4 The front doors — simple facade, switchable by data

The user-facing API is simple, pydantic-ai-shaped: build a model object once
(the provider-specific **model name is bound HERE, never carried in the
request**), then call it with pure conversation payloads.

```python
import ocai.chat
from ocai.core import ApiKey
from ocai.chat.types import ChatRequest, Message

chat = ocai.chat.model("openai", "gpt-5",
                       credentials=ApiKey.from_env("OPENAI_API_KEY"))
res = chat.chat(ChatRequest(messages=[Message.user("hello")]))
```

Two equivalent doors, neither forced:

1. **The core string door** — `ocai.chat.model(provider, model_name, *,
   credentials, host=None, catalog=None, transport=None, interceptors=())`:
   resolves the provider against the discovered default catalog (or an
   explicit one), builds the codec from the fragment's registered component
   factory, composes the `Binding` internally (`Direct` host from the
   fragment's first-party endpoint data unless a host is passed). Switching
   provider — or riding an interface migration — is changing a string or a
   pin.
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

## 4. `ocai.convert` — meaning

### 4.1 `graph.py` [frozen-candidate mechanics]
The Dijkstra planner survives. `Edge(src: NodeId, dst: NodeId, fn, contract,
origin)`; planner cost is **derived** from the contract (§4.2), never
author-declared. `Converted(value, report)` named result. `StreamEdge` is a
*transducer factory* (`feed(event) -> events; flush() -> (events, EdgeReport)`)
so chunk-shape edges are planned by the same machinery — streaming conversion
joins the graph instead of bypassing it.

### 4.2 `contract.py` — EdgeContract
An edge's declared per-field disposition census. Core derives the planner
weight as a lexicographic `LossGrade` (unsupported+dropped, approximated,
emulated, hops) — impossible to game with a magic float. The conformance
harness certifies at build time that an edge's *runtime* `FieldLoss` never
exceeds its declaration: **an edge claiming lossless that drops a field cannot
ship.**

### 4.3 `catalog.py` — scoped, governed registries
The old process-global `GRAPHS/SCHEMAS/COMPONENTS` are gone. Plugins export a
frozen declarative `CatalogFragment` (nodes, edges, transducers, profiles,
traits) with **no import-time mutation**. Applications compose
`Catalog.of(openai.FRAGMENT, ...)` — immutable, provenance-stamped;
`Catalog.discover()` (entry points) is an opt-in convenience. `TrustPolicy.
OWNED_ENDPOINTS` by default: a fragment may only register edges touching
shapes it publishes or canonical — foreign bridging needs named opt-in.
`Catalog.lock()` emits a diffable lockfile whose hash lands in every `Route`.

### 4.4 `migrate.py` — IR self-migration
When canonical revision `ocai@2027-01` ships, this module registers certified
`2026-07 ↔ 2027-01` edges — ordinary edges with contracts and fixtures. The
graph is the migration tool; archived transcripts convert forward through the
same honest machinery.

### 4.5 `conformance.py` — the moat as a product
Pure-stdlib harness plugins import: golden-fixture runner, EdgeContract-vs-
runtime-loss certifier, **fold triple** fixtures (wire event log → canonical
chunks → folded response, asserted with `canonjson.semantic_equal`), and
normative unknown-X fixtures every language port must pass.

## 5. `ocai.runtime` — movement

| Module | Objects & purpose |
|---|---|
| `decisions.py` | The sans-io policy vocabulary: hooks are objects returning `Proceed | Retry(after) | Fail(error) | Return(response)` — pure, debuggable, one implementation serving both drivers. Effectful backends (redis cache, distributed limiter) declare sync and/or async faces. |
| `drivers.py` | `SyncDriver` / `AsyncDriver` — the two thin executors of the one pipeline: encode (done by facade) → policy hooks → host envelope/endpoint → **credential.apply at the leaf, per attempt, after every hook has seen the request** (no hook, cache, or log can ever see a secret) → send → SSE/transducer pump → decode. All logic that is not the physical I/O call is synchronous and shared. |
| `interceptors.py` | `CallInterceptor` — port-tier middleware operating on canonical IR calls: fallback, semantic cache, policy/governance, cost metering, tracing. Meaningful for local AND remote (that is the admission test for this tier). Wire-tier concerns live in `ocai.wire.policies`. |
| `binding.py` | `Binding(host, credentials, transport, headers)` — the reusable remote nucleus, normally composed *internally* by the `ocai.chat.model()` front door (§3.4); power users build it by hand. `Binding.validate()` checks the whole stack against the chosen sync/async mode at **composition time** (`CompositionError` naming the offender — the mid-request TypeError class dies). There is deliberately no `Workspace`/container object: per-tenant isolation is several models built from different credentials/catalogs — plain Python, not a framework concept. |
| `dual.py` | `from_sync(port)` / `from_async(port)` adapters (thread offload / portal) — visible composition decisions, never silent bridging. |
| `observe.py` | `Observer` protocol + provisional event shapes [provisional — freezes at v1.0 after real exercise]. |

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

## 7. Plugins — one subpackage per interface

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

## 8. Request lifecycle (how it all interacts)

```
user code
  └─ ChatModel port (ocai.chat.protocol)              CallContext rides along
       └─ CallInterceptor chain (runtime)             fallback · policy · cost · cache · tracing
            └─ WireChatModel facade (ocai.chat.model)
                 ├─ Catalog.resolve(capability, provider, pins) → Route(NodeId, reason, catalog hash)
                 ├─ ConversionGraph.convert(request, ocai@rev → target NodeId)
                 │      └─ per-edge: EdgeContract-checked fn → FieldLoss/SemanticShift
                 ├─ Driver (sync or async — same pipeline)
                 │      ├─ Decision hooks (wire policies: retry, rate-limit, wiretap)
                 │      ├─ Host.envelope/endpoint/headers (ocai.wire.hosting)
                 │      ├─ Credential.apply — at the leaf, per attempt
                 │      └─ Transport.send / stream → SSEParser → transducer chain
                 ├─ ConversionGraph.convert(wire response → ocai@rev)
                 └─ CallResult(value, route, report, usage, raw)
streaming: chunks flow through StreamEdge transducers; the stream ends with
StreamEnd(usage, finish, report); StreamAccumulator.fold(chunks) == ChatResponse.
local adapters: implement the port directly — same CallResult, no wire/runtime.
```

## 9. Stability domains & freeze staging

Freeze is **earned**: at v0.2 only the data contracts freeze (`ocai.core`
vocabulary, chat port + chat IR, their `spec/` schemas). `ocai.embedding` /
`ocai.vectorstore` stay provisional until they carry `CallResult` in anger.
Hook protocols, plugin ABI (`CatalogFragment`), profile keys, and observer
events freeze at v1.0 **only after** the `/responses` migration and one real
cross-provider failover have been exercised through them — the flagship WUs
are the freeze qualification gate. Three version axes, never conflated:
interface **tag** (provider wire), canonical **revision** (`ocai@YYYY-MM`),
library **semver**.

## 10. spec/ — the language-neutral truth

`spec/canonical-json.md` (the equality predicate — write FIRST),
`spec/schema/` (JSON Schema per core contract + capability IR),
`spec/fixtures/` (golden conversion fixtures per edge; fold triples per
streaming edge), `spec/extensions/` (censused extension schemas),
`spec/interfaces/` (catalog descriptors as data). CI re-runs every language
suite on `spec/**` changes; fixtures are validated against schemas so
spec-vs-code contradictions are structurally detectable.
