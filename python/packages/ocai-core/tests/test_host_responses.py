"""Governed host response adaptation uses recorded wire pairs and public APIs."""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

import ocai.openai
from ocai.chat.facade import ObservedChatModel
from ocai.chat.facade import StalePreparationError
from ocai.chat.facade import WireChatModel
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.convert import Catalog
from ocai.convert import DeclaredDisposition
from ocai.convert.host_effects import HostContractError
from ocai.convert.host_effects import HostEffectContract
from ocai.core import ApiKey
from ocai.core import ContentFilterError
from ocai.core import Disposition
from ocai.core import FieldLoss
from ocai.core import OcaiError
from ocai.core import SemanticShift
from ocai.core.fidelity import FidelityPolicy
from ocai.core.fidelity import FidelityPolicyError
from ocai.core.result import CallContext
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.runtime.binding import Binding
from ocai.runtime.binding import CompositionError
from ocai.runtime.decisions import Decision
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.decisions import Retry
from ocai.runtime.decisions import Return
from ocai.runtime.observe import CallFinished
from ocai.runtime.observe import ObserveEvent
from ocai.wire import HostAdaptation
from ocai.wire import HostResponseAdapter
from ocai.wire.hosting import Direct
from ocai.wire.hosting import EndpointSpec
from ocai.wire.http import HttpRequest
from ocai.wire.http import HttpResponse
from ocai.wire.transport import HttpxTransport

HTTP = Path(__file__).parent / "http"
REQUEST = ChatRequest(messages=[Message.system("You are concise."),
                                Message.user("Hello, who are you?")])
MASK = SemanticShift("test.masking", "output", "Synthetic host masked output before decoding")


def _pair(name: str) -> dict[str, Any]:
    return json.loads((HTTP / f"host_response_{name}.json").read_text())


def _adapt(response: HttpResponse, payload: dict[str, Any], options: dict[str, Any]
           ) -> HostAdaptation:
    assert "sk-private" not in repr((response, payload, options))
    if "result" in payload:
        body = payload["result"]
        metadata = payload["host"]
        losses = (FieldLoss("body.result", Disposition.RENAMED),
                  FieldLoss("body.host", Disposition.RENAMED))
    else:
        body = payload
        metadata = {"action": body.pop("host_action"),
                    "tier": response.headers[options["tier_header"]]}
        losses = (FieldLoss("body.host_action", Disposition.RENAMED),)
    return HostAdaptation(body, metadata, losses, (MASK,),
        ContentFilterError("host blocked output", code="test.blocked") if options.get("block")
        else None)


@dataclass(frozen=True)
class ResponseHost(Direct):
    mapping: HostResponseAdapter

    def response_adapter(self, spec: EndpointSpec) -> HostResponseAdapter:
        return self.mapping


class Record:
    def __init__(self, *, retry: bool = False, returned: HttpResponse | None = None,
                 admission_return: bool = False) -> None:
        self.requests: list[HttpRequest] = []
        self.events: list[ObserveEvent] = []
        self.retry = retry
        self.returned = returned
        self.admission_return = admission_return

    def on_request(self, request: HttpRequest) -> Decision:
        self.requests.append(request)
        if self.admission_return and self.returned is not None:
            return Return(self.returned)
        return Proceed()

    def on_outcome(self, outcome: Outcome) -> Decision:
        if self.retry and outcome.attempt == 0:
            return Retry(0)
        return Return(self.returned) if self.returned is not None else Proceed()

    def on_event(self, event: ObserveEvent) -> None:
        self.events.append(event)

    def assert_safe(self) -> None:
        assert all("authorization" not in {k.lower() for k in request.headers}
                   for request in self.requests)
        assert "sk-private" not in repr((self.requests, self.events))
        assert "x-native-evidence" not in repr(self.events)
        assert "host_action" not in repr(self.events)


def _mapping(name: str) -> HostResponseAdapter:
    contract = HostEffectContract({path: DeclaredDisposition(Disposition.RENAMED)
        for path in ("body.host_action", "body.result", "body.host")}, (MASK,))
    return HostResponseAdapter(name, "test-adapter@1", _adapt, contract,
                                {"tier_header": "x-host-tier"})


def _model(name: str, record: Record, *, mapping: HostResponseAdapter | None = None,
           policy: FidelityPolicy | None = None
           ) -> tuple[WireChatModel, HttpxTransport, ResponseHost]:
    host = ResponseHost(f"https://{name}-host.test", mapping or _mapping(name))
    transport = HttpxTransport()
    model = WireChatModel(ChatCompletionsCodec(),
        Binding(host, ApiKey("sk-private"), transport), Catalog.of(ocai.openai.FRAGMENT),
        model_name="gpt-4o", policies=[record], attempt_observers=[record],
        conversion_policy=policy)
    return model, transport, host


def _mount(name: str, record: Record) -> respx.Route:
    pair = _pair(name)
    def respond(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == pair["request"]["json"]
        assert request.headers["authorization"] == "Bearer sk-private"
        record.assert_safe()
        return httpx.Response(200, headers=pair["response"]["headers"],
                              content=json.dumps(pair["response"]["json"]).encode())
    return respx.post(pair["request"]["url"]).mock(side_effect=respond)


@pytest.mark.parametrize("name", ["filter", "envelope"])
@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_prepared_host_response_evidence(name: str, asynchronous: bool) -> None:
    record = Record()
    model, transport, host = _model(name, record)
    route = _mount(name, record)
    prepared = model.prepare(REQUEST)
    declaration = prepared.inspection.host_effects[0]
    assert not declaration.conformance_evaluated
    assert declaration.contract.identity == host.mapping.contract.identity
    assert not prepared.inspection.request_report.hosts
    try:
        result = (await prepared.achat(ctx=CallContext(call_id=name)) if asynchronous
                  else prepared.chat(ctx=CallContext(call_id=name)))
    finally:
        transport.close()
        await transport.aclose()
    assert route.call_count == 1
    assert result.report and len(result.report.hosts) == 1
    assert result.report.hosts[0].contract_id == declaration.contract.identity
    assert MASK in result.report.shifts
    expected = _pair(name)["expect_host"]
    assert declaration.contract.to_dict() == _pair(name)["host_contract"]
    assert [loss.to_dict() for loss in result.report.hosts[0].losses] == expected["losses"]
    assert [shift.to_dict() for shift in result.report.hosts[0].shifts] == expected["shifts"]
    assert result.usage and result.usage.total_tokens > 0
    evidence = result.host_evidence
    assert evidence and evidence.metadata == expected["metadata"]
    assert evidence.response_headers and evidence.response_headers["x-host-tier"] == "fast"
    assert evidence.response_body == json.dumps(_pair(name)["response"]["json"]).encode()
    assert result.raw == _pair(name)["response"]["json"]
    assert all(event.call_id == name for event in record.events)
    record.assert_safe()


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("kind", ["semantic", "field", "census", "blocked"])
@respx.mock
async def test_rejected_host_outcomes_retain_known_accounting(
    asynchronous: bool, kind: str,
) -> None:
    mapping = _mapping("filter")
    if kind == "census":
        mapping = HostResponseAdapter(mapping.host, mapping.name, _adapt,
                                      HostEffectContract(), mapping.options)
    elif kind == "blocked":
        mapping = HostResponseAdapter(mapping.host, mapping.name, _adapt,
                                      mapping.contract, {**mapping.options, "block": True})
    policy = (FidelityPolicy(forbidden_shifts=frozenset({MASK.kind})) if kind == "semantic"
              else FidelityPolicy(allow_loss=lambda loss: loss.path != "body.host_action")
              if kind == "field" else None)
    record = Record()
    model, transport, _ = _model("filter", record, mapping=mapping, policy=policy)
    route = _mount("filter", record)
    expected = ContentFilterError if kind == "blocked" else FidelityPolicyError
    try:
        with pytest.raises(expected) as raised:
            if asynchronous:
                await model.achat(REQUEST)
            else:
                model.chat(REQUEST)
    finally:
        transport.close()
        await transport.aclose()
    error = raised.value
    assert route.call_count == 1
    assert error.report and len(error.report.hosts) == 1
    assert error.usage and error.usage.total_tokens > 0
    if kind == "census":
        assert isinstance(error, HostContractError) and error.violations
    if kind == "blocked":
        assert error.host_evidence and error.response_body
        assert error.code == "test.blocked"
    else:
        assert error.raw is None and error.host_evidence is None and error.response_body is None


@pytest.mark.parametrize("change", ["options", "callback", "contract"])
@respx.mock
async def test_host_adapter_change_invalidates_preparation(change: str) -> None:
    record = Record()
    model, transport, host = _model("filter", record)
    route = _mount("filter", record)
    prepared = model.prepare(REQUEST)
    if change == "options":
        assert isinstance(host.mapping.options, dict)
        host.mapping.options["tier_header"] = "different"
    elif change == "contract":
        assert isinstance(host.mapping.contract.census, dict)
        host.mapping.contract.census.clear()
    else:
        object.__setattr__(host, "mapping", HostResponseAdapter("filter", "test-adapter@1",
            lambda response, payload, options: _adapt(response, payload, options),
            host.mapping.contract, host.mapping.options))
    try:
        with pytest.raises(StalePreparationError):
            await prepared.achat()
    finally:
        transport.close()
        await transport.aclose()
    assert not route.calls


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_unary_adapter_cannot_be_bypassed_by_streaming(asynchronous: bool) -> None:
    record = Record()
    model, transport, _ = _model("filter", record)
    route = _mount("filter", record)
    try:
        with pytest.raises(CompositionError, match="unary"):
            if asynchronous:
                await model.astream(REQUEST)
            else:
                model.stream(REQUEST)
    finally:
        transport.close()
        await transport.aclose()
    assert not route.calls and not record.events


@pytest.mark.parametrize("mode", ["mutate", "raise", "invalid", "non_json"])
@respx.mock
async def test_adapter_isolation_and_fail_closed(mode: str) -> None:
    def callback(response: HttpResponse, payload: dict[str, Any], options: dict[str, Any]) -> Any:
        value = _adapt(response, payload, options)
        response.headers.clear()
        payload.clear()
        options.clear()
        if mode == "raise":
            raise RuntimeError("private-callback-detail")
        if mode == "invalid":
            return object()
        if mode == "non_json":
            return HostAdaptation(value.payload, {"invalid": object()})
        # The callback may mutate its inputs; preserve the output independently.
        original = _pair("filter")["response"]["json"]
        return _adapt(HttpResponse(200, {"x-host-tier": "fast"}), original,
                      {"tier_header": "x-host-tier"})
    base = _mapping("filter")
    mapping = HostResponseAdapter(base.host, base.name, callback, base.contract, base.options)
    record = Record()
    model, transport, _ = _model("filter", record, mapping=mapping)
    _mount("filter", record)
    try:
        if mode == "mutate":
            result = await model.achat(REQUEST)
            assert result.host_evidence and result.host_evidence.response_headers
        else:
            with pytest.raises(OcaiError) as raised:
                await model.achat(REQUEST)
            assert raised.value.code == "host_response_adaptation_failed"
            assert "private-callback-detail" not in str(raised.value)
            assert raised.value.__cause__ is None and raised.value.__context__ is None
            assert raised.value.host_evidence and raised.value.response_body
    finally:
        transport.close()
        await transport.aclose()
    assert mapping.options == {"tier_header": "x-host-tier"}
    record.assert_safe()


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("replacement", [False, True])
@respx.mock
async def test_final_selected_response_is_accounted_once(
    asynchronous: bool, replacement: bool,
) -> None:
    pair = _pair("filter")
    replaced = HttpResponse(200, {"x-host-tier": "cached"},
                            json.dumps(pair["response"]["json"]).encode())
    record = Record(retry=not replacement, returned=replaced if replacement else None)
    model, transport, _ = _model("filter", record)
    route = _mount("filter", record)
    try:
        result = await model.achat(REQUEST) if asynchronous else model.chat(REQUEST)
    finally:
        transport.close()
        await transport.aclose()
    assert route.call_count == (1 if replacement else 2)
    assert result.report and len(result.report.hosts) == 1
    assert result.host_evidence
    assert result.host_evidence.metadata["tier"] == ("cached" if replacement else "fast")


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_concurrent_host_evidence_is_independent(asynchronous: bool) -> None:
    records = [Record(), Record()]
    names = ["filter", "envelope"]
    models = [_model(name, record) for name, record in zip(names, records, strict=True)]
    for name, record in zip(names, records, strict=True):
        _mount(name, record)
    try:
        if asynchronous:
            results = await asyncio.gather(*(model.achat(REQUEST, ctx=CallContext(call_id=name))
                for name, (model, _, _) in zip(names, models, strict=True)))
        else:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(model.chat, REQUEST, ctx=CallContext(call_id=name))
                    for name, (model, _, _) in zip(names, models, strict=True)]
                results = [future.result() for future in futures]
    finally:
        for _, transport, _ in models:
            transport.close()
            await transport.aclose()
    hosts = [result.host_evidence.host if result.host_evidence else None for result in results]
    assert hosts == names
    for name, record in zip(names, records, strict=True):
        assert all(event.call_id == name for event in record.events)
        record.assert_safe()


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_admission_return_still_runs_host_adaptation(asynchronous: bool) -> None:
    pair = _pair("filter")
    returned = HttpResponse(200, pair["response"]["headers"],
                            json.dumps(pair["response"]["json"]).encode())
    record = Record(returned=returned, admission_return=True)
    model, transport, _ = _model("filter", record)
    try:
        result = await model.achat(REQUEST) if asynchronous else model.chat(REQUEST)
    finally:
        transport.close()
        await transport.aclose()
    assert result.report and len(result.report.hosts) == 1
    assert result.host_evidence and result.host_evidence.response_body == returned.body
    assert not record.events
    returned.headers.clear()
    assert result.host_evidence.response_headers


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("blocked", [False, True])
@respx.mock
async def test_lifecycle_retains_accounting_but_omits_native_evidence(
    asynchronous: bool, blocked: bool,
) -> None:
    base = _mapping("filter")
    mapping = HostResponseAdapter(base.host, base.name, _adapt, base.contract,
                                  {**base.options, "block": blocked})
    record = Record()
    inner, transport, _ = _model("filter", record, mapping=mapping)
    model = ObservedChatModel(inner, [record])
    _mount("filter", record)
    try:
        if blocked:
            with pytest.raises(ContentFilterError):
                if asynchronous:
                    await model.achat(REQUEST)
                else:
                    model.chat(REQUEST)
        elif asynchronous:
            await model.achat(REQUEST)
        else:
            model.chat(REQUEST)
    finally:
        transport.close()
        await transport.aclose()
    finished = [event for event in record.events if isinstance(event, CallFinished)]
    assert len(finished) == 1
    assert finished[0].report and len(finished[0].report.hosts) == 1
    assert finished[0].usage and finished[0].usage.total_tokens > 0
    assert finished[0].status == ("failed" if blocked else "completed")
    assert "x-native-evidence" not in repr(record.events)
    assert "sk-private" not in repr(record.events)
    assert "'tier': 'fast'" not in repr(record.events)
