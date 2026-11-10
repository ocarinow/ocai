"""WU-25: one governance chain for local/remote unary and streaming calls."""

from __future__ import annotations

from collections.abc import AsyncIterator
from collections.abc import Iterator
from typing import Any

import pytest
import respx

import ocai.chat
import ocai.openai
from ocai.chat.facade import InterceptedChatModel
from ocai.chat.protocol import ChatModel
from ocai.chat.types import AsyncChatStream
from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import ChatStream
from ocai.chat.types import Message
from ocai.chat.types import StreamEnd
from ocai.chat.types.stream import ChunkType
from ocai.convert.catalog import Catalog
from ocai.core.credentials import ApiKey
from ocai.core.errors import AuthError
from ocai.core.result import CallContext
from ocai.core.result import CallResult
from ocai.core.result import StreamOutcome
from ocai.runtime.binding import CompositionError
from ocai.runtime.interceptors import AsyncNextHandler
from ocai.runtime.interceptors import AsyncNextStreamHandler
from ocai.runtime.interceptors import AsyncStream
from ocai.runtime.interceptors import Call
from ocai.runtime.interceptors import NextHandler
from ocai.runtime.interceptors import NextStreamHandler
from ocai.runtime.interceptors import SyncStream


class Local:
    """An in-process capability with no wire dependency or buffering."""

    def __init__(self) -> None:
        self.calls = 0
        self.pulls = 0

    @property
    def details(self) -> dict[str, Any]:
        return {"provider": "local"}

    def chat(self, request: ChatRequest,
             *, ctx: CallContext | None = None) -> CallResult[ChatResponse]:
        self.calls += 1
        return CallResult(ChatResponse(message=Message.model("local")))

    async def achat(self, request: ChatRequest,
                    *, ctx: CallContext | None = None) -> CallResult[ChatResponse]:
        return self.chat(request, ctx=ctx)

    def stream(self, request: ChatRequest, *, ctx: CallContext | None = None) -> ChatStream:
        self.calls += 1

        def chunks() -> Iterator[ChatChunk]:
            self.pulls += 1
            yield ChatChunk(type=ChunkType.STREAM_START)
            self.pulls += 1
            yield ChatChunk(type=ChunkType.STREAM_STOP, end=StreamEnd())

        return ChatStream(chunks())

    async def astream(self, request: ChatRequest,
                      *, ctx: CallContext | None = None) -> AsyncChatStream:
        self.calls += 1

        async def chunks() -> AsyncIterator[ChatChunk]:
            self.pulls += 1
            yield ChatChunk(type=ChunkType.STREAM_START)
            self.pulls += 1
            yield ChatChunk(type=ChunkType.STREAM_STOP, end=StreamEnd())

        return AsyncChatStream(chunks())


class Govern:
    def __init__(self, deny: bool = False) -> None:
        self.deny = deny
        self.contexts: list[CallContext | None] = []
        self.outcomes: list[StreamOutcome] = []

    def admit(self, call: Call) -> None:
        self.contexts.append(call.ctx)
        if self.deny:
            raise AuthError("admission rejected")

    def intercept(self, call: Call, next: NextHandler) -> CallResult[Any]:
        self.admit(call)
        return next(call)

    async def aintercept(self, call: Call, next: AsyncNextHandler) -> CallResult[Any]:
        self.admit(call)
        return await next(call)

    def intercept_stream(self, call: Call, next: NextStreamHandler) -> SyncStream:
        self.admit(call)
        inner = next(call)
        wrapped = ChatStream(inner, report=lambda: inner.outcome.report if inner.outcome else None)
        wrapped.on_termination(self.outcomes.append)
        return wrapped

    async def aintercept_stream(self, call: Call, next: AsyncNextStreamHandler) -> AsyncStream:
        self.admit(call)
        inner = await next(call)
        wrapped = AsyncChatStream(inner,
                                  report=lambda: inner.outcome.report if inner.outcome else None)
        wrapped.on_termination(self.outcomes.append)
        return wrapped


async def invoke(model: ChatModel, mode: str, ctx: CallContext) -> None:
    request = ChatRequest(messages=[Message.user("hello")])
    if mode == "sync":
        model.chat(request, ctx=ctx)
    elif mode == "async":
        await model.achat(request, ctx=ctx)
    elif mode == "stream":
        with model.stream(request, ctx=ctx) as stream:
            list(stream)
    else:
        async with await model.astream(request, ctx=ctx) as astream:
            async for _ in astream:
                pass


@pytest.mark.parametrize("remote", [False, True])
@pytest.mark.parametrize("mode", ["sync", "async", "stream", "astream"])
async def test_denial_prevents_all_inner_execution(remote: bool, mode: str) -> None:
    policy = Govern(deny=True)
    local = Local()
    model = (ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"),
                            catalog=Catalog.of(ocai.openai.FRAGMENT), interceptors=[policy])
             if remote else InterceptedChatModel(local, [policy]))
    ctx = CallContext(tenant="tenant", compartment="compartment")
    with respx.mock as router:
        with pytest.raises(AuthError, match="admission rejected"):
            await invoke(model, mode, ctx)
        assert not router.calls
    assert local.calls == 0
    assert policy.contexts == [ctx]


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_wrapping_is_lazy_and_accounts_for_early_close(asynchronous: bool) -> None:
    policies = [Govern(), Govern()]
    local = Local()
    model = InterceptedChatModel(local, policies)
    ctx = CallContext(tenant="tenant")
    request = ChatRequest(messages=[])
    if asynchronous:
        stream = await model.astream(request, ctx=ctx)
        assert local.pulls == 0
        await anext(stream)
        await stream.aclose()
    else:
        sync_stream = model.stream(request, ctx=ctx)
        assert local.pulls == 0
        next(sync_stream)
        sync_stream.close()
    assert local.calls == local.pulls == 1
    for policy in policies:
        assert policy.contexts == [ctx]
        assert len(policy.outcomes) == 1
        assert policy.outcomes[0].status == "closed"


@pytest.mark.parametrize("mode", ["stream", "astream"])
async def test_unary_only_interceptor_cannot_be_bypassed(mode: str) -> None:
    class UnaryOnly:
        def intercept(self, call: Call, next: NextHandler) -> CallResult[Any]:
            raise AuthError("unary denial")

        async def aintercept(self, call: Call, next: AsyncNextHandler) -> CallResult[Any]:
            raise AuthError("unary denial")

    local = Local()
    with pytest.raises(CompositionError, match="cannot bypass"):
        await invoke(InterceptedChatModel(local, [UnaryOnly()]), mode, CallContext())
    assert local.calls == 0


@pytest.mark.parametrize("mode", ["stream", "astream"])
async def test_stream_continuations_cannot_restart_generation(mode: str) -> None:
    class Restart(Govern):
        def intercept_stream(self, call: Call, next: NextStreamHandler) -> SyncStream:
            next(call)
            return next(call)

        async def aintercept_stream(self, call: Call, next: AsyncNextStreamHandler) -> AsyncStream:
            await next(call)
            return await next(call)

    local = Local()
    with pytest.raises(RuntimeError, match="single-use"):
        await invoke(InterceptedChatModel(local, [Restart()]), mode, CallContext())
    assert local.calls == 1
    assert local.pulls == 0
