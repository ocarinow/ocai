"""WU-26: correlated metadata events around real recorded-wire execution."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import httpx
import pytest
import respx

import ocai.chat
import ocai.openai
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.convert.catalog import Catalog
from ocai.core.credentials import ApiKey
from ocai.core.errors import AuthError
from ocai.core.result import CallContext
from ocai.runtime.decisions import Decision
from ocai.runtime.decisions import Fail
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.decisions import Retry
from ocai.runtime.observe import CallFinished
from ocai.runtime.observe import CallStarted
from ocai.runtime.observe import ObserveEvent
from ocai.runtime.observe import WireExchanged
from ocai.runtime.observe import WireStarted
from ocai.wire.http import HttpRequest
from ocai.wire.transport import HttpxTransport

type LoadHttp = Callable[[str], dict[str, Any]]
URL = "https://api.openai.com/v1/chat/completions"


class Collect:
    def __init__(self) -> None:
        self.events: list[ObserveEvent] = []

    def on_event(self, event: ObserveEvent) -> None:
        self.events.append(event)


class Broken:
    def on_event(self, event: ObserveEvent) -> None:
        if isinstance(event, CallFinished) and event.report:
            event.report.edges.clear()
        raise asyncio.CancelledError("observer failure must not cancel application")


class Admission:
    def __init__(self, deny: bool = False) -> None:
        self.deny = deny
        self.contexts: list[CallContext | None] = []

    def on_request(self, request: HttpRequest) -> Decision:
        self.contexts.append(request.ctx)
        if self.deny:
            return Fail(AuthError("admission rejected"))
        if request.admission < 2:
            return Retry(after=0)
        return Proceed()

    def on_outcome(self, outcome: Outcome) -> Decision:
        self.contexts.append(outcome.ctx)
        return Proceed()


@pytest.mark.parametrize("mode", ["sync", "async", "stream", "astream"])
@pytest.mark.parametrize("deny", [False, True])
async def test_invocations_attempts_and_observer_isolation(
    load_http: LoadHttp,
    mode: str,
    deny: bool,
) -> None:
    pair = load_http(
        "openai_chat_completion_stream.json" if "stream" in mode else "openai_chat_completion.json"
    )
    collector, policy = Collect(), Admission(deny)
    transport = HttpxTransport(provider="openai")
    model = ocai.chat.model(
        "openai/gpt-4o",
        credentials=ApiKey("sk-observation"),
        catalog=Catalog.of(ocai.openai.FRAGMENT),
        transport=transport,
        policies=[policy],
        observers=[Broken(), collector],
    )
    ctx = CallContext(
        call_id="logical-call",
        parent_id="parent-call",
        correlation_id="trace",
        tenant="tenant",
        tags={"private": "private-tag"},
        extensions={"private": "private-context"},
    )
    request = ChatRequest(messages=[Message.user("payload-private")])
    with respx.mock(assert_all_called=False) as router:
        route = router.post(URL).mock(
            return_value=(
                httpx.Response(
                    200, content=("\n\n".join(pair["response"]["sse"]) + "\n\n").encode()
                )
                if "stream" in mode
                else httpx.Response(200, json=pair["response"]["json"])
            )
        )
        try:
            if mode == "sync":
                result = model.chat(request, ctx=ctx)
                assert result.report and result.report.edges
            elif mode == "async":
                result = await model.achat(request, ctx=ctx)
                assert result.report and result.report.edges
            elif mode == "stream":
                with model.stream(request, ctx=ctx) as stream:
                    list(stream)
                assert stream.end and stream.end.report and stream.end.report.edges
            else:
                async with await model.astream(request, ctx=ctx) as astream:
                    async for _ in astream:
                        pass
                assert astream.end and astream.end.report and astream.end.report.edges
            assert not deny
        except AuthError:
            assert deny
        assert route.call_count == (0 if deny else 1)
    transport.close()
    await transport.aclose()
    events = collector.events
    assert [type(event) for event in events] == (
        [CallStarted, CallFinished]
        if deny
        else [CallStarted, WireStarted, WireExchanged, CallFinished]
    )
    assert {event.call_id for event in events} == {"logical-call"}
    start, finish = events[0], events[-1]
    assert isinstance(start, CallStarted) and start.ctx
    assert start.ctx.parent_id == "parent-call"
    assert start.ctx.correlation_id == "trace"
    assert start.ctx.tags == start.ctx.extensions == {}
    assert isinstance(finish, CallFinished)
    assert finish.status == ("rejected" if deny else "completed")
    if not deny:
        assert finish.report and finish.report.edges
        assert finish.usage is not None
        attempt = events[1]
        assert isinstance(attempt, WireStarted) and attempt.attempt == 0
    assert all(context == ctx for context in policy.contexts)
    for marker in [
        "sk-observation",
        "payload-private",
        "private-tag",
        "private-context",
        "I am an AI assistant",
    ]:
        assert marker not in repr(events)


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_unconsumed_stream_has_no_attempt_and_one_close(asynchronous: bool) -> None:
    collector = Collect()
    model = ocai.chat.model(
        "openai/gpt-4o",
        credentials=ApiKey("sk-test"),
        catalog=Catalog.of(ocai.openai.FRAGMENT),
        observers=[collector],
    )
    with respx.mock as router:
        if asynchronous:
            stream = await model.astream(ChatRequest(messages=[]))
            assert len(collector.events) == 1
            await stream.aclose()
            await stream.aclose()
        else:
            sync_stream = model.stream(ChatRequest(messages=[]))
            assert len(collector.events) == 1
            sync_stream.close()
            sync_stream.close()
        assert not router.calls
    assert [type(event) for event in collector.events] == [CallStarted, CallFinished]
    finish = collector.events[-1]
    assert isinstance(finish, CallFinished) and finish.status == "closed"
    assert finish.usage is None


@respx.mock
async def test_concurrent_streams_keep_correlations(load_http: LoadHttp) -> None:
    pair = load_http("openai_chat_completion_stream.json")
    respx.post(URL).respond(200, content=("\n\n".join(pair["response"]["sse"]) + "\n\n").encode())
    collector = Collect()
    transport = HttpxTransport(provider="openai")
    model = ocai.chat.model(
        "openai/gpt-4o",
        credentials=ApiKey("sk-test"),
        catalog=Catalog.of(ocai.openai.FRAGMENT),
        observers=[collector],
        transport=transport,
    )

    async def consume(identifier: str) -> None:
        async with await model.astream(
            ChatRequest(messages=[]), ctx=CallContext(call_id=identifier)
        ) as stream:
            async for _ in stream:
                await asyncio.sleep(0)

    await asyncio.gather(consume("first"), consume("second"))
    await transport.aclose()
    for identifier in ["first", "second"]:
        events = [event for event in collector.events if event.call_id == identifier]
        assert [type(event) for event in events] == [
            CallStarted,
            WireStarted,
            WireExchanged,
            CallFinished,
        ]


@pytest.mark.parametrize("failure", ["provider", "transport", "retry"])
@respx.mock
async def test_physical_failures_and_retries_are_correlated(
    load_http: LoadHttp,
    failure: str,
) -> None:
    from ocai.core.errors import OcaiError
    from ocai.wire.policies import RetryPolicy

    collector = Collect()
    transport = HttpxTransport(provider="openai")
    model = ocai.chat.model(
        "openai/gpt-4o",
        credentials=ApiKey("sk-test"),
        catalog=Catalog.of(ocai.openai.FRAGMENT),
        observers=[collector],
        policies=[RetryPolicy(attempts=2, base_delay=0)],
        transport=transport,
    )
    pair = load_http("openai_chat_completion.json")
    errors = load_http("openai_chat_completion_auth_error.json")
    attempts: list[bool] = []

    def respond(request: httpx.Request) -> httpx.Response:
        attempts.append(True)
        if failure == "provider":
            return httpx.Response(401, json=errors["response"]["json"])
        if failure == "transport" or len(attempts) == 1:
            raise httpx.ConnectError("payload-private", request=request)
        return httpx.Response(200, json=pair["response"]["json"])

    respx.post(URL).mock(side_effect=respond)
    try:
        await model.achat(ChatRequest(messages=[]))
        assert failure == "retry"
    except OcaiError:
        assert failure != "retry"
    finally:
        await transport.aclose()
    exchanges = [event for event in collector.events if isinstance(event, WireExchanged)]
    assert [event.attempt for event in exchanges] == list(range(len(attempts)))
    assert len({event.call_id for event in collector.events}) == 1
    assert sum(isinstance(event, CallFinished) for event in collector.events) == 1
    assert "payload-private" not in repr(collector.events)
    finish = collector.events[-1]
    assert isinstance(finish, CallFinished)
    assert finish.status == ("completed" if failure == "retry" else "failed")
