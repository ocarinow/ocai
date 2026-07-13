"""`WireChatModel` — the wire-backed facade (architecture §3.3, §3.4, §8).

The ONE chat module allowed to import `ocai.convert` / `ocai.runtime` /
`ocai.wire` (the port and the types never do). Named `facade`, not `model`,
by convention: a facade module never shares the front-door factory's name,
so the future `ocai.chat.model()` factory (§3.4) is never shadowed by the
module that implements it. A provider is not a subclass
but a **composition of three values plus a bound resource**:

- a dialect **codec** — the wire I/O for one provider interface (shipped by
  the plugin, per §7; typed here as the `ChatCodec` protocol),
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

Sans-io discipline: everything except the physical send is synchronous and
shared — `chat` and `achat` run the *same* `_prepare`/`_assemble` helpers
and differ only in which driver executes the wire attempt.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol

from ocai.chat.canonical import CANONICAL_CHAT_REQUEST
from ocai.chat.canonical import CANONICAL_CHAT_RESPONSE
from ocai.chat.types.request import ChatRequest
from ocai.chat.types.response import ChatResponse
from ocai.chat.types.stream import AsyncChatStream
from ocai.chat.types.stream import ChatStream
from ocai.core.identity import CHAT
from ocai.core.identity import CHAT_RESPONSE
from ocai.core.result import CallContext
from ocai.core.result import CallResult
from ocai.runtime.binding import CompositionError
from ocai.runtime.drivers import AsyncDriver
from ocai.runtime.drivers import SyncDriver
from ocai.wire.hosting import EndpointSpec
from ocai.wire.hosting import Operation

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ocai.chat.types.stream import ChatChunk
    from ocai.convert.catalog import Catalog
    from ocai.convert.graph import EdgeOutput
    from ocai.core.errors import OcaiError
    from ocai.core.fidelity import FidelityReport
    from ocai.core.fidelity import Route
    from ocai.core.identity import NodeId
    from ocai.core.traits import DialectTraits
    from ocai.runtime.binding import Binding
    from ocai.runtime.decisions import WirePolicy


class ChatCodec(Protocol):
    """The dialect-codec surface a chat plugin ships, typed structurally.

    What `ocai.openai.chat_completions.ChatCompletionsCodec` and
    `ocai.anthropic.messages.MessagesCodec` actually share (§7): the
    interface's identity (provider/interface labels and the three shape
    nodes), the pure mapping halves (`encode_request` / `decode_response` /
    `decode_event` — wrapped into graph edges by the plugin's fragment, so
    the facade converts through the catalog and never calls them directly),
    and the wire-hygiene members the facade *does* consult per call:
    `native_path`, `dialect_traits`, `bind_resource`, and `map_error`.

    The protocol's home is this module because the facade is the only core
    consumer of the codec surface; plugins satisfy it structurally and never
    import it.
    """

    provider: str
    interface: str
    request_node: NodeId
    response_node: NodeId
    chunk_node: NodeId

    def native_path(self, model: str) -> str:
        """Return the dialect's first-party URL path for a chat call."""
        ...

    def dialect_traits(self) -> DialectTraits:
        """Return the dialect's hosting traits, read by any `Host` as data."""
        ...

    def bind_resource(self, payload: dict[str, Any], resource: str) -> dict[str, Any]:
        """Inject the bound model name into an encoded wire payload."""
        ...

    def encode_request(self, request: ChatRequest) -> EdgeOutput:
        """Encode a canonical `ChatRequest` into this dialect's wire body."""
        ...

    def decode_response(self, payload: dict[str, Any]) -> EdgeOutput:
        """Decode this dialect's response body into a canonical `ChatResponse`."""
        ...

    def decode_event(self, event: str | None, data: str) -> ChatChunk | None:
        """Decode one SSE frame into a canonical `ChatChunk`, if it surfaces one."""
        ...

    def map_error(self, status: int | None, body: dict[str, Any] | None) -> OcaiError | None:
        """Refine a coarse taxonomy error from the provider's error body."""
        ...


# The one chat operation, capability-fixed: hosts switch on `kind` (an
# endpoint family), and chat rides the generative family everywhere. The
# streaming twin (WU-11) derives from it with `streaming=True`.
_CHAT_OPERATION = Operation(name="chat", kind="generative")


@dataclass(frozen=True, slots=True)
class _PreparedCall:
    """One call's sans-io preamble: everything computed before the send.

    Produced by `WireChatModel._prepare` (shared by `chat` and `achat` — the
    sans-io rule) and consumed by `WireChatModel._assemble` after the driver
    returns.

    Attributes:
        route: The resolution record, host-stamped, carrying the catalog
            hash.
        spec: The endpoint spec the driver executes against.
        payload: The encoded wire body with the bound model injected.
        report: The request leg of the call's `FidelityReport`; the response
            leg is merged onto it at assembly.
    """

    route: Route
    spec: EndpointSpec
    payload: dict[str, Any]
    report: FidelityReport


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
        codec: ChatCodec,
        binding: Binding,
        catalog: Catalog,
        *,
        model_name: str,
        interface: str | None = None,
        tag: str | None = None,
        policies: Sequence[WirePolicy] = (),
    ) -> None:
        """Compose the facade from its three values and the bound resource.

        Args:
            codec: The dialect codec for the target provider interface —
                the `ChatCodec` surface the plugin ships (architecture §7).
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
            interface: The provider interface to pin, or None to pin the
                codec's own interface — the facade is composed *of* a
                dialect, so resolution can never wander onto a wire the
                codec does not speak (letting the catalog choose freely is
                the §3.4 front doors' job: they resolve first, then build
                the matching codec from the fragment's component factory).
            tag: The interface revision tag to pin, or None for latest
                eligible.
            policies: The wire-tier hooks (retry, rate-limit, wiretap) the
                drivers consult on every attempt, in order.
        """
        self._codec = codec
        self._binding = binding
        self._catalog = catalog
        self._model_name = model_name
        self._interface = interface
        self._tag = tag
        self._sync_driver = SyncDriver(binding, policies=policies)
        self._async_driver = AsyncDriver(binding, policies=policies)

    # --- The shared sans-io halves (identical for chat and achat) ---------

    def _refine_error(self, err: OcaiError) -> OcaiError | None:
        """Close the codec's body-aware `map_error` over a coarse wire error.

        The driver's `ErrorRefiner` seam (layer 2 of the two-layer error
        mapping): the transport classified by status; the codec refines from
        the provider's error body (`err.raw`, never a secret). Returning
        None keeps the coarse classification.

        Args:
            err: The coarse, status-based error the transport raised.

        Returns:
            The precise dialect error, or None to keep `err`.
        """
        return self._codec.map_error(err.status, err.raw)

    def _prepare(self, request: ChatRequest) -> _PreparedCall:
        """Run the pre-send lifecycle: resolve → encode → bind → spec.

        The request leg of §8, entirely synchronous and shared between
        `chat` and `achat`. The bound-model injection happens HERE, owned by
        the facade: graph edges stay model-agnostic (the encoded payload has
        no model member), and only the codec knows where its wire carries
        the name (`bind_resource`, the WU-05a seam).

        Args:
            request: The canonical chat request — pure conversation.

        Returns:
            The prepared call: host-stamped route, endpoint spec, bound
            payload, and the request-leg report.

        Raises:
            CompositionError: If an explicitly pinned interface disagrees
                with the composed codec's dialect.
            ResolutionError: If the catalog cannot resolve the pins.
            ConversionError: If no conversion path reaches the resolved
                node.
        """
        route = self._catalog.resolve(
            CHAT,
            self._codec.provider,
            interface=self._interface if self._interface is not None else self._codec.interface,
            tag=self._tag,
        )
        if route.node.interface != self._codec.interface:
            raise CompositionError(
                f"interface pin {self._interface!r} resolved to "
                f"{route.node.provider}/{route.node.interface}, but this facade is "
                f"composed with the {self._codec.provider}/{self._codec.interface} "
                "codec; pin the codec's interface (or none) or compose the matching codec."
            )
        encoded = self._catalog.convert(request, CANONICAL_CHAT_REQUEST, route.node)
        payload = self._codec.bind_resource(encoded.value, self._model_name)
        spec = EndpointSpec(
            dialect=route.node,
            traits=self._codec.dialect_traits(),
            op=_CHAT_OPERATION,
            resource=self._model_name,
            native_path=self._codec.native_path(self._model_name),
        )
        # Hosting is resolved below the graph: stamp where the call is
        # physically going (the audit joint's `host` lane) after the spec
        # exists, so resolution itself never knows clouds exist.
        route = replace(route, host=self._binding.host.endpoint(spec))
        return _PreparedCall(route=route, spec=spec, payload=payload, report=encoded.report)

    def _response_node(self, request_node: NodeId) -> NodeId:
        """Return the response-shape sibling of a resolved request node.

        Resolution operates on request-shape nodes (`Catalog.resolve`); the
        decode leg needs the same interface revision's response shape, which
        the serving fragment published alongside it.

        Args:
            request_node: The resolved request-shape node from the `Route`.

        Returns:
            The published response-shape node with the same
            provider/interface/tag coordinates.

        Raises:
            ResolutionError: If the composed catalog publishes no response
                shape for the revision — a malformed fragment.
        """
        from ocai.convert.catalog import ResolutionError

        for node in self._catalog.nodes:
            if (
                node.provider == request_node.provider
                and node.interface == request_node.interface
                and node.tag == request_node.tag
                and node.shape == CHAT_RESPONSE
            ):
                return node
        raise ResolutionError(
            f"the composed catalog publishes no chat.response node for "
            f"{request_node.provider}/{request_node.interface}@{request_node.tag}; "
            "the serving fragment must publish the response shape it decodes"
        )

    def _assemble(self, prepared: _PreparedCall, raw: dict[str, Any]) -> CallResult[ChatResponse]:
        """Run the post-send lifecycle: decode → merge reports → envelope.

        The response leg of §8, shared between `chat` and `achat`. The raw
        body decodes through the graph (wire response node → canonical), its
        report is folded onto the request leg, usage is lifted off the
        decoded response, and the untouched body rides `CallResult.raw`.

        Args:
            prepared: The call's pre-send preamble.
            raw: The raw response body the driver returned, untouched.

        Returns:
            The uniform envelope: value, route, two-leg report, usage, raw.

        Raises:
            ConversionError: If no conversion path decodes the response
                node.
        """
        decoded = self._catalog.convert(
            raw, self._response_node(prepared.route.node), CANONICAL_CHAT_RESPONSE
        )
        response: ChatResponse = decoded.value
        return CallResult(
            value=response,
            route=prepared.route,
            report=prepared.report.merge(decoded.report),
            usage=response.usage,
            raw=raw,
        )

    # --- The port methods ---------------------------------------------------

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
        the driver send. The driver runs the wire pipeline (policy hooks,
        host envelope, credential at the leaf per attempt, send) with the
        codec's `map_error` as the layer-2 error refiner.

        Args:
            request: The canonical chat request.
            ctx: The per-request governance context. Accepted per the port
                contract; threading it into the wire policy hooks is a later
                WU's seam.

        Returns:
            The uniform envelope: response, `Route` (host-stamped, carrying
            the catalog hash), merged `FidelityReport` (request leg +
            response leg), usage, and the untouched raw body.

        Raises:
            OcaiError: The refined taxonomy error when the wire attempt
                ultimately fails.
            CompositionError: If the composed stack cannot serve the call.
        """
        prepared = self._prepare(request)
        raw = self._sync_driver.execute(
            spec=prepared.spec,
            payload=prepared.payload,
            refine_error=self._refine_error,
        )
        return self._assemble(prepared, raw)

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
            ctx: The per-request governance context. Accepted per the port
                contract; threading it into the wire policy hooks is a later
                WU's seam.

        Returns:
            The uniform envelope carrying the canonical `ChatResponse`.

        Raises:
            OcaiError: The refined taxonomy error when the wire attempt
                ultimately fails.
            CompositionError: If the composed stack cannot serve the call.
        """
        prepared = self._prepare(request)
        raw = await self._async_driver.execute(
            spec=prepared.spec,
            payload=prepared.payload,
            refine_error=self._refine_error,
        )
        return self._assemble(prepared, raw)

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
        # TODO: §8 streaming (WU-11) — reuse _prepare (with a streaming
        # Operation derived from _CHAT_OPERATION), then build the pipeline via
        # catalog.stream_converter(codec.chunk_node -> canonical chunk node)
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
            A mapping with the codec's dialect coordinates, the bound model
            name, and the pins.
        """
        return {
            "provider": self._codec.provider,
            "interface": self._interface if self._interface is not None else self._codec.interface,
            "model_name": self._model_name,
            "tag": self._tag,
        }
