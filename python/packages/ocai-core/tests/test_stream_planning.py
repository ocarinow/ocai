"""Stream conversion joins the graph (WU-09): planner, pipeline, driver pump.

Covers the three legs of the streaming seam:

- **Planning** — `ConversionGraph.stream_converter` runs the same
  contract-graded Dijkstra as unary `convert` over the `StreamEdge`
  adjacency, with its own plan cache: grade-based multi-hop path choice,
  hop tie-breaking, registration-order determinism, cache invalidation.
- **Pipeline** — `StreamPipeline` builds FRESH transducers per traversal
  (`StreamEdge.build()` per planned edge per stream), pipes `feed` through
  the stages in path order, and `flush` drains front-to-back concatenating
  one `EdgeReport` per stage — exposed on `reports` for the facade to stamp
  into the terminal `StreamEnd.report`.
- **Driver pump** — both drivers stream recorded SSE bytes from a fake
  transport through a REAL transducer chain (the OpenAI chat-completions
  `StreamEdge`) into canonical `ChatChunk`s, with the credential applied at
  the leaf and the pipeline flushed exactly once — including on aborts.

The SSE body is a synthetic recording (wire-accurate, hand-authored) shared
with `tests/test_streaming.py`; no live API is ever called (rule 10).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest

from ocai.chat.types import ChatChunk
from ocai.chat.types import ChunkType
from ocai.convert.contract import DeclaredDisposition
from ocai.convert.contract import EdgeContract
from ocai.convert.graph import ConversionError
from ocai.convert.graph import ConversionGraph
from ocai.convert.graph import Edge
from ocai.convert.graph import EdgeOutput
from ocai.convert.graph import StreamEdge
from ocai.core.credentials import ApiKey
from ocai.core.errors import TransientError
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import EdgeReport
from ocai.core.identity import CHAT_CHUNK
from ocai.core.identity import NodeId
from ocai.core.identity import Origin
from ocai.core.identity import canonical_node
from ocai.core.traits import DialectTraits
from ocai.openai.chat_completions.codec import CANONICAL_CHUNK
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_CHUNK
from ocai.openai.chat_completions.edges import TRANSDUCERS
from ocai.runtime.binding import Binding
from ocai.runtime.drivers import AsyncDriver
from ocai.runtime.drivers import SyncDriver
from ocai.wire.hosting import Direct
from ocai.wire.hosting import EndpointSpec
from ocai.wire.hosting import Operation
from ocai.wire.http import HttpRequest
from ocai.wire.sse import SSEvent

# --- Planning fixtures: nodes, contracts, recordable transducers ------------

ORIGIN = Origin("test", "0.0.0")

# The canonical chunk node is the guaranteed backbone; provider nodes hang off it.
HUB = canonical_node(CHAT_CHUNK)


def _node(provider: str) -> NodeId:
    """Mint one chunk-shape provider node for planning tests."""
    return NodeId(provider, "iface", "2026-01", CHAT_CHUNK, date(2026, 1, 1))


def _lossless() -> EdgeContract:
    """An empty census: grades `(0, 0, 0, 1)`."""
    return EdgeContract(note="lossless")


def _lossy(dropped: int = 1) -> EdgeContract:
    """A census declaring `dropped` DROPPED fields: grades `(dropped, 0, 0, 1)`."""
    return EdgeContract(
        census={f"f{i}": DeclaredDisposition(Disposition.DROPPED) for i in range(dropped)},
        note="lossy",
    )


class TagTransducer:
    """A stateless-looking but per-traversal transducer: tags events with a label."""

    def __init__(self, label: str, src: NodeId, dst: NodeId) -> None:
        self.label = label
        self.fed: list[Any] = []
        self._src = src
        self._dst = dst

    def feed(self, event: Any) -> list[Any]:
        self.fed.append(event)
        return [f"{event}>{self.label}"]

    def flush(self) -> tuple[list[Any], EdgeReport]:
        return [], EdgeReport(self._src, self._dst, note=self.label)


class BufferingTransducer:
    """Holds every event until flush — exercises tail propagation through stages."""

    def __init__(self, src: NodeId, dst: NodeId) -> None:
        self._held: list[Any] = []
        self._src = src
        self._dst = dst

    def feed(self, event: Any) -> list[Any]:
        self._held.append(event)
        return []

    def flush(self) -> tuple[list[Any], EdgeReport]:
        return list(self._held), EdgeReport(self._src, self._dst, note="buffered")


def _edge(
    src: NodeId,
    dst: NodeId,
    label: str,
    contract: EdgeContract | None = None,
    built: list[TagTransducer] | None = None,
) -> StreamEdge:
    """Build a tagging StreamEdge whose factory records what it builds."""

    def factory() -> TagTransducer:
        transducer = TagTransducer(label, src, dst)
        if built is not None:
            built.append(transducer)
        return transducer

    return StreamEdge(src, dst, factory, contract or _lossless(), ORIGIN, note=label)


# --- Grade-based stream path choice ------------------------------------------


def test_stream_planner_prefers_lossless_two_hop_over_lossy_direct() -> None:
    a, c = _node("a"), _node("c")
    graph = ConversionGraph()
    graph.register_stream(_edge(a, c, "direct", _lossy()))
    graph.register_stream(_edge(a, HUB, "up"))
    graph.register_stream(_edge(HUB, c, "down"))

    pipeline = graph.stream_converter(a, c)

    # (0,0,0,2) beats (1,0,0,1): less declared loss wins over fewer hops.
    assert [e.note for e in pipeline.edges] == ["up", "down"]
    assert pipeline.feed("x") == ["x>up>down"]  # stages chained in path order


def test_stream_planner_prefers_fewer_hops_when_equally_lossless() -> None:
    a, c = _node("a"), _node("c")
    graph = ConversionGraph()
    graph.register_stream(_edge(a, HUB, "up"))
    graph.register_stream(_edge(HUB, c, "down"))
    graph.register_stream(_edge(a, c, "direct"))

    pipeline = graph.stream_converter(a, c)

    assert [e.note for e in pipeline.edges] == ["direct"]  # (0,0,0,1) < (0,0,0,2)


def test_stream_planning_is_deterministic_across_registration_order() -> None:
    a, c = _node("a"), _node("c")
    via1, via2 = _node("via1"), _node("via2")
    edges = [
        _edge(a, via1, "a>via1"),
        _edge(via1, c, "via1>c"),
        _edge(a, via2, "a>via2"),
        _edge(via2, c, "via2>c"),
    ]

    forward, backward = ConversionGraph(), ConversionGraph()
    for edge in edges:
        forward.register_stream(edge)
    for edge in reversed(edges):
        backward.register_stream(edge)

    plan_fwd = [e.note for e in forward.stream_converter(a, c).edges]
    plan_bwd = [e.note for e in backward.stream_converter(a, c).edges]

    # Two equal-grade paths: the (grade, str(dst)) traversal order decides,
    # not registration order — plans match and are stable.
    assert plan_fwd == plan_bwd == ["a>via1", "via1>c"]


def test_stream_plan_cache_is_separate_and_cleared_on_register() -> None:
    a, c = _node("a"), _node("c")
    graph = ConversionGraph()
    graph.register_stream(_edge(a, HUB, "up"))
    graph.register_stream(_edge(HUB, c, "down"))

    first = graph.stream_converter(a, c)
    second = graph.stream_converter(a, c)
    assert first.edges == second.edges  # cached plan, replayed

    # A new cheaper edge invalidates the stream plan cache.
    graph.register_stream(_edge(a, c, "direct"))
    assert [e.note for e in graph.stream_converter(a, c).edges] == ["direct"]


def test_unary_and_stream_adjacencies_are_separate() -> None:
    a, c = _node("a"), _node("c")
    graph = ConversionGraph()
    graph.register(Edge(a, c, lambda payload: EdgeOutput(payload), _lossless(), ORIGIN))

    assert graph.can_convert(a, c)  # unary path exists...
    with pytest.raises(ConversionError, match="no stream conversion path"):
        graph.stream_converter(a, c)  # ...but no stream path was registered


def test_no_stream_path_raises_conversion_error() -> None:
    a, c = _node("a"), _node("c")
    with pytest.raises(ConversionError, match="no stream conversion path"):
        ConversionGraph().stream_converter(a, c)


# --- Per-traversal transducer freshness ---------------------------------------


def test_transducers_are_fresh_per_traversal() -> None:
    a = _node("a")
    built: list[TagTransducer] = []
    graph = ConversionGraph()
    graph.register_stream(_edge(a, HUB, "up", built=built))
    graph.register_stream(_edge(HUB, a, "down"))

    one = graph.stream_converter(a, HUB)
    two = graph.stream_converter(a, HUB)

    # build() ran once per planned edge per stream — even on a cached plan.
    assert len(built) == 2
    assert built[0] is not built[1]

    # State never bleeds between traversals.
    one.feed("x")
    assert built[0].fed == ["x"]
    assert built[1].fed == []
    assert two.feed("y") == ["y>up"]


def test_identity_plan_passes_events_through() -> None:
    a = _node("a")
    pipeline = ConversionGraph().stream_converter(a, a)

    assert pipeline.edges == ()
    assert pipeline.feed("x") == ["x"]
    tail, reports = pipeline.flush()
    assert (tail, reports) == ([], ())
    assert pipeline.reports == ()


# --- Composite flush: front-to-back drain, concatenated reports ---------------


def test_flush_drains_front_to_back_and_concatenates_reports() -> None:
    a, c = _node("a"), _node("c")
    graph = ConversionGraph()
    graph.register_stream(
        StreamEdge(a, HUB, lambda: BufferingTransducer(a, HUB), _lossless(), ORIGIN)
    )
    graph.register_stream(_edge(HUB, c, "tag"))

    pipeline = graph.stream_converter(a, c)
    assert pipeline.reports is None  # nothing to account for before flush

    assert pipeline.feed("e1") == []  # stage 1 buffers: nothing reaches stage 2
    assert pipeline.feed("e2") == []

    tail, reports = pipeline.flush()

    # Stage 1's flushed tail was fed through stage 2 before stage 2 flushed.
    assert tail == ["e1>tag", "e2>tag"]
    assert [r.note for r in reports] == ["buffered", "tag"]  # path order
    assert [(r.src, r.dst) for r in reports] == [(a, HUB), (HUB, c)]
    assert pipeline.reports == reports  # exposed for the facade (WU-09 seam)


def test_flush_twice_raises() -> None:
    a = _node("a")
    pipeline = ConversionGraph().stream_converter(a, a)
    pipeline.flush()
    with pytest.raises(RuntimeError, match="once"):
        pipeline.flush()


# --- Driver pump: recorded SSE bytes -> real transducer chain -> chunks -------

# Synthetic recording (wire-accurate, hand-authored) of an OpenAI
# chat-completions SSE stream — same body as tests/test_streaming.py, split
# mid-line into transport chunks to exercise the parser's buffering.
OPENAI_SSE = (
    b'data: {"choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}\n\n'
    b'data: {"choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}\n\n'
    b'data: {"choices":[{"index":0,"delta":{"content":" world"},"finish_reason":null}]}\n\n'
    b'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n'
    b"data: [DONE]\n\n"
)

# Split points chosen to land inside lines, not on frame boundaries.
SSE_CHUNKS = [OPENAI_SSE[i : i + 97] for i in range(0, len(OPENAI_SSE), 97)]


class FakeSyncTransport:
    """A fake `SyncTransport` streaming a recorded body — no sockets (rule 10)."""

    def __init__(self, chunks: list[bytes], *, fail_after: int | None = None) -> None:
        self.chunks = chunks
        self.fail_after = fail_after
        self.requests: list[HttpRequest] = []

    def send_sync(self, request: HttpRequest) -> Any:
        raise AssertionError("streaming test must not use the unary send")

    def stream_sync(self, request: HttpRequest) -> Iterator[bytes]:
        self.requests.append(request)
        for served, chunk in enumerate(self.chunks):
            if self.fail_after is not None and served >= self.fail_after:
                raise TransientError("connection reset mid-stream")
            yield chunk

    def close(self) -> None:
        pass


class FakeAsyncTransport:
    """The async twin of `FakeSyncTransport`."""

    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.requests: list[HttpRequest] = []

    async def send(self, request: HttpRequest) -> Any:
        raise AssertionError("streaming test must not use the unary send")

    async def stream(self, request: HttpRequest) -> AsyncIterator[bytes]:
        self.requests.append(request)
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        pass


def _spec() -> EndpointSpec:
    """The streaming endpoint spec the facade would assemble for the codec."""
    return EndpointSpec(
        dialect=CHAT_COMPLETIONS_CHUNK,
        traits=DialectTraits(vendor="openai"),
        op=Operation(name="chat", kind="generative", streaming=True),
        resource="gpt-test",
        native_path="/v1/chat/completions",
    )


def _binding(transport: Any) -> Binding:
    return Binding(
        host=Direct("https://api.example.test"),
        credentials=ApiKey("sk-test"),
        transport=transport,
    )


def _real_pipeline() -> Any:
    """A fresh composite over the REAL OpenAI chunk-decode StreamEdge."""
    graph = ConversionGraph()
    for stream_edge in TRANSDUCERS:
        graph.register_stream(stream_edge)
    return graph.stream_converter(CHAT_COMPLETIONS_CHUNK, CANONICAL_CHUNK)


def test_sync_driver_pumps_sse_through_real_transducers_into_chunks() -> None:
    transport = FakeSyncTransport(SSE_CHUNKS)
    pipeline = _real_pipeline()
    driver = SyncDriver(_binding(transport))

    chunks = list(driver.stream(spec=_spec(), payload={"model": "gpt-test"}, pipeline=pipeline))

    # Converted events, not raw frames: canonical chunks with seq stamped.
    assert all(isinstance(c, ChatChunk) for c in chunks)
    assert [c.type for c in chunks] == [
        ChunkType.STREAM_START,
        ChunkType.PART_DELTA,
        ChunkType.PART_DELTA,
        ChunkType.FINISH,
    ]
    assert "".join(c.delta.text for c in chunks if c.type == ChunkType.PART_DELTA) == "Hello world"
    assert [c.seq for c in chunks] == [0, 1, 2, 3]

    # The seam: the driver flushed exactly once; the facade reads the
    # accounting off the pipeline and stamps StreamEnd.report with it.
    assert pipeline.reports is not None
    assert [(r.src, r.dst) for r in pipeline.reports] == [(CHAT_COMPLETIONS_CHUNK, CANONICAL_CHUNK)]
    assert pipeline.reports[0].lossless

    # Credential at the leaf, on the streaming path too (rule 13).
    (request,) = transport.requests
    assert request.headers["Authorization"] == "Bearer sk-test"
    assert request.url == "https://api.example.test/v1/chat/completions"
    assert request.stream is True


def test_sync_driver_without_pipeline_yields_raw_frames() -> None:
    transport = FakeSyncTransport(SSE_CHUNKS)
    driver = SyncDriver(_binding(transport))

    frames = list(driver.stream(spec=_spec(), payload={"model": "gpt-test"}))

    # No pipeline bound: the sentinel frame included, nothing decoded.
    assert all(isinstance(f, SSEvent) for f in frames)
    assert len(frames) == 5
    assert frames[-1].data == "[DONE]"


async def test_async_driver_pump_matches_sync() -> None:
    transport = FakeAsyncTransport(SSE_CHUNKS)
    pipeline = _real_pipeline()
    driver = AsyncDriver(_binding(transport))

    chunks = [
        chunk
        async for chunk in driver.stream(
            spec=_spec(), payload={"model": "gpt-test"}, pipeline=pipeline
        )
    ]

    assert [c.type for c in chunks] == [
        ChunkType.STREAM_START,
        ChunkType.PART_DELTA,
        ChunkType.PART_DELTA,
        ChunkType.FINISH,
    ]
    assert "".join(c.delta.text for c in chunks if c.type == ChunkType.PART_DELTA) == "Hello world"
    assert pipeline.reports is not None
    assert transport.requests[0].headers["Authorization"] == "Bearer sk-test"


def test_sync_driver_flushes_pipeline_on_mid_stream_error() -> None:
    # Two transport chunks served, then the wire dies.
    transport = FakeSyncTransport(SSE_CHUNKS, fail_after=2)
    pipeline = _real_pipeline()
    driver = SyncDriver(_binding(transport))

    received: list[ChatChunk] = []
    stream = driver.stream(spec=_spec(), payload={"model": "gpt-test"}, pipeline=pipeline)
    with pytest.raises(TransientError):
        # extend() appends element by element, so the chunks delivered before
        # the abort survive the raise.
        received.extend(stream)

    # Events before the abort were delivered; the pipeline was still flushed
    # (exactly once) so the traversal's accounting survives the abort.
    assert received  # at least STREAM_START made it through
    assert pipeline.reports is not None
    assert len(pipeline.reports) == 1
