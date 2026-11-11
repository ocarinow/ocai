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
        "anchors[]": DeclaredDisposition(Disposition.UNSUPPORTED),
        "extensions[ocai.request_unparsed_anchors]": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].parts[].extensions": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].parts[].annotations[]": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].parts[].annotations[].opaque": DeclaredDisposition(Disposition.UNSUPPORTED),
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
        "tools[]": DeclaredDisposition(
            Disposition.UNSUPPORTED, "server or unknown intent requires a qualified mapping"
        ),
        "tools[].extensions": DeclaredDisposition(Disposition.UNSUPPORTED),
        "tools[].user_location": DeclaredDisposition(Disposition.UNSUPPORTED),
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
        # The §2.4 scoped honesty rule: a ProviderRef leaving its validity
        # scope (interface-scoped elsewhere-minted anchors; any foreign
        # provider's refs) is UNSUPPORTED-and-reported, never silent.
        # Provider-scoped refs crossing Anthropic sibling interfaces pass
        # unreported by the same rule.
        "messages[].parts[].anchor": DeclaredDisposition(
            Disposition.UNSUPPORTED, "only refs valid on anthropic/messages cross (§2.4)"
        ),
        "messages[].parts[].source": DeclaredDisposition(
            Disposition.UNSUPPORTED,
            "a SourceRef file handle outside its validity scope is reported (§2.4)",
        ),
        # Foreign thinking anchors refuse replay (see codec._encode_reasoning).
        "messages[].parts[].text": DeclaredDisposition(Disposition.DROPPED),
        "messages[].parts[].opaque": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].parts[].signature": DeclaredDisposition(
            Disposition.UNSUPPORTED, "thinking replay requires this interface's anchor (§2.4)"
        ),
        # TODO: re-expand this interface's own censused extension keys and
        # tighten; today the whole bag has no encode lane, honestly DROPPED.
        "extensions[]": DeclaredDisposition(
            Disposition.DROPPED, "request extensions have no Messages encode lane yet"
        ),
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
        "content[].citations[]": DeclaredDisposition(Disposition.EXTENSIONS),
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
        "usage.server_tool_use": DeclaredDisposition(Disposition.EXTENSIONS),
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

# The audit direction (WU-15): a recorded Messages request decodes back into
# the canonical IR — the dialect's signature moves run backwards, declared:
# `system` un-hoists to a leading canonical system message, `role: user` wire
# messages carrying tool_result blocks re-thread as canonical tool turns, and
# `tool_use.input` serializes to the canonical args_json wire-truth lane. One
# deliberate asymmetry vs the encode census: the wire `model` member is
# routing data (§3.4 — the canonical request never carries a model), so its
# echo rides extensions['anthropic.model'], recoverable for the audit trail;
# re-encoding anywhere binds a fresh resource at the front door. The RENAMED
# rows document the exact knob inverses and produce no per-call records.
DECODE_REQUEST_CONTRACT = EdgeContract(
    census={
        "model": DeclaredDisposition(
            Disposition.EXTENSIONS,
            "routing data, not canonical content; echo preserved in "
            "extensions['anthropic.model'] (§3.4)",
        ),
        "system[]": DeclaredDisposition(
            Disposition.EXTENSIONS, "non-text system blocks ride PartOpaque"
        ),
        # TODO: decode image/document blocks onto the Source union and
        # tighten to EXACT.
        "messages[].content[]": DeclaredDisposition(
            Disposition.EXTENSIONS, "unrecognized block types ride PartOpaque"
        ),
        "messages[].content[].content[]": DeclaredDisposition(
            Disposition.EXTENSIONS, "non-text nested tool_result content rides PartOpaque"
        ),
        "tools[]": DeclaredDisposition(
            Disposition.EXTENSIONS, "unqualified server-tool entries retain native evidence"
        ),
        "tools[].max_uses": DeclaredDisposition(Disposition.EXTENSIONS),
        "messages[].content[].citations[]": DeclaredDisposition(Disposition.EXTENSIONS),
        "tool_choice": DeclaredDisposition(
            Disposition.EXTENSIONS,
            "inexpressible shapes ride extensions['anthropic.tool_choice']",
        ),
        "thinking": DeclaredDisposition(
            Disposition.EXTENSIONS,
            "renames to config.reasoning.budget_tokens; non-enabled shapes ride extensions",
        ),
        "output_config": DeclaredDisposition(
            Disposition.EXTENSIONS,
            "renames to config.output; unrecognized shapes ride extensions",
        ),
        "max_tokens": DeclaredDisposition(Disposition.RENAMED),
        "stop_sequences": DeclaredDisposition(Disposition.RENAMED),
        "tools": DeclaredDisposition(
            Disposition.RENAMED, "input_schema is the rename of the canonical parameters"
        ),
    },
    semantic_shifts=(
        SemanticShift(
            kind=ShiftKind.RELOCATION,
            path="system",
            note="top-level `system` field un-hoists to a leading canonical system message",
        ),
        SemanticShift(
            kind=ShiftKind.RELOCATION,
            path="messages[]",
            note=(
                "`role: user` wire messages carrying tool_result blocks "
                "re-thread as canonical tool turns"
            ),
        ),
        SemanticShift(
            kind="anthropic.args_serialized",
            path="messages[].content[].input",
            note="tool_use.input objects serialize to the canonical args_json wire-truth lane",
        ),
    ),
    note="anthropic/messages -> canonical chat.request (audit direction)",
)

DECODE_CHUNK_CONTRACT = EdgeContract(
    census={
        "message_start": DeclaredDisposition(Disposition.EXACT),
        # The opening snapshot's running totals map onto the dimensional
        # Consumption model (cumulative USAGE chunk), same rename as unary.
        "message_start.usage": DeclaredDisposition(Disposition.RENAMED),
        "message_start.usage.server_tool_use": DeclaredDisposition(Disposition.EXTENSIONS),
        "message_delta.usage.server_tool_use": DeclaredDisposition(Disposition.EXTENSIONS),
        "content[].citations[]": DeclaredDisposition(Disposition.EXTENSIONS),
        "content_block_start": DeclaredDisposition(Disposition.EXACT),
        # Start-block decode is total: unknown block types ride PartOpaque
        # and citations on a start block bank pending span validation —
        # the same paths the unary decoder reports (per event).
        "content[]": DeclaredDisposition(
            Disposition.EXTENSIONS, "unknown start-block types ride PartOpaque"
        ),
        "content[].citations": DeclaredDisposition(
            Disposition.EXTENSIONS, "citations ride raw/extensions pending span validation"
        ),
        "content_block_delta.text_delta": DeclaredDisposition(Disposition.EXACT),
        "content_block_delta.thinking_delta": DeclaredDisposition(Disposition.EXACT),
        "content_block_delta.input_json_delta": DeclaredDisposition(Disposition.EXTENSIONS),
        "content_block_delta.signature_delta": DeclaredDisposition(Disposition.EXACT),
        "content_block_delta.citations_delta": DeclaredDisposition(Disposition.EXTENSIONS),
        "content_block_stop": DeclaredDisposition(Disposition.EXACT),
        "message_delta.stop_reason": DeclaredDisposition(Disposition.EXACT),
        # The matched stop sequence rides the FINISH chunk's censused
        # `anthropic.stop_sequence` extension, mirroring the unary edge.
        "message_delta.stop_sequence": DeclaredDisposition(Disposition.EXTENSIONS),
        "message_delta.usage": DeclaredDisposition(Disposition.RENAMED),
        "message_stop": DeclaredDisposition(Disposition.EXACT),
        "ping": DeclaredDisposition(Disposition.EXACT),
        # Mid-stream error events decode to the wire-shaped ErrorInfo:
        # canonical taxonomy code + verbatim native payload + retryability.
        "error": DeclaredDisposition(Disposition.EXACT),
    },
    semantic_shifts=(
        SemanticShift(
            kind="anthropic.search_input_buffered",
            path="content_block_start",
            note="search input is emitted as one complete part at block stop",
        ),
    ),
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
    Edge(
        src=MESSAGES_REQUEST,
        dst=CANONICAL_REQUEST,
        fn=decode_request,
        contract=DECODE_REQUEST_CONTRACT,
        origin=ORIGIN,
    ),
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
    # Census: the shipped rejecting families are the opus-4-6 through
    # opus-4-8 lines, covered by one character-class pattern (extend the
    # class as new rejecting families ship). `temperature` is a plain
    # ABSENT; `top_p` stays NATIVE via the `"*"` sheet — the documented
    # temperature/top_p mutual exclusion on older models is a cross-knob
    # constraint the per-feature gate deliberately does not model (top_p
    # alone is accepted, so declaring it ABSENT would refuse valid
    # requests; the wire stays authoritative for the pairing rule).
    CapabilityProfile(
        provider=PROVIDER,
        interface=INTERFACE,
        model_pattern="claude-opus-4-[678]*",
        features={"chat.config.temperature": Support.ABSENT},
    ),
)
