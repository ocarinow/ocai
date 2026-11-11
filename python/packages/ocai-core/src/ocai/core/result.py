"""What every port returns, and what rides along with every call (§2.3).

`CallResult` is the uniform envelope **every** port returns, local or
remote — this is what makes governance, cost, tracing, and fallback compose
identically over FAISS and OpenAI. The `FidelityReport` lives *here and only
here*: IR payloads (e.g. `ChatResponse`) are pure graph payloads with no
report field — one home, not two.

`CallContext` is the per-request governance carrier, threaded through ports
as an optional keyword. A policy like "PII-classified traffic may not go to
provider X" needs the classification *at call time*; without a sanctioned
carrier, enterprises smuggle it through bags.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any
from typing import Literal

from ocai.core.evidence import HostEvidence
from ocai.core.fidelity import FidelityReport
from ocai.core.fidelity import Route
from ocai.core.usage import Usage


@dataclass(frozen=True, slots=True)
class CallResult[T]:
    """The uniform envelope every capability port returns.

    Assembled by the wire-backed facade after decode (route from
    `Catalog.resolve`, report merged across the request and response
    conversion legs) or built directly by an in-process adapter (which may
    leave `route` as None or stamp `route.host = "in-process"`).
    Port-tier `CallInterceptor`s see and may replace it wholesale — that is
    how fallback and semantic caching compose without touching payloads.

    Attributes:
        value: The capability payload — `ChatResponse`, `list[Embedding]`, …
        route: What ocai decided (node, pins, reason, catalog hash), or None
            for adapters that perform no resolution.
        report: THE fidelity account for this call. Payloads stay pure; the
            report has exactly this one home.
        usage: The capability's consumption record — the core-owned
            dimensional `Usage` model, uniform across capabilities.
        raw: The untouched provider response body for power users — never
            contains credentials.
        host_evidence: Optional detached native response and host metadata. Not part
            of the canonical payload and never automatically exported by observers.
    """

    value: T
    route: Route | None = None
    report: FidelityReport | None = None
    usage: Usage | None = None
    raw: Any | None = None
    host_evidence: HostEvidence | None = field(default=None, kw_only=True)


@dataclass(frozen=True, slots=True)
class CallContext:
    """The per-request governance carrier threaded through every port.

    Passed as the optional `ctx` keyword on port methods, seen by every
    `CallInterceptor` and policy hook on the way down, and available to
    observers on the way back up. It carries *facts about the caller and the
    call*, never payload data and never credentials.

    Attributes:
        compartment: Trusted isolation scope established by the platform.
        call_id: Optional logical invocation identifier.
        parent_id: Optional parent invocation identifier.
        correlation_id: Optional application correlation identifier.
        tenant: The tenancy the call is made on behalf of.
        principal: The end user or service identity initiating the call.
        classification: A data-classification label for the payload
            (e.g. `"pii"`, `"public"`) that routing policy can gate on.
        deadline: An absolute wall-clock deadline for the whole call,
            including retries. Must be timezone-aware; wire drivers enforce
            the remaining budget and reject late results. Synchronous custom
            transports must cooperate with request timeouts.
        tags: Free-form string labels for tracing/metering dimensions.
        extensions: A namespaced bag for enterprise-specific context fields
            that have no first-class slot (same namespacing convention as IR
            `extensions`).
    """

    tenant: str | None = None
    principal: str | None = None
    classification: str | None = None
    deadline: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict[str, str])
    extensions: dict[str, Any] = field(default_factory=dict[str, Any])
    compartment: str | None = None
    call_id: str | None = None
    parent_id: str | None = None
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the context to a plain JSON-compatible dict.

        Returns:
            A dict of the set fields; the `deadline` is ISO-8601 formatted.
        """
        out: dict[str, Any] = {}
        for name in ("compartment", "call_id", "parent_id", "correlation_id"):
            value = getattr(self, name)
            if value is not None:
                out[name] = value
        if self.tenant is not None:
            out["tenant"] = self.tenant
        if self.principal is not None:
            out["principal"] = self.principal
        if self.classification is not None:
            out["classification"] = self.classification
        if self.deadline is not None:
            out["deadline"] = self.deadline.isoformat()
        if self.tags:
            out["tags"] = dict(self.tags)
        if self.extensions:
            out["extensions"] = dict(self.extensions)
        return out


@dataclass(frozen=True)
class StreamOutcome:
    """Execution evidence, separate from the successful canonical StreamEnd.

    Missing usage means unknown, never zero. An incomplete or failed outcome
    may retain usage and conversion findings without claiming completion.
    This is a local execution contract, not a new canonical chunk or revision.
    """

    status: Literal["completed", "closed", "cancelled", "failed", "incomplete"]
    usage: Usage | None = None
    report: FidelityReport | None = None
    error: BaseException | None = None
