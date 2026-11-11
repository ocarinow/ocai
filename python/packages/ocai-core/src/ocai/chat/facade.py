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

import hashlib
from collections.abc import Awaitable
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import replace
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol

from ocai.chat.canonical import CANONICAL_CHAT_CHUNK
from ocai.chat.canonical import CANONICAL_CHAT_REQUEST
from ocai.chat.canonical import CANONICAL_CHAT_RESPONSE
from ocai.chat.types.config import OutputMode
from ocai.chat.types.parts import PartType
from ocai.chat.types.request import ChatRequest
from ocai.chat.types.response import ChatResponse
from ocai.chat.types.stream import AsyncChatStream
from ocai.chat.types.stream import ChatChunk
from ocai.chat.types.stream import ChatStream
from ocai.chat.types.stream import ChunkType
from ocai.chat.types.stream import StreamEnd
from ocai.convert.inspection import ExecutionInspection
from ocai.convert.inspection import FeatureCoverage
from ocai.core.canonjson import canonical
from ocai.core.errors import OcaiError
from ocai.core.errors import StreamProtocolError
from ocai.core.errors import UnsupportedFeatureError
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import EdgeReport
from ocai.core.fidelity import FidelityPolicy
from ocai.core.fidelity import FidelityPolicyError
from ocai.core.fidelity import FidelityReport
from ocai.core.fidelity import FieldLoss
from ocai.core.identity import CHAT
from ocai.core.identity import CHAT_CHUNK
from ocai.core.identity import CHAT_RESPONSE
from ocai.core.profile import Support
from ocai.core.profile import declared_support
from ocai.core.profile import resolve_support
from ocai.core.result import CallContext
from ocai.core.result import CallResult
from ocai.runtime.binding import CompositionError
from ocai.runtime.deadline import Deadline
from ocai.runtime.drivers import AsyncDriver
from ocai.runtime.drivers import SyncDriver
from ocai.runtime.drivers import build_request
from ocai.runtime.interceptors import AsyncStream
from ocai.runtime.interceptors import Call
from ocai.runtime.interceptors import StreamInterceptor
from ocai.runtime.interceptors import SyncStream
from ocai.runtime.interceptors import acompose
from ocai.runtime.interceptors import acompose_stream
from ocai.runtime.interceptors import compose
from ocai.runtime.interceptors import compose_stream
from ocai.runtime.observe import Invocation
from ocai.runtime.observe import Observer
from ocai.runtime.observe import failure_status
from ocai.wire.framing import StreamFraming
from ocai.wire.hosting import EndpointSpec
from ocai.wire.hosting import Operation
from ocai.wire.hosting import profile_key
from ocai.wire.hosting import stream_framing

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from collections.abc import Iterator
    from collections.abc import Sequence

    from ocai.chat.protocol import ChatModel
    from ocai.convert.catalog import Catalog
    from ocai.convert.graph import EdgeOutput
    from ocai.convert.graph import StreamPipeline
    from ocai.core.fidelity import Route
    from ocai.core.identity import NodeId
    from ocai.core.traits import DialectTraits
    from ocai.runtime.binding import Binding
    from ocai.runtime.decisions import WirePolicy
    from ocai.runtime.interceptors import CallInterceptor
    from ocai.wire.http import HttpRequest


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

    def bind_stream(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Mark an encoded wire payload as a streaming request."""
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
# streaming twin derives from it with `streaming=True` — same name, same
# family, only the response mode differs.
_CHAT_OPERATION = Operation(name="chat", kind="generative")
_STREAM_OPERATION = replace(_CHAT_OPERATION, streaming=True)


# --- The feature gate's request census (WU-12) ---------------------------------
#
# The namespaced feature keys a request can exhibit, aligned with the
# vocabulary the plugins' PROFILES declare (`"chat.config.temperature"`,
# `"chat.parts.audio"`, ...). Keys are open data (§2.5): a key derived here
# that no profile declares resolves NATIVE — absence of a declared limitation
# is not a limitation — so this census may name more than any profile does.

# Scalar/config knobs: attribute on `ChatConfig` -> feature key.
_CONFIG_FEATURES: tuple[tuple[str, str], ...] = (
    ("temperature", "chat.config.temperature"),
    ("top_p", "chat.config.top_p"),
    ("max_output_tokens", "chat.config.max_output_tokens"),
    ("stop_sequences", "chat.config.stop_sequences"),
    ("seed", "chat.config.seed"),
    ("frequency_penalty", "chat.config.frequency_penalty"),
    ("presence_penalty", "chat.config.presence_penalty"),
    ("top_k", "chat.config.top_k"),
    ("logprobs", "chat.config.logprobs"),
    ("modalities", "chat.config.modalities"),
    ("audio", "chat.config.audio"),
    ("cache", "chat.config.cache"),
)

# Gate-relevant part kinds: a media part needs a wire lane, and a reasoning
# part in a *request* is a replay. Text/tool parts ride the universal lanes
# and are not profile-gated.
_PART_FEATURES: dict[PartType, str] = {
    PartType.IMAGE: "chat.parts.image",
    PartType.AUDIO: "chat.parts.audio",
    PartType.VIDEO: "chat.parts.video",
    PartType.DOCUMENT: "chat.parts.document",
    PartType.REASONING: "chat.parts.reasoning.replay",
}


def _request_features(request: ChatRequest) -> tuple[tuple[str, str], ...]:
    """Derive the feature keys a request exhibits, with their field paths.

    The gate's census of one concrete request: every set config knob, the
    structured-output mode, the reasoning dials, tool presence, and the
    gate-relevant part kinds, each as a `(feature_key, path)` pair. Paths are
    canonical-request paths (`"config.temperature"`,
    `"messages[0].parts[1]"`) so annotate-mode `FieldLoss` records anchor to
    the field the user actually set. Occurrences are not de-duplicated —
    every gated part is its own field, reported individually.

    Args:
        request: The canonical request about to be gated.

    Returns:
        The `(feature_key, path)` pairs present, in stable order (config
        knobs, then tools, then parts in conversation order).
    """
    found: list[tuple[str, str]] = []
    config = request.config
    if config is not None:
        for attr, feature in _CONFIG_FEATURES:
            if getattr(config, attr) is not None:
                found.append((feature, f"config.{attr}"))
        if config.parallel_tool_calls is not None:
            found.append(("chat.tools.parallel", "config.parallel_tool_calls"))
        if config.reasoning is not None:
            if config.reasoning.effort is not None:
                found.append(("chat.config.reasoning.effort", "config.reasoning.effort"))
            if config.reasoning.budget_tokens is not None:
                found.append(
                    ("chat.config.reasoning.budget_tokens", "config.reasoning.budget_tokens")
                )
        if config.output is not None:
            if config.output.mode == OutputMode.JSON_SCHEMA:
                found.append(("chat.config.output.json_schema", "config.output"))
            elif config.output.mode == OutputMode.JSON:
                found.append(("chat.config.output.json", "config.output"))
    if request.tools:
        found.append(("chat.tools", "tools"))
    for i, message in enumerate(request.messages):
        for j, part in enumerate(message.parts):
            part_feature = _PART_FEATURES.get(getattr(part, "type", PartType.UNDEFINED))
            if part_feature is not None:
                found.append((part_feature, f"messages[{i}].parts[{j}]"))
    return tuple(found)


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
        report: The request leg of the call's `FidelityReport` (led by the
            feature gate's record when annotate mode found `ABSENT`
            features); the response leg is merged onto it at assembly.
        framing: Pinned host framing selection for streams; absent for unary calls.
    """

    route: Route
    spec: EndpointSpec
    payload: dict[str, Any]
    report: FidelityReport
    framing: StreamFraming | None = None


class StalePreparationError(OcaiError):
    """Prepared request or configuration changed; inspect and approve again."""


class PreparedChatCall:
    """A detached execution snapshot with public inspection and governed call faces.

    Inspection and request properties return copies. Execution runs the original
    snapshot, through the same middleware/observation composition that prepared it.
    A handle is in-process, not a portable authorization token or durable job.
    """

    def __init__(self, request: ChatRequest, inspection: ExecutionInspection,
                 model: ChatModel) -> None:
        """Build through a model's prepare method; callers inspect returned handles."""
        self._request = deepcopy(request)
        self._inspection = deepcopy(inspection)
        self._model = model

    @property
    def inspection(self) -> ExecutionInspection:
        """Return detached route, declarations, coverage and request findings."""
        return deepcopy(self._inspection)

    @property
    def request(self) -> ChatRequest:
        """Return a detached canonical request for admission and diagnostics."""
        return deepcopy(self._request)

    def wrap(self, wrapper: Callable[[ChatModel], ChatModel]) -> PreparedChatCall:
        """Wrap the approved execution port while retaining its inspection snapshot."""
        return PreparedChatCall(self._request, self._inspection, wrapper(self._model))

    def chat(self, *, ctx: CallContext | None = None) -> CallResult[ChatResponse]:
        """Execute the approved unary snapshot through its original governance chain."""
        if self._inspection.streaming:
            raise StalePreparationError("stream preparation cannot execute as unary")
        return self._model.chat(self.request, ctx=ctx)

    async def achat(self, *, ctx: CallContext | None = None) -> CallResult[ChatResponse]:
        """Execute the approved unary snapshot asynchronously."""
        if self._inspection.streaming:
            raise StalePreparationError("stream preparation cannot execute as unary")
        return await self._model.achat(self.request, ctx=ctx)

    def stream(self, *, ctx: CallContext | None = None) -> ChatStream:
        """Execute the approved stream snapshot with explicit stream ownership."""
        if not self._inspection.streaming:
            raise StalePreparationError("unary preparation cannot execute as a stream")
        return self._model.stream(self.request, ctx=ctx)

    async def astream(self, *, ctx: CallContext | None = None) -> AsyncChatStream:
        """Execute the approved stream snapshot asynchronously."""
        if not self._inspection.streaming:
            raise StalePreparationError("unary preparation cannot execute as a stream")
        return await self._model.astream(self.request, ctx=ctx)


def _wire_identity(request: HttpRequest) -> str:
    """Fingerprint pre-authentication wire semantics; execution metadata is excluded."""
    return hashlib.sha256(canonical({
        "method": request.method, "url": request.url, "headers": request.headers,
        "body": request.body.hex() if request.body else None, "stream": request.stream,
    }).encode()).hexdigest()


def _prepare_port(model: ChatModel, request: ChatRequest, streaming: bool) -> PreparedChatCall:
    """Use the optional public preparation capability without private gateway access."""
    method = getattr(model, "prepare", None)
    if method is None:
        raise CompositionError("this local capability does not expose conversion preparation")
    result = method(request, streaming=streaming)
    if not isinstance(result, PreparedChatCall):
        raise CompositionError("prepare must return PreparedChatCall")
    return result


class _PreparedModel:
    """Bound approved execution with explicit internal continuations."""

    def __init__(
        self, request: ChatRequest, data: _PreparedCall, *,
        guard: Callable[[HttpRequest], None], build: Callable[[], HttpRequest],
        chat: Callable[[_PreparedModel, ChatRequest, CallContext | None], CallResult[ChatResponse]],
        achat: Callable[[_PreparedModel, ChatRequest, CallContext | None],
                        Awaitable[CallResult[ChatResponse]]],
        stream: Callable[[_PreparedModel, ChatRequest, CallContext | None], ChatStream],
        astream: Callable[[_PreparedModel, ChatRequest, CallContext | None],
                          Awaitable[AsyncChatStream]],
        details: dict[str, Any],
    ) -> None:
        self.data = deepcopy(data)
        self.guard = guard
        self.build = build
        self.run_chat, self.run_achat = chat, achat
        self.run_stream, self.run_astream = stream, astream
        self.details = details
        self.request_identity = canonical(request.to_dict())

    def consume(self, request: ChatRequest, *, streaming: bool) -> _PreparedCall:
        if (canonical(request.to_dict()) != self.request_identity
                or streaming != self.data.spec.op.streaming):
            raise StalePreparationError("admission changed the approved request; prepare again")
        self.guard(self.build())
        return deepcopy(self.data)

    def chat(self, request: ChatRequest,
             *, ctx: CallContext | None = None) -> CallResult[ChatResponse]:
        return self.run_chat(self, request, ctx)

    async def achat(self, request: ChatRequest,
                    *, ctx: CallContext | None = None) -> CallResult[ChatResponse]:
        return await self.run_achat(self, request, ctx)

    def stream(self, request: ChatRequest, *, ctx: CallContext | None = None) -> ChatStream:
        return self.run_stream(self, request, ctx)

    async def astream(self, request: ChatRequest,
                      *, ctx: CallContext | None = None) -> AsyncChatStream:
        return await self.run_astream(self, request, ctx)


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
        strict: bool = False,
        attempt_observers: Sequence[Observer] = (),
        conversion_policy: FidelityPolicy | None = None,
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
            conversion_policy: Enforce field and semantic acceptance before I/O
                and after response conversion; stream output cannot be retracted.
            attempt_observers: Physical-attempt metadata observers. Wrap this
                model in ObservedChatModel for logical invocation events; the
                core model factory composes both automatically.
            strict: The feature-gate mode (§2.5). False (annotate, the
                default): a request feature the destination's
                `CapabilityProfile` declares `ABSENT` is recorded as an
                `UNSUPPORTED` field loss on the call's report and the call
                proceeds, payload untouched. True (strict): the same fact
                raises `UnsupportedFeatureError` before the request is
                encoded — nothing reaches the wire.
        """
        self._codec = codec
        self._binding = binding
        self._catalog = catalog
        self._model_name = model_name
        self._interface = interface
        self._tag = tag
        self._strict = strict
        self._conversion_policy = conversion_policy
        self._sync_driver = SyncDriver(binding, policies=policies, observers=attempt_observers)
        self._async_driver = AsyncDriver(binding, policies=policies, observers=attempt_observers)

    def _configuration(self, prepared: _PreparedCall) -> str:
        """Identify effective wire/configuration semantics without credentials."""
        _, request = build_request(self._binding, prepared.spec, prepared.payload)
        return hashlib.sha256(canonical({
            "wire": _wire_identity(request), "model": self._model_name,
            "interface": self._interface, "tag": self._tag, "strict": self._strict,
            "catalog": self._catalog.lock().hash,
            "profile_key": profile_key(self._binding.host, self._model_name),
            "framing": (stream_framing(self._binding.host, prepared.spec).configuration_id
                        if prepared.spec.op.streaming else None),
            "policy": id(self._conversion_policy) if self._conversion_policy else None,
        }).encode()).hexdigest()

    def prepare(self, request: ChatRequest, *, streaming: bool = False) -> PreparedChatCall:
        """Inspect and snapshot conversion without authentication or provider I/O."""
        snapshot = deepcopy(request)
        prepared = self._prepare(deepcopy(snapshot), streaming=streaming)
        profiles = self._catalog.profiles_for(
            prepared.route.node.provider, prepared.route.node.interface,
            profile_key(self._binding.host, self._model_name),
        )
        coverage = tuple(FeatureCoverage(
            feature, path, declared_support(profiles, feature),
            next((p.model_pattern for p in profiles if feature in p.features), None),
        ) for feature, path in _request_features(snapshot))
        response_src = (self._chunk_node(prepared.route.node) if streaming
                        else self._response_node(prepared.route.node))
        inspection = ExecutionInspection(
            prepared.route,
            self._catalog.inspect(CANONICAL_CHAT_REQUEST, prepared.route.node),
            self._catalog.inspect(response_src,
                                  CANONICAL_CHAT_CHUNK if streaming else CANONICAL_CHAT_RESPONSE,
                                  streaming=streaming),
            tuple(profiles), coverage, prepared.report, self._configuration(prepared), streaming,
        )
        _, wire = build_request(self._binding, prepared.spec, prepared.payload)
        identity, wire_identity = inspection.configuration_id, _wire_identity(wire)
        header_names = tuple(wire.headers)
        normalized_headers = {name.casefold() for name in header_names}

        def guard(request: HttpRequest) -> None:
            if self._conversion_policy is not None:
                self._conversion_policy.enforce(prepared.report, phase="request",
                                                route=prepared.route)
            # Explicit hooks may add transport metadata; changing approved fields
            # or effective host/configuration requires a fresh inspection.
            if any(name not in header_names and name.casefold() in normalized_headers
                   for name in request.headers):
                raise StalePreparationError(
                    "approved header shadowed by a case alias; prepare again")
            checked = replace(request, headers={key: request.headers[key]
                                                for key in header_names if key in request.headers})
            if (prepared.framing is not None and prepared.framing.configuration_id !=
                    stream_framing(self._binding.host, prepared.spec).configuration_id):
                raise StalePreparationError("stream framing changed; prepare again")
            if (self._configuration(prepared) != identity
                    or _wire_identity(checked) != wire_identity):
                raise StalePreparationError("configuration or wire request changed; prepare again")

        executor = _PreparedModel(
            snapshot, prepared, guard=guard,
            build=lambda: build_request(self._binding, prepared.spec, prepared.payload)[1],
            chat=lambda bound, request, ctx: self._chat_prepared(bound, request, ctx=ctx),
            achat=lambda bound, request, ctx: self._achat_prepared(bound, request, ctx=ctx),
            stream=lambda bound, request, ctx: self._stream_prepared(bound, request, ctx=ctx),
            astream=lambda bound, request, ctx: self._astream_prepared(bound, request, ctx=ctx),
            details=self.details,
        )
        return PreparedChatCall(snapshot, inspection, executor)

    def chat(self, request: ChatRequest,
             *, ctx: CallContext | None = None) -> CallResult[ChatResponse]:
        """Prepare and execute one governed synchronous call."""
        Deadline(ctx).remaining()
        return self.prepare(request).chat(ctx=ctx)

    async def achat(self, request: ChatRequest,
                    *, ctx: CallContext | None = None) -> CallResult[ChatResponse]:
        """Prepare and execute one governed async call."""
        Deadline(ctx).remaining()
        return await self.prepare(request).achat(ctx=ctx)

    def stream(self, request: ChatRequest, *, ctx: CallContext | None = None) -> ChatStream:
        """Prepare eagerly and return an owned, lazy stream."""
        Deadline(ctx).remaining()
        return self.prepare(request, streaming=True).stream(ctx=ctx)

    async def astream(self, request: ChatRequest,
                      *, ctx: CallContext | None = None) -> AsyncChatStream:
        """Prepare eagerly and return an owned async stream."""
        Deadline(ctx).remaining()
        return await self.prepare(request, streaming=True).astream(ctx=ctx)

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

    def _gate(self, request: ChatRequest, route: Route) -> FidelityReport:
        """Run the feature gate: profile facts checked BEFORE any encoding.

        Derives the request's feature keys (`_request_features`), resolves
        each against the catalog's specificity-ranked `CapabilityProfile`s
        for the resolved `(provider, interface)` and the bound model
        (`resolve_support` — first declaration wins, undeclared is NATIVE),
        and acts on every `ABSENT` fact per the composed mode: strict raises
        before a doomed payload is ever built; annotate returns the losses
        as one gate `EdgeReport` to be merged ahead of the request leg. The
        payload itself is never touched — values pass verbatim (the codec's
        job is translation, not opinion), so annotate mode warns honestly
        and lets the provider stay authoritative.

        Args:
            request: The canonical request about to be encoded.
            route: The resolved route naming the destination interface.

        Returns:
            A report holding one gate `EdgeReport` when annotate mode found
            `ABSENT` features; an empty report otherwise.

        Raises:
            UnsupportedFeatureError: In strict mode, when any feature on the
                request is declared `ABSENT` for the bound model.
        """
        features = _request_features(request)
        if not features:
            return FidelityReport()
        profiles = self._catalog.profiles_for(
            route.node.provider, route.node.interface,
            profile_key(self._binding.host, self._model_name)
        )
        if not profiles:
            return FidelityReport()
        absent = [
            (feature, path)
            for feature, path in features
            if resolve_support(profiles, feature) is Support.ABSENT
        ]
        if not absent:
            return FidelityReport()
        if self._strict:
            names = tuple(sorted({feature for feature, _ in absent}))
            raise UnsupportedFeatureError(
                f"{route.node.provider}/{route.node.interface} declares "
                f"{', '.join(names)} absent for model {self._model_name!r}; "
                "unset the feature(s), pick another model, or compose with "
                "strict=False to record the loss instead",
                features=names,
                model=self._model_name,
                provider=route.node.provider,
            )
        losses = tuple(
            FieldLoss(
                path=path,
                disposition=Disposition.UNSUPPORTED,
                note=(
                    f"feature gate: {feature} is declared absent on "
                    f"{route.node.provider}/{route.node.interface} "
                    f"for model {self._model_name!r}"
                ),
            )
            for feature, path in absent
        )
        return FidelityReport(
            edges=[
                EdgeReport(
                    src=CANONICAL_CHAT_REQUEST,
                    dst=route.node,
                    losses=losses,
                    note="feature gate (pre-encode)",
                )
            ]
        )

    def _prepare(self, request: ChatRequest, *, streaming: bool = False) -> _PreparedCall:
        """Run the pre-send lifecycle: resolve → encode → bind → spec.

        The request leg of §8, entirely synchronous and shared between all
        four port methods (the sans-io rule). The bound-model injection
        happens HERE, owned by the facade: graph edges stay model-agnostic
        (the encoded payload has no model member), and only the codec knows
        where its wire carries the name (`bind_resource`, the WU-05a seam).
        The streaming marking follows the same principle: graph edges never
        see it (a `ChatRequest` is pure conversation; how a dialect asks for
        a stream is wire hygiene), so the codec's `bind_stream` injects it
        after `bind_resource` and the spec carries the streaming operation.

        Args:
            request: The canonical chat request — pure conversation.
            streaming: Whether this call streams its response — selects the
                streaming `Operation` and applies the codec's `bind_stream`
                to the bound payload.

        Returns:
            The prepared call: host-stamped route, endpoint spec, bound
            payload, and the request-leg report.

        Raises:
            CompositionError: If an explicitly pinned interface disagrees
                with the composed codec's dialect.
            ResolutionError: If the catalog cannot resolve the pins.
            UnsupportedFeatureError: In strict mode, when the feature gate
                finds a request feature the destination's profile declares
                `ABSENT` — raised before any encoding, nothing reaches the
                wire.
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
        # The feature gate runs BEFORE encode (§2.5): strict mode refuses a
        # doomed request without ever building its payload; annotate mode
        # collects the gate's UNSUPPORTED records to lead the request leg.
        gate = self._gate(request, route)
        encoded = self._catalog.convert(request, CANONICAL_CHAT_REQUEST, route.node)
        report = gate.merge(encoded.report) if gate.edges else encoded.report
        payload = self._codec.bind_resource(encoded.value, self._model_name)
        if streaming:
            payload = self._codec.bind_stream(payload)
        spec = EndpointSpec(
            dialect=route.node,
            traits=self._codec.dialect_traits(),
            op=_STREAM_OPERATION if streaming else _CHAT_OPERATION,
            resource=self._model_name,
            native_path=self._codec.native_path(self._model_name),
        )
        # Hosting is resolved below the graph: stamp where the call is
        # physically going (the audit joint's `host` lane) after the spec
        # exists, so resolution itself never knows clouds exist.
        route = replace(route, host=self._binding.host.endpoint(spec))
        return _PreparedCall(
            route=route, spec=spec, payload=payload, report=report,
            framing=stream_framing(self._binding.host, spec) if streaming else None,
        )

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

    def _chunk_node(self, request_node: NodeId) -> NodeId:
        """Return the chunk-shape sibling of a resolved request node.

        The streaming twin of `_response_node`: the stream's decode leg
        needs the same interface revision's chunk shape — the source node of
        the `StreamPipeline` the driver pumps wire frames through. Resolved
        from the catalog (not read off the codec) so the resolved revision
        stays authoritative for every leg of the call.

        Args:
            request_node: The resolved request-shape node from the `Route`.

        Returns:
            The published chunk-shape node with the same
            provider/interface/tag coordinates.

        Raises:
            ResolutionError: If the composed catalog publishes no chunk
                shape for the revision — a malformed fragment for a
                streaming call.
        """
        from ocai.convert.catalog import ResolutionError

        for node in self._catalog.nodes:
            if (
                node.provider == request_node.provider
                and node.interface == request_node.interface
                and node.tag == request_node.tag
                and node.shape == CHAT_CHUNK
            ):
                return node
        raise ResolutionError(
            f"the composed catalog publishes no chat.chunk node for "
            f"{request_node.provider}/{request_node.interface}@{request_node.tag}; "
            "the serving fragment must publish the chunk shape it streams"
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
        report = prepared.report.merge(decoded.report)
        if self._conversion_policy is not None:
            self._conversion_policy.enforce(report, phase="response", usage=response.usage,
                                            route=prepared.route)
        return CallResult(value=response, route=prepared.route, report=report,
                          usage=response.usage, raw=raw)

    def _stamp_stream_report(
        self, terminal: ChatChunk, prepared: _PreparedCall, pipeline: StreamPipeline
    ) -> None:
        """Stamp the stream's two-leg `FidelityReport` onto its terminal chunk.

        The facade's half of the WU-09 seam, the streaming mirror of
        `_assemble`'s report merge: the request leg (gate + encode edges)
        is folded with the pipeline's per-edge flush accounting
        (`StreamPipeline.reports`, populated once the driver flushed at
        end-of-stream) and lands on `StreamEnd.report` — the streaming
        path's one report home. A codec that already stamped records onto
        the terminal's own report keeps them, appended after the two legs.

        Args:
            terminal: The stream's terminal `STREAM_STOP` chunk; its
                `StreamEnd` is enriched in place (or created bare when a
                dialect emitted a terminal without one).
            prepared: The call's pre-send preamble carrying the request-leg
                report.
            pipeline: The flushed stream pipeline whose `reports` carry the
                decode leg, one `EdgeReport` per traversed stream edge.
        """
        merged = self._stream_evidence(prepared, pipeline)
        end = terminal.end
        if end is None:
            terminal.end = StreamEnd(report=merged)
        elif end.report is None:
            end.report = merged
        else:
            end.report = merged.merge(end.report)

    def _pump(
        self, events: Iterator[Any], prepared: _PreparedCall, pipeline: StreamPipeline
    ) -> Iterator[ChatChunk]:
        """Relay the driver's converted chunks, enriching the terminal.

        Every chunk is yielded the moment the driver surfaces it — no
        lookahead, no buffering — except the terminal `STREAM_STOP`, which
        is held until the driver's generator is exhausted: only then has the
        driver flushed the pipeline (yielding any tail, which passes through
        here first), so only then does `pipeline.reports` carry the decode
        leg to stamp into `StreamEnd.report`. A stream that ends without a
        terminal (an abort) gets none synthesized — the codec's honesty
        stance — and a mid-stream error raises through untouched (already
        refined by the driver), after the driver flushed for accounting.

        Args:
            events: The driver's converted event stream for this call.
            prepared: The call's pre-send preamble.
            pipeline: The stream pipeline the driver is pumping.

        Yields:
            The canonical chunks in stream order, the terminal last with
            the two-leg report stamped.
        """
        terminal: ChatChunk | None = None
        delivered = 0
        try:
            for chunk in events:
                if terminal is not None:
                    raise StreamProtocolError("provider emitted content after stream termination")
                if isinstance(chunk, ChatChunk) and chunk.type == ChunkType.STREAM_STOP:
                    terminal = chunk
                else:
                    delivered += 1
                    yield chunk
            if terminal is not None:
                self._stamp_stream_report(terminal, prepared, pipeline)
                if self._conversion_policy is not None and terminal.end is not None:
                    self._conversion_policy.enforce(
                        terminal.end.report or FidelityReport(), phase="response",
                        usage=terminal.end.usage, route=prepared.route, delivered_events=delivered,
                    )
                yield terminal
        finally:
            close = getattr(events, "close", None)
            if close is not None:
                close()

    async def _apump(
        self, events: AsyncIterator[Any], prepared: _PreparedCall, pipeline: StreamPipeline
    ) -> AsyncIterator[ChatChunk]:
        """Relay converted chunks asynchronously — the `a`-twin of `_pump`.

        Args:
            events: The async driver's converted event stream.
            prepared: The call's pre-send preamble.
            pipeline: The stream pipeline the driver is pumping.

        Yields:
            The canonical chunks in stream order, the terminal last with
            the two-leg report stamped.
        """
        terminal: ChatChunk | None = None
        delivered = 0
        try:
            async for chunk in events:
                if terminal is not None:
                    raise StreamProtocolError("provider emitted content after stream termination")
                if isinstance(chunk, ChatChunk) and chunk.type == ChunkType.STREAM_STOP:
                    terminal = chunk
                else:
                    delivered += 1
                    yield chunk
            if terminal is not None:
                self._stamp_stream_report(terminal, prepared, pipeline)
                if self._conversion_policy is not None and terminal.end is not None:
                    self._conversion_policy.enforce(
                        terminal.end.report or FidelityReport(), phase="response",
                        usage=terminal.end.usage, route=prepared.route, delivered_events=delivered,
                    )
                yield terminal
        finally:
            close = getattr(events, "aclose", None)
            if close is not None:
                await close()

    @staticmethod
    def _stream_evidence(prepared: _PreparedCall, pipeline: StreamPipeline) -> FidelityReport:
        """Snapshot available findings once without mutating the request report."""
        report = deepcopy(prepared.report)
        return report.merge(FidelityReport(edges=list(pipeline.reports or ())))

    # --- The port methods ---------------------------------------------------

    def _chat_prepared(
        self,
        bound: _PreparedModel,
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
            bound: The approved execution snapshot and validation guard.
            request: The canonical chat request.
            ctx: Trusted per-call facts, snapshotted and propagated into wire
                policies without entering provider payloads. Its aware deadline
                bounds the whole call, including admission and retry waits.

        Returns:
            The uniform envelope: response, `Route` (host-stamped, carrying
            the catalog hash), merged `FidelityReport` (request leg +
            response leg), usage, and the untouched raw body.

        Raises:
            OcaiError: The refined taxonomy error when the wire attempt
                ultimately fails.
            CompositionError: If the composed stack cannot serve the call.
        """
        ctx = deepcopy(ctx)
        budget = Deadline(ctx)
        budget.remaining()
        prepared = bound.consume(request, streaming=False)
        raw = self._sync_driver.execute(
            spec=prepared.spec,
            payload=prepared.payload,
            ctx=ctx,
            budget=budget,
            request_guard=bound.guard,
            refine_error=self._refine_error,
        )
        result = self._assemble(prepared, raw)
        budget.remaining()
        return result

    async def _achat_prepared(
        self,
        bound: _PreparedModel,
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
            bound: The approved execution snapshot and validation guard.
            request: The canonical chat request.
            ctx: Trusted per-call facts, snapshotted and propagated into wire
                policies without entering provider payloads. Its aware deadline
                bounds the whole call, including admission and retry waits.

        Returns:
            The uniform envelope carrying the canonical `ChatResponse`.

        Raises:
            OcaiError: The refined taxonomy error when the wire attempt
                ultimately fails.
            CompositionError: If the composed stack cannot serve the call.
        """
        ctx = deepcopy(ctx)
        budget = Deadline(ctx)
        budget.remaining()
        prepared = bound.consume(request, streaming=False)
        raw = await self._async_driver.execute(
            spec=prepared.spec,
            payload=prepared.payload,
            ctx=ctx,
            budget=budget,
            request_guard=bound.guard,
            refine_error=self._refine_error,
        )
        result = self._assemble(prepared, raw)
        budget.remaining()
        return result

    def _stream_prepared(
        self,
        bound: _PreparedModel,
        request: ChatRequest,
        *,
        ctx: CallContext | None = None,
    ) -> ChatStream:
        """Send a streaming chat request, synchronously.

        Same request purity as `chat`: the bound `model_name` is injected
        into the encoded payload via `bind_resource` before the stream
        opens — the request never carries it — and the codec's
        `bind_stream` marks the payload for its dialect's streaming mode.
        The whole sans-io preamble (`_prepare`: resolve, gate, encode, bind)
        runs eagerly HERE, so a doomed request fails at the call site like
        `chat` does; only the wire attempt is lazy, opening on the first
        chunk pulled. The driver pumps host-decoded events through a fresh
        `StreamPipeline` (`catalog.stream_converter`, wire chunk node →
        canonical — conversion joins the graph, §4.1) and flushes it exactly
        once at end-of-stream; the facade folds the flush accounting into
        the terminal chunk's `StreamEnd.report` beside the request leg —
        honesty parity with the blocking path. Mid-stream wire errors raise
        the refined taxonomy error (`map_error`, like unary), after the
        driver flushed the pipeline for accounting.

        Args:
            bound: The approved execution snapshot and validation guard.
            request: The canonical chat request.
            ctx: Trusted per-call facts, snapshotted and propagated into wire
                policies without entering provider payloads. Its aware deadline
                bounds the whole call, including admission and retry waits.

        Returns:
            The canonical chunk stream; its terminal chunk carries
            `StreamEnd(usage, finish, report)`, exposed as `.end` after
            exhaustion.

        Raises:
            OcaiError: The refined taxonomy error when the wire attempt
                fails — raised from the iteration, where the wire is
                touched.
            CompositionError: If the composed stack cannot serve the call.
        """
        ctx = deepcopy(ctx)
        budget = Deadline(ctx)
        budget.remaining()
        prepared = bound.consume(request, streaming=True)
        pipeline = self._catalog.stream_converter(
            self._chunk_node(prepared.route.node), CANONICAL_CHAT_CHUNK
        )
        events = self._sync_driver.stream(
            spec=prepared.spec,
            payload=prepared.payload,
            ctx=ctx,
            budget=budget,
            request_guard=bound.guard,
            refine_error=self._refine_error,
            pipeline=pipeline,
            framing=prepared.framing,
        )
        return ChatStream(self._pump(events, prepared, pipeline),
                          report=lambda: self._stream_evidence(prepared, pipeline))

    async def _astream_prepared(
        self,
        bound: _PreparedModel,
        request: ChatRequest,
        *,
        ctx: CallContext | None = None,
    ) -> AsyncChatStream:
        """Send a streaming chat request, asynchronously.

        The `a`-twin of `stream`: identical eager preamble, pipeline
        construction, and terminal-report stamping (all synchronous and
        shared, per the sans-io rule) — only the physical pump goes through
        `AsyncDriver`.

        Args:
            bound: The approved execution snapshot and validation guard.
            request: The canonical chat request.
            ctx: Trusted per-call facts, snapshotted and propagated into wire
                policies without entering provider payloads. Its aware deadline
                bounds the whole call, including admission and retry waits.

        Returns:
            The async canonical chunk stream; its terminal chunk carries
            `StreamEnd(usage, finish, report)`, exposed as `.end` after
            exhaustion.

        Raises:
            OcaiError: The refined taxonomy error when the wire attempt
                fails — raised from the iteration, where the wire is
                touched.
            CompositionError: If the composed stack cannot serve the call.
        """
        ctx = deepcopy(ctx)
        budget = Deadline(ctx)
        budget.remaining()
        prepared = bound.consume(request, streaming=True)
        pipeline = self._catalog.stream_converter(
            self._chunk_node(prepared.route.node), CANONICAL_CHAT_CHUNK
        )
        events = self._async_driver.stream(
            spec=prepared.spec,
            payload=prepared.payload,
            ctx=ctx,
            budget=budget,
            request_guard=bound.guard,
            refine_error=self._refine_error,
            pipeline=pipeline,
            framing=prepared.framing,
        )
        return AsyncChatStream(self._apump(events, prepared, pipeline),
                               report=lambda: self._stream_evidence(prepared, pipeline))

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


class InterceptedChatModel:
    """A `ChatModel` wrapped in a port-tier `CallInterceptor` chain.

    What the §3.4 front door returns when `interceptors` are composed in: the
    chain is folded over the inner port's own call exactly once, at
    construction (`compose`/`acompose` from `ocai.runtime.interceptors`), and
    every `chat`/`achat` travels the onion — outermost interceptor first. The
    wrapper satisfies the `ChatModel` protocol structurally, so interceptors
    stack: an `InterceptedChatModel` can wrap another.

    `stream`/`astream` use the separate `StreamInterceptor` continuation.
    Every configured interceptor must support it or streaming fails closed
    before the inner port is invoked; unary-only governance is never bypassed.
    """

    def __init__(self, inner: ChatModel, interceptors: Sequence[CallInterceptor]) -> None:
        """Fold `interceptors` over `inner`'s unary faces.

        Args:
            inner: The port to wrap — typically a `WireChatModel`, but any
                `ChatModel` composes (local adapters included; that symmetry
                is the interceptor tier's admission test).
            interceptors: The chain, outermost first.
        """
        self._inner = inner
        self._interceptors = tuple(interceptors)
        self._handler = compose(self._interceptors, self._terminal)
        self._ahandler = acompose(self._interceptors, self._aterminal)
        stream_interceptors = [item for item in self._interceptors
                               if isinstance(item, StreamInterceptor)]
        self._stream_handler = (compose_stream(stream_interceptors, self._stream_terminal)
                                if len(stream_interceptors) == len(self._interceptors) else None)
        self._astream_handler = (acompose_stream(stream_interceptors, self._astream_terminal)
                                 if len(stream_interceptors) == len(self._interceptors) else None)

    def prepare(self, request: ChatRequest, *, streaming: bool = False) -> PreparedChatCall:
        """Retain the complete admission chain around an approved inner snapshot."""
        prepared = _prepare_port(self._inner, request, streaming)
        return prepared.wrap(lambda model: InterceptedChatModel(model, self._interceptors))

    def _stream_terminal(self, call: Call) -> SyncStream:
        return self._inner.stream(call.request, ctx=call.ctx)

    async def _astream_terminal(self, call: Call) -> AsyncStream:
        return await self._inner.astream(call.request, ctx=call.ctx)

    def _terminal(self, call: Call) -> CallResult[ChatResponse]:
        """The innermost sync handler: the wrapped port's own `chat`."""
        return self._inner.chat(call.request, ctx=call.ctx)

    async def _aterminal(self, call: Call) -> CallResult[ChatResponse]:
        """The innermost async handler: the wrapped port's own `achat`."""
        return await self._inner.achat(call.request, ctx=call.ctx)

    def chat(
        self,
        request: ChatRequest,
        *,
        ctx: CallContext | None = None,
    ) -> CallResult[ChatResponse]:
        """Send a blocking chat request down the interceptor chain.

        Args:
            request: The canonical chat request.
            ctx: The per-request governance context, visible to every
                interceptor on the way down.

        Returns:
            The `CallResult` the chain hands back — the inner port's result,
            or an interceptor's short-circuit.
        """
        return self._handler(Call(request=request, ctx=deepcopy(ctx)))

    async def achat(
        self,
        request: ChatRequest,
        *,
        ctx: CallContext | None = None,
    ) -> CallResult[ChatResponse]:
        """Send a blocking chat request down the async interceptor chain.

        Args:
            request: The canonical chat request.
            ctx: The per-request governance context.

        Returns:
            The `CallResult` the chain hands back.
        """
        return await self._ahandler(Call(request=request, ctx=deepcopy(ctx)))

    def stream(
        self,
        request: ChatRequest,
        *,
        ctx: CallContext | None = None,
    ) -> ChatStream:
        """Run eager streaming admission through every configured interceptor.

        Args:
            request: The canonical chat request.
            ctx: The per-request governance context.

        Returns:
            The inner port's canonical chunk stream.
        """
        if self._stream_handler is None:
            raise CompositionError("every interceptor must implement StreamInterceptor; "
                                   "streaming cannot bypass unary governance")
        stream = self._stream_handler(Call(request=request, ctx=deepcopy(ctx)))
        if isinstance(stream, ChatStream):
            return stream
        return ChatStream(stream, report=lambda: stream.outcome.report if stream.outcome else None)

    async def astream(
        self,
        request: ChatRequest,
        *,
        ctx: CallContext | None = None,
    ) -> AsyncChatStream:
        """Run eager async streaming admission through every interceptor.

        Args:
            request: The canonical chat request.
            ctx: The per-request governance context.

        Returns:
            The inner port's async canonical chunk stream.
        """
        if self._astream_handler is None:
            raise CompositionError("every interceptor must implement StreamInterceptor; "
                                   "streaming cannot bypass unary governance")
        stream = await self._astream_handler(Call(request=request, ctx=deepcopy(ctx)))
        if isinstance(stream, AsyncChatStream):
            return stream
        return AsyncChatStream(stream,
                               report=lambda: stream.outcome.report if stream.outcome else None)

    @property
    def details(self) -> dict[str, Any]:
        """Describe the wrapped composition.

        Returns:
            The inner port's details, unchanged — interceptors are transparent
            to diagnostics that describe the destination.
        """
        return self._inner.details


class ObservedChatModel:
    """Observe a local or remote capability outside its admission middleware.

    Invocation starts eagerly at the public call, including stream creation.
    A lazy stream finishes on exhaustion, failure or explicit close. An abandoned
    stream remains pending: callers must use its ownership contract. This wrapper
    never treats observers as enforceable admission or required durable audit.
    """

    def __init__(self, inner: ChatModel, observers: Sequence[Observer]) -> None:
        """Register authorized passive observers around the complete port chain."""
        self._inner = inner
        self._observers = tuple(observers)

    def prepare(self, request: ChatRequest, *, streaming: bool = False) -> PreparedChatCall:
        """Inspect without starting a call; observation begins when the handle executes."""
        prepared = _prepare_port(self._inner, request, streaming)
        return prepared.wrap(lambda model: ObservedChatModel(model, self._observers))

    @property
    def details(self) -> dict[str, Any]:
        """Describe the underlying target without exporting credentials."""
        return self._inner.details

    def chat(self, request: ChatRequest,
             *, ctx: CallContext | None = None) -> CallResult[ChatResponse]:
        """Observe one synchronous invocation including admission and conversion."""
        scope = Invocation(self._observers, ctx)
        try:
            result = self._inner.chat(request, ctx=scope.ctx)
        except BaseException as error:
            if isinstance(error, FidelityPolicyError):
                scope.finish(status="rejected" if error.phase == "request" else "failed",
                             error=error, usage=error.usage, report=error.report, route=error.route)
            else:
                scope.finish(status=failure_status(error), error=error)
            raise
        scope.finish(usage=result.usage, report=result.report, route=result.route)
        return result

    async def achat(self, request: ChatRequest,
                    *, ctx: CallContext | None = None) -> CallResult[ChatResponse]:
        """Observe one async invocation with the same correlation and accounting."""
        scope = Invocation(self._observers, ctx)
        try:
            result = await self._inner.achat(request, ctx=scope.ctx)
        except BaseException as error:
            if isinstance(error, FidelityPolicyError):
                scope.finish(status="rejected" if error.phase == "request" else "failed",
                             error=error, usage=error.usage, report=error.report, route=error.route)
            else:
                scope.finish(status=failure_status(error), error=error)
            raise
        scope.finish(usage=result.usage, report=result.report, route=result.route)
        return result

    def stream(self, request: ChatRequest, *, ctx: CallContext | None = None) -> ChatStream:
        """Start a logical invocation now; observe its owned lazy stream later."""
        scope = Invocation(self._observers, ctx, streaming=True)
        try:
            stream = self._inner.stream(request, ctx=scope.ctx)
        except BaseException as error:
            if isinstance(error, FidelityPolicyError):
                scope.finish(status="rejected" if error.phase == "request" else "failed",
                             error=error, usage=error.usage, report=error.report, route=error.route)
            else:
                scope.finish(status=failure_status(error), error=error)
            raise
        stream.on_termination(lambda outcome: scope.finish(
            status=(failure_status(outcome.error)
                    if outcome.status == "failed" and outcome.error else outcome.status),
            usage=outcome.usage, report=outcome.report, error=outcome.error,
        ))
        return stream

    async def astream(self, request: ChatRequest,
                      *, ctx: CallContext | None = None) -> AsyncChatStream:
        """Observe async creation and its one eventual terminal outcome."""
        scope = Invocation(self._observers, ctx, streaming=True)
        try:
            stream = await self._inner.astream(request, ctx=scope.ctx)
        except BaseException as error:
            if isinstance(error, FidelityPolicyError):
                scope.finish(status="rejected" if error.phase == "request" else "failed",
                             error=error, usage=error.usage, report=error.report, route=error.route)
            else:
                scope.finish(status=failure_status(error), error=error)
            raise
        stream.on_termination(lambda outcome: scope.finish(
            status=(failure_status(outcome.error)
                    if outcome.status == "failed" and outcome.error else outcome.status),
            usage=outcome.usage, report=outcome.report, error=outcome.error,
        ))
        return stream
