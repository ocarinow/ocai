"""`WireChatModel` — the wire-backed facade (architecture §3.3, §3.4, §8).

The ONE chat module allowed to import `ocai.convert` / `ocai.runtime` /
`ocai.wire` (the port and the types never do). A provider is not a subclass
but a **composition of three values plus a bound resource**:

- a dialect **codec** — the wire I/O for one provider interface (shipped by
  the plugin, per §7: `encode` / `decode` / `decode_event` / `map_error`),
- a **`Binding`** — the reusable remote nucleus (host, credentials,
  transport, headers),
- a **`Catalog`** — the governed conversion registry that resolves nodes
  and plans edge paths,
- the **bound `model_name`** — the provider-specific routing datum the §3.4
  front doors pass at construction. It is NEVER carried in a `ChatRequest`
  (requests are pure, portable conversation); the facade injects it into
  the encoded wire payload from the bound resource, below the graph.

The same class serves OpenAI-direct, Anthropic-on-Vertex, or a self-hosted
gateway; only the values change. Its lifecycle (§8): resolve a `Route`
through the catalog → convert the request through the graph (request leg of
the `FidelityReport`) → inject the bound model via the codec's
`bind_resource` seam → hand the wire payload to the driver (hooks, host
envelope, credential-at-the-leaf, transport) → convert the response back →
assemble `CallResult(value, route, report, usage, raw)`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from ocai.chat.types.request import ChatRequest
from ocai.chat.types.response import ChatResponse
from ocai.chat.types.stream import AsyncChatStream
from ocai.chat.types.stream import ChatStream
from ocai.core.result import CallContext
from ocai.core.result import CallResult

if TYPE_CHECKING:
    from ocai.convert.catalog import Catalog
    from ocai.runtime.binding import Binding


class WireChatModel:
    """The wire-backed `ChatModel`: codec + binding + catalog behind the port.

    Satisfies the `ChatModel` protocol structurally. Local adapters are its
    peers, not its subclasses — anything this facade returns (`CallResult`
    with a `Route` whose `host` names the physical destination) an
    in-process adapter can return too (`route.host = "in-process"`), which
    is what keeps the interceptor tier implementation-agnostic.

    Both §3.4 front doors resolve to this class: the core string door
    (`ocai.chat.model(provider, model_name, ...)`) and the plugin sugar
    (`ocai.openai.chat_model(model_name, ...)`) each bind the model name
    HERE, at construction. Switching provider — or model — is building a
    new facade; the `ChatRequest`s replay unchanged.
    """

    def __init__(
        self,
        codec: Any,
        binding: Binding,
        catalog: Catalog,
        *,
        model_name: str,
        interface: str | None = None,
        tag: str | None = None,
    ) -> None:
        """Compose the facade from its three values and the bound resource.

        Args:
            codec: The dialect codec for the target provider interface —
                duck-typed to the plugin codec surface (`encode`, `decode`,
                `decode_event`, `map_error`, `bind_resource`, per
                architecture §7).
            binding: The remote nucleus: host, credentials, transport, and
                headers. `binding.validate()` is expected to have checked
                sync/async coherence at composition time.
            catalog: The governed conversion catalog used to resolve the
                target `NodeId` and plan every conversion leg; its lockfile
                hash lands in each call's `Route`.
            model_name: The bound resource (§3.4): the provider-specific
                model name every call targets. Becomes
                `EndpointSpec.resource` and is injected into each encoded
                wire payload via the codec's `bind_resource` — requests
                never carry it.
            interface: The provider interface to pin
                (e.g. `"responses"`), or None to let the catalog choose.
            tag: The interface revision tag to pin, or None for latest
                stable.
        """
        # TODO: the codec protocol's typed home (convert vs. chat) is still
        # open in the blueprint; typed as Any until it lands.
        self._codec = codec
        self._binding = binding
        self._catalog = catalog
        self._model_name = model_name
        self._interface = interface
        self._tag = tag

    def chat(
        self,
        request: ChatRequest,
        *,
        ctx: CallContext | None = None,
    ) -> CallResult[ChatResponse]:
        """Send a blocking chat request through the full §8 lifecycle.

        The request is pure conversation (§3.4 — it carries no model); this
        facade injects the bound `model_name` into the encoded wire payload
        via the codec's `bind_resource`, after graph conversion and before
        the driver send.

        Args:
            request: The canonical chat request.
            ctx: The per-request governance context, forwarded to the
                driver's policy hooks.

        Returns:
            The uniform envelope: response, `Route`, merged
            `FidelityReport` (request leg + response leg), usage, raw body.
        """
        # TODO: §8 lifecycle — catalog.resolve(CHAT, provider, pins) -> Route;
        # graph.convert(request, CANONICAL_CHAT_REQUEST -> route.node);
        # codec.bind_resource(payload, self._model_name) — the WU-05a seam;
        # SyncDriver.send via binding (hooks, host envelope, credential at
        # the leaf) with EndpointSpec.resource = self._model_name;
        # graph.convert(raw -> CANONICAL_CHAT_RESPONSE); assemble
        # CallResult with the merged report. Needs ocai.convert.Catalog and
        # ocai.runtime.SyncDriver, which land in parallel.
        raise NotImplementedError

    async def achat(
        self,
        request: ChatRequest,
        *,
        ctx: CallContext | None = None,
    ) -> CallResult[ChatResponse]:
        """Send a blocking chat request, asynchronously.

        The `a`-twin of `chat`: identical resolve/convert/bind/assemble
        logic (all synchronous and shared, per the sans-io rule) — the bound
        `model_name` is injected the same way; only the physical I/O call
        goes through `AsyncDriver`.

        Args:
            request: The canonical chat request.
            ctx: The per-request governance context.

        Returns:
            The uniform envelope carrying the canonical `ChatResponse`.
        """
        # TODO: same pipeline as chat() over AsyncDriver — the sans-io split
        # means only the transport await differs.
        raise NotImplementedError

    def stream(
        self,
        request: ChatRequest,
        *,
        ctx: CallContext | None = None,
    ) -> ChatStream:
        """Send a streaming chat request, synchronously.

        Same request purity as `chat`: the bound `model_name` is injected
        into the encoded payload via `bind_resource` before the stream
        opens — the request never carries it.

        Args:
            request: The canonical chat request.
            ctx: The per-request governance context.

        Returns:
            The canonical chunk stream; its terminal chunk carries
            `StreamEnd(usage, finish, report)`.
        """
        # TODO: §8 streaming — encode via graph, then
        # codec.bind_resource(payload, self._model_name); build the pipeline via
        # catalog.stream_converter(wire chunk node -> canonical chunk node)
        # (fresh per stream) and pass it to SyncDriver.stream, which yields
        # the converted chunks and flushes at end-of-stream (WU-09 seam);
        # wrap in ChatStream, then read pipeline.reports after iteration and
        # stamp StreamEnd.report = request-leg report + those flush reports.
        raise NotImplementedError

    async def astream(
        self,
        request: ChatRequest,
        *,
        ctx: CallContext | None = None,
    ) -> AsyncChatStream:
        """Send a streaming chat request, asynchronously.

        The `a`-twin of `stream`, with the same bound-model injection.

        Args:
            request: The canonical chat request.
            ctx: The per-request governance context.

        Returns:
            The async canonical chunk stream.
        """
        # TODO: same streaming pipeline over AsyncDriver, wrapped in
        # AsyncChatStream — the same WU-09 seam: the driver yields converted
        # chunks; StreamEnd.report is stamped from pipeline.reports.
        raise NotImplementedError

    @property
    def details(self) -> dict[str, Any]:
        """Describe this facade's composition.

        Returns:
            A mapping with the bound model name and pins; grows the codec's
            declared capabilities once the codec protocol lands.
        """
        # TODO: merge the codec's capability declaration and the binding's
        # host label once those surfaces exist.
        return {
            "model_name": self._model_name,
            "interface": self._interface,
            "tag": self._tag,
        }
