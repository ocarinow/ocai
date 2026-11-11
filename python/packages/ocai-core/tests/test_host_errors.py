"""Provider-neutral error mapping over recorded host outcomes, without SDKs."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

import ocai.openai
from ocai.chat.facade import StalePreparationError
from ocai.chat.facade import WireChatModel
from ocai.chat.types import AsyncChatStream
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatStream
from ocai.chat.types import Message
from ocai.convert import Catalog
from ocai.core.credentials import ApiKey
from ocai.core.errors import ContextLengthError
from ocai.core.errors import OcaiError
from ocai.core.errors import RateLimitError
from ocai.core.result import CallContext
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.runtime.binding import Binding
from ocai.runtime.decisions import Decision
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.decisions import Retry
from ocai.runtime.observe import ObserveEvent
from ocai.runtime.observe import WireExchanged
from ocai.wire import HostErrorMapper
from ocai.wire.hosting import Direct
from ocai.wire.hosting import EndpointSpec
from ocai.wire.http import HttpRequest
from ocai.wire.transport import HttpxTransport

HTTP = Path(__file__).parent / "http"
REQUEST = ChatRequest(messages=[Message.user("Hello!")])


def _load(name: str, streaming: bool = False) -> dict[str, Any]:
    suffix = "_stream" if streaming else ""
    return json.loads((HTTP / f"host_error_{name}{suffix}.json").read_text())


def _native(error: OcaiError, options: dict[str, Any]) -> OcaiError | None:
    assert "sk-private" not in repr((error.__dict__, options))
    headers = error.response_headers or {}
    code = headers.get("x-amzn-errortype")
    return RateLimitError("host throttle", code=code) if code == options["code"] else None


def _gateway(error: OcaiError, options: dict[str, Any]) -> OcaiError | None:
    headers = error.response_headers or {}
    code = headers.get("x-service-failure")
    if code == options["code"]:
        return RateLimitError("gateway quota", code=code,
                              retry_after=float(headers["retry-after-ms"]) / 1000)
    return None


@dataclass(frozen=True)
class MappedHost(Direct):
    mapping: HostErrorMapper

    def error_mapper(self, spec: EndpointSpec) -> HostErrorMapper:
        return self.mapping


class RecordingBody(httpx.SyncByteStream, httpx.AsyncByteStream):
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        yield self.content

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.content

    def close(self) -> None:
        self.closed = True

    async def aclose(self) -> None:
        self.closed = True


class Record:
    def __init__(self, retry: bool = False) -> None:
        self.requests: list[HttpRequest] = []
        self.outcomes: list[Outcome] = []
        self.events: list[ObserveEvent] = []
        self.retry = retry
        self.bodies: list[RecordingBody] = []

    def on_request(self, request: HttpRequest) -> Decision:
        self.requests.append(request)
        return Proceed()

    def on_outcome(self, outcome: Outcome) -> Decision:
        self.outcomes.append(outcome)
        if self.retry and outcome.attempt == 0 and isinstance(outcome.error, RateLimitError):
            return Retry(after=0)
        return Proceed()

    def on_event(self, event: ObserveEvent) -> None:
        self.events.append(event)

    def assert_safe(self) -> None:
        for request in self.requests:
            assert "authorization" not in {key.lower() for key in request.headers}
        assert "sk-private" not in repr((self.requests, self.outcomes, self.events))
        assert "future_native" not in repr(self.events)
        assert "x-amzn-errortype" not in repr(self.events)
        assert "x-service-failure" not in repr(self.events)


def _model(name: str, record: Record, mapping: HostErrorMapper | None = None,
           *, legacy: bool = False) -> tuple[WireChatModel, HttpxTransport, MappedHost]:
    if mapping is None:
        callback = _native if name == "native" else _gateway
        mapping = HostErrorMapper(name, callback,
                                  {"code": "ThrottlingException" if name == "native" else "quota"})
    host = MappedHost(f"https://{name}-host.test", mapping)
    transport = HttpxTransport(provider="test-host")
    model = WireChatModel(ChatCompletionsCodec(),
        Binding(Direct(host.base_url) if legacy else host, ApiKey("sk-private"), transport),
        Catalog.of(ocai.openai.FRAGMENT), model_name="gpt-4o", policies=[record],
        attempt_observers=[record])
    return model, transport, host


def _mount(pair: dict[str, Any], record: Record) -> respx.Route:
    def response(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == pair["request"]["json"]
        assert request.headers["authorization"] == "Bearer sk-private"
        record.assert_safe()
        wire = pair["response"]
        body = RecordingBody(json.dumps(wire["json"]).encode())
        record.bodies.append(body)
        return httpx.Response(wire["status"], headers=wire["headers"], stream=body)
    return respx.post(pair["request"]["url"]).mock(side_effect=response)


@pytest.mark.parametrize("name", ["native", "gateway"])
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("streaming", [False, True])
@respx.mock
async def test_recorded_host_errors(name: str, asynchronous: bool, streaming: bool) -> None:
    pair = _load(name, streaming)
    record = Record()
    model, transport, _ = _model(name, record)
    route = _mount(pair, record)
    stream: ChatStream | AsyncChatStream | None = None
    ctx = CallContext(call_id=f"{name}-call", tenant=f"{name}-tenant")
    try:
        with pytest.raises(RateLimitError) as raised:
            if streaming:
                if asynchronous:
                    stream = await model.astream(REQUEST, ctx=ctx)
                    _ = [chunk async for chunk in stream]
                else:
                    stream = model.stream(REQUEST, ctx=ctx)
                    list(stream)
            elif asynchronous:
                await model.achat(REQUEST, ctx=ctx)
            else:
                model.chat(REQUEST, ctx=ctx)
    finally:
        transport.close()
        await transport.aclose()
    assert record.bodies and all(body.closed for body in record.bodies)
    error = raised.value
    assert error.code == ("ThrottlingException" if name == "native" else "quota")
    assert error.status == 400 and error.provider == "test-host"
    assert error.raw == pair["response"]["json"]
    assert error.response_body == json.dumps(pair["response"]["json"]).encode()
    assert error.response_headers is not None
    assert all(error.response_headers.get(k) == v for k, v in pair["response"]["headers"].items())
    if name == "gateway":
        assert error.retry_after == 1.25
    assert route.call_count == 1 and record.requests[0].ctx == ctx
    finished = [event for event in record.events if isinstance(event, WireExchanged)]
    assert len(finished) == 1 and finished[0].error_type == "RateLimitError"
    if stream is not None:
        assert stream.end is None and stream.outcome is not None
        assert stream.outcome.status == "failed" and stream.outcome.usage is None
    else:
        assert isinstance(record.outcomes[0].error, RateLimitError)
    record.assert_safe()


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_retry_policy_receives_mapped_error(asynchronous: bool) -> None:
    record = Record(retry=True)
    model, transport, _ = _model("native", record)
    route = _mount(_load("native"), record)
    try:
        with pytest.raises(RateLimitError):
            if asynchronous:
                await model.achat(REQUEST)
            else:
                model.chat(REQUEST)
    finally:
        transport.close()
        await transport.aclose()
    assert route.call_count == 2
    assert all(isinstance(outcome.error, RateLimitError) for outcome in record.outcomes)
    assert record.requests[0].headers is not record.requests[1].headers
    first, second = (outcome.error for outcome in record.outcomes)
    assert first is not None and second is not None
    assert first.response_headers is not second.response_headers
    record.assert_safe()


@pytest.mark.parametrize("legacy", [False, True])
@respx.mock
async def test_decline_and_legacy_keep_fallback(legacy: bool) -> None:
    def decline(error: OcaiError, options: dict[str, Any]) -> None:
        assert error.response_headers is not None
        error.response_headers.clear()
        options.clear()
        if error.raw is not None:
            error.raw.clear()

    mapping = HostErrorMapper("decline", decline, {"declared": True})
    record = Record()
    model, transport, _ = _model("native", record, mapping, legacy=legacy)
    _mount(_load("native"), record)
    try:
        with pytest.raises(OcaiError) as raised:
            model.chat(REQUEST)
    finally:
        transport.close()
        await transport.aclose()
    assert type(raised.value) is OcaiError
    assert raised.value.response_headers and raised.value.raw == _load("native")["response"]["json"]
    assert dict(mapping.options) == {"declared": True}


@pytest.mark.parametrize("mode", ["raise", "invalid"])
@respx.mock
async def test_mapper_failure_is_explicit_and_sanitized(mode: str) -> None:
    def broken(error: OcaiError, options: dict[str, Any]) -> Any:
        if mode == "raise":
            raise ValueError("private-callback-detail")
        return "invalid result"

    record = Record(retry=True)
    model, transport, _ = _model("native", record, HostErrorMapper("broken", broken))
    route = _mount(_load("native"), record)
    try:
        with pytest.raises(OcaiError) as raised:
            await model.achat(REQUEST)
    finally:
        transport.close()
        await transport.aclose()
    assert raised.value.code == "host_error_adaptation_failed"
    assert raised.value.response_headers
    assert "private-callback-detail" not in str(raised.value)
    assert raised.value.__cause__ is None and raised.value.__context__ is None
    assert route.call_count == 1


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("replacement", [False, True])
@respx.mock
async def test_changed_mapper_configuration_invalidates_preparation(
    streaming: bool, replacement: bool,
) -> None:
    record = Record()
    model, transport, host = _model("native", record)
    prepared = model.prepare(REQUEST, streaming=streaming)
    route = _mount(_load("native", streaming), record)
    # Declaration data is explicitly mutable for detecting changed effective configuration.
    assert isinstance(host.mapping.options, dict)
    if replacement:
        # Simulate an external host replacing its effective mapping implementation.
        object.__setattr__(host, "mapping", HostErrorMapper(
            host.mapping.name, _gateway, host.mapping.options))
    else:
        host.mapping.options["code"] = "changed"
    try:
        with pytest.raises(StalePreparationError):
            if streaming:
                list(prepared.stream())
            else:
                await prepared.achat()
    finally:
        transport.close()
        await transport.aclose()
    assert not route.calls


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_concurrent_host_mappings_are_independent(asynchronous: bool) -> None:
    records = [Record(), Record()]
    models = [_model(name, record) for name, record in zip(
        ("native", "gateway"), records, strict=True)]
    for name, record in zip(("native", "gateway"), records, strict=True):
        _mount(_load(name), record)

    def sync_call(model: WireChatModel, name: str) -> str | None:
        try:
            model.chat(REQUEST, ctx=CallContext(call_id=name))
        except OcaiError as error:
            return error.code
        raise AssertionError("expected error")

    async def async_call(model: WireChatModel, name: str) -> str | None:
        try:
            await model.achat(REQUEST, ctx=CallContext(call_id=name))
        except OcaiError as error:
            return error.code
        raise AssertionError("expected error")

    try:
        if asynchronous:
            results = await asyncio.gather(*(async_call(model, name)
                for (model, _, _), name in zip(models, ("native", "gateway"), strict=True)))
        else:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(sync_call, model, name)
                    for (model, _, _), name in zip(models, ("native", "gateway"), strict=True)]
                results = [future.result() for future in futures]
    finally:
        for _, transport, _ in models:
            transport.close()
            await transport.aclose()
    assert results == ["ThrottlingException", "quota"]
    for name, record in zip(("native", "gateway"), records, strict=True):
        assert all(event.call_id == name for event in record.events)
        record.assert_safe()


def test_error_evidence_construction_and_connection_failure() -> None:
    headers = {"native-code": "example"}
    error = OcaiError("safe", response_headers=headers, response_body=b"")
    headers.clear()
    assert error.response_headers == {"native-code": "example"}
    assert error.response_body == b""
    calls: list[OcaiError] = []
    def mapper(error: OcaiError, options: dict[str, Any]) -> None:
        calls.append(error)
    assert HostErrorMapper("http-only", mapper).apply(error) is None
    assert not calls
    assert OcaiError("unavailable").response_headers is None


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_dialect_refinement_preserves_native_evidence(asynchronous: bool) -> None:
    pair = json.loads((HTTP / "openai_chat_completion_context_length.json").read_text())
    body = json.dumps(pair["response"]["json"]).encode()
    route = respx.post(pair["request"]["url"]).respond(400, content=body)
    transport = HttpxTransport(provider="openai")
    host = MappedHost("https://api.openai.com", HostErrorMapper("decline", lambda e, o: None))
    model = WireChatModel(ChatCompletionsCodec(), Binding(host, ApiKey("sk-private"), transport),
                          Catalog.of(ocai.openai.FRAGMENT), model_name="gpt-4o")
    request = ChatRequest(messages=[Message.user("Hello, who are you?")])
    try:
        with pytest.raises(ContextLengthError) as raised:
            if asynchronous:
                await model.achat(request)
            else:
                model.chat(request)
    finally:
        transport.close()
        await transport.aclose()
    assert json.loads(route.calls.last.request.content) == pair["request"]["json"]
    assert raised.value.code == "context_length_exceeded"
    assert raised.value.response_body == body
    assert raised.value.response_headers is not None
    assert raised.value.raw == pair["response"]["json"]
