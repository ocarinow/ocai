"""Conformance: the echo fragment's edges satisfy their golden fixtures.

A plugin's whole test suite can stay this small because the harness ships in
core (`ocai.convert.conformance`): `check_edge` runs an edge over a fixture,
asserts the output is `semantic_equal` to `expect`, and certifies the runtime
`FieldLoss` never exceeds the edge's declared `EdgeContract` census. Equality
is always semantic equality over canonical JSON (`spec/canonical-json.md`) —
never `==` on raw dicts.

TEMPLATE STATUS: pending completion of the `ocai.convert` harness. The suite
skips gracefully (importorskip) until that layer lands, so this file
documents the settled test shape without failing the world in the meantime.
When echo grows streaming, add a fold-triple fixture and a
`check_fold_triple` test in the same change (the streaming-first ratchet).
"""

from __future__ import annotations

from pathlib import Path

import pytest

conformance = pytest.importorskip(
    "ocai.convert.conformance",
    reason="ocai.convert conformance harness not landed yet (template pending)",
)
echo = pytest.importorskip(
    "ocai.contrib.echo",
    reason="echo fragment imports ocai.convert, not landed yet (template pending)",
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _edge_for(fixture: object) -> object:
    """Find the FRAGMENT edge whose (src, dst) matches the fixture's."""
    for edge in echo.FRAGMENT.edges:
        if (edge.src, edge.dst) == (fixture.src, fixture.dst):
            return edge
    raise AssertionError(f"no echo edge declared for fixture {fixture!r}")


def test_edges_satisfy_golden_fixtures() -> None:
    """Every fixture converts to `expect` with loss within the declared census."""
    paths = sorted(FIXTURES.glob("*.json"))
    assert paths, "template must ship at least one golden fixture"
    for path in paths:
        fixture = conformance.load_fixture(path)
        report = conformance.check_edge(_edge_for(fixture), fixture)
        # echo's contracts are empty (a lossless claim); hold the edges to it.
        assert not report.losses
        assert not report.shifts


def test_fragment_declares_no_import_time_globals() -> None:
    """The fragment is a frozen value; composing catalogs is the app's job."""
    from ocai.convert.catalog import Catalog

    catalog = Catalog.of(echo.FRAGMENT)
    assert echo.ECHO_CHAT_REQUEST in catalog.nodes
