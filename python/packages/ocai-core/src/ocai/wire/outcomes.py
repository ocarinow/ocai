"""Pure, invocation-local host outcome adapters; no provider SDK or I/O."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from ocai.core.canonjson import canonical
from ocai.core.errors import OcaiError


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
