"""Edge definitions for `openai/responses` — empty-census skeletons [stub].

Declares the fragment material for the `/responses` interface: its nodes are
real (the catalog must be able to resolve and pin the interface), while its
edges ship only when their mappings and censuses are implemented — an edge
with a false census cannot ship (§4.2), so none are registered yet.

The direct `openai/chat_completions ↔ openai/responses` edges (the
higher-fidelity migration shortcut that skips the canonical hop) also belong
here once the codec lands; both endpoints are shapes this fragment publishes,
so `TrustPolicy.OWNED_ENDPOINTS` admits them without opt-in.
"""

from __future__ import annotations

from ocai.convert.contract import EdgeContract
from ocai.convert.graph import Edge
from ocai.convert.graph import StreamEdge
from ocai.core.identity import NodeId
from ocai.core.identity import Origin
from ocai.core.profile import CapabilityProfile
from ocai.openai.responses.codec import RESPONSES_CHUNK
from ocai.openai.responses.codec import RESPONSES_REQUEST
from ocai.openai.responses.codec import RESPONSES_RESPONSE

# Provenance stamp shared by everything this distribution registers.
# TODO: derive the version from importlib.metadata at fragment-build time.
ORIGIN = Origin(distribution="ocai-openai", version="0.1.0")

# Empty-census placeholders: filled in the same change that implements each
# mapping (the census is the implementation's honesty, never aspirational).
ENCODE_REQUEST_CONTRACT = EdgeContract(
    census={},
    note="canonical chat.request -> openai/responses [stub: census with the item-model encode]",
)
DECODE_RESPONSE_CONTRACT = EdgeContract(
    census={},
    note="openai/responses -> canonical chat.response [stub: census with the item-model decode]",
)
DECODE_CHUNK_CONTRACT = EdgeContract(
    census={},
    note="openai/responses -> canonical chat.chunk [stub: census with the semantic-event decode]",
)

NODES: tuple[NodeId, ...] = (
    RESPONSES_REQUEST,
    RESPONSES_RESPONSE,
    RESPONSES_CHUNK,
)

# TODO: register encode/decode edges + the chat_completions<->responses
# migration shortcut edges once ResponsesCodec is implemented.
EDGES: tuple[Edge, ...] = ()

# TODO: register the semantic-event StreamEdge once decode_event lands.
TRANSDUCERS: tuple[StreamEdge, ...] = ()

# TODO: declare the interface profile (reasoning replay NATIVE, server-side
# conversation state NATIVE via previous_response_id, hosted tools NATIVE).
PROFILES: tuple[CapabilityProfile, ...] = ()
