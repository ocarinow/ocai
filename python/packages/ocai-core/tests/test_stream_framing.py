"""WU-39: wire framing selection remains outside provider conversion semantics."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from collections.abc import Callable
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any

import httpx
import pytest
import respx

import ocai.chat
import ocai.openai
from ocai.chat.facade import StalePreparationError
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import Message
from ocai.chat.types import StreamAccumulator
from ocai.convert import Catalog
from ocai.core import ApiKey
from ocai.core.canonjson import semantic_equal
from ocai.core.errors import DeadlineExceededError
from ocai.core.errors import StreamProtocolError
from ocai.core.errors import TransientError
from ocai.core.ir import is_json_array
from ocai.core.ir import is_json_object
from ocai.core.result import CallContext
from ocai.runtime.decisions import Decision
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.decisions import Retry
from ocai.runtime.observe import ObserveEvent
from ocai.runtime.observe import WireExchanged
from ocai.wire.framing import StreamDecoder
from ocai.wire.framing import StreamFraming
from ocai.wire.framing import sse_framing
from ocai.wire.hosting import Direct
from ocai.wire.hosting import EndpointSpec
from ocai.wire.http import HttpRequest
from ocai.wire.sse import SSEvent
from ocai.wire.transport import HttpxTransport

LoadHttp = Callable[[str], dict[str, Any]]
URL = "https://framing.example.test/v1/chat/completions"


class LengthDecoder:
    """Test-only binary frame parser plus envelope removal, no semantic mapping."""

    def __init__(self, options: dict[str, Any]) -> None:
        self.options = options
        self.buffer = b""
        self.pending: list[Any] = []
        self.finished = 0
        self.closed = 0

    def feed(self, chunk: bytes) -> list[Any]:
        self.buffer += chunk
        events: list[Any] = []
        while len(self.buffer) >= 4:
            length = int.from_bytes(self.buffer[:4], "big")
            if length > 4096:
                raise StreamProtocolError("test frame exceeds its declared size limit")
            if len(self.buffer) < length + 4:
                break
            payload = json.loads(self.buffer[4 : 4 + length])
            self.buffer = self.buffer[4 + length :]
            event = SSEvent(data=payload[self.options["member"]])
            if self.options.get("defer_terminal") and event.data == "[DONE]":
                self.pending.append(event)
            else:
                events.append(event)
        return events

    def finish(self) -> list[Any]:
        self.finished += 1
        if self.buffer:
            raise StreamProtocolError("truncated test framing")
        return self.pending

    def close(self) -> None:
        self.closed += 1
        self.buffer = b""
        if self.options.get("close_error"):
            raise RuntimeError("test decoder close failed")


class Factory:
    """Record independent decoder instances without touching provider SDKs."""

    def __init__(self) -> None:
        self.instances: list[LengthDecoder] = []

    def __call__(self, options: dict[str, Any]) -> StreamDecoder:
        if options.get("build_error"):
            raise RuntimeError("test decoder construction failed")
        decoder = LengthDecoder(options)
        self.instances.append(decoder)
        return decoder


@dataclass(frozen=True)
class FramedHost(Direct):
    """Explicit host selection leaves the inherited wire/body mapping intact."""

    selection: StreamFraming

    def stream_framing(self, spec: EndpointSpec) -> StreamFraming:
        return self.selection


class RecordedBody(httpx.SyncByteStream, httpx.AsyncByteStream):
    """Replay exact recorded byte chunks, with transport cleanup probes."""

    def __init__(self, chunks: list[bytes], mode: str) -> None:
        self.chunks = chunks
        self.mode = mode
        self.closed = 0
        self.waiting = asyncio.Event()

    def __iter__(self) -> Iterator[bytes]:
        for chunk in self.chunks:
            # Split headers and payloads independently of logical frames.
            for index in range(0, len(chunk), 7):
                yield chunk[index : index + 7]
        if self.mode == "failure":
            raise httpx.ReadError("synthetic interrupted recording")

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self:
            yield chunk
            await asyncio.sleep(0)
        if self.mode == "wait":
            self.waiting.set()
            await asyncio.Event().wait()

    def close(self) -> None:
        self.closed += 1

    async def aclose(self) -> None:
        self.closed += 1


def _semantic(value: Any) -> Any:
    if is_json_object(value):
        return {
            key: _semantic(item)
            for key, item in value.items()
            if key not in {"raw", "raw_event", "info"}
        }
    if is_json_array(value):
        return [_semantic(item) for item in value]
    return value


def _chunks(load_http: LoadHttp, binary: bool) -> list[bytes]:
    if binary:
        pair = load_http("openai_chat_framed_stream.json")
        return [bytes.fromhex(value) for value in pair["response"]["chunks_hex"]]
    pair = load_http("custom_host_stream.json")
    return [(event + "\n\n").encode() for event in pair["response"]["sse"]]


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize(
    "mode", ["complete", "close", "unused", "incomplete", "failure", "truncated"]
)
async def test_recorded_framing_preserves_fold_and_ownership(
    load_http: LoadHttp,
    asynchronous: bool,
    binary: bool,
    mode: str,
) -> None:
    factory = Factory()
    host = (
        FramedHost(
            "https://framing.example.test",
            StreamFraming("test-length", factory, {"member": "payload"}),
        )
        if binary
        else Direct("https://framing.example.test")
    )
    chunks = _chunks(load_http, binary)
    if mode in {"incomplete", "failure"}:
        chunks = chunks[:-1]
    if mode == "truncated":
        # Even after the semantic DONE event, framing validation may reject EOF.
        chunks.append(b"\x00" if binary else b"\xc3")
    body = RecordedBody(chunks, mode)
    events: list[ObserveEvent] = []
    requests: list[HttpRequest] = []

    class Collect:
        def on_event(self, event: ObserveEvent) -> None:
            events.append(event)

        def on_request(self, request: HttpRequest) -> Proceed:
            requests.append(request)
            return Proceed()

        def on_outcome(self, outcome: Outcome) -> Proceed:
            requests.append(outcome.request)
            return Proceed()

    collect = Collect()
    transport = HttpxTransport(provider="openai")
    model = ocai.chat.model(
        "openai/vendor/model:fast",
        credentials=ApiKey("sk-framing-test"),
        host=host,
        catalog=Catalog.of(ocai.openai.FRAGMENT),
        transport=transport,
        observers=[collect],
        policies=[collect],
    )
    request = ChatRequest(messages=[Message.user("Hello!")])
    unary_pair = load_http("openai_chat_framed_stream_paired.json")
    try:
        with respx.mock(assert_all_called=False) as router:
            route = router.post(URL).respond(200, stream=body)
            if asynchronous:
                stream = await model.astream(request)
                try:
                    async with stream:
                        if mode == "close":
                            await anext(stream)
                            received = []
                        elif mode == "unused":
                            received = []
                        else:
                            received = [chunk async for chunk in stream]
                except (StreamProtocolError, TransientError):
                    assert mode in {"incomplete", "failure", "truncated"}
                    received = []
                await stream.aclose()
                outcome, end = stream.outcome, stream.end
            else:
                sync_stream = model.stream(request)
                try:
                    with sync_stream:
                        if mode == "close":
                            next(sync_stream)
                            received = []
                        elif mode == "unused":
                            received = []
                        else:
                            received = list(sync_stream)
                except (StreamProtocolError, TransientError):
                    assert mode in {"incomplete", "failure", "truncated"}
                    received = []
                sync_stream.close()
                outcome, end = sync_stream.outcome, sync_stream.end
            assert outcome is not None
            assert (end is not None) == (mode == "complete")
            assert (
                outcome.status
                == {
                    "complete": "completed",
                    "close": "closed",
                    "unused": "closed",
                    "incomplete": "incomplete",
                    "failure": "failed",
                    "truncated": "failed",
                }[mode]
            )
            assert body.closed == route.call_count == (0 if mode == "unused" else 1)
            assert outcome.report is not None
            if mode in {"complete", "incomplete", "failure", "truncated"}:
                assert outcome.usage and outcome.usage.input_tokens == 12
                assert len(outcome.report.edges) == 2
            if mode != "unused":
                sent = route.calls.last.request
                expected = load_http("openai_chat_framed_stream.json")["request"]["json"]
                assert json.loads(sent.content) == expected
                assert sent.headers["authorization"] == "Bearer sk-framing-test"
                assert requests and "sk-framing-test" not in repr(requests) + repr(events)
                assert all("Authorization" not in request.headers for request in requests)
            if binary:
                assert len(factory.instances) == (0 if mode == "unused" else 1)
                for decoder in factory.instances:
                    assert decoder.closed == 1
                    assert decoder.finished == (0 if mode in {"close", "failure"} else 1)
            if mode == "complete":
                route.mock(return_value=httpx.Response(200, json=unary_pair["response"]["json"]))
                result = await model.achat(request)
                assert json.loads(route.calls.last.request.content) == unary_pair["request"]["json"]
                folded = StreamAccumulator.fold(received)
                assert isinstance(folded, ChatResponse)
                assert semantic_equal(
                    _semantic(folded.to_dict()), _semantic(result.value.to_dict())
                )
                assert end and end.report == outcome.report
    finally:
        transport.close()
        await transport.aclose()


@pytest.mark.parametrize("change", ["options", "factory"])
@pytest.mark.parametrize("asynchronous", [False, True])
async def test_changed_framing_invalidates_approval_before_io(
    change: str,
    asynchronous: bool,
) -> None:
    factory = Factory()
    options = {"member": "payload"}
    selection = StreamFraming("test-length", factory, options)
    host = FramedHost("https://framing.example.test", selection)
    transport = HttpxTransport(provider="openai")
    model = ocai.chat.model(
        "openai/vendor/model:fast",
        credentials=ApiKey("sk-test"),
        host=host,
        transport=transport,
        catalog=Catalog.of(ocai.openai.FRAGMENT),
    )
    prepared = model.prepare(ChatRequest(messages=[]), streaming=True)
    # External caller data cannot change selection; effective config changes can.
    options["member"] = "external"
    assert selection.options["member"] == "payload"
    if change == "options":
        assert isinstance(selection.options, dict)
        selection.options["member"] = "changed"
    else:
        # Deliberately simulate a replaced callable on otherwise frozen config.
        object.__setattr__(selection, "factory", Factory())
    try:
        with respx.mock as router:
            with pytest.raises(StalePreparationError):
                if asynchronous:
                    async with await prepared.astream() as stream:
                        await anext(stream)
                else:
                    with prepared.stream() as sync_stream:
                        next(sync_stream)
            assert not router.calls
            assert not factory.instances
    finally:
        transport.close()
        await transport.aclose()


def test_sse_framing_decodes_split_utf8_and_fresh_state() -> None:
    selected = sse_framing()
    first, second = selected.build(), selected.build()
    assert first.feed(b'data: "\xc3') == []
    assert second.feed(b'data: "other"\n\n')[0].data == '"other"'
    assert first.feed(b'\xa9"\n\n')[0].data == '"é"'
    assert first.finish() == second.finish() == []
    first.close()
    second.close()


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("mode", ["build_error", "close_error", "primary_error"])
async def test_decoder_failure_does_not_leak_resources_or_mask_primary_error(
    load_http: LoadHttp,
    asynchronous: bool,
    mode: str,
) -> None:
    factory = Factory()
    options: dict[str, Any] = {"member": "payload"}
    options["build_error" if mode == "build_error" else "close_error"] = True
    host = FramedHost("https://framing.example.test", StreamFraming("test", factory, options))
    chunks = _chunks(load_http, True)
    if mode == "primary_error":
        chunks = chunks[:-1]
    body = RecordedBody(chunks, "failure" if mode == "primary_error" else "complete")
    events: list[ObserveEvent] = []

    class Collect:
        def on_event(self, event: ObserveEvent) -> None:
            events.append(event)

    transport = HttpxTransport(provider="openai")
    model = ocai.chat.model(
        "openai/vendor/model:fast",
        credentials=ApiKey("sk-test"),
        host=host,
        transport=transport,
        catalog=Catalog.of(ocai.openai.FRAGMENT),
        observers=[Collect()],
    )
    try:
        with respx.mock(assert_all_called=False) as router:
            route = router.post(URL).respond(200, stream=body)
            error = TransientError if mode == "primary_error" else RuntimeError
            stream = None
            sync_stream = None
            with pytest.raises(error):
                if asynchronous:
                    stream = await model.astream(ChatRequest(messages=[]))
                    async with stream:
                        async for _ in stream:
                            pass
                else:
                    sync_stream = model.stream(ChatRequest(messages=[]))
                    with sync_stream:
                        list(sync_stream)
            if asynchronous:
                assert stream is not None
                outcome, end = stream.outcome, stream.end
            else:
                assert sync_stream is not None
                outcome, end = sync_stream.outcome, sync_stream.end
            assert outcome and outcome.status == "failed"
            assert end is None
            expected = 0 if mode == "build_error" else 1
            assert route.call_count == body.closed == len(factory.instances) == expected
            assert len([event for event in events if isinstance(event, WireExchanged)]) == expected
            if expected:
                assert factory.instances[0].closed == 1
                assert outcome.usage and outcome.usage.input_tokens == 12
                assert outcome.report and len(outcome.report.edges) == 2
    finally:
        transport.close()
        await transport.aclose()


@pytest.mark.parametrize("mode", ["cancel", "deadline"])
async def test_framed_stream_cancellation_and_pending_read_deadline(
    load_http: LoadHttp,
    mode: str,
) -> None:
    factory = Factory()
    host = FramedHost(
        "https://framing.example.test", StreamFraming("test", factory, {"member": "payload"})
    )
    body = RecordedBody(_chunks(load_http, True)[:-1], "wait")
    transport = HttpxTransport(provider="openai")
    ctx = (
        CallContext(deadline=datetime.now(UTC) + timedelta(seconds=0.2))
        if mode == "deadline"
        else None
    )
    model = ocai.chat.model(
        "openai/vendor/model:fast",
        credentials=ApiKey("sk-test"),
        host=host,
        transport=transport,
        catalog=Catalog.of(ocai.openai.FRAGMENT),
    )
    try:
        with respx.mock as router:
            router.post(URL).respond(200, stream=body)
            stream = await model.astream(ChatRequest(messages=[]), ctx=ctx)

            async def consume() -> None:
                async with stream:
                    async for _ in stream:
                        pass

            task = asyncio.create_task(consume())
            await asyncio.wait_for(body.waiting.wait(), 2)
            if mode == "cancel":
                task.cancel()
            with pytest.raises(
                asyncio.CancelledError if mode == "cancel" else DeadlineExceededError
            ):
                await task
            assert body.closed == factory.instances[0].closed == 1
            assert factory.instances[0].finished == 0
            assert stream.end is None
            assert stream.outcome and stream.outcome.status == (
                "cancelled" if mode == "cancel" else "failed"
            )
            assert stream.outcome.usage and stream.outcome.usage.input_tokens == 12
    finally:
        await transport.aclose()


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_expired_framing_call_never_allocates_decoder_or_sends(asynchronous: bool) -> None:
    factory = Factory()
    host = FramedHost(
        "https://framing.example.test", StreamFraming("test", factory, {"member": "payload"})
    )
    transport = HttpxTransport(provider="openai")
    model = ocai.chat.model(
        "openai/vendor/model:fast",
        credentials=ApiKey("sk-test"),
        host=host,
        transport=transport,
        catalog=Catalog.of(ocai.openai.FRAGMENT),
    )
    prepared = model.prepare(ChatRequest(messages=[]), streaming=True)
    ctx = CallContext(deadline=datetime.now(UTC) - timedelta(seconds=1))
    try:
        with respx.mock as router:
            with pytest.raises(DeadlineExceededError):
                if asynchronous:
                    await prepared.astream(ctx=ctx)
                else:
                    prepared.stream(ctx=ctx)
            assert not router.calls
            assert not factory.instances
    finally:
        transport.close()
        await transport.aclose()


async def test_concurrent_streams_share_selection_but_not_decoder_state(
    load_http: LoadHttp,
) -> None:
    factory = Factory()
    host = FramedHost(
        "https://framing.example.test", StreamFraming("test", factory, {"member": "payload"})
    )
    transport = HttpxTransport(provider="openai")
    bodies: list[RecordedBody] = []
    auth_headers: set[str] = set()
    events: list[ObserveEvent] = []

    class Collect:
        def on_event(self, event: ObserveEvent) -> None:
            events.append(event)

    def response(request: httpx.Request) -> httpx.Response:
        auth_headers.add(request.headers["authorization"])
        body = RecordedBody(_chunks(load_http, True), "complete")
        bodies.append(body)
        return httpx.Response(200, stream=body)

    async def consume(identity: str) -> ChatResponse:
        model = ocai.chat.model(
            "openai/vendor/model:fast",
            credentials=ApiKey(identity),
            host=host,
            transport=transport,
            catalog=Catalog.of(ocai.openai.FRAGMENT),
            observers=[Collect()],
        )
        async with await model.astream(
            ChatRequest(messages=[]), ctx=CallContext(call_id=identity)
        ) as stream:
            return StreamAccumulator.fold([chunk async for chunk in stream])

    try:
        with respx.mock as router:
            route = router.post(URL).mock(side_effect=response)
            first, second = await asyncio.gather(consume("first"), consume("second"))
            assert semantic_equal(_semantic(first.to_dict()), _semantic(second.to_dict()))
            assert len(factory.instances) == 2
            assert factory.instances[0] is not factory.instances[1]
            assert all(decoder.closed == decoder.finished == 1 for decoder in factory.instances)
            assert all(body.closed == 1 for body in bodies)
            assert route.call_count == 2
            assert auth_headers == {
                "Bearer first",
                "Bearer second",
            }
            assert {event.call_id for event in events if isinstance(event, WireExchanged)} == {
                "first",
                "second",
            }
    finally:
        await transport.aclose()


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_finish_tail_and_admission_retry_keep_one_decoder(
    load_http: LoadHttp,
    asynchronous: bool,
) -> None:
    factory = Factory()
    host = FramedHost(
        "https://framing.example.test",
        StreamFraming("test", factory, {"member": "payload", "defer_terminal": True}),
    )
    body = RecordedBody(_chunks(load_http, True), "complete")
    admissions: list[int] = []

    class Admit:
        def on_request(self, request: HttpRequest) -> Decision:
            admissions.append(request.admission)
            assert not factory.instances
            return Retry(after=0) if len(admissions) == 1 else Proceed()

        def on_outcome(self, outcome: Outcome) -> Decision:
            return Proceed()

    transport = HttpxTransport(provider="openai")
    model = ocai.chat.model(
        "openai/vendor/model:fast",
        credentials=ApiKey("sk-test"),
        host=host,
        transport=transport,
        catalog=Catalog.of(ocai.openai.FRAGMENT),
        policies=[Admit()],
    )
    try:
        with respx.mock as router:
            route = router.post(URL).respond(200, stream=body)
            if asynchronous:
                async with await model.astream(ChatRequest(messages=[])) as stream:
                    result = StreamAccumulator.fold([chunk async for chunk in stream])
                    assert stream.end
            else:
                with model.stream(ChatRequest(messages=[])) as sync_stream:
                    result = StreamAccumulator.fold(list(sync_stream))
                    assert sync_stream.end
            assert result.message.text == "Hello! How can I help you today?"
            assert admissions == [0, 1]
            assert len(factory.instances) == body.closed == route.call_count == 1
            assert factory.instances[0].finished == factory.instances[0].closed == 1
    finally:
        transport.close()
        await transport.aclose()


@pytest.mark.parametrize("binary", [False, True])
def test_sync_deadline_rejects_late_framed_bytes_and_closes(
    load_http: LoadHttp,
    binary: bool,
) -> None:
    class SlowBody(RecordedBody):
        def __iter__(self) -> Iterator[bytes]:
            yield self.chunks[0]
            time.sleep(0.25)
            yield from self.chunks[1:]

    factory = Factory()
    host = (
        FramedHost(
            "https://framing.example.test", StreamFraming("test", factory, {"member": "payload"})
        )
        if binary
        else Direct("https://framing.example.test")
    )
    body = SlowBody(_chunks(load_http, binary), "complete")
    with HttpxTransport(provider="openai") as transport:
        model = ocai.chat.model(
            "openai/vendor/model:fast",
            credentials=ApiKey("sk-test"),
            host=host,
            transport=transport,
            catalog=Catalog.of(ocai.openai.FRAGMENT),
        )
        prepared = model.prepare(ChatRequest(messages=[]), streaming=True)
        with respx.mock as router:
            router.post(URL).respond(200, stream=body)
            ctx = CallContext(deadline=datetime.now(UTC) + timedelta(seconds=0.2))
            stream = prepared.stream(ctx=ctx)
            with pytest.raises(DeadlineExceededError), stream:
                list(stream)
            assert body.closed == 1
            assert stream.end is None
            assert stream.outcome and stream.outcome.status == "failed"
            if binary:
                assert factory.instances[0].closed == 1
                assert factory.instances[0].finished == 0
