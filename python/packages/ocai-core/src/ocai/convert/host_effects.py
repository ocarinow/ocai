"""Host effect declarations reuse census rules without inventing graph traversal."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from ocai.convert.contract import ContractViolation
from ocai.convert.contract import DeclaredDisposition
from ocai.convert.contract import EdgeContract
from ocai.core.canonjson import canonical
from ocai.core.fidelity import FidelityPolicyError
from ocai.core.fidelity import FidelityReport
from ocai.core.fidelity import FieldLoss
from ocai.core.fidelity import Route
from ocai.core.fidelity import SemanticShift
from ocai.core.usage import Usage


@dataclass(frozen=True)
class HostEffectContract:
    """A declared host-effect bound, not a graph edge or certification verdict."""

    census: Mapping[str, DeclaredDisposition] = field(
        default_factory=dict[str, DeclaredDisposition]
    )
    semantic_shifts: tuple[SemanticShift, ...] = ()

    def __post_init__(self) -> None:
        """Detach declaration data from the caller."""
        object.__setattr__(self, "census", deepcopy(dict(self.census)))
        object.__setattr__(self, "semantic_shifts", tuple(deepcopy(self.semantic_shifts)))

    def to_dict(self) -> dict[str, Any]:
        """Serialize only declarative content, without graph weights or callbacks."""
        return {
            "census": {
                path: {"disposition": value.disposition.value, "note": value.note}
                for path, value in self.census.items()
            },
            "semantic_shifts": [shift.to_dict() for shift in self.semantic_shifts],
        }

    @property
    def identity(self) -> str:
        """Hash declaration content deterministically, independently from execution."""
        return hashlib.sha256(canonical(self.to_dict()).encode()).hexdigest()

    def certify(
        self, losses: Iterable[FieldLoss], shifts: Iterable[SemanticShift]
    ) -> list[ContractViolation]:
        """Check findings with the same partial order and path rules as codecs."""
        return EdgeContract(self.census, self.semantic_shifts).certify(losses, shifts)


@dataclass(frozen=True)
class HostEffectDeclaration:
    """Detached inspection data; no executable callback or qualification claim."""

    host: str
    adapter: str
    contract: HostEffectContract
    configuration_id: str
    conformance_evaluated: bool = False


class HostContractError(FidelityPolicyError):
    """Host findings exceeded their declaration; rejected payload stays private."""

    def __init__(
        self,
        report: FidelityReport,
        violations: tuple[ContractViolation, ...],
        usage: Usage | None = None,
        route: Route | None = None,
    ) -> None:
        """Retain accounting and precise contract violations, never response data."""
        super().__init__(phase="host_contract", report=report, usage=usage, route=route)
        self.code = "host_contract_exceeded"
        self.violations = violations
