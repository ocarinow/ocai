"""WU-28: conversion rejection preserves evidence and prevents forbidden I/O."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
import respx

import ocai.anthropic
import ocai.chat
import ocai.openai
from ocai.chat.types import ChatConfig
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.convert.catalog import Catalog
from ocai.core.credentials import ApiKey
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import FidelityPolicy
from ocai.core.fidelity import FidelityPolicyError
from ocai.core.fidelity import FieldLoss

type LoadHttp = Callable[[str], dict[str, Any]]
URL = "https://api.openai.com/v1/chat/completions"


@pytest.mark.parametrize("mode", ["sync", "async", "stream", "astream"])
@pytest.mark.parametrize("semantic", [False, True])
async def test_forbidden_request_never_reaches_transport(mode: str, semantic: bool) -> None:
    policy = FidelityPolicy(
        forbidden_dispositions=frozenset({Disposition.APPROXIMATED}),
        forbidden_shifts=frozenset({"relocation"}),
    )
    model = ocai.chat.model(
        "anthropic/claude-sonnet-4" if semantic else "openai/gpt-4o",
        credentials=ApiKey("sk-test"),
        catalog=Catalog.of(ocai.anthropic.FRAGMENT if semantic else ocai.openai.FRAGMENT),
        conversion_policy=policy,
    )
    request = ChatRequest(
        messages=[Message.system("Be concise"), Message.user("Hello!")]
        if semantic
        else [Message.user("Hello!")],
        config=None if semantic else ChatConfig(temperature=4.0),
    )
    prepared = model.prepare(request, streaming="stream" in mode)
    if semantic:
        assert prepared.inspection.request_report.lossless
    with respx.mock as router:
        with pytest.raises(FidelityPolicyError) as error:
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
    assert error.value.phase == "request"
    assert error.value.report.edges
    assert not error.value.partial


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_response_rejection_retains_usage(load_http: LoadHttp, asynchronous: bool) -> None:
    pair = load_http("openai_chat_completion_tool_call.json")
    route = respx.post(URL).respond(200, json=pair["response"]["json"])
    model = ocai.chat.model(
        "openai/gpt-4o",
        credentials=ApiKey("sk-test"),
        catalog=Catalog.of(ocai.openai.FRAGMENT),
        conversion_policy=FidelityPolicy(
            allow_loss=lambda loss: not loss.path.startswith("choices")
        ),
    )
    request = ChatRequest(messages=[Message.user("Hello!")])
    with pytest.raises(FidelityPolicyError) as error:
        if asynchronous:
            await model.achat(request)
        else:
            model.chat(request)
    assert route.call_count == 1
    assert error.value.phase == "response"
    assert error.value.usage and error.value.usage.total_tokens > 0
    assert len(error.value.report.edges) == 2
    assert error.value.raw is None
    assert not error.value.partial


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_late_stream_policy_failure_is_partial(
    load_http: LoadHttp,
    asynchronous: bool,
) -> None:
    pair = load_http("openai_chat_completion_stream_extra_choice.json")
    route = respx.post(URL).respond(
        200, content=("\n\n".join(pair["response"]["sse"]) + "\n\n").encode()
    )
    model = ocai.chat.model(
        "openai/gpt-4o",
        credentials=ApiKey("sk-test"),
        catalog=Catalog.of(ocai.openai.FRAGMENT),
        conversion_policy=FidelityPolicy(forbidden_dispositions=frozenset({Disposition.DROPPED})),
    )
    request = ChatRequest(messages=[Message.user("Hello!")])
    delivered = 0
    if asynchronous:
        stream = await model.astream(request)
        with pytest.raises(FidelityPolicyError) as error:
            async with stream:
                async for _ in stream:
                    delivered += 1
    else:
        stream = model.stream(request)
        with pytest.raises(FidelityPolicyError) as error:
            with stream:
                for _ in stream:
                    delivered += 1
    assert route.call_count == 1
    assert delivered > 0 and error.value.delivered_events == delivered
    assert error.value.partial and error.value.phase == "response"
    assert stream.end is None
    assert stream.outcome and stream.outcome.status == "failed"
    assert stream.outcome.usage and stream.outcome.usage.total_tokens == 21
    assert stream.outcome.report and len(stream.outcome.report.edges) == 2


async def test_raising_policy_fails_closed() -> None:
    def unavailable(loss: FieldLoss) -> bool:
        raise RuntimeError("policy unavailable")

    model = ocai.chat.model(
        "openai/gpt-4o",
        credentials=ApiKey("sk-test"),
        catalog=Catalog.of(ocai.openai.FRAGMENT),
        conversion_policy=FidelityPolicy(allow_loss=unavailable),
    )
    with respx.mock as router:
        with pytest.raises(FidelityPolicyError):
            await model.achat(ChatRequest(messages=[], config=ChatConfig(temperature=4.0)))
        assert not router.calls
