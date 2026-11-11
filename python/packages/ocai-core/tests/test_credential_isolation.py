"""WU-22: authentication never mutates a request retained by a hook."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
import pytest
import respx

import ocai.openai
from ocai.chat.facade import WireChatModel
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.convert.catalog import Catalog
from ocai.core.credentials import ApiKey
from ocai.core.errors import OcaiError
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.runtime.binding import Binding
from ocai.runtime.decisions import Decision
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.decisions import Retry
from ocai.wire.hosting import Direct
from ocai.wire.http import HttpRequest
from ocai.wire.transport import HttpxTransport

type LoadHttp = Callable[[str], dict[str, Any]]
URL = "https://api.openai.com/v1/chat/completions"


class Retain:
    """Retain the actual objects, not redacted snapshots made by the test."""

    def __init__(self, retry: bool = False) -> None:
        self.requests: list[HttpRequest] = []
        self.outcomes: list[Outcome] = []
        self.retry = retry

    def on_request(self, request: HttpRequest) -> Decision:
        self.requests.append(request)
        request.headers["X-Allowed"] = "hook"
        return Proceed()

    def on_outcome(self, outcome: Outcome) -> Decision:
        self.outcomes.append(outcome)
        if self.retry and outcome.attempt == 0:
            return Retry(after=0)
        return Proceed()

    def assert_safe(self) -> None:
        assert self.requests
        for request in self.requests:
            assert "Authorization" not in request.headers
            assert "sk-isolation" not in repr(request)
        for outcome in self.outcomes:
            assert any(outcome.request is request for request in self.requests)
            assert "sk-isolation" not in repr(outcome)


def model(policy: Retain, key: str = "sk-isolation") -> tuple[WireChatModel, HttpxTransport]:
    transport = HttpxTransport(provider="openai")
    facade = WireChatModel(
        ChatCompletionsCodec(),
        Binding(
            host=Direct("https://api.openai.com"), credentials=ApiKey(key), transport=transport
        ),
        Catalog.of(ocai.openai.FRAGMENT),
        model_name="gpt-4o",
        policies=[policy],
    )
    return facade, transport


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("failure", ["none", "provider", "transport"])
@respx.mock
async def test_retained_requests_stay_safe(
    load_http: LoadHttp,
    asynchronous: bool,
    streaming: bool,
    failure: str,
) -> None:
    pair = load_http(
        "openai_chat_completion_stream.json" if streaming else "openai_chat_completion.json"
    )
    policy = Retain()
    facade, transport = model(policy)
    sent: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        assert request.headers["Authorization"] == "Bearer sk-isolation"
        assert request.headers["X-Allowed"] == "hook"
        policy.assert_safe()  # while the authenticated request is still in flight
        if failure == "transport":
            raise httpx.ConnectError("synthetic connection failure", request=request)
        if failure == "provider":
            error = load_http("openai_chat_completion_auth_error.json")
            return httpx.Response(error["response"]["status"], json=error["response"]["json"])
        if streaming:
            return httpx.Response(
                200, content=("\n\n".join(pair["response"]["sse"]) + "\n\n").encode()
            )
        return httpx.Response(200, json=pair["response"]["json"])

    respx.post(URL).mock(side_effect=respond)
    request = ChatRequest(messages=[Message.user("hello")])
    try:
        if asynchronous:
            if streaming:
                stream = await facade.astream(request)
                async for _ in stream:
                    pass
            else:
                await facade.achat(request)
        elif streaming:
            list(facade.stream(request))
        else:
            facade.chat(request)
        assert failure == "none"
    except OcaiError:
        assert failure != "none"
    finally:
        transport.close()
        await transport.aclose()
    assert len(sent) == 1
    policy.assert_safe()
    if not streaming:
        assert len(policy.outcomes) == 1
        assert (policy.outcomes[0].error is not None) == (failure != "none")


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_retry_and_concurrent_credentials_do_not_cross(
    load_http: LoadHttp,
    asynchronous: bool,
) -> None:
    pair = load_http("openai_chat_completion.json")
    policies = [Retain(retry=True), Retain(retry=True)]
    models = [model(policy, f"sk-isolation-{i}") for i, policy in enumerate(policies)]
    keys: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        keys.append(request.headers["Authorization"])
        for policy in policies:
            if policy.requests:
                policy.assert_safe()
        return httpx.Response(200, json=pair["response"]["json"])

    respx.post(URL).mock(side_effect=respond)
    request = ChatRequest(messages=[Message.user("hello")])
    try:
        if asynchronous:
            await asyncio.gather(*(facade.achat(request) for facade, _ in models))
        else:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(facade.chat, request) for facade, _ in models]
                for future in futures:
                    future.result()
    finally:
        for _, transport in models:
            transport.close()
            await transport.aclose()
    assert sorted(keys) == ["Bearer sk-isolation-0"] * 2 + ["Bearer sk-isolation-1"] * 2
    for policy in policies:
        policy.assert_safe()
        assert len(policy.requests) == len(policy.outcomes) == 2
        assert policy.requests[0].headers is not policy.requests[1].headers
