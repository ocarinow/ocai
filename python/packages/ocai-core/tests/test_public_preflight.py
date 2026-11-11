"""WU-27: approved snapshots execute through public APIs and existing governance."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
import respx

import ocai.chat
import ocai.openai
from ocai.chat.facade import StalePreparationError
from ocai.chat.facade import WireChatModel
from ocai.chat.types import ChatConfig
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.convert.catalog import Catalog
from ocai.core.credentials import ApiKey
from ocai.core.errors import AuthError
from ocai.core.result import CallResult
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.runtime.binding import Binding
from ocai.runtime.decisions import Decision
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.interceptors import AsyncNextHandler
from ocai.runtime.interceptors import Call
from ocai.runtime.interceptors import NextHandler
from ocai.runtime.observe import CallFinished
from ocai.runtime.observe import CallStarted
from ocai.runtime.observe import ObserveEvent
from ocai.wire.hosting import Direct
from ocai.wire.http import HttpRequest
from ocai.wire.transport import HttpxTransport

type LoadHttp = Callable[[str], dict[str, Any]]
URL = "https://api.openai.com/v1/chat/completions"


@pytest.mark.parametrize("mode", ["sync", "async", "stream", "astream"])
@respx.mock
async def test_snapshot_survives_input_and_inspection_mutation(
    load_http: LoadHttp, mode: str,
) -> None:
    pair = load_http("openai_chat_completion_stream.json" if "stream" in mode
                     else "openai_chat_completion.json")
    events: list[ObserveEvent] = []

    class Collect:
        def on_event(self, event: ObserveEvent) -> None:
            events.append(event)

    transport = HttpxTransport(provider="openai")
    model = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"),
                            catalog=Catalog.of(ocai.openai.FRAGMENT), transport=transport,
                            observers=[Collect()])
    request = ChatRequest(messages=[Message.user("approved")], config=ChatConfig(temperature=0.4))
    prepared = model.prepare(request, streaming="stream" in mode)
    assert events == []
    inspection = prepared.inspection
    assert inspection.route.node.interface == "chat_completions"
    assert inspection.request_path.edges
    assert inspection.response_path.streaming == ("stream" in mode)
    assert inspection.request_path.conformance_evaluated is False
    assert inspection.coverage_complete is False
    request.messages[:] = [Message.user("changed")]
    assert request.config
    request.config.temperature = 1.9
    inspection.request_report.edges.clear()
    for profile in inspection.profiles:
        profile.features.clear()
    prepared.request.messages.clear()

    def respond(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["messages"] == [{"role": "user", "content": "approved"}]
        assert payload["temperature"] == 0.4
        if "stream" in mode:
            return httpx.Response(200, content=("\n\n".join(pair["response"]["sse"])
                                               + "\n\n").encode())
        return httpx.Response(200, json=pair["response"]["json"])

    route = respx.post(URL).mock(side_effect=respond)
    try:
        if mode == "sync":
            result = prepared.chat()
            assert result.report and result.report.edges
        elif mode == "async":
            result = await prepared.achat()
            assert result.report and result.report.edges
        elif mode == "stream":
            with prepared.stream() as stream:
                list(stream)
        else:
            async with await prepared.astream() as astream:
                async for _ in astream:
                    pass
    finally:
        transport.close()
        await transport.aclose()
    assert route.call_count == 1
    assert isinstance(events[0], CallStarted) and isinstance(events[-1], CallFinished)
    assert prepared.inspection.request_report.edges


async def test_binding_change_requires_revalidation() -> None:
    headers = {"X-Deployment": "approved"}
    transport = HttpxTransport(provider="openai")
    binding = Binding(
        host=Direct("https://api.openai.com"), credentials=ApiKey("sk-test"),
        transport=transport, extra_headers=headers,
    )
    model = WireChatModel(ChatCompletionsCodec(), binding,
                         Catalog.of(ocai.openai.FRAGMENT), model_name="gpt-4o")
    prepared = model.prepare(ChatRequest(messages=[]))
    assert isinstance(binding.extra_headers, dict)
    binding.extra_headers["X-Deployment"] = "changed"
    with respx.mock as router:
        with pytest.raises(StalePreparationError, match="configuration"):
            await prepared.achat()
        assert not router.calls
    await transport.aclose()


async def test_wire_policy_cannot_change_approved_body() -> None:
    class Mutate:
        def on_request(self, request: HttpRequest) -> Decision:
            request.body = b'{"messages":[]}'
            return Proceed()

        def on_outcome(self, outcome: Outcome) -> Decision:
            return Proceed()

    model = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"),
                            catalog=Catalog.of(ocai.openai.FRAGMENT), policies=[Mutate()])
    prepared = model.prepare(ChatRequest(messages=[Message.user("approved")]))
    with respx.mock as router:
        with pytest.raises(StalePreparationError):
            await prepared.achat()
        assert not router.calls


@pytest.mark.parametrize("mutate", [False, True])
async def test_prepared_execution_retains_admission(mutate: bool) -> None:
    class Admission:
        def intercept(self, call: Call, next: NextHandler) -> CallResult[Any]:
            if not mutate:
                raise AuthError("denied")
            call.request.messages.clear()
            return next(call)

        async def aintercept(self, call: Call, next: AsyncNextHandler) -> CallResult[Any]:
            if not mutate:
                raise AuthError("denied")
            call.request.messages.clear()
            return await next(call)

    model = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"),
                            catalog=Catalog.of(ocai.openai.FRAGMENT), interceptors=[Admission()])
    prepared = model.prepare(ChatRequest(messages=[Message.user("approved")]))
    with respx.mock as router:
        with pytest.raises(StalePreparationError if mutate else AuthError):
            await prepared.achat()
        assert not router.calls


def test_undeclared_features_are_not_presented_as_qualified() -> None:
    from dataclasses import replace

    fragment = replace(ocai.openai.FRAGMENT, profiles=())
    model = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"),
                            catalog=Catalog.of(fragment))
    prepared = model.prepare(ChatRequest(messages=[], config=ChatConfig(temperature=0.4)))
    assert prepared.inspection.profiles == ()
    assert prepared.inspection.coverage
    assert all(item.support is None for item in prepared.inspection.coverage)
    assert prepared.inspection.coverage_complete is False


@pytest.mark.parametrize("mode", ["sync", "async", "stream", "astream"])
async def test_header_case_alias_cannot_change_approved_semantics(mode: str) -> None:
    class Mutate:
        def on_request(self, request: HttpRequest) -> Decision:
            assert "Content-Type" in request.headers
            request.headers["content-type"] = "application/changed"
            return Proceed()

        def on_outcome(self, outcome: Outcome) -> Decision:
            return Proceed()

    model = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"),
                            catalog=Catalog.of(ocai.openai.FRAGMENT), policies=[Mutate()])
    prepared = model.prepare(ChatRequest(messages=[]), streaming="stream" in mode)
    with respx.mock as router:
        with pytest.raises(StalePreparationError):
            if mode == "sync":
                prepared.chat()
            elif mode == "async":
                await prepared.achat()
            elif mode == "stream":
                with prepared.stream() as stream:
                    list(stream)
            else:
                async with await prepared.astream() as astream:
                    async for _ in astream:
                        pass
        assert not router.calls
