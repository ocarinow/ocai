"""WU-23: per-call context and whole-call budgets on recorded wire paths."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any

import httpx
import pytest
import respx

import ocai.chat
import ocai.openai
from ocai.chat.protocol import ChatModel
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.convert.catalog import Catalog
from ocai.core.credentials import ApiKey
from ocai.core.errors import DeadlineExceededError
from ocai.core.result import CallContext
from ocai.runtime.deadline import Deadline
from ocai.runtime.decisions import Decision
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.decisions import Retry
from ocai.wire.http import HttpRequest
from ocai.wire.transport import HttpxTransport

type LoadHttp = Callable[[str], dict[str, Any]]
URL = "https://api.openai.com/v1/chat/completions"


class ContextPolicy:
    def __init__(self, *, wait: float | None = None) -> None:
        self.requests: list[HttpRequest] = []
        self.outcomes: list[Outcome] = []
        self.wait = wait

    def on_request(self, request: HttpRequest) -> Decision:
        self.requests.append(request)
        if self.wait is not None:
            return Retry(after=self.wait)
        return Proceed()

    def on_outcome(self, outcome: Outcome) -> Decision:
        self.outcomes.append(outcome)
        return Proceed()


def model(policy: ContextPolicy) -> tuple[ChatModel, HttpxTransport]:
    transport = HttpxTransport(provider="openai")
    return ocai.chat.model(
        "openai/gpt-4o",
        catalog=Catalog.of(ocai.openai.FRAGMENT),
        credentials=ApiKey("sk-test"),
        transport=transport,
        policies=[policy],
    ), transport


async def invoke(facade: ChatModel, ctx: CallContext, mode: str) -> None:
    request = ChatRequest(messages=[Message.user("hello")])
    if mode == "sync":
        facade.chat(request, ctx=ctx)
    elif mode == "async":
        await facade.achat(request, ctx=ctx)
    elif mode == "stream":
        list(facade.stream(request, ctx=ctx))
    else:
        async for _ in await facade.astream(request, ctx=ctx):
            pass


@pytest.mark.parametrize("mode", ["sync", "async", "stream", "astream"])
@respx.mock
async def test_context_is_metadata_only(load_http: LoadHttp, mode: str) -> None:
    pair = load_http(
        "openai_chat_completion_stream.json" if "stream" in mode else "openai_chat_completion.json"
    )
    policy = ContextPolicy()
    facade, transport = model(policy)
    ctx = CallContext(
        tenant="tenant-private",
        principal="principal-private",
        compartment="scope-private",
        tags={"trace": "trace-private"},
        deadline=datetime.now(UTC) + timedelta(seconds=10),
    )

    def respond(request: httpx.Request) -> httpx.Response:
        assert b"private" not in request.content
        assert "private" not in repr(request.headers)
        timeout = request.extensions["timeout"]["read"]
        assert 0 < timeout <= 10
        if "stream" in mode:
            return httpx.Response(
                200, content=("\n\n".join(pair["response"]["sse"]) + "\n\n").encode()
            )
        return httpx.Response(200, json=pair["response"]["json"])

    respx.post(URL).mock(side_effect=respond)
    try:
        await invoke(facade, ctx, mode)
    finally:
        transport.close()
        await transport.aclose()
    assert policy.requests[0].ctx == ctx
    assert policy.requests[0].ctx is not ctx
    if policy.outcomes:
        assert policy.outcomes[0].ctx == ctx
    ctx.tags["trace"] = "changed-after-call"
    assert policy.requests[0].ctx is not None
    assert policy.requests[0].ctx.tags["trace"] == "trace-private"


@pytest.mark.parametrize("mode", ["sync", "async", "stream", "astream"])
@pytest.mark.parametrize("expired", [False, True])
@respx.mock(assert_all_called=False)
async def test_expiration_and_admission_wait_make_zero_calls(
    mode: str,
    expired: bool,
    respx_mock: respx.MockRouter,
) -> None:
    policy = ContextPolicy(wait=None if expired else 60)
    facade, transport = model(policy)
    route = respx_mock.post(URL).respond(200, json={})
    ctx = CallContext(deadline=datetime.now(UTC) + timedelta(seconds=-1 if expired else 10))
    try:
        with pytest.raises(DeadlineExceededError):
            await invoke(facade, ctx, mode)
    finally:
        transport.close()
        await transport.aclose()
    assert route.call_count == 0


@pytest.mark.parametrize("mode", ["sync", "async"])
@respx.mock
async def test_outcome_retry_cannot_extend_budget(load_http: LoadHttp, mode: str) -> None:
    class RetryOutcome(ContextPolicy):
        def on_outcome(self, outcome: Outcome) -> Decision:
            self.outcomes.append(outcome)
            return Retry(after=60)

    policy = RetryOutcome()
    facade, transport = model(policy)
    pair = load_http("openai_chat_completion.json")
    route = respx.post(URL).respond(200, json=pair["response"]["json"])
    try:
        with pytest.raises(DeadlineExceededError):
            await invoke(
                facade, CallContext(deadline=datetime.now(UTC) + timedelta(seconds=10)), mode
            )
    finally:
        transport.close()
        await transport.aclose()
    assert route.call_count == 1
    assert len(policy.outcomes) == 1


def test_deadline_is_monotonic_and_naive_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Deadline(CallContext(deadline=datetime(2030, 1, 1)))
    import time

    now = [100.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    budget = Deadline(CallContext(deadline=datetime.now(UTC) + timedelta(seconds=10)))
    assert budget.remaining() is not None
    now[0] += 11
    with pytest.raises(DeadlineExceededError):
        budget.remaining()


@respx.mock
async def test_concurrent_calls_keep_contexts_and_attempt_indices(load_http: LoadHttp) -> None:
    class DeferOnce(ContextPolicy):
        def on_request(self, request: HttpRequest) -> Decision:
            self.requests.append(request)
            return Retry(after=0) if request.admission == 0 else Proceed()

    policy = DeferOnce()
    facade, transport = model(policy)
    pair = load_http("openai_chat_completion.json")
    route = respx.post(URL).respond(200, json=pair["response"]["json"])
    contexts = [CallContext(tenant=str(i), call_id=f"call-{i}") for i in range(2)]
    try:
        await asyncio.gather(*(invoke(facade, ctx, "async") for ctx in contexts))
    finally:
        await transport.aclose()
    assert route.call_count == 2
    assert sorted(
        outcome.ctx.tenant
        for outcome in policy.outcomes
        if outcome.ctx and outcome.ctx.tenant is not None
    ) == ["0", "1"]
    assert [outcome.attempt for outcome in policy.outcomes] == [0, 0]
    assert all(outcome.request.admission == 1 for outcome in policy.outcomes)


@pytest.mark.parametrize("mode", ["sync", "async"])
@respx.mock
async def test_late_response_is_rejected_and_async_io_cancelled(
    load_http: LoadHttp,
    mode: str,
) -> None:
    import time

    policy = ContextPolicy()
    facade, transport = model(policy)
    pair = load_http("openai_chat_completion.json")
    entered: list[bool] = []
    exited: list[bool] = []

    def slow_sync(request: httpx.Request) -> httpx.Response:
        entered.append(True)
        time.sleep(0.3)
        exited.append(True)
        return httpx.Response(200, json=pair["response"]["json"])

    async def slow_async(request: httpx.Request) -> httpx.Response:
        entered.append(True)
        try:
            await asyncio.sleep(10)
        finally:
            exited.append(True)
        return httpx.Response(200, json=pair["response"]["json"])

    respx.post(URL).mock(side_effect=slow_sync if mode == "sync" else slow_async)
    try:
        with pytest.raises(DeadlineExceededError):
            await invoke(
                facade, CallContext(deadline=datetime.now(UTC) + timedelta(seconds=0.2)), mode
            )
    finally:
        transport.close()
        await transport.aclose()
    assert entered == exited == [True]
    assert isinstance(policy.outcomes[0].error, DeadlineExceededError)
