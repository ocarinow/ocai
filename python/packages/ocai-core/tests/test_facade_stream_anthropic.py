"""Facade streaming for the SECOND provider (WU-14b): the pattern proof, streamed.

The done-criterion of this module IS the claim: `stream`/`astream` run end to
end against `anthropic/messages` with **zero changes to `ocai/chat/facade.py`**
— adding a streaming provider is composing values (fragment catalog + `Direct`
binding + `MessagesCodec`), never touching the facade. Pytest cannot assert a
diff, so the guarantee is stated here and verified by the integrator via
`git diff -- python/packages/ocai-core/src/ocai/chat/facade.py` (empty for
this WU by construction).

Mirrors `test_facade_stream.py` over recorded `tests/http/anthropic_*` SSE
exchanges, replayed through the REAL `HttpxTransport` via respx (rule 10 — no
live keys, no provider-SDK mocks), plus this dialect's own streaming shape:

- recorded stream → canonical chunks in order (this wire signals part
  boundaries explicitly and keep-alives surface as `PING`), the terminal
  `STREAM_STOP` carrying `StreamEnd(usage, finish, report)` with BOTH legs'
  records (the request leg's gate+encode edges + the stream pipeline's flush
  accounting), exposed as `.end` after exhaustion; the terminal usage is the
  per-source settlement of the wire's cumulative snapshots (input from
  `message_start`, final output from `message_delta`); the wire saw the
  codec's `bind_stream` marking (`stream: true` alone — no `stream_options`
  on this dialect) with the bare `x-api-key` credential at the leaf;
- **fold-equals-unary at the port**: on the paired recordings
  (`anthropic_messages_stream.json` vs the unary `anthropic_messages.json` —
  the same logical request answered over both paths),
  `StreamAccumulator.fold(list(model.stream(req)))` is `semantic_equal` to
  `model.chat(req).value` — the fold law at the port — with the verbatim
  `raw` lanes and the response `info` excluded (WU-10/11's paired-assertion
  precedent: stream identity has no canonical chunk lane);
- `astream` twins for both;
- errors map to the taxonomy with wire shape (rule 8), both ways this wire
  can fail: a recorded IN-BAND `error` event surfaces as the wire-shaped
  `ERROR` chunk (`ErrorInfo`: canonical code `transient` + verbatim native
  payload + retryable) with NO terminal synthesized, and a recorded 529 on
  the stream open refines to `TransientError` through the codec's
  `map_error` (layer 2 on the streaming path — the coarse status error
  carries no code; `code == "overloaded_error"` proves the refiner ran).
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

import ocai.anthropic
from ocai.anthropic.messages.codec import ANTHROPIC_BASE_URL
from ocai.anthropic.messages.codec import ANTHROPIC_VERSION
from ocai.anthropic.messages.codec import CANONICAL_CHUNK
from ocai.anthropic.messages.codec import MESSAGES_CHUNK
from ocai.anthropic.messages.codec import MESSAGES_PATH
from ocai.anthropic.messages.codec import MESSAGES_REQUEST
from ocai.anthropic.messages.codec import MessagesCodec
from ocai.chat import CANONICAL_CHAT_REQUEST
from ocai.chat import WireChatModel
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChunkType
from ocai.chat.types import Message
from ocai.chat.types import StreamAccumulator
from ocai.convert.catalog import Catalog
from ocai.core import ApiKey
from ocai.core.canonjson import canonical
from ocai.core.canonjson import semantic_equal
from ocai.core.errors import TransientError
from ocai.core.fidelity import ShiftKind
from ocai.runtime.binding import Binding
from ocai.wire.hosting import Direct
from ocai.wire.transport import HttpxTransport

URL = f"{ANTHROPIC_BASE_URL}{MESSAGES_PATH}"

# One immutable catalog for the whole module — the real composed fragment.
CATALOG = Catalog.of(ocai.anthropic.FRAGMENT)

# The bound resource every recording was minted for.
MODEL = "claude-opus-4-6"

# The canonical chunk order the recorded stream decodes to (the WU-14b
# transducer contract): message_start splits into the stream opener and the
# cumulative opening usage snapshot, the keep-alive surfaces as PING, this
# wire signals part boundaries explicitly (partStart/partStop), message_delta
# splits into the accumulating finish and the cumulative usage update, and
# message_stop is the enriched terminal.
EXPECTED_TYPES = [
    ChunkType.STREAM_START,
    ChunkType.USAGE,
    ChunkType.PING,
    ChunkType.PART_START,
    ChunkType.PART_DELTA,
    ChunkType.PART_DELTA,
    ChunkType.PART_STOP,
    ChunkType.FINISH,
    ChunkType.USAGE,
    ChunkType.STREAM_STOP,
]


def _credentials() -> ApiKey:
    """Anthropic first-party auth: the bare key on `x-api-key`, no scheme."""
    return ApiKey("sk-ant-test", header="x-api-key", scheme="")


def _model() -> WireChatModel:
    """Compose the facade under test: real codec, Direct binding, real catalog.

    The exact `test_facade_stream.py` recipe with only the VALUES swapped —
    codec, binding, catalog — which is the streaming half of the WU-14
    pattern proof.
    """
    binding = Binding(
        host=Direct(ANTHROPIC_BASE_URL),
        credentials=_credentials(),
        transport=HttpxTransport(provider="anthropic"),
    )
    return WireChatModel(MessagesCodec(), binding, CATALOG, model_name=MODEL)


def _request() -> ChatRequest:
    """The canonical request the paired recordings were minted from."""
    return ChatRequest(
        messages=[Message.system("You are concise."), Message.user("Hello, who are you?")]
    )


def _sse_body(pair: dict[str, Any]) -> bytes:
    """Join a recording's verbatim SSE events into one wire body."""
    return ("\n\n".join(pair["response"]["sse"]) + "\n\n").encode()


def _strip_raw(value: Any) -> Any:
    """Drop the verbatim `raw`/`raw_event` lanes at any depth (§8).

    Fold-law equality excludes the untouched provider lanes
    (`spec/canonical-json.md` §8): the streaming path stamps every chunk's
    `raw_event` with its event while the blocking path carries the whole
    body — verbatim lanes can never agree across the two wires.
    """
    if isinstance(value, dict):
        return {k: _strip_raw(v) for k, v in value.items() if k not in ("raw", "raw_event")}
    if isinstance(value, list):
        return [_strip_raw(item) for item in value]
    return value


def _mock_stream(pair: dict[str, Any]) -> Any:
    """Mount the recorded streaming exchange on respx, matched by body."""
    return respx.post(URL, json=pair["request"]["json"]).mock(
        return_value=httpx.Response(
            200, headers=pair["response"]["headers"], content=_sse_body(pair)
        )
    )


def _mock_unary(pair: dict[str, Any]) -> Any:
    """Mount the recorded blocking exchange on respx, matched by body."""
    return respx.post(URL, json=pair["request"]["json"]).mock(
        return_value=httpx.Response(200, json=pair["response"]["json"])
    )


# --- (a) canonical chunks + the two-leg terminal report -------------------------


def _assert_streamed(chunks: list[Any], stream_end: Any, *, sent: httpx.Request) -> None:
    """The WU-14b done-criteria, asserted identically for both twins."""
    assert [c.type for c in chunks] == EXPECTED_TYPES
    assert [c.seq for c in chunks] == list(range(len(chunks)))
    text = "".join(c.delta.text for c in chunks if c.type == ChunkType.PART_DELTA)
    assert text == "I am Claude, an AI assistant."
    # The wrapper captured the terminal record after exhaustion (.end).
    assert stream_end is not None
    assert stream_end is chunks[-1].end
    # The authoritative usage/finish: the terminal StreamEnd settles the
    # wire's cumulative snapshots per source — input from message_start,
    # the final output from message_delta.
    assert stream_end.usage is not None
    assert stream_end.usage.input_tokens == 14
    assert stream_end.usage.output_tokens == 9
    assert stream_end.finish is not None
    assert stream_end.finish.reason == "complete"
    assert stream_end.finish.native == "end_turn"
    # The report spans BOTH legs: request encode + the stream pipeline's
    # flush accounting (the WU-09 seam), in traversal order — and carries
    # this dialect's declared request-leg shifts, honestly lossless AND
    # honestly shifted, exactly like the unary path (WU-14a).
    report = stream_end.report
    assert report is not None
    assert [(e.src, e.dst) for e in report.edges] == [
        (CANONICAL_CHAT_REQUEST, MESSAGES_REQUEST),
        (MESSAGES_CHUNK, CANONICAL_CHUNK),
    ]
    assert report.lossless
    assert [(s.kind, s.path) for s in report.shifts] == [
        (ShiftKind.RELOCATION, "messages[0]"),
        (ShiftKind.EMULATION, "config.max_output_tokens"),
    ]
    # What went over the wire: the recorded streaming body (bind_stream's
    # `stream: true` alone — no stream_options on this dialect), the bare
    # x-api-key credential at the leaf, and the anthropic-version header
    # composed by the Direct host from the dialect's declared traits.
    body = json.loads(sent.content)
    assert body["stream"] is True
    assert "stream_options" not in body
    assert sent.headers["x-api-key"] == "sk-ant-test"
    assert "authorization" not in sent.headers
    assert sent.headers["anthropic-version"] == ANTHROPIC_VERSION


@respx.mock
def test_stream_yields_canonical_chunks_with_terminal_report(load_http) -> None:
    pair = load_http("anthropic_messages_stream.json")
    route = _mock_stream(pair)

    stream = _model().stream(_request())
    chunks = list(stream)

    _assert_streamed(chunks, stream.end, sent=route.calls.last.request)
    # The route matched on the full recorded body — the exact wire payload.
    assert route.call_count == 1


@respx.mock
async def test_astream_yields_canonical_chunks_with_terminal_report(load_http) -> None:
    pair = load_http("anthropic_messages_stream.json")
    route = _mock_stream(pair)

    stream = await _model().astream(_request())
    chunks = [chunk async for chunk in stream]

    _assert_streamed(chunks, stream.end, sent=route.calls.last.request)


# --- (b) fold(stream(req)) == chat(req).value on the paired recordings ----------


def _assert_fold_law(folded: Any, unary_value: Any) -> None:
    """fold(chunks) reproduces the blocking value, raw/info excluded.

    The exclusions follow WU-10/11's paired-assertion precedent: verbatim
    `raw` lanes per canonical-json.md §8, and the response `info` because
    stream identity (id/model echo) has no canonical chunk lane — it rides
    every event's `raw_event` verbatim.
    """
    expected = _strip_raw(unary_value.to_dict())
    assert expected.pop("info", None) is not None  # the unary side carries identity
    actual = _strip_raw(folded.to_dict())
    actual.pop("info", None)
    assert semantic_equal(actual, expected), (
        "fold(stream(req)) did not reproduce chat(req).value.\n"
        f"  expected: {canonical(expected)}\n"
        f"  actual:   {canonical(actual)}"
    )


@respx.mock
def test_fold_of_stream_matches_unary_chat(load_http) -> None:
    _mock_stream(load_http("anthropic_messages_stream.json"))
    _mock_unary(load_http("anthropic_messages.json"))
    model = _model()

    folded = StreamAccumulator.fold(list(model.stream(_request())))
    res = model.chat(_request())

    _assert_fold_law(folded, res.value)


@respx.mock
async def test_fold_of_astream_matches_unary_achat(load_http) -> None:
    _mock_stream(load_http("anthropic_messages_stream.json"))
    _mock_unary(load_http("anthropic_messages.json"))
    model = _model()

    stream = await model.astream(_request())
    folded = StreamAccumulator.fold([chunk async for chunk in stream])
    res = await model.achat(_request())

    _assert_fold_law(folded, res.value)


# --- (c) errors map to the taxonomy with wire shape (rule 8) ---------------------


def _assert_error_stream(chunks: list[Any], stream_end: Any) -> None:
    """The in-band error contract, asserted identically for both twins."""
    assert [c.type for c in chunks] == [
        ChunkType.STREAM_START,
        ChunkType.USAGE,
        ChunkType.PART_START,
        ChunkType.PART_DELTA,
        ChunkType.ERROR,
    ]
    error = chunks[-1].error
    assert error is not None
    # The canonical taxonomy code, mapped through the same _ERROR_TYPES
    # table map_error uses (rule 8 on the in-band streaming path)...
    assert error.code == "transient"
    assert error.retryable is True
    # ...with the provider's error payload verbatim on the native lane, so
    # a recorded stream replays identically to a live one.
    assert error.native == {"type": "overloaded_error", "message": "Overloaded"}
    assert chunks[-1].raw_event["type"] == "error"
    # No terminal is synthesized for a stream that died before message_stop
    # — the accumulator's aborted-stream sealing is the honest downstream.
    assert stream_end is None


@respx.mock
def test_mid_stream_error_event_surfaces_wire_shaped_error_chunk(load_http) -> None:
    # Anthropic can fail IN-BAND: the HTTP exchange is a 200 and the uniform
    # error envelope arrives as an SSE `error` event — status-based mapping
    # never runs, so the codec's decode is the only honest place to classify.
    pair = load_http("anthropic_messages_stream_error.json")
    respx.post(URL).mock(
        return_value=httpx.Response(
            200, headers=pair["response"]["headers"], content=_sse_body(pair)
        )
    )

    stream = _model().stream(_request())
    chunks = list(stream)

    _assert_error_stream(chunks, stream.end)
    # The delivered content survives for the fold; the accumulator seals the
    # open part incomplete — never passed off as complete.
    folded = StreamAccumulator.fold(chunks)
    (part,) = folded.message.parts
    assert part.text == "I am"
    assert part.extensions["ocai.incomplete"] is True


@respx.mock
async def test_mid_stream_error_event_surfaces_wire_shaped_error_chunk_async(load_http) -> None:
    pair = load_http("anthropic_messages_stream_error.json")
    respx.post(URL).mock(
        return_value=httpx.Response(
            200, headers=pair["response"]["headers"], content=_sse_body(pair)
        )
    )

    stream = await _model().astream(_request())
    chunks = [chunk async for chunk in stream]

    _assert_error_stream(chunks, stream.end)


@respx.mock
def test_stream_open_error_refines_through_map_error(load_http) -> None:
    # A 529 on the stream open is coarsely transient by status alone, but
    # the coarse error carries no code: `code == "overloaded_error"` proves
    # the codec's body-aware map_error (layer 2) is wired on the STREAMING
    # path too. The provider's error body rides `raw` (wire shape).
    pair = load_http("anthropic_messages_overloaded_error.json")
    respx.post(URL).mock(
        return_value=httpx.Response(pair["response"]["status"], json=pair["response"]["json"])
    )

    with pytest.raises(TransientError) as exc:
        list(_model().stream(_request()))
    assert exc.value.status == 529
    assert exc.value.code == "overloaded_error"
    assert exc.value.raw == pair["response"]["json"]
    # The refined error chains the coarse one (`raise refined from coarse`).
    assert exc.value.__cause__ is not None
