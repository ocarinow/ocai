"""`ocai.openai.responses` — the OpenAI Responses interface [stub].

The *sibling interface* of `ocai.openai.chat_completions` for the same chat
capability — concurrent, not a version of it (§2.1) — and the destination of
the flagship migration WU: resolving a chat call onto `/responses` with no
user code change and every cost visible in the `FidelityReport`. Structure
only today: nodes and codec skeletons are declared; mappings, censuses, and
fixtures land together (§4.2).
"""

from __future__ import annotations

from ocai.convert.catalog import CatalogFragment
from ocai.openai.responses.codec import RESPONSES_CHUNK
from ocai.openai.responses.codec import RESPONSES_REQUEST
from ocai.openai.responses.codec import RESPONSES_RESPONSE
from ocai.openai.responses.codec import ResponsesCodec
from ocai.openai.responses.edges import EDGES
from ocai.openai.responses.edges import NODES
from ocai.openai.responses.edges import ORIGIN
from ocai.openai.responses.edges import PROFILES
from ocai.openai.responses.edges import TRANSDUCERS

__all__ = [
    "FRAGMENT",
    "RESPONSES_CHUNK",
    "RESPONSES_REQUEST",
    "RESPONSES_RESPONSE",
    "ResponsesCodec",
]

# Nodes only, until edges earn their censuses: composing this fragment makes
# the interface resolvable/pinnable without claiming conversions it lacks.
FRAGMENT = CatalogFragment(
    origin=ORIGIN,
    nodes=NODES,
    edges=EDGES,
    transducers=TRANSDUCERS,
    profiles=PROFILES,
    traits=(),  # TODO: DialectTraits(vendor="openai") once the codec lands.
)
