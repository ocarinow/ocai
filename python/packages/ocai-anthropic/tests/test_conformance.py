"""Anthropic messages certification (WU-13 unary + WU-14b streaming).

Drives the interface's two unary edges through the full conformance harness
over the golden edge fixtures in `spec/fixtures/anthropic/messages/`:

- `check_edge` — running each edge on its fixture `input` yields a value
  `semantic_equal` to `expect`, and the runtime `FieldLoss`/`SemanticShift`
  records match `expect_losses`/`expect_shifts` exactly;
- `certify_edge` — the same payload set certifies against each edge's
  declared `EdgeContract` census with zero violations (an edge claiming
  less loss than it incurs cannot ship);
- catalog routing — the same fixtures convert through a `Catalog` composed
  of the real `ocai.anthropic.FRAGMENT`, proving the certified edges are
  what the planner actually routes payloads through (a full graph *round
  trip* needs the reverse edges — `decode_request` / an encode-response
  edge — which do not exist yet, so each fixture is exercised in its edge's
  one registered direction);
- the wire-side rule-6 guarantee — the decoder never raises on unknown wire
  material (unknown stop reasons keep the native lane; unknown envelope
  keys sweep into namespaced `extensions`).

The WU-05a seam applies throughout: the canonical request carries no model,
the edge output has no `model` member, and the fixtures' wire bodies gain it
through the codec's `bind_resource` — the facade injection, below the graph.

The streaming half (WU-14b, the WU-10 pattern replay) drives the chunk-shape
`StreamEdge` over the fold triples in `streams/`: the recorded SSE event log
must decode through the real `MessagesStreamTransducer` to exactly the
expected canonical chunks, `StreamAccumulator.fold` must reproduce each
triple's response (the fold law, rule 7), the paired triple's fold must be
`semantic_equal` to the unary `response_plain_text.json` canonical, and the
transducer's flush accounting certifies against `DECODE_CHUNK_CONTRACT`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import cast

import pytest

import ocai.anthropic
from ocai.anthropic.messages.codec import MESSAGES_REQUEST
from ocai.anthropic.messages.codec import MESSAGES_RESPONSE
from ocai.anthropic.messages.codec import MessagesCodec
from ocai.anthropic.messages.codec import MessagesStreamTransducer
from ocai.anthropic.messages.edges import DECODE_CHUNK_CONTRACT
from ocai.anthropic.messages.edges import EDGES
from ocai.anthropic.messages.edges import ENCODE_REQUEST_CONTRACT
from ocai.chat import CANONICAL_CHAT_REQUEST
from ocai.chat import CANONICAL_CHAT_RESPONSE
from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChunkType
from ocai.chat.types import PartToolCall
from ocai.chat.types import StreamAccumulator
from ocai.convert.catalog import Catalog
from ocai.convert.conformance import certify_edge
from ocai.convert.conformance import check_edge
from ocai.convert.conformance import check_fold_triples
from ocai.convert.graph import Edge
from ocai.convert.graph import EdgeOutput
from ocai.core.canonjson import canonical
from ocai.core.canonjson import semantic_equal
from ocai.core.fidelity import Disposition
from ocai.core.identity import NodeId
from ocai.wire import SSEParser
from ocai.wire import SSEvent


def _find_repo_root(start: Path) -> Path:
    """Walk upward until we find the repo root (the dir containing `spec/`)."""
    for parent in [start, *start.parents]:
        if (parent / "spec" / "fixtures").is_dir():
            return parent
    raise RuntimeError("could not locate repo root (no spec/fixtures/ found)")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
FIXTURES_DIR = REPO_ROOT / "spec" / "fixtures" / "anthropic" / "messages"
FIXTURE_PATHS = sorted(FIXTURES_DIR.glob("*.json"))
STREAMS_DIR = FIXTURES_DIR / "streams"

_CODEC = MessagesCodec()
ENCODE_EDGE = next(edge for edge in EDGES if edge.dst == MESSAGES_REQUEST)
DECODE_EDGE = next(edge for edge in EDGES if edge.src == MESSAGES_RESPONSE)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _expect_shifts(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    """The fixture's pinned shift records; an absent or null key means none."""
    shifts: Any = fixture.get("expect_shifts")
    if not shifts:
        return []
    return cast(list[dict[str, Any]], shifts)


def _is_encode(fixture: dict[str, Any]) -> bool:
    """An `ocai`-source fixture exercises the encode edge; wire-source, decode."""
    return fixture["src"]["provider"] == "ocai"


def _edge_for(fixture: dict[str, Any]) -> Edge:
    return ENCODE_EDGE if _is_encode(fixture) else DECODE_EDGE


def _coordinates_match(coordinate: dict[str, Any], node: NodeId) -> bool:
    """The fixture's src/dst coordinates name the edge endpoint exactly."""
    return (
        coordinate["provider"] == node.provider
        and coordinate["interface"] == node.interface
        and coordinate["tag"] == node.tag
        and coordinate["shape"] == str(node.shape)
    )


def _run_fixture(fixture: dict[str, Any]) -> EdgeOutput:
    """Run one fixture through `check_edge` with the direction's seams."""
    if _is_encode(fixture):
        return check_edge(
            ENCODE_EDGE,
            fixture,
            decode_input=ChatRequest.from_dict,
            # WU-05a: edges are model-agnostic; the wire `model` member is
            # the facade's bind_resource injection, below the graph.
            bind=lambda payload: _CODEC.bind_resource(payload, fixture["expect"]["model"]),
        )
    return check_edge(DECODE_EDGE, fixture)


# --- The fixture set itself covers what WU-13 says it covers -------------------


def test_fixture_set_is_not_empty_and_covers_the_wu13_scenarios() -> None:
    assert len(FIXTURE_PATHS) >= 5, (
        f"WU-13 requires at least five edge fixtures in {FIXTURES_DIR}; found {len(FIXTURE_PATHS)}"
    )
    losses = [
        (entry["path"], entry["disposition"])
        for path in FIXTURE_PATHS
        for entry in _load(path)["expect_losses"]
    ]
    shifts = [
        (entry["kind"], entry["path"])
        for path in FIXTURE_PATHS
        for entry in _expect_shifts(_load(path))
    ]
    # (b) the system hoist is a declared SemanticShift(relocation).
    assert ("relocation", "messages[0]") in shifts
    # (d) the required max_tokens injection is a declared emulation shift.
    assert ("emulation", "config.max_output_tokens") in shifts
    # (e) the out-of-range temperature reports APPROXIMATED, passed verbatim.
    assert ("config.temperature", "approximated") in losses
    # (f) the extensions sweep reports both envelope keys as EXTENSIONS.
    assert ("stop_sequence", "extensions") in losses
    assert ("container", "extensions") in losses


def test_is_error_crosses_natively_the_honest_asymmetry_vs_openai() -> None:
    """(c) `tool_result.is_error` maps NATIVELY here — census EXACT, no loss.

    The honest asymmetry vs chat_completions, whose census declares the same
    path DROPPED: the same canonical payload costs different things on
    different wires, and the census is where that difference is visible.
    """
    declared = ENCODE_REQUEST_CONTRACT.census["messages[].parts[tool_result].is_error"]
    assert declared.disposition is Disposition.EXACT
    tool_round = _load(FIXTURES_DIR / "request_tool_round.json")
    # The flag actually crosses onto the wire...
    wire_blocks = [
        block
        for message in tool_round["expect"]["messages"]
        for block in message["content"]
        if block.get("type") == "tool_result"
    ]
    assert wire_blocks and wire_blocks[0]["is_error"] is True
    # ...and no fixture reports an is_error loss anywhere.
    losses = [entry["path"] for path in FIXTURE_PATHS for entry in _load(path)["expect_losses"]]
    assert not any(path.endswith("is_error") for path in losses)


@pytest.mark.parametrize("path", FIXTURE_PATHS, ids=lambda p: p.name)
def test_fixture_names_its_edge_endpoints(path: Path) -> None:
    fixture = _load(path)
    edge = _edge_for(fixture)
    assert _coordinates_match(fixture["src"], edge.src), (
        f"{path.name}: src coordinates do not name {edge.src}"
    )
    assert _coordinates_match(fixture["dst"], edge.dst), (
        f"{path.name}: dst coordinates do not name {edge.dst}"
    )


# --- Clauses 1+2: output equality, exact loss/shift match ----------------------


@pytest.mark.parametrize("path", FIXTURE_PATHS, ids=lambda p: p.name)
def test_edge_fixture(path: Path) -> None:
    _run_fixture(_load(path))


# --- Clause 3: certification — runtime loss never exceeds the declaration ------


def _payloads(edge: Edge) -> list[Any]:
    """Every fixture `input` for `edge`, lifted to its source representation."""
    payloads: list[Any] = []
    for path in FIXTURE_PATHS:
        fixture = _load(path)
        if _edge_for(fixture) is not edge:
            continue
        payload: Any = fixture["input"]
        if _is_encode(fixture):
            payload = ChatRequest.from_dict(payload)
        payloads.append(payload)
    assert payloads, f"no fixtures exercise {edge.src} -> {edge.dst}"
    return payloads


def test_encode_edge_certifies_over_all_fixtures() -> None:
    assert certify_edge(ENCODE_EDGE, _payloads(ENCODE_EDGE)) == []


def test_decode_edge_certifies_over_all_fixtures() -> None:
    assert certify_edge(DECODE_EDGE, _payloads(DECODE_EDGE)) == []


# --- Catalog routing: the composed fragment plans through the certified edges --


def _catalog() -> Catalog:
    return Catalog.of(ocai.anthropic.FRAGMENT)


@pytest.mark.parametrize("path", FIXTURE_PATHS, ids=lambda p: p.name)
def test_fixture_converts_through_the_catalog(path: Path) -> None:
    fixture = _load(path)
    catalog = _catalog()
    if _is_encode(fixture):
        converted = catalog.convert(
            ChatRequest.from_dict(fixture["input"]),
            CANONICAL_CHAT_REQUEST,
            MESSAGES_REQUEST,
        )
        rendered = _CODEC.bind_resource(converted.value, fixture["expect"]["model"])
    else:
        converted = catalog.convert(fixture["input"], MESSAGES_RESPONSE, CANONICAL_CHAT_RESPONSE)
        rendered = converted.value.to_dict()
    assert semantic_equal(rendered, fixture["expect"]), (
        f"{path.name}: catalog conversion did not match `expect`.\n"
        f"  expected: {canonical(fixture['expect'])}\n"
        f"  actual:   {canonical(rendered)}"
    )
    # The report carries the same records the direct edge run produced —
    # streaming through the planner adds no silent extra leg.
    actual_losses = sorted((loss.path, loss.disposition.value) for loss in converted.report.losses)
    expected_losses = sorted(
        (entry["path"], entry["disposition"]) for entry in fixture["expect_losses"]
    )
    assert actual_losses == expected_losses
    actual_shifts = sorted((shift.kind, shift.path) for shift in converted.report.shifts)
    expected_shifts = sorted(
        (entry["kind"], entry.get("path", "")) for entry in _expect_shifts(fixture)
    )
    assert actual_shifts == expected_shifts


# --- Rule 6 on the wire: the decoder is total over unknown material ------------


def test_decode_never_raises_on_unknown_wire_material() -> None:
    payload = {
        "id": "msg_01Unknown",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-4-8",
        "content": [{"type": "text", "text": "ok"}],
        "stop_reason": "TELEPATHY_LIMIT",
        "routing_tier": {"shard": 7},
    }
    out = DECODE_EDGE.fn(payload)  # total decode: must not raise
    response = out.value
    # The unknown stop reason decodes open with the native lane verbatim.
    assert response.finish is not None
    assert response.finish.reason == "unknown"
    assert response.finish.native == "TELEPATHY_LIMIT"
    # The unknown envelope key sweeps into the namespaced extensions bag,
    # with an honest EXTENSIONS record — never silently dropped. (Its path is
    # deliberately NOT in the census: a tomorrow-key cannot be declared in
    # advance, so the sweep is the rule-6 safety net — and the moment such a
    # key lands in a golden fixture, certification flags it until the census
    # names it. That is the drift alarm working, not a bug.)
    assert response.extensions["anthropic.routing_tier"] == {"shard": 7}
    assert ("routing_tier", "extensions") in [
        (loss.path, loss.disposition.value) for loss in out.losses
    ]


# --- WU-14b: the streaming edge — fold triples over recorded SSE event logs ----
#
# The fold-triple fixtures in `streams/` pin the chunk-shape StreamEdge the
# same way the edge fixtures pin the unary edges: the recorded SSE event log
# must decode (through the real transducer) to exactly the expected canonical
# chunks, and `StreamAccumulator.fold` over those chunks must reproduce the
# response — `fold(stream(request)) == complete(request)` on wire data.


def _strip_raw(value: Any) -> Any:
    """Drop the verbatim `raw`/`raw_event` lanes at any depth (§8).

    Fold-fixture equality excludes the untouched provider lanes
    (`spec/canonical-json.md` §8): the transducer stamps every chunk's
    `raw_event`, but the fixtures pin canonical content only.
    """
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        return {k: _strip_raw(v) for k, v in mapping.items() if k not in ("raw", "raw_event")}
    if isinstance(value, list):
        return [_strip_raw(item) for item in cast(list[Any], value)]
    return value


def _fold_dicts(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """The dict-speaking fold the conformance harness is handed."""
    return StreamAccumulator.fold(ChatChunk.from_dict(chunk) for chunk in chunks).to_dict()


def _wire_decoder() -> Any:
    """A dict-speaking `decode_event` over the REAL stream transducer.

    Each fold triple's `wire_events` entry is one verbatim SSE event text;
    it is parsed by the wire layer's `SSEParser` and fed to a
    `MessagesStreamTransducer`. The transducer is per-stream state, so a
    fresh one replaces it after each terminal `STREAM_STOP` — the walker
    (`check_fold_triples`) reuses one decoder across every fixture in the
    directory.
    """
    state = {"transducer": MessagesStreamTransducer()}

    def decode(event_text: str) -> list[dict[str, Any]]:
        decoded: list[dict[str, Any]] = []
        for frame in SSEParser().feed(event_text + "\n\n"):
            for chunk in state["transducer"].feed(frame):
                decoded.append(_strip_raw(chunk.to_dict()))
                if chunk.type == ChunkType.STREAM_STOP:
                    state["transducer"] = MessagesStreamTransducer()
        return decoded

    return decode


def test_fold_triples_over_recorded_streams() -> None:
    checked = check_fold_triples(STREAMS_DIR, decode_event=_wire_decoder(), fold=_fold_dicts)
    # WU-14b requires the three scenarios: plain text, tool-use args, and
    # the cumulative-usage stream paired with the unary canonical.
    assert len(checked) >= 3
    names = {path.name for path in checked}
    assert {
        "stream_plain_text.json",
        "stream_tool_use_args.json",
        "stream_usage_paired.json",
    } <= names


def test_paired_stream_fold_matches_the_unary_canonical() -> None:
    # Full paired equality includes info; only raw evidence is excluded.
    triple = _load(STREAMS_DIR / "stream_usage_paired.json")
    unary = _load(FIXTURES_DIR / "response_plain_text.json")

    folded = _fold_dicts(triple["chunks"])
    expected = _strip_raw(unary["expect"])
    assert semantic_equal(folded, expected), (
        "fold(chunks) did not reproduce the paired unary canonical.\n"
        f"  expected: {canonical(expected)}\n"
        f"  actual:   {canonical(folded)}"
    )


@pytest.mark.parametrize("path", sorted(STREAMS_DIR.glob("*.json")), ids=lambda p: p.name)
def test_chunk_edge_certifies_over_stream_fixtures(path: Path) -> None:
    # Clause 3 for the streaming edge: the transducer's flush accounting
    # over every fold triple's event log stays within DECODE_CHUNK_CONTRACT
    # — an edge whose runtime loss exceeds its census cannot ship.
    transducer = MessagesStreamTransducer()
    for event_text in _load(path)["wire_events"]:
        for frame in SSEParser().feed(event_text + "\n\n"):
            transducer.feed(frame)
    _, report = transducer.flush()
    assert DECODE_CHUNK_CONTRACT.certify(report.losses, report.shifts) == []


# --- WU-14b: transducer event handling — settlement, terminal, honesty ---------


def _sse(payload: dict[str, Any]) -> SSEvent:
    """Wrap one wire event body as the sans-io SSE event the driver feeds."""
    return SSEvent(data=json.dumps(payload), event=payload.get("type"))


def test_transducer_settles_cumulative_usage_into_the_terminal() -> None:
    # message_start and message_delta report CUMULATIVE snapshots covering
    # exactly the keys each names: the terminal StreamEnd merges per source
    # — input/cached keep their message_start values, output takes the
    # final cumulative one — and seq stays monotonic across the splits.
    transducer = MessagesStreamTransducer()
    fed: list[ChatChunk] = []
    fed += transducer.feed(
        _sse(
            {
                "type": "message_start",
                "message": {
                    "id": "msg_01T",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-opus-4-8",
                    "content": [],
                    "usage": {"input_tokens": 14, "output_tokens": 1, "cache_read_input_tokens": 3},
                },
            }
        )
    )
    fed += transducer.feed(
        _sse(
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"output_tokens": 9},
            }
        )
    )
    fed += transducer.feed(_sse({"type": "message_stop"}))

    assert [c.type for c in fed] == [
        ChunkType.STREAM_START,
        ChunkType.METADATA,
        ChunkType.USAGE,
        ChunkType.FINISH,
        ChunkType.USAGE,
        ChunkType.STREAM_STOP,
    ]
    assert [c.seq for c in fed] == list(range(len(fed)))
    usage_chunks = [c for c in fed if c.type == ChunkType.USAGE]
    assert all(c.usage_cumulative is True for c in usage_chunks)
    end = fed[-1].end
    assert end is not None
    assert end.finish is not None and end.finish.native == "end_turn"
    assert end.usage is not None
    assert [(c.source, c.value) for c in end.usage.consumptions] == [
        ("input", 14),
        ("output", 9),
        ("cached", 3),
    ]
    # The tail is empty (the terminal rode message_stop) and lossless.
    tail, report = transducer.flush()
    assert tail == []
    assert report.lossless


def test_transducer_seals_open_slots_at_message_stop() -> None:
    # A block whose content_block_stop never arrived is sealed at the
    # terminal (PART_STOP before STREAM_STOP), advancing the fold to
    # input_complete — the seal-on-end semantics of the WU-10 exemplar.
    transducer = MessagesStreamTransducer()
    fed: list[ChatChunk] = []
    fed += transducer.feed(_sse({"type": "message_start", "message": {"role": "assistant"}}))
    fed += transducer.feed(
        _sse(
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {
                    "type": "tool_use",
                    "id": "toolu_01Seal",
                    "name": "get_weather",
                    "input": {},
                },
            }
        )
    )
    fed += transducer.feed(
        _sse(
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "input_json_delta", "partial_json": '{"city": "Paris"}'},
            }
        )
    )
    terminal = transducer.feed(_sse({"type": "message_stop"}))

    assert [c.type for c in terminal] == [ChunkType.PART_STOP, ChunkType.STREAM_STOP]
    assert terminal[0].index == 0
    response = StreamAccumulator.fold([*fed, *terminal])
    (part,) = response.message.parts
    assert isinstance(part, PartToolCall) and part.status == "input_complete"
    assert part.args_json == '{"city": "Paris"}'
    # The wire's placeholder `input: {}` never seeded the string lane.
    assert part.args() == {"city": "Paris"}


def test_transducer_emits_no_terminal_for_aborted_streams() -> None:
    # A stream that dies before message_stop gets no synthesized
    # STREAM_STOP — the accumulator's aborted-stream sealing is the honest
    # downstream.
    transducer = MessagesStreamTransducer()
    fed: list[ChatChunk] = []
    fed += transducer.feed(_sse({"type": "message_start", "message": {"role": "assistant"}}))
    fed += transducer.feed(
        _sse(
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            }
        )
    )

    tail, report = transducer.flush()
    assert tail == []
    assert report.lossless
    assert all(chunk.type != ChunkType.STREAM_STOP for chunk in fed)


def test_transducer_suppresses_a_second_terminal() -> None:
    # A malformed double message_stop mints no second terminal.
    transducer = MessagesStreamTransducer()
    first = transducer.feed(_sse({"type": "message_stop"}))
    second = transducer.feed(_sse({"type": "message_stop"}))
    assert [c.type for c in first] == [ChunkType.STREAM_STOP]
    assert second == []


def test_error_event_maps_to_the_wire_shaped_taxonomy_record() -> None:
    # The in-band error envelope classifies through the SAME taxonomy table
    # map_error uses (rule 8): canonical open code + verbatim native payload
    # + retryability, as DATA on the stream — a recorded stream replays
    # identically to a live one.
    codec = MessagesCodec()
    out = codec.decode_frame(
        "error",
        json.dumps(
            {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}}
        ),
    )
    (chunk,) = out.value
    assert chunk.type == ChunkType.ERROR
    assert chunk.error is not None
    assert chunk.error.code == "transient"
    assert chunk.error.retryable is True
    assert chunk.error.native == {"type": "overloaded_error", "message": "Overloaded"}

    auth = codec.decode_frame(
        "error",
        json.dumps({"type": "error", "error": {"type": "authentication_error", "message": "x"}}),
    ).value[0]
    assert auth.error is not None
    assert auth.error.code == "auth"
    assert auth.error.retryable is False

    # An unrecognized error type stays open: code "unknown", retryability
    # unclaimed, native verbatim — never a raise (rule 6).
    unknown = codec.decode_frame(
        "error",
        json.dumps({"type": "error", "error": {"type": "solar_flare_error", "message": "?"}}),
    ).value[0]
    assert unknown.error is not None
    assert unknown.error.code == "unknown"
    assert unknown.error.retryable is None
    assert unknown.error.native == {"type": "solar_flare_error", "message": "?"}


def test_stop_sequence_rides_the_finish_chunk_extensions() -> None:
    # message_delta's matched stop sequence is preserved on the FINISH
    # chunk's censused extension with an honest EXTENSIONS record —
    # mirroring the unary edge, never silently dropped.
    codec = MessagesCodec()
    out = codec.decode_frame(
        "message_delta",
        json.dumps(
            {
                "type": "message_delta",
                "delta": {"stop_reason": "stop_sequence", "stop_sequence": "###"},
                "usage": {"output_tokens": 5},
            }
        ),
    )
    finish, usage = out.value
    assert finish.type == ChunkType.FINISH
    assert finish.finish is not None and finish.finish.reason == "stop_sequence"
    assert finish.extensions["anthropic.stop_sequence"] == "###"
    assert usage.type == ChunkType.USAGE and usage.usage_cumulative is True
    assert [(loss.path, loss.disposition.value) for loss in out.losses] == [
        ("message_delta.stop_sequence", "extensions")
    ]
