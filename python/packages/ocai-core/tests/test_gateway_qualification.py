"""WU-32: recorded four-leg gateway paths through public APIs only."""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import httpx
import pytest
import respx

import ocai.anthropic
import ocai.chat
import ocai.openai
from ocai.anthropic.messages.codec import MESSAGES_RESPONSE
from ocai.chat import CANONICAL_CHAT_CHUNK
from ocai.chat import CANONICAL_CHAT_REQUEST
from ocai.chat import CANONICAL_CHAT_RESPONSE
from ocai.chat.types import ChatChunk
from ocai.chat.types import StreamAccumulator
from ocai.convert.catalog import Catalog
from ocai.core.credentials import ApiKey
from ocai.core.errors import AuthError
from ocai.core.fidelity import FidelityPolicy
from ocai.core.fidelity import FidelityPolicyError
from ocai.core.fidelity import FidelityReport
from ocai.core.result import CallContext
from ocai.core.result import CallResult
from ocai.openai.chat_completions.client import ClientMetadata
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_CHUNK
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_REQUEST
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_RESPONSE
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.openai.chat_completions.codec import ChatCompletionsStreamTransducer
from ocai.runtime.decisions import Decision
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.interceptors import AsyncNextHandler
from ocai.runtime.interceptors import AsyncNextStreamHandler
from ocai.runtime.interceptors import AsyncStream
from ocai.runtime.interceptors import Call
from ocai.runtime.interceptors import NextHandler
from ocai.runtime.interceptors import NextStreamHandler
from ocai.runtime.interceptors import SyncStream
from ocai.runtime.observe import CallFinished
from ocai.runtime.observe import CallStarted
from ocai.runtime.observe import ObserveEvent
from ocai.runtime.observe import WireStarted
from ocai.wire import SSEvent
from ocai.wire.http import HttpRequest
from ocai.wire.transport import HttpxTransport

if TYPE_CHECKING:
    from examples.governed_gateway import ClientDelivery
    from examples.governed_gateway import client_complete
    from examples.governed_gateway import client_stream
else:
    example_path = Path(__file__).resolve().parents[4] / "examples/governed_gateway.py"
    example_spec = importlib.util.spec_from_file_location("ocai_gateway_example", example_path)
    assert example_spec is not None and example_spec.loader is not None
    example_module = importlib.util.module_from_spec(example_spec)
    sys.modules[example_spec.name] = example_module
    example_spec.loader.exec_module(example_module)
    ClientDelivery = example_module.ClientDelivery
    client_complete = example_module.client_complete
    client_stream = example_module.client_stream

type LoadHttp = Callable[[str], dict[str, Any]]
METADATA = ClientMetadata("chatcmpl-gateway", "deployment", 1767225600)
CTX = CallContext(tenant="tenant-a", compartment="compartment-a", principal="principal-a",
                  call_id="call-a", parent_id="parent-a", correlation_id="correlation-a")


class Admission:
    """Enforce the same context rule at all four port faces."""

    def __init__(self, *, deny: bool = False) -> None:
        self.contexts: list[CallContext | None] = []
        self.deny = deny

    def check(self, call: Call) -> None:
        self.contexts.append(call.ctx)
        assert call.ctx == CTX
        if self.deny:
            raise AuthError("admission rejected")

    def intercept(self, call: Call, next: NextHandler) -> CallResult[Any]:
        self.check(call)
        return next(call)

    async def aintercept(self, call: Call, next: AsyncNextHandler) -> CallResult[Any]:
        self.check(call)
        return await next(call)

    def intercept_stream(self, call: Call, next: NextStreamHandler) -> SyncStream:
        self.check(call)
        return next(call)

    async def aintercept_stream(self, call: Call, next: AsyncNextStreamHandler) -> AsyncStream:
        self.check(call)
        return await next(call)


class Evidence:
    """Retain safe wire requests and metadata-only observations."""

    def __init__(self) -> None:
        self.requests: list[HttpRequest] = []
        self.events: list[ObserveEvent] = []

    def on_request(self, request: HttpRequest) -> Decision:
        self.requests.append(request)
        assert request.ctx == CTX
        return Proceed()

    def on_outcome(self, outcome: Outcome) -> Decision:
        assert outcome.ctx == CTX
        self.requests.append(outcome.request)
        return Proceed()

    def on_event(self, event: ObserveEvent) -> None:
        self.events.append(event)


def _client(load_http: LoadHttp, provider: str, tools: bool) -> dict[str, Any]:
    if tools:
        return {**load_http("openai_chat_completion_tool_call.json")["request"]["json"],
                "model": "deployment"}
    if provider == "anthropic":
        return {"model": "deployment", "messages": [
            {"role": "system", "content": "You are concise."},
            {"role": "user", "content": "Hello, who are you?"}]}
    return {"model": "deployment", "messages": [{"role": "user", "content": "Hello!"}]}


def _recording(load_http: LoadHttp, provider: str, tools: bool,
               streaming: bool) -> dict[str, Any]:
    if tools:
        return load_http(f"gateway_{provider}_tools{'_stream' if streaming else ''}.json")
    if provider == "anthropic":
        return load_http(f"anthropic_messages{'_stream' if streaming else ''}.json")
    return load_http("openai_chat_completion_stream.json" if streaming else
                     "openai_chat_completion_stream_paired.json")


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
@pytest.mark.parametrize("tools", [False, True])
@pytest.mark.parametrize("mode", ["sync", "async", "stream", "astream"])
@respx.mock
async def test_full_client_path(load_http: LoadHttp, provider: str, tools: bool, mode: str) -> None:
    catalog = Catalog.of(ocai.openai.FRAGMENT, ocai.anthropic.FRAGMENT)
    policy = FidelityPolicy()  # Acceptance is explicit; findings remain visible.
    evidence = Evidence()
    admission = Admission()
    transport = HttpxTransport(provider=provider)
    resource = "gpt-4o" if provider == "openai" else "claude-opus-4-6"
    credential = (ApiKey("sk-test") if provider == "openai" else
                  ApiKey("sk-test", header="x-api-key", scheme=""))
    model = ocai.chat.model(f"{provider}/{resource}", credentials=credential,
        catalog=catalog, transport=transport, interceptors=[admission],
        policies=[evidence], observers=[evidence], conversion_policy=policy)
    payload = _client(load_http, provider, tools)
    streaming = "stream" in mode
    pair = _recording(load_http, provider, tools, streaming)

    def respond(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == pair["request"]["json"]
        assert request.headers["authorization" if provider == "openai" else "x-api-key"] == (
            "Bearer sk-test" if provider == "openai" else "sk-test")
        assert "tenant-a" not in request.content.decode()
        if streaming:
            return httpx.Response(200, content=("\n\n".join(pair["response"]["sse"])
                                               + "\n\n").encode())
        return httpx.Response(200, json=pair["response"]["json"])

    route = respx.post(pair["request"]["url"]).mock(side_effect=respond)
    body: dict[str, Any] | None = None
    events: list[dict[str, Any]] = []
    try:
        if mode == "sync":
            result = client_complete(payload, model=model, catalog=catalog, policy=policy,
                                     metadata=METADATA, ctx=CTX)
            body, report = result.value, result.report
        elif mode == "stream":
            with client_stream(payload, model=model, catalog=catalog, policy=policy,
                               metadata=METADATA, ctx=CTX) as delivery:
                events = list(delivery.events)
            assert delivery.outcome and delivery.outcome.status == "completed"
            report = delivery.report
        else:
            ingress = catalog.convert(payload, CHAT_COMPLETIONS_REQUEST, CANONICAL_CHAT_REQUEST)
            policy.enforce(ingress.report, phase="client_request")
            prepared = model.prepare(ingress.value, streaming=streaming)
            if mode == "async":
                result = await prepared.achat(ctx=CTX)
                egress = catalog.convert(result.value, CANONICAL_CHAT_RESPONSE,
                                          CHAT_COMPLETIONS_RESPONSE)
                body = METADATA.bind(egress.value)
                report = FidelityReport(edges=[*ingress.report.edges,
                    *(result.report or FidelityReport()).edges, *egress.report.edges])
            else:
                pipeline = catalog.stream_converter(CANONICAL_CHAT_CHUNK, CHAT_COMPLETIONS_CHUNK)
                async with await prepared.astream(ctx=CTX) as stream:
                    async for chunk in stream:
                        events.extend(METADATA.bind(event) for event in pipeline.feed(chunk))
                tail, reports = pipeline.flush()
                events.extend(METADATA.bind(event) for event in tail)
                assert stream.end and stream.end.report
                report = FidelityReport(edges=[*ingress.report.edges,
                                                *stream.end.report.edges, *reports])
        assert report and len(report.edges) == 4
        policy.enforce(report, phase="client_response")
        # Compare delivered client semantics with the paired recorded unary response.
        unary = _recording(load_http, provider, tools, False)
        src = CHAT_COMPLETIONS_RESPONSE if provider == "openai" else MESSAGES_RESPONSE
        canonical = catalog.convert(unary["response"]["json"], src, CANONICAL_CHAT_RESPONSE)
        expected = catalog.convert(canonical.value, CANONICAL_CHAT_RESPONSE,
                                   CHAT_COMPLETIONS_RESPONSE)
        if body is not None:
            assert body == METADATA.bind(expected.value)
        else:
            decoder = ChatCompletionsStreamTransducer()
            chunks: list[ChatChunk] = []
            for event in events:
                assert event["model"] == "deployment" and event["id"] == METADATA.id
                chunks.extend(decoder.feed(SSEvent(data=json.dumps(event))))
            chunks.extend(decoder.feed(SSEvent(data="[DONE]")))
            folded = StreamAccumulator.fold(chunks)
            expected_response = ChatCompletionsCodec().decode_response(expected.value).value
            assert folded.message == expected_response.message
            assert folded.finish == expected_response.finish
            assert folded.usage == expected_response.usage
        assert route.call_count == 1
        assert admission.contexts == [CTX]
        assert evidence.requests
        assert "sk-test" not in repr(evidence.requests) + repr(evidence.events) + repr(report)
        assert len([event for event in evidence.events if isinstance(event, CallStarted)]) == 1
        terminal = [event for event in evidence.events if isinstance(event, CallFinished)]
        assert len(terminal) == 1 and terminal[0].status == "completed"
        attempts = [event for event in evidence.events if isinstance(event, WireStarted)]
        assert len(attempts) == 1 and attempts[0].call_id == "call-a"
    finally:
        transport.close()
        await transport.aclose()


@pytest.mark.parametrize("streaming", [False, True])
async def test_example_admission_denial_has_zero_io(streaming: bool) -> None:
    catalog = Catalog.of(ocai.openai.FRAGMENT)
    model = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"), catalog=catalog,
                            interceptors=[Admission(deny=True)])
    with respx.mock as router:
        with pytest.raises(AuthError):
            if streaming:
                with client_stream({"messages": []}, model=model, catalog=catalog,
                                   policy=FidelityPolicy(), metadata=METADATA, ctx=CTX):
                    pass
            else:
                client_complete({"messages": []}, model=model, catalog=catalog,
                                policy=FidelityPolicy(), metadata=METADATA, ctx=CTX)
        assert not router.calls


@respx.mock
async def test_egress_rejection_withholds_success_and_retains_evidence(load_http: LoadHttp) -> None:
    catalog = Catalog.of(ocai.openai.FRAGMENT, ocai.anthropic.FRAGMENT)
    pair = load_http("anthropic_messages_stream.json")
    respx.post(pair["request"]["url"]).respond(
        200, content=("\n\n".join(pair["response"]["sse"]) + "\n\n").encode())
    model = ocai.chat.model("anthropic/claude-opus-4-6",
                            credentials=ApiKey("sk-test", header="x-api-key", scheme=""),
                            catalog=catalog)
    policy = FidelityPolicy(allow_loss=lambda loss: loss.path != "finish.native")
    delivered: list[dict[str, Any]] = []
    delivery: ClientDelivery | None = None
    with pytest.raises(FidelityPolicyError) as error:
        with client_stream(_client(load_http, "anthropic", False), model=model, catalog=catalog,
                           policy=policy, metadata=METADATA, ctx=CTX) as delivery:
            delivered.extend(delivery.events)
    assert error.value.partial and error.value.usage and error.value.usage.total_tokens == 23
    assert len(error.value.report.edges) == 4
    assert delivery is not None and delivery.outcome and delivery.outcome.status == "failed"
    assert delivered
    assert all(event["choices"][0]["finish_reason"] is None for event in delivered)


async def test_unconsumed_example_stream_is_closed_without_io() -> None:
    catalog = Catalog.of(ocai.openai.FRAGMENT)
    model = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"), catalog=catalog)
    with respx.mock as router:
        with client_stream({"messages": []}, model=model, catalog=catalog,
                           policy=FidelityPolicy(), metadata=METADATA, ctx=CTX) as delivery:
            pass
        assert not router.calls
    assert delivery.outcome and delivery.outcome.status == "closed"
    assert delivery.usage is None
    assert len(delivery.report.edges) == 3  # ingress, preparation, incomplete egress; no response


@pytest.mark.parametrize("streaming", [False, True])
async def test_client_conversion_denial_has_zero_provider_calls(streaming: bool) -> None:
    from ocai.core.fidelity import Disposition

    catalog = Catalog.of(ocai.openai.FRAGMENT)
    model = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"), catalog=catalog)
    policy = FidelityPolicy(forbidden_dispositions=frozenset({Disposition.UNSUPPORTED}))
    payload: dict[str, Any] = {"messages": [], "n": 2}
    with respx.mock as router:
        with pytest.raises(FidelityPolicyError) as error:
            if streaming:
                with client_stream(payload, model=model, catalog=catalog, policy=policy,
                                   metadata=METADATA, ctx=CTX):
                    pass
            else:
                client_complete(payload, model=model, catalog=catalog, policy=policy,
                                metadata=METADATA, ctx=CTX)
        assert not router.calls
    assert error.value.phase == "client_request"
    assert any(loss.path == "n" for loss in error.value.report.losses)


@respx.mock
async def test_example_partial_close_keeps_all_available_legs(load_http: LoadHttp) -> None:
    catalog = Catalog.of(ocai.openai.FRAGMENT)
    model = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"), catalog=catalog)
    pair = load_http("openai_chat_completion_stream.json")
    respx.post(pair["request"]["url"]).respond(
        200, content=("\n\n".join(pair["response"]["sse"]) + "\n\n").encode())
    with client_stream(_client(load_http, "openai", False), model=model, catalog=catalog,
                       policy=FidelityPolicy(), metadata=METADATA, ctx=CTX) as delivery:
        assert next(delivery.events)["choices"][0]["delta"]["role"] == "assistant"
    assert delivery.outcome and delivery.outcome.status == "closed"
    assert delivery.usage is None
    assert len(delivery.report.edges) == 4
    assert any(loss.path == "termination" for loss in delivery.report.losses)
