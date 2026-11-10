"""WU-24: stream ownership closes the actual recorded HTTP stream."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from collections.abc import Callable
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
import respx

import ocai.chat
import ocai.openai
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.chat.types import StreamOutcome
from ocai.convert.catalog import Catalog
from ocai.core.credentials import ApiKey
from ocai.core.errors import StreamProtocolError
from ocai.core.errors import TransientError
from ocai.wire.transport import HttpxTransport

type LoadHttp = Callable[[str], dict[str, Any]]
URL = "https://api.openai.com/v1/chat/completions"


class RecordedBody(httpx.SyncByteStream, httpx.AsyncByteStream):
    """Replay recorded bytes with explicit resource and interruption probes."""

    def __init__(self, events: list[str], mode: str) -> None:
        self.events = events
        self.mode = mode
        self.closed = 0
        self.waiting = asyncio.Event()

    def __iter__(self) -> Iterator[bytes]:
        for event in self.events:
            yield (event + "\n\n").encode()
        if self.mode == "failure":
            raise httpx.ReadError("synthetic interrupted recording")

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for event in self.events:
            yield (event + "\n\n").encode()
        if self.mode == "failure":
            raise httpx.ReadError("synthetic interrupted recording")
        if self.mode == "cancel":
            self.waiting.set()
            await asyncio.sleep(60)

    def close(self) -> None:
        self.closed += 1

    async def aclose(self) -> None:
        self.closed += 1


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("mode", ["complete", "close", "incomplete", "failure", "unused"])
async def test_stream_owns_upstream_and_retains_evidence(
    load_http: LoadHttp, asynchronous: bool, mode: str,
) -> None:
    pair = load_http("openai_chat_completion_stream.json")
    events = pair["response"]["sse"]
    if mode in ("failure", "incomplete"):
        events = events[:-1]  # truncate the recording before its explicit [DONE]
    body = RecordedBody(events, mode)
    transport = HttpxTransport(provider="openai")
    facade = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"),
                             catalog=Catalog.of(ocai.openai.FRAGMENT), transport=transport)
    outcomes: list[StreamOutcome] = []
    request = ChatRequest(messages=[Message.user("Hello!")])
    with respx.mock(assert_all_called=False) as router:
        route = router.post(URL).respond(200, stream=body)
        if asynchronous:
            stream = await facade.astream(request)
            stream.on_termination(outcomes.append)
            try:
                async with stream:
                    if mode == "close":
                        await anext(stream)
                    elif mode != "unused":
                        async for _ in stream:
                            pass
            except (StreamProtocolError, TransientError):
                assert mode in ("failure", "incomplete")
            await stream.aclose()
            outcome, end = stream.outcome, stream.end
        else:
            sync_stream = facade.stream(request)
            sync_stream.on_termination(outcomes.append)
            try:
                with sync_stream:
                    if mode == "close":
                        next(sync_stream)
                    elif mode != "unused":
                        list(sync_stream)
            except (StreamProtocolError, TransientError):
                assert mode in ("failure", "incomplete")
            sync_stream.close()
            outcome, end = sync_stream.outcome, sync_stream.end
        assert outcome is not None
        assert len(outcomes) == 1
        assert outcome.status == {"complete": "completed", "close": "closed",
                                  "unused": "closed", "incomplete": "incomplete",
                                  "failure": "failed"}[mode]
        assert (end is not None) == (mode == "complete")
        assert body.closed == route.call_count == (0 if mode == "unused" else 1)
        assert outcome.report is not None
        assert len(outcome.report.edges) == (1 if mode == "unused" else 2)
        if mode in ("complete", "failure", "incomplete"):
            assert outcome.usage is not None
            assert outcome.usage.input_tokens == 12
        else:
            assert outcome.usage is None
    transport.close()
    await transport.aclose()


@respx.mock
async def test_cancellation_closes_http_stream_once(load_http: LoadHttp) -> None:
    pair = load_http("openai_chat_completion_stream.json")
    body = RecordedBody(pair["response"]["sse"][:-1], "cancel")
    transport = HttpxTransport(provider="openai")
    facade = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"),
                             catalog=Catalog.of(ocai.openai.FRAGMENT), transport=transport)
    respx.post(URL).respond(200, stream=body)
    stream = await facade.astream(ChatRequest(messages=[Message.user("Hello!")]))
    outcomes: list[StreamOutcome] = []
    stream.on_termination(outcomes.append)

    async def consume() -> None:
        async with stream:
            async for _ in stream:
                pass

    task = asyncio.create_task(consume())
    await asyncio.wait_for(body.waiting.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await stream.aclose()
    await transport.aclose()
    assert body.closed == 1
    assert len(outcomes) == 1
    assert outcomes[0].status == "cancelled"
    assert stream.end is None
    assert outcomes[0].usage is not None
    assert outcomes[0].report is not None
    assert len(outcomes[0].report.edges) == 2
