"""Recorded InvokeModel qualification through public contracts and real AWS signing."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

import ocai.anthropic
import ocai.chat
from ocai.anthropic.messages import MESSAGES_REQUEST
from ocai.anthropic.messages.codec import dialect_traits
from ocai.aws import SigV4Credential
from ocai.bedrock import Bedrock
from ocai.chat.facade import InterceptedChatModel
from ocai.chat.facade import ObservedChatModel
from ocai.chat.facade import StalePreparationError
from ocai.chat.facade import WireChatModel
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.chat.types import PartToolCall
from ocai.chat.types import Tool
from ocai.chat.types import ToolChoice
from ocai.convert import Catalog
from ocai.core import AuthError
from ocai.core import ContentFilterError
from ocai.core import Disposition
from ocai.core import OcaiError
from ocai.core import RateLimitError
from ocai.core import TransientError
from ocai.core import UnsupportedFeatureError
from ocai.core.fidelity import FidelityPolicy
from ocai.core.fidelity import FidelityPolicyError
from ocai.core.jsonschema import JsonSchema
from ocai.core.result import CallContext
from ocai.runtime.decisions import Decision
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.decisions import Retry
from ocai.runtime.observe import CallFinished
from ocai.runtime.observe import ObserveEvent
from ocai.wire.hosting import EndpointSpec
from ocai.wire.hosting import Operation
from ocai.wire.http import HttpRequest
from ocai.wire.http import HttpResponse
from ocai.wire.transport import HttpxTransport

HTTP = Path(__file__).parent / "http"
RESOURCE = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
CATALOG = Catalog.of(ocai.anthropic.FRAGMENT)
ACCESS = "synthetic-access-key"
SECRET = "synthetic-secret-key"
TOKEN = "synthetic-session-token"


def _pair(name: str) -> dict[str, Any]:
    return json.loads((HTTP / f"bedrock_invoke_{name}.json").read_text())


def _request(tools: bool = False) -> ChatRequest:
    if not tools:
        return ChatRequest(
            messages=[Message.system("You are concise."), Message.user("Hello, who are you?")]
        )
    return ChatRequest(
        messages=[Message.user("What is the weather in Paris?")],
        tools=[
            Tool(
                name="get_weather",
                parameters=JsonSchema.from_dict(
                    {
                        "type": "object",
                        "properties": {"city": {"type": "string", "description": "City name."}},
                        "required": ["city"],
                    }
                ),
                description="Get the current weather for a city.",
            )
        ],
        tool_choice=ToolChoice(mode="auto"),
    )


def _spec(resource: str = RESOURCE, *, streaming: bool = False) -> EndpointSpec:
    return EndpointSpec(
        MESSAGES_REQUEST,
        dialect_traits(),
        Operation("chat", "generative", streaming=streaming),
        resource,
        "/v1/messages",
    )


class Record:
    def __init__(self, *, retry: bool = False) -> None:
        self.requests: list[HttpRequest] = []
        self.outcomes: list[Outcome] = []
        self.events: list[ObserveEvent] = []
        self.signings = 0
        self.retry = retry

    def clock(self) -> datetime:
        self.signings += 1
        return datetime(2026, 11, 11, 12, 0, self.signings, tzinfo=UTC)

    def on_request(self, request: HttpRequest) -> Decision:
        self.requests.append(request)
        return Proceed()

    def on_outcome(self, outcome: Outcome) -> Decision:
        self.outcomes.append(outcome)
        if self.retry and isinstance(outcome.error, RateLimitError) and outcome.attempt == 0:
            return Retry(0)
        return Proceed()

    def on_event(self, event: ObserveEvent) -> None:
        self.events.append(event)

    def assert_safe(self) -> None:
        requests = self.requests + [outcome.request for outcome in self.outcomes]
        for request in requests:
            assert not {"authorization", "x-amz-security-token", "x-amz-date"} & {
                key.lower() for key in request.headers
            }
        for value in (ACCESS, SECRET, TOKEN):
            assert value not in repr((requests, self.events))
        assert "sample@example.test" not in repr(self.events)
        assert "modelOutput" not in repr(self.events)


def _model(
    host: Bedrock, record: Record, transport: HttpxTransport, policy: FidelityPolicy | None = None
) -> WireChatModel | InterceptedChatModel | ObservedChatModel:
    return ocai.chat.model(
        f"anthropic/{RESOURCE}",
        host=host,
        catalog=CATALOG,
        credentials=SigV4Credential(
            ACCESS, SECRET, region="us-east-1", session_token=TOKEN, clock=record.clock
        ),
        transport=transport,
        policies=[record],
        observers=[record],
        conversion_policy=policy,
    )


def _host(name: str) -> Bedrock:
    if name in {"masked", "blocked", "uncertain"}:
        return Bedrock(
            "us-east-1",
            guardrail_identifier="synthetic-guardrail",
            guardrail_version="1",
            trace="ENABLED",
        )
    return Bedrock("us-east-1")


def _mount(pair: dict[str, Any], record: Record) -> respx.Route:
    def respond(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == pair["request"]["json"]
        for key, value in pair["request"]["headers"].items():
            assert request.headers[key] == value
        assert "anthropic-version" not in request.headers
        assert "anthropic-beta" not in request.headers
        assert request.headers["x-amz-security-token"] == TOKEN
        authorization = request.headers["authorization"]
        assert authorization.startswith(f"AWS4-HMAC-SHA256 Credential={ACCESS}/")
        assert "/us-east-1/bedrock/aws4_request" in authorization
        assert "Signature=" in authorization
        assert "tenant" not in request.headers and b"private-tenant" not in request.content
        record.assert_safe()
        return httpx.Response(
            pair["response"]["status"],
            headers=pair["response"]["headers"],
            content=json.dumps(pair["response"]["json"]).encode(),
        )

    return respx.post(pair["request"]["url"]).mock(side_effect=respond)


@pytest.mark.parametrize("name", ["text", "tools", "masked", "uncertain", "future"])
@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_public_invoke_model_recordings(name: str, asynchronous: bool) -> None:
    pair = _pair(name)
    record, transport = Record(), HttpxTransport(provider="anthropic")
    model = _model(_host(name), record, transport)
    route = _mount(pair, record)
    prepared = model.prepare(_request(name == "tools"))
    assert all(profile.model_pattern == "*" for profile in prepared.inspection.profiles)
    # Existing dialect-wide declarations are not host/model qualification.
    declaration = prepared.inspection.host_effects[0]
    assert declaration.host == "bedrock" and not declaration.conformance_evaluated
    assert declaration.contract.to_dict() == _pair("text")["host_contract"]
    ctx = CallContext(call_id=name, tenant="private-tenant", correlation_id="synthetic-correlation")
    try:
        result = await prepared.achat(ctx=ctx) if asynchronous else prepared.chat(ctx=ctx)
    finally:
        transport.close()
        await transport.aclose()
    assert route.call_count == record.signings == 1
    assert result.route and result.route.node == MESSAGES_REQUEST
    assert result.route.host == pair["request"]["url"]
    assert result.route.catalog_hash == CATALOG.lock().hash
    assert result.usage and result.usage.input_tokens == (55 if name == "tools" else 14)
    assert result.usage.output_tokens == (17 if name == "tools" else 9)
    assert result.value.finish and result.value.finish.reason == (
        "tool_call" if name == "tools" else "complete"
    )
    assert result.value.info and result.value.info.model == "claude-3-5-sonnet-20241022"
    if name == "tools":
        call = result.value.message.parts[0]
        assert isinstance(call, PartToolCall)
        assert (call.call_id, call.name, call.args()) == (
            "toolu_01A2B3C4",
            "get_weather",
            {"city": "Paris"},
        )
    else:
        assert result.value.message.text == pair["response"]["json"]["content"][0]["text"]
    assert result.report and len(result.report.edges) == 2 and len(result.report.hosts) == 1
    host_report = result.report.hosts[0]
    expected = pair["expect_host"]
    assert host_report.contract_id == declaration.contract.identity
    assert [loss.path for loss in host_report.losses] == expected["paths"]
    assert all(loss.disposition == Disposition.RENAMED for loss in host_report.losses)
    assert [shift.kind for shift in host_report.shifts] == expected["shifts"]
    assert declaration.contract.certify(host_report.losses, host_report.shifts) == []
    evidence = result.host_evidence
    assert evidence and evidence.metadata == expected["metadata"]
    assert evidence.response_body == json.dumps(pair["response"]["json"]).encode()
    assert result.raw == pair["response"]["json"]
    if name == "future":
        assert "future_vendor_field" in repr(result.value.extensions)
    assert all(request.ctx == ctx for request in record.requests)
    assert all(outcome.ctx == ctx for outcome in record.outcomes)
    assert all(event.call_id == name for event in record.events)
    assert len([event for event in record.events if isinstance(event, CallFinished)]) == 1
    record.assert_safe()


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("name", ["blocked", "masked", "uncertain"])
@respx.mock
async def test_guardrail_failure_and_policy_preserve_accounting(
    name: str,
    asynchronous: bool,
) -> None:
    record, transport = Record(), HttpxTransport()
    policy = FidelityPolicy(
        forbidden_shifts=frozenset({"bedrock.masked_output", "bedrock.guardrail_intervened"})
    )
    model = _model(_host(name), record, transport, policy)
    route = _mount(_pair(name), record)
    try:
        with pytest.raises(ContentFilterError if name == "blocked" else FidelityPolicyError) as exc:
            if asynchronous:
                await model.achat(_request())
            else:
                model.chat(_request())
    finally:
        transport.close()
        await transport.aclose()
    error = exc.value
    assert error.report and len(error.report.hosts) == 1
    assert error.usage and error.usage.total_tokens == 23
    if name == "blocked":
        assert error.code == "guardrail_intervened" and error.host_evidence
    else:
        assert error.raw is None and error.host_evidence is None and error.response_body is None
    assert route.call_count == 1
    terminal = [event for event in record.events if isinstance(event, CallFinished)]
    assert len(terminal) == 1 and terminal[0].usage == error.usage
    record.assert_safe()


@pytest.mark.parametrize(
    "name,error_type",
    [
        ("throttled", RateLimitError),
        ("denied", AuthError),
        ("model_error", TransientError),
        ("validation", OcaiError),
        ("unknown_error", OcaiError),
    ],
)
@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_native_errors_keep_exact_evidence(
    name: str,
    error_type: type[OcaiError],
    asynchronous: bool,
) -> None:
    pair, record, transport = _pair(name), Record(), HttpxTransport(provider="anthropic")
    model = _model(_host(name), record, transport)
    _mount(pair, record)
    try:
        with pytest.raises(error_type) as exc:
            if asynchronous:
                await model.achat(_request())
            else:
                model.chat(_request())
    finally:
        transport.close()
        await transport.aclose()
    error = exc.value
    assert type(error) is error_type
    assert error.status == pair["response"]["status"]
    assert error.code == (
        pair["response"]["headers"].get("x-amzn-errortype") or pair["response"]["json"]["__type"]
    )
    assert error.raw == pair["response"]["json"]
    assert error.response_body == json.dumps(pair["response"]["json"]).encode()
    assert error.response_headers and error.response_headers["x-amzn-requestid"]
    assert isinstance(record.outcomes[0].error, error_type)
    record.assert_safe()


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_retry_signs_each_attempt_after_safe_hooks(asynchronous: bool) -> None:
    record, transport = Record(retry=True), HttpxTransport()
    model = _model(_host("text"), record, transport)
    first, second = _pair("throttled"), _pair("text")
    sent: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        pair = (first, second)[len(sent)]
        sent.append(request)
        record.assert_safe()
        return httpx.Response(
            pair["response"]["status"],
            headers=pair["response"]["headers"],
            json=pair["response"]["json"],
        )

    route = respx.post(first["request"]["url"]).mock(side_effect=respond)
    try:
        result = await model.achat(_request()) if asynchronous else model.chat(_request())
    finally:
        transport.close()
        await transport.aclose()
    assert result.usage and result.usage.total_tokens == 23
    assert route.call_count == record.signings == 2
    assert sent[0].headers["authorization"] != (sent[1].headers["authorization"])
    assert [outcome.attempt for outcome in record.outcomes] == [0, 1]
    assert all(json.loads(request.content) == first["request"]["json"] for request in sent)
    record.assert_safe()


@pytest.mark.parametrize("mode", ["sync", "async"])
@respx.mock
async def test_streaming_is_rejected_before_io(mode: str) -> None:
    record, transport = Record(), HttpxTransport()
    model = _model(Bedrock("us-east-1"), record, transport)
    try:
        with pytest.raises(UnsupportedFeatureError):
            if mode == "sync":
                list(model.stream(_request()))
            else:
                async for _ in await model.astream(_request()):
                    pass
    finally:
        transport.close()
        await transport.aclose()
    assert record.signings == 0 and not respx.calls


def test_versions_beta_encoded_resource_and_explicit_profile_alias() -> None:
    resource = "arn:aws:bedrock:us-east-1:000000000000:inference-profile/synthetic"
    host = Bedrock(
        "us-east-1",
        beta=("computer-use-2024-10-22",),
        profile_aliases={resource: "claude-opus-4-6"},
    )
    spec = _spec(resource)
    assert host.endpoint(spec).endswith(
        "/model/arn%3Aaws%3Abedrock%3Aus-east-1%3A000000000000%3Ainference-profile%2Fsynthetic/invoke"
    )
    assert host.profile_key(resource) == "claude-opus-4-6"
    assert host.profile_key(RESOURCE) == RESOURCE
    body: dict[str, Any] = {"model": resource, "stream": False, "messages": []}
    assert host.envelope(spec).wrap(body) == {
        "messages": [],
        "anthropic_version": "bedrock-2023-05-31",
        "anthropic_beta": ["computer-use-2024-10-22"],
    }
    assert body == {"model": resource, "stream": False, "messages": []}
    feature = replace(
        spec,
        traits=replace(spec.traits, feature_headers={"anthropic-beta": "computer-use-2024-10-22"}),
    )
    assert "anthropic-beta" not in host.headers(feature)
    assert host.envelope(feature).wrap(body)["anthropic_beta"] == ["computer-use-2024-10-22"]
    with pytest.raises(ValueError, match="conflicting Bedrock"):
        host.envelope(spec).wrap({"model": resource, "anthropic_version": "conflict"})
    with pytest.raises(ValueError, match="model conflicts"):
        host.envelope(spec).wrap({"model": "different"})
    with pytest.raises(ValueError, match="beta declarations"):
        replace(host, beta=("different",)).envelope(feature).wrap(body)
    assert (
        Bedrock("cn-north-1")
        .endpoint(_spec())
        .startswith("https://bedrock-runtime.cn-north-1.amazonaws.com.cn/")
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"guardrail_identifier": "only-id"},
        {"guardrail_config": {}},
        {"static_headers": {"anthropic-version": "wrong"}},
        {"static_headers": {"Authorization": "forbidden"}},
    ],
)
def test_invalid_host_configuration_fails_before_io(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        Bedrock("us-east-1", **kwargs)


@respx.mock
async def test_host_configuration_change_invalidates_approval() -> None:
    record, transport = Record(), HttpxTransport()
    host = Bedrock("us-east-1", static_headers={"x-explicit-routing": "first"})
    model = _model(host, record, transport)
    prepared = model.prepare(_request())
    assert isinstance(host.static_headers, dict)
    host.static_headers["x-explicit-routing"] = "second"
    try:
        with pytest.raises(StalePreparationError):
            prepared.chat()
    finally:
        transport.close()
        await transport.aclose()
    assert record.signings == 0 and not respx.calls


@pytest.mark.parametrize(
    "trace",
    [
        {"guardrail": {"modelOutput": [{"action": "BLOCKED"}]}},
        {
            "guardrail": {
                "input": {
                    "synthetic": {
                        "sensitiveInformationPolicy": {"piiEntities": [{"action": "ANONYMIZED"}]}
                    }
                }
            }
        },
        {"guardrails": {"outputAssessments": {"action": "BLOCKED"}}},
        {"guardrail": {"outputs": [{"synthetic": {"futurePolicy": {"action": "BLOCKED"}}}]}},
    ],
)
def test_unqualified_trace_never_guesses_blocking_or_masking(trace: dict[str, Any]) -> None:
    payload = {"amazon-bedrock-guardrailAction": "INTERVENED", "amazon-bedrock-trace": trace}
    adapted = (
        Bedrock("us-east-1").response_adapter(_spec()).apply(HttpResponse(200, {}, b"{}"), payload)
    )
    assert adapted.error is None and not adapted.violations
    assert [shift.kind for shift in adapted.report.shifts] == ["bedrock.guardrail_intervened"]
    assert adapted.evidence.metadata["body"]["amazon-bedrock-trace"] == trace


def test_host_rejects_unqualified_interface_or_missing_version() -> None:
    host = Bedrock("us-east-1")
    spec = _spec()
    with pytest.raises(UnsupportedFeatureError):
        host.endpoint(replace(spec, dialect=replace(spec.dialect, provider="other")))
    with pytest.raises(UnsupportedFeatureError):
        host.envelope(
            replace(spec, traits=replace(spec.traits, host_body_versions={"bedrock": None}))
        )


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_request_policy_rejection_makes_no_provider_attempt(asynchronous: bool) -> None:
    record, transport = Record(), HttpxTransport()
    policy = FidelityPolicy(forbidden_shifts=frozenset({"relocation"}))
    model = _model(Bedrock("us-east-1"), record, transport, policy)
    try:
        with pytest.raises(FidelityPolicyError):
            if asynchronous:
                await model.achat(_request())
            else:
                model.chat(_request())
    finally:
        transport.close()
        await transport.aclose()
    assert record.signings == 0 and not respx.calls
