"""Pure, invocation-local host outcome adapters; no provider SDK or I/O."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from ocai.convert.contract import ContractViolation
from ocai.convert.host_effects import HostEffectContract
from ocai.convert.host_effects import HostEffectDeclaration
from ocai.core.canonjson import canonical
from ocai.core.errors import OcaiError
from ocai.core.evidence import HostEvidence
from ocai.core.fidelity import FieldLoss
from ocai.core.fidelity import HostEffectReport
from ocai.core.fidelity import SemanticShift
from ocai.core.ir import is_json_object
from ocai.wire.http import HttpResponse


def _result(value: object) -> OcaiError | None:
    """Validate an application callback at the untyped execution boundary."""
    if value is not None and not isinstance(value, OcaiError):
        raise TypeError("host error mapper must return an ocai error or None")
    return value


def preserve_error_evidence(mapped: OcaiError, original: OcaiError) -> OcaiError:
    """Keep native response evidence independent from the new classification."""
    mapped.response_headers = deepcopy(original.response_headers)
    mapped.response_body = original.response_body
    if original.raw is not None:
        mapped.raw = deepcopy(original.raw)
    if original.status is not None:
        mapped.status = original.status
    if original.provider is not None:
        mapped.provider = original.provider
    if mapped.retry_after is None:
        mapped.retry_after = original.retry_after
    if mapped.code is None:
        mapped.code = original.code
    return mapped


@dataclass(frozen=True)
class HostErrorMapper:
    """Declare a pure host error classifier with explicit, detached options.

    The callback receives a copy of an ocai error containing native response
    evidence. None declines to the existing dialect/coarse fallback. A returned
    error claims classification; native evidence remains unchanged. Callbacks
    must use declared options rather than hidden mutable state. They never
    receive authenticated requests or SDK objects.
    """

    name: str
    mapper: Callable[[OcaiError, dict[str, Any]], OcaiError | None]
    options: Mapping[str, Any] = field(default_factory=dict[str, Any])

    def __post_init__(self) -> None:
        """Snapshot non-secret JSON configuration without invoking the mapper."""
        if not self.name:
            raise ValueError("host error mapping requires a name")
        options = deepcopy(dict(self.options))
        canonical(options)
        object.__setattr__(self, "options", options)

    def snapshot(self) -> HostErrorMapper:
        """Detach declaration data while preserving callback ownership."""
        return HostErrorMapper(self.name, self.mapper, self.options)

    def __deepcopy__(self, memo: dict[int, Any]) -> HostErrorMapper:
        result = self.snapshot()
        memo[id(self)] = result
        return result

    @property
    def configuration_id(self) -> str:
        """Identify declared data and callback ownership for in-process approval."""
        function = getattr(self.mapper, "__func__", self.mapper)
        owner = getattr(self.mapper, "__self__", None)
        return hashlib.sha256(
            canonical(
                {
                    "name": self.name,
                    "options": dict(self.options),
                    "mapper": id(function),
                    "owner": id(owner) if owner is not None else None,
                }
            ).encode()
        ).hexdigest()

    def apply(self, error: OcaiError) -> OcaiError | None:
        """Classify HTTP evidence, fail closed on invalid/raising callbacks.

        Connection failures have no HTTP status and are left to the existing
        fallback. The original error and declaration cannot be mutated through
        the callback. Callback exceptions are not chained or exposed as text.
        """
        if error.status is None:
            return None
        try:
            mapped = _result(self.mapper(deepcopy(error), deepcopy(dict(self.options))))
            if mapped is None:
                return None
            return preserve_error_evidence(deepcopy(mapped), error)
        except Exception:
            failure = OcaiError("host error adaptation failed", code="host_error_adaptation_failed")
        return preserve_error_evidence(failure, error)


@dataclass(frozen=True)
class HostAdaptation:
    """A pure unary host adapter's dialect payload, metadata and actual effects."""

    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict[str, Any])
    losses: tuple[FieldLoss, ...] = ()
    shifts: tuple[SemanticShift, ...] = ()
    error: OcaiError | None = None


def _validate_records(values: Iterable[object], kind: type[object]) -> None:
    """Check untyped callback records before they enter public report contracts."""
    if any(not isinstance(value, kind) for value in values):
        raise TypeError("invalid host findings")


def _adaptation_result(value: object) -> HostAdaptation:
    """Validate a callback result at the execution boundary."""
    if not isinstance(value, HostAdaptation):
        raise TypeError("invalid host adaptation result")
    _validate_records(value.losses, FieldLoss)
    _validate_records(value.shifts, SemanticShift)
    _result(value.error)
    return value


@dataclass(frozen=True)
class AdaptedHostResponse:
    """Validated adapter output with immutable attribution and census evidence."""

    payload: dict[str, Any]
    evidence: HostEvidence
    report: HostEffectReport
    violations: tuple[ContractViolation, ...] = ()
    error: OcaiError | None = None


@dataclass(frozen=True)
class HostResponseAdapter:
    """Explicit pure unary response adaptation; SDKs and requests stay outside."""

    host: str
    name: str
    adapter: Callable[[HttpResponse, dict[str, Any], dict[str, Any]], HostAdaptation]
    contract: HostEffectContract = field(default_factory=HostEffectContract)
    options: Mapping[str, Any] = field(default_factory=dict[str, Any])

    def __post_init__(self) -> None:
        """Snapshot declaration and non-secret JSON configuration."""
        if not self.host or not self.name:
            raise ValueError("host response adaptation requires host and adapter identities")
        options = deepcopy(dict(self.options))
        canonical(options)
        object.__setattr__(self, "options", options)
        object.__setattr__(self, "contract", deepcopy(self.contract))

    def snapshot(self) -> HostResponseAdapter:
        """Detach data while retaining callable ownership."""
        return HostResponseAdapter(self.host, self.name, self.adapter, self.contract, self.options)

    def __deepcopy__(self, memo: dict[int, Any]) -> HostResponseAdapter:
        result = self.snapshot()
        memo[id(self)] = result
        return result

    @property
    def configuration_id(self) -> str:
        """Identify declared configuration and in-process callable ownership."""
        function = getattr(self.adapter, "__func__", self.adapter)
        owner = getattr(self.adapter, "__self__", None)
        return hashlib.sha256(
            canonical(
                {
                    "host": self.host,
                    "name": self.name,
                    "contract": self.contract.identity,
                    "options": dict(self.options),
                    "adapter": id(function),
                    "owner": id(owner) if owner is not None else None,
                }
            ).encode()
        ).hexdigest()

    @property
    def declaration(self) -> HostEffectDeclaration:
        """Expose a detached declaration without claiming provider qualification."""
        return HostEffectDeclaration(
            self.host, self.name, deepcopy(self.contract), self.configuration_id
        )

    def apply(self, response: HttpResponse, payload: dict[str, Any]) -> AdaptedHostResponse:
        """Adapt detached facts and retain native evidence, failing closed on misuse."""
        try:
            value = _adaptation_result(
                self.adapter(deepcopy(response), deepcopy(payload), deepcopy(dict(self.options)))
            )
            if not is_json_object(value.payload) or not is_json_object(value.metadata):
                raise TypeError("host adaptation must return JSON objects")
            canonical(value.payload)
            canonical(value.metadata)
            evidence = HostEvidence(
                self.host,
                self.name,
                response.status,
                response.headers,
                response.body,
                value.metadata,
            )
            report = HostEffectReport(
                self.host,
                self.name,
                self.contract.identity,
                "response",
                tuple(value.losses),
                tuple(value.shifts),
            )
            return AdaptedHostResponse(
                deepcopy(value.payload),
                evidence,
                report,
                tuple(self.contract.certify(report.losses, report.shifts)),
                deepcopy(value.error),
            )
        except Exception:
            failure = OcaiError(
                "host response adaptation failed",
                code="host_response_adaptation_failed",
                status=response.status,
                response_headers=response.headers,
                response_body=response.body,
                host_evidence=HostEvidence(
                    self.host, self.name, response.status, response.headers, response.body
                ),
            )
        raise failure from None
