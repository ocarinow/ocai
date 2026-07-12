"""`ocai.convert` — meaning: the governed conversion catalog (architecture §4).

The layer that owns *what payloads mean* across provider interfaces and
canonical revisions. Depends on `ocai.core` only; movement (drivers, wire)
lives above it, which is why an offline audit tool can re-convert archived
traffic with this package and a plugin's fragments alone — no HTTP stack
installed.

The pieces and how they interact:

- `graph` — the Dijkstra planner and executor for one `Shape`: `Edge`
  (payload conversion) and `StreamEdge` (chunk transducer factory), planned
  by cost **derived** from each edge's contract; `convert` returns
  `Converted(value, report)`.
- `contract` — `EdgeContract`, the declared per-field disposition census an
  edge ships; source of the planner's lexicographic `LossGrade` and the
  baseline conformance certifies runtime loss against.
- `catalog` — scoped, governed composition: plugins export frozen
  `CatalogFragment`s; applications build an immutable `Catalog`
  (`Catalog.of(...)` or entry-point `Catalog.discover()`) under a
  `TrustPolicy`; `Catalog.lock()` hashes into every `Route`.
- `migrate` — IR self-migration: canonical revisions are graph nodes, so
  revision migration is ordinary certified edges.
- `conformance` — the harness plugins import to prove all of the above
  against golden fixtures (import as `ocai.convert.conformance`; its
  checkers are test-suite tools, not runtime API).
"""

from __future__ import annotations

from ocai.convert.catalog import ENTRY_POINT_GROUP
from ocai.convert.catalog import AdmissionError
from ocai.convert.catalog import Catalog
from ocai.convert.catalog import CatalogBuilder
from ocai.convert.catalog import CatalogFragment
from ocai.convert.catalog import CatalogLock
from ocai.convert.catalog import Component
from ocai.convert.catalog import ComponentFactory
from ocai.convert.catalog import ResolutionError
from ocai.convert.catalog import TrustPolicy
from ocai.convert.catalog import default_catalog
from ocai.convert.contract import ContractViolation
from ocai.convert.contract import DeclaredDisposition
from ocai.convert.contract import EdgeContract
from ocai.convert.contract import LossGrade
from ocai.convert.graph import ConversionError
from ocai.convert.graph import ConversionGraph
from ocai.convert.graph import Converted
from ocai.convert.graph import Edge
from ocai.convert.graph import EdgeFn
from ocai.convert.graph import EdgeOutput
from ocai.convert.graph import StreamConverter
from ocai.convert.graph import StreamConverterFactory
from ocai.convert.graph import StreamEdge
from ocai.convert.graph import StreamPipeline
from ocai.convert.migrate import register_revision_migration

__all__ = [
    "ENTRY_POINT_GROUP",
    "AdmissionError",
    "Catalog",
    "CatalogBuilder",
    "CatalogFragment",
    "CatalogLock",
    "Component",
    "ComponentFactory",
    "ContractViolation",
    "Converted",
    "ConversionError",
    "ConversionGraph",
    "DeclaredDisposition",
    "Edge",
    "EdgeContract",
    "EdgeFn",
    "EdgeOutput",
    "LossGrade",
    "ResolutionError",
    "StreamConverter",
    "StreamConverterFactory",
    "StreamEdge",
    "StreamPipeline",
    "TrustPolicy",
    "default_catalog",
    "register_revision_migration",
]
