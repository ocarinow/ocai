"""Golden client request qualification and supported provider round trips."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import ocai.anthropic
import ocai.openai
from ocai.chat.types import ChatRequest
from ocai.convert.catalog import Catalog
from ocai.convert.conformance import certify_edge
from ocai.convert.conformance import check_edge
from ocai.core.canonjson import semantic_equal
from ocai.openai.chat_completions.codec import CANONICAL_REQUEST
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_REQUEST
from ocai.openai.chat_completions.edges import EDGES

FIXTURES = Path(__file__).resolve().parents[4] / "spec/fixtures/openai/chat_completions/gateway"
DECODE = next(edge for edge in EDGES if edge.src == CHAT_COMPLETIONS_REQUEST)


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("request_*.json")), ids=lambda p: p.name)
def test_client_request_golden_and_catalog(path: Path) -> None:
    fixture: dict[str, Any] = json.loads(path.read_text())
    check_edge(DECODE, fixture)
    assert certify_edge(DECODE, [fixture["input"]]) == []
    catalog = Catalog.of(ocai.openai.FRAGMENT)
    converted = catalog.convert(fixture["input"], CHAT_COMPLETIONS_REQUEST, CANONICAL_REQUEST)
    assert semantic_equal(converted.value.to_dict(), fixture["expect"])


def test_structured_tools_round_trip_and_cross_provider_findings() -> None:
    from ocai.anthropic.messages.codec import MESSAGES_REQUEST

    fixture: dict[str, Any] = json.loads((FIXTURES / "request_structured_tools.json").read_text())
    catalog = Catalog.of(ocai.openai.FRAGMENT, ocai.anthropic.FRAGMENT)
    canonical = catalog.convert(fixture["input"], CHAT_COMPLETIONS_REQUEST, CANONICAL_REQUEST)
    encoded = catalog.convert(canonical.value, CANONICAL_REQUEST, CHAT_COMPLETIONS_REQUEST)
    assert semantic_equal(encoded.value, fixture["input"])
    cross = catalog.convert(canonical.value, CANONICAL_REQUEST, MESSAGES_REQUEST)
    assert cross.value["tools"][0]["name"] == "weather"
    assert cross.value["tool_choice"]["name"] == "weather"
    # The schema survives; provider-specific name/strict selectors are reported.
    assert (
        cross.value["output_config"]["format"]["schema"]
        == (fixture["input"]["response_format"]["json_schema"]["schema"])
    )
    assert {"config.output.name", "config.output.strict"} <= {
        loss.path for loss in cross.report.losses
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"messages": 1, "tools": True},
        {"messages": [None, {"role": "assistant", "tool_calls": [42, {"type": "future"}]}]},
        {
            "messages": [
                {"role": "user", "content": [42, {"type": "text", "text": "x", "future": True}]}
            ]
        },
        {
            "tool_choice": {"type": "function", "function": 42},
            "response_format": {"type": "json_schema", "json_schema": 42},
        },
    ],
)
def test_nested_unknown_shapes_decode_totally(payload: dict[str, Any]) -> None:
    output = DECODE.fn(payload)
    assert isinstance(output.value, ChatRequest)
    assert output.value.extensions["openai.request_unmapped"]
    assert any(loss.path == "unmapped" for loss in output.losses)
