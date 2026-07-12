"""The two flagship proofs: version resolution/chaining and field-level fidelity.

1. **Version bump, no user-code change.** A provider ships `v1.1`; only the
   cheap `v1.1 <-> v1` delta edges are registered (no new path to canonical).
   `Catalog.resolve` picks `v1.1` as latest by `released` (never parsing the
   opaque tag), and the graph reaches it by *chaining* `canonical -> v1 ->
   v1.1` — the calling code never names a revision.
2. **Honest, field-level fidelity.** A lossy edge reports a `DROPPED`
   `FieldLoss` and the report is not `lossless`; planner cost is derived from
   each edge's declared `EdgeContract` census (`LossGrade`), so a declared-
   lossless two-hop path beats a lossy direct shortcut.

These use an **isolated** `Catalog` / `ConversionGraph` built from a synthetic
`acme` fragment (the catalogs are scoped, not process-global) so the synthetic
`v1.1` never leaks into other tests.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from ocai.chat import CANONICAL_CHAT_REQUEST
from ocai.convert import Catalog
from ocai.convert import CatalogFragment
from ocai.convert import ConversionGraph
from ocai.convert import DeclaredDisposition
from ocai.convert import Edge
from ocai.convert import EdgeContract
from ocai.convert import EdgeOutput
from ocai.core import CHAT
from ocai.core import CHAT_REQUEST
from ocai.core import Disposition
from ocai.core import FieldLoss
from ocai.core import NodeId
from ocai.core import Origin

# A synthetic provider's two dated chat.request nodes. v1.1 is newer by
# `released` — tags are opaque and never parsed.
ORIGIN = Origin(distribution="ocai-acme", version="0.0.1")
ACME_V1 = NodeId("acme", "chat", "v1", CHAT_REQUEST, date(2024, 1, 1))
ACME_V1_1 = NodeId("acme", "chat", "v1.1", CHAT_REQUEST, date(2024, 6, 1))

LOSSLESS = EdgeContract()  # empty census == declared lossless, grade (0,0,0,1)
DOWNGRADE = EdgeContract(
    census={
        "reasoning_effort": DeclaredDisposition(
            Disposition.DROPPED, note="v1 cannot represent reasoning_effort"
        )
    },
    note="v1.1 -> v1 downgrade delta",
)


def _canonical_to_v1(payload: Any) -> EdgeOutput:
    return EdgeOutput({"stage": "v1", "src": payload})


def _v1_to_canonical(payload: Any) -> EdgeOutput:
    return EdgeOutput({"stage": "canonical", "src": payload})


def _v1_to_v1_1(payload: Any) -> EdgeOutput:
    # A clean, lossless upgrade delta.
    return EdgeOutput({"stage": "v1.1", "src": payload})


def _v1_1_to_v1(payload: Any) -> EdgeOutput:
    # The downgrade delta drops a v1.1-only field — reported, not silent.
    loss = FieldLoss(
        path="reasoning_effort",
        disposition=Disposition.DROPPED,
        severity=1.0,
        note="v1 cannot represent reasoning_effort",
    )
    return EdgeOutput({"stage": "v1", "src": payload}, (loss,))


def _edges() -> tuple[Edge, ...]:
    return (
        # Full canonical <-> v1 mapping...
        Edge(ACME_V1, CANONICAL_CHAT_REQUEST, _v1_to_canonical, LOSSLESS, ORIGIN, "v1 -> canon"),
        Edge(CANONICAL_CHAT_REQUEST, ACME_V1, _canonical_to_v1, LOSSLESS, ORIGIN, "canon -> v1"),
        # ...and ONLY the v1.1 <-> v1 deltas. No direct v1.1 <-> canonical edge.
        Edge(ACME_V1_1, ACME_V1, _v1_1_to_v1, DOWNGRADE, ORIGIN, "downgrade, drops effort"),
        Edge(ACME_V1, ACME_V1_1, _v1_to_v1_1, LOSSLESS, ORIGIN, "upgrade delta"),
    )


def _catalog() -> Catalog:
    fragment = CatalogFragment(origin=ORIGIN, nodes=(ACME_V1, ACME_V1_1), edges=_edges())
    return Catalog.of(fragment)


def _graph() -> ConversionGraph:
    graph = ConversionGraph()
    for edge in _edges():
        graph.register(edge)
    return graph


# --- Resolution: the dated resolver, never parsing tags ---------------------


def test_resolver_picks_latest_by_date() -> None:
    route = _catalog().resolve(CHAT, "acme")  # no revision pinned
    assert route.node.tag == "v1.1"
    assert route.requested_tag is None
    assert "2024-06-01" in route.reason
    assert route.catalog_hash  # the audit joint: route + lockfile


def test_pinned_tag_overrides_latest() -> None:
    route = _catalog().resolve(CHAT, "acme", tag="v1")
    assert route.node.tag == "v1"
    assert route.requested_tag == "v1"
    assert route.reason == "pinned"


# --- Chaining: the version-bump-no-user-code-change proof --------------------


def test_version_chaining_without_direct_edge() -> None:
    # The flagship: target the resolved latest (v1.1) with no direct path to
    # canonical; the graph chains canonical -> v1 -> v1.1 on its own.
    catalog = _catalog()
    route = catalog.resolve(CHAT, "acme")
    converted = catalog.convert({"hello": "world"}, CANONICAL_CHAT_REQUEST, route.node)
    assert converted.report.path == [CANONICAL_CHAT_REQUEST, ACME_V1, ACME_V1_1]
    # The value reflects both hops (canonical -> v1 -> v1.1).
    assert converted.value["stage"] == "v1.1"
    assert converted.value["src"]["stage"] == "v1"
    # Upgrade chain is lossless and auditable.
    assert converted.report.lossless


# --- Fidelity: honest per-field records + contract-derived planning ----------


def test_lossy_edge_reports_dropped_field() -> None:
    converted = _graph().convert({"reasoning_effort": "high"}, ACME_V1_1, ACME_V1)
    assert not converted.report.lossless
    dropped = converted.report.dropped
    assert [loss.path for loss in dropped] == ["reasoning_effort"]
    assert dropped[0].disposition is Disposition.DROPPED
    assert converted.report.total_cost == 1.0


def test_lossless_conversion_reports_lossless() -> None:
    converted = _graph().convert({"x": 1}, CANONICAL_CHAT_REQUEST, ACME_V1)
    assert converted.report.lossless


def test_planner_prefers_declared_lossless_path_over_lossy_shortcut() -> None:
    # Planner weight is DERIVED from the contract census (§4.2): the direct
    # edge declares a DROPPED field, so its grade (1,0,0,1) loses to the
    # two-hop declared-lossless chain's (0,0,0,2) — no float to game.
    def _lossy_direct(payload: Any) -> EdgeOutput:
        loss = FieldLoss("x", Disposition.DROPPED, severity=1.0)
        return EdgeOutput({"stage": "direct", "src": payload}, (loss,))

    graph = _graph()
    graph.register(
        Edge(
            src=CANONICAL_CHAT_REQUEST,
            dst=ACME_V1_1,
            fn=_lossy_direct,
            contract=EdgeContract(census={"x": DeclaredDisposition(Disposition.DROPPED)}),
            origin=ORIGIN,
            note="lossy shortcut",
        )
    )
    converted = graph.convert({}, CANONICAL_CHAT_REQUEST, ACME_V1_1)
    assert converted.report.path == [CANONICAL_CHAT_REQUEST, ACME_V1, ACME_V1_1]
    assert converted.report.lossless
