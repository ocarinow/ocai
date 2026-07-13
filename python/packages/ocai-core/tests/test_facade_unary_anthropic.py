"""Facade unary lifecycle for the SECOND provider (WU-14a): the pattern proof.

The done-criterion of this module IS the claim: `chat`/`achat` run end to end
against `anthropic/messages` with **zero changes to `ocai/chat/facade.py`** —
adding a provider is composing values (fragment catalog + `Direct` binding +
`MessagesCodec`), never touching the facade. Pytest cannot assert a diff, so
the guarantee is stated here and verified by the integrator via
`git diff -- python/packages/ocai-core/src/ocai/chat/facade.py` (empty for
this WU by construction).

Mirrors `test_facade_unary.py` over recorded `tests/http/anthropic_*` pairs,
replayed through the REAL `HttpxTransport` via respx (rule 10 — no live keys,
no provider-SDK mocks), plus this dialect's own honest signature moves:

- plain pair → a `CallResult` whose `value` is `semantic_equal` to the
  hand-authored expected canonical, `route.catalog_hash == catalog.lock().
  hash`, a two-leg report (encode + decode edges) carrying the declared
  system RELOCATION shift (the request holds a leading system turn) and the
  required-`max_tokens` EMULATION shift — shifts, never losses;
- tool-call pair → typed `PartToolCall` recovered via the canonical
  `args_json` wire-truth lane (the declared `anthropic.args_serialized`
  shift), `finish.reason == "tool_call"`, and the dimensional usage buckets
  including both cache dimensions (`cache_read_input_tokens` → cached,
  `cache_creation_input_tokens` → the open `anthropic.cache_write` source);
- 529 overloaded → `TransientError` with the codec's `map_error` naming the
  wire condition (`code == "overloaded_error"` — the coarse status layer
  alone carries no code, so this proves the layer-2 refiner is wired);
- 401 → `AuthError` refined from the uniform Anthropic error envelope;
- the §3.4 front door (`ocai.chat.model("anthropic/claude-opus-4-6", ...)`)
  is the identical composition over the same recording — door parity for
  the second provider.

Every `achat` twin runs the identical assertions — the sans-io split means
only the physical send differs.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

import ocai.anthropic
import ocai.chat
from ocai.anthropic.messages import MESSAGES_REQUEST
from ocai.anthropic.messages import MESSAGES_RESPONSE
from ocai.anthropic.messages import MessagesCodec
from ocai.anthropic.messages.codec import ANTHROPIC_BASE_URL
from ocai.anthropic.messages.codec import ANTHROPIC_VERSION
from ocai.anthropic.messages.codec import MESSAGES_PATH
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
from ocai.core.errors import TransientError
from ocai.core.fidelity import ShiftKind
from ocai.core.jsonschema import JsonSchema
from ocai.core.refs import ProviderRef
from ocai.runtime.binding import Binding
from ocai.wire.hosting import Direct
from ocai.wire.transport import HttpxTransport

URL = f"{ANTHROPIC_BASE_URL}{MESSAGES_PATH}"

# One immutable catalog for the whole module: the real composed fragment,
# exactly what an application would build. Its lock hash must land in every
# Route the facade returns.
CATALOG = Catalog.of(ocai.anthropic.FRAGMENT)

# The bound resource every recording was minted for.
MODEL = "claude-opus-4-6"


def _credentials() -> ApiKey:
    """Anthropic first-party auth: the bare key on `x-api-key`, no scheme."""
    return ApiKey("sk-ant-test", header="x-api-key", scheme="")


def _model(policies: Any = (), **kwargs: Any) -> WireChatModel:
    """Compose the facade under test: real codec, Direct binding, real catalog.

    The exact `test_facade_unary.py` recipe with only the VALUES swapped —
    codec, binding, catalog — which is the WU-14a pattern proof.
    """
    binding = Binding(
        host=Direct(ANTHROPIC_BASE_URL),
        credentials=_credentials(),
        transport=HttpxTransport(provider="anthropic"),
    )
    return WireChatModel(
        MessagesCodec(),
        binding,
        CATALOG,
        model_name=MODEL,
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
        message=Message.model("I am Claude, an AI assistant."),
        finish=FinishInfo(reason="complete", native="end_turn"),
        usage=Usage(
            consumptions=[
                Consumption(modality="text", unit="tokens", source="input", value=14),
                Consumption(modality="text", unit="tokens", source="output", value=9),
            ]
        ),
        info=ResponseInfo(
            id=ProviderRef(
                provider="anthropic",
                interface="messages",
                kind="response_id",
                id="msg_01XYZ",
            ),
            model=MODEL,
        ),
        raw=raw,
    )


def _expected_tool_call(raw: dict[str, Any]) -> ChatResponse:
    return ChatResponse(
        message=Message(
            role="model",
            parts=[
                PartToolCall(
                    call_id="toolu_01A2B3C4",
                    name="get_weather",
                    args_json='{"city": "Paris"}',
                    status="input_complete",
                    executed_by="client",
                )
            ],
        ),
        finish=FinishInfo(reason="tool_call", native="tool_use"),
        usage=Usage(
            consumptions=[
                Consumption(modality="text", unit="tokens", source="input", value=55),
                Consumption(modality="text", unit="tokens", source="output", value=17),
                Consumption(modality="text", unit="tokens", source="cached", value=10),
                Consumption(
                    modality="text", unit="tokens", source="anthropic.cache_write", value=4
                ),
            ]
        ),
        info=ResponseInfo(
            id=ProviderRef(
                provider="anthropic",
                interface="messages",
                kind="response_id",
                id="msg_01TOOL",
            ),
            model=MODEL,
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
    """The WU-07 done-criteria, replayed verbatim on the second provider."""
    # The value is semantically the hand-authored canonical.
    assert semantic_equal(res.value, expected), (
        f"decoded value != expected canonical\n"
        f"  expected: {canonical(expected)}\n"
        f"  actual:   {canonical(res.value)}"
    )
    # The route records the resolution under THIS catalog, host-stamped.
    assert res.route is not None
    assert res.route.node == MESSAGES_REQUEST
    assert res.route.catalog_hash == CATALOG.lock().hash
    assert res.route.host == URL
    # The report spans both legs, in traversal order.
    assert res.report is not None
    assert [(e.src, e.dst) for e in res.report.edges] == [
        (CANONICAL_CHAT_REQUEST, MESSAGES_REQUEST),
        (MESSAGES_RESPONSE, CANONICAL_CHAT_RESPONSE),
    ]
    # Usage matches the recording, through the ergonomic accessor.
    assert res.usage is not None
    assert res.usage.input_tokens == input_tokens
    # Raw rides untouched, and the value's raw lane is the same object.
    assert res.raw == pair["response"]["json"]
    assert res.value.raw is res.raw
    # What went over the wire: the recorded body (model injected via
    # bind_resource, below the graph), the bare x-api-key credential applied
    # at the leaf (never a Bearer scheme), and the anthropic-version header
    # composed by the Direct host from the dialect's declared traits.
    assert json.loads(sent.content) == pair["request"]["json"]
    assert sent.headers["x-api-key"] == "sk-ant-test"
    assert "authorization" not in sent.headers
    assert sent.headers["anthropic-version"] == ANTHROPIC_VERSION
    assert sent.url == pair["request"]["url"]


# --- (a) plain pair -------------------------------------------------------------


@respx.mock
def test_chat_plain_pair(load_http) -> None:
    pair = load_http("anthropic_messages.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    res = _model().chat(_plain_request())

    _assert_call_result(
        res,
        pair=pair,
        expected=_expected_plain(pair["response"]["json"]),
        input_tokens=14,
        sent=route.calls.last.request,
    )
    # Data-exact but semantically moved: the leading system turn relocated to
    # the top-level `system` field and the wire-required `max_tokens` got the
    # injected default — both declared SHIFTS on the request leg, never
    # losses, so the report is honestly lossless AND honestly shifted.
    assert res.report.lossless
    assert res.report.losses == []
    assert [(s.kind, s.path) for s in res.report.shifts] == [
        (ShiftKind.RELOCATION, "messages[0]"),
        (ShiftKind.EMULATION, "config.max_output_tokens"),
    ]


@respx.mock
async def test_achat_plain_pair(load_http) -> None:
    pair = load_http("anthropic_messages.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    res = await _model().achat(_plain_request())

    _assert_call_result(
        res,
        pair=pair,
        expected=_expected_plain(pair["response"]["json"]),
        input_tokens=14,
        sent=route.calls.last.request,
    )
    assert res.report.lossless
    assert [s.kind for s in res.report.shifts] == [ShiftKind.RELOCATION, ShiftKind.EMULATION]


# --- (b) tool-call pair ---------------------------------------------------------


@respx.mock
def test_chat_tool_call_pair(load_http) -> None:
    pair = load_http("anthropic_messages_tool_call.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    res = _model().chat(_tool_request())

    _assert_call_result(
        res,
        pair=pair,
        expected=_expected_tool_call(pair["response"]["json"]),
        input_tokens=55,
        sent=route.calls.last.request,
    )
    # The decode leg records the wire `input` object serializing to the
    # canonical args_json wire-truth lane as this dialect's plugin-minted
    # shift (never a loss); the request leg carries only the max_tokens
    # emulation (no system turn here).
    assert res.report.lossless
    assert res.report.losses == []
    assert [(s.kind, s.path) for s in res.report.shifts] == [
        (ShiftKind.EMULATION, "config.max_output_tokens"),
        ("anthropic.args_serialized", "content[0].input"),
    ]
    assert res.value.finish is not None
    assert res.value.finish.reason == "tool_call"
    call = res.value.message.parts[0]
    assert isinstance(call, PartToolCall)
    assert call.args() == {"city": "Paris"}
    # The dimensional usage buckets, disjoint per the WU-13 decision:
    # cache_read -> the canonical cached bucket, cache_creation -> the open
    # `anthropic.cache_write` source, and total stays a plain sum.
    assert res.usage.input_tokens == 55
    assert res.usage.output_tokens == 17
    assert res.usage.cached_input_tokens == 10
    cache_writes = [c for c in res.usage.consumptions if c.source == "anthropic.cache_write"]
    assert [c.value for c in cache_writes] == [4]
    assert res.usage.total_tokens == 55 + 17 + 10 + 4


@respx.mock
async def test_achat_tool_call_pair(load_http) -> None:
    pair = load_http("anthropic_messages_tool_call.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    res = await _model().achat(_tool_request())

    _assert_call_result(
        res,
        pair=pair,
        expected=_expected_tool_call(pair["response"]["json"]),
        input_tokens=55,
        sent=route.calls.last.request,
    )


# --- (c) errors: the uniform envelope refined via map_error ---------------------


@respx.mock
def test_chat_refines_529_overloaded_to_transient_error(load_http) -> None:
    # A 529 is coarsely transient by status alone, but the coarse error
    # carries no code: `code == "overloaded_error"` proves the codec's
    # body-aware map_error (layer 2) actually ran through the facade.
    pair = load_http("anthropic_messages_overloaded_error.json")
    respx.post(URL).mock(
        return_value=httpx.Response(pair["response"]["status"], json=pair["response"]["json"])
    )

    with pytest.raises(TransientError) as exc:
        _model().chat(_plain_request())
    assert exc.value.status == 529
    assert exc.value.code == "overloaded_error"
    assert exc.value.provider == "anthropic"
    # The provider's parsed error body rides `raw` — never a header, never a
    # key — and the refined error chains the coarse one (`raise ... from`).
    assert exc.value.raw == pair["response"]["json"]
    assert exc.value.__cause__ is not None


@respx.mock
async def test_achat_refines_529_overloaded_to_transient_error(load_http) -> None:
    pair = load_http("anthropic_messages_overloaded_error.json")
    respx.post(URL).mock(
        return_value=httpx.Response(pair["response"]["status"], json=pair["response"]["json"])
    )

    with pytest.raises(TransientError) as exc:
        await _model().achat(_plain_request())
    assert exc.value.code == "overloaded_error"


@respx.mock
def test_chat_maps_401_to_auth_error(load_http) -> None:
    pair = load_http("anthropic_messages_auth_error.json")
    respx.post(URL).mock(
        return_value=httpx.Response(pair["response"]["status"], json=pair["response"]["json"])
    )

    with pytest.raises(AuthError) as exc:
        _model().chat(_plain_request())
    assert exc.value.status == 401
    # error.type is the authoritative classifier on this wire; the refiner
    # carried it as the machine-readable code.
    assert exc.value.code == "authentication_error"
    assert exc.value.raw == pair["response"]["json"]


@respx.mock
async def test_achat_maps_401_to_auth_error(load_http) -> None:
    pair = load_http("anthropic_messages_auth_error.json")
    respx.post(URL).mock(
        return_value=httpx.Response(pair["response"]["status"], json=pair["response"]["json"])
    )

    with pytest.raises(AuthError) as exc:
        await _model().achat(_plain_request())
    assert exc.value.status == 401


# --- (e) the front door composes the same model over the same recording ---------


@respx.mock
def test_front_door_spec_string_is_the_same_composition(load_http) -> None:
    pair = load_http("anthropic_messages.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    hand_built = _model()
    door = ocai.chat.model(
        f"anthropic/{MODEL}",
        credentials=_credentials(),
        catalog=CATALOG,
    )

    # Identical composition, before any call.
    assert door.details == hand_built.details

    door_res = door.chat(_plain_request())
    door_sent = json.loads(route.calls.last.request.content)
    hand_res = hand_built.chat(_plain_request())
    hand_sent = json.loads(route.calls.last.request.content)

    # Same wire bytes, same route coordinates, same decoded canonical value.
    assert door_sent == hand_sent == pair["request"]["json"]
    assert door_res.route.node == hand_res.route.node == MESSAGES_REQUEST
    assert door_res.route.host == hand_res.route.host == URL
    assert door_res.route.catalog_hash == CATALOG.lock().hash
    assert semantic_equal(door_res.value, hand_res.value)
    # The door's Direct host came from the fragment's declared traits — the
    # required anthropic-version header rode along without a plugin import.
    assert route.calls.last.request.headers["anthropic-version"] == ANTHROPIC_VERSION


@respx.mock
async def test_front_door_async_twin(load_http) -> None:
    pair = load_http("anthropic_messages.json")
    respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    door = ocai.chat.model(f"anthropic/{MODEL}", credentials=_credentials(), catalog=CATALOG)
    res = await door.achat(_plain_request())

    assert semantic_equal(res.value, _expected_plain(pair["response"]["json"]))
    assert res.route.host == URL


# --- Composition description ------------------------------------------------------


def test_details_names_the_composition() -> None:
    details = _model().details
    assert details["provider"] == "anthropic"
    assert details["interface"] == "messages"
    assert details["model_name"] == MODEL
