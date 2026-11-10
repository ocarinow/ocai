# Tier 1–2 integration program

Source: maintainer request to "produce docs/plans/integration-program.md" from
[the capability roadmap](../capabilities/README.md), then implement one WU per
PR. The maintainer subsequently authorized stacked PRs, retaining one WU per PR.

## Baseline and sequencing

PRs #14–#23 and their parent #8 are merged into `main`; #24 supplies the survey,
and #26 supplies the platform design. The executable baseline is current main,
not the survey's implementation-status paragraphs. WU-22–32 already provide
credential isolation, context/deadlines, stream ownership and middleware,
metadata-only lifecycle events, public preflight and fidelity enforcement.
`WireExchanged` has an emission site in `runtime.observe.Attempt.finish`, called
by both drivers. `ApiKey` already accepts a header name and scheme. `Annotation`,
`Span`, `DeltaAnnotation`, server-tool response parts, `ProviderRef` replay lanes,
and per-part `CacheHint` also exist. This program extends and qualifies them.

WU-34/35 belong to the separate platform MVP track. This program owns WU-36–70.
The plan PR is WU-36 only: future WU entries are contracts, not implementation.
Execute entries in dependency order with one WU per branch and PR. Stacked PRs
are permitted: a dependent WU targets its predecessor branch so its diff contains
only its own changes. Keep the stack rooted in current main; after a predecessor
merges, rebase and retarget its successor onto main before merging it.
Dependencies remain implementation prerequisites; they need not have merged before
a dependent draft starts. Each WU is reviewed and merged separately.
No TypeScript/Go implementation, gateway HTTP serving, identity administration,
budget enforcement, persistence, agent orchestration, or other platform MVP work
is included. The first satellites here are independently packaged libraries.
For any generic capability interface beyond chat, the maintainer must first review
and explicitly approve its design, public API, schemas and architecture. Roadmap
approval is not that design approval; implementation waits for that separate review.

[ADR 0005](../decisions/0005-revised-freeze-gate.md) remains the release gate.
[ADR 0007](../decisions/0007-governed-execution.md) remains the execution boundary.
[The proposed integration ADR](../decisions/0008-integration-contract-additions.md)
must have the relevant portion accepted before a WU changes a frozen-candidate
surface; the maintainer authorized WU-37 after PR #27 and WU-38 after PR #30
merged. The remaining proposals still await acceptance. All additions
remain optional/open and preserve existing serialized forms and constructors.
There is no canonical-node promotion or ordered-item migration in this program.
The stale semver-based freeze wording in procedure templates does not override
ADR 0005. A rejected ADR proposal blocks its dependent WUs; it is not permission
to choose a different public shape during implementation.

### Common implementation contract

Each Scope owns the named source paths plus its associated tests, fixtures,
extension schemas, architecture sections and status rows. File estimates exclude
mechanical regeneration; stop and split by a plan amendment before exceeding
roughly 40 non-mechanical files or adding a second observable outcome. Shared
files are edited only in the owning sections, in an isolated worktree. Rebase
the stack onto current main before opening each PR. Newly discovered kernel gaps
go in `gaps.md`, not into a widened implementation.

Use `wu-session`, `add-edge` for every changed/new edge, and `record-wire-pair`
for HTTP/SSE recordings. All edge WUs include a per-field census, exact expected
losses AND shifts, unknown-input vectors, catalog routing and certification;
streaming edges additionally include deltas, PART_STOP checks and fold triples
paired with unary recordings. An unsupported advertised feature is an explicit
report/admission result, never an untested claim. New fixture formats are defined
in `spec/README.md` and validated in the same owning WU. No live keys or SDK mocks.
No provider SDKs, no new core dependencies. All non-I/O logic stays sans-io.

Where a dependent survey claim is unverified, the entry's **First step** is
vendor verification, with source URL, date and result in its provider page (or
capability page for convention/catalog claims). These are research steps, not
live API tests. Unconfirmed claims stay excluded; if essential to Done, the WU
is blocked and its Open item is updated. Every WU runs
`uv run python scripts/check.py`, pastes its summary verbatim, and runs
`scripts/privacy_check.py` before pushing. A checked box denotes completed WU
work; each PR still requires its own review and merge.

### Hosting coverage inventory

The roadmap calls this a 16-item growth list, but the linked hosting page does
not enumerate sixteen items. The following explicit sixteen-item decomposition
covers its mapping section together with the Bedrock/Azure requirements; it is
this plan's inventory, not a quotation of a missing list. Existing mechanisms
are preserved and tested, not renamed or replaced.

| # | Mechanism / qualification | Owner | Survey decision source |
|---|---|---|---|
| 1 | Per-host body-version map; retain legacy single tuple | WU-37 | Bedrock §13(a) |
| 2 | Version-header handling separate from feature headers | WU-37 | Bedrock §13(a), Azure §13 |
| 3 | Header-to-body feature mapping (`anthropic_beta`) | WU-37 | Bedrock §13(a) |
| 4 | Explicit path prefix | WU-38 | Hosting, Mapping (a) |
| 5 | Unary/stream operation path remapping | WU-38 | Bedrock §1/13(a) |
| 6 | Static non-secret attribution/feature headers | WU-38 | Hosting, Mapping (a) |
| 7 | Query maps independent of path/version/feature headers | WU-38 | Azure §1/13 |
| 8 | Resource interpolation with safe segment encoding | WU-38 | Bedrock §1 (ARN identifiers) |
| 9 | `profile_key(resource)` without changing transmitted resource | WU-38 | Hosting, Mapping (a) |
| 10 | Explicit `NoCredential`, no ambient auth discovery | WU-38 | Hosting, Mapping (a) |
| 11 | Existing custom-header `ApiKey` and explicit bearer composition | WU-38, WU-55 | Hosting, Mapping (a); Azure §11 |
| 12 | Host-selected framing and streaming envelope contract | WU-39 | Bedrock §6/13(a) |
| 13 | CRC-checked EventStream framing implementation | WU-49 | Bedrock §6/13(a) |
| 14 | `chunk.bytes` unwrap into the existing Anthropic converter | WU-50 | Bedrock §13(a) |
| 15 | Dual `reasoning` / `reasoning_content` decode | WU-44b, WU-58 | Hosting, Mapping (c) |
| 16 | Host error/metadata preservation, including HTTP-200 stream errors | WU-48/56/58/59/60 | Hosting, Mapping (c–d); Azure §13; Bedrock §13 |

Items 15–16 are semantic conversion work owned by plugins, not host-side copies
of codecs. All new hosts depend on the shared foundation WU-37–39. Hosts live in
`ocai.wire`; plugins declare pure traits/data and never import wire or HTTPX.
The stdlib AWS credential lives in an independent `ocai-aws` package importing
core only. Converse lives in a separate `ocai-bedrock` conversion plugin.

## WU-36 — Define the tier 1–2 integration program

- [x] **Status:** complete in this documentation PR; implementation awaits merge.
- **Scope:** This plan, roadmap rows, proposed additive-contract ADR, architecture
  §8 navigation, gap ownership links and the G-04 baseline correction only; no source/spec changes.
- **Done:** The plan structure check passes with exactly one test-shaped Done,
  explicit Deps/Architecture/Freeze/Decision/Open per WU, unique reserved IDs,
  backward-only dependencies and a matching README row for every entry.
- **Deps:** WU-21–33 merged; capability survey PR #24 merged.
- **Architecture:** §8 navigation; §9 gate unchanged.
- **Freeze:** none changed; proposals name `DialectTraits`, credentials/errors,
  chat IR/schemas, `Usage` and `CallContext` for later additive changes.
- **Decision:** Follow the roadmap's tier 1 then tier 2 sequencing; defer tiers
  3–6 and preserve the kernel/satellite split (roadmap, Six-tier sequencing).
- **Open:** The proposed ADR needs review/acceptance; vendor uncertainties below
  are not resolved by merging a plan.

## WU-37 — Declare host-specific dialect versions

- [x] **Status:** complete; merged in PR #30.
- **Scope:** `core/traits.py`, catalog trait snapshots/lock serialization, existing
  Anthropic trait declarations and Vertex envelope; 12–20 files. Add host-keyed
  body versions, distinguish version/feature headers and declarative feature-body
  mapping. Preserve the old tuple and header map with deterministic precedence;
  no new host or edge.
- **Done:** A trait composition regression test passes: identical Anthropic input
  resolves independent Vertex/Bedrock version and beta settings without mutation,
  legacy Vertex output remains identical, and each relevant change alters the lock.
- **Deps:** WU-36; accepted WU-37 host-declaration portion of ADR 0008.
- **Architecture:** §2.9, §4.3, §6, §7.
- **Freeze:** additive `ocai.core.DialectTraits`; no chat shape changes; accepted WU-37 portion of the
  integration ADR covers the legacy-field preservation rule.
- **Decision:** Use a per-host map, never overload the Vertex tuple for Bedrock
  ([Bedrock §13(a)](../providers/amazon-bedrock.md#13-mapping-to-ocai)).
- **Open:** None for WU-37; unsupported mapping conflicts fail at
  composition rather than selecting a silent winner.

## WU-38 — Compose explicit host endpoints and profiles

- [x] **Status:** complete; awaiting implementation PR review/merge.
- **Goal:** Applications compose explicit host endpoints and profile lookup without
  copying provider codecs or exposing credentials to policies.
- **Scope:** `wire/hosting.py`, `runtime/binding.py`, facade preparation, credential
  vocabulary and catalog host data; 20–30 files. Implement inventory 4–11 with
  immutable/snapshotted maps, explicit precedence and prepared-handle identity.
  `NoCredential` is an explicit value; reuse `ApiKey(header=..., scheme=...)`.
  Host profile lookup may normalize variants but wire resource stays verbatim.
- **Done:** A recorded-host composition matrix passes for path/query/header and
  variant inputs, including escaped ARN segments, unchanged legacy bindings,
  uncertain undeclared profile coverage, safe credentials and stale-preflight rejection.
- **Deps:** WU-37 (merged in PR #30); accepted WU-38 portion of ADR 0008.
- **Architecture:** §2.5, §2.9, §3.3–3.4, §4.3, §5–6.
- **Integration:** Wire host values consume pure catalog descriptors; runtime builds
  safe requests, then applies credentials at the transport leaf. Facade preparation
  fingerprints the effective endpoint, headers, query and profile lookup key.
  Modules: `convert/hosts.py`, `wire/hosting.py`, `runtime/binding.py`,
  `runtime/drivers.py`, `chat/facade.py`, and `core/credentials.py`.
- **Freeze:** additive explicit credential value in `ocai.core.credentials`;
  preserve `Credential`/`ApiKey` signatures; no chat IR changes (integration ADR).
- **Decision:** Hosts are composed values with data-driven profiles and no copied
  codec ([Hosting, Mapping (a)](../capabilities/hosting-and-aggregators.md));
  Concrete endpoint/header/profile precedence is recorded in the accepted WU-38
  portion of [ADR 0008](../decisions/0008-integration-contract-additions.md);
  query/version handling follows [Azure §13](../providers/azure-openai.md#13-mapping-to-ocai).
- **Open:** None for the supported composition surface; automatic deployment-to-model
  discovery and secret-bearing static headers are excluded.
- **Area:** wire
- **Priority:** P0
- **Tier:** 1
- **Owner:** Codex

## WU-39 — Select framing independently of semantic conversion

- [x] **Status:** complete; stacked on WU-38 (PR #35), awaiting PR review.
- **Goal:** Hosted providers can select framing independently of semantic codecs,
  while preparation, deadlines and stream ownership still govern execution.
- **Scope:** `wire/hosting.py`, transport/framing contracts, both drivers and facade
  stream plumbing; 15–25 files. Add an optional host framing/envelope selection
  contract with SSE as the legacy default; codecs continue receiving decoded
  events. Include ownership/error propagation tests, not an AWS parser yet.
- **Done:** A transport recording test passes through default SSE and an explicitly
  selected test framing adapter with identical canonical output, closure, deadline,
  credential isolation and approved-configuration behavior in both drivers.
- **Deps:** WU-38.
- **Architecture:** §3.3, §5–6, §8.
- **Integration:** Wire `FramingHost` selects `StreamFraming`; the facade pins its
  configuration, runtime owns one decoder per admitted stream, and decoded events
  enter the existing conversion graph. Modules: `wire/framing.py`, `wire/hosting.py`,
  `runtime/drivers.py` and `chat/facade.py`; plugins retain provider mapping.
- **Freeze:** none changed: `ChatChunk`, `StreamEnd`, `StreamOutcome`, `CallContext`
  and their schemas remain intact; wire protocols are provisional.
- **Decision:** Binary framing belongs beside SSE in wire, semantic decode stays
  in plugins ([Bedrock §6/13(a)](../providers/amazon-bedrock.md)). The optional
  selector, decoder ownership and approval identity are recorded in
  [ADR 0014](../decisions/0014-host-selected-stream-framing.md).
- **Open:** None; any need to change canonical chunk shape becomes a separate gap.
- **Area:** wire
- **Priority:** P0
- **Tier:** 1
- **Owner:** Codex

## WU-40 — Qualify URL citations on canonical text

- [x] **Status:** implemented; stacked PR #77, pending review.
- **Goal:** Canonical text can carry URL citations and local search-result references
  with honest Unicode span validation and preserved malformed evidence.
- **Scope:** `chat/types/annotations.py`, accumulation, canonical schemas and
  unknown/fold fixtures; 12–20 files. Add optional open `kind="url_citation"`
  and source-result reference/native metadata lanes to existing Annotation;
  retain `span`, `url`, `title`, `cited_text`, `file`, `opaque` and DeltaAnnotation.
  Bounds validation is contextual, never an exception-producing total decoder.
- **Done:** Canonical citation conformance passes for Unicode/combining text,
  bounds, unknown kinds and malformed offsets, preserving invalid evidence without
  attributing a false span and yielding identical unary and folded annotations.
- **Deps:** WU-39; accepted integration ADR.
- **Architecture:** §2.6–2.7, §3.1, §3.5, §4.5, §10.
- **Integration:** The chat IR owns Annotation/Span and local SourceResultRef data;
  response validation and stream sealing share contextual text validation.
  Schemas and canonical fixtures qualify decode and fold parity. Provider edge
  qualification remains separate; no provider codec or canonical node changes.
- **Freeze:** additive Annotation/chat response and chunk schemas; Span/DeltaAnnotation
  behavior qualified without removing legacy forms (integration ADR).
- **Decision:** ADR 0008 accepts the additive citation fields and contextual
  validation. Validated code-point spans only; whole-block citations may stay
  unpositioned; marker-only citations stay in extensions
  ([Search §1.3–1.4](../capabilities/web-search-and-retrieval.md)).
- **Open:** Provider offset units remain unverified for some interfaces; no
  OpenAI Responses/Gemini/xAI edge is claimed by this canonical-only WU.
- **Area:** chat IR
- **Priority:** P0
- **Tier:** 1
- **Owner:** Codex

## WU-41 — Admit server-tool definitions on ChatRequest

- [x] **Status:** implemented; stacked PR #80, pending review.
- **Goal:** Portable requests distinguish provider-executed tool intent from
  function definitions, preserving unknown tools and reporting unsupported intent.
- **Scope:** `chat/types/tools.py`, request reader/schema, generic edge census
  fallbacks and canonical/unknown fixtures; 15–25 files. Add a tagged ServerTool
  alternative while preserving existing untagged function Tool payloads. Initial
  first-class fields: kind, allowed/blocked domains and user location; optional
  provider-only controls stay in censused extensions/provider_options.
- **Done:** The request round-trip test passes for mixed function/server tools and
  future tool kinds, and unsupported destinations report the entire server-tool
  intent instead of interpreting it as a function or dropping it.
- **Deps:** WU-40; accepted integration ADR.
- **Architecture:** §3.1, §3.5, §4.2, §7, §10.
- **Integration:** ChatRequest decodes the tool union in chat IR. Provider request
  edges consume it and report unsupported server/unknown entries before execution;
  preflight policies can reject those findings. No tool executor enters core.
- **Freeze:** additive ChatRequest.tools union and tool/request schemas; existing
  function Tool constructors and serialization preserved (integration ADR).
- **Decision:** ADR 0008 records the additive union. Server tools are declared request intent, not client-side execution;
  max_uses/search_context_size remain provider lanes
  ([Search §1.4](../capabilities/web-search-and-retrieval.md)).
- **Open:** None for this union; MCP registry/client execution and Tool.strict/origin
  promotion are excluded and must receive separate WUs if later required.

- **Area:** chat IR
- **Priority:** P0
- **Tier:** 1
- **Owner:** Codex

## WU-42 — Preserve required server-tool replay anchors

- [x] **Status:** implemented; stacked PR #83, pending review.
- **Goal:** Requests preserve scoped continuation data and expose replay failures
  through the conversion ledger before a governed call reaches the provider.
- **Scope:** Existing PartServerToolResult/Annotation reference lanes, request
  continuation anchors, ref guards, canonical schemas and transcript fixtures;
  15–25 files. Add ChatRequest.anchors for request-side continuation (G-01), reuse
  part.anchor/annotation.opaque as ProviderRef carriers, never duplicate opaque
  token strings in a new canonical scalar lane.
- **Done:** A transcript conformance test passes same-scope required-anchor replay
  byte-for-byte and reports/rejects cross-scope or missing required replay before
  provider I/O without losing the original evidence.
- **Deps:** WU-41; accepted integration ADR.
- **Architecture:** §2.4, §3.1, §3.5, §4.5, §10.
- **Integration:** ChatRequest owns optional anchors; existing part/annotation refs
  remain the replay carriers. Request codecs enforce scope and report unavailable
  lanes; public prepared execution applies the caller's fidelity policy. Canonical
  transcript fixtures preserve server-tool tokens; recorded Anthropic thinking
  replay proves the already-qualified wire lane. Search wire replay is WU-43.
- **Freeze:** additive ChatRequest.anchors and request schema; existing ProviderRef,
  part.anchor and Annotation.opaque semantics preserved (integration ADR).
- **Decision:** ADR 0008 accepts request anchors. Encrypted search tokens and continuation ids are scoped replay
  anchors, not portable content ([Search §1.4](../capabilities/web-search-and-retrieval.md));
  this closes the data-carrier part of G-01, not the deferred Responses interface.
- **Open:** None for the canonical contract; provider-specific replay qualification
  remains the responsibility of each codec WU.

- **Area:** chat IR
- **Priority:** P0
- **Tier:** 1
- **Owner:** Codex

## WU-43 — Account for provider-executed search requests

- [ ] **Status:** not started.
- **First step:** Verify the selected Anthropic web-search tool version, replay
  fields and usage increments against vendor docs; record them in its provider page.
- **Scope:** Anthropic request/response/stream edges and extension census, search
  usage vocabulary/spec plus HTTP/SSE and fold/transcript fixtures; 25–35 files.
  Qualify one web-search version, valid whole-block citations, required encrypted
  replay and in-band tool failure. Other search/fetch versions remain unsupported.
- **Done:** A recorded Anthropic search transcript passes unary/stream fold parity
  with typed server tools, validated citations, exact replay and a `search_requests`
  consumption count that is neither token-counted nor inferred from tool-call count.
- **Deps:** WU-40–42; accepted integration ADR.
- **Architecture:** §2.8, §3.1, §4.2/4.5, §7, §10.
- **Freeze:** additive open Usage consumption unit `search_requests` and its spec;
  no new part type or revision (integration ADR).
- **Decision:** Billable search operations and visible server-tool calls are
  different counts ([Search §1.1/1.4](../capabilities/web-search-and-retrieval.md)).
- **Open:** Tool-version verification is a start gate; a version that cannot fit
  the existing parts is a gap, not authority to promote ordered-item IR.

## WU-44a — Declare the DeepSeek compatible interface variant

- [ ] **Status:** not started.
- **First step:** Verify the chosen model ids and Chat Completions revision,
  recording sourced endpoint/profile facts in `providers/deepseek.md`.
- **Scope:** DeepSeek interface descriptor, traits/profile data and independently
  attributable non-serveable nodes, sharing existing OpenAI wire structures;
  8–14 files. No payload edge or new codec implementation in this WU.
- **Done:** An installed-fragment identity test passes DeepSeek provenance and
  deterministic lock composition while proving its descriptor-only nodes are
  not yet eligible for public chat execution.
- **Deps:** WU-43.
- **Architecture:** §2.1/2.5/2.9, §4.3, §7, §10.
- **Freeze:** none changed: provider interface nodes only; canonical nodes,
  ChatRequest/PartReasoning and their schemas stay intact.
- **Decision:** Share the compatible wire implementation but preserve DeepSeek
  vendor identity and replay scope ([DeepSeek §13(a)](../providers/deepseek.md));
  declaring the graph identity and certifying its edges are separate WUs.
- **Open:** Model names and retirement dates require verification before pinning;
  no model lifecycle claim is inherited from a compatible OpenAI model.

## WU-44b — Certify the DeepSeek compatible dialect variant

- [ ] **Status:** not started.
- **First step:** Verify selected model ids, thinking/tool replay rules, error
  envelopes and supported parameters; record results in `providers/deepseek.md`.
- **Scope:** Existing Chat Completions codec's pure dialect configuration,
  DeepSeek traits/profiles and unary edge census/fixtures; 20–30 files. Share the
  mapping implementation, using WU-44a’s separately declared DeepSeek nodes
  and contracts so provider identity and replay scope do not masquerade as OpenAI.
  No host-specific semantic mapping in wire; no new interface family.
- **Done:** Unary conformance passes text/tools/JSON-object/reasoning and unknown
  inputs, proving all prior reasoning_content required by tool histories replays
  verbatim and unavailable required reasoning is UNSUPPORTED before sending.
- **Deps:** WU-44a.
- **Architecture:** §2.4–2.5, §3.5, §4.2–4.3, §7.
- **Freeze:** none changed: PartReasoning, ProviderRef, ChatRequest and Usage
  retain their existing shapes; new provider variant nodes are not canonical nodes.
- **Decision:** Reuse the OpenAI-compatible codec with DeepSeek traits/profiles
  ([DeepSeek §13(a–c)](../providers/deepseek.md)); distinct effect declarations
  cover ignored knobs and effort aliases without clamping input values.
- **Open:** Model retirement dates and native error codes are unverified; no
  pin/code-dependent support claim ships until the first step resolves it.

## WU-45 — Qualify DeepSeek unary execution

- [ ] **Status:** not started.
- **Scope:** DeepSeek binding/front-door data and recorded HTTP pairs through the
  public facade; 8–15 files. Pattern replay of WU-14a, using WU-44b conversions,
  declared profile coverage and explicit credentials; no new conversion edge.
- **Done:** Recorded sync/async DeepSeek calls pass through public preparation and
  execution with exact wire payload, reasoning replay, usage and fidelity evidence,
  including zero-I/O rejection of incomplete tool history.
- **Deps:** WU-44b.
- **Architecture:** §3.3–3.4, §7–8.
- **Freeze:** none changed: chat port/IR, CallContext, credentials and schemas stay intact.
- **Decision:** Missing tool-history reasoning is a correctness failure, not a
  summary substitution ([DeepSeek §5/7/13](../providers/deepseek.md)).
- **Open:** None once WU-44b's verified subset is fixed; FIM, media, Responses and
  Anthropic compatibility routes are excluded.

## WU-46 — Qualify DeepSeek streaming

- [ ] **Status:** not started.
- **Scope:** DeepSeek-configured Chat Completions transducer, census, SSE pairs and
  fold triples; 15–25 files. Reasoning/content/tool deltas, keepalives, final-content
  usage, error/truncation evidence and all four public call faces.
- **Done:** Recorded DeepSeek SSE passes fold parity against paired unary responses with usage on
  the final content chunk retained alongside finish, exact tool identity/order and
  reasoning, and incomplete streams never gain a successful terminal record.
- **Deps:** WU-45.
- **Architecture:** §3.1, §4.1–4.2/4.5, §7–8.
- **Freeze:** none changed: ChatChunk/StreamEnd/deltas and their schemas remain intact.
- **Decision:** Usage is not required to arrive in a separate empty-choices chunk
  ([DeepSeek §6/13](../providers/deepseek.md)); pattern replay of WU-14b.
- **Open:** None for verified SSE; unknown finish values retain native strings.

## WU-47 — Sign independent transport attempts with SigV4

- [ ] **Status:** not started.
- **First step:** Verify Bedrock canonical URI/query/header rules and whether
  content-sha256 is required; record sourced answers in `providers/amazon-bedrock.md`.
- **Scope:** Independent `python/packages/ocai-aws` credential package using only
  stdlib/core, explicit access/secret/session-token inputs and per-attempt signing;
  10–18 files. Official synthetic signing vectors and recorded retry requests.
- **Done:** A signing-vector/recording test passes exact authorization for fixed
  clocks and payload bytes across sync/async retries while all hooks, observers,
  retained references and reprs remain free of credentials.
- **Deps:** WU-46.
- **Architecture:** §2.9, §5–7.
- **Freeze:** none changed: existing Credential protocol/ApiKey and request/result
  contracts remain intact; SigV4Credential is an external implementation.
- **Decision:** HMAC/SHA-256 are stdlib, no AWS SDK/signing dependency
  ([Bedrock §11/13(b)](../providers/amazon-bedrock.md)); no implicit IMDS/env/STS
  discovery. Token refresh is explicit caller-supplied state, outside this WU.
- **Open:** Signing verification is required before implementation; no speculative
  header requirement becomes a permanent signing rule.

## WU-48 — Host Anthropic unary calls on Bedrock InvokeModel

- [ ] **Status:** not started.
- **First step:** Verify selected model/profile identifiers and InvokeModel feature
  header/body and error behavior; record results in the Bedrock provider page.
- **Scope:** `wire.hosting.Bedrock` and InvokeModel envelope, Anthropic declarative
  trait data and host metadata/error preservation; 18–28 files with recorded pairs.
  Move model to the encoded path, select Bedrock version, relocate beta to body;
  preserve host metadata through registered extensions, never copy codec mappings.
- **Done:** A recorded Anthropic-on-Bedrock unary test passes both drivers with
  exact signed envelope, canonical response/fidelity/usage and exception-name-based
  errors, including distinction between blocked and masked successful output.
- **Deps:** WU-47.
- **Architecture:** §2.9, §3.3, §5–7.
- **Freeze:** none changed: existing traits/reference/error contracts are consumed;
  added host extension schemas do not redefine canonical shapes.
- **Decision:** InvokeModel is an envelope over Anthropic, not a new semantic
  interface ([Bedrock §13(a/c/d)](../providers/amazon-bedrock.md)).
- **Open:** Runtime/mantle compatibility routes and regional availability discovery
  are excluded; only verified InvokeModel identifiers enter fixtures.

## WU-49 — Parse AWS EventStream without I/O

- [ ] **Status:** not started.
- **Scope:** `wire/eventstream.py`, framing adapter and a binary recording format
  extension described in spec; 12–20 files. Parse typed headers, bounded lengths,
  prelude/message CRCs, fragmented bytes, unknown event kinds and truncation.
  Record binary bodies as encoded bytes with explicit encoding; no AWS SDK mocks.
- **Done:** Recorded binary vectors pass every chunk-boundary split and CRC/length
  corruption case, producing identical typed frames or explicit framing failure
  without unbounded allocation or invented completion.
- **Deps:** WU-48 (and framing contract WU-39).
- **Architecture:** §6, §10.
- **Freeze:** none changed: wire parser is provisional; canonical IR, deltas and
  schemas are untouched; the new recording format is not a canonical revision.
- **Decision:** EventStream is a CRC-checked sans-io sibling of SSE
  ([Bedrock §6/13(a)](../providers/amazon-bedrock.md)).
- **Open:** None; unknown semantic event payloads remain available to the codec,
  whereas corrupt framing fails explicitly.

## WU-50 — Stream Anthropic through Bedrock envelopes

- [ ] **Status:** not started.
- **Scope:** Bedrock InvokeModel streaming envelope/operation paths and existing
  Anthropic transducer integration, censuses for affected host fields, binary
  recordings and fold triples; 15–25 files. Unwrap chunk.bytes without buffering
  complete output and map typed exception events to the rule-8 shape.
- **Done:** Recorded binary Anthropic streams pass fold parity against paired InvokeModel unary
  responses with exact usage/replay evidence, and close/cancellation/mid-stream
  exceptions release transport resources while preserving partial accounting.
- **Deps:** WU-49.
- **Architecture:** §3.3, §4.5, §5–7, §10.
- **Freeze:** none changed: StreamEnd/StreamOutcome/ChatChunk and schemas remain intact.
- **Decision:** Reuse Anthropic semantics after envelope decoding
  ([Bedrock §6/13(a/d)](../providers/amazon-bedrock.md)); no streaming restart.
- **Open:** None for InvokeModel; SSE behavior of compatibility routes stays
  unverified and excluded.

## WU-51 — Declare the Bedrock Converse interface

- [ ] **Status:** not started.
- **First step:** Verify the chosen Converse revision, supported block/parameter
  subset and structured-output schema; record evidence in the Bedrock page.
- **Scope:** `ocai-bedrock` package metadata, pure wire structs, interface descriptor,
  traits, non-serveable nodes and profile declarations; 10–18 files. No payload
  edges or front-door execution yet; separate interface admission from conversion.
- **Done:** An installed-wheel catalog test passes deterministic Converse identity
  and unknown wire decoding while proving a descriptor-only interface cannot be
  selected as a serveable chat implementation.
- **Deps:** WU-50.
- **Architecture:** §2.1, §4.3, §7, §10.
- **Freeze:** none changed: new provider nodes only; no canonical node/shape/schema changes.
- **Decision:** Converse is Bedrock's own interface, not Anthropic under another
  host ([Bedrock §13(a)](../providers/amazon-bedrock.md)).
- **Open:** Structured-output members are unverified; exclude that feature unless
  verification settles its wire schema before the supported matrix is fixed.

## WU-52 — Certify Converse unary conversion

- [ ] **Status:** not started.
- **Scope:** Converse request/response codecs, contracts, extension census and golden
  fixtures; 25–35 files. Text, function tools, signed reasoning, finish, usage and
  guardrail metadata form the initial matrix; unknown blocks remain opaque.
  Media, managed prompts/system tools and unverified structured output are excluded.
- **Done:** Converse unary certification passes canonical round trips on the
  supported matrix with required signature replay, disjoint cache accounting and
  explicit masked-output shifts, and runtime findings stay within every census.
- **Deps:** WU-51.
- **Architecture:** §2.4/2.8, §3.1, §4.2/4.5, §7.
- **Freeze:** none changed: consumes existing parts and open usage dimensions;
  cache writes use the open `cache_write` code pending WU-66's named constant.
- **Decision:** Converse inputTokens excludes cache reads/writes; cache and output
  masking semantics must be reported ([Bedrock §8/13(c)](../providers/amazon-bedrock.md)).
- **Open:** None for verified subset; out-of-range temperature passes verbatim
  with APPROXIMATED evidence, never a silent clamp.

## WU-53 — Execute Converse unary through public APIs

- [ ] **Status:** not started.
- **Scope:** Converse facade factory/front-door registration and Bedrock operation
  composition with recorded HTTP pairs; 8–15 files. No additional semantic edge.
- **Done:** A recorded sync/async public API test passes Converse preparation,
  signed wire execution and response conversion with correct route/profile
  uncertainty and zero provider calls for forbidden conversion findings.
- **Deps:** WU-52.
- **Architecture:** §3.3–3.4, §6–8.
- **Freeze:** none changed: chat port, preparation contract, CallResult and schemas
  are used without new fields.
- **Decision:** Resource routing remains host data; capability facts are model-specific
  ([Bedrock §1/13(a)](../providers/amazon-bedrock.md)).
- **Open:** None; cross-region routing policy and account enablement belong to callers.

## WU-54 — Certify Converse streaming conversion

- [ ] **Status:** not started.
- **Scope:** Converse stream codec, EdgeContract, binary pairs/fold triples and
  façade registration; 20–30 files. Match WU-52's matrix with indexed tool deltas,
  reasoning/signatures, metadata after messageStop and exception events.
- **Done:** Converse binary streams pass fold conformance against paired unary
  responses, retaining post-messageStop usage and all partial error evidence
  without generating successful StreamEnd before terminal metadata is consumed.
- **Deps:** WU-53.
- **Architecture:** §3.1, §4.1–4.2/4.5, §6–8, §10.
- **Freeze:** none changed: existing chat chunks/deltas/StreamEnd and schemas suffice;
  any missing part/delta is a new gap, not an implicit scope extension.
- **Decision:** messageStop is not the end of accounting
  ([Bedrock §6](../providers/amazon-bedrock.md#6-streaming)).
- **Open:** None within the unary matrix; media deltas and server-tool expansion defer.

## WU-55 — Host Chat Completions on Azure v1

- [ ] **Status:** not started.
- **First step:** Verify v1 endpoint families, api-version behavior and Entra scope
  for each selected resource family; record the conflicting-scope resolution in
  `providers/azure-openai.md` without guessing a universal scope.
- **Scope:** Azure host data/composition, deployment profile hint and explicit
  api-key or supplied Entra bearer credential; 12–20 files with recorded pairs.
  Existing ApiKey machinery supplies both header modes; no token acquisition SDK.
- **Done:** An Azure v1 recorded-call matrix passes identical canonical requests
  using either api-key or Entra bearer auth, exact deployment body/path/query
  selection and credential isolation on every applicable hook/observer.
- **Deps:** WU-54.
- **Architecture:** §2.5/2.9, §3.4, §6–7.
- **Freeze:** none changed: Credential/ApiKey, ChatRequest and CallContext are reused.
- **Decision:** Azure v1 is a host of existing codecs; model is a deployment name
  ([Azure §1/11/13](../providers/azure-openai.md)).
- **Open:** Entra scopes require verification; legacy dated deployment APIs, token
  acquisition, and user_security_context inference from governance context are out.

## WU-56 — Preserve Azure content-filter evidence in streams

- [ ] **Status:** not started.
- **Scope:** Chat Completions host-qualified decode, Azure content-filter extension
  census, HTTP/SSE recordings and fold triples; 15–25 files. Preserve prompt/choice
  annotations and async filter offsets, including leading empty-choices events.
- **Done:** Azure paired recordings pass fold conformance with content-filter
  annotations/offsets retained and output-withheld shifts visible, while malformed
  or late filter events never invent content, zero usage or retracted delivery.
- **Deps:** WU-55.
- **Architecture:** §3.1, §4.2/4.5, §7–8.
- **Freeze:** none changed: extensions on existing response/chunk shapes only;
  no alteration to successful StreamEnd or partial-result semantics.
- **Decision:** Asynchronous filters can arrive after delivered tokens; disclose
  that fact rather than promising pre-delivery safety
  ([Azure §6/13(c)](../providers/azure-openai.md)).
- **Open:** None for recorded v1 filtering; unsupported future fields are preserved.

## WU-57 — Honor Azure millisecond retry hints

- [ ] **Status:** not started.
- **First step:** Verify retry-after-ms precedence relative to Retry-After on the
  selected Azure surface and record the result in its provider page.
- **Scope:** Pure error/retry hint normalization and wire-policy recordings;
  8–12 files. Convert milliseconds to seconds explicitly; preserve original
  evidence and whole-call deadline semantics; no proactive rate limiter yet.
- **Done:** A virtual-clock recorded retry test passes valid, conflicting, malformed
  and expired Azure hints with identical sync/async attempt counts and no attempt
  after the logical deadline.
- **Deps:** WU-56.
- **Architecture:** §2.3, §5–6, §8.
- **Freeze:** none changed: Retry/CallContext/error contracts retain their shapes.
- **Decision:** Azure retry-after-ms is a pacing signal, never a deadline extension
  ([Azure §11/13](../providers/azure-openai.md)).
- **Open:** Header precedence is a verification gate; no undocumented guess ships.

## WU-58 — Qualify vLLM as an existing-codec host

- [ ] **Status:** not started.
- **First step:** Verify selected vLLM version and parser/configuration requirements
  for tools, reasoning, structured output and usage; add a sourced provider page.
- **Scope:** vLLM host/profile data, shared Chat Completions dual reasoning decoder,
  HTTP-200 error decode and censused extensions with paired HTTP/SSE fixtures;
  20–30 files. No new graph interface; no parsing of inline think markers.
- **Done:** A recorded vLLM host matrix passes both reasoning spellings, tool
  identity/order and usage fold parity, and converts an HTTP-200 stream failure
  into the canonical code/native/retryable error shape rather than successful text.
- **Deps:** WU-57 (reuse WU-44b's reasoning variant support).
- **Architecture:** §2.5, §4.2/4.5, §6–7.
- **Freeze:** none changed: PartReasoning and stream error contracts stay intact.
- **Decision:** Parser-dependent support is profile data; preserve source spelling
  and unknown fields ([Hosting, vLLM; Mapping (a/c)](../capabilities/hosting-and-aggregators.md)).
- **Open:** The selected release/configuration must be pinned by verification;
  native Ollama, TGI and unrelated server configurations are excluded.

## WU-59 — Distinguish exhausted credit from authentication failure

- [ ] **Status:** not started.
- **Scope:** Core open error vocabulary and tested provider mappings for qualified
  402 payment failures, including DeepSeek and OpenRouter; 10–16 files. Preserve
  status/native codes and raw evidence outside observer events; no blanket mapping
  of every authorization/billing failure from message substrings.
- **Done:** Recorded payment failures pass taxonomy tests as non-retryable
  `payment_required`, distinct from AuthError and transient rate limits, while
  unknown provider codes retain native evidence without decode failure.
- **Deps:** WU-58; accepted integration ADR.
- **Architecture:** §2.9, §5–7.
- **Freeze:** additive payment_required error code/constant in core taxonomy;
  no existing error code renamed (integration ADR).
- **Decision:** Prefer the common billing distinction explicitly requested by the
  maintainer and [Hosting, Mapping (d)](../capabilities/hosting-and-aggregators.md)
  over DeepSeek §13(e)'s older suggestion to classify 402 as authentication.
- **Open:** None for verified 402 recordings; additional billing statuses need evidence.

## WU-60 — Qualify OpenRouter as an existing-codec host

- [ ] **Status:** not started.
- **First step:** Verify the chosen Chat Completions route, final usage/finish
  duplication, metadata and error envelopes; record them in a new provider page.
- **Scope:** OpenRouter host/profile data and existing codec extension/error paths,
  HTTP/SSE fixtures and fold triples; 20–30 files. Preserve usage.cost/cost_details,
  provider selection/attempt metadata, reasoning_details and native finish values
  in registered extensions. Reuse reasoning dual decode and payment taxonomy.
- **Done:** Recorded OpenRouter streams pass fold parity with one logical finish,
  measured usage counted once, reported cost/provider metadata preserved and
  HTTP-200 errors surfaced with partial evidence instead of success.
- **Deps:** WU-59.
- **Architecture:** §2.5/2.8, §4.2/4.5, §6–7.
- **Freeze:** none changed: Usage/Route/chat IR shapes remain intact; host cost stays
  in censused extensions until an explicit cost adapter consumes it.
- **Decision:** Variant normalization affects profile lookup only; routing controls
  stay provider_options ([Hosting, OpenRouter; Mapping (a/c/d)](../capabilities/hosting-and-aggregators.md)).
- **Open:** Anthropic-compatible routing and transform/plugin schemas are unverified
  and excluded; provider-reported cost is not a first-party price estimate.

## WU-61 — Carry inbound trace context explicitly

- [ ] **Status:** not started.
- **Scope:** Optional typed TraceContext(traceparent, tracestate) on CallContext,
  snapshots/observer projection and correlation documentation; 12–18 files. No
  baggage export or automatic provider-header propagation; no OTel dependency.
- **Done:** Concurrent recorded calls pass context propagation tests joining each
  authorized observer to its supplied trace context while credentials, arbitrary
  context bags and trace fields never enter provider bodies or headers.
- **Deps:** WU-60; accepted integration ADR.
- **Architecture:** §2.3, §5, §8–9.
- **Freeze:** additive CallContext.trace_context and stdlib TraceContext vocabulary;
  existing call/parent/correlation ids preserved (integration ADR).
- **Decision:** G-04 needs inbound trace context, not a second invocation-id system
  ([Observability §3/5](../capabilities/observability.md)); document generated
  32-lowercase-hex UUID ids and caller responsibility for supplied-id uniqueness.
- **Open:** None for transport: the exporter validates W3C syntax and decides
  whether to join; invalid context does not authenticate or fail a model call.

## WU-62 — Observe stream progress and terminal evidence

- [ ] **Status:** not started.
- **Scope:** `runtime.observe`, observed chat wrapper and metadata-only event
  tests; 12–20 files. Add first-chunk timing and StreamEnded usage/finish/report
  with outcome, without buffering chunks. Qualify existing WireExchanged emission
  rather than adding a duplicate site; update the remaining G-04 evidence.
- **Done:** A concurrent recorded-stream lifecycle test passes one documented
  terminal outcome per started invocation, correct first-chunk/attempt correlation
  across denial, unconsumed close, cancellation and failure, with passive observer
  errors and no event containing credentials or payload bodies.
- **Deps:** WU-61.
- **Architecture:** §3.3, §5, §8–9.
- **Freeze:** none changed: core StreamOutcome, CallContext, chat chunks and
  StreamEnd unchanged; additive provisional Observer event variants only.
- **Decision:** Existing CallFinished remains the invocation terminal; StreamEnded
  adds stream accounting without finalizing twice; pending lazy streams follow
  ADR 0007 ([Observability §3–5](../capabilities/observability.md)).
- **Open:** None; content capture and durable audit are deliberately excluded.

## WU-63 — Export metadata through the first OTel satellite

- [ ] **Status:** not started.
- **First step:** Verify and pin an official GenAI convention revision, attribute
  names and inbound context semantics; record them in the observability page.
- **Scope:** Independent `ocai-otel` package, Observer adapter, offline recorded
  export expectations and package/boundary checks; 15–25 files. OTel API dependency
  only at runtime; SDK/collector export configured by the consumer. Inference and
  physical-attempt spans include route, usage, fidelity and stream timing metadata.
- **Done:** An installed-satellite recorded-call test passes parent-trace joining,
  attempt child spans and terminal usage/fidelity projection for unary/stream
  success and cancellation, with no content/credential export and no outcome
  change when the observer/export backend fails.
- **Deps:** WU-62.
- **Architecture:** §5, §9, §12.
- **Freeze:** none changed: uses public Observer and CallContext contracts; no
  data-contract schema additions or automatic hook freeze.
- **Decision:** OTel-first passive export with a pinned convention revision and
  ocai.* fields for facts with no standard equivalent
  ([Observability §4–6](../capabilities/observability.md)); ADR 0007's metadata-only
  events supersede the survey's obsolete payload-bearing event descriptions.
- **Open:** Unstable convention names require verification; payload opt-in,
  archive refs, vendor adapters and metrics are follow-up scope, not hidden TODOs.

## WU-64 — Load model descriptors as attributable profile data

- [ ] **Status:** not started.
- **First step:** Verify the selected OpenAI/Anthropic model endpoint fields and
  source provenance; record supported facts in the model-catalog/provider pages.
- **Scope:** Descriptor JSON Schema/data under `spec/interfaces`, pure loader into
  CapabilityProfile and lock identity, explicit pricing/provenance sibling data;
  18–28 files. Start with OpenAI/Anthropic fixtures, unknown coverage by default.
- **Done:** Descriptor conformance passes immutable deterministic profile loading,
  source/confidence/evidence distinctions and hash changes for relevant fact/price
  changes, while catalog-only support never becomes proof of qualified behavior.
- **Deps:** WU-63.
- **Architecture:** §2.5, §4.3/4.5, §10.
- **Freeze:** none changed: CapabilityProfile is provisional, core Usage/Route and
  canonical schemas unchanged; descriptor schema is separate from chat IR.
- **Decision:** Versioned descriptors under spec feed existing feature keys, with
  independently identified pricing data; lock hashes declarations, not artifact
  reproducibility ([Model catalog, Proposal/Shape](../capabilities/model-catalog.md)).
- **Open:** None for the schema; unverified fields stay absent. A pricing data
  identity must be included explicitly rather than claiming today's lock already
  hashes arbitrary descriptor contents.

## WU-65 — Refresh model facts into reviewable diffs

- [ ] **Status:** not started.
- **Scope:** Explicit refresh script, recorded model-list inputs, descriptor
  consistency checker and provenance docs; 10–18 files. No import-time/network
  refresh; test every declared NATIVE/ABSENT evidence link against matching fixtures.
- **Done:** An offline refresh test passes deterministic descriptor diffs and
  rejects missing/stale or model-mismatched qualification evidence without promoting
  catalog-only claims into certified profiles.
- **Deps:** WU-64.
- **Architecture:** §2.5, §4.5, §10.
- **Freeze:** none changed: no core/chat contract additions; descriptor data and
  its provisional loader only.
- **Decision:** Human-reviewed refresh, provider facts ahead of third-party claims
  ([Model catalog, Refresh cadence and verification](../capabilities/model-catalog.md)).
- **Open:** None for recorded OpenAI/Anthropic inputs; LiteLLM data licensing is
  unverified and its importer is excluded.

## WU-66 — Name cache-write consumption explicitly

- [ ] **Status:** not started.
- **Scope:** UsageSource.CACHE_WRITE, usage schema/docs and Anthropic/Bedrock
  consumption census/fixtures; 12–20 files. Preserve legacy provider-specific
  evidence without counting it twice; per-TTL splits use registered extensions.
- **Done:** Cache-accounting conformance passes Anthropic and Converse unary/stream
  fixtures with disjoint input/read/write/output buckets, truthful missing usage
  and preserved per-TTL evidence without duplicate billable consumption.
- **Deps:** WU-65; accepted integration ADR.
- **Architecture:** §2.8, §3.1, §4.2/4.5, §7, §10.
- **Freeze:** additive core UsageSource.CACHE_WRITE and usage schema vocabulary;
  old open codes remain readable (integration ADR).
- **Decision:** Cache writes are a distinct bucket before hint execution ships
  ([Caching §4.2](../capabilities/caching-cost-and-rate-limits.md)).
- **Open:** None; no OpenAI Responses cache-write support is inferred from Bedrock docs.

## WU-67 — Add a request-level cache hint without replacing CacheConfig

- [ ] **Status:** not started.
- **Scope:** Optional ChatConfig.cache_hint: CacheHint, config/schema readers and
  canonical fixtures; 10–16 files. Retain cache: CacheConfig and per-part markers.
  Request hint means requested automatic placement/TTL, never a fabricated hit;
  conflicting off/explicit policies are rejected during preparation, not decode.
- **Done:** Canonical cache-intent tests pass old request round trips and the new
  hint with explicit precedence/conflict behavior, including unknown TTL tokens
  retained for destination reporting and no automatic caching request when absent.
- **Deps:** WU-66; accepted integration ADR.
- **Architecture:** §3.1, §3.5, §4, §10.
- **Freeze:** additive ChatConfig.cache_hint and config/request schemas; existing
  CacheConfig and per-part CacheHint retained (integration ADR).
- **Decision:** The maintainer explicitly requests CacheHint on ChatConfig; it
  complements the survey's existing per-part marker and mode/ref lanes
  ([Caching §3/4.1](../capabilities/caching-cost-and-rate-limits.md)).
- **Open:** ADR review must accept the proposed request-level meaning; a plan
  merge alone does not settle contradictory placement intent.

## WU-68 — Execute Anthropic prompt-cache intent honestly

- [ ] **Status:** not started.
- **First step:** Verify top-level automatic cache_control, supported TTLs and
  breakpoint interactions; record the selected subset in the Anthropic provider page.
- **Scope:** Anthropic request/decode/stream censuses and cache fixtures; 15–25 files.
  Map config/per-part hints to supported cache_control, retain unsupported intent
  with findings and move exercised config.cache census rows from DROPPED to their
  justified dispositions. Include automatic and explicit placement recordings.
- **Done:** Recorded Anthropic cache calls pass exact request assertions and fold
  parity for measured reads/writes, with no silent TTL clamping, no fabricated hit
  when usage is missing, and runtime findings bounded by the updated census.
- **Deps:** WU-67.
- **Architecture:** §3.1/3.5, §4.2/4.5, §7.
- **Freeze:** none changed: consumes WU-67's additive config fields and WU-66 usage;
  no further canonical shape changes.
- **Decision:** Cache hints are opt-in provider knobs; read/write prices and
  placement differ ([Caching §2/4.1–4.2/5](../capabilities/caching-cost-and-rate-limits.md)).
- **Open:** None after vendor verification; Responses and Gemini cache lifecycle
  are deferred, and one provider's hint support does not itself earn a freeze.

## WU-69 — Price measured usage in a cost satellite

- [ ] **Status:** not started.
- **First step:** Verify selected provider price units/tier rules and any models.dev
  fields used by the reference loader; record source/date in the catalog page.
- **Scope:** Independent `ocai-cost` package, explicit pricing-table protocol over
  WU-64 descriptors, port middleware and recorded unary/stream accounting tests;
  15–25 files. No live price fetch, budgets or tenant billing store. Price estimates
  and OpenRouter-reported cost remain distinct evidence, never added together.
- **Done:** A cost-interceptor test passes measured input/output/cache-read/write
  dimensions against a pinned table for unary and partial streams, preserving
  original Usage and reporting incomplete/unpriced dimensions instead of zero cost.
- **Deps:** WU-64–68.
- **Architecture:** §2.8, §5, §12.
- **Freeze:** none changed: existing Consumption open dimensions and extensions;
  no kernel price table or CallResult schema addition.
- **Decision:** Pricing is a satellite lookup; descriptor facts supply provenance
  ([Caching §4.5](../capabilities/caching-cost-and-rate-limits.md);
  [Model catalog, Shape](../capabilities/model-catalog.md)).
- **Open:** None for explicit pinned prices; negotiated rates, taxes, budgets and
  automatic catalog refresh are caller responsibilities.

## WU-70 — Pace requests from measured rate-limit signals

- [ ] **Status:** not started.
- **First step:** Verify selected OpenAI/Anthropic header formats and spend-limit
  signals; record sourced examples in the corresponding provider pages.
- **Scope:** `wire.policies.RateLimitPolicy`, pure RateState/header normalization
  and explicit in-process backend, recorded pairs and virtual-clock tests;
  15–25 files. Reuse WU-57 millisecond handling and existing deadline budget.
- **Done:** Recorded pacing tests pass concurrent sync/async admission and server
  backoff without counting admission waits as provider attempts, leaking credentials
  or scheduling another attempt beyond the caller's deadline.
- **Deps:** WU-69.
- **Architecture:** §2.3, §5–6, §8.
- **Freeze:** none changed: existing CallContext/Decision contracts stay intact;
  RateState/backend protocols remain provisional wire machinery.
- **Decision:** Provider pacing belongs at wire tier; tenant budgets do not
  ([Caching §4.4/5](../capabilities/caching-cost-and-rate-limits.md)).
- **Open:** None for the verified two-provider subset; distributed limiters and
  undocumented Bedrock headers are excluded.

## Deferred work and market verification

The six-tier roadmap is preserved: retrieval capabilities (tier 3), Responses /
Interactions and other new-generation surfaces (tier 4), jobs/files (tier 5),
and registry/agent execution (tier 6) need their own programs. This does not
remove Responses or ordered-item qualification from ADR 0005. The ongoing MVP
track can consume merged public contracts without moving service features here.
Exact/semantic response caches, content telemetry, vendor exporters and catalog
imports beyond the qualified subset are not implied by tier-2 completion.

The roadmap's "Market changes worth knowing" section is dated research, not a
reason to implement deprecated surfaces or silently drop compatibility. Reverify
vendor retirement/migration claims when selecting a future interface; no model
retirement date, pricing number or unstable convention is hard-coded by this plan.
