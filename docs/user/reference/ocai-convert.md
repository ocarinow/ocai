# `ocai.convert` API reference

Generated from the checked-out package sources. Signatures, declared fields,
methods, type aliases and explicit re-exports are checked for drift. Inherited
members follow their named base class; a type's presence does not establish
provider execution support. See [supported features](../provider-feature-matrix.md).

## `ocai.convert`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/convert/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-convert-entry-point-group"></span>`ENTRY_POINT_GROUP` | [`ocai.convert.catalog.ENTRY_POINT_GROUP`](ocai-convert.md#ocai-convert-catalog-entry-point-group) |
| <span id="ocai-convert-admissionerror"></span>`AdmissionError` | [`ocai.convert.catalog.AdmissionError`](ocai-convert.md#ocai-convert-catalog-admissionerror) |
| <span id="ocai-convert-catalog"></span>`Catalog` | [`ocai.convert.catalog.Catalog`](ocai-convert.md#ocai-convert-catalog-catalog) |
| <span id="ocai-convert-catalogbuilder"></span>`CatalogBuilder` | [`ocai.convert.catalog.CatalogBuilder`](ocai-convert.md#ocai-convert-catalog-catalogbuilder) |
| <span id="ocai-convert-catalogfragment"></span>`CatalogFragment` | [`ocai.convert.catalog.CatalogFragment`](ocai-convert.md#ocai-convert-catalog-catalogfragment) |
| <span id="ocai-convert-cataloglock"></span>`CatalogLock` | [`ocai.convert.catalog.CatalogLock`](ocai-convert.md#ocai-convert-catalog-cataloglock) |
| <span id="ocai-convert-component"></span>`Component` | [`ocai.convert.catalog.Component`](ocai-convert.md#ocai-convert-catalog-component) |
| <span id="ocai-convert-componentfactory"></span>`ComponentFactory` | [`ocai.convert.catalog.ComponentFactory`](ocai-convert.md#ocai-convert-catalog-componentfactory) |
| <span id="ocai-convert-resolutionerror"></span>`ResolutionError` | [`ocai.convert.catalog.ResolutionError`](ocai-convert.md#ocai-convert-catalog-resolutionerror) |
| <span id="ocai-convert-trustpolicy"></span>`TrustPolicy` | [`ocai.convert.catalog.TrustPolicy`](ocai-convert.md#ocai-convert-catalog-trustpolicy) |
| <span id="ocai-convert-default-catalog"></span>`default_catalog` | [`ocai.convert.catalog.default_catalog`](ocai-convert.md#ocai-convert-catalog-default-catalog) |
| <span id="ocai-convert-contractviolation"></span>`ContractViolation` | [`ocai.convert.contract.ContractViolation`](ocai-convert.md#ocai-convert-contract-contractviolation) |
| <span id="ocai-convert-declareddisposition"></span>`DeclaredDisposition` | [`ocai.convert.contract.DeclaredDisposition`](ocai-convert.md#ocai-convert-contract-declareddisposition) |
| <span id="ocai-convert-edgecontract"></span>`EdgeContract` | [`ocai.convert.contract.EdgeContract`](ocai-convert.md#ocai-convert-contract-edgecontract) |
| <span id="ocai-convert-lossgrade"></span>`LossGrade` | [`ocai.convert.contract.LossGrade`](ocai-convert.md#ocai-convert-contract-lossgrade) |
| <span id="ocai-convert-conversionerror"></span>`ConversionError` | [`ocai.convert.graph.ConversionError`](ocai-convert.md#ocai-convert-graph-conversionerror) |
| <span id="ocai-convert-conversiongraph"></span>`ConversionGraph` | [`ocai.convert.graph.ConversionGraph`](ocai-convert.md#ocai-convert-graph-conversiongraph) |
| <span id="ocai-convert-converted"></span>`Converted` | [`ocai.convert.graph.Converted`](ocai-convert.md#ocai-convert-graph-converted) |
| <span id="ocai-convert-edge"></span>`Edge` | [`ocai.convert.graph.Edge`](ocai-convert.md#ocai-convert-graph-edge) |
| <span id="ocai-convert-edgefn"></span>`EdgeFn` | [`ocai.convert.graph.EdgeFn`](ocai-convert.md#ocai-convert-graph-edgefn) |
| <span id="ocai-convert-edgeoutput"></span>`EdgeOutput` | [`ocai.convert.graph.EdgeOutput`](ocai-convert.md#ocai-convert-graph-edgeoutput) |
| <span id="ocai-convert-streamconverter"></span>`StreamConverter` | [`ocai.convert.graph.StreamConverter`](ocai-convert.md#ocai-convert-graph-streamconverter) |
| <span id="ocai-convert-streamconverterfactory"></span>`StreamConverterFactory` | [`ocai.convert.graph.StreamConverterFactory`](ocai-convert.md#ocai-convert-graph-streamconverterfactory) |
| <span id="ocai-convert-streamedge"></span>`StreamEdge` | [`ocai.convert.graph.StreamEdge`](ocai-convert.md#ocai-convert-graph-streamedge) |
| <span id="ocai-convert-streampipeline"></span>`StreamPipeline` | [`ocai.convert.graph.StreamPipeline`](ocai-convert.md#ocai-convert-graph-streampipeline) |
| <span id="ocai-convert-hostdescriptor"></span>`HostDescriptor` | [`ocai.convert.hosts.HostDescriptor`](ocai-convert.md#ocai-convert-hosts-hostdescriptor) |
| <span id="ocai-convert-register-revision-migration"></span>`register_revision_migration` | [`ocai.convert.migrate.register_revision_migration`](ocai-convert.md#ocai-convert-migrate-register-revision-migration) |
| <span id="ocai-convert-conformanceresources"></span>`ConformanceResources` | [`ocai.convert.resources.ConformanceResources`](ocai-convert.md#ocai-convert-resources-conformanceresources) |

## `ocai.convert.catalog`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/convert/catalog.py)

### `ENTRY_POINT_GROUP` { #ocai-convert-catalog-entry-point-group }

```python
ENTRY_POINT_GROUP = 'ocai.fragments'
```

### `ComponentFactory` { #ocai-convert-catalog-componentfactory }

```python
type ComponentFactory = Callable[..., Any]
```

### `TrustPolicy` { #ocai-convert-catalog-trustpolicy }

```python
class TrustPolicy(str, Enum):
    OWNED_ENDPOINTS = 'owned_endpoints'
    ALLOW_LISTED = 'allow_listed'
```

````text
How a `CatalogBuilder` admits fragments — the governance dial.

Attributes:
    OWNED_ENDPOINTS: The default. Every edge a fragment registers must
        have both endpoints on an interface the fragment itself
        publishes (via `nodes`) or on the canonical `ocai` interface. A
        third-party fragment can therefore never silently insert itself
        between two providers it does not own.
    ALLOW_LISTED: Like `OWNED_ENDPOINTS`, except fragments whose
        `origin.distribution` appears in the builder's `allow` set may
        bridge foreign endpoints — the named opt-in for deliberate
        cross-provider bridge packages.
````

### `AdmissionError` { #ocai-convert-catalog-admissionerror }

```python
class AdmissionError(OcaiError)
```

````text
Raised when a fragment fails the composing `TrustPolicy`'s checks.
````

### `ResolutionError` { #ocai-convert-catalog-resolutionerror }

```python
class ResolutionError(OcaiError)
```

````text
Raised when `Catalog.resolve` cannot satisfy a request or its pins.
````

### `Component` { #ocai-convert-catalog-component }

```python
class Component:
    provider: str
    interface: str
    capability: Capability
    factory: ComponentFactory
```

````text
A runtime factory a fragment contributes for one resolved interface.

The declarative successor of the old `ComponentRegistry` entry: it names
*which* `(provider, interface, capability)` the factory serves, so the
facade layer can ask the catalog for the codec/adapter builder matching
a resolved `Route` without the catalog ever calling it.

Attributes:
    provider: The provider the factory serves (e.g. `"openai"`).
    interface: The interface within the provider
        (e.g. `"chat_completions"`).
    capability: The capability the built object implements.
    factory: The opaque builder; its signature belongs to the plugin.
````

### `CatalogFragment` { #ocai-convert-catalog-catalogfragment }

```python
class CatalogFragment:
    origin: Origin
    nodes: tuple[NodeId, ...] = ()
    edges: tuple[Edge, ...] = ()
    transducers: tuple[StreamEdge, ...] = ()
    profiles: tuple[CapabilityProfile, ...] = ()
    traits: tuple[DialectTraits, ...] = ()
    components: tuple[Component, ...] = ()
    conformance: ConformanceResources | None = None
    hosts: Mapping[str, HostDescriptor] = field(default_factory=dict[str, HostDescriptor])
```

````text
Everything one distribution contributes to a catalog — as frozen data.

The plugin ABI (freezes at v1.0). A plugin module exposes exactly one
`FRAGMENT` constant; building it must not mutate shared catalog state.
Entry-point imports still execute arbitrary Python, not sandboxed code.
The `CatalogBuilder` admission-checks a fragment against the composing application's
`TrustPolicy` before any of its contents become reachable.

Attributes:
    origin: Who ships this fragment — stamped into lockfiles and audit
        records for every node/edge below.
    nodes: The `NodeId`s this fragment publishes (its own interfaces'
        shapes, dated and statused). These define what the fragment
        "owns" for `TrustPolicy.OWNED_ENDPOINTS`.
    edges: The payload conversion edges, each carrying its
        `EdgeContract`.
    transducers: The chunk-shape transducer edges, likewise
        contracted.
    profiles: The `CapabilityProfile` fact sheets for the fragment's
        interfaces (feature support per model pattern).
    traits: The `DialectTraits` (`ocai.core.traits`) the wire layer
        reads as data to host this fragment's interfaces (headers,
        envelope facts). Carried here opaquely — the catalog never
        interprets them.
    components: The runtime factories (codec/adapter builders) keyed by
        `(provider, interface, capability)`.
    conformance: Optional package-relative fixture/schema locations. Only
        the explicit test harness reads resources; admission does not.
    hosts: Explicitly named host data; selecting a host never changes codecs.
        Names must agree across fragments; admission/readback detach maps.
````

### `CatalogLock` { #ocai-convert-catalog-cataloglock }

```python
class CatalogLock:
    hash: str
    payload: dict[str, Any]
```

````text
The diffable description of one composed catalog, content-hashed.

Emitted by `Catalog.lock()`. The `hash` lands in every `Route` the
catalog resolves, so a stored `Route` plus a stored lockfile
identifies declared plugin versions, contracts, and routing metadata. It
does not hash executable code or resource file contents and cannot prove
which artifact served a call. Committing the lockfile and diffing it across
dependency bumps is the intended change-review workflow.

Attributes:
    hash: The SHA-256 hex digest of the payload's canonical JSON
        (`ocai.core.canonjson.canonical`), so semantically equal
        catalogs hash equal regardless of composition order artifacts.
    payload: The JSON-shaped lockfile content: trust policy, and per
        fragment its origin, nodes (with released/status), edges (with
        full contracts, derived grades and origins), stream edges, profiles,
        components, traits, and conformance resource locations.
````

#### `CatalogLock.to_json` { #ocai-convert-catalog-cataloglock-to-json }

```python
def to_json(self) -> str
```

````text
Render the lockfile as stable, indented, diff-friendly JSON.

Returns:
    The payload serialized with sorted keys and two-space indents —
    the form meant to be committed to version control.
````

### `CatalogBuilder` { #ocai-convert-catalog-catalogbuilder }

```python
class CatalogBuilder
```

````text
Accumulates admission-checked fragments and builds an immutable `Catalog`.

The mutable composition step, deliberately separate from the immutable
result: `add` fails fast at the offending fragment (naming it), so a
trust violation surfaces at composition time, never mid-request.

Interaction: plugins never see a builder — they export data
(`CatalogFragment`); applications drive the builder (directly, or via
the `Catalog.of` / `Catalog.discover` conveniences that wrap it).
````

#### `CatalogBuilder.__init__` { #ocai-convert-catalog-catalogbuilder---init-- }

```python
def __init__(self, *, trust: TrustPolicy=TrustPolicy.OWNED_ENDPOINTS, allow: frozenset[str]=frozenset()) -> None
```

````text
Create an empty builder under a trust policy.

Args:
    trust: The admission policy for every fragment added.
    allow: Distribution names granted foreign-bridging opt-in;
        meaningful only with `TrustPolicy.ALLOW_LISTED`.
````

#### `CatalogBuilder.of` { #ocai-convert-catalog-catalogbuilder-of }

```python
@classmethod
def of(cls, *fragments: CatalogFragment, trust: TrustPolicy=TrustPolicy.OWNED_ENDPOINTS, allow: frozenset[str]=frozenset()) -> Catalog
```

````text
Compose `fragments` into a catalog in one expression.

Args:
    fragments: The fragments to admit, in order.
    trust: The admission policy.
    allow: Distribution names granted foreign-bridging opt-in.

Returns:
    The built, immutable `Catalog`.

Raises:
    AdmissionError: If any fragment violates the trust policy.
````

#### `CatalogBuilder.add` { #ocai-convert-catalog-catalogbuilder-add }

```python
def add(self, fragment: CatalogFragment) -> Self
```

````text
Admission-check `fragment` and stage it for the build.

Args:
    fragment: The fragment to admit.

Returns:
    This builder, for chaining.

Raises:
    AdmissionError: If the fragment violates the trust policy.
````

#### `CatalogBuilder.discover` { #ocai-convert-catalog-catalogbuilder-discover }

```python
def discover(self, *, group: str=ENTRY_POINT_GROUP) -> Self
```

````text
Add every fragment advertised by installed distributions.

The opt-in "compose everything installed" convenience: loads each
entry point in `group`, accepting either a `CatalogFragment` value
or a zero-argument callable returning one, and admits it through
the same trust gate as `add`. Deterministic: entry points are
processed in sorted name order.

Args:
    group: The entry-point group to scan.

Returns:
    This builder, for chaining.

Raises:
    AdmissionError: If a discovered fragment violates the trust
        policy — discovery grants no extra trust.
    TypeError: If an entry point yields something that is not a
        `CatalogFragment`.
````

#### `CatalogBuilder.build` { #ocai-convert-catalog-catalogbuilder-build }

```python
def build(self) -> Catalog
```

````text
Freeze the staged fragments into an immutable `Catalog`.

Returns:
    The composed catalog.
````

### `Catalog` { #ocai-convert-catalog-catalog }

```python
class Catalog
```

````text
An immutable, provenance-stamped composition of fragments.

The application-scoped successor of the old process-global registries.
Construction indexes everything once: one `ConversionGraph` per `Shape`
(fed the fragments' edges and stream edges), the published nodes for
resolution, and the profile/component lookups. After that the catalog
only answers questions — `resolve` (which interface revision serves a
call, recorded as a `Route`), `convert` (delegate to the right shape's
graph), `lock` (the audit lockfile) — and never changes.

The wire-backed facade (`ocai.chat.facade.WireChatModel`) holds one and
drives resolve → convert(request) → send → convert(response); the §3.4
front door (`ocai.chat.model`) hands every model it builds the same
catalog, so per-tenant isolation is plain Python — several models built
from different credentials/catalogs, no container object above them.
````

#### `Catalog.__init__` { #ocai-convert-catalog-catalog---init-- }

```python
def __init__(self, fragments: Iterable[CatalogFragment]=(), *, trust: TrustPolicy=TrustPolicy.OWNED_ENDPOINTS, allow: frozenset[str]=frozenset()) -> None
```

````text
Compose `fragments` into an indexed, immutable catalog.

Re-runs admission for every fragment (so direct construction cannot
bypass the trust gate), then builds the per-shape graphs and lookup
indexes. Prefer `Catalog.of` / `Catalog.discover` in application
code.

Args:
    fragments: The fragments to compose, in order.
    trust: The admission policy the composition is checked against.
    allow: Distribution names granted foreign-bridging opt-in.

Raises:
    AdmissionError: If any fragment violates the trust policy, or
        node metadata, directed edges, profiles, or components conflict,
        or an edge crosses shapes.
````

#### `Catalog.of` { #ocai-convert-catalog-catalog-of }

```python
@classmethod
def of(cls, *fragments: CatalogFragment, trust: TrustPolicy=TrustPolicy.OWNED_ENDPOINTS, allow: frozenset[str]=frozenset()) -> Catalog
```

````text
Compose `fragments` into a catalog (delegates to `CatalogBuilder`).

The canonical application spelling:
`Catalog.of(openai.FRAGMENT, anthropic.FRAGMENT)`.

Args:
    fragments: The fragments to admit, in order.
    trust: The admission policy.
    allow: Distribution names granted foreign-bridging opt-in.

Returns:
    The built, immutable catalog.

Raises:
    AdmissionError: If any fragment violates the trust policy.
````

#### `Catalog.discover` { #ocai-convert-catalog-catalog-discover }

```python
@classmethod
def discover(cls, *, trust: TrustPolicy=TrustPolicy.OWNED_ENDPOINTS, allow: frozenset[str]=frozenset(), group: str=ENTRY_POINT_GROUP) -> Catalog
```

````text
Compose everything installed (delegates to `CatalogBuilder.discover`).

Args:
    trust: The admission policy — discovery grants no extra trust.
    allow: Distribution names granted foreign-bridging opt-in.
    group: The entry-point group to scan.

Returns:
    The built catalog of all discovered fragments.

Raises:
    AdmissionError: If a discovered fragment violates the policy.
````

#### `Catalog.fragments` { #ocai-convert-catalog-catalog-fragments }

```python
@property
def fragments(self) -> tuple[CatalogFragment, ...]
```

````text
Return the composed fragments, in admission order.
````

#### `Catalog.nodes` { #ocai-convert-catalog-catalog-nodes }

```python
@property
def nodes(self) -> tuple[NodeId, ...]
```

````text
Return every published node, de-duplicated, in admission order.
````

#### `Catalog.resolve` { #ocai-convert-catalog-catalog-resolve }

```python
def resolve(self, capability: Capability, provider: str, *, interface: str | None=None, tag: str | None=None, channel: Status=Status.STABLE) -> Route
```

````text
Decide which interface revision serves a call; record it as a `Route`.

Resolution operates on the provider's published request-shape nodes
for `capability`. With pins, they are honored exactly (a pinned tag
may select `PREVIEW`/`DEPRECATED`/`RETIRED` revisions — pinning is
the explicit escape hatch). Without pins, the newest eligible
revision within one interface wins: latest `STABLE` by `released`
under the default channel, never parsing the opaque tag. The returned `Route` carries
the reason and this catalog's lock hash — the audit joint. Multiple eligible
sibling interfaces require an explicit interface pin; their dates are
not comparable API preferences.

Args:
    capability: The capability being called (e.g. `CHAT`).
    provider: The provider to resolve within (e.g. `"openai"`).
    interface: An interface pin, or None for "let ocai choose".
    tag: A revision-tag pin, or None for "latest eligible".
    channel: The lowest status eligible for auto-selection when
        `tag` is not pinned.

Returns:
    The `Route` recording the chosen node, the pins, the reason,
    and the catalog hash.

Raises:
    ResolutionError: If the provider/capability is unknown here, the
        pinned interface or tag does not exist, or nothing is
        eligible under `channel`.
````

#### `Catalog.inspect` { #ocai-convert-catalog-catalog-inspect }

```python
def inspect(self, src: NodeId, dst: NodeId, *, streaming: bool=False) -> ConversionInspection
```

````text
Inspect selected declarations without executing or claiming conformance.
````

#### `Catalog.convert` { #ocai-convert-catalog-catalog-convert }

```python
def convert(self, payload: Any, src: NodeId, dst: NodeId) -> Converted
```

````text
Convert `payload` between two nodes of one shape.

Delegates to the shape's partitioned `ConversionGraph` — the
catalog's only conversion entry point, so every conversion in an
application runs over admitted, contract-carrying edges.

Args:
    payload: The input payload, in `src`'s representation.
    src: The source node.
    dst: The destination node; must share `src`'s shape.

Returns:
    A `Converted` with the output value and its `FidelityReport`.

Raises:
    ConversionError: If the shapes differ, no edges exist for the
        shape, or no path exists.
````

#### `Catalog.stream_converter` { #ocai-convert-catalog-catalog-stream-converter }

```python
def stream_converter(self, src: NodeId, dst: NodeId) -> StreamPipeline
```

````text
Build the composite transducer converting chunk events `src -> dst`.

The streaming twin of `convert`, delegating to the chunk shape's
graph. The facade hands the result to a driver, which pumps decoded
wire events through it; after the driver flushes it, the per-edge
accounting on `StreamPipeline.reports` is folded into the terminal
`StreamEnd.report` (the WU-09 seam).

Args:
    src: The source chunk-shape node.
    dst: The destination chunk-shape node; must share `src`'s shape.

Returns:
    A fresh `StreamPipeline` for one stream traversal.

Raises:
    ConversionError: If the shapes differ, no edges exist for the
        shape, or no stream path exists.
````

#### `Catalog.profiles_for` { #ocai-convert-catalog-catalog-profiles-for }

```python
def profiles_for(self, provider: str, interface: str, model: str) -> tuple[CapabilityProfile, ...]
```

````text
Return every `CapabilityProfile` covering `model`, ranked.

The feature gate's lookup: consulted before payload conversion so an
`ABSENT` feature can be refused (strict) or loss-recorded (annotate)
without building a doomed request. Profiles are filtered to the
`(provider, interface)` pair and to those whose `model_pattern`
matches `model`, then ranked **most specific first**: specificity is
the length of the pattern's literal prefix (the run before its first
wildcard), so a `"claude-4*"` sheet beats a `"*"` sheet for
`"claude-4-opus"`. Ties sort lexically by pattern, independent of
admission order. The gate layers the result via `ocai.core.profile.resolve_support` — the
first profile declaring a feature key wins; a key no profile
declares defaults to `Support.NATIVE`.

Args:
    provider: The provider the request targets.
    interface: The interface within the provider.
    model: The concrete model name from the request.

Returns:
    The matching profiles, most specific first; empty when the
    catalog holds no facts for the triple.
````

#### `Catalog.profile` { #ocai-convert-catalog-catalog-profile }

```python
def profile(self, provider: str, interface: str, model: str) -> CapabilityProfile | None
```

````text
Return the most specific `CapabilityProfile` covering `model`.

The single-sheet convenience over `profiles_for` — the head of the
specificity ranking. The feature gate itself consults the full
ranked stack (a specific sheet declares only its exceptions and must
not mask the interface-wide sheet beneath it).

Args:
    provider: The provider the request targets.
    interface: The interface within the provider.
    model: The concrete model name from the request.

Returns:
    The best-matching profile, or None when the catalog holds no
    facts for the triple.
````

#### `Catalog.component` { #ocai-convert-catalog-catalog-component }

```python
def component(self, provider: str, interface: str, capability: Capability) -> ComponentFactory
```

````text
Return the runtime factory registered for the resolved interface.

Called by the facade layer with a `Route`'s coordinates to obtain
the codec/adapter builder the serving plugin shipped.

Args:
    provider: The provider from the resolved route.
    interface: The interface from the resolved route.
    capability: The capability being served.

Returns:
    The plugin's opaque factory.

Raises:
    LookupError: If no fragment in this catalog provides one — with
        an install hint, because a missing component usually means a
        missing plugin distribution, not a broken import.
````

#### `Catalog.components_for` { #ocai-convert-catalog-catalog-components-for }

```python
def components_for(self, provider: str, capability: Capability) -> tuple[Component, ...]
```

````text
Return every component registered for `provider` serving `capability`.

The front doors' auto-selection seam (§3.4): a nodes-only stub
interface is resolvable when *pinned*, but only interfaces backed by
a registered component factory can actually be served, so the front
door restricts unpinned resolution to this set.

Args:
    provider: The provider to list components for.
    capability: The capability the built objects must implement.

Returns:
    The matching components, in fragment admission order; empty when
    no composed fragment registered any.
````

#### `Catalog.host` { #ocai-convert-catalog-catalog-host }

```python
def host(self, name: str) -> HostDescriptor
```

````text
Return detached, explicitly selected host data from this catalog.

Raises:
    ResolutionError: No host is declared under the requested name.
````

#### `Catalog.lock` { #ocai-convert-catalog-catalog-lock }

```python
def lock(self) -> CatalogLock
```

````text
Emit the diffable lockfile describing this composition, hashed.

Computed once and cached (the catalog is immutable). The hash is the
SHA-256 of the payload's canonical JSON and is stamped into every
`Route` this catalog resolves.

Returns:
    The `CatalogLock` for this exact composition.
````

### `default_catalog` { #ocai-convert-catalog-default-catalog }

```python
def default_catalog() -> Catalog
```

````text
Return the process's entry-point-discovered catalog, built once.

The **only** module-level state in `ocai.convert`, and it is a memoized
pure function, not a mutable registry: the first call runs
`Catalog.discover()` under the default `TrustPolicy.OWNED_ENDPOINTS`
and every later call returns that same immutable catalog. Convenience
entry points (a bare `WireChatModel` with no explicit catalog) use it;
applications that care about governance compose `Catalog.of(...)`
explicitly and never touch this.

Returns:
    The memoized default catalog.
````

## `ocai.convert.conformance`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/convert/conformance.py)

### `Fixture` { #ocai-convert-conformance-fixture }

```python
type Fixture = dict[str, Any]
```

### `check_fragment` { #ocai-convert-conformance-check-fragment }

```python
def check_fragment(fragment: CatalogFragment, fixtures: Iterable[Fixture], *, decode_inputs: Mapping[NodeId, Callable[[dict[str, Any]], Any]] | None=None, bind_outputs: Mapping[NodeId, Callable[[Any], Any]] | None=None) -> int
```

````text
Check every payload edge against independently authored fixtures.

Args:
    fragment: The fragment to admit and check. Streaming edges still
        require their dedicated fold triples.
    fixtures: Edge fixtures, such as a loaded resource bundle's values.
    decode_inputs: Optional typed decoders keyed by source node.
    bind_outputs: Optional post-conversion finishers keyed by destination.

Returns:
    The number of checked fixtures.

Raises:
    AssertionError: If a fixture names no unique edge, an edge has no
        fixture, expected output/records differ, or a declaration is exceeded.
````

### `DecodeFn` { #ocai-convert-conformance-decodefn }

```python
type DecodeFn = Callable[[dict[str, Any]], dict[str, Any]]
```

### `EncodeFn` { #ocai-convert-conformance-encodefn }

```python
type EncodeFn = Callable[[dict[str, Any]], dict[str, Any]]
```

### `load_fixture` { #ocai-convert-conformance-load-fixture }

```python
def load_fixture(path: str | Path) -> Fixture
```

````text
Read a single golden fixture from `path`.

Args:
    path: The fixture JSON file to read.

Returns:
    The parsed fixture object.
````

### `iter_fixtures` { #ocai-convert-conformance-iter-fixtures }

```python
def iter_fixtures(directory: str | Path, *, pattern: str='*.json') -> Iterator[tuple[Path, Fixture]]
```

````text
Yield every golden fixture under `directory`, sorted by filename.

Args:
    directory: The folder of golden fixtures to walk (non-recursive).
    pattern: The glob selecting fixture files. Defaults to `"*.json"`.

Yields:
    A `(path, fixture)` pair per matching file, in sorted path order.
````

### `check_edge` { #ocai-convert-conformance-check-edge }

```python
def check_edge(edge: Edge, fixture: Fixture, *, decode_input: Callable[[dict[str, Any]], Any] | None=None, bind: Callable[[Any], Any] | None=None) -> EdgeOutput
```

````text
Assert one edge fixture: output equality plus exact loss/shift match.

The executable form of the edge-fixture contract in `spec/README.md`
(clauses 1 and 2; clause 3 — runtime loss never exceeding the declared
census — is `certify_edge`'s job, fed with the same fixture payloads):

1. Running `edge.fn` on the fixture's `input` yields a value
   `semantic_equal` to `expect`.
2. The runtime `FieldLoss` records match `expect_losses` and the runtime
   `SemanticShift` records match `expect_shifts` **exactly** — same
   multiset, nothing extra, nothing missing. Records compare on
   `(path, disposition)` / `(kind, path)`; notes and severities are
   prose/diagnostics and are never compared (mirroring
   `EdgeContract.certify`). `expect_losses` must be present even when
   empty — the honest part of a fixture is never absent by accident;
   `expect_shifts` defaults to empty.

The harness stays capability-neutral: fixtures store payloads as plain
JSON, so a canonical-source fixture supplies `decode_input` (typically a
`from_dict`) to lift `input` into the IR object the edge function takes,
and an output exposing `to_dict` is rendered through it for comparison.

Args:
    edge: The contracted edge under test; the fixture's `src`/`dst`
        coordinates must name its endpoints (the caller selects the
        edge; this helper does not resolve catalogs).
    fixture: An edge fixture carrying `input`, `expect`, and
        `expect_losses` (plus optional `expect_shifts`).
    decode_input: Lifts the fixture's `input` payload into the edge's
        source representation; None when the input is already the raw
        payload the edge function takes (wire-source fixtures).
    bind: A post-edge finisher applied to the output value before
        comparison — the facade seam below the graph (e.g. injecting the
        bound model via a codec's `bind_resource`); None for edges whose
        output is already the complete `expect` payload.

Returns:
    The `EdgeOutput` of the run, so callers can feed the same payload
    set to `certify_edge` or inspect the records further.

Raises:
    AssertionError: If the output diverges from `expect`, the records
        diverge from the expectations, or `expect_losses` is missing.
````

### `assert_fixture_roundtrip` { #ocai-convert-conformance-assert-fixture-roundtrip }

```python
def assert_fixture_roundtrip(fixture: Fixture, *, decode: DecodeFn, encode: EncodeFn) -> None
```

````text
Assert a codec satisfies the golden-fixture contract for one fixture.

Checks both directions independently under `semantic_equal`: decoding
the provider `raw` payload yields the expected `canonical` IR, and
encoding that `canonical` IR yields the original `raw` back (a lossless
round-trip, up to canonical-JSON semantics — embedded `*_json` strings
compare parsed, per the parse-compare rule).

Args:
    fixture: A golden fixture carrying `raw` and `canonical`.
    decode: The plugin's provider-`raw` → canonical-dict function
        (typically `lambda raw: codec.decode(raw).value.to_dict()`).
    encode: The plugin's canonical-dict → provider-`raw` function
        (typically `lambda c: codec.encode(Type.from_dict(c)).value`).

Raises:
    AssertionError: If either direction does not match the fixture.
````

### `check_codec` { #ocai-convert-conformance-check-codec }

```python
def check_codec(directory: str | Path, *, decode: DecodeFn, encode: EncodeFn) -> list[Path]
```

````text
Run `assert_fixture_roundtrip` over every fixture in `directory`.

A convenience for a plugin's test suite: point it at the plugin's
fixture folder and it checks each one, failing loudly if the folder is
empty (an empty fixture set silently "passing" would defeat the drift
alarm).

Args:
    directory: The folder of golden fixtures to check.
    decode: The codec's provider-`raw` → canonical-dict function.
    encode: The codec's canonical-dict → provider-`raw` function.

Returns:
    The list of fixture paths that were checked.

Raises:
    AssertionError: If a fixture fails the round-trip, or none are
        found.
````

### `assert_graph_roundtrip` { #ocai-convert-conformance-assert-graph-roundtrip }

```python
def assert_graph_roundtrip(catalog: Catalog, fixture: Fixture, *, wire: NodeId, canonical_node: NodeId, canonical_to_dict: Callable[[Any], dict[str, Any]]=lambda v: v.to_dict()) -> FidelityReport
```

````text
Assert a registered wire node round-trips through the canonical backbone.

Converts the fixture's `raw` payload `wire → canonical_node` via the
catalog (asserting `semantic_equal` with the fixture's `canonical`) and
back `canonical_node → wire` (asserting it recovers `raw`). The
plugin's fragment must be composed into `catalog` first — which also
means the edges exercised here passed admission, exactly as in
production.

Args:
    catalog: The composed catalog holding the plugin's fragment.
    fixture: A golden fixture carrying `raw` and `canonical`.
    wire: The plugin's wire node for one shape (e.g. its
        `chat.request` node).
    canonical_node: The canonical backbone node for the same shape.
    canonical_to_dict: How to render the converted canonical value as a
        dict for comparison; defaults to calling its `to_dict()`.

Returns:
    The `FidelityReport` from the forward (`wire → canonical_node`)
    conversion, so callers can additionally assert on the chosen path
    and per-field loss.

Raises:
    AssertionError: If either conversion does not match the fixture.
````

### `assert_fold_triple` { #ocai-convert-conformance-assert-fold-triple }

```python
def assert_fold_triple(fixture: Fixture, *, decode_event: Callable[[Any], list[dict[str, Any]]] | None=None, fold: Callable[[list[dict[str, Any]]], dict[str, Any]]) -> None
```

````text
Assert one fold-triple fixture: wire events → chunks → folded response.

The executable form of the streaming law
`fold(stream(request)) == complete(request)` (rule 7). A fold triple
carries correlated views of one streamed call:

- `wire_events` — the recorded wire event log, *optional*: absent on
  canonical-node triples whose chunks are already canonical,
- `chunks` — the canonical `ChatChunk` dicts those events must decode
  to,
- `response` — the canonical response dict the chunks must fold to.

Three clauses, all under `semantic_equal`:

1. **Decode leg** (only when `wire_events` is present): the events
   decode, in order, to exactly the expected chunks.
2. **Fold leg** (mandatory): folding the chunks reproduces the
   response.
3. **The ratchet's second clause**: each `partStop`'s authoritative
   final part MUST equal its delta accumulation — checked by stripping
   the finals from every delta-fed `partStop`
   (`_strip_authoritative_finals`) and asserting the re-fold still
   reproduces the response.

`decode_event` and `fold` are parameters (typically wrapping the
codec's `decode_event` and `StreamAccumulator.fold`) so this harness
never imports a capability package; both speak plain dicts.

Args:
    fixture: A fold-triple fixture carrying `chunks`, `response`, and
        optionally `wire_events`.
    decode_event: The codec's wire-event → canonical-chunk-dicts
        function (one event may yield zero or more chunks); required
        exactly when the fixture carries `wire_events`.
    fold: The capability's normative accumulator, folding a canonical
        chunk-dict sequence into the complete response dict.

Raises:
    AssertionError: If any clause diverges from the fixture, or the
        fixture carries `wire_events` but no `decode_event` was
        supplied.
````

### `check_fold_triples` { #ocai-convert-conformance-check-fold-triples }

```python
def check_fold_triples(directory: str | Path, *, decode_event: Callable[[Any], list[dict[str, Any]]] | None=None, fold: Callable[[list[dict[str, Any]]], dict[str, Any]], pattern: str='*.json') -> list[Path]
```

````text
Run `assert_fold_triple` over every fixture in `directory`.

The per-streaming-edge companion of `check_codec`: every streaming edge
ships fold triples, and this walker refuses to "pass" on an empty
folder.

Args:
    directory: The folder of fold-triple fixtures to check.
    decode_event: The codec's wire-event → canonical-chunk-dicts
        function; required for fixtures carrying `wire_events`.
    fold: The capability's normative accumulator, folding a canonical
        chunk-dict sequence into the complete response dict.
    pattern: The glob selecting fixture files.

Returns:
    The list of fixture paths that were checked.

Raises:
    AssertionError: If a triple fails, or none are found.
````

### `certify_edge` { #ocai-convert-conformance-certify-edge }

```python
def certify_edge(edge: Edge, payloads: Iterable[Any]) -> list[ContractViolation]
```

````text
Certify an edge's runtime loss against its declared contract.

The build-time honesty gate (§4.2): runs the edge function over every
fixture payload, collects the `FieldLoss` and `SemanticShift` records it
actually emitted, and checks them against the declared census and
declared shifts via `EdgeContract.certify`.
A plugin's test suite asserts the result is empty — an edge whose
runtime loss exceeds its declaration cannot ship, which is what makes a
"lossless" claim in a lockfile trustworthy.

Args:
    edge: The contracted edge under certification.
    payloads: Source-node payloads to exercise the edge with —
        typically every relevant fixture's `raw` (or `canonical`) side.

Returns:
    Every violation found across all payloads; empty means certified.
````

### `assert_unknown_vector` { #ocai-convert-conformance-assert-unknown-vector }

```python
def assert_unknown_vector(fixture: Fixture, *, decode: Callable[[dict[str, Any]], Any]) -> None
```

````text
Assert one unknown-X vector: total decode, fallback typing, no loss.

The executable form of rule 6 for a single vector (the fixture shape and
`expect` vocabulary are normative in `spec/README.md`, "Normative
unknown-X fixtures"). Four assertions:

1. **Total decode** — `decode(document)` never raises, whatever unknown
   material the document carries.
2. **Fallback typing** — every `expect.fallbacks` path decodes to the
   canonical fallback type it names. Types are compared by *name*
   (`PartUnknown`, `DeltaUnknown`, `DetailOpaque`, `SourceUnknown`) so
   this module never imports a capability package and the vocabulary
   stays language-neutral.
3. **Sweeps and preservation** — every `expect.extensions` key lands
   verbatim in its owner's `extensions` bag (and only there), and every
   `expect.preserved` path re-encodes `semantic_equal` to the document's
   value.
4. **Round trip** — `to_dict()` of the decoded value is `semantic_equal`
   to the document with the declared sweeps applied; verbatim when none
   are declared.

Args:
    fixture: An unknown vector carrying `document` and `expect`.
    decode: The decoder under test (canonical document dict → IR object
        exposing `to_dict`).

Raises:
    AssertionError: If decoding raises, a fallback lands on the wrong
        type, a sweep or preservation expectation fails, or the round
        trip loses material.
````

### `check_unknown_inputs` { #ocai-convert-conformance-check-unknown-inputs }

```python
def check_unknown_inputs(directory: str | Path, *, decode: Callable[[dict[str, Any]], Any], pattern: str='*.json') -> list[Path]
```

````text
Run the normative unknown-X vectors: total decode, never a raise.

The executable form of rule 6, and part of the cross-language
conformance bar (TS/Go ports run the same fixtures). Each vector's
`document` contains deliberately unknown material — unknown part/delta/
detail tags, unknown envelope keys, unknown open codes — and the runner
asserts, per `assert_unknown_vector`: the decoder (a) never raises,
(b) lands unknown tags on the registered Unknown fallback types,
(c) sweeps unknown envelope keys into `extensions`, and (d) preserves
everything verbatim through a `to_dict()` round trip (`semantic_equal`),
so nothing is lost on the way to a future revision that names it. The
vector shape and `expect` vocabulary are documented in `spec/README.md`
("Normative unknown-X fixtures").

Args:
    directory: The folder of unknown-X vectors to check.
    decode: The decoder under test (canonical document dict → IR
        object); use `pattern` to select the vectors this decoder
        handles (e.g. `"message_*.json"`).
    pattern: The glob selecting vector files.

Returns:
    The list of vector paths that were checked.

Raises:
    AssertionError: If any vector fails, or none are found.
````

## `ocai.convert.contract`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/convert/contract.py)

### `LossGrade` { #ocai-convert-contract-lossgrade }

```python
type LossGrade = tuple[int, int, int, int]
```

### `DeclaredDisposition` { #ocai-convert-contract-declareddisposition }

```python
class DeclaredDisposition:
    disposition: Disposition
    note: str = ''
```

````text
One census entry: the declared fate of one field, with its rationale.

The value side of `EdgeContract.census`. Kept as a named object (not a
bare `Disposition`) so every declared loss can carry the author's
explanation — the note surfaces verbatim in lockfiles and audit reviews.

Attributes:
    disposition: What the edge declares it does to the field.
    note: The author's one-line rationale for the mapping or the loss.
````

### `ContractViolation` { #ocai-convert-contract-contractviolation }

```python
class ContractViolation:
    path: str
    actual: Disposition | None = None
    declared: Disposition | None = None
    shift_kind: str | None = None
    note: str = ''
```

````text
One certified breach: a runtime record that exceeds the declaration.

Produced by `EdgeContract.certify`, for either lane of the contract: a
`FieldLoss` exceeding the census, or a `SemanticShift` the contract
never declared. A violation is a shipping blocker, not a report entry:
the conformance harness fails the build on any non-empty violation
list, because an undeclared loss is exactly the silent dishonesty the
contract system exists to prevent.

Attributes:
    path: The path the runtime record was recorded at.
    actual: The disposition the edge actually applied at run time; None
        on a semantic-shift violation (shifts have no disposition).
    declared: The disposition the census declared for the path — None
        when the path was not in the census at all, or on a
        semantic-shift violation.
    shift_kind: The runtime `SemanticShift.kind` on a shift violation;
        None on a field-loss violation.
    note: A human-readable explanation of the breach.
````

### `EdgeContract` { #ocai-convert-contract-edgecontract }

```python
class EdgeContract:
    census: Mapping[str, DeclaredDisposition] = field(default_factory=dict[str, DeclaredDisposition])
    semantic_shifts: tuple[SemanticShift, ...] = ()
    note: str = ''
```

````text
An edge's declared per-field disposition census (§4.2).

Attached to every `Edge` and `StreamEdge` in a `CatalogFragment`. Fields
*not* in the census are implicitly declared `EXACT`: the census names
only what the edge renames, approximates, emulates, banks in
`extensions`, drops, or cannot support — so a truly lossless edge ships
an empty census and grades `(0, 0, 0, 1)`.

Attributes:
    census: The declared mapping from field path (dotted/bracketed, e.g.
        `"messages[].parts[].args_json"`) to its `DeclaredDisposition`.
    semantic_shifts: The semantics-level divergences the edge declares
        up front (relocations, emulations, id regeneration). Runtime
        `SemanticShift` records are certified against these the same way
        runtime losses are certified against `census`.
    note: A human-readable summary of what the edge converts.
````

#### `EdgeContract.loss_grade` { #ocai-convert-contract-edgecontract-loss-grade }

```python
def loss_grade(self) -> LossGrade
```

````text
Derive this edge's lexicographic planner cost from the census.

The only source of planner weight in the system — there is no
author-declared number to tune. Counts census entries per lossy
disposition band; `EXACT`, `RENAMED`, and `EXTENSIONS` entries cost
nothing (the information survives recoverably). The trailing `1` is
this edge's hop contribution: path grades are summed elementwise, so
equally-lossy plans prefer fewer hops.

Returns:
    The `(unsupported+dropped, approximated, emulated, hops=1)`
    grade for one traversal of this edge.
````

#### `EdgeContract.certify` { #ocai-convert-contract-edgecontract-certify }

```python
def certify(self, runtime_losses: Iterable[FieldLoss], runtime_shifts: Iterable[SemanticShift]=()) -> list[ContractViolation]
```

````text
Check runtime loss and shift records against this declaration.

The certification half of the contract: called by the conformance
harness (`ocai.convert.conformance.certify_edge`) with the
`FieldLoss` and `SemanticShift` records an edge function actually
emitted over golden fixtures. Runtime records milder than declared
are fine — a contract is an upper bound, not an exact prediction —
and declared-but-unexercised entries (census or shifts) produce no
violation: a contract is an upper bound, not an exercise checklist.
The semantics below are **normative** for every language port.

**Severity partial order.** `actual` is within `declared` iff
`actual == declared` or `actual` sits in a strictly lower band of
`EXACT < RENAMED/EXTENSIONS < APPROXIMATED/EMULATED <
DROPPED/UNSUPPORTED`. Distinct dispositions sharing a band are
*incomparable*: declaring `APPROXIMATED` never licenses running
`EMULATED` (they occupy different `LossGrade` slots, so the swap
would falsify the lockfile's grade), declaring `RENAMED` never
licenses `EXTENSIONS`, and declaring `DROPPED` never licenses
`UNSUPPORTED` — same-band substitution is a violation.

**Path matching.** A path is its token sequence of names and
bracket tokens (`"messages[0].parts[2].is_error"` is name
`messages`, bracket `0`, name `parts`, bracket `2`, name
`is_error`). A census path covers a runtime path iff the sequences
have the same length and token kinds position by position, every
name is equal verbatim, and every census bracket token matches the
runtime one: a concrete index (ASCII digits, e.g. `[0]`) matches
only the identical token; the empty wildcard `[]` and non-numeric
selector tokens (e.g. `[reasoning]`, `[1:]`) match any runtime
bracket token. There is no prefix matching — a census entry for a
parent path never governs a child path.

**Reserved recursive-descent token.** The census token `[**]` is
RESERVED for "this entry covers any suffix below this point" —
recursive descent, needed for unbounded trees (a vectorstore filter
tree has no fixed depth). It MUST NOT be used today: the current
parser would treat `**` as an ordinary non-numeric selector (one
level, any bracket token), silently under-covering. The
implementation lands with the vectorstore capability.

**Resolution per runtime loss.** (1) *Exact-path precedence*: when
the census holds the runtime path verbatim, that entry alone
governs. (2) Otherwise the record is within declaration when it is
within *any* pattern-matching entry — selector entries such as
`parts[text]`/`parts[reasoning]` deliberately overlap on the same
index space because a path alone cannot discriminate content
types, so the census bounds the edge through the most permissive
matching declaration. (3) Otherwise the path is undeclared and
therefore implicitly `EXACT`: any non-`EXACT` record is a
violation carrying `declared=None`.

**Shift certification.** A runtime `SemanticShift` is within
declaration iff some declared shift has the same `kind` and its
path covers the runtime path: a declared empty path covers any
location; otherwise the declared path must cover the runtime path
under the path-matching rule above (a runtime shift with an empty
path is covered only by a kind-matching declaration whose path is
also empty). Notes are never compared. An uncovered shift is a
violation carrying `shift_kind` and no dispositions.

Args:
    runtime_losses: The field-level records one or more runs of the
        edge function emitted.
    runtime_shifts: The semantics-level records the same runs
        emitted, certified against `semantic_shifts`.

Returns:
    The violations found, empty when the runtime stayed within the
    declaration. Non-empty means the edge cannot ship.
````

## `ocai.convert.graph`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/convert/graph.py)

### `EdgeOutput` { #ocai-convert-graph-edgeoutput }

```python
class EdgeOutput:
    value: Any
    losses: tuple[FieldLoss, ...] = ()
    shifts: tuple[SemanticShift, ...] = ()
```

````text
The result of running one conversion edge on a payload.

Attributes:
    value: The converted payload, in the destination node's
        representation.
    losses: The actual field-level records this edge incurred, in order.
    shifts: The actual semantics-level records this edge incurred, in
        order.
````

### `EdgeFn` { #ocai-convert-graph-edgefn }

```python
EdgeFn = Callable[[Any], EdgeOutput]
```

### `Edge` { #ocai-convert-graph-edge }

```python
class Edge:
    src: NodeId
    dst: NodeId
    fn: EdgeFn
    contract: EdgeContract
    origin: Origin
    note: str = ''
```

````text
A directed conversion edge between two graph nodes.

The unit a `CatalogFragment` declares and a `ConversionGraph` plans over.
Its planner cost is derived from `contract.loss_grade()` — the edge
author declares dispositions, never a number.

Attributes:
    src: The source node this edge converts from.
    dst: The destination node this edge converts to. Must share `src`'s
        `Shape` — an edge never crosses message shapes.
    fn: The transform applied to the payload when traversing this edge.
    contract: The declared per-field disposition census; the planner
        weight and the conformance certification baseline.
    origin: Which distribution shipped this edge — surfaces in lockfiles
        and audit records.
    note: A human-readable note describing what the conversion does.
````

### `StreamConverter` { #ocai-convert-graph-streamconverter }

```python
class StreamConverter(Protocol)
```

````text
One live transducer instance converting a chunk stream across an edge.

Built per stream traversal by `StreamEdge.build()`; stateful by design
(it buffers partial events, correlates deltas, seals parts). The driver
pumps decoded wire events through `feed` and calls `flush` exactly once
when the stream ends, collecting both the tail events and the edge's
`EdgeReport` — which the facade folds into the terminal `StreamEnd`
report so streaming has honesty parity with complete calls.
````

#### `StreamConverter.feed` { #ocai-convert-graph-streamconverter-feed }

```python
def feed(self, event: Any) -> list[Any]
```

````text
Consume one upstream event and emit zero or more downstream ones.

A transducer may buffer (returning `[]`), pass through, split one
event into several, or coalesce several into one.

Args:
    event: The next event in the source node's representation.

Returns:
    The events ready to emit, in the destination node's
    representation, in order.
````

#### `StreamConverter.flush` { #ocai-convert-graph-streamconverter-flush }

```python
def flush(self) -> tuple[list[Any], EdgeReport]
```

````text
Finish the stream: drain buffers and account for the traversal.

Called exactly once, after the last `feed`. Aborted streams flush
too — sealing in-flight state incomplete rather than dropping it.

Returns:
    The remaining events to emit, and the `EdgeReport` of losses
    and shifts this traversal incurred.
````

### `StreamConverterFactory` { #ocai-convert-graph-streamconverterfactory }

```python
StreamConverterFactory = Callable[[], StreamConverter]
```

### `StreamEdge` { #ocai-convert-graph-streamedge }

```python
class StreamEdge:
    src: NodeId
    dst: NodeId
    factory: StreamConverterFactory
    contract: EdgeContract
    origin: Origin
    note: str = ''
```

````text
A directed streaming-conversion edge: a transducer factory.

The chunk-shape sibling of `Edge`, planned by the same Dijkstra
machinery over the same contract-derived grades — streaming conversion
joins the graph instead of bypassing it. Where an `Edge` maps one whole
payload, a `StreamEdge` builds a stateful `StreamConverter` per stream
and converts events incrementally.

Attributes:
    src: The source chunk-shape node.
    dst: The destination chunk-shape node. Must share `src`'s `Shape`.
    factory: Builds a fresh transducer instance for one traversal.
    contract: The declared census; planner weight is derived from it,
        identically to payload edges.
    origin: Which distribution shipped this edge.
    note: A human-readable note describing what the conversion does.
````

#### `StreamEdge.build` { #ocai-convert-graph-streamedge-build }

```python
def build(self) -> StreamConverter
```

````text
Return a fresh, stateful transducer for one stream traversal.

Returns:
    A new `StreamConverter`; never shared across streams.
````

### `StreamPipeline` { #ocai-convert-graph-streampipeline }

```python
class StreamPipeline
```

````text
The composite transducer executing one planned stream path.

Built by `ConversionGraph.stream_converter` — one per stream traversal,
never shared or reused. The planned path is cached; the transducer
instances never are: construction calls `StreamEdge.build()` once per
planned edge, so every traversal gets fresh, unshared state. `feed` pipes
each event through every stage in path order; `flush` drains the stages
front-to-back (a front stage's tail is fed through the stages behind it)
and concatenates one `EdgeReport` per stage, in path order.

The driver/facade seam (settled in WU-09): the driver pumps decoded
`SSEvent`s through `feed` and yields the converted events; when the wire
is exhausted (or aborts) it calls `flush` exactly once, yielding the tail
events. The per-edge flush reports are then exposed on `reports`, and the
facade — which built this pipeline and handed it to the driver — reads
them after iteration and folds them into the terminal `StreamEnd.report`
beside the request-leg report, so streaming conversion pays the same
visible toll as unary conversion.
````

#### `StreamPipeline.__init__` { #ocai-convert-graph-streampipeline---init-- }

```python
def __init__(self, edges: tuple[StreamEdge, ...]) -> None
```

````text
Build one fresh transducer per planned edge.

Args:
    edges: The planned stream path, in traversal order. Empty for an
        identity plan (`src == dst`), in which case `feed` passes
        events through untouched.
````

#### `StreamPipeline.edges` { #ocai-convert-graph-streampipeline-edges }

```python
@property
def edges(self) -> tuple[StreamEdge, ...]
```

````text
Return the planned stream edges this pipeline traverses, in order.
````

#### `StreamPipeline.reports` { #ocai-convert-graph-streampipeline-reports }

```python
@property
def reports(self) -> tuple[EdgeReport, ...] | None
```

````text
Return the per-edge flush accounting, or None before `flush` ran.

The facade's half of the WU-09 seam: after the driver exhausts the
stream (which flushes this pipeline), read this and fold each report
into the terminal `StreamEnd.report`.
````

#### `StreamPipeline.feed` { #ocai-convert-graph-streampipeline-feed }

```python
def feed(self, event: Any) -> list[Any]
```

````text
Pipe one event through every stage, in path order.

Args:
    event: The next event in the path's source representation.

Returns:
    The converted events ready to emit, in the path's destination
    representation, in order — empty while stages buffer. With no
    stages (an identity plan) the event passes through unchanged.
````

#### `StreamPipeline.flush` { #ocai-convert-graph-streampipeline-flush }

```python
def flush(self) -> tuple[list[Any], tuple[EdgeReport, ...]]
```

````text
Finish the stream: drain every stage and collect the accounting.

Drains front-to-back: each stage's flush tail is fed through the
stages behind it before the next stage flushes, so composition
preserves event order. Aborted streams are flushed too (the driver
flushes on its error path), sealing in-flight state and keeping the
accounting rather than dropping both.

Returns:
    The remaining events to emit, and one `EdgeReport` per stage in
    path order — the same tuple exposed on `reports` afterwards.

Raises:
    RuntimeError: If called more than once — a pipeline serves a
        single traversal by contract.
````

### `Converted` { #ocai-convert-graph-converted }

```python
class Converted:
    value: Any
    report: FidelityReport
```

````text
The result of a graph conversion: the output value plus its report.

Attributes:
    value: The converted payload at the destination node.
    report: The `FidelityReport` accumulated along the path — one
        `EdgeReport` per traversed edge, in order.
````

### `ConversionError` { #ocai-convert-graph-conversionerror }

```python
class ConversionError(LookupError)
```

````text
Raised when no conversion path exists between two graph nodes.
````

### `ConversionGraph` { #ocai-convert-graph-conversiongraph }

```python
class ConversionGraph
```

````text
Edges for one `Shape`, with cached contract-graded shortest-path plans.

Owned and populated by a `Catalog` (which partitions one graph per
shape); user code converts through `Catalog.convert`, which delegates
here. Registration is idempotent so composing overlapping fragments is
safe. Structural honesty rules the graph is responsible for (e.g. a
`ProviderRef` crossing its minting `(provider, interface)` is
`UNSUPPORTED`-and-reported) are enforced by the edge functions and
certified by conformance; the planner itself only routes.
````

#### `ConversionGraph.__init__` { #ocai-convert-graph-conversiongraph---init-- }

```python
def __init__(self) -> None
```

````text
Construct an empty graph with no edges and empty plan caches.
````

#### `ConversionGraph.register` { #ocai-convert-graph-conversiongraph-register }

```python
def register(self, edge: Edge) -> None
```

````text
Register a directed conversion edge. Idempotent.

Registering an identical edge again is a no-op, so composing
overlapping fragments is safe. Register both directions explicitly
if the conversion is bidirectional (they will have different
contracts — decode and encode rarely cost the same).

Args:
    edge: The edge to add.

Raises:
    ValueError: If the edge's endpoints have different `Shape`s —
        graphs never mix shapes; conflicting directed edges or node metadata are rejected.
````

#### `ConversionGraph.register_stream` { #ocai-convert-graph-conversiongraph-register-stream }

```python
def register_stream(self, edge: StreamEdge) -> None
```

````text
Register a directed streaming-conversion edge. Idempotent.

Args:
    edge: The transducer-factory edge to add.

Raises:
    ValueError: If shapes differ or a directed edge/node declaration conflicts.
````

#### `ConversionGraph.inspect` { #ocai-convert-graph-conversiongraph-inspect }

```python
def inspect(self, src: NodeId, dst: NodeId, *, streaming: bool=False) -> tuple[EdgeDeclaration, ...]
```

````text
Inspect a path without executing converters or constructing transducers.
````

#### `ConversionGraph.convert` { #ocai-convert-graph-conversiongraph-convert }

```python
def convert(self, payload: Any, src: NodeId, dst: NodeId) -> Converted
```

````text
Convert `payload` from node `src` to node `dst`.

Composes the edge functions along the cheapest planned path and
returns a `Converted` carrying the output value and the
`FidelityReport` accumulated along the way — one `EdgeReport`
(losses, shifts, note) per traversed edge.

Args:
    payload: The input payload, in `src`'s representation.
    src: The source node.
    dst: The destination node.

Returns:
    A `Converted` with the output value and its `FidelityReport`.

Raises:
    ConversionError: If no path exists from `src` to `dst`.
````

#### `ConversionGraph.stream_converter` { #ocai-convert-graph-conversiongraph-stream-converter }

```python
def stream_converter(self, src: NodeId, dst: NodeId) -> StreamPipeline
```

````text
Plan and build the composite transducer converting chunks `src -> dst`.

The streaming twin of `convert`: plans a `StreamEdge` path with the
same contract-graded Dijkstra (via `_plan_stream`, with its own plan
cache), then chains one freshly-built (`StreamEdge.build`) transducer
per planned edge into a `StreamPipeline` — the plan is cached, the
transducer instances never are. The driver pumps SSE-decoded events
through the result and the facade reads the flush accounting off
`StreamPipeline.reports` for the terminal `StreamEnd.report` (the
WU-09 seam).

Args:
    src: The source chunk-shape node.
    dst: The destination chunk-shape node.

Returns:
    A fresh `StreamPipeline` for one stream traversal.

Raises:
    ConversionError: If no stream-edge path exists.
````

#### `ConversionGraph.can_convert` { #ocai-convert-graph-conversiongraph-can-convert }

```python
def can_convert(self, src: NodeId, dst: NodeId) -> bool
```

````text
Return whether any conversion path exists from `src` to `dst`.

Args:
    src: The source node.
    dst: The destination node.

Returns:
    True if a path exists (or `src == dst`), False otherwise. Never
    raises; a missing path is reported as False rather than
    propagated.
````

## `ocai.convert.host_effects`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/convert/host_effects.py)

### `HostEffectContract` { #ocai-convert-host-effects-hosteffectcontract }

```python
class HostEffectContract:
    census: Mapping[str, DeclaredDisposition] = field(default_factory=dict[str, DeclaredDisposition])
    semantic_shifts: tuple[SemanticShift, ...] = ()
```

````text
A declared host-effect bound, not a graph edge or certification verdict.
````

#### `HostEffectContract.to_dict` { #ocai-convert-host-effects-hosteffectcontract-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize only declarative content, without graph weights or callbacks.
````

#### `HostEffectContract.identity` { #ocai-convert-host-effects-hosteffectcontract-identity }

```python
@property
def identity(self) -> str
```

````text
Hash declaration content deterministically, independently from execution.
````

#### `HostEffectContract.certify` { #ocai-convert-host-effects-hosteffectcontract-certify }

```python
def certify(self, losses: Iterable[FieldLoss], shifts: Iterable[SemanticShift]) -> list[ContractViolation]
```

````text
Check findings with the same partial order and path rules as codecs.
````

### `HostEffectDeclaration` { #ocai-convert-host-effects-hosteffectdeclaration }

```python
class HostEffectDeclaration:
    host: str
    adapter: str
    contract: HostEffectContract
    configuration_id: str
    conformance_evaluated: bool = False
```

````text
Detached inspection data; no executable callback or qualification claim.
````

### `HostContractError` { #ocai-convert-host-effects-hostcontracterror }

```python
class HostContractError(FidelityPolicyError)
```

````text
Host findings exceeded their declaration; rejected payload stays private.
````

#### `HostContractError.__init__` { #ocai-convert-host-effects-hostcontracterror---init-- }

```python
def __init__(self, report: FidelityReport, violations: tuple[ContractViolation, ...], usage: Usage | None=None, route: Route | None=None) -> None
```

````text
Retain accounting and precise contract violations, never response data.
````

## `ocai.convert.hosts`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/convert/hosts.py)

### `HostDescriptor` { #ocai-convert-hosts-hostdescriptor }

```python
class HostDescriptor:
    base_url: str
    paths: Mapping[str, str] = field(default_factory=dict[str, str])
    path_prefix: str = ''
    streaming_paths: Mapping[str, str] = field(default_factory=dict[str, str])
    static_headers: Mapping[str, str] = field(default_factory=dict[str, str])
    query: Mapping[str, str] = field(default_factory=dict[str, str])
    profile_aliases: Mapping[str, str] = field(default_factory=dict[str, str])
    profile_suffixes: tuple[str, ...] = ()
```

````text
Pure host data, explicitly selected by a caller rather than auto-routed.

Attributes:
    base_url: Explicit HTTP(S) origin, optionally including a base path.
    paths: Unary operation-kind path templates; only `{resource}` is supported.
    path_prefix: Path prepended to the selected native or remapped path.
    streaming_paths: Stream-specific templates, falling back to `paths`.
    static_headers: Non-secret host headers, overriding dialect defaults.
    query: Explicit query values, independent of path and version headers.
    profile_aliases: Exact resource-to-profile-key aliases; wire names stay intact.
    profile_suffixes: Explicit suffixes to remove once for profile lookup only.
````

## `ocai.convert.inspection`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/convert/inspection.py)

### `EdgeDeclaration` { #ocai-convert-inspection-edgedeclaration }

```python
class EdgeDeclaration:
    src: NodeId
    dst: NodeId
    origin: Origin
    contract: EdgeContract
```

````text
One selected edge's declaration; no executable callable is exposed.
````

### `ConversionInspection` { #ocai-convert-inspection-conversioninspection }

```python
class ConversionInspection:
    src: NodeId
    dst: NodeId
    edges: tuple[EdgeDeclaration, ...]
    catalog_hash: str
    streaming: bool = False
    resources: tuple[ConformanceResources, ...] = ()
    conformance_evaluated: bool = False
```

````text
Selected path and resource locations, distinct from conformance verdicts.
````

### `FeatureCoverage` { #ocai-convert-inspection-featurecoverage }

```python
class FeatureCoverage:
    feature: str
    path: str
    support: Support | None
    model_pattern: str | None = None
```

````text
Declared support for a recognized request feature; None means unknown.
````

### `ExecutionInspection` { #ocai-convert-inspection-executioninspection }

```python
class ExecutionInspection:
    route: Route
    request_path: ConversionInspection
    response_path: ConversionInspection
    profiles: tuple[CapabilityProfile, ...]
    coverage: tuple[FeatureCoverage, ...]
    request_report: FidelityReport
    configuration_id: str
    streaming: bool = False
    coverage_complete: bool = False
    host_effects: tuple[HostEffectDeclaration, ...] = field(default=(), kw_only=True)
```

````text
Detached inspection data; none of these declarations proves qualification.

Request findings are payload-specific. Response findings are not known yet.
Coverage enumerates recognized feature keys, never the complete open feature
universe. Resource locations are evidence pointers, not certification results.
Configuration identity excludes credentials, which rotate at the transport leaf.
````

## `ocai.convert.migrate`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/convert/migrate.py)

### `register_revision_migration` { #ocai-convert-migrate-register-revision-migration }

```python
def register_revision_migration(builder: CatalogBuilder, src_rev: str, dst_rev: str, edges: Iterable[Edge]) -> None
```

````text
Stage certified migration edges between two canonical revisions.

Wraps `edges` in an ocai-originated `CatalogFragment` that publishes the
canonical nodes for `src_rev` and `dst_rev` and adds it to `builder`, so
the migration participates in planning, lockfiles, and admission exactly
like provider conversion logic. Every edge must connect canonical nodes
at the two named revisions — a migration never touches provider
interfaces (cross-provider paths reach it through the canonical
backbone).

Args:
    builder: The catalog composition to stage the migration into.
    src_rev: The older canonical revision tag (e.g. `"2026-07"`).
    dst_rev: The newer canonical revision tag (e.g. `"2027-01"`).
    edges: The migration edges, one per shape and direction, each
        carrying its `EdgeContract` (forward edges are typically
        lossless; backward edges declare what the older revision cannot
        express).

Raises:
    ValueError: If an edge endpoint is not a canonical node at
        `src_rev` or `dst_rev`.
````

## `ocai.convert.resources`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/convert/resources.py)

### `ConformanceResources` { #ocai-convert-resources-conformanceresources }

```python
class ConformanceResources:
    package: str
    fixtures: str = 'conformance/fixtures'
    extensions: str | None = None
```

````text
Locations shipped inside an independently installed plugin wheel.

Catalogs record this manifest without reading it. Only the conformance
harness loads files. Schema validators are supplied by the test suite.

Attributes:
    package: Importable package owning the resources.
    fixtures: Relative directory containing JSON edge fixtures.
    extensions: Optional relative directory containing extension value schemas.
````

### `ConformanceBundle` { #ocai-convert-resources-conformancebundle }

```python
class ConformanceBundle:
    fixtures: dict[str, dict[str, Any]]
    extensions: dict[str, dict[str, Any]]
```

````text
Loaded fixtures and schemas for explicit test-suite use.

Fixture names include distribution provenance. Extension schemas describe
one bag value each; callers supply their validator and select canonical
extension bags, avoiding accidental traversal into arbitrary raw JSON.
````

#### `ConformanceBundle.check_extension_bag` { #ocai-convert-resources-conformancebundle-check-extension-bag }

```python
def check_extension_bag(self, bag: dict[str, Any], *, validate: Callable[[dict[str, Any], Any], None]) -> None
```

````text
Validate every key/value in one canonical extension bag.

Args:
    bag: A canonical object's extension bag.
    validate: Test-suite callback accepting schema then instance;
        it must raise on invalid data.

Raises:
    AssertionError: If a key has no registered schema.
````

### `load_conformance_resources` { #ocai-convert-resources-load-conformance-resources }

```python
def load_conformance_resources(*fragments: CatalogFragment) -> ConformanceBundle
```

````text
Load explicitly declared resources from installed packages.

No files are fetched from a network and no schema validator is imported.
Loading resources may import the declared Python package, like ordinary
entry-point loading; this is not a sandbox or publisher authentication.

Args:
    fragments: Fragments whose independently packaged resources to load.

Returns:
    The combined bundle. A fragment without a manifest contributes nothing.

Raises:
    ValueError: If resources are missing, empty, malformed, or conflicting.
````
