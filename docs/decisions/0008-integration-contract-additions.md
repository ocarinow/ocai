# 0008 — Additive integration contracts before the qualification gate

- **Status:** WU-37–38 and WU-40–42 chat additions accepted; remaining proposals pending
- **Date:** 2026-11-10
- **Deciders:** maintainer authorized WU-37 after PR #27 and WU-38 after PR #30
  merged; directed execution of assigned integration WUs on 2026-11-11.
  WU-40–42 acceptance is recorded here; other implementation portions remain pending.

## Context

The [capability roadmap](../capabilities/README.md) selects chat completeness,
enterprise hosts and observability as tiers 1–2. The merged gateway mechanisms
already provide the enforcement and lifecycle boundary in ADR 0007. Several
survey recommendations need additive changes to frozen-candidate core/chat
contracts before provider plugins or satellites can use them honestly.

This proposal accompanies WU-36 in the [integration program](../plans/integration-program.md).
The plan did not implement or accept its own decisions. The maintainer
subsequently authorized WU-37 and WU-38; acceptance below is limited to their
host-declaration, composition and explicit no-auth surfaces. ADR 0005
remains the freeze gate; neither a library semver nor merging this plan earns
qualification. The active canonical revision stays 2026-07. ADR 0003's
ordered-item candidate and the required Responses migration remain separate work.

## Proposed decision

Accept the following bounded additions through their owning WUs. Every addition
is optional/open, stdlib-only in core, and omit-absent. Preserve old field names,
constructor behavior and serialized payloads when the new feature is absent.
Each implementation includes schema/unknown-input evidence and the affected
edge contracts; a plan cannot authorize removing a legacy field.

### Host declarations and composition (WU-37–38 accepted)

Add host-keyed body-version declarations and separate version-header versus
feature-header handling to DialectTraits. Keep cloud_body_version and
first_party_headers as legacy fallbacks. A host-specific explicit declaration
wins over its legacy fallback; contradictory explicit declarations fail
composition. Feature-to-body mappings are declared data, not provider field
mapping duplicated in hosts. Binding overrides apply only to non-secret headers;
credential application remains the driver leaf after hooks on an independent
request. Snapshot all maps and include relevant host/trait configuration in
catalog or prepared-handle identity so approval cannot silently go stale.

WU-37 concretizes the accepted declarations as `version_headers`,
`feature_headers`, `host_body_versions` and `host_feature_body_mappings` with
`HeaderBodyMapping(header, field, separator)`. Explicit groups override legacy
header values case-insensitively; a header cannot have both explicit roles.
Duplicate body destinations/sources and version-versus-feature body collisions
fail construction. A host-specific None entry disables the legacy body version.
`body_fields(host)` resolves declared values only, without reading environment
or binding headers. Header list splitting trims delimiter whitespace and rejects
empty items; it never silently removes a feature. Vertex forwards explicit
unmapped feature headers. Payload collisions with explicit declarations fail
before I/O; legacy-only Vertex setdefault behavior remains intact.

Catalog admission/readback copies all maps; locks include every nonempty new
field and omit empty additions so legacy-only lock hashes stay identical. The
Anthropic declarations now carry both cloud versions and the Bedrock beta mapping,
without enabling any beta or implementing a Bedrock host. The fixture qualifies
existing Vertex unary execution through both driver faces. No conversion edge,
canonical schema or credentials protocol changes in WU-37.

The following WU-38 credential and binding composition additions are accepted:

Add an explicit NoCredential implementation. Preserve Credential and ApiKey's
existing protocol/signatures and configurable header/scheme. Absence of a
credential never triggers environment, filesystem, IMDS, STS or OAuth discovery.
SigV4 is an external stdlib credential implementation; token acquisition remains
outside this kernel change. Hosts remain wire values; conversion plugins import
only core/convert. No provider SDK or signing dependency enters core.

WU-38 represents catalog host data as provisional `convert.HostDescriptor` values
in `CatalogFragment.hosts`. Explicit string host selection composes a wire `Custom`;
there is no automatic host routing or new graph node. Conflicting named declarations
fail admission. Maps are copied on construction, admission and readback; nonempty
host declarations enter the catalog lock, while empty additions preserve old hashes.

A stream path overrides its unary operation path, which otherwise falls back to
the codec native path. Base path and explicit prefix precede that path; resource
interpolation encodes a single segment and query parameters are separate sorted
data. Static header precedence is dialect, host, then binding, case-insensitively.
Conflicting case aliases within one group fail. Known authentication carriers are
rejected in static headers/query and URLs cannot contain credentials. Callers must
still keep arbitrary custom fields non-secret; validation is not secret detection.
Binding headers do not participate in trait-to-body relocation; concrete cloud
hosts qualify that behavior in their own WUs.

Exact profile aliases win; otherwise the longest declared suffix is removed once
for lookup only. Unknown suffixes remain intact. Both gating and inspection use
that key, and prepared identity includes it even when the wire request is unchanged.
Existing hosts need no new required method. Unknown profile coverage stays unknown.
Recordings cover all four call faces, existing fold parity, escaped resources,
credential isolation, detached maps and stale approval. They do not qualify a vendor
endpoint, and no conversion edge or canonical schema changes in WU-38.

Sources: [Hosting, Mapping (a)](../capabilities/hosting-and-aggregators.md),
[Bedrock §13(a–b)](../providers/amazon-bedrock.md),
[Azure §11/13](../providers/azure-openai.md).

### Citations and server-tool intent (WU-40–41 accepted)

Extend existing Annotation with optional open kind (including url_citation),
a source-result reference and native metadata. Retain Span, url, document_index,
file, title, cited_text and opaque. Source-result references name a sibling
server-tool result by call identity and a payload pointer; they do not fetch
content or assert that an external URL was verified. Native metadata is preserved
under registered extension keys. Existing annotations without kind still decode.

Span remains a half-open Unicode-code-point interval into decoded text. A codec
may attach a positioned citation only when the interval and the source text
agree; byte/UTF-16 offsets need a qualified conversion fixture. Text normalization
must either carry a validated offset mapping or preserve the citation unpositioned
with original evidence; do not reuse pre-normalization offsets on changed text.
Unpositioned whole-block citations stay representable. Invalid spans are retained
as unpositioned evidence in a censused extension, never silently repaired and
never allowed to make total decode raise. Streaming reuses DeltaAnnotation and
must prove fold/PART_STOP parity in the same change.

WU-40 names the local reference `SourceResultRef(call_id, pointer)` and the
optional annotation field `source_result`; `kind` is an open string. Native
provider metadata uses existing registered extension lanes. Validation uses the
actual decoded text's Unicode code points without NFC rewriting. `cited_text`
quotes a source and is not assumed equal to the attributed output slice; a codec
can separately supply the expected output slice when checking offsets. Malformed
positions are retained in a registered extension and exposed without a span.
Validation is deferred until final text is known, so annotations may arrive before
their text deltas without being prematurely rejected.

The following WU-41 addition is accepted for implementation:

Add a tagged ServerTool alternative to ChatRequest.tools, retaining untagged
function Tool serialization. The initial common intent is an open kind plus
allowed/blocked domains and user location. Provider-specific max_uses,
search_context_size, dynamic thresholds and display obligations use censused
extensions; destination controls use provider_options. Unknown tool tags decode
to a preserving unknown representation and unsupported destinations report them.
This does not add tool execution, an MCP client or a registry to the kernel.

WU-41 uses `type="server"` for `ServerTool`; legacy untagged Tool serialization
is unchanged. `ToolUnknown` retains the original payload for unknown tags and
non-object entries. `ServerToolLocation` carries optional country, region, city
and timezone; unknown fields stay in its extensions. Explicit empty domain lists
remain explicit, and malformed location data is retained in a registered extension. The initial provider request
edges report whole unsupported entries at `tools[index]` and never encode them
as functions. Provider-specific search qualification belongs to WU-43.

Sources: [Web search §1.3–1.4](../capabilities/web-search-and-retrieval.md).
The survey's sketch mentions max_uses/search_context_size as possible fields;
its explicit three-lane mapping places them in extensions. That narrower mapping
is the proposal here.

### Replay anchors (WU-42 accepted) and search accounting (WU-43 proposed)

Add optional ChatRequest.anchors for request-side ProviderRef continuation.
Use existing part.anchor and Annotation.opaque for server-tool replay tokens.
Required encrypted bytes and response identifiers retain provider/interface
scope and replay obligations. Cross-scope reuse is UNSUPPORTED with evidence;
missing required replay fails governed preparation before I/O. A plain reasoning
text history, such as DeepSeek reasoning_content, remains PartReasoning text;
it is not converted into a fictitious opaque signature.

WU-42 adds the request-side carrier without claiming a continuation wire lane on
Chat Completions or Messages. These interfaces report each request anchor as
unsupported; same scope is necessary but does not prove that a mapping exists.
Malformed/future reference documents retain original evidence under a registered
request extension rather than degrading an unknown replay requirement to optional.
Existing Anthropic thinking signatures qualify byte-preserving replay; foreign,
missing or unqualified model-scoped references are reported without forwarding a
foreign or fabricated token. A fidelity policy denying unsupported conversion
prevents all four call faces from sending such a request. Canonical server-tool
transcript evidence does not claim provider search qualification before WU-43.

Add search_requests as a named open consumption unit. It measures the provider's
reported billable search operations, not the number of tool-call parts or tokens.
Missing counts remain absent. Provider-native counters, different billing units
and replay evidence retain registered extension lanes with their declared shifts.
The concrete provider WU certifies these mappings before claiming compatibility.

Sources: [Web search §1.1/1.4](../capabilities/web-search-and-retrieval.md),
[DeepSeek §5/7](../providers/deepseek.md), and gap G-01.

### Payment and trace vocabulary (WU-59/61)

Add the non-retryable payment_required open error code; do not rename existing
codes or classify credit exhaustion as invalid authentication. Native status/code
remain available, and vendor mappings need recorded evidence.

Add optional CallContext.trace_context carrying stdlib TraceContext(traceparent,
tracestate). These are caller-supplied correlation facts, not authenticated tenant
identity. Snapshot them through middleware/facade/drivers and explicitly expose
them to registered observers. Do not copy them to provider headers or bodies.
Arbitrary context bags and baggage stay outside automatic export. Exporters
validate W3C syntax; invalid context means a new root trace, not a failed model
call. Preserve existing caller call_id/parent_id/correlation_id. Document generated
ids as 32 lowercase hexadecimal UUID characters; supplied ids stay opaque, with
uniqueness and reuse responsibility on the caller. No process-global correlation.

Sources: [Hosting, Mapping (d)](../capabilities/hosting-and-aggregators.md),
[Observability §3/5](../capabilities/observability.md). ADR 0007 supersedes the
survey's old payload-bearing observer examples: stream events remain passive,
metadata-only, correlated and independent of durable audit enforcement.

### Cache intent and measured writes (WU-66–68)

Add UsageSource.CACHE_WRITE with the open string cache_write. Keep cache reads,
writes, uncached input and output disjoint according to each provider's measured
fields. Per-TTL detail rides registered consumption extensions. Preserve legacy
provider-specific cache-write evidence, but never emit a second billable bucket
for the same quantity. Missing usage is unknown, not zero.

Add optional ChatConfig.cache_hint: CacheHint for automatic-placement/TTL intent.
Keep ChatConfig.cache: CacheConfig and all per-part cache_hint fields. With no
new hint, old behavior is unchanged. With a request hint and absent mode, the
caller requests automatic placement; mode=auto is compatible. Mode=off conflicts
with any hint; mode=explicit conflicts with a request-level automatic hint but
allows per-part markers. Explicit per-part markers may accompany mode=auto only
when the destination qualifies the combination and slot limits; otherwise
preparation reports unsupported intent. Total decoding preserves conflicts;
execution validation reports/rejects them before I/O. TTL stays an open string:
unsupported values are preserved and reported, never silently rounded or clamped.
No caching is requested implicitly and no hint is evidence of a cache hit.

Sources: [Caching §3/4.1–4.2](../capabilities/caching-cost-and-rate-limits.md).
The request-level field is an explicit maintainer requirement beyond the survey's
per-part hint. This proposal needs review before WU-67 starts. Cost pricing remains
an independently packaged port interceptor, not a price table or budget engine
in core. OpenRouter-reported cost stays a censused extension until an explicit
adapter consumes it; estimates and reported charges must not be summed together.

## Alternatives considered

- Put everything into untyped bags: avoids a visible API change but leaves
  citations, server-tool intent, replay and accounting inaccessible to portable
  policies. Use bags only for provider-specific semantics.
- Replace existing Annotation/CacheConfig/trait fields: breaks old recordings
  and consumers without dated migration evidence. Add optional fields instead.
- Normalize every compatible host into an indistinguishable OpenAI dialect:
  hides ignored knobs, native identities and replay restrictions. Reuse mapping
  code while declaring qualified variants/effects and explicit host provenance.
- Export request bodies and context bags to implement telemetry: violates the
  merged execution boundary. Start with metadata; separately authorized payload
  capture is future work with its own redaction contract.
- Treat this program as a new freeze gate: an integration roadmap cannot replace
  ADR 0005's ordered-item, plugin, streaming and Responses qualification.

## Consequences

No runtime, schema, edge, catalog registration or dependency changes in this ADR
PR. Acceptance authorizes the named additive shapes, not blanket modernization.
Every owning WU still updates architecture, fixtures, censuses and its status,
passes the strict gate, opens one PR and waits for review/merge. If evidence
requires another shape, record a gap and amend the design before implementation.
