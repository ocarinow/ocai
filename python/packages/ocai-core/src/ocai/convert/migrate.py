"""IR self-migration: canonical revisions convert through the graph (§4.4).

The canonical IR is *just another interface* (`ocai`), with dated revisions
(`ocai@2026-07`) — so migrating the IR is not a special code path, a script,
or a breaking release. When a new canonical revision ships (say
`ocai@2027-01`), core registers ordinary conversion edges
`2026-07 ↔ 2027-01` here: each with an `EdgeContract` (the migration's
declared per-field census), golden fixtures in `spec/fixtures/`, and the
same conformance certification every provider edge gets.

Consequences this module exists to guarantee:

- **Archived transcripts convert forward** through the same honest
  machinery — a bank re-reading two-year-old `ocai@2026-07` traffic plans a
  path through the migration edges and gets a `FidelityReport` saying
  exactly what the revision change cost.
- **Plugins upgrade independently** — a plugin still speaking `2026-07`
  keeps working against a `2027-01` application because the planner routes
  through the migration hop (visible in the report, never silent).
- **`PartUnknown` payloads are upgradeable** — content decoded under an old
  revision's Unknown fallback can be re-decoded once the revision that
  names it exists.

The migration edges live in a fragment like any other; nothing here mutates
global state.
"""

from __future__ import annotations

from collections.abc import Iterable

from ocai.convert.catalog import CatalogBuilder
from ocai.convert.graph import Edge


def register_revision_migration(
    builder: CatalogBuilder,
    src_rev: str,
    dst_rev: str,
    edges: Iterable[Edge],
) -> None:
    """Stage certified migration edges between two canonical revisions.

    Wraps `edges` in an ocai-originated `CatalogFragment` that publishes the
    canonical nodes for `src_rev` and `dst_rev` and adds it to `builder`, so
    the migration participates in planning, lockfiles, and admission exactly
    like provider conversion logic. Every edge must connect canonical nodes
    at the two named revisions — a migration never touches provider
    interfaces (cross-provider paths reach it through the canonical
    backbone).

    Args:
        builder: The catalog composition to stage the migration into.
        src_rev: The older canonical revision tag (e.g. `"2026-07"`).
        dst_rev: The newer canonical revision tag (e.g. `"2027-01"`).
        edges: The migration edges, one per shape and direction, each
            carrying its `EdgeContract` (forward edges are typically
            lossless; backward edges declare what the older revision cannot
            express).

    Raises:
        ValueError: If an edge endpoint is not a canonical node at
            `src_rev` or `dst_rev`.
    """
    # TODO: validate each edge's endpoints are canonical nodes (provider
    # `ocai`) tagged exactly src_rev/dst_rev, build a CatalogFragment with
    # Origin("ocai", core __version__) publishing both revisions' nodes,
    # and builder.add() it.
    raise NotImplementedError
