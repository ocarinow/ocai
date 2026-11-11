"""Cross-conversion fidelity proof — flagship demo #1 (WU-15).

Pure `ocai.convert`, no wire: recorded provider requests convert **across
providers** through the canonical backbone, and every cost of the move is
visible in the merged `FidelityReport`. The golden pins live in
`spec/fixtures/cross/`:

- the two merged cross fixtures (`request_openai_to_anthropic.json`,
  `request_anthropic_to_openai.json`) pin input → output across the 2-hop
  path plus the merged per-edge loss/shift records — the system RELOCATION
  shift and the `is_error` DROP are the story;
- the two `decode_request_*.json` fixtures pin each new audit-direction
  edge alone, so the intermediate canonical form is golden too (and
  schema-validated by the spec harness — the `dst` side is canonical).

Also here: certification of the new decode edges (runtime loss never
exceeds the census) and of the encode edges over the cross intermediates;
the §2.4 `ProviderRef` scoped-crossing rule (interface-scoped refs are
UNSUPPORTED-and-reported across `(provider, interface)`; provider-scoped
refs cross sibling interfaces unreported); the honest response-leg scope
(both response DECODE directions exist and merge into one report — the
encode-response direction does not exist yet, recorded in the WU-15 plan);
and the runnable example's printed report, asserted so the demo can never
drift from what the library actually reports.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any
from typing import cast

import pytest

import ocai.anthropic
import ocai.openai
from ocai.anthropic.messages.codec import MESSAGES_REQUEST
from ocai.anthropic.messages.codec import MESSAGES_RESPONSE
from ocai.anthropic.messages.codec import MessagesCodec
from ocai.anthropic.messages.edges import EDGES as ANTHROPIC_EDGES
from ocai.chat import CANONICAL_CHAT_REQUEST
from ocai.chat import CANONICAL_CHAT_RESPONSE
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import Message
from ocai.chat.types import PartImage
from ocai.convert.catalog import Catalog
from ocai.convert.conformance import certify_edge
from ocai.convert.conformance import check_edge
from ocai.convert.graph import ConversionError
from ocai.core.canonjson import canonical
from ocai.core.canonjson import semantic_equal
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import FidelityReport
from ocai.core.refs import ProviderRef
from ocai.core.refs import RefScope
from ocai.core.sources import SourceRef
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_REQUEST
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_RESPONSE
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.openai.chat_completions.edges import EDGES as OPENAI_EDGES


def _find_repo_root(start: Path) -> Path:
    """Walk upward until we find the repo root (the dir containing `spec/`)."""
    for parent in [start, *start.parents]:
        if (parent / "spec" / "fixtures").is_dir():
            return parent
    raise RuntimeError("could not locate repo root (no spec/fixtures/ found)")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
CROSS_DIR = REPO_ROOT / "spec" / "fixtures" / "cross"

# The wire endpoints, keyed the way the fixtures' src/dst coordinates name them.
_WIRE_NODES = {
    ("openai", "chat_completions"): CHAT_COMPLETIONS_REQUEST,
    ("anthropic", "messages"): MESSAGES_REQUEST,
}
_CODECS = {
    ("openai", "chat_completions"): ChatCompletionsCodec(),
    ("anthropic", "messages"): MessagesCodec(),
}

# The new audit-direction edges (wire chat.request -> canonical chat.request).
OPENAI_DECODE_REQUEST = next(edge for edge in OPENAI_EDGES if edge.src == CHAT_COMPLETIONS_REQUEST)
ANTHROPIC_DECODE_REQUEST = next(edge for edge in ANTHROPIC_EDGES if edge.src == MESSAGES_REQUEST)
OPENAI_ENCODE_REQUEST = next(edge for edge in OPENAI_EDGES if edge.dst == CHAT_COMPLETIONS_REQUEST)
ANTHROPIC_ENCODE_REQUEST = next(edge for edge in ANTHROPIC_EDGES if edge.dst == MESSAGES_REQUEST)

CROSS_FIXTURES = sorted(CROSS_DIR.glob("request_*.json"))
DECODE_FIXTURES = sorted(CROSS_DIR.glob("decode_request_*.json"))


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _expect_shifts(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    """The fixture's pinned shift records; an absent or null key means none."""
    shifts: Any = fixture.get("expect_shifts")
    if not shifts:
        return []
    return cast(list[dict[str, Any]], shifts)


def _catalog() -> Catalog:
    return Catalog.of(ocai.openai.FRAGMENT, ocai.anthropic.FRAGMENT)


def _node(coordinate: dict[str, Any]):
    return _WIRE_NODES[(coordinate["provider"], coordinate["interface"])]


def _sorted_losses(report: FidelityReport) -> list[tuple[str, str]]:
    return sorted((loss.path, loss.disposition.value) for loss in report.losses)


def _sorted_shifts(report: FidelityReport) -> list[tuple[str, str]]:
    return sorted((shift.kind, shift.path) for shift in report.shifts)


# --- The flagship claim: wire A -> canonical -> wire B, everything reported ----


def test_cross_fixture_set_covers_the_wu15_story() -> None:
    assert len(CROSS_FIXTURES) >= 2 and len(DECODE_FIXTURES) >= 2, (
        f"WU-15 expects at least two merged cross fixtures and two decode pins in {CROSS_DIR}"
    )
    losses = [
        (entry["path"], entry["disposition"])
        for path in CROSS_FIXTURES
        for entry in _load(path)["expect_losses"]
    ]
    shifts = [
        (entry["kind"], entry["path"])
        for path in CROSS_FIXTURES
        for entry in _expect_shifts(_load(path))
    ]
    # The system RELOCATION shift appears in the merged reports — both the
    # destination hoist (openai -> anthropic) and the source un-hoist.
    assert ("relocation", "messages[0]") in shifts
    assert ("relocation", "system") in shifts
    # The is_error DROP appears (anthropic -> openai: the flag crossed the
    # Messages wire EXACTLY and chat_completions has no lane for it).
    assert ("messages[3].parts[0].is_error", "dropped") in losses
    # The wire model is routing data on BOTH source dialects.
    assert losses.count(("model", "extensions")) == 2


@pytest.mark.parametrize("path", CROSS_FIXTURES, ids=lambda p: p.name)
def test_planner_chose_the_two_hop_path_through_canonical(path: Path) -> None:
    fixture = _load(path)
    src, dst = _node(fixture["src"]), _node(fixture["dst"])
    converted = _catalog().convert(fixture["input"], src, dst)
    assert converted.report.path == [src, CANONICAL_CHAT_REQUEST, dst], (
        f"{path.name}: expected the 2-hop plan through the canonical backbone, "
        f"got {[str(node) for node in converted.report.path]}"
    )
    assert len(converted.report.edges) == 2


@pytest.mark.parametrize("path", CROSS_FIXTURES, ids=lambda p: p.name)
def test_cross_fixture_output_and_merged_report(path: Path) -> None:
    fixture = _load(path)
    src, dst = _node(fixture["src"]), _node(fixture["dst"])
    converted = _catalog().convert(fixture["input"], src, dst)
    # WU-05a: edges are model-agnostic; the destination wire `model` member
    # is the bind_resource injection, below the graph — converting re-binds
    # a fresh resource at the front door.
    codec = _CODECS[(fixture["dst"]["provider"], fixture["dst"]["interface"])]
    rendered = codec.bind_resource(converted.value, fixture["expect"]["model"])
    assert semantic_equal(rendered, fixture["expect"]), (
        f"{path.name}: cross conversion did not match `expect`.\n"
        f"  expected: {canonical(fixture['expect'])}\n"
        f"  actual:   {canonical(rendered)}"
    )
    # The merged per-edge report matches the fixture's pinned records exactly.
    expected_losses = sorted(
        (entry["path"], entry["disposition"]) for entry in fixture["expect_losses"]
    )
    expected_shifts = sorted(
        (entry["kind"], entry.get("path", "")) for entry in _expect_shifts(fixture)
    )
    assert _sorted_losses(converted.report) == expected_losses
    assert _sorted_shifts(converted.report) == expected_shifts


# --- The audit-direction edges, pinned and certified alone ---------------------


@pytest.mark.parametrize("path", DECODE_FIXTURES, ids=lambda p: p.name)
def test_decode_request_fixture(path: Path) -> None:
    fixture = _load(path)
    edge = OPENAI_DECODE_REQUEST if "openai" in path.name else ANTHROPIC_DECODE_REQUEST
    assert fixture["src"]["provider"] == edge.src.provider
    check_edge(edge, fixture)


def _wire_payloads(provider: str) -> list[dict[str, Any]]:
    """Every recorded wire request for `provider` across the cross fixtures."""
    payloads = [
        _load(path)["input"]
        for path in [*CROSS_FIXTURES, *DECODE_FIXTURES]
        if _load(path)["src"]["provider"] == provider
    ]
    assert payloads, f"no recorded {provider} wire requests in {CROSS_DIR}"
    return payloads


def test_openai_decode_request_edge_certifies() -> None:
    assert certify_edge(OPENAI_DECODE_REQUEST, _wire_payloads("openai")) == []


def test_anthropic_decode_request_edge_certifies() -> None:
    assert certify_edge(ANTHROPIC_DECODE_REQUEST, _wire_payloads("anthropic")) == []


def test_encode_edges_certify_over_the_cross_intermediates() -> None:
    """The canonical intermediates stay within the encode censuses.

    They carry the banked wire model in `extensions` — the truth-up that made
    the foreign-extension DROP declared, not silent.
    """
    openai_intermediate = OPENAI_DECODE_REQUEST.fn(_wire_payloads("openai")[0]).value
    anthropic_intermediate = ANTHROPIC_DECODE_REQUEST.fn(_wire_payloads("anthropic")[0]).value
    assert certify_edge(ANTHROPIC_ENCODE_REQUEST, [openai_intermediate]) == []
    assert certify_edge(OPENAI_ENCODE_REQUEST, [anthropic_intermediate]) == []


# --- The response leg: honest scope — decode directions exist, merge works -----


def test_response_decode_directions_exist_and_reports_merge() -> None:
    catalog = _catalog()
    openai_response = _load(
        REPO_ROOT / "spec" / "fixtures" / "openai" / "chat_completions" / "response_plain_text.json"
    )["input"]
    anthropic_response = _load(
        REPO_ROOT / "spec" / "fixtures" / "anthropic" / "messages" / "response_tool_use.json"
    )["input"]
    # Both wire responses decode to canonical — any archived response is
    # re-convertible (the audit posture).
    openai_leg = catalog.convert(
        openai_response, CHAT_COMPLETIONS_RESPONSE, CANONICAL_CHAT_RESPONSE
    )
    anthropic_leg = catalog.convert(anthropic_response, MESSAGES_RESPONSE, CANONICAL_CHAT_RESPONSE)
    # A request leg and a response leg merge into ONE report, exactly as the
    # facade folds them onto CallResult.report.
    request_fixture = _load(CROSS_DIR / "request_openai_to_anthropic.json")
    request_leg = catalog.convert(
        request_fixture["input"], CHAT_COMPLETIONS_REQUEST, MESSAGES_REQUEST
    )
    merged = FidelityReport(edges=list(request_leg.report.edges)).merge(anthropic_leg.report)
    assert len(merged.edges) == 3
    assert merged.edges[-1].src == MESSAGES_RESPONSE
    merged_shifts = _sorted_shifts(merged)
    assert ("anthropic.args_serialized", "content[1].input") in merged_shifts
    assert ("relocation", "messages[0]") in merged_shifts
    assert openai_leg.report.edges, "the openai response decode leg must report its edge"


def test_client_response_direction_exists_only_for_qualified_interface() -> None:
    """WU-30 adds the client OpenAI direction; Anthropic serving stays out of scope."""
    catalog = _catalog()
    response = ChatResponse(message=Message(role="model", parts=[]))
    with pytest.raises(ConversionError):
        catalog.convert(response, CANONICAL_CHAT_RESPONSE, MESSAGES_RESPONSE)
    encoded = catalog.convert(response, CANONICAL_CHAT_RESPONSE, CHAT_COMPLETIONS_RESPONSE)
    assert encoded.value["choices"][0]["message"]["role"] == "assistant"


# --- §2.4: the ProviderRef scoped-crossing rule ---------------------------------


def _request_with_file_ref(ref: ProviderRef) -> ChatRequest:
    return ChatRequest(
        messages=[Message(role="user", parts=[PartImage(source=SourceRef(ref=ref))])]
    )


def _unsupported_ref_losses(report: FidelityReport) -> list[str]:
    return [
        loss.path
        for loss in report.losses
        if loss.disposition is Disposition.UNSUPPORTED and loss.path.endswith(".source")
    ]


def test_interface_scoped_ref_crossing_providers_is_unsupported_and_reported() -> None:
    """An interface-scoped file id crossing providers is UNSUPPORTED.

    A SourceRef minted by openai/chat_completions converted toward
    anthropic/messages is reported, never silently dropped.
    """
    request = _request_with_file_ref(
        ProviderRef(provider="openai", interface="chat_completions", kind="file", id="file-abc123")
    )
    converted = _catalog().convert(request, CANONICAL_CHAT_REQUEST, MESSAGES_REQUEST)
    assert _unsupported_ref_losses(converted.report) == ["messages[0].parts[0].source"]


def test_provider_scoped_ref_crossing_sibling_interface_is_unreported() -> None:
    """A provider-scoped ref crossing a sibling interface is NOT reported.

    An OpenAI file id valid across chat_completions / responses / batch
    crossing to a sibling OpenAI interface stays silent — the deliberate
    silence of the scoped rule.
    """
    request = _request_with_file_ref(
        ProviderRef(
            provider="openai",
            interface="responses",
            kind="file",
            id="file-abc123",
            scope=RefScope.PROVIDER,
        )
    )
    converted = _catalog().convert(request, CANONICAL_CHAT_REQUEST, CHAT_COMPLETIONS_REQUEST)
    assert _unsupported_ref_losses(converted.report) == []


def test_interface_scoped_ref_crossing_sibling_interface_is_reported() -> None:
    """The contrast case: an interface-scoped ref IS reported on the same crossing.

    The default, narrowest reading of the scope.
    """
    request = _request_with_file_ref(
        ProviderRef(provider="openai", interface="responses", kind="file", id="file-abc123")
    )
    converted = _catalog().convert(request, CANONICAL_CHAT_REQUEST, CHAT_COMPLETIONS_REQUEST)
    assert _unsupported_ref_losses(converted.report) == ["messages[0].parts[0].source"]


# --- The runnable example prints exactly what the library reports --------------


def test_example_output_is_the_real_report() -> None:
    demo_path = REPO_ROOT / "examples" / "cross_conversion_demo.py"
    spec = importlib.util.spec_from_file_location("cross_conversion_demo", demo_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = module.main()
    # The 2-hop path through the canonical backbone is printed verbatim.
    assert (
        "openai/chat_completions@2023-11#chat.request  ->  "
        "ocai/ocai@2026-07#chat.request  ->  "
        "anthropic/messages@2023-06#chat.request"
    ) in output
    # The system hoist shift, visibly.
    assert "shift (relocation) messages[0]" in output
    assert "system" in output
    # The is_error drop, visibly.
    assert "loss  [dropped] messages[3].parts[0].is_error" in output
    # The wire model banked as routing data, visibly.
    assert "extensions['openai.model']" in output
    # Honesty is derived, never asserted: the conversions cost something.
    assert "lossless: NO" in output
    # The recorded response-leg scope.
    assert "encode-response" in output
