"""Conformance and discovery from independently installed distributions.

Run with the core and example wheels installed. Missing packages and obsolete
APIs fail collection rather than skipping.
"""

from __future__ import annotations

from importlib.metadata import distribution
from pathlib import Path
from typing import Any

import pytest

import ocai.contrib.echo as echo
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import PartUnknown
from ocai.convert.catalog import Catalog
from ocai.convert.conformance import certify_edge
from ocai.convert.conformance import check_edge
from ocai.convert.conformance import load_fixture
from ocai.convert.graph import Edge
from ocai.core.canonjson import semantic_equal
from ocai.core.identity import CHAT
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import NodeId
from ocai.core.identity import canonical_node

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
PATHS = sorted(FIXTURES.glob("*.json"))


def _matches(node: NodeId, coordinate: dict[str, str]) -> bool:
    """Match fixture coordinates without inventing release dates."""
    return (
        node.provider == coordinate["provider"]
        and node.interface == coordinate["interface"]
        and node.tag == coordinate["tag"]
        and str(node.shape) == coordinate["shape"]
    )


def _edge_for(fixture: dict[str, Any]) -> Edge:
    """Find the declared edge named by an independent fixture."""
    return next(
        edge
        for edge in echo.FRAGMENT.edges
        if _matches(edge.src, fixture["src"]) and _matches(edge.dst, fixture["dst"])
    )


@pytest.mark.parametrize("path", PATHS, ids=lambda path: path.stem)
def test_edge_output_and_contract(path: Path) -> None:
    fixture = load_fixture(path)
    edge = _edge_for(fixture)
    decode = ChatRequest.from_dict if edge.src.provider == "ocai" else None
    check_edge(edge, fixture, decode_input=decode)
    payload = decode(fixture["input"]) if decode else fixture["input"]
    assert certify_edge(edge, [payload]) == []


def test_every_edge_has_a_fixture() -> None:
    assert PATHS, "the plugin must ship fixtures"
    covered = [
        (_edge_for(load_fixture(path)).src, _edge_for(load_fixture(path)).dst) for path in PATHS
    ]
    assert set(covered) == {(edge.src, edge.dst) for edge in echo.FRAGMENT.edges}


def test_installed_entry_point_discovers_a_working_conversion() -> None:
    dist = distribution("ocai-contrib-echo")
    entries = [entry for entry in dist.entry_points if entry.group == "ocai.fragments"]
    assert len(entries) == 1
    assert entries[0].load() is echo.FRAGMENT
    assert echo.ECHO_ORIGIN.version == dist.version
    files = [str(path) for path in dist.files or ()]
    assert "ocai/contrib/echo/py.typed" in files
    assert "ocai/__init__.py" not in files
    assert "ocai/contrib/__init__.py" not in files
    catalog = Catalog.discover()
    fixture = load_fixture(FIXTURES / "echo_chat_request.json")
    converted = catalog.convert(
        fixture["input"],
        echo.ECHO_CHAT_REQUEST,
        canonical_node(CHAT_REQUEST),
    )
    assert isinstance(converted.value, ChatRequest)
    assert semantic_equal(converted.value, fixture["expect"])
    assert converted.report.lossless
    assert catalog.components_for("echo", CHAT) == ()


def test_request_roundtrip_and_unknown_content_preservation() -> None:
    catalog = Catalog.of(echo.FRAGMENT)
    fixture = load_fixture(FIXTURES / "echo_unknown_part.json")
    decoded = catalog.convert(
        fixture["input"],
        echo.ECHO_CHAT_REQUEST,
        canonical_node(CHAT_REQUEST),
    )
    assert isinstance(decoded.value.messages[0].parts[0], PartUnknown)
    encoded = catalog.convert(decoded.value, canonical_node(CHAT_REQUEST), echo.ECHO_CHAT_REQUEST)
    assert semantic_equal(encoded.value, fixture["input"])


def test_response_decode_returns_a_typed_response() -> None:
    fixture = load_fixture(FIXTURES / "echo_chat_response.json")
    result = Catalog.of(echo.FRAGMENT).convert(
        fixture["input"],
        echo.ECHO_CHAT_RESPONSE,
        echo.FRAGMENT.edges[-1].dst,
    )
    assert isinstance(result.value, ChatResponse)
    assert result.value.message.text == "Hello!"
