"""Schema-only design checks; no claim of implemented conversion or replay."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.protocols import Validator
from referencing import Registry
from referencing import Resource
from referencing.jsonschema import Schema

ROOT = Path(__file__).resolve().parents[4]
PROPOSAL = ROOT / "spec/proposals/ordered-items"
SCHEMAS = sorted(PROPOSAL.glob("*.schema.json"))
FIXTURES = sorted((PROPOSAL / "fixtures").glob("*.json"))


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _validator(name: str) -> Validator:
    resources = [_read(path) for path in [*(ROOT / "spec/schema").glob("*.json"), *SCHEMAS]]
    registry = Registry[Schema]().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in resources
    )
    return Draft202012Validator(_read(PROPOSAL / name), registry=registry)


def _at(document: Any, path: list[str | int]) -> Any:
    for key in path:
        document = document[key]
    return document


@pytest.mark.parametrize("path", SCHEMAS, ids=lambda path: path.stem)
def test_draft_schema_is_valid(path: Path) -> None:
    Draft202012Validator.check_schema(_read(path))


@pytest.mark.parametrize("path", FIXTURES, ids=lambda path: path.stem)
def test_design_fixture_and_selected_preservation_requirements(path: Path) -> None:
    fixture = _read(path)
    assert fixture["provenance"]["kind"] == "synthetic"
    assert fixture["requirements"]
    _validator(fixture["schema"]).validate(fixture["document"])
    for requirement in fixture.get("preserved", []):
        assert _at(fixture["input"], requirement["source"]) == _at(
            fixture["document"], requirement["target"]
        )


@pytest.mark.parametrize(
    "item",
    [
        {},
        {"type": "message", "content": []},
        {"type": "message", "role": "model"},
        {"type": "tool_call", "name": "lookup", "args_json": "{}"},
        {"type": "tool_call", "call_id": "c1", "name": "lookup"},
        {"type": "tool_call", "call_id": "c1", "name": "lookup", "args_json": {}},
        {"type": "tool_result", "content": []},
        {"type": "approval_request", "name": "lookup", "args_json": "{}"},
        {"type": "approval_response", "approval_id": "a1"},
        {"type": "approval_response", "approval_id": "a1", "approved": "yes"},
        {"type": "future.example", "source_group": {"container": "m1", "index": -1}},
    ],
)
def test_known_item_requirements_cannot_fall_through(item: dict[str, Any]) -> None:
    assert not _validator("items.schema.json").is_valid(item)


@pytest.mark.parametrize(
    "part",
    [
        {"type": "text"},
        {"type": "json"},
        {"type": "file"},
        {"type": "file", "source": {}, "size_bytes": -1},
        {"type": "reasoning", "text": "summary"},
        {"type": "tool_call", "call_id": "c1", "name": "lookup", "args_json": "{}"},
    ],
)
def test_content_boundary_rejects_malformed_or_execution_parts(part: dict[str, Any]) -> None:
    assert not _validator("content.schema.json").is_valid(part)


@pytest.mark.parametrize("value", [None, False, 0, "", [], {"a": None}])
def test_native_json_preserves_null_and_scalar_values(value: Any) -> None:
    _validator("content.schema.json").validate({"type": "json", "value": value})


def test_history_keeps_tool_correlation_arguments_and_binary_sample() -> None:
    """Check independent requirements of the candidate, not a converter."""
    import base64

    document = _read(PROPOSAL / "fixtures/history_json_binary.json")["document"]
    items = document["items"]
    assert items[1]["call_id"] == items[2]["call_id"] == "call_1"
    assert items[1]["id"] != items[1]["call_id"]
    assert items[1]["args_json"] == '{ "topic" : "ocai" }'
    sample = items[0]["content"][2]
    assert base64.b64decode(sample["source"]["data"], validate=True) == b"\x00\x01\xff"
    assert sample["size_bytes"] == 3


def test_native_grouping_keeps_block_order_and_argument_meaning() -> None:
    fixture = _read(PROPOSAL / "fixtures/anthropic_blocks.json")
    items = fixture["document"]["items"]
    assert [item["source_group"]["index"] for item in items] == [0, 1]
    assert {item["source_group"]["container"] for item in items} == {fixture["input"]["id"]}
    assert json.loads(items[1]["args_json"]) == fixture["input"]["content"][1]["input"]


def test_unknown_items_and_content_remain_open() -> None:
    item = _read(PROPOSAL / "fixtures/unknown_item.json")["document"]["items"][0]
    original = deepcopy(item)
    _validator("items.schema.json").validate(item)
    _validator("content.schema.json").validate(item)
    assert item == original


def test_proposal_marker_cannot_be_mistaken_for_active_request() -> None:
    validator = _validator("request.schema.json")
    assert not validator.is_valid({"version": "2026-07", "messages": []})
    assert not validator.is_valid({"proposal": "2026-07", "items": []})
