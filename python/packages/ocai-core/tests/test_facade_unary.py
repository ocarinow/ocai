"""Facade unary lifecycle (WU-07): `WireChatModel.chat`/`achat`, end to end.

The §8 assembly proven over the real wire path: recorded request/response
pairs from `tests/http/` are replayed through the REAL `HttpxTransport` via
respx (rule 10 — no live keys, no provider-SDK mocks), beneath a facade
composed of the real `ocai.openai.FRAGMENT` catalog, a `Direct` first-party
binding, and the `ChatCompletionsCodec`:

- plain pair → a `CallResult` whose `value` is `semantic_equal` to the
  hand-authored expected canonical, `route.catalog_hash == catalog.lock().
  hash`, a two-leg report (encode + decode edges), `usage.input_tokens`
  matching the recording, and `raw` untouched;
- tool-call pair → typed `PartToolCall` value, the decode leg's EXACT
  tool-call record, `finish.reason == "tool_call"`;
- 429-then-200 → `RetryPolicy` end to end through the facade (two wire
  attempts, then the normal result);
- 401 → `AuthError` through the two-layer mapping (`map_error` defers to
  the coarse status classification);
- 400 context overflow → `ContextLengthError`, which ONLY the codec's
  body-aware `map_error` can produce (the status alone says nothing) —
  proof the layer-2 refiner is actually wired.

Every `achat` twin runs the identical assertions — the sans-io split means
only the physical send differs.
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import Any

import httpx
import pytest
import respx

import ocai.openai
from ocai.chat import CANONICAL_CHAT_REQUEST
from ocai.chat import CANONICAL_CHAT_RESPONSE
from ocai.chat import WireChatModel
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import Consumption
from ocai.chat.types import FinishInfo
from ocai.chat.types import Message
from ocai.chat.types import PartToolCall
from ocai.chat.types import ResponseInfo
from ocai.chat.types import Tool
from ocai.chat.types import ToolChoice
from ocai.chat.types import Usage
from ocai.convert.catalog import Catalog
from ocai.core import ApiKey
from ocai.core.canonjson import canonical
from ocai.core.canonjson import semantic_equal
from ocai.core.errors import AuthError
from ocai.core.errors import ContextLengthError
from ocai.core.jsonschema import JsonSchema
from ocai.core.refs import ProviderRef
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_PATH
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_REQUEST
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_RESPONSE
from ocai.openai.chat_completions.codec import OPENAI_BASE_URL
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.runtime.binding import Binding
from ocai.runtime.binding import CompositionError
from ocai.wire.hosting import Direct
from ocai.wire.policies import RetryPolicy
from ocai.wire.transport import HttpxTransport

URL = f"{OPENAI_BASE_URL}{CHAT_COMPLETIONS_PATH}"

# One immutable catalog for the whole module: the real composed fragment,
# exactly what an application would build. Its lock hash must land in every
# Route the facade returns.
CATALOG = Catalog.of(ocai.openai.FRAGMENT)


def _model(policies: Any = (), **kwargs: Any) -> WireChatModel:
    """Compose the facade under test: real codec, Direct binding, real catalog."""
    binding = Binding(
        host=Direct(OPENAI_BASE_URL),
        credentials=ApiKey("sk-test"),
        transport=HttpxTransport(provider="openai"),
    )
    return WireChatModel(
        ChatCompletionsCodec(),
        binding,
        CATALOG,
        model_name="gpt-4o",
        policies=policies,
        **kwargs,
    )


# --- The canonical requests the recordings were minted from --------------------


def _plain_request() -> ChatRequest:
    return ChatRequest(
        messages=[Message.system("You are concise."), Message.user("Hello, who are you?")]
    )


def _tool_request() -> ChatRequest:
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


# --- Hand-authored expected canonicals (independent of the decode path) --------


def _expected_plain(raw: dict[str, Any]) -> ChatResponse:
    return ChatResponse(
        message=Message.model("I am an AI assistant."),
        finish=FinishInfo(reason="complete", native="stop"),
        usage=Usage(
            consumptions=[
                Consumption(modality="text", unit="tokens", source="input", value=18),
                Consumption(modality="text", unit="tokens", source="output", value=6),
            ]
        ),
        info=ResponseInfo(
            id=ProviderRef(
                provider="openai",
                interface="chat_completions",
                kind="response_id",
                id="chatcmpl-abc123",
            ),
            model="gpt-4o",
            created=datetime.fromtimestamp(1700000000, tz=UTC),
        ),
        raw=raw,
    )


def _expected_tool_call(raw: dict[str, Any]) -> ChatResponse:
    return ChatResponse(
        message=Message(
            role="model",
            parts=[
                PartToolCall(
                    call_id="call_u7Xw1QyLp0",
                    name="get_weather",
                    args_json='{"city":"Paris"}',
                    status="input_complete",
                    executed_by="client",
                )
            ],
        ),
        finish=FinishInfo(reason="tool_call", native="tool_calls"),
        usage=Usage(
            consumptions=[
                Consumption(modality="text", unit="tokens", source="input", value=55),
                Consumption(modality="text", unit="tokens", source="output", value=17),
                Consumption(modality="text", unit="tokens", source="cached", value=0),
                Consumption(modality="text", unit="tokens", source="reasoning", value=0),
            ]
        ),
        info=ResponseInfo(
            id=ProviderRef(
                provider="openai",
                interface="chat_completions",
                kind="response_id",
                id="chatcmpl-tool123",
            ),
            model="gpt-4o",
            created=datetime.fromtimestamp(1700000060, tz=UTC),
        ),
        raw=raw,
    )


# --- Shared assertion body (chat and achat must be indistinguishable) ----------


def _assert_call_result(
    res: Any,
    *,
    pair: dict[str, Any],
    expected: ChatResponse,
    input_tokens: int,
    sent: httpx.Request,
) -> None:
    """The WU-07 done-criteria, asserted identically for both twins."""
    import json

    # The value is semantically the hand-authored canonical.
    assert semantic_equal(res.value, expected), (
        f"decoded value != expected canonical\n"
        f"  expected: {canonical(expected)}\n"
        f"  actual:   {canonical(res.value)}"
    )
    # The route records the resolution under THIS catalog, host-stamped.
    assert res.route is not None
    assert res.route.node == CHAT_COMPLETIONS_REQUEST
    assert res.route.catalog_hash == CATALOG.lock().hash
    assert res.route.host == URL
    # The report spans both legs, in traversal order.
    assert res.report is not None
    assert [(e.src, e.dst) for e in res.report.edges] == [
        (CANONICAL_CHAT_REQUEST, CHAT_COMPLETIONS_REQUEST),
        (CHAT_COMPLETIONS_RESPONSE, CANONICAL_CHAT_RESPONSE),
    ]
    # Usage matches the recording, through the ergonomic accessor.
    assert res.usage is not None
    assert res.usage.input_tokens == input_tokens
    # Raw rides untouched, and the value's raw lane is the same object.
    assert res.raw == pair["response"]["json"]
    assert res.value.raw is res.raw
    # What went over the wire: the recorded body (model injected via
    # bind_resource, below the graph) with the credential applied at the leaf.
    assert json.loads(sent.content) == pair["request"]["json"]
    assert sent.headers["authorization"] == "Bearer sk-test"
    assert sent.url == pair["request"]["url"]


# --- (a) plain pair -------------------------------------------------------------


@respx.mock
def test_chat_plain_pair(load_http) -> None:
    pair = load_http("openai_chat_completion.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    res = _model().chat(_plain_request())

    _assert_call_result(
        res,
        pair=pair,
        expected=_expected_plain(pair["response"]["json"]),
        input_tokens=18,
        sent=route.calls.last.request,
    )
    # This particular conversion is honestly lossless, and says so.
    assert res.report.lossless
    assert res.report.losses == []


@respx.mock
async def test_achat_plain_pair(load_http) -> None:
    pair = load_http("openai_chat_completion.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    res = await _model().achat(_plain_request())

    _assert_call_result(
        res,
        pair=pair,
        expected=_expected_plain(pair["response"]["json"]),
        input_tokens=18,
        sent=route.calls.last.request,
    )
    assert res.report.lossless


# --- (b) tool-call pair ---------------------------------------------------------


@respx.mock
def test_chat_tool_call_pair(load_http) -> None:
    pair = load_http("openai_chat_completion_tool_call.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    res = _model().chat(_tool_request())

    _assert_call_result(
        res,
        pair=pair,
        expected=_expected_tool_call(pair["response"]["json"]),
        input_tokens=55,
        sent=route.calls.last.request,
    )
    # The decode leg records the typed tool-call mapping (EXACT — recorded,
    # not lossy) and the finish decodes to the canonical open code with the
    # native lane verbatim.
    assert [(loss.path, loss.disposition.value) for loss in res.report.losses] == [
        ("choices[0].message.tool_calls[0]", "exact")
    ]
    assert res.report.lossless
    assert res.value.finish is not None
    assert res.value.finish.reason == "tool_call"
    call = res.value.message.parts[0]
    assert isinstance(call, PartToolCall)
    assert call.args() == {"city": "Paris"}


@respx.mock
async def test_achat_tool_call_pair(load_http) -> None:
    pair = load_http("openai_chat_completion_tool_call.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    res = await _model().achat(_tool_request())

    _assert_call_result(
        res,
        pair=pair,
        expected=_expected_tool_call(pair["response"]["json"]),
        input_tokens=55,
        sent=route.calls.last.request,
    )


# --- (c) 429-then-200: RetryPolicy end to end -----------------------------------


def _retry_responses(pair: dict[str, Any]) -> list[httpx.Response]:
    return [
        httpx.Response(
            attempt["status"],
            headers=attempt.get("headers"),
            json=attempt["json"],
        )
        for attempt in pair["responses"]
    ]


@respx.mock
def test_chat_retries_through_a_429_then_succeeds(load_http) -> None:
    pair = load_http("openai_chat_completion_retry.json")
    route = respx.post(URL).mock(side_effect=_retry_responses(pair))

    res = _model(policies=(RetryPolicy(attempts=3, base_delay=0.0),)).chat(_plain_request())

    # Two physical attempts: the 429 judged by the policy, then the success.
    assert route.call_count == 2
    expected = _expected_plain(pair["responses"][1]["json"])
    assert semantic_equal(res.value, expected)
    assert res.usage.input_tokens == 18
    assert res.route.catalog_hash == CATALOG.lock().hash


@respx.mock
async def test_achat_retries_through_a_429_then_succeeds(load_http) -> None:
    pair = load_http("openai_chat_completion_retry.json")
    route = respx.post(URL).mock(side_effect=_retry_responses(pair))

    model = _model(policies=(RetryPolicy(attempts=3, base_delay=0.0),))
    res = await model.achat(_plain_request())

    assert route.call_count == 2
    assert semantic_equal(res.value, _expected_plain(pair["responses"][1]["json"]))


@respx.mock
def test_chat_without_a_retry_policy_raises_the_429(load_http) -> None:
    pair = load_http("openai_chat_completion_retry.json")
    respx.post(URL).mock(side_effect=_retry_responses(pair))

    from ocai.core import RateLimitError

    with pytest.raises(RateLimitError):
        _model().chat(_plain_request())


# --- (d) 401 → AuthError; 400 overflow → ContextLengthError via map_error -------


@respx.mock
def test_chat_maps_401_to_auth_error(load_http) -> None:
    pair = load_http("openai_chat_completion_auth_error.json")
    respx.post(URL).mock(
        return_value=httpx.Response(pair["response"]["status"], json=pair["response"]["json"])
    )

    with pytest.raises(AuthError) as exc:
        _model().chat(_plain_request())
    assert exc.value.status == 401
    # The provider's parsed error body rides `raw` — never a header, never a key.
    assert exc.value.raw == pair["response"]["json"]


@respx.mock
async def test_achat_maps_401_to_auth_error(load_http) -> None:
    pair = load_http("openai_chat_completion_auth_error.json")
    respx.post(URL).mock(
        return_value=httpx.Response(pair["response"]["status"], json=pair["response"]["json"])
    )

    with pytest.raises(AuthError) as exc:
        await _model().achat(_plain_request())
    assert exc.value.status == 401


@respx.mock
def test_chat_refines_400_overflow_to_context_length_error(load_http) -> None:
    # A context overflow is a 400 on this wire: layer 1 (status) alone would
    # raise a plain OcaiError; only the codec's map_error can name it. This
    # is the proof the facade actually wires refine_error into the driver.
    pair = load_http("openai_chat_completion_context_length.json")
    respx.post(URL).mock(
        return_value=httpx.Response(pair["response"]["status"], json=pair["response"]["json"])
    )

    with pytest.raises(ContextLengthError) as exc:
        _model().chat(_plain_request())
    assert exc.value.code == "context_length_exceeded"
    # The refined error chains the coarse one (`raise refined from coarse`).
    assert exc.value.__cause__ is not None


@respx.mock
async def test_achat_refines_400_overflow_to_context_length_error(load_http) -> None:
    pair = load_http("openai_chat_completion_context_length.json")
    respx.post(URL).mock(
        return_value=httpx.Response(pair["response"]["status"], json=pair["response"]["json"])
    )

    with pytest.raises(ContextLengthError):
        await _model().achat(_plain_request())


# --- Composition honesty: a mismatched interface pin cannot send ----------------


def test_mismatched_interface_pin_raises_composition_error() -> None:
    # The catalog resolves the pin, but this facade is composed with the
    # chat_completions codec — sending /responses wire with it would be a
    # silent lie, so the facade refuses at the seam.
    model = _model(interface="responses")
    with pytest.raises(CompositionError):
        model.chat(_plain_request())


def test_details_names_the_composition() -> None:
    details = _model().details
    assert details["provider"] == "openai"
    assert details["interface"] == "chat_completions"
    assert details["model_name"] == "gpt-4o"
