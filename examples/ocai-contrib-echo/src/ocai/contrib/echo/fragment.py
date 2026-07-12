"""The echo plugin's declarative catalog contribution.

This module is the whole registration story of a plugin under the July 2026
architecture: it builds frozen values — `NodeId`s, `Edge`s with their
`EdgeContract` census, a `CapabilityProfile` — and assembles them into one
exported `FRAGMENT`. Nothing here mutates shared state at import time; the
*application* decides what exists by composing
`Catalog.of(echo.FRAGMENT, ...)`, and `Catalog.discover()` finds this value
through the `ocai.plugins` entry point.

echo is a fictional provider whose wire format is — by construction — the
canonical ocai JSON, so its edges are identity functions carrying an *empty*
`EdgeContract`. An empty census is a lossless claim, the strongest a plugin
can make: the conformance harness certifies at build time that the edges'
runtime `FieldLoss` never exceeds it. A real provider declares real
dispositions here (see `docs/writing-a-plugin.md`).

TEMPLATE STATUS: pending completion of the `ocai.convert` harness — the
imports below name the settled contract (architecture §4) and resolve once
that layer lands.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from ocai.convert.catalog import CatalogFragment
from ocai.convert.contract import EdgeContract
from ocai.convert.graph import Converted
from ocai.convert.graph import Edge
from ocai.core.fidelity import EdgeReport
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import CHAT_RESPONSE
from ocai.core.identity import NodeId
from ocai.core.identity import Origin
from ocai.core.identity import canonical_node
from ocai.core.profile import CapabilityProfile
from ocai.core.profile import Support

# Provenance stamp carried by every node/edge this fragment registers; it
# surfaces in catalog lockfiles and every Route/report that used echo logic.
ECHO_ORIGIN = Origin(distribution="ocai-contrib-echo", version="0.2.0")

# echo publishes ONE interface ("chat") at one dated revision. `tag` is an
# opaque token ordered by `released`; `status` defaults to STABLE, so
# Catalog.resolve may auto-select it.
_RELEASED = date(2026, 7, 1)

ECHO_CHAT_REQUEST = NodeId(
    provider="echo",
    interface="chat",
    tag="2026-07",
    shape=CHAT_REQUEST,
    released=_RELEASED,
)
ECHO_CHAT_RESPONSE = NodeId(
    provider="echo",
    interface="chat",
    tag="2026-07",
    shape=CHAT_RESPONSE,
    released=_RELEASED,
)

# The canonical IR nodes these edges connect to. Canonical is not special:
# it is provider "ocai" publishing interface "ocai" at a dated revision.
OCAI_CHAT_REQUEST = canonical_node(CHAT_REQUEST)
OCAI_CHAT_RESPONSE = canonical_node(CHAT_RESPONSE)

# The honest empty census: echo's wire IS canonical JSON, so every field is
# implicitly EXACT and there is nothing to declare. The planner derives a
# zero-loss weight from this, and conformance holds the edges to it.
_IDENTITY_CONTRACT = EdgeContract(fields={})


def _encode_request(payload: dict[str, Any]) -> Converted:
    """Convert a canonical chat request into echo wire form (identity).

    The graph calls this when planning `ocai@2026-07 -> echo/chat@2026-07`
    for the `chat.request` shape. A real provider renames/relocates fields
    here and returns each divergence as a `FieldLoss`/`SemanticShift` on the
    `EdgeReport` — never silently.

    Args:
        payload: The canonical `chat.request` document.

    Returns:
        The echo wire document plus the per-edge fidelity account (empty:
        the mapping is identity).
    """
    # TODO: template identity — a real provider maps fields and records losses.
    return Converted(
        value=payload,
        report=EdgeReport(src=OCAI_CHAT_REQUEST, dst=ECHO_CHAT_REQUEST),
    )


def _decode_request(payload: dict[str, Any]) -> Converted:
    """Convert an echo wire request back to canonical form (identity).

    The reverse direction exists so archived echo traffic can be re-converted
    toward canonical (and onward to any other interface) through the same
    honest machinery — the offline-audit use case plugins must serve.

    Args:
        payload: The echo wire `chat.request` document.

    Returns:
        The canonical document plus its (empty) fidelity account.
    """
    # TODO: template identity — a real provider maps fields and records losses.
    return Converted(
        value=payload,
        report=EdgeReport(src=ECHO_CHAT_REQUEST, dst=OCAI_CHAT_REQUEST),
    )


def _decode_response(payload: dict[str, Any]) -> Converted:
    """Convert an echo wire response into canonical form (identity).

    Args:
        payload: The echo wire `chat.response` document.

    Returns:
        The canonical document plus its (empty) fidelity account.
    """
    # TODO: template identity — a real provider maps fields and records losses.
    return Converted(
        value=payload,
        report=EdgeReport(src=ECHO_CHAT_RESPONSE, dst=OCAI_CHAT_RESPONSE),
    )


# Declared support facts, keyed below interface level (model_pattern) because
# support can vary per model. Consulted by the feature gate BEFORE payload
# conversion: strict mode refuses, annotate mode records the loss.
ECHO_PROFILE = CapabilityProfile(
    provider="echo",
    interface="chat",
    model_pattern="*",
    features={
        "tools": Support.ABSENT,
        "streaming": Support.ABSENT,
        "vision": Support.ABSENT,
        "reasoning": Support.ABSENT,
    },
)

# The single frozen export. Under the default TrustPolicy.OWNED_ENDPOINTS this
# fragment may only register edges touching shapes it publishes or canonical —
# exactly what these three edges do.
# TODO: add a StreamEdge transducer + fold-triple fixtures when echo learns to
# stream (the streaming-first ratchet: no part type without its delta type).
FRAGMENT = CatalogFragment(
    origin=ECHO_ORIGIN,
    nodes=(ECHO_CHAT_REQUEST, ECHO_CHAT_RESPONSE),
    edges=(
        Edge(
            src=OCAI_CHAT_REQUEST,
            dst=ECHO_CHAT_REQUEST,
            fn=_encode_request,
            contract=_IDENTITY_CONTRACT,
            origin=ECHO_ORIGIN,
        ),
        Edge(
            src=ECHO_CHAT_REQUEST,
            dst=OCAI_CHAT_REQUEST,
            fn=_decode_request,
            contract=_IDENTITY_CONTRACT,
            origin=ECHO_ORIGIN,
        ),
        Edge(
            src=ECHO_CHAT_RESPONSE,
            dst=OCAI_CHAT_RESPONSE,
            fn=_decode_response,
            contract=_IDENTITY_CONTRACT,
            origin=ECHO_ORIGIN,
        ),
    ),
    transducers=(),
    profiles=(ECHO_PROFILE,),
    traits=(),
)
