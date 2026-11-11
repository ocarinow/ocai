"""Detached host execution evidence, separate from capability payloads."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass(frozen=True, slots=True)
class HostEvidence:
    """Native response facts and adapter metadata for authorized application use.

    None means unavailable; an empty body/header map is known empty evidence.
    Values are detached, never SDK objects or outgoing credentials. This carrier
    is not exported by passive observers and is not a canonical capability payload.
    """

    host: str
    adapter: str
    response_status: int | None = None
    response_headers: dict[str, str] | None = None
    response_body: bytes | None = None
    metadata: dict[str, Any] = field(default_factory=dict[str, Any])

    def __post_init__(self) -> None:
        """Detach mutable evidence from the adapter and transport."""
        object.__setattr__(self, "response_headers", deepcopy(self.response_headers))
        object.__setattr__(self, "metadata", deepcopy(self.metadata))
