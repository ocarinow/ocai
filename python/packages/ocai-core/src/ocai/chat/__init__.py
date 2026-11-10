"""`ocai.chat` — the chat capability contract (architecture §3).

The port (`ChatModel`), the canonical chat IR (`ocai.chat.types`), the
canonical graph nodes (`ocai.chat.canonical`), the wire-backed facade
(`WireChatModel`), and the §3.4 front door (`model`). Everything except
`facade.py` depends on `ocai.core` only; `facade.py` is the one designated
module that composes convert/runtime/wire behind the port (named `facade`
so the `ocai.chat.model()` front-door factory is never shadowed by a
module — the factory below composes lazily, inside the call, through the
same sanctioned seams).

The curated exports below are the user-facing surface: build a model with
`model("openai/gpt-5", credentials=...)`, build a `ChatRequest` from
`Message`s and `Tool`s, call any `ChatModel`, receive a
`CallResult[ChatResponse]` or a `ChatStream` of `ChatChunk`s.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ocai.chat.canonical import CANONICAL_CHAT_CHUNK
from ocai.chat.canonical import CANONICAL_CHAT_REQUEST
from ocai.chat.canonical import CANONICAL_CHAT_RESPONSE
from ocai.chat.canonical import OCAI_INTERFACE
from ocai.chat.canonical import REVISION
from ocai.chat.facade import WireChatModel
from ocai.chat.protocol import ChatModel
from ocai.chat.types import AsyncChatStream
from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatConfig
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import ChatStream
from ocai.chat.types import FinishInfo
from ocai.chat.types import Message
from ocai.chat.types import Part
from ocai.chat.types import Role
from ocai.chat.types import StreamAccumulator
from ocai.chat.types import StreamEnd
from ocai.chat.types import StreamOutcome
from ocai.chat.types import Tool
from ocai.chat.types import ToolChoice
from ocai.chat.types import Usage

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ocai.chat.facade import InterceptedChatModel
    from ocai.chat.facade import ObservedChatModel
    from ocai.convert.catalog import Catalog
    from ocai.core.credentials import Credential
    from ocai.core.fidelity import Route
    from ocai.runtime.decisions import WirePolicy
    from ocai.runtime.interceptors import CallInterceptor
    from ocai.runtime.observe import Observer
    from ocai.wire.hosting import Host
    from ocai.wire.transport import SyncTransport
    from ocai.wire.transport import Transport

__all__ = [
    "CANONICAL_CHAT_CHUNK",
    "CANONICAL_CHAT_REQUEST",
    "CANONICAL_CHAT_RESPONSE",
    "OCAI_INTERFACE",
    "REVISION",
    "AsyncChatStream",
    "ChatChunk",
    "ChatConfig",
    "ChatModel",
    "ChatRequest",
    "ChatResponse",
    "ChatStream",
    "FinishInfo",
    "Message",
    "Part",
    "Role",
    "StreamAccumulator",
    "StreamEnd",
    "StreamOutcome",
    "Tool",
    "ToolChoice",
    "Usage",
    "WireChatModel",
    "model",
]


def model(
    spec: str,
    *,
    credentials: Credential,
    host: Host | None = None,
    catalog: Catalog | None = None,
    transport: Transport | SyncTransport | None = None,
    interceptors: Sequence[CallInterceptor] = (),
    policies: Sequence[WirePolicy] = (),
    observers: Sequence[Observer] = (),
    interface: str | None = None,
    tag: str | None = None,
) -> WireChatModel | InterceptedChatModel | ObservedChatModel:
    """Build a chat model from one spec string — the §3.4 core front door.

    The whole provider+model choice is ONE data value
    (`model(os.environ["OCAI_MODEL"], ...)` — switching providers is a
    deployment change, zero code):

    ```python
    import ocai.chat
    from ocai.core import ApiKey

    chat = ocai.chat.model("openai/gpt-5", credentials=ApiKey.from_env("OPENAI_API_KEY"))
    res = chat.chat(ChatRequest(messages=[Message.user("hello")]))
    ```

    The factory resolves the provider against the catalog, builds the codec
    from the serving fragment's registered component factory, composes the
    `Binding` internally (a `Direct` host at the fragment's declared
    first-party origin unless `host` is passed), and binds the model name to
    the returned object — requests stay pure conversation. Unpinned
    resolution considers only interfaces the catalog can actually *serve*
    (those with a registered chat component); a nodes-only stub interface is
    reachable by explicit `interface=` pin only.

    Everything composed here is reachable by hand (`WireChatModel` + a
    `Binding` + a `Catalog`); this door adds nothing a power user cannot
    build — and the plugin `chat_model` helpers are sugar over exactly this
    path, never a separate one.

    Args:
        spec: The model spec `"<provider>/<model>"` (the LiteLLM/OpenRouter
            convention). Split on the FIRST slash only — the model part may
            itself contain slashes (`"openai/meta-llama/Llama-3.3-70B"` on a
            vLLM gateway). The spec never carries an interface; pinning is
            the `interface`/`tag` kwargs.
        credentials: The credential the driver applies at the leaf, per
            attempt. Required — there is no ambient discovery (rule 13).
        host: The hosting target, or None for first-party `Direct` at the
            dialect's declared origin.
        catalog: The governed conversion catalog, or None for the
            entry-point-discovered `default_catalog()`.
        transport: The wire transport, or None for a fresh `HttpxTransport`.
        interceptors: The port-tier chain wrapped around the facade,
            outermost first; empty for the bare facade.
        observers: Authorized passive metadata-only lifecycle observers.
        policies: The wire-tier hooks (retry, rate-limit, wiretap) the
            drivers consult on every attempt, in order.
        interface: An interface pin (e.g. `"chat_completions"`), or None to
            let the catalog choose among serveable interfaces.
        tag: A revision-tag pin, or None for latest eligible.

    Returns:
        A composed `ChatModel` bound to the parsed model name.

    Raises:
        ValueError: If `spec` is not of the `"<provider>/<model>"` form.
        ResolutionError: If the provider is not in the catalog (the message
            names the providers that are), or no serveable interface
            matches the pins.
        LookupError: If a pinned interface has no registered component
            factory (a declared stub, or a missing plugin distribution).
        CompositionError: If the dialect declares no first-party endpoint
            and no explicit `host` was given.
    """
    # Deferred imports: `ocai.chat` sits below convert/runtime/wire in the
    # layer map, so the front door reaches up only at call time, through the
    # same documented seams as the facade (see [tool.importlinter] ignores).
    from ocai.chat.facade import InterceptedChatModel
    from ocai.chat.facade import ObservedChatModel
    from ocai.convert.catalog import ResolutionError
    from ocai.convert.catalog import default_catalog
    from ocai.core.identity import CANONICAL_PROVIDER
    from ocai.core.identity import CHAT
    from ocai.runtime.binding import Binding
    from ocai.runtime.binding import CompositionError
    from ocai.wire.hosting import Direct

    provider, slash, model_name = spec.partition("/")
    if not slash or not provider or not model_name:
        raise ValueError(
            f"chat model spec must be '<provider>/<model>' (split on the first "
            f"slash; the model part may contain slashes), got {spec!r}"
        )
    composed = catalog if catalog is not None else default_catalog()
    components = composed.components_for(provider, CHAT)
    if not components:
        known = sorted(
            {
                node.provider
                for fragment in composed.fragments
                for node in fragment.nodes
                if node.provider != CANONICAL_PROVIDER
            }
        )
        raise ResolutionError(
            f"no chat component for provider {provider!r} (from spec {spec!r}) in "
            f"this catalog; providers composed here: {', '.join(known) or 'none'}. "
            f"If the plugin is not installed, install it with:  pip install "
            f"ocai-{provider}"
        )
    if interface is not None:
        route = composed.resolve(CHAT, provider, interface=interface, tag=tag)
    else:
        # Unpinned: auto-select only among component-backed interfaces (the
        # ones this catalog can serve). Multiple eligible sibling APIs require
        # an explicit pin; newer dates do not imply interface preference.
        routes: list[Route] = []
        for component in components:
            try:
                routes.append(
                    composed.resolve(CHAT, provider, interface=component.interface, tag=tag)
                )
            except ResolutionError:
                continue
        if not routes:
            pin = f" tag {tag!r}" if tag is not None else ""
            raise ResolutionError(
                f"no serveable chat interface for provider {provider!r}{pin} in this catalog"
            )
        if len(routes) > 1:
            names = ", ".join(sorted(route.node.interface for route in routes))
            raise ResolutionError(
                f"ambiguous serveable interfaces for {provider}: {names}; "
                "pass interface= explicitly"
            )
        route = routes[0]
    codec = composed.component(provider, route.node.interface, CHAT)()
    if host is None:
        base_url = codec.dialect_traits().first_party_base_url
        if base_url is None:
            raise CompositionError(
                f"{provider}/{route.node.interface} declares no first-party "
                "endpoint (DialectTraits.first_party_base_url); pass host= "
                "explicitly (Direct/Custom/Vertex, ocai.wire.hosting)"
            )
        host = Direct(base_url)
    if transport is None:
        from ocai.wire.transport import HttpxTransport

        transport = HttpxTransport(provider=provider)
    binding = Binding(host=host, credentials=credentials, transport=transport)
    facade: WireChatModel | InterceptedChatModel | ObservedChatModel = WireChatModel(
        codec,
        binding,
        composed,
        model_name=model_name,
        interface=interface,
        tag=tag,
        policies=policies,
        attempt_observers=observers,
    )
    if interceptors:
        facade = InterceptedChatModel(facade, interceptors)
    if observers:
        facade = ObservedChatModel(facade, observers)
    return facade
