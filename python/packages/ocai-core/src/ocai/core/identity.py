"""Four-level identity: who is speaking (architecture §2.1).

Every payload that crosses a conversion boundary is identified at four levels,
each owning exactly one kind of change:

- `Capability` — the semantic job a user programs against (`"chat"`).
- `Shape` — a message schema role within a capability (`"chat.request"`).
- `NodeId` — the conversion-graph node: one provider *interface* revision of
  one shape. `interface` is the coordinate the old `SchemaVersion` was
  missing — `openai/chat_completions` and `openai/responses` are *concurrent
  sibling interfaces* of one capability, not versions of each other.
- `Origin` — the provenance stamp `(distribution, version)` carried by every
  node and edge a plugin registers, so reports and audit records can say who
  shipped the conversion logic that served a call.

The canonical IR is **just another interface**, named `ocai`, with dated
revisions (`ocai@2026-07`). IR migration therefore *is* graph conversion — no
special case. `canonical_node` builds those nodes.

Everything here is a frozen, hashable value object: `NodeId` is a dict key in
every `Catalog`, and `Shape` partitions graphs (graphs never mix shapes).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

# The provider and interface labels of the canonical IR. Canonical is not a
# special case anywhere: it is provider "ocai" publishing interface "ocai".
CANONICAL_PROVIDER = "ocai"
CANONICAL_INTERFACE = "ocai"

# The current canonical IR revision — a dated tag on the `ocai` interface,
# distinct from the library semver and from any provider interface tag
# (three version axes, never conflated).
CANONICAL_REVISION = "2026-07"


@dataclass(frozen=True, slots=True)
class Capability:
    """The semantic job a user programs against.

    One canonical IR and one port `Protocol` exist per capability; the
    capability is the top of the identity hierarchy and the first argument to
    `Catalog.resolve`. An open value object rather than a closed enum so a
    contrib distribution can mint `Capability("rerank")` without touching
    `ocai.core`.

    Attributes:
        name: The capability's stable identifier (e.g. `"chat"`).
    """

    name: str

    def __str__(self) -> str:
        """Return the capability name."""
        return self.name


# The core-shipped capabilities. Contrib packages may mint additional ones.
CHAT = Capability("chat")
EMBEDDING = Capability("embedding")
VECTORSTORE = Capability("vectorstore")


@dataclass(frozen=True, slots=True)
class Shape:
    """A message schema role within a capability — the graph partition key.

    A `Shape` pairs a `Capability` with an open `role` code and renders as a
    dotted token (`"chat.request"`). Because the role is qualified by
    capability, a chat request and an embedding request are different shapes
    and live in different graphs; the planner never mixes shapes on one path.

    Attributes:
        capability: The capability this message belongs to.
        role: The message's role within its capability — an open string code
            with canonical constants `request`, `response`, `chunk`.
    """

    capability: Capability
    role: str

    def __str__(self) -> str:
        """Return the dotted `capability.role` token (e.g. `"chat.request"`)."""
        return f"{self.capability}.{self.role}"


# Chat shapes. Other capabilities define theirs the same way.
CHAT_REQUEST = Shape(CHAT, "request")
CHAT_RESPONSE = Shape(CHAT, "response")
CHAT_CHUNK = Shape(CHAT, "chunk")


class Status(str, Enum):
    """The release channel a `NodeId` belongs to; drives catalog resolution.

    Attributes:
        STABLE: Generally available; eligible to be auto-selected as "latest".
        PREVIEW: Pre-release; reachable only when pinned explicitly by tag.
        DEPRECATED: Superseded; still reachable when pinned, never
            auto-selected.
        RETIRED: No longer served by the provider; kept so archived traffic
            can still be re-converted through migration edges.
    """

    STABLE = "stable"
    PREVIEW = "preview"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class NodeId:
    """The conversion-graph node: one interface revision of one shape.

    A node is the full six-coordinate identity of a message schema. `Catalog`s
    key nodes and edges by it, the planner searches over it, `Route` records
    the one that was chosen, and every conversion `EdgeReport` names its `src`
    and `dst` with it.

    The `tag` is an opaque dated revision token — **never parsed**; ordering
    among one `(provider, interface)`'s revisions comes from `released`
    instead, and cross-provider date comparison is meaningless. `status` is
    the resolution channel (`Catalog.resolve` auto-selects only `STABLE`).

    Attributes:
        provider: The provider label (`"openai"`, or `"ocai"` for canonical).
        interface: The wire protocol within the provider
            (`"chat_completions"`, `"responses"`, `"ocai"`). Sibling
            interfaces are concurrent, not versions of each other.
        tag: The interface's opaque dated revision token (e.g. `"2026-01"`).
        shape: Which message this schema is (`chat.request`, …).
        released: The internal sort key — the revision's release date,
            compared only within one `(provider, interface)`.
        status: The release channel; defaults to `Status.STABLE`.
    """

    provider: str
    interface: str
    tag: str
    shape: Shape
    released: date
    status: Status = Status.STABLE

    @property
    def capability(self) -> Capability:
        """Return the capability this node's `shape` belongs to."""
        return self.shape.capability

    def __str__(self) -> str:
        """Return the compact node label `provider/interface@tag#shape`.

        For example `"openai/responses@2026-01#chat.request"`.
        """
        return f"{self.provider}/{self.interface}@{self.tag}#{self.shape}"


@dataclass(frozen=True, slots=True)
class Origin:
    """Provenance stamp: which distribution registered a node or edge.

    Carried by every node/edge a plugin registers into a `CatalogFragment`,
    threaded through the `Catalog` into lockfiles and audit records, so a
    `Route` plus a catalog lockfile reconstructs exactly whose conversion
    logic served a call.

    Attributes:
        distribution: The distribution name (e.g. `"ocai-openai"`).
        version: The distribution's installed version (e.g. `"0.1.0"`).
    """

    distribution: str
    version: str

    def __str__(self) -> str:
        """Return the pip-style pin label `distribution==version`."""
        return f"{self.distribution}=={self.version}"


def canonical_node(
    shape: Shape,
    tag: str = CANONICAL_REVISION,
    released: date | None = None,
) -> NodeId:
    """Return the canonical IR node for `shape` at a canonical revision.

    Canonical nodes are ordinary nodes under provider/interface `ocai`; the
    graph treats them like any other, which is what makes IR self-migration
    (`ocai@2026-07 → ocai@2027-01`) ordinary edge traversal.

    Args:
        shape: The message shape whose canonical node is wanted.
        tag: The canonical revision tag; defaults to `CANONICAL_REVISION`.
            Canonical tags are always dated `YYYY-MM` tokens.
        released: The revision's release date. When omitted it is derived
            from `tag` (the first day of the revision month) — safe because
            canonical tags are ocai-owned and dated by construction.

    Returns:
        The `NodeId` identifying the canonical IR schema for `shape`.
    """
    if released is None:
        released = date.fromisoformat(f"{tag}-01")
    return NodeId(
        provider=CANONICAL_PROVIDER,
        interface=CANONICAL_INTERFACE,
        tag=tag,
        shape=shape,
        released=released,
    )
