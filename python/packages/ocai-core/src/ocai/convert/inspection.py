"""Public conversion declarations and execution inspection, never certification."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from ocai.convert.contract import EdgeContract
from ocai.convert.host_effects import HostEffectDeclaration
from ocai.convert.resources import ConformanceResources
from ocai.core.fidelity import FidelityReport
from ocai.core.fidelity import Route
from ocai.core.identity import NodeId
from ocai.core.identity import Origin
from ocai.core.profile import CapabilityProfile
from ocai.core.profile import Support


@dataclass(frozen=True)
class EdgeDeclaration:
    """One selected edge's declaration; no executable callable is exposed."""

    src: NodeId
    dst: NodeId
    origin: Origin
    contract: EdgeContract


@dataclass(frozen=True)
class ConversionInspection:
    """Selected path and resource locations, distinct from conformance verdicts."""

    src: NodeId
    dst: NodeId
    edges: tuple[EdgeDeclaration, ...]
    catalog_hash: str
    streaming: bool = False
    resources: tuple[ConformanceResources, ...] = ()
    conformance_evaluated: bool = False


@dataclass(frozen=True)
class FeatureCoverage:
    """Declared support for a recognized request feature; None means unknown."""

    feature: str
    path: str
    support: Support | None
    model_pattern: str | None = None


@dataclass(frozen=True)
class ExecutionInspection:
    """Detached inspection data; none of these declarations proves qualification.

    Request findings are payload-specific. Response findings are not known yet.
    Coverage enumerates recognized feature keys, never the complete open feature
    universe. Resource locations are evidence pointers, not certification results.
    Configuration identity excludes credentials, which rotate at the transport leaf.
    """

    route: Route
    request_path: ConversionInspection
    response_path: ConversionInspection
    profiles: tuple[CapabilityProfile, ...]
    coverage: tuple[FeatureCoverage, ...]
    request_report: FidelityReport
    configuration_id: str
    streaming: bool = False
    coverage_complete: bool = False
    host_effects: tuple[HostEffectDeclaration, ...] = field(default=(), kw_only=True)
