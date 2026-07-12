"""Conformance: the real plugin fragments compose, resolve, and convert honestly.

Drives the first-party fragments through the same scoped `Catalog` machinery a
third-party application uses: admission under `TrustPolicy.OWNED_ENDPOINTS`,
resolution recorded as a `Route`, request/response conversion over contract-
censused edges (each returning a `FidelityReport`), and the diffable
content-hashed lockfile.
"""

from __future__ import annotations

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
