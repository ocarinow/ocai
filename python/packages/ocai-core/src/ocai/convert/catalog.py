"""Scoped, governed conversion registries (§4.3).

The old process-global `GRAPHS`/`SCHEMAS`/`COMPONENTS` are gone. A plugin
exports one frozen, declarative `CatalogFragment` — data, no import-time
mutation of any shared state — and an application composes exactly the
fragments it trusts:

    catalog = Catalog.of(openai.FRAGMENT, anthropic.FRAGMENT)

`Catalog.discover()` (entry points, group `ocai.fragments`) is an opt-in
convenience for "compose everything installed"; `default_catalog()` memoizes
it and is deliberately the **only** module-level state in `ocai.convert`.

Admission is governed by a `TrustPolicy` (default `OWNED_ENDPOINTS`: a
fragment may only register edges touching interfaces it publishes or the
canonical `ocai` interface — foreign bridging needs a named opt-in), and the
whole composition is auditable: `Catalog.lock()` emits a diffable lockfile
whose content hash (computed via `ocai.core.canonjson.canonical`) lands in
every `Route` the catalog resolves.

Internally the catalog partitions one `ConversionGraph` per `Shape` (graphs
never mix shapes) and delegates `convert`/`stream_converter` to the right
partition.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import replace
from enum import Enum
from functools import cache
from importlib.metadata import entry_points
from typing import Any
from typing import Self

from ocai.convert.graph import ConversionError
from ocai.convert.graph import ConversionGraph
from ocai.convert.graph import Converted
from ocai.convert.graph import Edge
from ocai.convert.graph import StreamEdge
from ocai.convert.graph import StreamPipeline
from ocai.convert.resources import ConformanceResources
from ocai.core.canonjson import canonical
from ocai.core.errors import OcaiError
from ocai.core.fidelity import Route
from ocai.core.identity import CANONICAL_INTERFACE
from ocai.core.identity import CANONICAL_PROVIDER
from ocai.core.identity import Capability
from ocai.core.identity import NodeId
from ocai.core.identity import Origin
from ocai.core.identity import Shape
from ocai.core.identity import Status
from ocai.core.profile import CapabilityProfile
from ocai.core.traits import DialectTraits

# The entry-point group a plugin distribution advertises its fragment under
# (`[project.entry-points."ocai.fragments"] openai = "ocai.openai:FRAGMENT"`).
# Supersedes the old `ocai.plugins` group of register-callables: the entry
# point now names *data* (a `CatalogFragment`, or a zero-argument callable
# returning one), never a function that mutates globals.
ENTRY_POINT_GROUP = "ocai.fragments"

# A component factory builds a runtime object (codec, adapter) for one
# resolved `(provider, interface, capability)`. Opaque to the catalog — the
# plugin owns its signature; the catalog only stores it and hands it back.
type ComponentFactory = Callable[..., Any]


class TrustPolicy(str, Enum):
    """How a `CatalogBuilder` admits fragments — the governance dial.

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
    """

    OWNED_ENDPOINTS = "owned_endpoints"
    ALLOW_LISTED = "allow_listed"


class AdmissionError(OcaiError):
    """Raised when a fragment fails the composing `TrustPolicy`'s checks."""


class ResolutionError(OcaiError):
    """Raised when `Catalog.resolve` cannot satisfy a request or its pins."""


@dataclass(frozen=True, slots=True)
class Component:
    """A runtime factory a fragment contributes for one resolved interface.

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
    """

    provider: str
    interface: str
    capability: Capability
    factory: ComponentFactory


@dataclass(frozen=True, slots=True)
class CatalogFragment:
    """Everything one distribution contributes to a catalog — as frozen data.

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
    """

    origin: Origin
    nodes: tuple[NodeId, ...] = ()
    edges: tuple[Edge, ...] = ()
    transducers: tuple[StreamEdge, ...] = ()
    profiles: tuple[CapabilityProfile, ...] = ()
    traits: tuple[DialectTraits, ...] = ()
    components: tuple[Component, ...] = ()
    conformance: ConformanceResources | None = None


def _snapshot(fragment: CatalogFragment) -> CatalogFragment:
    """Copy declaration mappings without copying executable callables."""

    def edge_copy[E: (Edge, StreamEdge)](edge: E) -> E:
        return replace(edge, contract=replace(edge.contract, census=dict(edge.contract.census)))

    return replace(
        fragment,
        edges=tuple(edge_copy(edge) for edge in fragment.edges),
        transducers=tuple(edge_copy(edge) for edge in fragment.transducers),
        profiles=tuple(replace(p, features=dict(p.features)) for p in fragment.profiles),
        traits=tuple(
            replace(t, first_party_headers=dict(t.first_party_headers)) for t in fragment.traits
        ),
    )


def _canonical(node: NodeId) -> bool:
    return node.provider == CANONICAL_PROVIDER and node.interface == CANONICAL_INTERFACE


@dataclass(frozen=True, slots=True)
class CatalogLock:
    """The diffable description of one composed catalog, content-hashed.

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
    """

    hash: str
    payload: dict[str, Any]

    def to_json(self) -> str:
        """Render the lockfile as stable, indented, diff-friendly JSON.

        Returns:
            The payload serialized with sorted keys and two-space indents —
            the form meant to be committed to version control.
        """
        return json.dumps(self.payload, sort_keys=True, indent=2, ensure_ascii=False)


def _admit(fragment: CatalogFragment, trust: TrustPolicy, allow: frozenset[str]) -> None:
    """Check `fragment` against the trust policy; raise on violation.

    The single admission gate shared by `CatalogBuilder.add` (fail fast at
    composition) and `Catalog.__init__` (so a directly-constructed catalog
    cannot bypass governance). Two checks run, in order:

    1. **Endpoint ownership** (the trust check). Under `OWNED_ENDPOINTS`,
       every edge endpoint must be canonical or on a
       `(provider, interface)` the fragment's own `nodes` publish; under
       `ALLOW_LISTED`, fragments named in `allow` are exempt from this
       check only.
    2. **Canonical-backbone connectivity** (applies under every trust
       policy — allow-listing buys foreign bridging, never a disconnected
       backbone). The exact rule, per non-canonical
       `(provider, interface)` the fragment publishes nodes for: if the
       fragment registers at least one edge or transducer touching that
       interface, then at least one of them must have its *other* endpoint
       on the canonical `ocai` interface. Interfaces published with zero
       touching edges are admitted as declared stubs — resolvable and
       pinnable, but performing no conversions (e.g. an interface whose
       codec has not yet earned its census). This is the pragmatic
       per-interface-overall check; the per-shape refinement (one
       canonical-touching edge for *each* shape the interface publishes)
       is deliberately deferred until a real fragment needs it.

    Args:
        fragment: The fragment seeking admission.
        trust: The composing application's policy.
        allow: Distribution names granted foreign-bridging opt-in.

    Raises:
        AdmissionError: If any edge touches an interface the fragment
            neither owns nor is allowed to bridge, or if a published
            interface registers conversions without a single edge
            connecting it to the canonical backbone.
    """
    owned = {(node.provider, node.interface) for node in fragment.nodes}
    every_edge: tuple[Edge | StreamEdge, ...] = (*fragment.edges, *fragment.transducers)
    exempt = trust is TrustPolicy.ALLOW_LISTED and fragment.origin.distribution in allow
    if not exempt:
        for edge in every_edge:
            for endpoint in (edge.src, edge.dst):
                if _canonical(endpoint):
                    continue
                if (endpoint.provider, endpoint.interface) not in owned:
                    raise AdmissionError(
                        f"fragment {fragment.origin} registers an edge touching "
                        f"{endpoint.provider}/{endpoint.interface}, which it does not publish; "
                        f"foreign bridging requires TrustPolicy.ALLOW_LISTED with "
                        f"{fragment.origin.distribution!r} in the allow set"
                    )
    # Canonical-backbone connectivity: for each published non-canonical
    # interface, track whether any edge touches it (participates) and whether
    # any of those edges reaches canonical on the other side (connected).
    published = {key for key in owned if key[0] != CANONICAL_PROVIDER}
    connected: dict[tuple[str, str], bool] = {}
    for edge in every_edge:
        for endpoint, other in ((edge.src, edge.dst), (edge.dst, edge.src)):
            key = (endpoint.provider, endpoint.interface)
            if key in published:
                touches_canonical = _canonical(other)
                connected[key] = connected.get(key, False) or touches_canonical
    for key in sorted(connected):
        if not connected[key]:
            provider, interface = key
            raise AdmissionError(
                f"fragment {fragment.origin} publishes {provider}/{interface} and "
                f"registers edges touching it, but none of them connects it to the "
                f"canonical backbone; every converting interface needs at least one "
                f"edge or transducer whose other endpoint is canonical (publish the "
                f"interface nodes-only to ship it as a conversionless stub)"
            )


def _channel_allows(channel: Status, status: Status) -> bool:
    """Return whether a node with `status` is auto-selectable under `channel`.

    `STABLE` admits only stable nodes; `PREVIEW` admits stable and preview;
    `DEPRECATED` additionally admits deprecated. `RETIRED` nodes are never
    auto-selected — they stay reachable only when pinned by tag, existing so
    archived traffic can still be re-converted through migration edges.

    Args:
        channel: The lowest channel eligible for auto-selection.
        status: The candidate node's status.

    Returns:
        True if `status` is eligible under `channel`.
    """
    rank = {Status.STABLE: 0, Status.PREVIEW: 1, Status.DEPRECATED: 2, Status.RETIRED: 3}
    return rank[status] <= rank[channel] and status is not Status.RETIRED


def _literal_prefix_len(pattern: str) -> int:
    """Return the length of a glob pattern's leading literal run.

    The specificity key `Catalog.profiles_for` ranks profiles by: the number
    of characters before the pattern's first wildcard metacharacter
    (`*`, `?`, or `[`). A fully literal pattern is maximally specific;
    `"*"` scores zero.

    Args:
        pattern: The glob-style `model_pattern` to measure.

    Returns:
        The count of leading non-wildcard characters.
    """
    for index, char in enumerate(pattern):
        if char in "*?[":
            return index
    return len(pattern)


class CatalogBuilder:
    """Accumulates admission-checked fragments and builds an immutable `Catalog`.

    The mutable composition step, deliberately separate from the immutable
    result: `add` fails fast at the offending fragment (naming it), so a
    trust violation surfaces at composition time, never mid-request.

    Interaction: plugins never see a builder — they export data
    (`CatalogFragment`); applications drive the builder (directly, or via
    the `Catalog.of` / `Catalog.discover` conveniences that wrap it).
    """

    def __init__(
        self,
        *,
        trust: TrustPolicy = TrustPolicy.OWNED_ENDPOINTS,
        allow: frozenset[str] = frozenset(),
    ) -> None:
        """Create an empty builder under a trust policy.

        Args:
            trust: The admission policy for every fragment added.
            allow: Distribution names granted foreign-bridging opt-in;
                meaningful only with `TrustPolicy.ALLOW_LISTED`.
        """
        self._trust = trust
        self._allow = allow
        self._fragments: list[CatalogFragment] = []

    @classmethod
    def of(
        cls,
        *fragments: CatalogFragment,
        trust: TrustPolicy = TrustPolicy.OWNED_ENDPOINTS,
        allow: frozenset[str] = frozenset(),
    ) -> Catalog:
        """Compose `fragments` into a catalog in one expression.

        Args:
            fragments: The fragments to admit, in order.
            trust: The admission policy.
            allow: Distribution names granted foreign-bridging opt-in.

        Returns:
            The built, immutable `Catalog`.

        Raises:
            AdmissionError: If any fragment violates the trust policy.
        """
        builder = cls(trust=trust, allow=allow)
        for fragment in fragments:
            builder.add(fragment)
        return builder.build()

    def add(self, fragment: CatalogFragment) -> Self:
        """Admission-check `fragment` and stage it for the build.

        Args:
            fragment: The fragment to admit.

        Returns:
            This builder, for chaining.

        Raises:
            AdmissionError: If the fragment violates the trust policy.
        """
        candidate = _snapshot(fragment)
        Catalog((*self._fragments, candidate), trust=self._trust, allow=self._allow)
        self._fragments.append(candidate)
        return self

    def discover(self, *, group: str = ENTRY_POINT_GROUP) -> Self:
        """Add every fragment advertised by installed distributions.

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
        """
        for ep in sorted(entry_points(group=group), key=lambda ep: ep.name):
            loaded = ep.load()
            fragment = loaded() if callable(loaded) else loaded
            if not isinstance(fragment, CatalogFragment):
                raise TypeError(
                    f"entry point {ep.name!r} in group {group!r} yielded "
                    f"{type(fragment).__name__}, expected a CatalogFragment"
                )
            self.add(fragment)
        return self

    def build(self) -> Catalog:
        """Freeze the staged fragments into an immutable `Catalog`.

        Returns:
            The composed catalog.
        """
        return Catalog(tuple(self._fragments), trust=self._trust, allow=self._allow)


class Catalog:
    """An immutable, provenance-stamped composition of fragments.

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
    """

    def __init__(
        self,
        fragments: Iterable[CatalogFragment] = (),
        *,
        trust: TrustPolicy = TrustPolicy.OWNED_ENDPOINTS,
        allow: frozenset[str] = frozenset(),
    ) -> None:
        """Compose `fragments` into an indexed, immutable catalog.

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
        """
        self._fragments = tuple(_snapshot(fragment) for fragment in fragments)
        self._trust = trust
        self._allow = allow
        self._graphs: dict[Shape, ConversionGraph] = {}
        node_index: dict[NodeId, None] = {}  # insertion-ordered de-dup
        components: dict[tuple[str, str, Capability], Component] = {}
        profiles: list[CapabilityProfile] = []
        coordinates: dict[tuple[str, str, str, Shape], NodeId] = {}
        profile_index: dict[tuple[str, str, str], CapabilityProfile] = {}
        for fragment in self._fragments:
            _admit(fragment, trust, allow)
            all_edges: tuple[Edge | StreamEdge, ...] = (*fragment.edges, *fragment.transducers)
            endpoints = (
                node for conversion in all_edges for node in (conversion.src, conversion.dst)
            )
            for node in (*fragment.nodes, *endpoints):
                node_key = (node.provider, node.interface, node.tag, node.shape)
                if node_key in coordinates and coordinates[node_key] != node:
                    raise AdmissionError(f"conflicting node metadata for {node}")
                coordinates[node_key] = node
            for node in fragment.nodes:
                node_index.setdefault(node, None)
            for edge in fragment.edges:
                try:
                    self._graphs.setdefault(edge.src.shape, ConversionGraph()).register(edge)
                except ValueError as exc:
                    raise AdmissionError(f"{fragment.origin}: {exc}") from exc
            for stream_edge in fragment.transducers:
                try:
                    self._graphs.setdefault(
                        stream_edge.src.shape, ConversionGraph()
                    ).register_stream(stream_edge)
                except ValueError as exc:
                    raise AdmissionError(f"{fragment.origin}: {exc}") from exc
            for profile in fragment.profiles:
                profile_key = (profile.provider, profile.interface, profile.model_pattern)
                if profile_key in profile_index and profile_index[profile_key] != profile:
                    raise AdmissionError(f"conflicting capability profile {profile_key}")
                if profile_key not in profile_index:
                    profiles.append(profile)
                    profile_index[profile_key] = profile
            for component in fragment.components:
                component_key = (component.provider, component.interface, component.capability)
                existing = components.get(component_key)
                if existing is not None and existing.factory is not component.factory:
                    raise AdmissionError(
                        f"fragment {fragment.origin} registers a component for "
                        f"{component.provider}/{component.interface} "
                        f"({component.capability}) already provided by another "
                        f"fragment; refusing to shadow it"
                    )
                components[component_key] = component
        self._nodes = tuple(node_index)
        self._profiles = tuple(profiles)
        self._components = components
        self._lock: CatalogLock | None = None  # computed lazily, then cached

    @classmethod
    def of(
        cls,
        *fragments: CatalogFragment,
        trust: TrustPolicy = TrustPolicy.OWNED_ENDPOINTS,
        allow: frozenset[str] = frozenset(),
    ) -> Catalog:
        """Compose `fragments` into a catalog (delegates to `CatalogBuilder`).

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
        """
        return CatalogBuilder.of(*fragments, trust=trust, allow=allow)

    @classmethod
    def discover(
        cls,
        *,
        trust: TrustPolicy = TrustPolicy.OWNED_ENDPOINTS,
        allow: frozenset[str] = frozenset(),
        group: str = ENTRY_POINT_GROUP,
    ) -> Catalog:
        """Compose everything installed (delegates to `CatalogBuilder.discover`).

        Args:
            trust: The admission policy — discovery grants no extra trust.
            allow: Distribution names granted foreign-bridging opt-in.
            group: The entry-point group to scan.

        Returns:
            The built catalog of all discovered fragments.

        Raises:
            AdmissionError: If a discovered fragment violates the policy.
        """
        return CatalogBuilder(trust=trust, allow=allow).discover(group=group).build()

    @property
    def fragments(self) -> tuple[CatalogFragment, ...]:
        """Return the composed fragments, in admission order."""
        return tuple(_snapshot(fragment) for fragment in self._fragments)

    @property
    def nodes(self) -> tuple[NodeId, ...]:
        """Return every published node, de-duplicated, in admission order."""
        return self._nodes

    def resolve(
        self,
        capability: Capability,
        provider: str,
        *,
        interface: str | None = None,
        tag: str | None = None,
        channel: Status = Status.STABLE,
    ) -> Route:
        """Decide which interface revision serves a call; record it as a `Route`.

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
        """
        candidates = [
            node
            for node in self._nodes
            if node.provider == provider
            and node.capability == capability
            and node.shape.role == "request"
            and (interface is None or node.interface == interface)
        ]
        if not candidates:
            pin = f" (interface pin {interface!r})" if interface is not None else ""
            raise ResolutionError(
                f"no registered interface for {provider}/{capability}{pin} in this catalog"
            )
        if tag is not None:
            pinned = [node for node in candidates if node.tag == tag]
            if not pinned:
                known = ", ".join(sorted({f"{n.interface}@{n.tag}" for n in candidates}))
                raise ResolutionError(
                    f"{provider}/{capability} has no revision {tag!r}; known: {known}"
                )
            _require_one_interface(pinned)
            chosen = max(pinned, key=lambda n: (n.released, str(n)))
            reason = "pinned"
        else:
            eligible = [node for node in candidates if _channel_allows(channel, node.status)]
            if not eligible:
                raise ResolutionError(
                    f"no {channel.value} revision for {provider}/{capability} in this catalog"
                )
            _require_one_interface(eligible)
            chosen = max(eligible, key=lambda n: (n.released, str(n)))
            reason = f"latest {chosen.status.value}, released {chosen.released.isoformat()}"
        return Route(
            capability=capability,
            node=chosen,
            requested_interface=interface,
            requested_tag=tag,
            reason=reason,
            catalog_hash=self.lock().hash,
        )

    def convert(self, payload: Any, src: NodeId, dst: NodeId) -> Converted:
        """Convert `payload` between two nodes of one shape.

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
        """
        if src.shape != dst.shape:
            raise ConversionError(f"cannot convert across shapes: {src.shape} -> {dst.shape}")
        graph = self._graphs.get(src.shape)
        if graph is None:
            raise ConversionError(f"no conversion edges registered for shape {src.shape}")
        return graph.convert(payload, src, dst)

    def stream_converter(self, src: NodeId, dst: NodeId) -> StreamPipeline:
        """Build the composite transducer converting chunk events `src -> dst`.

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
        """
        if src.shape != dst.shape:
            raise ConversionError(f"cannot convert across shapes: {src.shape} -> {dst.shape}")
        graph = self._graphs.get(src.shape)
        if graph is None:
            raise ConversionError(f"no conversion edges registered for shape {src.shape}")
        return graph.stream_converter(src, dst)

    def profiles_for(
        self, provider: str, interface: str, model: str
    ) -> tuple[CapabilityProfile, ...]:
        """Return every `CapabilityProfile` covering `model`, ranked.

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
        """
        matched = [
            profile
            for profile in self._profiles
            if profile.provider == provider
            and profile.interface == interface
            and profile.matches(model)
        ]
        matched.sort(key=lambda p: (-_literal_prefix_len(p.model_pattern), p.model_pattern))
        return tuple(replace(profile, features=dict(profile.features)) for profile in matched)

    def profile(self, provider: str, interface: str, model: str) -> CapabilityProfile | None:
        """Return the most specific `CapabilityProfile` covering `model`.

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
        """
        ranked = self.profiles_for(provider, interface, model)
        return ranked[0] if ranked else None

    def component(self, provider: str, interface: str, capability: Capability) -> ComponentFactory:
        """Return the runtime factory registered for the resolved interface.

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
        """
        component = self._components.get((provider, interface, capability))
        if component is None:
            composed = sorted({p for (p, _, _) in self._components}) or ["none"]
            raise LookupError(
                f"no component for {provider}/{interface} ({capability}) in this catalog. "
                f"Composed providers: {', '.join(composed)}. If the plugin is not "
                f"installed, install it with:  pip install ocai-{provider}"
            )
        return component.factory

    def components_for(self, provider: str, capability: Capability) -> tuple[Component, ...]:
        """Return every component registered for `provider` serving `capability`.

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
        """
        return tuple(
            component
            for (p, _, cap), component in self._components.items()
            if p == provider and cap == capability
        )

    def lock(self) -> CatalogLock:
        """Emit the diffable lockfile describing this composition, hashed.

        Computed once and cached (the catalog is immutable). The hash is the
        SHA-256 of the payload's canonical JSON and is stamped into every
        `Route` this catalog resolves.

        Returns:
            The `CatalogLock` for this exact composition.
        """
        if self._lock is None:
            payload: dict[str, Any] = {
                "format": "ocai.catalog-lock/2",
                "trust": self._trust.value,
                "allow": sorted(self._allow),
                "fragments": [
                    {
                        "origin": str(fragment.origin),
                        "nodes": [_lock_node(node) for node in fragment.nodes],
                        "edges": [_lock_edge(edge) for edge in fragment.edges],
                        "transducers": [_lock_edge(edge) for edge in fragment.transducers],
                        "profiles": [
                            {
                                "provider": profile.provider,
                                "interface": profile.interface,
                                "model_pattern": profile.model_pattern,
                                "features": {
                                    key: support.value
                                    for key, support in sorted(profile.features.items())
                                },
                            }
                            for profile in fragment.profiles
                        ],
                        "components": [
                            {
                                "provider": component.provider,
                                "interface": component.interface,
                                "capability": str(component.capability),
                            }
                            for component in fragment.components
                        ],
                        "traits": [asdict(trait) for trait in fragment.traits],
                        "conformance": (
                            asdict(fragment.conformance)
                            if fragment.conformance is not None
                            else None
                        ),
                    }
                    for fragment in self._fragments
                ],
            }
            for fragment in payload["fragments"]:
                for key in ("nodes", "edges", "transducers", "profiles", "components", "traits"):
                    fragment[key] = sorted(fragment[key], key=canonical)
            payload["fragments"].sort(key=canonical)
            digest = hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
            self._lock = CatalogLock(hash=digest, payload=payload)
        return CatalogLock(hash=self._lock.hash, payload=deepcopy(self._lock.payload))


def _lock_node(node: NodeId) -> dict[str, Any]:
    """Record coordinates structurally as well as their display spelling."""
    return {
        "id": str(node),
        "provider": node.provider,
        "interface": node.interface,
        "tag": node.tag,
        "shape": {"capability": node.capability.name, "role": node.shape.role},
        "released": node.released.isoformat(),
        "status": node.status.value,
    }


def _lock_edge(edge: Edge | StreamEdge) -> dict[str, Any]:
    """Render one edge's lockfile entry: endpoints, grade, provenance.

    Includes full contract declarations and endpoint metadata. Callable code
    and external resource contents are deliberately not fingerprinted.

    Args:
        edge: The payload or stream edge to describe.

    Returns:
        The JSON-shaped lockfile entry.
    """
    return {
        "src": str(edge.src),
        "dst": str(edge.dst),
        "src_metadata": _lock_node(edge.src),
        "dst_metadata": _lock_node(edge.dst),
        "grade": list(edge.contract.loss_grade()),
        "origin": str(edge.origin),
        "note": edge.note,
        "contract": {
            "census": {
                path: {"disposition": declaration.disposition.value, "note": declaration.note}
                for path, declaration in sorted(edge.contract.census.items())
            },
            "semantic_shifts": [shift.to_dict() for shift in edge.contract.semantic_shifts],
            "note": edge.contract.note,
        },
    }


def _require_one_interface(nodes: list[NodeId]) -> None:
    """Require an explicit pin rather than compare unrelated interface dates."""
    interfaces = sorted({node.interface for node in nodes})
    if len(interfaces) > 1:
        raise ResolutionError(
            f"ambiguous interfaces {', '.join(interfaces)}; pass interface= explicitly"
        )


@cache
def default_catalog() -> Catalog:
    """Return the process's entry-point-discovered catalog, built once.

    The **only** module-level state in `ocai.convert`, and it is a memoized
    pure function, not a mutable registry: the first call runs
    `Catalog.discover()` under the default `TrustPolicy.OWNED_ENDPOINTS`
    and every later call returns that same immutable catalog. Convenience
    entry points (a bare `WireChatModel` with no explicit catalog) use it;
    applications that care about governance compose `Catalog.of(...)`
    explicitly and never touch this.

    Returns:
        The memoized default catalog.
    """
    return Catalog.discover()
