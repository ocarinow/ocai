"""Client response edge golden, certification, and usage inversion evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import ocai.openai
from ocai.chat.types import ChatResponse
from ocai.chat.types import FinishInfo
from ocai.chat.types import Message
from ocai.chat.types import PartText
from ocai.chat.types import ResponseInfo
from ocai.convert.catalog import Catalog
from ocai.convert.conformance import certify_edge
from ocai.convert.conformance import check_edge
from ocai.core.canonjson import semantic_equal
from ocai.core.refs import ProviderRef
from ocai.openai.chat_completions.client import ClientMetadata
from ocai.openai.chat_completions.codec import CANONICAL_RESPONSE
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_RESPONSE
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.openai.chat_completions.edges import EDGES

FIXTURES = Path(__file__).resolve().parents[4] / "spec/fixtures/openai/chat_completions/gateway"
ENCODE = next(edge for edge in EDGES if edge.src == CANONICAL_RESPONSE)


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("response_*.json")), ids=lambda p: p.name)
def test_response_edge_golden_and_catalog(path: Path) -> None:
    fixture: dict[str, Any] = json.loads(path.read_text())
    check_edge(ENCODE, fixture, decode_input=ChatResponse.from_dict)
    response = ChatResponse.from_dict(fixture["input"])
    assert certify_edge(ENCODE, [response]) == []
    converted = Catalog.of(ocai.openai.FRAGMENT).convert(
        response, CANONICAL_RESPONSE, CHAT_COMPLETIONS_RESPONSE
    )
    assert semantic_equal(converted.value, fixture["expect"])
    metadata = ClientMetadata(id="chatcmpl-gateway", model="deployment", created=1767225600)
    document = metadata.bind(converted.value)
    assert document["id"] == "chatcmpl-gateway"
    assert "id" not in converted.value


def test_nonzero_usage_round_trip_counts_each_token_once() -> None:
    fixture: dict[str, Any] = json.loads((FIXTURES / "response_tools_usage.json").read_text())
    decoded = ChatCompletionsCodec().decode_response(fixture["expect"])
    assert decoded.value.usage.total_tokens == 21
    assert decoded.value.usage.input_tokens == 8
    assert decoded.value.usage.output_tokens == 6
    encoded = ENCODE.fn(decoded.value)
    assert encoded.value["usage"] == fixture["expect"]["usage"]
    decode_edge = next(edge for edge in EDGES if edge.src == CHAT_COMPLETIONS_RESPONSE)
    assert certify_edge(decode_edge, [fixture["expect"]]) == []


@pytest.mark.parametrize(
    "reason, native, expected",
    [
        ("complete", "stop", "stop"),
        ("max_tokens", "length", "length"),
        ("content_filter", "content_filter", "content_filter"),
        ("unknown", "tomorrow", "tomorrow"),
    ],
)
def test_finish_and_unknown_usage(reason: str, native: str, expected: str) -> None:
    response = ChatResponse(
        message=Message(role="model", parts=[PartText(text="hi")]),
        finish=FinishInfo(reason=reason, native=native),
    )
    result = ENCODE.fn(response)
    assert result.value["choices"][0]["finish_reason"] == expected
    assert "usage" not in result.value
    assert ENCODE.contract.certify(result.losses, result.shifts) == []
    if reason == "unknown":
        assert any(loss.path == "finish.reason" for loss in result.losses)


def test_foreign_response_identity_never_becomes_an_openai_reference() -> None:
    response = ChatResponse(
        message=Message(role="model", parts=[]),
        info=ResponseInfo(
            id=ProviderRef(
                provider="anthropic", interface="messages", kind="response_id", id="msg-x"
            )
        ),
    )
    result = ENCODE.fn(response)
    assert "id" not in result.value
    assert [(loss.path, loss.disposition.value) for loss in result.losses] == [
        ("info.id", "unsupported")
    ]
    assert ENCODE.contract.certify(result.losses, result.shifts) == []
