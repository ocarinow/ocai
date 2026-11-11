"""Facade streaming (WU-11): `WireChatModel.stream`/`astream`, end to end.

The §8 streaming lifecycle proven over the real wire path: recorded SSE
exchanges from `tests/http/` are replayed through the REAL `HttpxTransport`
via respx (rule 10 — no live keys, no provider-SDK mocks), beneath a facade
composed of the real `ocai.openai.FRAGMENT` catalog, a `Direct` first-party
binding, and the `ChatCompletionsCodec`:

- recorded stream → canonical chunks in order, the terminal `STREAM_STOP`
  carrying `StreamEnd(usage, finish, report)` with BOTH legs' records (the
  request leg's encode edge + the stream pipeline's flush accounting — the
  WU-09 seam), exposed as `.end` after exhaustion; the wire saw the codec's
  `bind_stream` marking (`stream: true`, `stream_options.include_usage`);
- **the M2 criterion**: on the paired recordings (the WU-10 stream fixture's
  event log vs the same logical request answered blocking),
  `StreamAccumulator.fold(list(model.stream(req)))` is `semantic_equal` to
  `model.chat(req).value` — the fold law at the port — with the verbatim
  `raw` lanes and the response `info` excluded (WU-10's paired-assertion
  precedent: stream identity has no canonical chunk lane);
- `astream` twins for both;
- errors map to the taxonomy with wire shape (rule 8): a recorded 400
  overflow on the streaming request refines to `ContextLengthError` through
  the codec's `map_error` (layer 2 on the streaming path), and a recorded
  stream that DIES mid-body surfaces `TransientError` — chunks delivered
  before the abort survive, and no terminal is synthesized.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from collections.abc import Callable
from collections.abc import Iterator
from typing import Any
from typing import cast

import httpx
import pytest
import respx

import ocai.openai
from ocai.chat import CANONICAL_CHAT_REQUEST
from ocai.chat import WireChatModel
from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import ChunkType
from ocai.chat.types import DeltaText
from ocai.chat.types import Message
from ocai.chat.types import StreamAccumulator
from ocai.chat.types import StreamEnd
from ocai.convert.catalog import Catalog
from ocai.core import ApiKey
from ocai.core.canonjson import canonical
from ocai.core.canonjson import semantic_equal
from ocai.core.errors import ContextLengthError
from ocai.core.errors import TransientError
from ocai.openai.chat_completions.codec import CANONICAL_CHUNK
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_CHUNK
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_PATH
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_REQUEST
from ocai.openai.chat_completions.codec import OPENAI_BASE_URL
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.runtime.binding import Binding
from ocai.wire.hosting import Direct
from ocai.wire.transport import HttpxTransport

# The `load_http` conftest fixture: a recorded request/response pair by file name.
type LoadHttp = Callable[[str], dict[str, Any]]

URL = f"{OPENAI_BASE_URL}{CHAT_COMPLETIONS_PATH}"

# One immutable catalog for the whole module — the real composed fragment.
CATALOG = Catalog.of(ocai.openai.FRAGMENT)

# The canonical chunk order the recorded stream decodes to (WU-10's
# transducer contract): the opening role frame, the synthesized text
# skeleton, three text deltas (the first empty — the role frame carries
# `content: ""`), the finish, the stream_options usage frame, the terminal.
EXPECTED_TYPES = [
    ChunkType.STREAM_START,
    ChunkType.METADATA,
    ChunkType.PART_START,
    ChunkType.PART_DELTA,
    ChunkType.PART_DELTA,
    ChunkType.PART_DELTA,
    ChunkType.FINISH,
    ChunkType.USAGE,
    ChunkType.STREAM_STOP,
]


def _model() -> WireChatModel:
    """Compose the facade under test: real codec, Direct binding, real catalog."""
    binding = Binding(
        host=Direct(OPENAI_BASE_URL),
        credentials=ApiKey("sk-test"),
        transport=HttpxTransport(provider="openai"),
    )
    return WireChatModel(ChatCompletionsCodec(), binding, CATALOG, model_name="gpt-4o")


def _request() -> ChatRequest:
    """The canonical request the paired recordings were minted from."""
    return ChatRequest(messages=[Message.user("Hello!")])


def _sse_body(pair: dict[str, Any]) -> bytes:
    """Join a recording's verbatim SSE events into one wire body."""
    return ("\n\n".join(pair["response"]["sse"]) + "\n\n").encode()


def _strip_raw(value: Any) -> Any:
    """Drop the verbatim `raw`/`raw_event` lanes at any depth (§8).

    Fold-law equality excludes the untouched provider lanes
    (`spec/canonical-json.md` §8): the streaming path stamps every chunk's
    `raw_event` with its frame while the blocking path carries the whole
    body — verbatim lanes can never agree across the two wires.
    """
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        return {k: _strip_raw(v) for k, v in mapping.items() if k not in ("raw", "raw_event")}
    if isinstance(value, list):
        return [_strip_raw(item) for item in cast(list[Any], value)]
    return value


def _mock_stream(pair: dict[str, Any]) -> respx.Route:
    """Mount the recorded streaming exchange on respx, matched by body."""
    return respx.post(URL, json=pair["request"]["json"]).mock(
        return_value=httpx.Response(
            200, headers=pair["response"]["headers"], content=_sse_body(pair)
        )
    )


def _mock_unary(pair: dict[str, Any]) -> respx.Route:
    """Mount the recorded blocking exchange on respx, matched by body."""
    return respx.post(URL, json=pair["request"]["json"]).mock(
        return_value=httpx.Response(200, json=pair["response"]["json"])
    )


class _DyingStream(httpx.SyncByteStream, httpx.AsyncByteStream):
    """A recorded body that dies mid-stream: yields its bytes, then resets."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __iter__(self) -> Iterator[bytes]:
        yield self._body
        raise httpx.ReadError("connection reset mid-stream")

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self._body
        raise httpx.ReadError("connection reset mid-stream")


# --- (a) canonical chunks + the two-leg terminal report -------------------------


def _assert_streamed(
    chunks: list[ChatChunk], stream_end: StreamEnd | None, *, sent: httpx.Request
) -> None:
    """The WU-11 done-criteria, asserted identically for both twins."""
    import json

    assert [c.type for c in chunks] == EXPECTED_TYPES
    assert [c.seq for c in chunks] == list(range(len(chunks)))
    fragments: list[str] = []
    for chunk in chunks:
        if chunk.type == ChunkType.PART_DELTA:
            assert isinstance(chunk.delta, DeltaText)
            fragments.append(chunk.delta.text)
    text = "".join(fragments)
    assert text == "Hello! How can I help you today?"
    # The wrapper captured the terminal record after exhaustion (.end).
    assert stream_end is not None
    assert stream_end is chunks[-1].end
    # The authoritative usage/finish from the terminal StreamEnd.
    assert stream_end.usage is not None
    assert stream_end.usage.input_tokens == 12
    assert stream_end.finish is not None
    assert stream_end.finish.reason == "complete"
    assert stream_end.finish.native == "stop"
    # The report spans BOTH legs: request encode + the stream pipeline's
    # flush accounting (the WU-09 seam), in traversal order.
    report = stream_end.report
    assert report is not None
    assert [(e.src, e.dst) for e in report.edges] == [
        (CANONICAL_CHAT_REQUEST, CHAT_COMPLETIONS_REQUEST),
        (CHAT_COMPLETIONS_CHUNK, CANONICAL_CHUNK),
    ]
    assert report.lossless
    # What went over the wire: the recorded streaming body (bind_stream's
    # marking included) with the credential applied at the leaf.
    body = json.loads(sent.content)
    assert body["stream"] is True
    assert body["stream_options"] == {"include_usage": True}
    assert sent.headers["authorization"] == "Bearer sk-test"


@respx.mock
def test_stream_yields_canonical_chunks_with_terminal_report(load_http: LoadHttp) -> None:
    pair = load_http("openai_chat_completion_stream.json")
    route = _mock_stream(pair)

    stream = _model().stream(_request())
    chunks = list(stream)

    _assert_streamed(chunks, stream.end, sent=route.calls.last.request)
    # The route matched on the full recorded body — the exact wire payload.
    assert route.call_count == 1


@respx.mock
async def test_astream_yields_canonical_chunks_with_terminal_report(load_http: LoadHttp) -> None:
    pair = load_http("openai_chat_completion_stream.json")
    route = _mock_stream(pair)

    stream = await _model().astream(_request())
    chunks = [chunk async for chunk in stream]

    _assert_streamed(chunks, stream.end, sent=route.calls.last.request)


# --- (b) THE M2 CRITERION: fold(stream(req)) == chat(req).value ------------------


def _assert_fold_law(folded: ChatResponse, unary_value: ChatResponse) -> None:
    """Compare the complete canonical response, excluding only raw wire evidence."""
    expected = _strip_raw(unary_value.to_dict())
    actual = _strip_raw(folded.to_dict())
    assert semantic_equal(actual, expected), (
        "fold(stream(req)) did not reproduce chat(req).value.\n"
        f"  expected: {canonical(expected)}\n"
        f"  actual:   {canonical(actual)}"
    )


@respx.mock
def test_fold_of_stream_matches_unary_chat(load_http: LoadHttp) -> None:
    _mock_stream(load_http("openai_chat_completion_stream.json"))
    _mock_unary(load_http("openai_chat_completion_stream_paired.json"))
    model = _model()

    folded = StreamAccumulator.fold(list(model.stream(_request())))
    res = model.chat(_request())

    _assert_fold_law(folded, res.value)


@respx.mock
async def test_fold_of_astream_matches_unary_achat(load_http: LoadHttp) -> None:
    _mock_stream(load_http("openai_chat_completion_stream.json"))
    _mock_unary(load_http("openai_chat_completion_stream_paired.json"))
    model = _model()

    stream = await model.astream(_request())
    folded = StreamAccumulator.fold([chunk async for chunk in stream])
    res = await model.achat(_request())

    _assert_fold_law(folded, res.value)


# --- (d) errors map to the taxonomy with wire shape (rule 8) ---------------------


@respx.mock
def test_stream_open_error_refines_through_map_error(load_http: LoadHttp) -> None:
    # A context overflow is a 400 on this wire: only the codec's map_error
    # can name it — proof the layer-2 refiner is wired on the STREAMING
    # path too. The provider's error body rides `raw` (wire shape).
    pair = load_http("openai_chat_completion_context_length.json")
    respx.post(URL).mock(
        return_value=httpx.Response(pair["response"]["status"], json=pair["response"]["json"])
    )

    with pytest.raises(ContextLengthError) as exc:
        list(_model().stream(_request()))
    assert exc.value.code == "context_length_exceeded"
    assert exc.value.raw == pair["response"]["json"]
    # The refined error chains the coarse one (`raise refined from coarse`).
    assert exc.value.__cause__ is not None


@respx.mock
def test_mid_stream_death_maps_to_transient_error(load_http: LoadHttp) -> None:
    # The recorded stream died after three frames: the delivered chunks
    # survive, the wire failure surfaces as the taxonomy TransientError,
    # and NO terminal is synthesized (the accumulator's aborted-stream
    # sealing is the honest downstream).
    pair = load_http("openai_chat_completion_stream_abort.json")
    respx.post(URL).mock(
        return_value=httpx.Response(
            200, headers=pair["response"]["headers"], stream=_DyingStream(_sse_body(pair))
        )
    )

    stream = _model().stream(_request())
    received: list[ChatChunk] = []
    with pytest.raises(TransientError):
        # extend() appends element by element, so the chunks delivered
        # before the abort survive the raise.
        received.extend(stream)

    assert [c.type for c in received] == [
        ChunkType.STREAM_START,
        ChunkType.METADATA,
        ChunkType.PART_START,
        ChunkType.PART_DELTA,
        ChunkType.PART_DELTA,
        ChunkType.PART_DELTA,
    ]
    assert stream.end is None  # aborted: no terminal, honestly


@respx.mock
async def test_mid_stream_death_maps_to_transient_error_async(load_http: LoadHttp) -> None:
    pair = load_http("openai_chat_completion_stream_abort.json")
    respx.post(URL).mock(
        return_value=httpx.Response(
            200, headers=pair["response"]["headers"], stream=_DyingStream(_sse_body(pair))
        )
    )

    stream = await _model().astream(_request())
    with pytest.raises(TransientError):
        _ = [chunk async for chunk in stream]

    # Partial delivery is proven by the sync twin; here the taxonomy
    # mapping and the absent terminal are the async-path assertions.
    assert stream.end is None
