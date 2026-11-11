"""WU-45: recorded DeepSeek traffic through public preparation and execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

import ocai.chat
import ocai.deepseek
from ocai.chat.types import ChatRequest
from ocai.chat.types import PartReasoning
from ocai.chat.types import PartText
from ocai.chat.types import PartToolCall
from ocai.convert import Catalog
from ocai.core import ApiKey
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import FidelityPolicy
from ocai.core.fidelity import FidelityPolicyError
from ocai.core.result import CallContext
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.observe import CallFinished
from ocai.runtime.observe import CallStarted
from ocai.runtime.observe import ObserveEvent
from ocai.runtime.observe import WireExchanged
from ocai.runtime.observe import WireStarted
from ocai.wire.http import HttpRequest
from ocai.wire.transport import HttpxTransport

HTTP = Path(__file__).parent / "http"
SPEC = Path(__file__).resolve().parents[4] / "spec/fixtures/deepseek/chat_completions"
URL = "https://api.deepseek.com/chat/completions"


def _pair(name: str) -> dict[str, Any]:
    return json.loads((HTTP / f"deepseek_chat_{name}.json").read_text())


def _request(name: str) -> ChatRequest:
    fixture = {
        "text": "request_text",
        "json": "request_json_object",
        "tools": "request_text",
        "replay": "request_reasoning_replay",
    }[name]
    data: dict[str, Any] = json.loads((SPEC / f"{fixture}.json").read_text())["input"]
    if name == "tools":
        data["messages"] = [{"role": "user", "parts": [{"type": "text", "text": "Look it up."}]}]
        data["tools"] = [{"name": "lookup", "parameters": {"type": "object"}}]
    return ChatRequest.from_dict(data)


class Capture:
    """Retain actual public policy and observer values across the transport attempt."""

    def __init__(self) -> None:
        self.requests: list[HttpRequest] = []
        self.outcomes: list[Outcome] = []
        self.events: list[ObserveEvent] = []

    def on_request(self, request: HttpRequest) -> Proceed:
        self.requests.append(request)
        return Proceed()

    def on_outcome(self, outcome: Outcome) -> Proceed:
        self.outcomes.append(outcome)
        return Proceed()

    def on_event(self, event: ObserveEvent) -> None:
        self.events.append(event)


@pytest.mark.parametrize("name", ["text", "json", "tools", "replay"])
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("discover", [False, True])
@respx.mock
async def test_prepared_recording_retains_identity_context_credentials_and_evidence(
    name: str,
    asynchronous: bool,
    discover: bool,
) -> None:
    pair = _pair(name)
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))
    capture = Capture()
    transport = HttpxTransport(provider="deepseek")
    catalog = None if discover else Catalog.of(ocai.deepseek.FRAGMENT)
    model = ocai.chat.model(
        "deepseek/deepseek-flash",
        credentials=ApiKey("sk-test-deepseek"),
        catalog=catalog,
        transport=transport,
        policies=[capture],
        observers=[capture],
        conversion_policy=FidelityPolicy(
            forbidden_dispositions=frozenset({Disposition.UNSUPPORTED})
        ),
    )
    request = _request(name)
    ctx = CallContext(
        tenant="tenant-test",
        principal="principal-test",
        compartment="scope-test",
        call_id="call-test",
        parent_id="parent-test",
        correlation_id="trace-test",
    )
    try:
        prepared = model.prepare(request)
        inspection = prepared.inspection
        assert not route.calls and not capture.events
        assert inspection.route.node.provider == "deepseek"
        assert inspection.route.node.tag == "2026-11"
        assert inspection.route.catalog_hash
        assert inspection.request_path.edges and inspection.response_path.edges
        assert inspection.request_path.conformance_evaluated is False
        request.messages.clear()  # approved preparation owns an independent snapshot
        result = await prepared.achat(ctx=ctx) if asynchronous else prepared.chat(ctx=ctx)
    finally:
        transport.close()
        await transport.aclose()
    assert route.call_count == 1
    sent = route.calls.last.request
    assert json.loads(sent.content) == pair["request"]["json"]
    assert sent.headers["authorization"] == "Bearer sk-test-deepseek"
    assert "tenant-test" not in sent.content.decode()
    assert result.route is not None
    assert result.report is not None
    assert result.value.finish is not None
    assert result.route.node.provider == "deepseek"
    assert result.value.info and result.value.info.id
    assert result.value.info.id.provider == "deepseek"
    assert result.raw == pair["response"]["json"]
    assert result.usage is not None
    assert {item.source: item.value for item in result.usage.consumptions} == {
        "input": 6,
        "cached": 4,
        "output": 4,
        "reasoning": 2,
    }
    assert any(isinstance(part, PartReasoning) for part in result.value.message.parts)
    if name == "tools":
        calls = [part for part in result.value.message.parts if isinstance(part, PartToolCall)]
        assert [(part.call_id, part.name, part.args_json) for part in calls] == [
            ("call_synthetic", "lookup", "{}"),
        ]
        assert result.value.finish.reason == "tool_call"
    else:
        texts = [part.text for part in result.value.message.parts if isinstance(part, PartText)]
        assert texts == [pair["response"]["json"]["choices"][0]["message"]["content"]]
        assert result.value.finish.reason == "complete"
    assert len(result.report.edges) == 2
    assert result.report.edges[0].dst.provider == "deepseek"
    assert result.report.edges[1].src.provider == "deepseek"
    assert capture.requests and capture.outcomes
    assert capture.requests[0].ctx == capture.outcomes[0].ctx == ctx
    assert all(
        "authorization" not in {key.lower() for key in req.headers}
        for req in [*capture.requests, *(out.request for out in capture.outcomes)]
    )
    assert [type(event) for event in capture.events] == [
        CallStarted,
        WireStarted,
        WireExchanged,
        CallFinished,
    ]
    assert all(event.call_id == "call-test" for event in capture.events)
    assert "sk-test-deepseek" not in repr(capture.events)
    assert "sk-test-deepseek" not in repr(result.report)


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_missing_reasoning_is_rejected_without_an_attempt(asynchronous: bool) -> None:
    fixture = json.loads((SPEC / "request_missing_reasoning.json").read_text())
    capture = Capture()
    transport = HttpxTransport(provider="deepseek")
    model = ocai.chat.model(
        "deepseek/deepseek-flash",
        credentials=ApiKey("sk-test"),
        catalog=Catalog.of(ocai.deepseek.FRAGMENT),
        transport=transport,
        observers=[capture],
        conversion_policy=FidelityPolicy(
            forbidden_dispositions=frozenset({Disposition.UNSUPPORTED})
        ),
    )
    route = respx.post(URL).mock(
        return_value=httpx.Response(200, json=_pair("text")["response"]["json"])
    )
    try:
        with pytest.raises(FidelityPolicyError) as error:
            if asynchronous:
                await model.achat(ChatRequest.from_dict(fixture["input"]))
            else:
                model.chat(ChatRequest.from_dict(fixture["input"]))
        assert error.value.phase == "request"
        assert any(
            loss.path == "messages[3].parts[reasoning]"
            for edge in error.value.report.edges
            for loss in edge.losses
        )
        assert not route.calls
        assert not any(isinstance(event, WireStarted) for event in capture.events)
    finally:
        transport.close()
        await transport.aclose()


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_response_policy_preserves_measured_usage_and_fidelity(asynchronous: bool) -> None:
    pair = _pair("response_evidence")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))
    transport = HttpxTransport(provider="deepseek")
    model = ocai.chat.model(
        "deepseek/deepseek-flash",
        credentials=ApiKey("sk-test"),
        catalog=Catalog.of(ocai.deepseek.FRAGMENT),
        transport=transport,
        conversion_policy=FidelityPolicy(
            forbidden_dispositions=frozenset({Disposition.EXTENSIONS})
        ),
    )
    try:
        with pytest.raises(FidelityPolicyError) as caught:
            if asynchronous:
                await model.achat(_request("text"))
            else:
                model.chat(_request("text"))
        assert caught.value.phase == "response"
        assert caught.value.usage is not None and caught.value.usage.consumptions
        assert caught.value.report.edges[-1].src.provider == "deepseek"
        assert any(loss.path == "unmapped" for loss in caught.value.report.edges[-1].losses)
        assert route.call_count == 1
        assert not caught.value.partial
    finally:
        transport.close()
        await transport.aclose()
