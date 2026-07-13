"""`ocai.openai.chat_completions` — the OpenAI Chat Completions interface.

One subpackage per interface (§7): this package is everything ocai knows about
`POST /v1/chat/completions` as a wire protocol — its msgspec decode-boundary
models (`wire`), its identity + mapping codec (`codec`), and its declarative
catalog material (`edges`). The sibling `ocai.openai.responses` package is a
*concurrent interface* of the same chat capability, not a version of this one.

The public surface is `FRAGMENT`: a frozen, provenance-stamped
`CatalogFragment` an application composes explicitly —
`Catalog.of(ocai.openai.chat_completions.FRAGMENT, ...)` — with **no
import-time registration** into any global (rule 14). This package depends on
`ocai.core` + `ocai.convert` + `ocai.chat` only, never on `ocai.wire`/httpx,
so offline audit tooling can re-convert archived traffic without the ability
to make a network call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ocai.convert.catalog import Catalog
from ocai.convert.catalog import CatalogFragment
from ocai.convert.catalog import Component
from ocai.core.identity import CHAT
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_CHUNK
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_REQUEST
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_RESPONSE
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.openai.chat_completions.codec import dialect_traits
from ocai.openai.chat_completions.edges import EDGES
from ocai.openai.chat_completions.edges import NODES
from ocai.openai.chat_completions.edges import ORIGIN
from ocai.openai.chat_completions.edges import PROFILES
from ocai.openai.chat_completions.edges import TRANSDUCERS

if TYPE_CHECKING:
    from ocai.chat.protocol import ChatModel
    from ocai.core.credentials import Credential

__all__ = [
    "CHAT_COMPLETIONS_CHUNK",
    "CHAT_COMPLETIONS_REQUEST",
    "CHAT_COMPLETIONS_RESPONSE",
    "FRAGMENT",
    "ChatCompletionsCodec",
    "chat_model",
]

# The frozen declarative fragment this interface contributes to a Catalog:
# its three nodes, its contract-censused edges, its chunk transducer, its
# capability profile, its hosting traits, and its codec factory (the
# component the §3.4 front door builds the serving codec from) — all stamped
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
            provider=ChatCompletionsCodec.provider,
            interface=ChatCompletionsCodec.interface,
            capability=CHAT,
            factory=ChatCompletionsCodec,
        ),
    ),
)


def chat_model(
    model_name: str,
    *,
    credentials: Credential,
) -> ChatModel:
    """Sanctioned sugar (§3.4 door 2): a first-party OpenAI chat model.

    A THIN wrapper over the exact same fragment + facade machinery as the
    core string door — never a separate code path: it *is* a call to
    `ocai.chat.model(f"openai/{model_name}", ...)` over a minimal catalog
    built from this interface's `FRAGMENT` (so the front door composes a
    `Direct` host at the OpenAI origin from the fragment's declared traits,
    the `ChatCompletionsCodec` from the fragment's component factory, and an
    `HttpxTransport`). The model name binds to the returned model object
    here, at construction; `ChatRequest`s stay pure conversation and never
    carry it. Power users compose the pieces themselves (any host, any
    transport, richer catalogs); this factory adds nothing they cannot
    reach.

    Args:
        model_name: The OpenAI model name bound to the returned model
            object (the facade's `EndpointSpec.resource`).
        credentials: The credential applied per request at the driver leaf.
            Required — there is no ambient discovery (rule 13).

    Returns:
        A `ChatModel` implementation backed by this interface.
    """
    # Deferred import (the documented door-2 seam): the plugin stays inert at
    # import time and reaches the wire only through the core front door, at
    # call time — the same composition path, one frame deeper.
    from ocai.chat import model

    return model(
        f"{ChatCompletionsCodec.provider}/{model_name}",
        credentials=credentials,
        catalog=Catalog.of(FRAGMENT),
    )
