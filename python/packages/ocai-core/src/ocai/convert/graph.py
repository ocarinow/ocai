"""The conversion graph: planner and executor for one message shape (§4.1).

Nodes are `ocai.core.identity.NodeId`s — one provider *interface* revision of
one `Shape`. Edges are conversion functions with an `EdgeContract` and an
`Origin`. Converting `A -> B` is a shortest-path search (Dijkstra) where the
cost of an edge is **derived from its contract** (`EdgeContract.loss_grade()`,
a lexicographic tuple) — there is no author-declared float weight, so an edge
can only be "cheaper" by declaring less loss. The old float `HOP_PENALTY`
survives as the grade's trailing hops component: equal-loss paths still
prefer fewer hops, with no magic constant.

Canonical IR nodes (`ocai/ocai@rev`) form the intended backbone. Reachability
depends on registered directions and shapes; admission does not guarantee a
path for every pair. Direct edges can provide higher-fidelity shortcuts.

**Two-tier loss.** Dijkstra plans *before* seeing a payload, on the declared
census. The **actual** field-level loss is produced when an edge function
runs — each returns an `EdgeOutput` carrying the converted value plus its
`FieldLoss`/`SemanticShift` records. `convert` rolls those into a
`FidelityReport` and returns a `Converted` (value + report), never a bare
tuple. The conformance harness certifies that the actual records never
exceed the declared census.

One graph holds exactly one `Shape` (graphs never mix shapes); the `Catalog`
partitions its graphs per shape. Streaming conversion joins the same
machinery via `StreamEdge` — a transducer factory planned like any edge —
instead of bypassing the graph: `stream_converter` plans a stream path with
the same contract-graded Dijkstra (over its own adjacency and plan cache) and
builds a fresh `StreamPipeline` per traversal.
"""

from __future__ import annotations

import heapq
import itertools
from collections.abc import Callable
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import replace
from types import MappingProxyType
from typing import Any
from typing import Protocol

from ocai.convert.contract import EdgeContract
from ocai.convert.contract import LossGrade
from ocai.convert.inspection import EdgeDeclaration
from ocai.core.fidelity import EdgeReport
from ocai.core.fidelity import FidelityReport
from ocai.core.fidelity import FieldLoss
from ocai.core.fidelity import SemanticShift
from ocai.core.identity import NodeId
from ocai.core.identity import Origin
from ocai.core.identity import Shape


@dataclass(frozen=True, slots=True)
class EdgeOutput:
    """The result of running one conversion edge on a payload.

    Attributes:
        value: The converted payload, in the destination node's
            representation.
        losses: The actual field-level records this edge incurred, in order.
        shifts: The actual semantics-level records this edge incurred, in
            order.
    """

    value: Any
    losses: tuple[FieldLoss, ...] = ()
    shifts: tuple[SemanticShift, ...] = ()


# An edge's transform: opaque payload in, `EdgeOutput` out. Payloads are
# provider-format dicts at dialect nodes and canonical IR objects at the
# canonical nodes; only the conversion function at each edge knows the shapes.
EdgeFn = Callable[[Any], EdgeOutput]


@dataclass(frozen=True, slots=True)
class Edge:
    """A directed conversion edge between two graph nodes.

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
    """

    src: NodeId
    dst: NodeId
    fn: EdgeFn
    contract: EdgeContract
    origin: Origin
    note: str = ""


class StreamConverter(Protocol):
    """One live transducer instance converting a chunk stream across an edge.

    Built per stream traversal by `StreamEdge.build()`; stateful by design
    (it buffers partial events, correlates deltas, seals parts). The driver
    pumps decoded wire events through `feed` and calls `flush` exactly once
    when the stream ends, collecting both the tail events and the edge's
    `EdgeReport` — which the facade folds into the terminal `StreamEnd`
    report so streaming has honesty parity with complete calls.
    """

    def feed(self, event: Any) -> list[Any]:
        """Consume one upstream event and emit zero or more downstream ones.

        A transducer may buffer (returning `[]`), pass through, split one
        event into several, or coalesce several into one.

        Args:
            event: The next event in the source node's representation.

        Returns:
            The events ready to emit, in the destination node's
            representation, in order.
        """
        ...

    def flush(self) -> tuple[list[Any], EdgeReport]:
        """Finish the stream: drain buffers and account for the traversal.

        Called exactly once, after the last `feed`. Aborted streams flush
        too — sealing in-flight state incomplete rather than dropping it.

        Returns:
            The remaining events to emit, and the `EdgeReport` of losses
            and shifts this traversal incurred.
        """
        ...


# Builds a fresh `StreamConverter` per stream traversal (transducers are
# stateful; edges are shared and immutable, so the edge carries a factory).
StreamConverterFactory = Callable[[], StreamConverter]


@dataclass(frozen=True, slots=True)
class StreamEdge:
    """A directed streaming-conversion edge: a transducer factory.

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
    """

    src: NodeId
    dst: NodeId
    factory: StreamConverterFactory
    contract: EdgeContract
    origin: Origin
    note: str = ""

    def build(self) -> StreamConverter:
        """Return a fresh, stateful transducer for one stream traversal.

        Returns:
            A new `StreamConverter`; never shared across streams.
        """
        return self.factory()


class StreamPipeline:
    """The composite transducer executing one planned stream path.

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
    """

    def __init__(self, edges: tuple[StreamEdge, ...]) -> None:
        """Build one fresh transducer per planned edge.

        Args:
            edges: The planned stream path, in traversal order. Empty for an
                identity plan (`src == dst`), in which case `feed` passes
                events through untouched.
        """
        self._edges = edges
        self._stages: tuple[StreamConverter, ...] = tuple(edge.build() for edge in edges)
        self._reports: tuple[EdgeReport, ...] | None = None

    @property
    def edges(self) -> tuple[StreamEdge, ...]:
        """Return the planned stream edges this pipeline traverses, in order."""
        return self._edges

    @property
    def reports(self) -> tuple[EdgeReport, ...] | None:
        """Return the per-edge flush accounting, or None before `flush` ran.

        The facade's half of the WU-09 seam: after the driver exhausts the
        stream (which flushes this pipeline), read this and fold each report
        into the terminal `StreamEnd.report`.
        """
        return self._reports

    def feed(self, event: Any) -> list[Any]:
        """Pipe one event through every stage, in path order.

        Args:
            event: The next event in the path's source representation.

        Returns:
            The converted events ready to emit, in the path's destination
            representation, in order — empty while stages buffer. With no
            stages (an identity plan) the event passes through unchanged.
        """
        events = [event]
        for stage in self._stages:
            emitted: list[Any] = []
            for item in events:
                emitted.extend(stage.feed(item))
            events = emitted
        return events

    def flush(self) -> tuple[list[Any], tuple[EdgeReport, ...]]:
        """Finish the stream: drain every stage and collect the accounting.

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
        """
        if self._reports is not None:
            raise RuntimeError(
                "StreamPipeline.flush() may only be called once; build a fresh "
                "pipeline per stream traversal via stream_converter()."
            )
        tail: list[Any] = []
        reports: list[EdgeReport] = []
        for index, stage in enumerate(self._stages):
            events, report = stage.flush()
            reports.append(report)
            drained = list(events)
            for downstream in self._stages[index + 1 :]:
                emitted: list[Any] = []
                for item in drained:
                    emitted.extend(downstream.feed(item))
                drained = emitted
            tail.extend(drained)
        self._reports = tuple(reports)
        return tail, self._reports


@dataclass(frozen=True, slots=True)
class Converted:
    """The result of a graph conversion: the output value plus its report.

    Attributes:
        value: The converted payload at the destination node.
        report: The `FidelityReport` accumulated along the path — one
            `EdgeReport` per traversed edge, in order.
    """

    value: Any
    report: FidelityReport


class ConversionError(LookupError):
    """Raised when no conversion path exists between two graph nodes."""


# The additive identity for grade accumulation along a path.
_ZERO_GRADE: LossGrade = (0, 0, 0, 0)


def _grade_sum(a: LossGrade, b: LossGrade) -> LossGrade:
    """Return the elementwise sum of two lexicographic loss grades."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2], a[3] + b[3])


def _dijkstra[E: (Edge, StreamEdge)](
    adjacency: Mapping[NodeId, Sequence[E]],
    src: NodeId,
    dst: NodeId,
    counter: Iterator[int],
) -> list[E] | None:
    """Find the cheapest (lowest summed grade) edge sequence `src -> dst`.

    The one shortest-path search serving both the unary (`Edge`) and the
    streaming (`StreamEdge`) adjacencies — same `LossGrade` cost, same
    determinism, so the two planners can never drift. Path cost is the
    elementwise sum of contract-derived edge grades: the comparison prefers
    less breakage, then less approximation, then less emulation, then fewer
    hops. Deterministic: outgoing edges are traversed in grade then destination-coordinate
    order and a monotonic counter breaks heap ties, so nodes and paths are
    never compared directly.

    Args:
        adjacency: The per-node outgoing edges to search over.
        src: The source node.
        dst: The destination node; assumed different from `src` (callers
            short-circuit the identity plan).
        counter: The graph's monotonic heap tiebreaker.

    Returns:
        The ordered edges forming the cheapest path, or None when no path
        exists (callers raise their own `ConversionError`).
    """
    heap: list[tuple[LossGrade, int, NodeId, list[E]]] = [(_ZERO_GRADE, next(counter), src, [])]
    best: dict[NodeId, LossGrade] = {src: _ZERO_GRADE}
    while heap:
        grade, _, node, path = heapq.heappop(heap)
        if node == dst:
            return path
        node_best = best.get(node)
        if node_best is not None and grade > node_best:
            continue
        for edge in sorted(
            adjacency.get(node, []),
            key=lambda e: (
                e.contract.loss_grade(),
                e.dst.provider,
                e.dst.interface,
                e.dst.tag,
                e.dst.shape.capability.name,
                e.dst.shape.role,
            ),
        ):
            nd = _grade_sum(grade, edge.contract.loss_grade())
            dst_best = best.get(edge.dst)
            if dst_best is None or nd < dst_best:
                best[edge.dst] = nd
                heapq.heappush(heap, (nd, next(counter), edge.dst, path + [edge]))
    return None


class ConversionGraph:
    """Edges for one `Shape`, with cached contract-graded shortest-path plans.

    Owned and populated by a `Catalog` (which partitions one graph per
    shape); user code converts through `Catalog.convert`, which delegates
    here. Registration is idempotent so composing overlapping fragments is
    safe. Structural honesty rules the graph is responsible for (e.g. a
    `ProviderRef` crossing its minting `(provider, interface)` is
    `UNSUPPORTED`-and-reported) are enforced by the edge functions and
    certified by conformance; the planner itself only routes.
    """

    def __init__(self) -> None:
        """Construct an empty graph with no edges and empty plan caches."""
        self._shape: Shape | None = None
        self._nodes: dict[tuple[str, str, str, Shape], NodeId] = {}
        self._edges: dict[NodeId, list[Edge]] = {}
        self._stream_edges: dict[NodeId, list[StreamEdge]] = {}
        # Caches of planned paths keyed by (src, dst) — one per adjacency,
        # cleared by the matching register method.
        self._plan_cache: dict[tuple[NodeId, NodeId], list[Edge]] = {}
        self._stream_plan_cache: dict[tuple[NodeId, NodeId], list[StreamEdge]] = {}
        # Monotonic tiebreaker so heap entries never compare NodeId/path.
        self._counter = itertools.count()

    def _validate_registration(self, edge: Edge | StreamEdge) -> None:
        """Reject mixed shapes and contradictory metadata before mutation."""
        if edge.src.shape != edge.dst.shape or (
            self._shape is not None and edge.src.shape != self._shape
        ):
            raise ValueError("conversion graph cannot mix shapes")
        pending = dict(self._nodes)
        for node in (edge.src, edge.dst):
            key = (node.provider, node.interface, node.tag, node.shape)
            if key in pending and pending[key] != node:
                raise ValueError(f"conflicting node metadata for {node}")
            pending[key] = node

    def _remember_nodes(self, edge: Edge | StreamEdge) -> None:
        self._shape = edge.src.shape
        for node in (edge.src, edge.dst):
            self._nodes[(node.provider, node.interface, node.tag, node.shape)] = node

    def register(self, edge: Edge) -> None:
        """Register a directed conversion edge. Idempotent.

        Registering an identical edge again is a no-op, so composing
        overlapping fragments is safe. Register both directions explicitly
        if the conversion is bidirectional (they will have different
        contracts — decode and encode rarely cost the same).

        Args:
            edge: The edge to add.

        Raises:
            ValueError: If the edge's endpoints have different `Shape`s —
                graphs never mix shapes; conflicting directed edges or node metadata are rejected.
        """
        self._validate_registration(edge)
        edges = self._edges.get(edge.src, [])
        if edge in edges:
            return  # idempotent: identical edge already registered
        if any(existing.dst == edge.dst for existing in edges):
            raise ValueError(f"conflicting conversion edge {edge.src} -> {edge.dst}")
        self._remember_nodes(edge)
        self._edges.setdefault(edge.src, []).append(
            replace(
                edge,
                contract=replace(
                    edge.contract, census=MappingProxyType(dict(edge.contract.census))
                ),
            )
        )
        self._plan_cache.clear()  # any new edge may create a cheaper path

    def register_stream(self, edge: StreamEdge) -> None:
        """Register a directed streaming-conversion edge. Idempotent.

        Args:
            edge: The transducer-factory edge to add.

        Raises:
            ValueError: If shapes differ or a directed edge/node declaration conflicts.
        """
        self._validate_registration(edge)
        edges = self._stream_edges.get(edge.src, [])
        if edge in edges:
            return  # idempotent: identical edge already registered
        if any(existing.dst == edge.dst for existing in edges):
            raise ValueError(f"conflicting stream edge {edge.src} -> {edge.dst}")
        self._remember_nodes(edge)
        self._stream_edges.setdefault(edge.src, []).append(
            replace(
                edge,
                contract=replace(
                    edge.contract, census=MappingProxyType(dict(edge.contract.census))
                ),
            )
        )
        self._stream_plan_cache.clear()  # any new edge may create a cheaper path

    def _plan(self, src: NodeId, dst: NodeId) -> list[Edge]:
        """Return the cheapest (lowest summed grade) edge sequence `src -> dst`.

        The `_dijkstra` search over the unary adjacency (see its docstring
        for the cost and determinism rules — the grade's hops component is
        what the old float `HOP_PENALTY` became), memoized in the unary plan
        cache.

        Args:
            src: The source node.
            dst: The destination node.

        Returns:
            The ordered edges forming the cheapest path (empty if
            `src == dst`).

        Raises:
            ConversionError: If no path exists.
        """
        if src == dst:
            return []
        cached = self._plan_cache.get((src, dst))
        if cached is not None:
            return cached
        path = _dijkstra(self._edges, src, dst, self._counter)
        if path is None:
            raise ConversionError(f"no conversion path from {src} to {dst}")
        self._plan_cache[(src, dst)] = path
        return path

    def _plan_stream(self, src: NodeId, dst: NodeId) -> list[StreamEdge]:
        """Return the cheapest stream-edge sequence `src -> dst`.

        The streaming twin of `_plan`: the same `_dijkstra` search with the
        same contract-derived grades and determinism, over the stream
        adjacency, memoized in the separate stream plan cache (cleared by
        `register_stream`).

        Args:
            src: The source chunk-shape node.
            dst: The destination chunk-shape node.

        Returns:
            The ordered stream edges forming the cheapest path (empty if
            `src == dst`).

        Raises:
            ConversionError: If no stream-edge path exists.
        """
        if src == dst:
            return []
        cached = self._stream_plan_cache.get((src, dst))
        if cached is not None:
            return cached
        path = _dijkstra(self._stream_edges, src, dst, self._counter)
        if path is None:
            raise ConversionError(f"no stream conversion path from {src} to {dst}")
        self._stream_plan_cache[(src, dst)] = path
        return path

    def inspect(self, src: NodeId, dst: NodeId, *,
                streaming: bool = False) -> tuple[EdgeDeclaration, ...]:
        """Inspect a path without executing converters or constructing transducers."""
        edges: Sequence[Edge | StreamEdge] = (
            self._plan_stream(src, dst) if streaming else self._plan(src, dst)
        )
        return tuple(EdgeDeclaration(
            edge.src, edge.dst, edge.origin,
            replace(edge.contract, census=dict(edge.contract.census)),
        ) for edge in edges)

    def convert(self, payload: Any, src: NodeId, dst: NodeId) -> Converted:
        """Convert `payload` from node `src` to node `dst`.

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
        """
        path = self._plan(src, dst)
        report = FidelityReport()
        value = payload
        for edge in path:
            out = edge.fn(value)
            value = out.value
            report.edges.append(
                EdgeReport(edge.src, edge.dst, tuple(out.losses), tuple(out.shifts), edge.note)
            )
        return Converted(value, report)

    def stream_converter(self, src: NodeId, dst: NodeId) -> StreamPipeline:
        """Plan and build the composite transducer converting chunks `src -> dst`.

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
        """
        return StreamPipeline(tuple(self._plan_stream(src, dst)))

    def can_convert(self, src: NodeId, dst: NodeId) -> bool:
        """Return whether any conversion path exists from `src` to `dst`.

        Args:
            src: The source node.
            dst: The destination node.

        Returns:
            True if a path exists (or `src == dst`), False otherwise. Never
            raises; a missing path is reported as False rather than
            propagated.
        """
        try:
            self._plan(src, dst)
            return True
        except ConversionError:
            return False
