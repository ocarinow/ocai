"""DeepSeek's conservative policies, opaque evidence, and usage accounting."""

from copy import deepcopy
from typing import Any

import pytest
import respx

import ocai.deepseek
from ocai.chat.types import ChatRequest
from ocai.chat.types import PartUnknown
from ocai.convert import Catalog
from ocai.convert.conformance import certify_edge
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import FidelityPolicy
from ocai.core.fidelity import FidelityPolicyError
from ocai.core.fidelity import FieldLoss
from ocai.deepseek.chat_completions.codec import DeepSeekCodec
from ocai.deepseek.chat_completions.edges import EDGES
from ocai.deepseek.chat_completions.usage import decode_usage


@pytest.mark.parametrize(
    ("change", "path"),
    [
        ({"seed": 3}, "config.seed"),
        ({"top_p": 0.8}, "config.top_p"),
        ({"parallel_tool_calls": False}, "config.parallel_tool_calls"),
        ({"reasoning": {"include_thoughts": False}}, "config.reasoning.include_thoughts"),
        ({"output": {"mode": "json_schema", "schema": {"type": "object"}}}, "config.output"),
        ({"output": {"mode": "future"}}, "config.output"),
        (
            {"extensions": {"deepseek.request_unmapped": []}},
            "config.extensions[deepseek.request_unmapped]",
        ),
    ],
)
def test_public_policy_rejects_unqualified_intent_without_io(
    change: dict[str, Any],
    path: str,
) -> None:
    request = ChatRequest.from_dict({"messages": [], "config": change})
    edge = EDGES[0]
    with respx.mock as transport:
        converted = Catalog.of(ocai.deepseek.FRAGMENT).convert(request, edge.src, edge.dst)
        assert any(loss.path == path for loss in converted.report.edges[0].losses)
        policy = FidelityPolicy(forbidden_dispositions=frozenset({Disposition.UNSUPPORTED}))
        with pytest.raises(FidelityPolicyError) as caught:
            policy.enforce(converted.report, phase="request")
        assert caught.value.report == converted.report
        assert not transport.calls
    assert certify_edge(edge, [request]) == []


@pytest.mark.parametrize("reasoning", [None, 7, {"future": True}])
def test_raw_message_override_cannot_bypass_required_replay(reasoning: Any) -> None:
    payload: dict[str, Any] = {
        "tools": [{"type": "function", "function": {"name": "lookup", "parameters": {}}}],
        "messages": [{"role": "assistant", "content": "Done.", "reasoning_content": reasoning}],
    }
    request = ChatRequest.from_dict(
        {
            "messages": [],
            "provider_options": {"deepseek.chat_completions": payload},
        }
    )
    out = DeepSeekCodec().encode_request(request)
    assert out.value == payload
    assert any(loss.path.endswith("messages[0].reasoning_content") for loss in out.losses)
    assert certify_edge(EDGES[0], [request]) == []


def test_native_override_effects_and_empty_reasoning_are_explicit() -> None:
    request = ChatRequest.from_dict(
        {
            "messages": [],
            "provider_options": {
                "deepseek.chat_completions": {
                    "thinking": {"type": "enabled"},
                    "reasoning_effort": "none",
                    "temperature": 0.6,
                    "top_p": 0.8,
                    "tools": [{"type": "function", "function": {"name": "lookup"}}],
                    "messages": [
                        {"role": "assistant", "content": "Done.", "reasoning_content": ""}
                    ],
                },
            },
        }
    )
    before = deepcopy(request.to_dict())
    out = DeepSeekCodec().encode_request(request)
    assert request.to_dict() == before
    assert out.value["messages"][0]["reasoning_content"] == ""
    assert {shift.kind for shift in out.shifts} == {
        "deepseek.thinking_override",
        "deepseek.ignored_parameter",
    }
    assert [loss.path for loss in out.losses] == [
        "provider_options[deepseek.chat_completions].top_p",
    ]
    assert certify_edge(EDGES[0], [request]) == []


@pytest.mark.parametrize(
    ("native", "reason"),
    [
        ("stop", "complete"),
        ("length", "max_tokens"),
        ("tool_calls", "tool_call"),
        ("content_filter", "content_filter"),
        ("aborted", "error"),
        ("insufficient_system_resource", "error"),
        ("future_finish", "unknown"),
    ],
)
def test_finish_codes_and_whitespace_are_not_fabricated(native: str, reason: str) -> None:
    out = DeepSeekCodec().decode_response(
        {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "   "},
                    "finish_reason": native,
                }
            ]
        }
    )
    assert out.value.message.parts[0].text == "   "
    assert out.value.finish.native == native
    assert out.value.finish.reason == reason
    assert out.value.usage is None


def test_future_content_tag_remains_an_unknown_part() -> None:
    future = {"type": "future_binary", "bytes": "opaque"}
    raw = {"messages": [{"role": "user", "content": [future]}]}
    out = DeepSeekCodec().decode_request(raw)
    part = out.value.messages[0].parts[0]
    assert isinstance(part, PartUnknown)
    assert part.to_dict() == future
    assert certify_edge(EDGES[1], [raw]) == []


@pytest.mark.parametrize(
    "raw",
    [
        {"total_tokens": 9},
        {"prompt_tokens": 9, "prompt_cache_hit_tokens": 10},
        {"completion_tokens": 4, "completion_tokens_details": {"reasoning_tokens": 8}},
        {"completion_tokens": True},
        {"future_tokens": 7},
    ],
)
def test_uncertain_usage_retains_measurements_without_double_counting(raw: dict[str, Any]) -> None:
    losses: list[FieldLoss] = []
    usage = decode_usage(raw, losses)
    assert usage is not None
    assert usage.extensions == {"deepseek.usage_unmapped": raw}
    assert len(losses) == 1
    assert all(
        isinstance(item.value, (int, float)) and item.value >= 0 for item in usage.consumptions
    )
    assert len({item.source for item in usage.consumptions}) == len(usage.consumptions)


def test_missing_details_do_not_mean_zero_cached_or_reasoning() -> None:
    usage = decode_usage({"prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16}, [])
    assert usage is not None
    assert {item.source: item.value for item in usage.consumptions} == {
        "deepseek.prompt_total": 10,
        "deepseek.completion_total": 6,
    }


@pytest.mark.parametrize(
    "part",
    [
        {"type": "reasoning"},
        {
            "type": "text",
            "text": "source",
            "annotations": [
                {"kind": "url_citation", "start": 0, "end": 6, "url": "https://example.test/source"}
            ],
        },
    ],
)
def test_unavailable_reasoning_and_unqualified_annotations_are_reported(
    part: dict[str, Any],
) -> None:
    request = ChatRequest.from_dict({"messages": [{"role": "model", "parts": [part]}]})
    out = DeepSeekCodec().encode_request(request)
    assert any(loss.disposition is Disposition.UNSUPPORTED for loss in out.losses)
    assert certify_edge(EDGES[0], [request]) == []
