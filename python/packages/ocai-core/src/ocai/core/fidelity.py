"""What conversion cost: the fidelity vocabulary (architecture §2.2).

A conversion records **what it cost**, not just whether it succeeded. As a
payload traverses the graph, each edge emits field-level `FieldLoss` records
and semantics-level `SemanticShift` records; the per-edge `EdgeReport`s roll
up into one `FidelityReport` — the single report type the whole library
speaks, delivered on `CallResult.report` (payloads stay pure).

Field loss and semantic divergence are **different kinds of honesty**:
a `FieldLoss` says what happened to one field's *data*; a `SemanticShift`
says the *meaning or mechanics* moved (a system role relocated into
`systemInstruction`, a transcript replayed to emulate a server-side thread,
a tool-call id regenerated). Conflating them understates what a migration
cost, so they are separate records with separate vocabularies.

`Route` is the decision record: which node ocai chose, what the caller
pinned, why, and under which catalog. A `Route` plus a catalog lockfile
reconstructs exactly which conversion logic served a call — the audit joint.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from enum import Enum
from typing import Any
from typing import Final
from typing import Self

from ocai.core.errors import OcaiError
from ocai.core.identity import Capability
from ocai.core.identity import NodeId
from ocai.core.identity import Shape
from ocai.core.ir import is_json_array
from ocai.core.ir import is_json_object
from ocai.core.usage import Usage


class Disposition(str, Enum):
    """What became of one field as a conversion edge crossed it.

    Attributes:
        EXACT: Carried through unchanged.
        RENAMED: Mapped to a differently-named field with the same meaning.
        APPROXIMATED: Mapped to a near-equivalent that is not exact
            (including out-of-range values passed verbatim).
        EMULATED: The destination has no native support; the effect is
            reproduced by other means (see `SemanticShift` for the how).
        EXTENSIONS: Preserved in the `extensions` bag — recoverable, but not
            a first-class canonical field. Distinct from `DROPPED`.
        DROPPED: Discarded; the destination cannot represent it. Lost.
        UNSUPPORTED: The destination rejects the field outright (a hard gap —
            e.g. a `ProviderRef` crossing its minting interface).
    """

    EXACT = "exact"
    RENAMED = "renamed"
    APPROXIMATED = "approximated"
    EMULATED = "emulated"
    EXTENSIONS = "extensions"
    DROPPED = "dropped"
    UNSUPPORTED = "unsupported"


# Dispositions that degrade information or behavior. EXACT/RENAMED/EXTENSIONS
# preserve everything recoverably; these four do not, and they are what the
# derived `lossless` flags key off.
_LOSSY = frozenset(
    {
        Disposition.APPROXIMATED,
        Disposition.EMULATED,
        Disposition.DROPPED,
        Disposition.UNSUPPORTED,
    }
)


class ShiftKind:
    """Canonical constants for `SemanticShift.kind` — an **open** vocabulary.

    `kind` is an open string code, not an enum: edges may mint new kinds
    (namespaced for plugins) without a core release. These constants name the
    kinds core itself emits.

    Attributes:
        RELOCATION: Content moved to a structurally different home with the
            same meaning (system role → `systemInstruction`).
        EMULATION: Behavior reproduced by different mechanics (server-side
            conversation state emulated by transcript replay).
        ID_REGENERATED: A correlation id could not survive the boundary and
            was re-minted (tool-call ids across providers).
        RANGE_PASSTHROUGH: A value outside the destination's documented range
            was passed verbatim — never rescaled, never clamped.
    """

    RELOCATION: Final = "relocation"
    EMULATION: Final = "emulation"
    ID_REGENERATED: Final = "id_regenerated"
    RANGE_PASSTHROUGH: Final = "range_passthrough"


def _decode_disposition(code: Any) -> Disposition:
    """Decode a serialized disposition code, totally.

    An unrecognized (or non-string) code decodes to `Disposition.DROPPED` —
    the conservative bucket: a replayed report may overstate loss, never
    understate it (a newer ocai's disposition code names some kind of
    change, and claiming `EXACT` for it would be the one dishonest answer).

    Args:
        code: The serialized disposition value.

    Returns:
        The decoded `Disposition`.
    """
    try:
        return Disposition(code)
    except ValueError:
        return Disposition.DROPPED


def _released_from_tag(tag: str) -> date:
    """Derive a `released` sort key from a dated revision tag, totally.

    Node labels (`provider/interface@tag#shape`) do not carry the release
    date, so a replayed node re-derives it from the tag when the tag is a
    full ISO date or a `YYYY-MM` month (canonical tags always are). A tag
    that is neither gets `date.min` — a sentinel that keeps the replayed
    record usable for rendering while never claiming a real ordering.

    Args:
        tag: The node's opaque revision tag.

    Returns:
        The derived release date, or `date.min` when underivable.
    """
    for candidate in (tag, f"{tag}-01", f"{tag}-01-01"):
        try:
            return date.fromisoformat(candidate)
        except ValueError:
            continue
    return date.min


def _node_from_label(label: str) -> NodeId:
    """Decode a compact node label back into a `NodeId`, totally.

    The inverse of `NodeId.__str__` (`provider/interface@tag#shape`), for
    replaying recorded reports. The label does not carry `released` or
    `status`, so the replayed node derives `released` from the tag (see
    `_released_from_tag`) and keeps the default status. A malformed label
    lands whole in `provider` with empty coordinates — preserved, never
    raised on.

    Args:
        label: The serialized node label.

    Returns:
        The decoded `NodeId`.
    """
    try:
        rest, shape_token = label.rsplit("#", 1)
        provider_interface, tag = rest.rsplit("@", 1)
        provider, interface = provider_interface.split("/", 1)
    except ValueError:
        return NodeId(
            provider=label,
            interface="",
            tag="",
            shape=Shape(Capability(""), ""),
            released=date.min,
        )
    capability, _, role = shape_token.partition(".")
    return NodeId(
        provider=provider,
        interface=interface,
        tag=tag,
        shape=Shape(Capability(capability), role),
        released=_released_from_tag(tag),
    )


@dataclass(frozen=True, slots=True)
class FieldLoss:
    """One field-level record of what a conversion edge did to a field.

    Attributes:
        path: A dotted/bracketed path to the field
            (e.g. `"messages[0].parts[2].args_json"`).
        disposition: What happened to the field.
        severity: A diagnostic information-cost weight (0.0 == lossless).
            Report views sum it; the *planner* weight comes from the edge's
            declared `EdgeContract` LossGrade, never from this number.
        note: A human-readable explanation of the mapping or the loss.
    """

    path: str
    disposition: Disposition
    severity: float = 0.0
    note: str = ""

    @property
    def lossy(self) -> bool:
        """Return whether this record degrades information or behavior."""
        return self.disposition in _LOSSY

    def to_dict(self) -> dict[str, Any]:
        """Serialize the record to a plain JSON-compatible dict.

        Returns:
            A dict with `path`, the `disposition` value, `severity`, and
            `note`.
        """
        return {
            "path": self.path,
            "disposition": self.disposition.value,
            "severity": self.severity,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `FieldLoss` from a serialized dict, totally.

        An unrecognized disposition code decodes to `Disposition.DROPPED`
        (see `_decode_disposition`); a non-numeric severity decodes to 0.0.

        Args:
            data: A mapping with `path`, `disposition`, and the optional
                `severity`/`note`.

        Returns:
            The decoded `FieldLoss`.
        """
        severity = data.get("severity", 0.0)
        if isinstance(severity, bool) or not isinstance(severity, (int, float)):
            severity = 0.0
        return cls(
            path=str(data.get("path", "")),
            disposition=_decode_disposition(data.get("disposition")),
            severity=float(severity),
            note=str(data.get("note", "")),
        )


@dataclass(frozen=True, slots=True)
class SemanticShift:
    """A semantics-level divergence record, distinct from field mapping.

    Emitted alongside `FieldLoss` records when an edge changed *how* something
    works rather than *what data* a field holds. Shifts do not flip the
    derived `lossless` flag (the information survived); they are surfaced
    separately so a migration's behavioral cost is never understated.

    Attributes:
        kind: The open shift-kind code; canonical constants on `ShiftKind`.
            Plugin-minted kinds must be namespaced (`"anthropic.xyz"`).
        path: A dotted/bracketed path to the affected location, when one
            location is identifiable.
        note: A human-readable explanation of the divergence.
    """

    kind: str
    path: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize the shift to a plain JSON-compatible dict.

        Returns:
            A dict with `kind`, `path`, and `note`.
        """
        return {"kind": self.kind, "path": self.path, "note": self.note}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `SemanticShift` from a serialized dict, totally.

        `kind` is an open code, so any string passes through verbatim.

        Args:
            data: A mapping with `kind` and the optional `path`/`note`.

        Returns:
            The decoded `SemanticShift`.
        """
        return cls(
            kind=str(data.get("kind", "")),
            path=str(data.get("path", "")),
            note=str(data.get("note", "")),
        )


@dataclass(frozen=True, slots=True)
class EdgeReport:
    """The losses and shifts incurred by traversing one conversion edge.

    Produced by an edge's conversion function; the conformance harness
    certifies at build time that these runtime records never exceed the
    edge's declared `EdgeContract` census.

    Attributes:
        src: The edge's source node.
        dst: The edge's destination node.
        losses: The per-field records this edge emitted, in order.
        shifts: The semantics-level records this edge emitted, in order.
        note: A human-readable description of the edge's conversion.
    """

    src: NodeId
    dst: NodeId
    losses: tuple[FieldLoss, ...] = ()
    shifts: tuple[SemanticShift, ...] = ()
    note: str = ""

    @property
    def cost(self) -> float:
        """Return the summed diagnostic `severity` across this edge's losses.

        A report view, not a planner input — planner weight is derived from
        the edge's `EdgeContract`.
        """
        return sum(loss.severity for loss in self.losses)

    @property
    def lossless(self) -> bool:
        """Return whether this edge preserved all information and behavior."""
        return not any(loss.lossy for loss in self.losses)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the edge report to a plain JSON-compatible dict.

        Returns:
            A dict with `src`/`dst` labels, the `note`, the summed `cost`,
            and the serialized `losses` and `shifts`.
        """
        return {
            "src": str(self.src),
            "dst": str(self.dst),
            "note": self.note,
            "cost": self.cost,
            "losses": [loss.to_dict() for loss in self.losses],
            "shifts": [shift.to_dict() for shift in self.shifts],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build an `EdgeReport` from a serialized dict, totally.

        The `src`/`dst` node labels decode via `_node_from_label`; the
        serialized `cost` is ignored — it is derived from the loss records,
        never trusted from data (`lossless` honesty applies to replay too).

        Args:
            data: A mapping with the `src`/`dst` labels and the optional
                `losses`/`shifts`/`note`.

        Returns:
            The decoded `EdgeReport`.
        """
        raw_losses = data.get("losses")
        raw_shifts = data.get("shifts")
        return cls(
            src=_node_from_label(str(data.get("src", ""))),
            dst=_node_from_label(str(data.get("dst", ""))),
            losses=tuple(
                FieldLoss.from_dict(loss)
                for loss in (raw_losses if is_json_array(raw_losses) else [])
                if is_json_object(loss)
            ),
            shifts=tuple(
                SemanticShift.from_dict(shift)
                for shift in (raw_shifts if is_json_array(raw_shifts) else [])
                if is_json_object(shift)
            ),
            note=str(data.get("note", "")),
        )


@dataclass(frozen=True, slots=True)
class HostEffectReport:
    """Actual host effects, separate from graph edges and qualification evidence.

    Attributes:
        host: Non-secret host identity supplied by the adapter.
        adapter: Versioned adapter identity responsible for these findings.
        contract_id: Identity of the declaration governing these effects, not certification.
        phase: Open execution phase code, initially request or response.
        losses: Field effects recorded by this adapter invocation.
        shifts: Semantic effects recorded by this adapter invocation.
    """

    host: str
    adapter: str
    contract_id: str
    phase: str
    losses: tuple[FieldLoss, ...] = ()
    shifts: tuple[SemanticShift, ...] = ()

    @property
    def cost(self) -> float:
        """Return diagnostic severity, never graph planner weight."""
        return sum(loss.severity for loss in self.losses)

    @property
    def lossless(self) -> bool:
        """Return whether field information survived; shifts remain separate."""
        return not any(loss.lossy for loss in self.losses)

    def to_dict(self) -> dict[str, Any]:
        """Serialize provenance and findings without inventing graph coordinates."""
        return {
            "host": self.host, "adapter": self.adapter, "contract_id": self.contract_id,
            "phase": self.phase, "cost": self.cost,
            "losses": [loss.to_dict() for loss in self.losses],
            "shifts": [shift.to_dict() for shift in self.shifts],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Decode findings totally, preserving open phase and semantic codes."""
        raw_losses = data.get("losses")
        raw_shifts = data.get("shifts")
        return cls(
            host=str(data.get("host", "")), adapter=str(data.get("adapter", "")),
            contract_id=str(data.get("contract_id", "")), phase=str(data.get("phase", "")),
            losses=tuple(FieldLoss.from_dict(loss)
                for loss in (raw_losses if is_json_array(raw_losses) else [])
                if is_json_object(loss)),
            shifts=tuple(SemanticShift.from_dict(shift)
                for shift in (raw_shifts if is_json_array(raw_shifts) else [])
                if is_json_object(shift)),
        )


@dataclass(slots=True)
class FidelityReport:
    """The accumulated graph conversion and host-effect account of one call.

    The single report type the library speaks. It lives on
    `CallResult.report` and on the terminal `StreamEnd` of a stream — and
    only there; IR payloads never carry a report. Built by appending one
    `EdgeReport` per traversed edge; the request leg and the response leg of
    a call are folded together with `merge`.

    `lossless` is **derived, never asserted**: it is recomputed from the
    records every time, so no edge can claim fidelity its records contradict.

    Attributes:
        edges: One `EdgeReport` per traversed edge, in traversal order.
        hosts: Actual host effects, in insertion order, separate from graph traversal.
    """

    edges: list[EdgeReport] = field(default_factory=list[EdgeReport])
    hosts: list[HostEffectReport] = field(default_factory=list[HostEffectReport], kw_only=True)

    @property
    def path(self) -> list[NodeId]:
        """Return the ordered nodes visited, derived from the edge records.

        Empty when no edge was traversed (an identity conversion).
        """
        if not self.edges:
            return []
        return [self.edges[0].src, *(edge.dst for edge in self.edges)]

    @property
    def losses(self) -> list[FieldLoss]:
        """Return graph then host field records, preserving order within each lane."""
        return ([loss for edge in self.edges for loss in edge.losses]
                + [loss for host in self.hosts for loss in host.losses])

    @property
    def shifts(self) -> list[SemanticShift]:
        """Return graph then host semantic records, preserving order within each lane."""
        return ([shift for edge in self.edges for shift in edge.shifts]
                + [shift for host in self.hosts for shift in host.shifts])

    @property
    def dropped(self) -> list[FieldLoss]:
        """Return the records for fields that were dropped or unsupported."""
        return [
            loss
            for loss in self.losses
            if loss.disposition in (Disposition.DROPPED, Disposition.UNSUPPORTED)
        ]

    @property
    def lossless(self) -> bool:
        """Return whether the whole conversion preserved all information.

        Derived from the field records (`SemanticShift`s do not flip it —
        they are reported in their own lane via `shifts`).
        """
        return not any(loss.lossy for loss in self.losses)

    @property
    def total_cost(self) -> float:
        """Return diagnostic cost across graph and host records, never planner weight."""
        return sum(edge.cost for edge in self.edges) + sum(host.cost for host in self.hosts)

    def merge(self, other: Self) -> Self:
        """Fold `other` into `self` (in place) and return `self`.

        Both lanes concatenate without deduplication — typically the response leg
        folded onto the request leg by the facade before it assembles the
        `CallResult`.

        Args:
            other: The report to fold in.

        Returns:
            `self`, after folding in `other`.
        """
        self.edges.extend(other.edges)
        self.hosts.extend(other.hosts)
        return self

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report to a plain JSON-compatible dict.

        Returns:
            A dict with the `path` (node labels), `lossless`, `total_cost`,
            and the serialized `edges`.
        """
        out: dict[str, Any] = {
            "path": [str(node) for node in self.path],
            "lossless": self.lossless,
            "total_cost": self.total_cost,
            "edges": [edge.to_dict() for edge in self.edges],
        }
        if self.hosts:
            out["hosts"] = [host.to_dict() for host in self.hosts]
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `FidelityReport` from a serialized dict, totally.

        Only `edges` and `hosts` are read: `path`, `lossless`, and `total_cost` are
        derived views, recomputed from the decoded records every time — a
        replayed report can no more assert fidelity its records contradict
        than a live one can. This is what lets a recorded `StreamEnd`
        replay with its report intact.

        Args:
            data: A mapping with serialized edges and optional host effects.

        Returns:
            The decoded `FidelityReport`.
        """
        raw_edges = data.get("edges")
        raw_hosts = data.get("hosts")
        return cls(
            edges=[
                EdgeReport.from_dict(edge)
                for edge in (raw_edges if is_json_array(raw_edges) else [])
                if is_json_object(edge)
            ],
            hosts=[HostEffectReport.from_dict(host)
                for host in (raw_hosts if is_json_array(raw_hosts) else [])
                if is_json_object(host)],
        )


@dataclass(frozen=True, slots=True)
class Route:
    """What ocai *decided* for one call — the audit joint.

    Records the resolution `Catalog.resolve(capability, provider, pins)`
    performed: the chosen node (interface + tag), what the caller pinned,
    the human-readable reason, and the hash of the catalog lockfile the
    decision was made under. A `Route` plus that lockfile reconstructs
    exactly which conversion logic (down to plugin distribution versions)
    served a call. Delivered on `CallResult.route`.

    Attributes:
        capability: The capability the call was made against.
        node: The chosen graph node (provider, interface, tag, shape, …).
        requested_interface: The interface the caller pinned, or None for
            "let ocai choose".
        requested_tag: The revision tag the caller pinned, or None for
            "latest stable".
        reason: A human-readable resolution explanation
            (e.g. `"latest stable, released 2026-01-15"`).
        catalog_hash: The hash of the `Catalog.lock()` lockfile the
            resolution was made under; empty for catalog-less adapters.
        host: Where the call was physically sent — a host label or
            `"in-process"` for local adapters. Stamped after host resolution
            (hosting lives below the graph), so resolution itself never
            knows clouds exist.
    """

    capability: Capability
    node: NodeId
    requested_interface: str | None = None
    requested_tag: str | None = None
    reason: str = ""
    catalog_hash: str = ""
    host: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the route to a plain JSON-compatible dict.

        Returns:
            A dict with the `capability`, the `node` label, the requested
            pins, the `reason`, the `catalog_hash`, and the `host` when set.
        """
        return {
            "capability": str(self.capability),
            "node": str(self.node),
            "requested_interface": self.requested_interface,
            "requested_tag": self.requested_tag,
            "reason": self.reason,
            "catalog_hash": self.catalog_hash,
            "host": self.host,
        }


class FidelityPolicyError(OcaiError):
    """Conversion policy rejected execution; accounting survives without payloads."""

    def __init__(
        self,
        *,
        phase: str,
        report: FidelityReport,
        usage: Usage | None = None,
        route: Route | None = None,
        delivered_events: int = 0,
    ) -> None:
        """Retain detached evidence, never the rejected response or raw body."""
        super().__init__(f"conversion policy rejected {phase}")
        self.phase = phase
        self.report = deepcopy(report)
        self.usage = deepcopy(usage)
        self.route = route
        self.delivered_events = delivered_events
        self.partial = delivered_events > 0


@dataclass(frozen=True)
class FidelityPolicy:
    """Caller-defined acceptance over both field records and semantic shifts.

    Predicates receive detached records and must be pure. A raising predicate
    rejects execution. Predicates are re-evaluated before every physical attempt;
    closures are application policy code, not portable conformance evidence.
    Neither semantic acceptance nor coverage is inferred from report.lossless.
    """

    forbidden_dispositions: frozenset[Disposition] = frozenset()
    forbidden_shifts: frozenset[str] = frozenset()
    allow_loss: Callable[[FieldLoss], bool] | None = None
    allow_shift: Callable[[SemanticShift], bool] | None = None

    def enforce(
        self,
        report: FidelityReport,
        *,
        phase: str,
        usage: Usage | None = None,
        route: Route | None = None,
        delivered_events: int = 0,
    ) -> None:
        """Reject forbidden findings while retaining usage and the complete ledger."""
        accepted = True
        try:
            for loss in report.losses:
                    if loss.disposition in self.forbidden_dispositions:
                        accepted = False
                    if self.allow_loss is not None and not self.allow_loss(deepcopy(loss)):
                        accepted = False
            for shift in report.shifts:
                    if shift.kind in self.forbidden_shifts:
                        accepted = False
                    if self.allow_shift is not None and not self.allow_shift(deepcopy(shift)):
                        accepted = False
        except Exception:
            accepted = False
        if not accepted:
            raise FidelityPolicyError(
                phase=phase,
                report=report,
                usage=usage,
                route=route,
                delivered_events=delivered_events,
            )
