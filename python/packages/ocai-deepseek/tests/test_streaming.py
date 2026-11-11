"""Recorded DeepSeek full-fold qualification through graph and public execution."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

import ocai.chat
import ocai.deepseek
from ocai.chat.types import AsyncChatStream
from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatStream
from ocai.chat.types import ChunkType
from ocai.chat.types import StreamAccumulator
from ocai.convert import Catalog
from ocai.convert.conformance import assert_fold_triple
from ocai.core import ApiKey
from ocai.core.canonjson import semantic_equal
from ocai.core.ir import is_json_array
from ocai.core.ir import is_json_object
from ocai.core.result import CallContext
from ocai.deepseek.chat_completions.codec import DeepSeekCodec
from ocai.deepseek.chat_completions.edges import DECODE_CHUNK_CONTRACT
from ocai.deepseek.chat_completions.edges import TRANSDUCERS
from ocai.deepseek.chat_completions.streaming import DeepSeekStreamCodec
from ocai.deepseek.chat_completions.streaming import DeepSeekStreamTransducer
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.observe import ObserveEvent
from ocai.wire import SSEParser
from ocai.wire import SSEvent
from ocai.wire.http import HttpRequest
from ocai.wire.transport import HttpxTransport

ROOT = Path(__file__).resolve().parents[4]
SPEC = ROOT / "spec/fixtures/deepseek/chat_completions/streams"
HTTP = Path(__file__).parent / "http"
URL = "https://api.deepseek.com/chat/completions"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _strip(value: Any) -> Any:
    if is_json_object(value):
        return {key: _strip(item) for key, item in value.items() if key not in {"raw", "raw_event"}}
    if is_json_array(value):
        return [_strip(item) for item in value]
    return value


def _body(pair: dict[str, Any]) -> bytes:
    return ("\n\n".join(pair["response"]["sse"]) + "\n\n").encode()


@pytest.mark.parametrize("name", ["text", "tools", "parallel", "unknown_finish"])
def test_stream_edge_full_fold_and_independent_census(name: str) -> None:
    fixture = _load(SPEC / f"stream_{name}.json")
    transducer = DeepSeekStreamTransducer()

    def decode(line: str) -> list[dict[str, Any]]:
        chunks: list[ChatChunk] = []
        for frame in SSEParser().feed(line + "\n\n"):
            chunks.extend(transducer.feed(frame))
        return [_strip(chunk.to_dict()) for chunk in chunks]

    assert_fold_triple(fixture, decode_event=decode,
        fold=lambda chunks: StreamAccumulator.fold(
            ChatChunk.from_dict(c) for c in chunks).to_dict())
    tail, report = transducer.flush()
    assert not tail
    assert DECODE_CHUNK_CONTRACT.certify(report.losses, report.shifts) == []
    assert [(loss.path, loss.disposition.value) for loss in report.losses] == [
        (loss["path"], loss["disposition"]) for loss in fixture["expect_losses"]]
    pair = _load(HTTP / f"deepseek_chat_stream_{name}_paired.json")
    unary = DeepSeekCodec().decode_response(pair["response"]["json"]).value
    assert semantic_equal(fixture["response"], _strip(unary.to_dict()))
    edge = TRANSDUCERS[0]
    pipeline = Catalog.of(ocai.deepseek.FRAGMENT).stream_converter(edge.src, edge.dst)
    actual: list[ChatChunk] = []
    for frame in SSEParser().feed("\n\n".join(fixture["wire_events"]) + "\n\n"):
        actual.extend(pipeline.feed(frame))
    extra, reports = pipeline.flush()
    actual.extend(extra)
    assert len(reports) == 1 and reports[0].src.provider == "deepseek"
    assert semantic_equal(_strip(StreamAccumulator.fold(actual).to_dict()), fixture["response"])


@pytest.mark.parametrize("name", ["text", "tools", "parallel", "unknown_finish"])
@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_recorded_public_unary_and_streaming_faces(name: str, asynchronous: bool) -> None:
    pair = _load(HTTP / f"deepseek_chat_stream_{name}.json")
    unary_pair = _load(HTTP / f"deepseek_chat_stream_{name}_paired.json")
    streaming_route = respx.post(URL, json=pair["request"]["json"]).mock(return_value=
        httpx.Response(200, headers=pair["response"]["headers"], content=_body(pair)))
    unary_route = respx.post(URL, json=unary_pair["request"]["json"]).mock(return_value=
        httpx.Response(200, json=unary_pair["response"]["json"]))
    # Decode the pinned native request using the plugin's public audit direction.
    request: ChatRequest = DeepSeekCodec().decode_request(unary_pair["request"]["json"]).value
    request.extensions.clear()  # routing model echo is bound by the model front door
    transport = HttpxTransport(provider="deepseek")
    model = ocai.chat.model("deepseek/deepseek-flash", credentials=ApiKey("sk-test-stream"),
                           catalog=Catalog.of(ocai.deepseek.FRAGMENT), transport=transport)
    ctx = CallContext(call_id=f"call-{name}", tenant="tenant-test",
                      correlation_id="correlation-test")
    try:
        prepared = model.prepare(request, streaming=True)
        assert not streaming_route.calls
        unary = (await model.achat(request, ctx=ctx) if asynchronous
                 else model.chat(request, ctx=ctx))
        stream: ChatStream | AsyncChatStream
        if asynchronous:
            stream = await prepared.astream(ctx=ctx)
            chunks = [chunk async for chunk in stream]
        else:
            sync_stream = prepared.stream(ctx=ctx)
            chunks = list(sync_stream)
            stream = sync_stream
        assert stream.end is not None and stream.outcome is not None
        assert stream.outcome.status == "completed"
        assert stream.end.usage == unary.usage
        assert stream.end.report is not None and len(stream.end.report.edges) == 2
        assert stream.end.report.edges[-1].src.provider == "deepseek"
        assert semantic_equal(_strip(StreamAccumulator.fold(chunks).to_dict()),
                              _strip(unary.value.to_dict()))
        assert stream.end.finish == unary.value.finish
    finally:
        transport.close()
        await transport.aclose()
    assert streaming_route.call_count == unary_route.call_count == 1
    for route in (streaming_route, unary_route):
        sent = route.calls.last.request
        assert sent.headers["authorization"] == "Bearer sk-test-stream"
        assert "tenant-test" not in sent.content.decode()


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("failure", ["aborted", "truncated", "missing_finish"])
@respx.mock
async def test_partial_execution_never_manufactures_success(
    failure: str, asynchronous: bool,
) -> None:
    pair = _load(HTTP / ("deepseek_chat_stream_aborted.json" if failure == "aborted"
                        else "deepseek_chat_stream_text.json"))
    if failure == "truncated":
        pair["response"]["sse"].pop()  # exact recording prefix: usage present, sentinel missing
    if failure == "missing_finish":
        pair["response"]["sse"].pop(-2)  # no final usage/finish frame before sentinel
    route = respx.post(URL).mock(return_value=httpx.Response(
        200, headers=pair["response"]["headers"], content=_body(pair)))
    transport = HttpxTransport(provider="deepseek")
    model = ocai.chat.model("deepseek/deepseek-flash", credentials=ApiKey("sk-test"),
                           catalog=Catalog.of(ocai.deepseek.FRAGMENT), transport=transport)
    request = ChatRequest.from_dict(
        {"messages": [{"role": "user", "parts": [{"type": "text", "text": "Hi"}]}]})
    try:
        stream: ChatStream | AsyncChatStream
        if asynchronous:
            stream = await model.astream(request)
            chunks = [chunk async for chunk in stream]
        else:
            sync_stream = model.stream(request)
            chunks = list(sync_stream)
            stream = sync_stream
        assert stream.end is None and stream.outcome is not None
        assert stream.outcome.status in {"failed", "incomplete"}
        assert not any(chunk.type == ChunkType.STREAM_STOP for chunk in chunks)
        assert stream.outcome.report is not None
        if failure != "missing_finish":
            assert stream.outcome.usage is not None
            assert stream.outcome.usage.output_tokens == 4
        else:
            assert stream.outcome.usage is None
        assert StreamAccumulator.fold(chunks).info is not None
    finally:
        transport.close()
        await transport.aclose()
    assert route.call_count == 1


UNKNOWN_FRAMES: list[Any] = [None, [], 1, "future", {"choices": [None]},
    {"choices": [{"delta": {"tool_calls": [7]}, "finish_reason": []}]},
    {"choices": [{"delta": {"content": 7}}]}, {"usage": ["future"]},
    {"future_event": {"opaque": True}}]


@pytest.mark.parametrize("raw", UNKNOWN_FRAMES)
def test_unknown_frames_decode_totally_with_evidence(raw: Any) -> None:
    result = DeepSeekStreamCodec().decode_frame(None, json.dumps(raw))
    assert result.losses
    assert DECODE_CHUNK_CONTRACT.certify(result.losses, result.shifts) == []
    assert any(chunk.raw_event == raw for chunk in result.value)


def test_interleaved_transducers_keep_metadata_and_arguments_separate() -> None:
    pair = _load(HTTP / "deepseek_chat_stream_tools.json")
    events = list(SSEParser().feed(_body(pair)))
    left, right = DeepSeekStreamTransducer(), DeepSeekStreamTransducer()
    a: list[ChatChunk] = []
    b: list[ChatChunk] = []
    for event in events:
        a.extend(left.feed(event))
        other = deepcopy(event)
        if other.data != "[DONE]":
            assert isinstance(other.data, str)
            raw = json.loads(other.data)
            raw["id"] = "completion-second"
            other = SSEvent(data=json.dumps(raw))
        b.extend(right.feed(other))
    one, two = StreamAccumulator.fold(a), StreamAccumulator.fold(b)
    assert one.info and one.info.id and two.info and two.info.id
    assert one.info.id.id == "completion-synthetic"
    assert two.info.id.id == "completion-second"
    assert one.message == two.message


class _Capture:
    def __init__(self) -> None:
        self.requests: list[HttpRequest] = []
        self.outcomes: list[Outcome] = []
        self.events: list[ObserveEvent] = []

    def on_request(self, request: HttpRequest) -> Proceed:
        self.requests.append(request)
        return Proceed()

    def on_outcome(self, outcome: Outcome) -> Proceed:
        self.outcomes.append(outcome)
        return Proceed()

    def on_event(self, event: ObserveEvent) -> None:
        self.events.append(event)


@respx.mock
async def test_concurrent_streams_keep_context_and_credentials_isolated() -> None:
    pair = _load(HTTP / "deepseek_chat_stream_text.json")
    routes = [respx.post(URL, headers={"authorization": f"Bearer sk-test-{index}"}).mock(
        return_value=httpx.Response(200, headers=pair["response"]["headers"], content=_body(pair)))
        for index in range(2)]

    async def consume(index: int) -> _Capture:
        capture = _Capture()
        ctx = CallContext(call_id=f"call-{index}", tenant=f"tenant-{index}")
        transport = HttpxTransport(provider="deepseek")
        model = ocai.chat.model("deepseek/deepseek-flash", credentials=ApiKey(f"sk-test-{index}"),
            catalog=Catalog.of(ocai.deepseek.FRAGMENT), transport=transport,
            policies=[capture], observers=[capture])
        try:
            stream = await model.astream(ChatRequest(messages=[]), ctx=ctx)
            chunks = [chunk async for chunk in stream]
            assert StreamAccumulator.fold(chunks).info is not None
            assert stream.end and stream.end.report
            assert "sk-test" not in repr(stream.end.report)
        finally:
            transport.close()
            await transport.aclose()
        assert capture.requests
        # Wire outcome decisions are unary-only in the existing driver contract;
        # streaming termination is observed through lifecycle events/outcome.
        assert not capture.outcomes
        assert all(request.ctx == ctx for request in capture.requests)
        assert all(outcome.ctx == ctx for outcome in capture.outcomes)
        assert all(event.call_id == ctx.call_id for event in capture.events)
        for request in [*capture.requests, *(outcome.request for outcome in capture.outcomes)]:
            assert "authorization" not in {key.lower() for key in request.headers}
        assert "sk-test" not in repr(capture.events)
        return capture

    first, second = await asyncio.gather(consume(0), consume(1))
    assert first.requests[0] is not second.requests[0]
    assert all(route.call_count == 1 for route in routes)


class _Recording(httpx.SyncByteStream, httpx.AsyncByteStream):
    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        for line in self.lines:
            yield (line + "\n\n").encode()

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for line in self.lines:
            yield (line + "\n\n").encode()

    def close(self) -> None:
        self.closed = True

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_explicit_close_releases_recorded_upstream(asynchronous: bool) -> None:
    pair = _load(HTTP / "deepseek_chat_stream_tools.json")
    recording = _Recording(pair["response"]["sse"])
    respx.post(URL).mock(return_value=httpx.Response(
        200, headers=pair["response"]["headers"], stream=recording))
    transport = HttpxTransport(provider="deepseek")
    model = ocai.chat.model("deepseek/deepseek-flash", credentials=ApiKey("sk-test"),
                           catalog=Catalog.of(ocai.deepseek.FRAGMENT), transport=transport)
    try:
        stream: ChatStream | AsyncChatStream
        if asynchronous:
            stream = await model.astream(ChatRequest(messages=[]))
            await anext(stream)
            await anext(stream)
            await stream.aclose()
            await stream.aclose()
        else:
            stream = model.stream(ChatRequest(messages=[]))
            next(stream)
            next(stream)
            stream.close()
            stream.close()
        assert recording.closed
        assert stream.end is None and stream.outcome is not None
        assert stream.outcome.status == "closed"
        assert stream.outcome.usage is None
        assert stream.outcome.report is not None
    finally:
        transport.close()
        await transport.aclose()
