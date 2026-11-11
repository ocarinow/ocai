"""Edge definitions for `openai/chat_completions` — the fragment's contents.

This module turns the codec's mapping functions into declarative catalog
material: graph `Edge`s (each with its honest `EdgeContract` census), the
chunk-shape `StreamEdge` transducer, and the interface's `CapabilityProfile`.
Everything here is frozen data assembled once at module load — **no
import-time mutation of any shared registry** (rule 14); the package
`__init__` folds these tuples into the exported `CatalogFragment`, and an
application opts in with `Catalog.of(ocai.openai.FRAGMENT, ...)`.

The censuses below are the load-bearing honesty: the planner derives this
interface's edge weights from them, and the conformance harness certifies at
build time that runtime `FieldLoss` never exceeds the declaration — an edge
claiming lossless that drops a field cannot ship (§4.2). Census entries are
therefore declared for the *current* implementation (e.g. media parts are
`DROPPED` until their encode lands), and tightened in the same change that
implements the mapping.
"""

from __future__ import annotations

from typing import Any

from ocai.chat.types import ChatRequest
from ocai.convert.contract import DeclaredDisposition
from ocai.convert.contract import EdgeContract
from ocai.convert.graph import Edge
from ocai.convert.graph import EdgeOutput
from ocai.convert.graph import StreamEdge
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import SemanticShift
from ocai.core.fidelity import ShiftKind
from ocai.core.identity import NodeId
from ocai.core.identity import Origin
from ocai.core.profile import CapabilityProfile
from ocai.core.profile import Support
from ocai.openai.chat_completions.client import encode_response
from ocai.openai.chat_completions.client_stream import ClientStreamTransducer
from ocai.openai.chat_completions.codec import CANONICAL_CHUNK
from ocai.openai.chat_completions.codec import CANONICAL_REQUEST
from ocai.openai.chat_completions.codec import CANONICAL_RESPONSE
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_CHUNK
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_REQUEST
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_RESPONSE
from ocai.openai.chat_completions.codec import INTERFACE
from ocai.openai.chat_completions.codec import PROVIDER
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.openai.chat_completions.codec import ChatCompletionsStreamTransducer

# Provenance stamp for every node/edge this distribution registers; surfaces
# in catalog lockfiles and audit records.
# TODO: derive the version from importlib.metadata at fragment-build time.
ORIGIN = Origin(distribution="ocai-openai", version="0.1.0")

# The single stateless codec instance the edge functions share.
_CODEC = ChatCompletionsCodec()

# --- Contracts (the per-field disposition census, §4.2) ----------------------

# Census upper-bound decision (WU-06): a census entry bounds EVERY payload the
# edge may see, so range-limited knobs (temperature, top_p, the penalties)
# declare APPROXIMATED — the runtime emits APPROXIMATED only for out-of-range
# values (passed verbatim, never clamped) and stays silent (EXACT) in range,
# which certification accepts because EXACT sits in a strictly lower severity
# band. The declared grade is honestly worse for it: this edge pays four
# APPROXIMATED slots in `loss_grade()` rather than advertising an exactness
# it cannot promise for every payload.
ENCODE_REQUEST_CONTRACT = EdgeContract(
    # No `model` row: the canonical request carries no model (WU-05a, §3.4) —
    # the wire member is injected by the facade from the bound resource via
    # `ChatCompletionsCodec.bind_resource`, below this edge.
    census={
        "messages[].parts[].signature": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].parts[].opaque": DeclaredDisposition(Disposition.UNSUPPORTED),
        "anchors[]": DeclaredDisposition(Disposition.UNSUPPORTED),
        "extensions[ocai.request_unparsed_anchors]": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].parts[].annotations[].opaque": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].role": DeclaredDisposition(Disposition.EXACT),
        "messages[].parts[text]": DeclaredDisposition(Disposition.EXACT),
        "messages[].parts[tool_call]": DeclaredDisposition(Disposition.EXACT),
        # Relocated to a sibling `role: tool` wire message — a SemanticShift,
        # data-exact.
        "messages[].parts[tool_result]": DeclaredDisposition(Disposition.EXACT),
        "messages[].parts[tool_result].is_error": DeclaredDisposition(
            Disposition.DROPPED,
            "OpenAI has no error flag on `role: tool` messages; scope guard: a "
            "censused convention stays out of WU-06",
        ),
        # Nested non-text result content (images, documents) has no wire lane.
        "messages[].parts[tool_result].parts[]": DeclaredDisposition(Disposition.DROPPED),
        "messages[].parts[refusal]": DeclaredDisposition(Disposition.EXACT),
        # TODO: tighten to EXACT once Source-union media encode lands (kept
        # OUT of WU-06 by scope guard — DROPPED is the certifiable truth).
        "messages[].parts[image]": DeclaredDisposition(Disposition.DROPPED),
        "messages[].parts[audio]": DeclaredDisposition(Disposition.DROPPED),
        "messages[].parts[document]": DeclaredDisposition(Disposition.DROPPED),
        # No replay lane on this interface; /responses is the reasoning home.
        "messages[].parts[reasoning]": DeclaredDisposition(Disposition.DROPPED),
        "tools": DeclaredDisposition(Disposition.EXACT),
        "tools[]": DeclaredDisposition(
            Disposition.UNSUPPORTED, "server or unknown intent requires a qualified mapping"
        ),
        "tool_choice": DeclaredDisposition(Disposition.EXACT),
        "config.temperature": DeclaredDisposition(
            Disposition.APPROXIMATED, "range-limited (0..2): out-of-range passes verbatim"
        ),
        "config.top_p": DeclaredDisposition(
            Disposition.APPROXIMATED, "range-limited (0..1): out-of-range passes verbatim"
        ),
        "config.max_output_tokens": DeclaredDisposition(Disposition.RENAMED),
        "config.stop_sequences": DeclaredDisposition(Disposition.RENAMED),
        "config.seed": DeclaredDisposition(Disposition.EXACT),
        "config.frequency_penalty": DeclaredDisposition(
            Disposition.APPROXIMATED, "range-limited (-2..2): out-of-range passes verbatim"
        ),
        "config.presence_penalty": DeclaredDisposition(
            Disposition.APPROXIMATED, "range-limited (-2..2): out-of-range passes verbatim"
        ),
        "config.parallel_tool_calls": DeclaredDisposition(Disposition.EXACT),
        "config.top_k": DeclaredDisposition(Disposition.UNSUPPORTED),
        "config.logprobs": DeclaredDisposition(Disposition.EXACT),
        "config.reasoning.effort": DeclaredDisposition(Disposition.RENAMED),
        "config.reasoning.budget_tokens": DeclaredDisposition(Disposition.UNSUPPORTED),
        "config.output": DeclaredDisposition(Disposition.RENAMED),
        # TODO: implement modalities/audio/cache encode and tighten.
        "config.modalities": DeclaredDisposition(Disposition.DROPPED),
        "config.audio": DeclaredDisposition(Disposition.DROPPED),
        "config.cache": DeclaredDisposition(Disposition.DROPPED),
        # The §2.4 scoped honesty rule: a ProviderRef leaving its validity
        # scope (interface-scoped elsewhere-minted anchors; any foreign
        # provider's refs) is UNSUPPORTED-and-reported, never silent.
        # Provider-scoped refs crossing OpenAI sibling interfaces pass
        # unreported by the same rule.
        "messages[].parts[].anchor": DeclaredDisposition(
            Disposition.UNSUPPORTED, "only refs valid on openai/chat_completions cross (§2.4)"
        ),
        "messages[].parts[].source": DeclaredDisposition(
            Disposition.UNSUPPORTED,
            "a SourceRef file handle outside its validity scope is reported (§2.4)",
        ),
        # TODO: re-expand this interface's own censused extension keys and
        # tighten; today the whole bag has no encode lane, honestly DROPPED.
        "extensions[]": DeclaredDisposition(
            Disposition.DROPPED, "request extensions have no chat_completions encode lane yet"
        ),
    },
    semantic_shifts=(
        SemanticShift(
            kind=ShiftKind.RELOCATION,
            path="messages[].parts[]",
            note="tool results relocate to sibling `role: tool` wire messages",
        ),
    ),
    note="canonical chat.request -> openai/chat_completions",
)

DECODE_RESPONSE_CONTRACT = EdgeContract(
    census={
        "response_info": DeclaredDisposition(Disposition.EXTENSIONS),
        "choices[0].message.content": DeclaredDisposition(Disposition.EXACT),
        "choices[0].message.tool_calls[]": DeclaredDisposition(Disposition.EXACT),
        "choices[0].message.refusal": DeclaredDisposition(Disposition.EXACT),
        # TODO: re-anchor to PartText.annotations after span validation.
        "choices[0].message.annotations": DeclaredDisposition(Disposition.EXTENSIONS),
        # TODO: decode to PartAudio + ProviderRef audio id anchor.
        "choices[0].message.audio": DeclaredDisposition(Disposition.EXTENSIONS),
        "choices[0].message.function_call": DeclaredDisposition(Disposition.EXTENSIONS),
        "choices[0].finish_reason": DeclaredDisposition(Disposition.EXACT),
        "choices[0].logprobs": DeclaredDisposition(Disposition.EXTENSIONS),
        # Single message forever (§3.1): extras preserved, loss reported.
        "choices[1:]": DeclaredDisposition(Disposition.EXTENSIONS),
        "usage": DeclaredDisposition(Disposition.RENAMED),
        "id": DeclaredDisposition(Disposition.EXACT),
        "model": DeclaredDisposition(Disposition.EXACT),
        # Unix seconds -> the typed `info.created` UTC timestamp: an exact,
        # reversible rename, recorded here rather than re-reported per call.
        "created": DeclaredDisposition(Disposition.RENAMED),
        "system_fingerprint": DeclaredDisposition(Disposition.EXTENSIONS),
        "service_tier": DeclaredDisposition(Disposition.EXTENSIONS),
    },
    note="openai/chat_completions -> canonical chat.response",
)

# The audit direction (WU-15): a recorded chat_completions request decodes
# back into the canonical IR. One deliberate asymmetry vs the encode census:
# the wire `model` member is routing data (§3.4 — the canonical request never
# carries a model), so its echo rides extensions['openai.model'], recoverable
# for the audit trail; re-encoding anywhere binds a fresh resource at the
# front door. The RENAMED rows document the exact knob inverses and produce
# no per-call records.
DECODE_REQUEST_CONTRACT = EdgeContract(
    census={
        "unmapped": DeclaredDisposition(Disposition.EXTENSIONS),
        "n": DeclaredDisposition(Disposition.UNSUPPORTED),
        "future_option": DeclaredDisposition(Disposition.EXTENSIONS),
        "model": DeclaredDisposition(
            Disposition.EXTENSIONS,
            "routing data, not canonical content; echo preserved in "
            "extensions['openai.model'] (§3.4)",
        ),
        # TODO: decode image_url/input_audio/file content items onto the
        # Source union and tighten to EXACT.
        "messages[].content[]": DeclaredDisposition(
            Disposition.EXTENSIONS, "non-text array content items ride PartOpaque"
        ),
        "tools[]": DeclaredDisposition(
            Disposition.EXTENSIONS, "non-function tool entries ride extensions['openai.tools']"
        ),
        "tool_choice": DeclaredDisposition(
            Disposition.EXTENSIONS, "inexpressible shapes ride extensions['openai.tool_choice']"
        ),
        "max_completion_tokens": DeclaredDisposition(Disposition.RENAMED),
        "max_tokens": DeclaredDisposition(Disposition.RENAMED, "legacy alias, same rename"),
        "stop": DeclaredDisposition(Disposition.RENAMED),
        "reasoning_effort": DeclaredDisposition(Disposition.RENAMED),
        "response_format": DeclaredDisposition(
            Disposition.EXTENSIONS,
            "renames to config.output; unrecognized selectors ride extensions",
        ),
    },
    semantic_shifts=(
        SemanticShift(
            kind=ShiftKind.RELOCATION,
            path="messages[]",
            note="sibling `role: tool` wire messages re-thread as canonical tool turns",
        ),
    ),
    note="openai/chat_completions -> canonical chat.request (audit direction)",
)

DECODE_CHUNK_CONTRACT = EdgeContract(
    census={
        "id": DeclaredDisposition(Disposition.EXACT),
        "model": DeclaredDisposition(Disposition.EXACT),
        "created": DeclaredDisposition(Disposition.RENAMED),
        "response_info": DeclaredDisposition(Disposition.EXTENSIONS),
        "choices[0].delta.content": DeclaredDisposition(Disposition.EXACT),
        "choices[0].delta.tool_calls": DeclaredDisposition(Disposition.EXACT),
        "choices[0].delta.refusal": DeclaredDisposition(Disposition.EXACT),
        "choices[0].delta.role": DeclaredDisposition(Disposition.EXACT),
        "choices[0].finish_reason": DeclaredDisposition(Disposition.EXACT),
        "usage": DeclaredDisposition(Disposition.RENAMED),
        # TODO: surface streamed logprobs/obfuscation via censused extensions.
        "choices[0].logprobs": DeclaredDisposition(Disposition.DROPPED),
        # Single-message IR (§3.1): n>1 fails admission; a stream that
        # interleaves foreign choices anyway has them dropped per frame with
        # a reported FieldLoss (WU-10 stance: drop-with-report, recoverable
        # verbatim from raw_event — a stream has no coherent extensions home
        # for interleaved foreign deltas, unlike the unary edge's bag).
        "choices[1:]": DeclaredDisposition(Disposition.DROPPED),
    },
    note="openai/chat_completions -> canonical chat.chunk (per event)",
)

ENCODE_RESPONSE_CONTRACT = EdgeContract(
    census={
        "message.role": DeclaredDisposition(Disposition.UNSUPPORTED),
        "message.parts[]": DeclaredDisposition(Disposition.UNSUPPORTED),
        "message.parts[].anchor": DeclaredDisposition(Disposition.UNSUPPORTED),
        "message.parts[].id": DeclaredDisposition(Disposition.DROPPED),
        "message.parts[].cache_hint": DeclaredDisposition(Disposition.DROPPED),
        "message.parts[].annotations": DeclaredDisposition(Disposition.DROPPED),
        "message.parts[].extensions": DeclaredDisposition(Disposition.DROPPED),
        "message.parts[].status": DeclaredDisposition(Disposition.UNSUPPORTED),
        "message.parts[].executed_by": DeclaredDisposition(Disposition.UNSUPPORTED),
        "message.extensions": DeclaredDisposition(Disposition.DROPPED),
        "response.extensions": DeclaredDisposition(Disposition.DROPPED),
        "finish.reason": DeclaredDisposition(Disposition.UNSUPPORTED),
        "finish.native": DeclaredDisposition(Disposition.RENAMED),
        "finish.detail": DeclaredDisposition(Disposition.DROPPED),
        "finish.extensions": DeclaredDisposition(Disposition.DROPPED),
        "usage.consumptions[]": DeclaredDisposition(Disposition.UNSUPPORTED),
        "usage.extensions": DeclaredDisposition(Disposition.DROPPED),
        "info.id": DeclaredDisposition(Disposition.UNSUPPORTED),
        "info.created": DeclaredDisposition(Disposition.UNSUPPORTED),
        "info.extensions": DeclaredDisposition(Disposition.DROPPED),
    },
    semantic_shifts=(
        SemanticShift(
            kind="relocation",
            path="message.parts",
            note="ordered parts grouped into client message lanes",
        ),
    ),
    note="canonical response to client semantics; gateway binds serving metadata",
)


ENCODE_CHUNK_CONTRACT = EdgeContract(
    census={
        "chunk.info": DeclaredDisposition(Disposition.UNSUPPORTED),
        **ENCODE_RESPONSE_CONTRACT.census,
        "chunk.extensions": DeclaredDisposition(Disposition.UNSUPPORTED),
        "chunk.type": DeclaredDisposition(Disposition.UNSUPPORTED),
        "chunk.delta": DeclaredDisposition(Disposition.UNSUPPORTED),
        "termination": DeclaredDisposition(Disposition.UNSUPPORTED),
    },
    semantic_shifts=ENCODE_RESPONSE_CONTRACT.semantic_shifts,
    note="canonical chunks to client JSON events; gateway owns metadata and framing",
)


# --- Edge functions (thin, pure wrappers over the codec) ---------------------


def encode_request(request: ChatRequest) -> EdgeOutput:
    """Edge fn `canonical chat.request → openai/chat_completions`.

    Args:
        request: The canonical request the planner routed to this edge.

    Returns:
        The wire request dict with this edge's report.
    """
    return _CODEC.encode_request(request)


def decode_response(payload: dict[str, Any]) -> EdgeOutput:
    """Edge fn `openai/chat_completions → canonical chat.response`.

    Args:
        payload: The raw response body, already JSON-parsed.

    Returns:
        The canonical `ChatResponse` with this edge's report.
    """
    return _CODEC.decode_response(payload)


def decode_request(payload: dict[str, Any]) -> EdgeOutput:
    """Edge fn `openai/chat_completions → canonical chat.request`.

    The audit-tool direction: re-converting archived wire traffic back into
    the canonical IR without any ability to make network calls (§1), and the
    first hop of every cross-provider request conversion (WU-15).

    Args:
        payload: The raw archived request body.

    Returns:
        The canonical `ChatRequest` with this edge's report.
    """
    return _CODEC.decode_request(payload)


# --- Fragment contents --------------------------------------------------------

NODES: tuple[NodeId, ...] = (
    CHAT_COMPLETIONS_REQUEST,
    CHAT_COMPLETIONS_RESPONSE,
    CHAT_COMPLETIONS_CHUNK,
)

EDGES: tuple[Edge, ...] = (
    Edge(
        src=CANONICAL_RESPONSE,
        dst=CHAT_COMPLETIONS_RESPONSE,
        fn=encode_response,
        contract=ENCODE_RESPONSE_CONTRACT,
        origin=ORIGIN,
    ),
    Edge(
        src=CANONICAL_REQUEST,
        dst=CHAT_COMPLETIONS_REQUEST,
        fn=encode_request,
        contract=ENCODE_REQUEST_CONTRACT,
        origin=ORIGIN,
    ),
    Edge(
        src=CHAT_COMPLETIONS_RESPONSE,
        dst=CANONICAL_RESPONSE,
        fn=decode_response,
        contract=DECODE_RESPONSE_CONTRACT,
        origin=ORIGIN,
    ),
    Edge(
        src=CHAT_COMPLETIONS_REQUEST,
        dst=CANONICAL_REQUEST,
        fn=decode_request,
        contract=DECODE_REQUEST_CONTRACT,
        origin=ORIGIN,
    ),
)

TRANSDUCERS: tuple[StreamEdge, ...] = (
    StreamEdge(
        src=CANONICAL_CHUNK,
        dst=CHAT_COMPLETIONS_CHUNK,
        factory=ClientStreamTransducer,
        contract=ENCODE_CHUNK_CONTRACT,
        origin=ORIGIN,
    ),
    StreamEdge(
        src=CHAT_COMPLETIONS_CHUNK,
        dst=CANONICAL_CHUNK,
        factory=ChatCompletionsStreamTransducer,
        contract=DECODE_CHUNK_CONTRACT,
        origin=ORIGIN,
    ),
)

# Declared capability facts, consulted by the feature gate BEFORE payload
# conversion (§2.5). Keys are namespaced open data, not a frozen taxonomy.
#
# The reasoning families (the `o*` series and `gpt-5*`) reject the classic
# sampler knobs outright — sending `temperature`/`top_p` is a 400, not a
# default — so they are declared plain ABSENT below interface level, while
# `reasoning.effort` is the families' native dial. fnmatch has no
# alternation, so the two family patterns share one fact sheet. A specific
# sheet declares only its EXCEPTIONS: everything it is silent about layers
# down to the `"*"` sheet (first declaration wins, undeclared is NATIVE).
_REASONING_MODEL_FEATURES: dict[str, Support] = {
    "chat.config.temperature": Support.ABSENT,
    "chat.config.top_p": Support.ABSENT,
    "chat.config.reasoning.effort": Support.NATIVE,
}

PROFILES: tuple[CapabilityProfile, ...] = (
    CapabilityProfile(
        provider=PROVIDER,
        interface=INTERFACE,
        model_pattern="*",
        features={
            "chat.config.temperature": Support.NATIVE,
            "chat.config.top_p": Support.NATIVE,
            "chat.config.top_k": Support.ABSENT,
            "chat.config.seed": Support.NATIVE,
            "chat.config.logprobs": Support.NATIVE,
            "chat.config.frequency_penalty": Support.NATIVE,
            "chat.config.presence_penalty": Support.NATIVE,
            "chat.config.output.json_schema": Support.NATIVE,
            "chat.parts.image": Support.NATIVE,
            "chat.parts.audio": Support.NATIVE,
            "chat.parts.reasoning.replay": Support.ABSENT,
            "chat.tools.parallel": Support.NATIVE,
        },
    ),
    CapabilityProfile(
        provider=PROVIDER,
        interface=INTERFACE,
        model_pattern="o*",
        features=dict(_REASONING_MODEL_FEATURES),
    ),
    CapabilityProfile(
        provider=PROVIDER,
        interface=INTERFACE,
        model_pattern="gpt-5*",
        features=dict(_REASONING_MODEL_FEATURES),
    ),
)
