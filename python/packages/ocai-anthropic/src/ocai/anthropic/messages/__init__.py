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
from ocai.convert.catalog import CatalogFragment

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
# its three nodes, its contract-censused edges, its chunk transducer, and its
# capability profiles — stamped with this distribution's Origin.
FRAGMENT = CatalogFragment(
    origin=ORIGIN,
    nodes=NODES,
    edges=EDGES,
    transducers=TRANSDUCERS,
    profiles=PROFILES,
    traits=(dialect_traits(),),
)


def chat_model(
    model_name: str,
    *,
    credentials: Credential | None = None,
) -> ChatModel:
    """Sanctioned sugar (§3.4 door 2): a first-party Anthropic chat model.

    A THIN wrapper over the exact same fragment + facade machinery as the
    core string door (`ocai.chat.model("anthropic", model_name, ...)`) —
    never a separate code path: it composes `WireChatModel(MessagesCodec(),
    binding, catalog, model_name=model_name)` with a `Direct` host at the
    Anthropic origin (whose traits inject the `anthropic-version` header)
    and a minimal catalog from this interface's `FRAGMENT`. The model name
    binds to the returned model object here, at construction;
    `ChatRequest`s stay pure conversation and never carry it. For
    Vertex/Bedrock, compose the pieces directly with the appropriate host
    and credential.

    Args:
        model_name: The Anthropic model name bound to the returned model
            object (the facade's `EndpointSpec.resource`).
        credentials: The credential applied per request at the driver leaf —
            `x-api-key` first-party, so supply
            `ApiKey(key, header="x-api-key", scheme="")`. Required; there is
            no ambient discovery (rule 13).

    Returns:
        A `ChatModel` implementation backed by this interface.

    Raises:
        NotImplementedError: Always, until WU-16 wires the front doors.
    """
    # TODO: WU-16 — build Catalog.of(FRAGMENT), Binding(Direct(ANTHROPIC_BASE_URL),
    # credentials, HttpxTransport()), and return WireChatModel(...,
    # model_name=model_name) via DEFERRED imports of ocai.chat.facade /
    # ocai.runtime / ocai.wire (module level would break the plugin import
    # contract; the facade is the sanctioned composition seam).
    raise NotImplementedError
