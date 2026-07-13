"""Edge definitions for `anthropic/messages` — the fragment's contents.

Turns `MessagesCodec`'s mapping functions into declarative catalog material:
graph `Edge`s with honest `EdgeContract` censuses, the chunk-shape
`StreamEdge`, and the interface's `CapabilityProfile`s. Frozen data assembled
at module load, **no import-time mutation** of shared state (rule 14); the
package `__init__` folds these tuples into the exported `CatalogFragment`.

The censuses declare the *current* implementation (the conformance harness
certifies runtime loss never exceeds them, §4.2) and are tightened in the
same change that implements a tighter mapping. The profile pair below is the
model-pattern dimension in action (§2.5): interface-wide facts on `"*"`, plus
the newest-model override where `temperature` is rejected outright.
"""

from __future__ import annotations

from typing import Any

from ocai.anthropic.messages.codec import CANONICAL_CHUNK
from ocai.anthropic.messages.codec import CANONICAL_REQUEST
from ocai.anthropic.messages.codec import CANONICAL_RESPONSE
from ocai.anthropic.messages.codec import INTERFACE
from ocai.anthropic.messages.codec import MESSAGES_CHUNK
from ocai.anthropic.messages.codec import MESSAGES_REQUEST
from ocai.anthropic.messages.codec import MESSAGES_RESPONSE
from ocai.anthropic.messages.codec import PROVIDER
from ocai.anthropic.messages.codec import MessagesCodec
from ocai.anthropic.messages.codec import MessagesStreamTransducer
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

# Provenance stamp for every node/edge this distribution registers.
# TODO: derive the version from importlib.metadata at fragment-build time.
ORIGIN = Origin(distribution="ocai-anthropic", version="0.1.0")

# The single stateless codec instance the edge functions share.
_CODEC = MessagesCodec()

# --- Contracts (the per-field disposition census, §4.2) ----------------------

# Census upper-bound decision (WU-13, replaying WU-06): a census entry bounds
# EVERY payload the edge may see, so the range-limited knobs (temperature and
# top_p — Anthropic documents a 0..1 ceiling for both, unlike OpenAI's 0..2
# temperature) declare APPROXIMATED. The runtime emits APPROXIMATED only for
# out-of-range values (passed verbatim, never clamped) and stays silent
# (EXACT) in range, which certification accepts because EXACT sits in a
# strictly lower severity band. The declared grade is honestly worse for it:
# this edge pays two APPROXIMATED slots in `loss_grade()` rather than
# advertising an exactness it cannot promise for every payload.
ENCODE_REQUEST_CONTRACT = EdgeContract(
    # No `model` row: the canonical request carries no model (WU-05a, §3.4) —
    # the wire member is injected by the facade from the bound resource via
    # `MessagesCodec.bind_resource`, below this edge.
    census={
        "messages[].role": DeclaredDisposition(Disposition.EXACT),
        # Leading system turns relocate to the top-level `system` field — a
        # declared SemanticShift, data-exact.
        "messages[system]": DeclaredDisposition(Disposition.RENAMED),
        # TODO: censused emulation lane (anthropic.mid_conv_system).
        "messages[system, mid-conversation]": DeclaredDisposition(Disposition.DROPPED),
        "messages[].parts[text]": DeclaredDisposition(Disposition.EXACT),
        # args_json string parsed back into the wire `input` object.
        "messages[].parts[tool_call]": DeclaredDisposition(Disposition.RENAMED),
        # `tool_result` blocks are native — is_error INCLUDED, the honest
        # asymmetry vs chat_completions (which drops the error flag).
        "messages[].parts[tool_result]": DeclaredDisposition(Disposition.EXACT),
        "messages[].parts[tool_result].is_error": DeclaredDisposition(Disposition.EXACT),
        # TODO: nested image/document result content is native on this wire.
        "messages[].parts[tool_result].parts[]": DeclaredDisposition(Disposition.DROPPED),
        # thinking replay w/ REQUIRED signature anchor; foreign anchors are
        # UNSUPPORTED by the graph's ref rule before this edge runs.
        "messages[].parts[reasoning]": DeclaredDisposition(Disposition.EXACT),
        # TODO: tighten to EXACT once Source-union media encode lands
        # (base64/url/file sources are all native on this wire).
        "messages[].parts[image]": DeclaredDisposition(Disposition.DROPPED),
        "messages[].parts[document]": DeclaredDisposition(Disposition.DROPPED),
        "messages[].parts[refusal]": DeclaredDisposition(Disposition.DROPPED),
        "tools": DeclaredDisposition(Disposition.RENAMED),
        "tool_choice": DeclaredDisposition(Disposition.RENAMED),
        "config.temperature": DeclaredDisposition(
            Disposition.APPROXIMATED, "range-limited (0..1): out-of-range passes verbatim"
        ),
        "config.top_p": DeclaredDisposition(
            Disposition.APPROXIMATED, "range-limited (0..1): out-of-range passes verbatim"
        ),
        "config.top_k": DeclaredDisposition(Disposition.EXACT),
        "config.max_output_tokens": DeclaredDisposition(Disposition.RENAMED),
        "config.stop_sequences": DeclaredDisposition(Disposition.RENAMED),
        "config.seed": DeclaredDisposition(Disposition.UNSUPPORTED),
        "config.frequency_penalty": DeclaredDisposition(Disposition.UNSUPPORTED),
        "config.presence_penalty": DeclaredDisposition(Disposition.UNSUPPORTED),
        "config.logprobs": DeclaredDisposition(Disposition.UNSUPPORTED),
        "config.parallel_tool_calls": DeclaredDisposition(Disposition.RENAMED),
        "config.reasoning.budget_tokens": DeclaredDisposition(Disposition.RENAMED),
        "config.reasoning.effort": DeclaredDisposition(Disposition.APPROXIMATED),
        "config.output": DeclaredDisposition(Disposition.RENAMED),
        # The wire's output_config.format carries only the schema itself.
        "config.output.name": DeclaredDisposition(Disposition.DROPPED),
        "config.output.strict": DeclaredDisposition(Disposition.DROPPED),
        # TODO: cache_hint → per-block cache_control breakpoints.
        "config.modalities": DeclaredDisposition(Disposition.DROPPED),
        "config.audio": DeclaredDisposition(Disposition.DROPPED),
        "config.cache": DeclaredDisposition(Disposition.DROPPED),
    },
    semantic_shifts=(
        SemanticShift(
            kind=ShiftKind.RELOCATION,
            path="messages[]",
            note=(
                "leading system turns relocate to the top-level `system` field; "
                "canonical tool turns thread as `role: user` wire messages"
            ),
        ),
        SemanticShift(
            kind=ShiftKind.EMULATION,
            path="config.max_output_tokens",
            note="the wire requires max_tokens; an omitted ceiling gets the injected default",
        ),
    ),
    note="canonical chat.request -> anthropic/messages",
)

DECODE_RESPONSE_CONTRACT = EdgeContract(
    census={
        "content[text]": DeclaredDisposition(Disposition.EXACT),
        # TODO: re-anchor onto PartText.annotations after span validation.
        "content[text].citations": DeclaredDisposition(Disposition.EXTENSIONS),
        "content[thinking]": DeclaredDisposition(Disposition.EXACT),
        "content[redacted_thinking]": DeclaredDisposition(Disposition.EXACT),
        # input object serialized to the canonical args_json string lane.
        "content[tool_use]": DeclaredDisposition(Disposition.RENAMED),
        "content[server_tool_use]": DeclaredDisposition(Disposition.EXACT),
        "content[*_tool_result]": DeclaredDisposition(Disposition.EXACT),
        # Deliberate provider-unique blocks ride PartOpaque, censused.
        "content[unknown]": DeclaredDisposition(Disposition.EXTENSIONS),
        "stop_reason": DeclaredDisposition(Disposition.EXACT),
        "stop_details": DeclaredDisposition(Disposition.EXACT),
        "stop_sequence": DeclaredDisposition(Disposition.EXTENSIONS),
        # cache_read_input_tokens → the canonical cached bucket;
        # cache_creation_input_tokens → the open `anthropic.cache_write`
        # consumption source (WU-13 decision, see `codec._usage`).
        "usage": DeclaredDisposition(Disposition.RENAMED),
        "id": DeclaredDisposition(Disposition.EXACT),
        "model": DeclaredDisposition(Disposition.EXACT),
        "container": DeclaredDisposition(Disposition.EXTENSIONS),
    },
    semantic_shifts=(
        SemanticShift(
            kind="anthropic.args_serialized",
            path="content[].input",
            note="tool_use.input objects serialize to the canonical args_json wire-truth lane",
        ),
    ),
    note="anthropic/messages -> canonical chat.response",
)

DECODE_CHUNK_CONTRACT = EdgeContract(
    census={
        "message_start": DeclaredDisposition(Disposition.EXACT),
        "content_block_start": DeclaredDisposition(Disposition.EXACT),
        "content_block_delta.text_delta": DeclaredDisposition(Disposition.EXACT),
        "content_block_delta.thinking_delta": DeclaredDisposition(Disposition.EXACT),
        "content_block_delta.input_json_delta": DeclaredDisposition(Disposition.EXACT),
        "content_block_delta.signature_delta": DeclaredDisposition(Disposition.EXACT),
        # TODO: DeltaAnnotation after span validation.
        "content_block_delta.citations_delta": DeclaredDisposition(Disposition.DROPPED),
        "content_block_stop": DeclaredDisposition(Disposition.EXACT),
        "message_delta.stop_reason": DeclaredDisposition(Disposition.EXACT),
        "message_delta.usage": DeclaredDisposition(Disposition.RENAMED),
        "message_stop": DeclaredDisposition(Disposition.EXACT),
        "error": DeclaredDisposition(Disposition.EXACT),
    },
    note="anthropic/messages -> canonical chat.chunk (per event)",
)

# --- Edge functions (thin, pure wrappers over the codec) ---------------------


def encode_request(request: ChatRequest) -> EdgeOutput:
    """Edge fn `canonical chat.request → anthropic/messages`.

    Args:
        request: The canonical request the planner routed to this edge.

    Returns:
        The wire request dict with this edge's report.
    """
    return _CODEC.encode_request(request)


def decode_response(payload: dict[str, Any]) -> EdgeOutput:
    """Edge fn `anthropic/messages → canonical chat.response`.

    Args:
        payload: The raw response body, already JSON-parsed.

    Returns:
        The canonical `ChatResponse` with this edge's report.
    """
    return _CODEC.decode_response(payload)


def decode_request(payload: dict[str, Any]) -> EdgeOutput:
    """Edge fn `anthropic/messages → canonical chat.request`.

    The audit-tool direction: re-converting archived wire traffic back into
    the canonical IR without any ability to make network calls (§1).

    Args:
        payload: The raw archived request body.

    Returns:
        The canonical `ChatRequest` with this edge's report.
    """
    raise NotImplementedError  # TODO: inverse mapping + census; needed by archive re-conversion.


# --- Fragment contents --------------------------------------------------------

NODES: tuple[NodeId, ...] = (
    MESSAGES_REQUEST,
    MESSAGES_RESPONSE,
    MESSAGES_CHUNK,
)

EDGES: tuple[Edge, ...] = (
    Edge(
        src=CANONICAL_REQUEST,
        dst=MESSAGES_REQUEST,
        fn=encode_request,
        contract=ENCODE_REQUEST_CONTRACT,
        origin=ORIGIN,
    ),
    Edge(
        src=MESSAGES_RESPONSE,
        dst=CANONICAL_RESPONSE,
        fn=decode_response,
        contract=DECODE_RESPONSE_CONTRACT,
        origin=ORIGIN,
    ),
    # TODO: register the decode_request audit edge once implemented.
)

TRANSDUCERS: tuple[StreamEdge, ...] = (
    StreamEdge(
        src=MESSAGES_CHUNK,
        dst=CANONICAL_CHUNK,
        factory=MessagesStreamTransducer,
        contract=DECODE_CHUNK_CONTRACT,
        origin=ORIGIN,
    ),
)

# Declared capability facts, consulted by the feature gate BEFORE payload
# conversion (§2.5). Two entries: interface-wide facts, then the
# newest-model override — support varies BELOW interface level, which is why
# the model_pattern dimension exists at all.
PROFILES: tuple[CapabilityProfile, ...] = (
    CapabilityProfile(
        provider=PROVIDER,
        interface=INTERFACE,
        model_pattern="*",
        features={
            "chat.config.temperature": Support.NATIVE,
            "chat.config.top_p": Support.NATIVE,
            "chat.config.top_k": Support.NATIVE,
            "chat.config.seed": Support.ABSENT,
            "chat.config.logprobs": Support.ABSENT,
            "chat.config.frequency_penalty": Support.ABSENT,
            "chat.config.presence_penalty": Support.ABSENT,
            "chat.config.output.json_schema": Support.NATIVE,
            "chat.config.reasoning.budget_tokens": Support.NATIVE,
            "chat.parts.image": Support.NATIVE,
            "chat.parts.document": Support.NATIVE,
            "chat.parts.audio": Support.ABSENT,
            "chat.parts.reasoning.replay": Support.NATIVE,
            "chat.tools.parallel": Support.NATIVE,
        },
    ),
    # The newest models reject `temperature` outright (a 400, not a warning):
    # strict mode refuses before conversion, annotate mode records the loss.
    # TODO: census the exact rejecting model families as they ship.
    CapabilityProfile(
        provider=PROVIDER,
        interface=INTERFACE,
        model_pattern="claude-opus-4-6*",
        features={"chat.config.temperature": Support.ABSENT},
    ),
)
