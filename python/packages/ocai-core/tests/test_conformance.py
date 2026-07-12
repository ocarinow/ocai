"""Conformance: the real plugin fragments compose, resolve, and convert honestly.

Drives the first-party fragments through the same scoped `Catalog` machinery a
third-party application uses: admission under `TrustPolicy.OWNED_ENDPOINTS`,
resolution recorded as a `Route`, request/response conversion over contract-
censused edges (each returning a `FidelityReport`), and the diffable
content-hashed lockfile.
"""

from __future__ import annotations

from datetime import date

import pytest

import ocai.anthropic
import ocai.openai
from ocai.chat import CANONICAL_CHAT_REQUEST
from ocai.chat import CANONICAL_CHAT_RESPONSE
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import Message
from ocai.convert import AdmissionError
from ocai.convert import Catalog
from ocai.convert import CatalogFragment
from ocai.convert import Converted
from ocai.convert import Edge
from ocai.convert import EdgeContract
from ocai.convert import EdgeOutput
from ocai.core import CHAT
from ocai.core import CHAT_REQUEST
from ocai.core import NodeId
from ocai.core import Origin
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_REQUEST
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_RESPONSE

_REQUEST = ChatRequest(model="gpt-4o", messages=[Message(role="user", parts="hi")])


def _catalog() -> Catalog:
    return Catalog.of(ocai.openai.FRAGMENT, ocai.anthropic.FRAGMENT)


# --- Composition & governance ------------------------------------------------


def test_fragments_compose_under_owned_endpoints() -> None:
    catalog = _catalog()
    assert CHAT_COMPLETIONS_REQUEST in catalog.nodes
    # Both distributions' provenance is visible on the composition.
    origins = {str(fragment.origin) for fragment in catalog.fragments}
    assert origins == {"ocai-openai==0.1.0", "ocai-anthropic==0.1.0"}


def test_foreign_bridging_is_refused_by_default() -> None:
    # A fragment registering an edge between two interfaces it does not
    # publish is exactly the silent-insertion attack OWNED_ENDPOINTS blocks.
    from ocai.anthropic.messages.codec import MESSAGES_REQUEST

    bridge = CatalogFragment(
        origin=Origin(distribution="ocai-evil", version="0.0.1"),
        edges=(
            Edge(
                src=CHAT_COMPLETIONS_REQUEST,
                dst=MESSAGES_REQUEST,
                fn=lambda payload: EdgeOutput(payload),
                contract=EdgeContract(),
                origin=Origin(distribution="ocai-evil", version="0.0.1"),
            ),
        ),
    )
    with pytest.raises(AdmissionError):
        Catalog.of(ocai.openai.FRAGMENT, ocai.anthropic.FRAGMENT, bridge)


def test_lock_hash_is_stable_and_lands_in_routes() -> None:
    first, second = _catalog(), _catalog()
    assert first.lock().hash == second.lock().hash  # same composition, same hash
    route = first.resolve(CHAT, "anthropic")
    assert route.catalog_hash == first.lock().hash


# --- Resolution ----------------------------------------------------------------


def test_resolution_records_an_auditable_route() -> None:
    route = _catalog().resolve(CHAT, "openai", interface="chat_completions")
    assert route.node == CHAT_COMPLETIONS_REQUEST
    assert route.requested_interface == "chat_completions"
    assert "latest stable" in route.reason


# --- Conversion: the canonical backbone in both directions ---------------------


def test_request_encodes_through_the_catalog() -> None:
    converted = _catalog().convert(_REQUEST, CANONICAL_CHAT_REQUEST, CHAT_COMPLETIONS_REQUEST)
    assert isinstance(converted, Converted)  # value + report, never a bare tuple
    wire = converted.value
    assert wire["model"] == "gpt-4o"
    assert wire["messages"][0]["role"] == "user"
    assert converted.report.path == [CANONICAL_CHAT_REQUEST, CHAT_COMPLETIONS_REQUEST]


def test_response_decodes_through_the_catalog(load_http) -> None:
    rec = load_http("openai_chat_completion.json")
    converted = _catalog().convert(
        rec["response"]["json"], CHAT_COMPLETIONS_RESPONSE, CANONICAL_CHAT_RESPONSE
    )
    response = converted.value
    assert isinstance(response, ChatResponse)
    assert response.message.role == "model"  # wire "assistant", normalized once
    assert response.message.text == "I am an AI assistant."
    assert response.usage is not None
    assert response.usage.input_tokens == 18
    assert response.usage.output_tokens == 6
    assert response.finish is not None and response.finish.native == "stop"
    assert response.raw == rec["response"]["json"]  # untouched provider body
    assert converted.report.path == [CHAT_COMPLETIONS_RESPONSE, CANONICAL_CHAT_RESPONSE]


# --- Admission: canonical-backbone connectivity ---------------------------------
#
# The `_admit` rule (WU-01): a published non-canonical interface that registers
# any edge/transducer must connect to the canonical backbone with at least one
# of them; a nodes-only interface is a sanctioned conversionless stub.


def _acme_pair() -> tuple[NodeId, NodeId]:
    """Two dated `chat.request` nodes of one synthetic acme interface."""
    v1 = NodeId("acme", "chat", "v1", CHAT_REQUEST, date(2024, 1, 1))
    v2 = NodeId("acme", "chat", "v2", CHAT_REQUEST, date(2024, 6, 1))
    return v1, v2


_ACME = Origin(distribution="ocai-acme", version="0.0.1")


def test_canonical_touching_edge_connects_the_interface() -> None:
    # One canonical-touching edge satisfies connectivity for the whole
    # interface; the intra-interface delta edge then rides along.
    v1, v2 = _acme_pair()
    canon = CANONICAL_CHAT_REQUEST
    fragment = CatalogFragment(
        origin=_ACME,
        nodes=(v1, v2),
        edges=(
            Edge(v1, canon, lambda p: EdgeOutput(p), EdgeContract(), _ACME, "v1 -> canon"),
            Edge(v1, v2, lambda p: EdgeOutput(p), EdgeContract(), _ACME, "delta"),
        ),
    )
    catalog = Catalog.of(fragment)
    assert v1 in catalog.nodes and v2 in catalog.nodes


def test_interface_with_edges_but_no_canonical_touch_is_refused() -> None:
    # An island: the interface converts (v1 <-> v2 deltas) but nothing ever
    # reaches the canonical backbone — inadmissible, not silently stranded.
    v1, v2 = _acme_pair()
    fragment = CatalogFragment(
        origin=_ACME,
        nodes=(v1, v2),
        edges=(
            Edge(v1, v2, lambda p: EdgeOutput(p), EdgeContract(), _ACME, "delta up"),
            Edge(v2, v1, lambda p: EdgeOutput(p), EdgeContract(), _ACME, "delta down"),
        ),
    )
    with pytest.raises(AdmissionError, match="canonical backbone"):
        Catalog.of(fragment)
    # Direct construction cannot bypass the gate either.
    with pytest.raises(AdmissionError, match="canonical backbone"):
        Catalog((fragment,))


def test_owned_sibling_shortcut_alone_does_not_connect() -> None:
    # Both endpoints are owned (ownership passes), but a shortcut between two
    # sibling interfaces connects neither of them to the backbone.
    alpha = NodeId("acme", "alpha", "v1", CHAT_REQUEST, date(2024, 1, 1))
    beta = NodeId("acme", "beta", "v1", CHAT_REQUEST, date(2024, 1, 1))
    fragment = CatalogFragment(
        origin=_ACME,
        nodes=(alpha, beta),
        edges=(Edge(alpha, beta, lambda p: EdgeOutput(p), EdgeContract(), _ACME, "shortcut"),),
    )
    with pytest.raises(AdmissionError, match="canonical backbone"):
        Catalog.of(fragment)


def test_nodes_only_stub_interface_is_admitted() -> None:
    # The sanctioned stub (the shape of ocai.openai.responses today): nodes
    # make the interface resolvable/pinnable while it honestly performs no
    # conversions, because its codec has not yet earned a census.
    stub = NodeId("acme", "future", "v1", CHAT_REQUEST, date(2024, 1, 1))
    catalog = Catalog.of(CatalogFragment(origin=_ACME, nodes=(stub,)))
    assert stub in catalog.nodes
