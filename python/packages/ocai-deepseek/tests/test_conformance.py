"""WU-44b: exact fixtures and independent census certification for the DeepSeek variant."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import ocai.deepseek
from ocai.chat.types import ChatRequest
from ocai.convert import Catalog
from ocai.convert.conformance import certify_edge
from ocai.convert.conformance import check_edge
from ocai.convert.graph import Edge
from ocai.deepseek.chat_completions.codec import DeepSeekCodec
from ocai.deepseek.chat_completions.edges import EDGES

FIXTURES = Path(__file__).resolve().parents[4] / "spec/fixtures/deepseek/chat_completions"
PATHS = sorted(FIXTURES.glob("*.json"))


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _input(fixture: dict[str, Any]) -> Any:
    value = fixture["input"]
    return ChatRequest.from_dict(value) if fixture["src"]["provider"] == "ocai" else value


@pytest.mark.parametrize("path", PATHS, ids=lambda path: path.stem)
def test_golden_edge_and_catalog_match(path: Path) -> None:
    fixture = _load(path)
    edge = next(
        edge
        for edge in EDGES
        if edge.src.provider == fixture["src"]["provider"]
        and str(edge.src.shape) == fixture["src"]["shape"]
    )
    before = deepcopy(fixture["input"])
    check_edge(
        edge,
        fixture,
        decode_input=ChatRequest.from_dict if fixture["src"]["provider"] == "ocai" else None,
    )
    assert fixture["input"] == before
    converted = Catalog.of(ocai.deepseek.FRAGMENT).convert(_input(fixture), edge.src, edge.dst)
    actual = converted.value.to_dict() if hasattr(converted.value, "to_dict") else converted.value
    assert actual == fixture["expect"]
    assert converted.report.edges[0].src == edge.src
    assert converted.report.edges[0].dst == edge.dst


@pytest.mark.parametrize("edge", EDGES, ids=lambda edge: str(edge.src.shape) + edge.src.provider)
def test_runtime_loss_is_bounded_by_own_contract(edge: Edge) -> None:
    fixtures = [_load(path) for path in PATHS]
    inputs = [
        _input(fixture)
        for fixture in fixtures
        if fixture["src"]["provider"] == edge.src.provider
        and fixture["src"]["shape"] == str(edge.src.shape)
    ]
    assert inputs
    assert certify_edge(edge, inputs) == []


UNKNOWN_RESPONSES: list[Any] = [
    None,
    [],
    7,
    "future",
    {"choices": [None]},
    {
        "choices": [
            {"finish_reason": [], "message": {"role": [], "content": 8, "tool_calls": "future"}}
        ]
    },
    {"created": 10**300, "choices": [{"message": {"reasoning_content": {"future": 1}}}]},
]


@pytest.mark.parametrize("raw", UNKNOWN_RESPONSES)
def test_unknown_response_documents_are_total_and_keep_evidence(raw: Any) -> None:
    output = DeepSeekCodec().decode_response(raw)
    assert output.value.raw == raw
    assert output.value.extensions["deepseek.response_unmapped"]
    assert any(loss.path == "unmapped" for loss in output.losses)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        [],
        7,
        "future",
        {"messages": [None]},
        {"messages": [{"role": [], "content": [{"type": "future", "payload": "opaque"}]}]},
        {"messages": [{"role": "assistant", "tool_calls": [{"type": "future"}]}]},
    ],
)
def test_unknown_request_documents_are_total_and_keep_evidence(raw: Any) -> None:
    output = DeepSeekCodec().decode_request(raw)
    assert output.value.extensions["deepseek.request_unmapped"]
    assert any(loss.path == "unmapped" for loss in output.losses)


def test_every_assistant_reasoning_turn_replays_without_changes() -> None:
    fixture = _load(FIXTURES / "request_reasoning_replay.json")
    request = ChatRequest.from_dict(fixture["input"])
    codec = DeepSeekCodec()
    wire = codec.encode_request(request)
    audited = codec.decode_request(wire.value)
    replayed = codec.encode_request(audited.value)
    assert replayed.value == wire.value == fixture["expect"]
    assert not audited.losses
    assert not replayed.losses
