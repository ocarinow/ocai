"""OpenAI chat_completions unary certification (WU-06).

Drives the interface's two unary edges through the full conformance harness
over the golden edge fixtures in `spec/fixtures/openai/chat_completions/`:

- `check_edge` — running each edge on its fixture `input` yields a value
  `semantic_equal` to `expect`, and the runtime `FieldLoss`/`SemanticShift`
  records match `expect_losses`/`expect_shifts` exactly;
- `certify_edge` — the same payload set certifies against each edge's
  declared `EdgeContract` census with zero violations (an edge claiming
  less loss than it incurs cannot ship);
- catalog routing — the same fixtures convert through a `Catalog` composed
  of the real `ocai.openai.FRAGMENT`, proving the certified edges are what
  the planner actually routes payloads through (a full graph *round trip*
  needs the reverse edges — `decode_request` / an encode-response edge —
  which do not exist yet, so each fixture is exercised in its edge's one
  registered direction);
- the wire-side rule-6 guarantee — the decoder never raises on unknown wire
  material (unknown finish reasons keep the native lane; unknown envelope
  keys sweep into namespaced `extensions`).

The WU-05a seam applies throughout: the canonical request carries no model,
the edge output has no `model` member, and the fixtures' wire bodies gain it
through the codec's `bind_resource` — the facade injection, below the graph.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import cast

import pytest

import ocai.openai
from ocai.chat import CANONICAL_CHAT_REQUEST
from ocai.chat import CANONICAL_CHAT_RESPONSE
from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChunkType
from ocai.chat.types import PartText
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
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_REQUEST
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_RESPONSE
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.openai.chat_completions.codec import ChatCompletionsStreamTransducer
from ocai.openai.chat_completions.edges import EDGES
from ocai.wire import SSEParser
from ocai.wire import SSEvent


def _find_repo_root(start: Path) -> Path:
    """Walk upward until we find the repo root (the dir containing `spec/`)."""
    for parent in [start, *start.parents]:
        if (parent / "spec" / "fixtures").is_dir():
            return parent
    raise RuntimeError("could not locate repo root (no spec/fixtures/ found)")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
FIXTURES_DIR = REPO_ROOT / "spec" / "fixtures" / "openai" / "chat_completions"
FIXTURE_PATHS = sorted(FIXTURES_DIR.glob("*.json"))
STREAMS_DIR = FIXTURES_DIR / "streams"

_CODEC = ChatCompletionsCodec()
ENCODE_EDGE = next(edge for edge in EDGES if edge.dst == CHAT_COMPLETIONS_REQUEST)
DECODE_EDGE = next(edge for edge in EDGES if edge.src == CHAT_COMPLETIONS_RESPONSE)


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


# --- The fixture set itself covers what WU-06 says it covers -------------------


def test_fixture_set_is_not_empty_and_covers_the_wu06_scenarios() -> None:
    assert len(FIXTURE_PATHS) >= 5, (
        f"WU-06 requires at least five edge fixtures in {FIXTURES_DIR}; found {len(FIXTURE_PATHS)}"
    )
    losses = [
        (entry["path"], entry["disposition"])
        for path in FIXTURE_PATHS
        for entry in _load(path)["expect_losses"]
    ]
    # (c) the tool round reports the is_error DROPPED loss on the encode edge.
    assert ("messages[2].parts[0].is_error", "dropped") in losses
    # (d) the out-of-range temperature reports APPROXIMATED, passed verbatim.
    assert ("config.temperature", "approximated") in losses
    # (e) the extensions sweep reports both envelope keys as EXTENSIONS.
    assert ("service_tier", "extensions") in losses
    assert ("system_fingerprint", "extensions") in losses


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
    return Catalog.of(ocai.openai.FRAGMENT)


@pytest.mark.parametrize("path", FIXTURE_PATHS, ids=lambda p: p.name)
def test_fixture_converts_through_the_catalog(path: Path) -> None:
    fixture = _load(path)
    catalog = _catalog()
    if _is_encode(fixture):
        converted = catalog.convert(
            ChatRequest.from_dict(fixture["input"]),
            CANONICAL_CHAT_REQUEST,
            CHAT_COMPLETIONS_REQUEST,
        )
        rendered = _CODEC.bind_resource(converted.value, fixture["expect"]["model"])
    else:
        converted = catalog.convert(
            fixture["input"], CHAT_COMPLETIONS_RESPONSE, CANONICAL_CHAT_RESPONSE
        )
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
        "id": "chatcmpl-unknown",
        "object": "chat.completion",
        "created": 1767225600,
        "model": "gpt-4o-2024-08-06",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "TELEPATHY_LIMIT",
            }
        ],
        "routing_tier": {"shard": 7},
    }
    out = DECODE_EDGE.fn(payload)  # total decode: must not raise
    response = out.value
    # The unknown finish reason decodes open with the native lane verbatim.
    assert response.finish is not None
    assert response.finish.reason == "unknown"
    assert response.finish.native == "TELEPATHY_LIMIT"
    # The unknown envelope key sweeps into the namespaced extensions bag,
    # with an honest EXTENSIONS record — never silently dropped. (Its path is
    # deliberately NOT in the census: a tomorrow-key cannot be declared in
    # advance, so the sweep is the rule-6 safety net — and the moment such a
    # key lands in a golden fixture, certification flags it until the census
    # names it. That is the drift alarm working, not a bug.)
    assert response.extensions["openai.routing_tier"] == {"shard": 7}
    assert ("routing_tier", "extensions") in [
        (loss.path, loss.disposition.value) for loss in out.losses
    ]


# --- WU-10: the streaming edge — fold triples over recorded SSE wire logs ------
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
    `ChatCompletionsStreamTransducer`. The transducer is per-stream state,
    so a fresh one replaces it after each terminal `STREAM_STOP` — the
    walker (`check_fold_triples`) reuses one decoder across every fixture
    in the directory.
    """
    state = {"transducer": ChatCompletionsStreamTransducer()}

    def decode(event_text: str) -> list[dict[str, Any]]:
        decoded: list[dict[str, Any]] = []
        for frame in SSEParser().feed(event_text + "\n\n"):
            for chunk in state["transducer"].feed(frame):
                decoded.append(_strip_raw(chunk.to_dict()))
                if chunk.type == ChunkType.STREAM_STOP:
                    state["transducer"] = ChatCompletionsStreamTransducer()
        return decoded

    return decode


def test_fold_triples_over_recorded_streams() -> None:
    checked = check_fold_triples(STREAMS_DIR, decode_event=_wire_decoder(), fold=_fold_dicts)
    # WU-10 requires the three scenarios: plain text, tool-call args, and
    # usage-in-final-chunk via stream_options.
    assert len(checked) >= 3
    names = {path.name for path in checked}
    assert {
        "stream_plain_text.json",
        "stream_tool_call_args.json",
        "stream_usage_final_chunk.json",
    } <= names


def test_paired_stream_fold_matches_the_unary_canonical() -> None:
    # Full paired equality includes info; only raw evidence is excluded.
    triple = _load(STREAMS_DIR / "stream_usage_final_chunk.json")
    unary = _load(FIXTURES_DIR / "response_plain_text.json")

    folded = _fold_dicts(triple["chunks"])
    expected = _strip_raw(unary["expect"])
    assert semantic_equal(folded, expected), (
        "fold(chunks) did not reproduce the paired unary canonical.\n"
        f"  expected: {canonical(expected)}\n"
        f"  actual:   {canonical(folded)}"
    )


# --- WU-10: transducer frame handling — multi-signal splits, terminal, n>1 -----


def _sse(payload: dict[str, Any]) -> SSEvent:
    """Wrap one wire chunk body as the sans-io SSE event the driver feeds."""
    return SSEvent(data=json.dumps(payload))


def _chunk_frame(*choices: dict[str, Any], usage: dict[str, Any] | None = None) -> SSEvent:
    """Build a wire-accurate `chat.completion.chunk` frame around `choices`."""
    body: dict[str, Any] = {
        "id": "chatcmpl-test",
        "object": "chat.completion.chunk",
        "created": 1767225600,
        "model": "gpt-4o-2024-08-06",
        "choices": list(choices),
    }
    if usage is not None:
        body["usage"] = usage
    return _sse(body)


def test_transducer_splits_role_and_content_frame() -> None:
    # One frame, two signals: the opening role and the first text fragment.
    # The split emits ordered chunks, with the synthesized PART_START
    # carrying the PartText skeleton before the first delta.
    transducer = ChatCompletionsStreamTransducer()
    chunks = transducer.feed(
        _chunk_frame({"index": 0, "delta": {"role": "assistant", "content": "Hi"}})
    )

    assert [c.type for c in chunks] == [
        ChunkType.STREAM_START,
        ChunkType.METADATA,
        ChunkType.PART_START,
        ChunkType.PART_DELTA,
    ]
    assert [c.seq for c in chunks] == [0, 1, 2, 3]
    start, delta = chunks[2], chunks[3]
    assert isinstance(start.part, PartText) and start.part.text == ""
    assert start.index == delta.index == 0
    assert delta.delta is not None and delta.delta.text == "Hi"  # type: ignore[union-attr]


def test_transducer_splits_id_and_arguments_frame() -> None:
    # One tool_calls entry carrying id AND a non-empty argument fragment:
    # the PART_START skeleton must precede the first DeltaToolArgs.
    transducer = ChatCompletionsStreamTransducer()
    chunks = transducer.feed(
        _chunk_frame(
            {
                "index": 0,
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": '{"ci'},
                        }
                    ]
                },
            }
        )
    )

    assert [c.type for c in chunks] == [
        ChunkType.METADATA, ChunkType.PART_START, ChunkType.PART_DELTA]
    _, start, delta = chunks
    assert isinstance(start.part, PartToolCall)
    assert start.part.call_id == "call_1"
    assert start.part.name == "get_weather"
    assert start.part.status == "input_streaming"
    # The stateless slot mapping: tool_calls wire index 0 rides slot 1
    # (slot 0 is the message text lane), mirroring the unary part order.
    assert start.index == delta.index == 1
    assert delta.delta is not None and delta.delta.fragment == '{"ci'  # type: ignore[union-attr]


def test_transducer_splits_several_tool_call_entries_in_one_frame() -> None:
    transducer = ChatCompletionsStreamTransducer()
    chunks = transducer.feed(
        _chunk_frame(
            {
                "index": 0,
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "call_a",
                            "type": "function",
                            "function": {"name": "alpha", "arguments": ""},
                        },
                        {
                            "index": 1,
                            "id": "call_b",
                            "type": "function",
                            "function": {"name": "beta", "arguments": ""},
                        },
                    ]
                },
            }
        )
    )

    assert [c.type for c in chunks] == [
        ChunkType.METADATA, ChunkType.PART_START, ChunkType.PART_START]
    assert [c.index for c in chunks] == [None, 1, 2]
    assert [c.seq for c in chunks] == [0, 1, 2]


def test_transducer_emits_terminal_stream_stop_on_done() -> None:
    # [DONE] seals the open tool slot (PART_STOP -> input_complete in the
    # fold) and emits STREAM_STOP carrying StreamEnd(usage, finish): usage
    # from the stream_options final chunk, finish from the accumulated
    # finish_reason.
    transducer = ChatCompletionsStreamTransducer()
    fed: list[ChatChunk] = []
    fed += transducer.feed(
        _chunk_frame(
            {
                "index": 0,
                "delta": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": '{"city": "Paris"}'},
                        }
                    ],
                },
            }
        )
    )
    fed += transducer.feed(_chunk_frame({"index": 0, "delta": {}, "finish_reason": "tool_calls"}))
    fed += transducer.feed(
        _chunk_frame(usage={"prompt_tokens": 12, "completion_tokens": 9, "total_tokens": 21})
    )
    terminal = transducer.feed(SSEvent(data="[DONE]"))

    assert [c.type for c in terminal] == [ChunkType.PART_STOP, ChunkType.STREAM_STOP]
    seal, stop = terminal
    assert seal.index == 1  # the tool slot opened by the id frame
    assert stop.end is not None
    assert stop.end.finish is not None and stop.end.finish.native == "tool_calls"
    assert stop.end.usage is not None and stop.end.usage.output_tokens == 9
    # seq stays monotonic across the whole stream, splits included.
    assert [c.seq for c in [*fed, *terminal]] == list(range(len(fed) + len(terminal)))

    # The tail is empty (the terminal was emitted at [DONE]) and lossless.
    tail, report = transducer.flush()
    assert tail == []
    assert report.lossless

    # The stream folds to the blocking shape: the sealed tool call is
    # input_complete, the terminal usage/finish are authoritative.
    response = StreamAccumulator.fold([*fed, *terminal])
    (part,) = response.message.parts
    assert isinstance(part, PartToolCall) and part.status == "input_complete"
    assert part.args_json == '{"city": "Paris"}'


def test_transducer_emits_no_terminal_for_aborted_streams() -> None:
    # A stream that dies before [DONE] gets no synthesized STREAM_STOP —
    # the accumulator's aborted-stream sealing is the honest downstream.
    transducer = ChatCompletionsStreamTransducer()
    fed = transducer.feed(
        _chunk_frame({"index": 0, "delta": {"role": "assistant", "content": "cut"}})
    )

    tail, report = transducer.flush()
    assert tail == []
    assert report.lossless
    assert all(chunk.type != ChunkType.STREAM_STOP for chunk in fed)


def test_transducer_drops_foreign_choices_with_report() -> None:
    # The WU-10 admission stance for n>1 streams: choice 0 is the message,
    # foreign choices are dropped per frame with a reported FieldLoss
    # (recoverable verbatim from raw_event) — never surfaced, never silent.
    transducer = ChatCompletionsStreamTransducer()
    chunks = transducer.feed(
        _chunk_frame(
            {"index": 0, "delta": {"role": "assistant", "content": "a"}},
            {"index": 1, "delta": {"role": "assistant", "content": "b"}},
        )
    )
    transducer.feed(SSEvent(data="[DONE]"))

    deltas = [c for c in chunks if c.type == ChunkType.PART_DELTA]
    assert [d.delta.text for d in deltas] == ["a"]  # type: ignore[union-attr]
    _, report = transducer.flush()
    assert not report.lossless
    (loss,) = report.losses
    assert loss.path == "choices[1:]"
    assert loss.disposition is Disposition.DROPPED
