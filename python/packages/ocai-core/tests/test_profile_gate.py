"""The profile gate (WU-12): declared capability facts, consulted pre-encode.

Three tiers, bottom-up:

1. **Vocabulary** — `CapabilityProfile.matches` (fnmatch semantics, case
   sensitivity, character classes), `check_feature` (declared facts, the
   normative undeclared→NATIVE policy, the pattern-mismatch refusal), and
   `resolve_support` (specificity layering: the first profile declaring a
   key wins, a silent specific sheet never masks the wide sheet).
2. **Catalog lookup** — `Catalog.profiles_for` filters by
   `(provider, interface)` + pattern match and ranks most-specific-first
   over the REAL composed plugin fragments; `Catalog.profile` is its head.
3. **The facade gate** — over a recorded pair (rule 10): `temperature` on a
   `gpt-5*` reasoning model raises `UnsupportedFeatureError` in strict mode
   BEFORE encode (proven: the catalog's `convert` is never called and respx
   sees zero wire attempts) and, in annotate mode, records the
   `UNSUPPORTED` field loss as a gate leg ahead of the encode leg while the
   payload goes out verbatim — never stripped, never clamped.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

import ocai.anthropic
import ocai.openai
from ocai.chat import CANONICAL_CHAT_REQUEST
from ocai.chat import CANONICAL_CHAT_RESPONSE
from ocai.chat import WireChatModel
from ocai.chat.facade import _request_features
from ocai.chat.types import ChatConfig
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.chat.types import OutputFormat
from ocai.chat.types import PartImage
from ocai.chat.types import PartReasoning
from ocai.chat.types import ReasoningConfig
from ocai.chat.types import Tool
from ocai.convert.catalog import Catalog
from ocai.core import ApiKey
from ocai.core import SourceUrl
from ocai.core.errors import UnsupportedFeatureError
from ocai.core.jsonschema import JsonSchema
from ocai.core.profile import CapabilityProfile
from ocai.core.profile import Support
from ocai.core.profile import resolve_support
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_PATH
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_REQUEST
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_RESPONSE
from ocai.openai.chat_completions.codec import OPENAI_BASE_URL
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.runtime.binding import Binding
from ocai.wire.hosting import Direct
from ocai.wire.transport import HttpxTransport

URL = f"{OPENAI_BASE_URL}{CHAT_COMPLETIONS_PATH}"

# The real composed fragments — the facts under test are the plugins' own.
CATALOG = Catalog.of(ocai.openai.FRAGMENT, ocai.anthropic.FRAGMENT)


# --- 1a. matches(): fnmatch semantics over model_pattern -----------------------


@pytest.mark.parametrize(
    ("pattern", "model", "expected"),
    [
        ("*", "anything-at-all", True),
        ("gpt-5*", "gpt-5", True),
        ("gpt-5*", "gpt-5.2-mini", True),
        ("gpt-5*", "gpt-4o", False),
        ("gpt-5*", "GPT-5", False),  # fnmatchcase: model names are case-sensitive
        ("o*", "o3-mini", True),
        ("o*", "gpt-4o", False),  # prefix, not substring
        ("claude-opus-4-[678]*", "claude-opus-4-8", True),
        ("claude-opus-4-[678]*", "claude-opus-4-6-20260210", True),
        ("claude-opus-4-[678]*", "claude-opus-4-5", False),
        ("gpt-4o", "gpt-4o", True),  # fully literal pattern
        ("gpt-4o", "gpt-4o-mini", False),
    ],
)
def test_matches_model_patterns(pattern: str, model: str, expected: bool) -> None:
    profile = CapabilityProfile(provider="p", interface="i", model_pattern=pattern)
    assert profile.matches(model) is expected


# --- 1b. check_feature(): declared facts + the undeclared policy ---------------


_SHEET = CapabilityProfile(
    provider="openai",
    interface="chat_completions",
    model_pattern="gpt-5*",
    features={"chat.config.temperature": Support.ABSENT},
)


def test_check_feature_returns_the_declared_fact() -> None:
    assert _SHEET.check_feature("chat.config.temperature", "gpt-5") is Support.ABSENT


def test_check_feature_undeclared_defaults_to_native() -> None:
    # The normative policy: profiles declare EXCEPTIONS; the absence of a
    # declared limitation is not a limitation (keys are open data — no
    # profile could ever enumerate the whole feature universe).
    assert _SHEET.check_feature("chat.config.never_heard_of", "gpt-5") is Support.NATIVE


def test_check_feature_refuses_a_model_outside_the_pattern() -> None:
    with pytest.raises(LookupError):
        _SHEET.check_feature("chat.config.temperature", "gpt-4o")


# --- 1c. resolve_support(): specificity layering --------------------------------


_WIDE = CapabilityProfile(
    provider="openai",
    interface="chat_completions",
    model_pattern="*",
    features={
        "chat.config.temperature": Support.NATIVE,
        "chat.config.top_k": Support.ABSENT,
    },
)


def test_resolve_support_first_declaration_wins() -> None:
    assert resolve_support([_SHEET, _WIDE], "chat.config.temperature") is Support.ABSENT


def test_resolve_support_silent_specific_sheet_never_masks_the_wide_one() -> None:
    # The gpt-5* sheet says nothing about top_k; the "*" sheet's ABSENT
    # must shine through the layering.
    assert resolve_support([_SHEET, _WIDE], "chat.config.top_k") is Support.ABSENT


def test_resolve_support_undeclared_everywhere_is_native() -> None:
    assert resolve_support([_SHEET, _WIDE], "chat.parts.telepathy") is Support.NATIVE
    assert resolve_support([], "chat.config.temperature") is Support.NATIVE


# --- 2. Catalog.profiles_for / Catalog.profile over the real fragments ----------


def test_profiles_for_ranks_most_specific_first() -> None:
    assert [
        p.model_pattern for p in CATALOG.profiles_for("openai", "chat_completions", "gpt-5.2")
    ] == ["gpt-5*", "*"]
    assert [
        p.model_pattern for p in CATALOG.profiles_for("openai", "chat_completions", "o3-mini")
    ] == ["o*", "*"]
    assert [
        p.model_pattern for p in CATALOG.profiles_for("anthropic", "messages", "claude-opus-4-8")
    ] == ["claude-opus-4-[678]*", "*"]


def test_profiles_for_filters_by_provider_interface_and_model() -> None:
    # A non-reasoning model sees only the interface-wide sheet.
    assert [
        p.model_pattern for p in CATALOG.profiles_for("openai", "chat_completions", "gpt-4o")
    ] == ["*"]
    # The /responses interface ships no profiles yet; unknown providers none.
    assert CATALOG.profiles_for("openai", "responses", "gpt-5") == ()
    assert CATALOG.profiles_for("acme", "chat", "gpt-5") == ()


def test_profile_returns_the_ranking_head_or_none() -> None:
    best = CATALOG.profile("openai", "chat_completions", "gpt-5")
    assert best is not None
    assert best.model_pattern == "gpt-5*"
    assert CATALOG.profile("acme", "chat", "gpt-5") is None


def test_anthropic_temperature_census_for_the_newest_models() -> None:
    # The opus-4-6..4-8 lines reject temperature outright; top_p stays
    # NATIVE via the "*" sheet (the temperature/top_p mutual exclusion is a
    # cross-knob constraint the per-feature gate deliberately leaves to the
    # wire).
    newest = CATALOG.profiles_for("anthropic", "messages", "claude-opus-4-8")
    assert resolve_support(newest, "chat.config.temperature") is Support.ABSENT
    assert resolve_support(newest, "chat.config.top_p") is Support.NATIVE
    older = CATALOG.profiles_for("anthropic", "messages", "claude-sonnet-4-5")
    assert resolve_support(older, "chat.config.temperature") is Support.NATIVE


# --- 3a. _request_features: the gate's census of one request --------------------


def test_request_features_derives_keys_and_paths() -> None:
    request = ChatRequest(
        messages=[
            Message.user(["look at this", PartImage(source=SourceUrl(url="https://x/y.png"))]),
            Message(role="model", parts=[PartReasoning(text="thinking...")]),
        ],
        tools=[Tool(name="t", parameters=JsonSchema.from_dict({"type": "object"}))],
        config=ChatConfig(
            temperature=0.5,
            top_k=40,
            reasoning=ReasoningConfig(effort="high"),
            output=OutputFormat(mode="json_schema", schema=JsonSchema.from_dict({})),
        ),
    )
    features = _request_features(request)
    assert ("chat.config.temperature", "config.temperature") in features
    assert ("chat.config.top_k", "config.top_k") in features
    assert ("chat.config.reasoning.effort", "config.reasoning.effort") in features
    assert ("chat.config.output.json_schema", "config.output") in features
    assert ("chat.tools", "tools") in features
    assert ("chat.parts.image", "messages[0].parts[1]") in features
    assert ("chat.parts.reasoning.replay", "messages[1].parts[0]") in features
    # Unset knobs and plain text parts contribute nothing.
    assert not any(feature == "chat.config.top_p" for feature, _ in features)


def test_request_features_empty_for_a_bare_request() -> None:
    assert _request_features(ChatRequest(messages=[Message.user("hi")])) == ()


# --- 3b. The facade gate over a recorded pair -----------------------------------


class _SpyCatalog:
    """A delegating catalog wrapper recording every `convert` call."""

    def __init__(self, inner: Catalog) -> None:
        self._inner = inner
        self.convert_calls: list[tuple[Any, Any]] = []

    def convert(self, payload: Any, src: Any, dst: Any) -> Any:
        self.convert_calls.append((src, dst))
        return self._inner.convert(payload, src, dst)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def _model(*, model_name: str, strict: bool, catalog: Any = CATALOG) -> WireChatModel:
    binding = Binding(
        host=Direct(OPENAI_BASE_URL),
        credentials=ApiKey("sk-test"),
        transport=HttpxTransport(provider="openai"),
    )
    return WireChatModel(
        ChatCompletionsCodec(),
        binding,
        catalog,
        model_name=model_name,
        strict=strict,
    )


def _temperature_request() -> ChatRequest:
    return ChatRequest(
        messages=[Message.user("Hello, who are you?")],
        config=ChatConfig(temperature=0.2),
    )


@respx.mock
def test_strict_gate_refuses_before_encode_and_before_the_wire(load_http) -> None:
    pair = load_http("openai_chat_completion_reasoning.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))
    spy = _SpyCatalog(CATALOG)

    with pytest.raises(UnsupportedFeatureError) as exc:
        _model(model_name="gpt-5", strict=True, catalog=spy).chat(_temperature_request())

    # The typed refusal names the feature and the bound model.
    assert exc.value.features == ("chat.config.temperature",)
    assert exc.value.model == "gpt-5"
    assert exc.value.provider == "openai"
    assert "chat.config.temperature" in str(exc.value)
    assert "gpt-5" in str(exc.value)
    # Gate-before-encode, proven twice over: the graph never converted the
    # request, and nothing touched the wire.
    assert spy.convert_calls == []
    assert route.call_count == 0


@respx.mock
async def test_strict_gate_refuses_in_the_async_twin_too(load_http) -> None:
    pair = load_http("openai_chat_completion_reasoning.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    with pytest.raises(UnsupportedFeatureError):
        await _model(model_name="gpt-5", strict=True).achat(_temperature_request())
    assert route.call_count == 0


@respx.mock
def test_annotate_gate_records_the_loss_and_sends_verbatim(load_http) -> None:
    pair = load_http("openai_chat_completion_reasoning.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    res = _model(model_name="gpt-5", strict=False).chat(_temperature_request())

    # The gate leg leads the report, ahead of the encode leg, then decode.
    assert [(e.src, e.dst) for e in res.report.edges] == [
        (CANONICAL_CHAT_REQUEST, CHAT_COMPLETIONS_REQUEST),  # feature gate
        (CANONICAL_CHAT_REQUEST, CHAT_COMPLETIONS_REQUEST),  # encode
        (CHAT_COMPLETIONS_RESPONSE, CANONICAL_CHAT_RESPONSE),  # decode
    ]
    assert res.report.edges[0].note == "feature gate (pre-encode)"
    # The ABSENT feature is an UNSUPPORTED loss anchored on the field set.
    assert [(loss.path, loss.disposition.value) for loss in res.report.losses] == [
        ("config.temperature", "unsupported")
    ]
    assert not res.report.lossless
    assert res.report.dropped[0].path == "config.temperature"
    # The payload went out verbatim — the recorded body, temperature intact,
    # never stripped, never clamped. The provider stays authoritative.
    assert route.call_count == 1
    assert json.loads(route.calls.last.request.content) == pair["request"]["json"]
    # The call itself assembles normally.
    assert res.usage is not None
    assert res.usage.input_tokens == 12
    assert res.raw == pair["response"]["json"]


@respx.mock
def test_gate_is_silent_when_the_profile_declares_support(load_http) -> None:
    # Same knob, non-reasoning model: temperature is NATIVE on the "*"
    # sheet, so no gate leg appears — the report is the plain two-leg one —
    # and strict mode does not bite.
    pair = load_http("openai_chat_completion_reasoning.json")
    respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    res = _model(model_name="gpt-4o", strict=True).chat(_temperature_request())

    assert [(e.src, e.dst) for e in res.report.edges] == [
        (CANONICAL_CHAT_REQUEST, CHAT_COMPLETIONS_REQUEST),
        (CHAT_COMPLETIONS_RESPONSE, CANONICAL_CHAT_RESPONSE),
    ]
    assert res.report.lossless
