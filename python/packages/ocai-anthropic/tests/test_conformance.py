"""Anthropic messages unary certification (WU-13, the WU-06 pattern replay).

Drives the interface's two unary edges through the full conformance harness
over the golden edge fixtures in `spec/fixtures/anthropic/messages/`:

- `check_edge` — running each edge on its fixture `input` yields a value
  `semantic_equal` to `expect`, and the runtime `FieldLoss`/`SemanticShift`
  records match `expect_losses`/`expect_shifts` exactly;
- `certify_edge` — the same payload set certifies against each edge's
  declared `EdgeContract` census with zero violations (an edge claiming
  less loss than it incurs cannot ship);
- catalog routing — the same fixtures convert through a `Catalog` composed
  of the real `ocai.anthropic.FRAGMENT`, proving the certified edges are
  what the planner actually routes payloads through (a full graph *round
  trip* needs the reverse edges — `decode_request` / an encode-response
  edge — which do not exist yet, so each fixture is exercised in its edge's
  one registered direction);
- the wire-side rule-6 guarantee — the decoder never raises on unknown wire
  material (unknown stop reasons keep the native lane; unknown envelope
  keys sweep into namespaced `extensions`).

The WU-05a seam applies throughout: the canonical request carries no model,
the edge output has no `model` member, and the fixtures' wire bodies gain it
through the codec's `bind_resource` — the facade injection, below the graph.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import ocai.anthropic
from ocai.anthropic.messages.codec import MESSAGES_REQUEST
from ocai.anthropic.messages.codec import MESSAGES_RESPONSE
from ocai.anthropic.messages.codec import MessagesCodec
from ocai.anthropic.messages.edges import EDGES
from ocai.anthropic.messages.edges import ENCODE_REQUEST_CONTRACT
from ocai.chat import CANONICAL_CHAT_REQUEST
from ocai.chat import CANONICAL_CHAT_RESPONSE
from ocai.chat.types import ChatRequest
from ocai.convert.catalog import Catalog
from ocai.convert.conformance import certify_edge
from ocai.convert.conformance import check_edge
from ocai.convert.graph import Edge
from ocai.convert.graph import EdgeOutput
from ocai.core.canonjson import canonical
from ocai.core.canonjson import semantic_equal
from ocai.core.fidelity import Disposition
from ocai.core.identity import NodeId


def _find_repo_root(start: Path) -> Path:
    """Walk upward until we find the repo root (the dir containing `spec/`)."""
    for parent in [start, *start.parents]:
        if (parent / "spec" / "fixtures").is_dir():
            return parent
    raise RuntimeError("could not locate repo root (no spec/fixtures/ found)")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
FIXTURES_DIR = REPO_ROOT / "spec" / "fixtures" / "anthropic" / "messages"
FIXTURE_PATHS = sorted(FIXTURES_DIR.glob("*.json"))

_CODEC = MessagesCodec()
ENCODE_EDGE = next(edge for edge in EDGES if edge.dst == MESSAGES_REQUEST)
DECODE_EDGE = next(edge for edge in EDGES if edge.src == MESSAGES_RESPONSE)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _is_encode(fixture: dict[str, Any]) -> bool:
    """An `ocai`-source fixture exercises the encode edge; wire-source, decode."""
    return fixture["src"]["provider"] == "ocai"


def _edge_for(fixture: dict[str, Any]) -> Edge:
    return ENCODE_EDGE if _is_encode(fixture) else DECODE_EDGE


def _coordinates_match(coordinate: dict[str, Any], node: NodeId) -> bool:
    """The fixture's src/dst coordinates name the edge endpoint exactly."""
    return (
        coordinate["provider"] == node.provider
        and coordinate["interface"] == node.interface
        and coordinate["tag"] == node.tag
        and coordinate["shape"] == str(node.shape)
    )


def _run_fixture(fixture: dict[str, Any]) -> EdgeOutput:
    """Run one fixture through `check_edge` with the direction's seams."""
    if _is_encode(fixture):
        return check_edge(
            ENCODE_EDGE,
            fixture,
            decode_input=ChatRequest.from_dict,
            # WU-05a: edges are model-agnostic; the wire `model` member is
            # the facade's bind_resource injection, below the graph.
            bind=lambda payload: _CODEC.bind_resource(payload, fixture["expect"]["model"]),
        )
    return check_edge(DECODE_EDGE, fixture)


# --- The fixture set itself covers what WU-13 says it covers -------------------


def test_fixture_set_is_not_empty_and_covers_the_wu13_scenarios() -> None:
    assert len(FIXTURE_PATHS) >= 5, (
        f"WU-13 requires at least five edge fixtures in {FIXTURES_DIR}; "
        f"found {len(FIXTURE_PATHS)}"
    )
    losses = [
        (entry["path"], entry["disposition"])
        for path in FIXTURE_PATHS
        for entry in _load(path)["expect_losses"]
    ]
    shifts = [
        (entry["kind"], entry["path"])
        for path in FIXTURE_PATHS
        for entry in _load(path).get("expect_shifts") or []
    ]
    # (b) the system hoist is a declared SemanticShift(relocation).
    assert ("relocation", "messages[0]") in shifts
    # (d) the required max_tokens injection is a declared emulation shift.
    assert ("emulation", "config.max_output_tokens") in shifts
    # (e) the out-of-range temperature reports APPROXIMATED, passed verbatim.
    assert ("config.temperature", "approximated") in losses
    # (f) the extensions sweep reports both envelope keys as EXTENSIONS.
    assert ("stop_sequence", "extensions") in losses
    assert ("container", "extensions") in losses


def test_is_error_crosses_natively_the_honest_asymmetry_vs_openai() -> None:
    """(c) `tool_result.is_error` maps NATIVELY here — census EXACT, no loss.

    The honest asymmetry vs chat_completions, whose census declares the same
    path DROPPED: the same canonical payload costs different things on
    different wires, and the census is where that difference is visible.
    """
    declared = ENCODE_REQUEST_CONTRACT.census["messages[].parts[tool_result].is_error"]
    assert declared.disposition is Disposition.EXACT
    tool_round = _load(FIXTURES_DIR / "request_tool_round.json")
    # The flag actually crosses onto the wire...
    wire_blocks = [
        block
        for message in tool_round["expect"]["messages"]
        for block in message["content"]
        if block.get("type") == "tool_result"
    ]
    assert wire_blocks and wire_blocks[0]["is_error"] is True
    # ...and no fixture reports an is_error loss anywhere.
    losses = [
        entry["path"]
        for path in FIXTURE_PATHS
        for entry in _load(path)["expect_losses"]
    ]
    assert not any(path.endswith("is_error") for path in losses)


@pytest.mark.parametrize("path", FIXTURE_PATHS, ids=lambda p: p.name)
def test_fixture_names_its_edge_endpoints(path: Path) -> None:
    fixture = _load(path)
    edge = _edge_for(fixture)
    assert _coordinates_match(fixture["src"], edge.src), (
        f"{path.name}: src coordinates do not name {edge.src}"
    )
    assert _coordinates_match(fixture["dst"], edge.dst), (
        f"{path.name}: dst coordinates do not name {edge.dst}"
    )


# --- Clauses 1+2: output equality, exact loss/shift match ----------------------


@pytest.mark.parametrize("path", FIXTURE_PATHS, ids=lambda p: p.name)
def test_edge_fixture(path: Path) -> None:
    _run_fixture(_load(path))


# --- Clause 3: certification — runtime loss never exceeds the declaration ------


def _payloads(edge: Edge) -> list[Any]:
    """Every fixture `input` for `edge`, lifted to its source representation."""
    payloads: list[Any] = []
    for path in FIXTURE_PATHS:
        fixture = _load(path)
        if _edge_for(fixture) is not edge:
            continue
        payload: Any = fixture["input"]
        if _is_encode(fixture):
            payload = ChatRequest.from_dict(payload)
        payloads.append(payload)
    assert payloads, f"no fixtures exercise {edge.src} -> {edge.dst}"
    return payloads


def test_encode_edge_certifies_over_all_fixtures() -> None:
    assert certify_edge(ENCODE_EDGE, _payloads(ENCODE_EDGE)) == []


def test_decode_edge_certifies_over_all_fixtures() -> None:
    assert certify_edge(DECODE_EDGE, _payloads(DECODE_EDGE)) == []


# --- Catalog routing: the composed fragment plans through the certified edges --


def _catalog() -> Catalog:
    return Catalog.of(ocai.anthropic.FRAGMENT)


@pytest.mark.parametrize("path", FIXTURE_PATHS, ids=lambda p: p.name)
def test_fixture_converts_through_the_catalog(path: Path) -> None:
    fixture = _load(path)
    catalog = _catalog()
    if _is_encode(fixture):
        converted = catalog.convert(
            ChatRequest.from_dict(fixture["input"]),
            CANONICAL_CHAT_REQUEST,
            MESSAGES_REQUEST,
        )
        rendered = _CODEC.bind_resource(converted.value, fixture["expect"]["model"])
    else:
        converted = catalog.convert(
            fixture["input"], MESSAGES_RESPONSE, CANONICAL_CHAT_RESPONSE
        )
        rendered = converted.value.to_dict()
    assert semantic_equal(rendered, fixture["expect"]), (
        f"{path.name}: catalog conversion did not match `expect`.\n"
        f"  expected: {canonical(fixture['expect'])}\n"
        f"  actual:   {canonical(rendered)}"
    )
    # The report carries the same records the direct edge run produced —
    # streaming through the planner adds no silent extra leg.
    actual_losses = sorted(
        (loss.path, loss.disposition.value) for loss in converted.report.losses
    )
    expected_losses = sorted(
        (entry["path"], entry["disposition"]) for entry in fixture["expect_losses"]
    )
    assert actual_losses == expected_losses
    actual_shifts = sorted((shift.kind, shift.path) for shift in converted.report.shifts)
    expected_shifts = sorted(
        (entry["kind"], entry.get("path", ""))
        for entry in fixture.get("expect_shifts") or []
    )
    assert actual_shifts == expected_shifts


# --- Rule 6 on the wire: the decoder is total over unknown material ------------


def test_decode_never_raises_on_unknown_wire_material() -> None:
    payload = {
        "id": "msg_01Unknown",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-4-8",
        "content": [{"type": "text", "text": "ok"}],
        "stop_reason": "TELEPATHY_LIMIT",
        "routing_tier": {"shard": 7},
    }
    out = DECODE_EDGE.fn(payload)  # total decode: must not raise
    response = out.value
    # The unknown stop reason decodes open with the native lane verbatim.
    assert response.finish is not None
    assert response.finish.reason == "unknown"
    assert response.finish.native == "TELEPATHY_LIMIT"
    # The unknown envelope key sweeps into the namespaced extensions bag,
    # with an honest EXTENSIONS record — never silently dropped. (Its path is
    # deliberately NOT in the census: a tomorrow-key cannot be declared in
    # advance, so the sweep is the rule-6 safety net — and the moment such a
    # key lands in a golden fixture, certification flags it until the census
    # names it. That is the drift alarm working, not a bug.)
    assert response.extensions["anthropic.routing_tier"] == {"shard": 7}
    assert ("routing_tier", "extensions") in [
        (loss.path, loss.disposition.value) for loss in out.losses
    ]
