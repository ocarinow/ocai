"""Real AWS signer with recorded wire attempts and unchanged runtime contracts."""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from ocai.aws import SigV4Credential
from ocai.core.credentials import CredentialError
from ocai.core.errors import AuthError
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import NodeId
from ocai.core.result import CallContext
from ocai.core.traits import DialectTraits
from ocai.runtime.binding import Binding
from ocai.runtime.decisions import Decision
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.decisions import Retry
from ocai.runtime.drivers import AsyncDriver
from ocai.runtime.drivers import SyncDriver
from ocai.runtime.observe import ObserveEvent
from ocai.runtime.observe import WireExchanged
from ocai.wire.hosting import Custom
from ocai.wire.hosting import EndpointSpec
from ocai.wire.hosting import Operation
from ocai.wire.http import HttpRequest
from ocai.wire.transport import HttpxTransport

PAIR: dict[str, Any] = json.loads(
    (Path(__file__).parent / "http/bedrock_signed_attempts.json").read_text()
)
SPEC = EndpointSpec(
    NodeId("anthropic", "messages", "2023-06-01", CHAT_REQUEST, date(2023, 6, 1)),
    DialectTraits(vendor="anthropic"),
    Operation("chat", "generative"),
    "anthropic.claude-3-haiku-20240307-v1:0",
    "/unused",
)


class RecordingPolicy:
    def __init__(self, retry: bool = False) -> None:
        self.requests: list[HttpRequest] = []
        self.outcomes: list[Outcome] = []
        self.events: list[ObserveEvent] = []
        self.retry = retry

    def on_request(self, request: HttpRequest) -> Decision:
        self.requests.append(request)
        request.headers["X-Test-Policy"] = "allowed"
        return Proceed()

    def on_outcome(self, outcome: Outcome) -> Decision:
        self.outcomes.append(outcome)
        return Retry(after=0) if self.retry and outcome.attempt == 0 else Proceed()

    def on_event(self, event: ObserveEvent) -> None:
        self.events.append(event)

    def assert_safe(self) -> None:
        for request in self.requests:
            assert not {"authorization", "x-amz-security-token", "x-amz-date"}.intersection(
                key.lower() for key in request.headers
            )
        evidence = repr((self.requests, self.outcomes, self.events))
        for key in ("access_key", "secret_key", "session_token"):
            assert PAIR["credentials"][key] not in evidence


def _binding(policy: RecordingPolicy) -> tuple[Binding, HttpxTransport]:
    dates = iter(datetime.fromisoformat(step["date"]) for step in PAIR["attempts"])
    credential = SigV4Credential(**PAIR["credentials"], clock=lambda: next(dates))
    transport = HttpxTransport(provider="bedrock")
    host = Custom(
        "https://bedrock-runtime.us-east-1.amazonaws.com",
        paths={"generative": "/model/{resource}/invoke"},
    )
    return Binding(host, credential, transport), transport


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("retry", ["none", "success", "provider", "transport"])
@respx.mock
async def test_exact_attempt_signatures_and_isolation(asynchronous: bool, retry: str) -> None:
    policy = RecordingPolicy(retry=retry != "none")
    binding, transport = _binding(policy)
    calls: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        index = len(calls)
        calls.append(request)
        assert str(request.url) == PAIR["request"]["url"]
        assert request.content == json.dumps(PAIR["request"]["json"]).encode()
        for key, value in PAIR["attempts"][index]["headers"].items():
            assert request.headers[key] == value
        policy.assert_safe()
        if index == 0 and retry == "transport":
            raise httpx.ConnectError("synthetic failure", request=request)
        response = (
            PAIR["retry_response"] if index == 0 and retry == "provider" else PAIR["response"]
        )
        return httpx.Response(
            response["status"], json=response["json"], headers=response.get("headers", {})
        )

    respx.post(PAIR["request"]["url"]).mock(side_effect=respond)
    ctx = CallContext(call_id="aws-call", tenant="tenant-synthetic")
    try:
        if asynchronous:
            result = await AsyncDriver(binding, policies=[policy], observers=[policy]).execute(
                spec=SPEC, payload=PAIR["request"]["json"], ctx=ctx
            )
        else:
            result = SyncDriver(binding, policies=[policy], observers=[policy]).execute(
                spec=SPEC, payload=PAIR["request"]["json"], ctx=ctx
            )
    finally:
        transport.close()
        await transport.aclose()
    assert result == PAIR["response"]["json"]
    expected_calls = 1 if retry == "none" else 2
    assert len(calls) == len(policy.outcomes) == expected_calls
    assert len({id(request.headers) for request in policy.requests}) == expected_calls
    assert all(request.ctx == ctx for request in policy.requests)
    finished = [event for event in policy.events if isinstance(event, WireExchanged)]
    assert [event.attempt for event in finished] == list(range(expected_calls))
    assert all(event.call_id == "aws-call" for event in policy.events)
    policy.assert_safe()


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_provider_failure_stays_safe(asynchronous: bool) -> None:
    policy = RecordingPolicy()
    binding, transport = _binding(policy)
    respx.post(PAIR["request"]["url"]).respond(
        403,
        headers={"x-amzn-ErrorType": "AccessDeniedException"},
        json={"message": "Synthetic access denied"},
    )
    try:
        with pytest.raises(AuthError):
            if asynchronous:
                await AsyncDriver(binding, policies=[policy], observers=[policy]).execute(
                    spec=SPEC, payload=PAIR["request"]["json"]
                )
            else:
                SyncDriver(binding, policies=[policy], observers=[policy]).execute(
                    spec=SPEC, payload=PAIR["request"]["json"]
                )
    finally:
        transport.close()
        await transport.aclose()
    assert policy.outcomes[0].error is not None
    policy.assert_safe()


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_concurrent_calls_keep_signers_and_contexts_separate(asynchronous: bool) -> None:
    policies = [RecordingPolicy(), RecordingPolicy()]
    bindings = [_binding(policy) for policy in policies]
    dates = [datetime.fromisoformat(PAIR["attempts"][0]["date"])] * 2
    for index, (binding, _) in enumerate(bindings):
        # Separate credentials are explicit; no process-wide SDK session is involved.
        bindings[index] = (
            replace(
                binding,
                credentials=SigV4Credential(
                    f"access-{index}",
                    f"secret-{index}",
                    session_token=f"token-{index}",
                    region="us-east-1",
                    clock=lambda: dates[0],
                ),
            ),
            bindings[index][1],
        )
    signatures: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        signatures.append(request.headers["authorization"])
        for policy in policies:
            policy.assert_safe()
        return httpx.Response(200, json=PAIR["response"]["json"])

    respx.post(PAIR["request"]["url"]).mock(side_effect=respond)
    contexts = [CallContext(call_id=f"aws-{i}", tenant=f"tenant-{i}") for i in range(2)]
    try:
        if asynchronous:
            await asyncio.gather(
                *(
                    AsyncDriver(binding, policies=[policy], observers=[policy]).execute(
                        spec=SPEC, payload=PAIR["request"]["json"], ctx=ctx
                    )
                    for (binding, _), policy, ctx in zip(bindings, policies, contexts, strict=True)
                )
            )
        else:
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(
                        SyncDriver(binding, policies=[policy], observers=[policy]).execute,
                        spec=SPEC,
                        payload=PAIR["request"]["json"],
                        ctx=ctx,
                    )
                    for (binding, _), policy, ctx in zip(bindings, policies, contexts, strict=True)
                ]
                for future in futures:
                    future.result()
    finally:
        for _, transport in bindings:
            transport.close()
            await transport.aclose()
    assert len(set(signatures)) == 2
    for index, policy in enumerate(policies):
        assert policy.requests[0].ctx == contexts[index]
        assert all(event.call_id == f"aws-{index}" for event in policy.events)
        for marker in ("access-", "secret-", "token-"):
            assert marker not in repr((policy.requests, policy.outcomes, policy.events))


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
async def test_signing_failure_prevents_transport(asynchronous: bool) -> None:
    policy = RecordingPolicy()
    binding, transport = _binding(policy)
    binding = replace(
        binding,
        credentials=SigV4Credential(
            "access", "secret", region="us-east-1", clock=lambda: datetime(2026, 1, 1)
        ),
    )
    route = respx.post(PAIR["request"]["url"]).respond(200, json=PAIR["response"]["json"])
    try:
        with pytest.raises(CredentialError):
            if asynchronous:
                await AsyncDriver(binding, policies=[policy], observers=[policy]).execute(
                    spec=SPEC, payload=PAIR["request"]["json"]
                )
            else:
                SyncDriver(binding, policies=[policy], observers=[policy]).execute(
                    spec=SPEC, payload=PAIR["request"]["json"]
                )
    finally:
        transport.close()
        await transport.aclose()
    assert not route.calls and not policy.events
    policy.assert_safe()
