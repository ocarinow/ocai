"""`ocai.anthropic.messages` — the Anthropic Messages interface.

One subpackage per interface (§7): everything ocai knows about
`POST /v1/messages` as a wire protocol — its msgspec decode-boundary models
(`wire`), its identity + mapping codec (`codec`), and its declarative catalog
material (`edges`). Should Anthropic ship a sibling wire protocol, it becomes
a sibling subpackage, never a new "version" of this one.

The public surface is `FRAGMENT`: a frozen, provenance-stamped
`CatalogFragment` an application composes explicitly with **no import-time
registration** (rule 14). This package depends on `ocai.core` +
`ocai.convert` + `ocai.chat` only, never on `ocai.wire`/httpx — hosting
(first-party, Vertex, Bedrock) is a separate axis composed below the graph,
parameterized by the traits declared in `codec.dialect_traits`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ocai.anthropic.messages.codec import MESSAGES_CHUNK
from ocai.anthropic.messages.codec import MESSAGES_REQUEST
from ocai.anthropic.messages.codec import MESSAGES_RESPONSE
from ocai.anthropic.messages.codec import MessagesCodec
from ocai.anthropic.messages.codec import dialect_traits
from ocai.anthropic.messages.edges import EDGES
from ocai.anthropic.messages.edges import NODES
from ocai.anthropic.messages.edges import ORIGIN
from ocai.anthropic.messages.edges import PROFILES
from ocai.anthropic.messages.edges import TRANSDUCERS
from ocai.convert.catalog import Catalog
from ocai.convert.catalog import CatalogFragment
from ocai.convert.catalog import Component
from ocai.core.identity import CHAT

if TYPE_CHECKING:
    from ocai.chat.protocol import ChatModel
    from ocai.core.credentials import Credential

__all__ = [
    "FRAGMENT",
    "MESSAGES_CHUNK",
    "MESSAGES_REQUEST",
    "MESSAGES_RESPONSE",
    "MessagesCodec",
    "chat_model",
]

# The frozen declarative fragment this interface contributes to a Catalog:
# its three nodes, its contract-censused edges, its chunk transducer, its
# capability profiles, its hosting traits, and its codec factory (the
# component the §3.4 front door builds the serving codec from) — stamped
# with this distribution's Origin.
FRAGMENT = CatalogFragment(
    origin=ORIGIN,
    nodes=NODES,
    edges=EDGES,
    transducers=TRANSDUCERS,
    profiles=PROFILES,
    traits=(dialect_traits(),),
    components=(
        Component(
            provider=MessagesCodec.provider,
            interface=MessagesCodec.interface,
            capability=CHAT,
            factory=MessagesCodec,
        ),
    ),
)


def chat_model(
    model_name: str,
    *,
    credentials: Credential,
) -> ChatModel:
    """Sanctioned sugar (§3.4 door 2): a first-party Anthropic chat model.

    A THIN wrapper over the exact same fragment + facade machinery as the
    core string door — never a separate code path: it *is* a call to
    `ocai.chat.model(f"anthropic/{model_name}", ...)` over a minimal catalog
    built from this interface's `FRAGMENT` (so the front door composes a
    `Direct` host at the Anthropic origin from the fragment's declared
    traits — which inject the `anthropic-version` header — the
    `MessagesCodec` from the fragment's component factory, and an
    `HttpxTransport`). The model name binds to the returned model object
    here, at construction; `ChatRequest`s stay pure conversation and never
    carry it. For Vertex/Bedrock, compose the pieces directly with the
    appropriate host and credential.

    Args:
        model_name: The Anthropic model name bound to the returned model
            object (the facade's `EndpointSpec.resource`).
        credentials: The credential applied per request at the driver leaf —
            `x-api-key` first-party, so supply
            `ApiKey(key, header="x-api-key", scheme="")`. Required; there is
            no ambient discovery (rule 13).

    Returns:
        A `ChatModel` implementation backed by this interface.
    """
    # Deferred import (the documented door-2 seam): the plugin stays inert at
    # import time and reaches the wire only through the core front door, at
    # call time — the same composition path, one frame deeper.
    from ocai.chat import model

    return model(
        f"{MessagesCodec.provider}/{model_name}",
        credentials=credentials,
        catalog=Catalog.of(FRAGMENT),
    )
