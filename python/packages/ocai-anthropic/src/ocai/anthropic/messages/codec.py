"""The `anthropic/messages` interface codec — identity + payload mapping.

The meeting point of the interface's three concerns:

- **Identity** — the three `NodeId`s (`MESSAGES_REQUEST` /
  `MESSAGES_RESPONSE` / `MESSAGES_CHUNK`) naming this interface's shapes in
  every `Catalog`, `Route`, and `EdgeReport`. The tag (`2023-06`) is an opaque
  dated revision, distinct from (though contemporaneous with) the
  `anthropic-version` wire header — the interface tag names conversion logic;
  the header is a wire artifact the hosting traits carry.
- **Mapping** — `MessagesCodec.encode_request` / `decode_response` /
  `decode_event`, wrapped into graph `Edge`s by
  `ocai.anthropic.messages.edges`. Every mapping returns an `EdgeOutput` with
  an `EdgeReport`; nothing is silently dropped (rule 5). The signature moves
  of this dialect are handled honestly: system prompts *relocate* to the
  top-level `system` field (a `SemanticShift`, not a loss), thinking blocks
  carry `REQUIRED`-replay signature anchors (dropping one is breakage, §2.4),
  and `tool_use.input` objects are serialized to the canonical `args_json`
  wire-truth lane.
- **Wire hygiene** — `map_error` (the uniform `error.type` envelope) and
  `native_path`. Hosting stays a separate axis: the same codec runs
  first-party, on Vertex, or on Bedrock; the traits declare the
  `anthropic-version` header / `anthropic_version` body field a host injects.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any
from typing import TypeIs

from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatConfig
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import ChunkType
from ocai.chat.types import Consumption
from ocai.chat.types import Delta
from ocai.chat.types import DeltaReasoning
from ocai.chat.types import DeltaSignature
from ocai.chat.types import DeltaText
from ocai.chat.types import DeltaToolArgs
from ocai.chat.types import ErrorInfo
from ocai.chat.types import FinishInfo
from ocai.chat.types import Message
from ocai.chat.types import OutputFormat
from ocai.chat.types import Part
from ocai.chat.types import PartOpaque
from ocai.chat.types import PartReasoning
from ocai.chat.types import PartServerToolCall
from ocai.chat.types import PartServerToolResult
from ocai.chat.types import PartText
from ocai.chat.types import PartToolCall
from ocai.chat.types import PartToolResult
from ocai.chat.types import ReasoningConfig
from ocai.chat.types import RefusalDetail
from ocai.chat.types import ResponseInfo
from ocai.chat.types import StreamEnd
from ocai.chat.types import Tool
from ocai.chat.types import ToolChoice
from ocai.chat.types import Usage
from ocai.convert.graph import EdgeOutput
from ocai.core.errors import AuthError
from ocai.core.errors import OcaiError
from ocai.core.errors import RateLimitError
from ocai.core.errors import TransientError
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import EdgeReport
from ocai.core.fidelity import FieldLoss
from ocai.core.fidelity import SemanticShift
from ocai.core.fidelity import ShiftKind
from ocai.core.identity import CHAT_CHUNK
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import CHAT_RESPONSE
from ocai.core.identity import NodeId
from ocai.core.identity import Status
from ocai.core.identity import canonical_node
from ocai.core.jsonschema import JsonSchema
from ocai.core.jsonschema import decode_schema
from ocai.core.refs import ProviderRef
from ocai.core.refs import RefScope
from ocai.core.refs import Replay
from ocai.core.sources import SourceRef
from ocai.core.traits import DialectTraits

# Interface coordinates. `TAG` is an opaque dated revision token, ordered by
# `released`, never parsed.
PROVIDER = "anthropic"
INTERFACE = "messages"
TAG = "2023-06"
_RELEASED = date(2023, 6, 1)

# First-party origin and endpoint; hosting composes these below the graph.
ANTHROPIC_BASE_URL = "https://api.anthropic.com"
MESSAGES_PATH = "/v1/messages"

# The required first-party Messages API version header value (a wire
# artifact carried by the hosting traits — NOT the interface tag).
ANTHROPIC_VERSION = "2023-06-01"

# The `anthropic_version` BODY value cloud hosts (Vertex) require in place of
# the first-party header. Distinct from the header value above.
# TODO: confirm/parameterize per cloud host as more cloud targets land.
ANTHROPIC_VERTEX_VERSION = "vertex-2023-10-16"

# The Messages API requires max_tokens; when the canonical config omits it the
# encoder injects this default and reports the shift.
# TODO: revisit — a profile-driven per-model default beats one constant.
DEFAULT_MAX_TOKENS = 1024

# The interface's three graph nodes — one per message shape.
MESSAGES_REQUEST = NodeId(
    provider=PROVIDER,
    interface=INTERFACE,
    tag=TAG,
    shape=CHAT_REQUEST,
    released=_RELEASED,
    status=Status.STABLE,
)
MESSAGES_RESPONSE = NodeId(
    provider=PROVIDER,
    interface=INTERFACE,
    tag=TAG,
    shape=CHAT_RESPONSE,
    released=_RELEASED,
    status=Status.STABLE,
)
MESSAGES_CHUNK = NodeId(
    provider=PROVIDER,
    interface=INTERFACE,
    tag=TAG,
    shape=CHAT_CHUNK,
    released=_RELEASED,
    status=Status.STABLE,
)

# The canonical endpoints this interface's edges connect to.
CANONICAL_REQUEST = canonical_node(CHAT_REQUEST)
CANONICAL_RESPONSE = canonical_node(CHAT_RESPONSE)
CANONICAL_CHUNK = canonical_node(CHAT_CHUNK)

# Anthropic error `type` → neutral taxonomy. The body's `error.type` is the
# authoritative classifier (the envelope is uniform across endpoints).
_ERROR_TYPES: dict[str, type[OcaiError]] = {
    "rate_limit_error": RateLimitError,
    "overloaded_error": TransientError,
    "api_error": TransientError,
    "authentication_error": AuthError,
    "permission_error": AuthError,
}

# Taxonomy class → the open canonical `ErrorInfo.code` for the mid-stream
# `error` event (rule 8 on the streaming path): the SSE stream is HTTP 200,
# so the two-layer status/body mapping never runs — the codec maps the
# in-band envelope through the SAME `_ERROR_TYPES` taxonomy and renders the
# wire-shaped `ErrorInfo` (code + verbatim native payload + retryability).
_ERROR_CODES: dict[type[OcaiError], str] = {
    RateLimitError: "rate_limit",
    TransientError: "transient",
    AuthError: "auth",
}


def _is_obj(value: object) -> TypeIs[dict[str, Any]]:
    """Narrow a wire JSON value to an object (a `dict`).

    JSON objects always carry string keys, so the `dict[str, Any]` narrowing
    is exact for anything `json.loads` produced; the values stay `Any`
    because the wire is inherently dynamic (rule 6: decode never trusts a
    shape it has not checked).

    Args:
        value: The wire value to check.

    Returns:
        Whether `value` is a JSON object.
    """
    return isinstance(value, dict)


def _is_list(value: object) -> TypeIs[list[Any]]:
    """Narrow a wire JSON value to an array (a `list`).

    Args:
        value: The wire value to check.

    Returns:
        Whether `value` is a JSON array.
    """
    return isinstance(value, list)


def _as_list(value: object) -> list[Any]:
    """Return a wire JSON value as an array, or an empty array when it is not one.

    The tolerant-reader loop helper: a missing, null, or mis-typed array
    member iterates as empty rather than raising (rule 6).

    Args:
        value: The wire value to coerce.

    Returns:
        The array itself, or an empty list.
    """
    return value if _is_list(value) else []


def _stream_error(err: dict[str, Any]) -> ErrorInfo:
    """Map a mid-stream `error` event payload onto the wire-shaped `ErrorInfo`.

    The streaming face of `map_error` (rule 8): `error.type` classifies
    through the same `_ERROR_TYPES` taxonomy, the canonical code comes from
    the mapped class (`TransientError` descendants are retryable, `AuthError`
    is not), and the provider's error object rides `native` verbatim — so a
    recorded stream replays identically to a live one. An unrecognized type
    maps to the open `"unknown"` code with retryability unclaimed, never a
    raise (rule 6).

    Args:
        err: The wire `error` member of the event (`{"type", "message"}`).

    Returns:
        The wire-shaped mid-stream error record.
    """
    cls = _ERROR_TYPES.get(err.get("type") or "")
    if cls is None:
        return ErrorInfo(code="unknown", native=err)
    return ErrorInfo(
        code=_ERROR_CODES[cls],
        native=err,
        retryable=issubclass(cls, TransientError),
    )

# Wire `stop_reason` → canonical open `FinishInfo.reason` code. Unknown wire
# values decode to `"unknown"` with the verbatim value in `native` (rule 6).
_STOP_REASONS = {
    "end_turn": "complete",
    "max_tokens": "max_tokens",
    "stop_sequence": "stop_sequence",
    "tool_use": "tool_call",
    "pause_turn": "paused",
    "refusal": "refusal",
}

# Wire role ↔ canonical role, normalized exactly once at this boundary.
_ROLE_TO_CANONICAL = {"assistant": "model"}
_ROLE_FROM_CANONICAL = {"model": "assistant"}

# Response envelope keys the decoder maps explicitly; every other key sweeps
# into namespaced `extensions` (tolerant reader, rule 6).
_KNOWN_RESPONSE_KEYS = frozenset(
    {
        "id",
        "type",
        "role",
        "model",
        "content",
        "stop_reason",
        "stop_sequence",
        "stop_details",
        "usage",
    }
)

# Anthropic's documented inclusive ranges for the range-limited sampling
# knobs (https://platform.claude.com/docs/en/api/messages — note the 0..1
# temperature ceiling, unlike OpenAI's 0..2). Out-of-range values pass
# VERBATIM with an APPROXIMATED FieldLoss — never rescaled, never clamped,
# never silent (§3.1 honesty rule).
_KNOB_RANGES: dict[str, tuple[float, float]] = {
    "temperature": (0.0, 1.0),
    "top_p": (0.0, 1.0),
}

# Request envelope keys `decode_request` maps explicitly (the audit
# direction); every other key sweeps into namespaced `extensions` (rule 6).
_KNOWN_REQUEST_KEYS = frozenset(
    {
        "model",
        "messages",
        "system",
        "max_tokens",
        "temperature",
        "top_p",
        "top_k",
        "stop_sequences",
        "tools",
        "tool_choice",
        "thinking",
        "output_config",
    }
)

# The `*_tool_result` block types that decode to PartServerToolResult, mapped
# to their open canonical `kind` codes.
_SERVER_RESULT_KINDS = {
    "web_search_tool_result": "web_search",
    "web_fetch_tool_result": "web_fetch",
    "code_execution_tool_result": "code_execution",
    "bash_code_execution_tool_result": "bash_code_execution",
    "text_editor_code_execution_tool_result": "text_editor",
    "tool_search_tool_result": "tool_search",
}


def dialect_traits() -> DialectTraits:
    """Build the hosting traits the wire layer composes for this interface.

    Anthropic first-party auth is the `x-api-key` header plus the required
    `anthropic-version` header; cloud hosts (Vertex) drop the header and
    require the `anthropic_version` body field instead. Declaring both here
    is what lets the one codec run first-party, on Vertex, or on Bedrock
    with no codec change (rule 14). The first-party origin
    (`ANTHROPIC_BASE_URL`) rides along so the §3.4 front door can compose a
    `Direct` binding without importing this plugin.

    Returns:
        The interface's `DialectTraits`.
    """
    return DialectTraits(
        vendor=PROVIDER,
        first_party_headers={"anthropic-version": ANTHROPIC_VERSION},
        cloud_body_version=("anthropic_version", ANTHROPIC_VERTEX_VERSION),
        first_party_base_url=ANTHROPIC_BASE_URL,
    )


def _usage(raw: dict[str, Any] | None) -> Usage | None:
    """Map an Anthropic `usage` object onto the dimensional model.

    Buckets per the documented disjoint-bucket rule for this provider:
    `input_tokens` → input (NOT including cache reads or cache writes —
    Anthropic's buckets are disjoint, unlike OpenAI's), `output_tokens` →
    output, `cache_read_input_tokens` → the canonical cached bucket,
    `cache_creation_input_tokens` → the plugin-namespaced open source code
    `anthropic.cache_write` (WU-13 decision: cache writes are real billed
    tokens Anthropic itemizes disjointly, so they belong on the dimensional
    `Consumption` model — where `total_tokens` stays a plain sum — not in an
    extensions bag; the source code is namespaced like every plugin-minted
    open code, with promotion to a core `UsageSource` constant triggered by
    a second provider itemizing cache writes), and
    `output_tokens_details.thinking_tokens` → reasoning.

    Args:
        raw: The wire `usage` object, if present.

    Returns:
        The canonical `Usage`, or `None` when the wire reported nothing.
    """
    if not raw:
        return None
    consumptions: list[Consumption] = []

    def _add(source: str, value: int | None) -> None:
        if value is not None:
            consumptions.append(
                Consumption(modality="text", unit="tokens", source=source, value=value)
            )

    _add("input", raw.get("input_tokens"))
    _add("output", raw.get("output_tokens"))
    _add("cached", raw.get("cache_read_input_tokens"))
    _add("anthropic.cache_write", raw.get("cache_creation_input_tokens"))
    details: dict[str, Any] = raw.get("output_tokens_details") or {}
    _add("reasoning", details.get("thinking_tokens"))
    return Usage(consumptions=consumptions)


def _thought_signature(signature: str) -> ProviderRef:
    """Anchor a thinking-block signature as REQUIRED-replay provider state.

    Anthropic rejects a replayed thinking block whose signature is missing or
    altered, so dropping this anchor across a boundary is *breakage*, weighted
    accordingly by the planner (§2.4).

    Args:
        signature: The verbatim signature string from the wire.

    Returns:
        The `ProviderRef` naming the signature.
    """
    return ProviderRef(
        provider=PROVIDER,
        interface=INTERFACE,
        kind="thought_signature",
        id=signature,
        replay=Replay.REQUIRED,
    )


def _foreign_ref_loss(path: str, ref: ProviderRef | None) -> FieldLoss | None:
    """Report a `ProviderRef` leaving its validity scope (the §2.4 rule).

    A ref is valid here when its minting `(provider, interface)` is this
    interface, or when it is provider-scoped and same-provider (crossing
    Anthropic sibling interfaces is unreported by design). Anything else is
    `UNSUPPORTED`-and-reported, never silently dropped; `REQUIRED`-replay
    anchors weigh heavier because dropping them is breakage (a 400 on
    replay), not degraded output.

    Args:
        path: The loss path the record anchors to.
        ref: The ref under the crossing check, if any.

    Returns:
        The `UNSUPPORTED` record, or None when the ref is valid here (or
        absent).
    """
    if ref is None:
        return None
    if ref.provider == PROVIDER and (
        ref.interface == INTERFACE or ref.scope == RefScope.PROVIDER
    ):
        return None
    return FieldLoss(
        path=path,
        disposition=Disposition.UNSUPPORTED,
        severity=2.0 if ref.replay is Replay.REQUIRED else 1.0,
        note=(
            f"{ref.scope}-scoped ref {ref} is not valid on "
            f"{PROVIDER}/{INTERFACE}; reported, never silently dropped (§2.4)"
        ),
    )


def _part_ref_losses(path: str, part: Part) -> list[FieldLoss]:
    """Collect the §2.4 crossing records for one part's provider-anchored state.

    Checks the universal `anchor` plus a media part's `SourceRef` handle.
    Reasoning `signature`/`opaque` anchors are handled by `_encode_reasoning`
    itself (the replay refusal path).

    Args:
        path: The part's loss path prefix.
        part: The canonical part to check.

    Returns:
        The `UNSUPPORTED` records for refs leaving their scope; empty when
        every ref (if any) is valid here.
    """
    losses: list[FieldLoss] = []
    anchor_loss = _foreign_ref_loss(f"{path}.anchor", getattr(part, "anchor", None))
    if anchor_loss is not None:
        losses.append(anchor_loss)
    source = getattr(part, "source", None)
    if isinstance(source, SourceRef):
        source_loss = _foreign_ref_loss(f"{path}.source", source.ref)
        if source_loss is not None:
            losses.append(source_loss)
    return losses


class MessagesCodec:
    """The `anthropic/messages` dialect codec — pure mapping, no I/O.

    Same obligations as its OpenAI sibling: every conversion returns a
    `EdgeOutput` with its loss/shift records; unknown input never raises; only the
    `"anthropic.messages"` `provider_options` namespace is expanded. See the
    module docstring for this dialect's signature moves (system relocation,
    REQUIRED thinking signatures, `input` ↔ `args_json`).
    """

    provider = PROVIDER
    interface = INTERFACE
    request_node = MESSAGES_REQUEST
    response_node = MESSAGES_RESPONSE
    chunk_node = MESSAGES_CHUNK

    def native_path(self, model: str) -> str:
        """Return the first-party endpoint path for a Messages call.

        Args:
            model: The target model name (unused first-party; a cloud host
                lifts it into the URL instead — that is the host's job).

        Returns:
            The Messages API path.
        """
        return MESSAGES_PATH

    def dialect_traits(self) -> DialectTraits:
        """Return this interface's hosting traits (the module `dialect_traits`).

        The codec-attached face of the facade seam (WU-07): `WireChatModel`
        builds each call's `EndpointSpec.traits` from the codec it was
        composed with, so the wire layer reads the dialect's hosting facts
        (the `anthropic-version` header, the Vertex body-version injection)
        as data without the facade ever reaching into plugin modules.

        Returns:
            The interface's `DialectTraits`.
        """
        return dialect_traits()

    def bind_resource(self, payload: dict[str, Any], resource: str) -> dict[str, Any]:
        """Inject the bound model name as this wire's `model` member.

        The facade half of the WU-05a seam: the canonical `ChatRequest`
        carries no model (routing data binds to the model object, §3.4) and
        the graph edges stay model-agnostic, so `encode_request` emits no
        `model` key. `WireChatModel` calls this after graph conversion —
        with `EndpointSpec.resource`, before the driver send — and only the
        codec knows where its dialect carries the name (here: the `model`
        body member; a hosting envelope may still relocate or strip it, e.g.
        Vertex lifts it into the URL).

        Args:
            payload: The encoded wire request body, without a model member.
            resource: The bound model name from `EndpointSpec.resource`.

        Returns:
            A new payload dict with the `model` member set; the input is
            not mutated.
        """
        return {**payload, "model": resource}

    def bind_stream(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Mark an encoded wire payload as a streaming request.

        The streaming half of the bind seam (WU-11): how a dialect asks for
        a stream is wire hygiene, not conversation, so graph edges never
        emit it — the facade calls this after `bind_resource` when serving
        `stream`/`astream`. On this wire that is the single `stream: true`
        body member; usage needs no opt-in (`message_start`/`message_delta`
        carry it natively).

        Args:
            payload: The encoded wire request body, model already bound.

        Returns:
            A new payload dict with `stream` set; the input is not mutated.
        """
        return {**payload, "stream": True}

    def encode_request(self, request: ChatRequest) -> EdgeOutput:
        """Encode a canonical `ChatRequest` into a Messages body.

        The `canonical chat.request → anthropic/messages` edge function.
        Leading system messages relocate to the top-level `system` field (a
        `SemanticShift`, data-exact); mid-conversation system messages have
        no wire home and ride the censused `anthropic.mid_conv_system`
        extension lane with reported loss. `max_tokens` is required by the
        wire: an omitted `config.max_output_tokens` gets `DEFAULT_MAX_TOKENS`
        with a reported shift, never silently.

        The emitted body has **no `model` member**: the canonical request
        carries none (§3.4 — routing data binds to the model object), so
        there is nothing to lose or report here; the facade injects the
        bound resource via `bind_resource` before send.

        Args:
            request: The canonical request to encode.

        Returns:
            An `EdgeOutput` with the wire request dict and this edge's records.
        """
        losses: list[FieldLoss] = []
        shifts: list[SemanticShift] = []
        system_texts: list[str] = []
        messages: list[dict[str, Any]] = []
        for index, message in enumerate(request.messages):
            if message.role == "system":
                if not messages:
                    system_texts.append(message.text)
                    shifts.append(
                        SemanticShift(
                            kind=ShiftKind.RELOCATION,
                            path=f"messages[{index}]",
                            note="system message relocated to the top-level `system` field",
                        )
                    )
                else:
                    # TODO: censused extension + emulation strategy for
                    # mid-conversation system turns (anthropic.mid_conv_system).
                    losses.append(
                        FieldLoss(
                            path=f"messages[{index}]",
                            disposition=Disposition.DROPPED,
                            severity=1.0,
                            note="mid-conversation system turn has no Messages wire home yet",
                        )
                    )
                continue
            messages.append(self._encode_message(index, message, losses, shifts))
        payload: dict[str, Any] = {"messages": messages}
        if system_texts:
            payload["system"] = "".join(system_texts)
        if request.tools:
            payload["tools"] = [self._encode_tool(tool) for tool in request.tools]
        self._encode_tool_choice(request, payload, losses)
        self._encode_config(request, payload, losses, shifts)
        # Lane 3: expand only OUR destination namespace (three-lane law §3.4).
        own = (request.provider_options or {}).get(f"{PROVIDER}.{INTERFACE}")
        if _is_obj(own):
            payload.update(own)
        # Lane 2 (extensions) has no encode lane on this interface yet: the
        # bag is preserved on the canonical form, but this wire body cannot
        # carry it — reported, never silently vanished (rule 5).
        # TODO: re-expand this interface's own censused extension keys onto
        # the payload and tighten the census.
        losses.extend(
            FieldLoss(
                path=f"extensions[{key}]",
                disposition=Disposition.DROPPED,
                severity=0.5,
                note=f"extensions[{key!r}] has no {PROVIDER}/{INTERFACE} encode lane yet",
            )
            for key in sorted(request.extensions or {})
        )
        return EdgeOutput(payload, tuple(losses), tuple(shifts))

    def _encode_message(
        self,
        index: int,
        message: Message,
        losses: list[FieldLoss],
        shifts: list[SemanticShift],
    ) -> dict[str, Any]:
        """Encode one canonical message as a Messages wire message.

        Parts map onto content blocks: `PartText` → `text`, `PartToolCall` →
        `tool_use` (the `args_json` wire truth parsed back into the `input`
        object), `PartToolResult` → `tool_result` (native here — `is_error`
        included, the honest asymmetry vs chat_completions), `PartReasoning`
        → `thinking` with its REQUIRED signature anchor replayed verbatim.
        Parts with no lane are reported, never silenced.

        The Messages wire has no `tool` role: a canonical tool turn threads
        as a `role: user` message whose content is the `tool_result` blocks
        — data-exact, recorded as a `SemanticShift(relocation)`.

        Args:
            index: The message's position, used in loss paths.
            message: The canonical message to encode.
            losses: The edge's loss accumulator, appended in place.
            shifts: The edge's shift accumulator, appended in place.

        Returns:
            The wire message dict.
        """
        role = _ROLE_FROM_CANONICAL.get(message.role, message.role)
        if message.role == "tool":
            role = "user"
            shifts.append(
                SemanticShift(
                    kind=ShiftKind.RELOCATION,
                    path=f"messages[{index}]",
                    note="canonical tool turn threads as a `role: user` wire message",
                )
            )
        blocks: list[dict[str, Any]] = []
        for p, part in enumerate(message.parts):
            path = f"messages[{index}].parts[{p}]"
            # The §2.4 scoped honesty rule: provider-anchored state leaving
            # its validity scope is UNSUPPORTED-and-reported before the part
            # itself is mapped (or dropped) below.
            losses.extend(_part_ref_losses(path, part))
            if isinstance(part, PartText):
                blocks.append({"type": "text", "text": part.text})
            elif isinstance(part, PartToolCall):
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": part.call_id,
                        "name": part.name,
                        # args_json is the authoritative wire truth; Anthropic
                        # wants the parsed object back.
                        "input": part.args() if part.args_json else {},
                    }
                )
            elif isinstance(part, PartToolResult):
                blocks.append(self._encode_tool_result(path, part, losses))
            elif isinstance(part, PartReasoning):
                blocks.append(self._encode_reasoning(path, part, losses))
            else:
                # TODO: encode PartImage/PartDocument via the Source union
                # (base64/url/file_id sources are all native here).
                losses.append(
                    FieldLoss(
                        path=path,
                        disposition=Disposition.DROPPED,
                        severity=1.0,
                        note=f"part type {type(part).__name__!r} not yet encoded on this interface",
                    )
                )
        return {"role": role, "content": blocks}

    def _encode_tool_result(
        self, path: str, part: PartToolResult, losses: list[FieldLoss]
    ) -> dict[str, Any]:
        """Encode a `PartToolResult` as a native `tool_result` block.

        Args:
            path: The loss path prefix for this part.
            part: The canonical tool result, correlated by `call_id`.
            losses: The edge's loss accumulator, appended in place.

        Returns:
            The wire `tool_result` block.
        """
        content: list[dict[str, Any]] = []
        for n, nested in enumerate(part.parts or []):
            if isinstance(nested, PartText):
                content.append({"type": "text", "text": nested.text})
            else:
                # TODO: nested image/document results are native on this wire.
                losses.append(
                    FieldLoss(
                        path=f"{path}.parts[{n}]",
                        disposition=Disposition.DROPPED,
                        severity=1.0,
                        note="non-text tool-result content not yet encoded",
                    )
                )
        block: dict[str, Any] = {
            "type": "tool_result",
            "tool_use_id": part.call_id,
            "content": content,
        }
        # `is_error` is a plain bool on the canonical part (never None), and it
        # crosses natively here — always emitted, the honest asymmetry vs
        # chat_completions where the flag is DROPPED.
        block["is_error"] = part.is_error
        return block

    def _encode_reasoning(
        self, path: str, part: PartReasoning, losses: list[FieldLoss]
    ) -> dict[str, Any]:
        """Encode a `PartReasoning` as a `thinking`/`redacted_thinking` block.

        A part carrying an `opaque` anchor minted here replays as
        `redacted_thinking`; a text part replays as `thinking` with its
        signature anchor verbatim. A part whose anchors were minted by a
        *different* interface must already have been reported `UNSUPPORTED`
        by the graph's ref rule (§2.4) — this encoder still refuses to
        fabricate a signature.

        Args:
            path: The loss path prefix for this part.
            part: The canonical reasoning part to replay.
            losses: The edge's loss accumulator, appended in place.

        Returns:
            The wire thinking block.
        """
        opaque = part.opaque
        if opaque is not None and opaque.provider == PROVIDER and opaque.interface == INTERFACE:
            return {"type": "redacted_thinking", "data": opaque.id}
        signature = part.signature
        if signature is None or signature.provider != PROVIDER:
            losses.append(
                FieldLoss(
                    path=f"{path}.signature",
                    disposition=Disposition.UNSUPPORTED,
                    severity=2.0,
                    note="thinking replay requires this interface's REQUIRED signature anchor",
                )
            )
            return {"type": "thinking", "thinking": part.text or "", "signature": ""}
        return {"type": "thinking", "thinking": part.text or "", "signature": signature.id}

    def _encode_tool(self, tool: Tool) -> dict[str, Any]:
        """Encode one canonical `Tool` as a custom tool definition.

        Args:
            tool: The canonical tool (name, description, `parameters` schema).

        Returns:
            The wire custom-tool entry (`input_schema` is the rename of the
            canonical `parameters`).
        """
        entry: dict[str, Any] = {
            "type": "custom",
            "name": tool.name,
            "input_schema": tool.parameters.to_dict(),
        }
        if tool.description is not None:
            entry["description"] = tool.description
        return entry

    def _encode_tool_choice(
        self, request: ChatRequest, payload: dict[str, Any], losses: list[FieldLoss]
    ) -> None:
        """Encode the canonical `ToolChoice` onto the payload.

        The canonical open modes map to Anthropic's tagged objects:
        `auto` → `{"type": "auto"}`, `required` → `{"type": "any"}` (a
        rename), `none` → `{"type": "none"}`; `named` becomes
        `{"type": "tool", "name": ...}`. A mode this interface cannot
        express (an unknown open code, or `named` without a name) is
        reported `DROPPED`, never silenced.

        Args:
            request: The canonical request carrying `tool_choice`.
            payload: The wire payload, mutated in place.
            losses: The edge's loss accumulator, appended in place.
        """
        choice = request.tool_choice
        if choice is None:
            return
        mode = choice.mode
        wire = {"auto": "auto", "required": "any", "none": "none"}.get(mode)
        if wire is not None:
            payload["tool_choice"] = {"type": wire}
            return
        name = getattr(choice, "name", None)
        if mode == "named" and name:
            payload["tool_choice"] = {"type": "tool", "name": name}
            return
        losses.append(
            FieldLoss(
                path="tool_choice",
                disposition=Disposition.DROPPED,
                severity=1.0,
                note=f"tool_choice mode {mode!r} has no Messages expression",
            )
        )

    def _encode_config(
        self,
        request: ChatRequest,
        payload: dict[str, Any],
        losses: list[FieldLoss],
        shifts: list[SemanticShift],
    ) -> None:
        """Encode `ChatConfig` knobs onto the payload, censused per field.

        `temperature`/`top_p`/`top_k` are native (the newest models reject
        `temperature` — a *profile* fact the feature gate applies before this
        encoder runs, §2.5). Values pass **verbatim** — never rescaled, never
        clamped; a value outside a documented range (`_KNOB_RANGES` — note
        Anthropic's 0..1 temperature ceiling) is the provider's to reject and
        ours to report with an `APPROXIMATED` `FieldLoss`. `max_output_tokens`
        renames to the **required** `max_tokens`; sampling knobs Anthropic
        lacks (`seed`, penalties, `logprobs`) are reported `UNSUPPORTED`.

        Args:
            request: The canonical request carrying `config`.
            payload: The wire payload, mutated in place.
            losses: The edge's loss accumulator, appended in place.
            shifts: The edge's shift accumulator, appended in place.
        """
        config = request.config
        max_tokens = config.max_output_tokens if config is not None else None
        if max_tokens is None:
            payload["max_tokens"] = DEFAULT_MAX_TOKENS
            shifts.append(
                SemanticShift(
                    kind=ShiftKind.EMULATION,
                    path="config.max_output_tokens",
                    note=f"wire requires max_tokens; injected default {DEFAULT_MAX_TOKENS}",
                )
            )
        else:
            payload["max_tokens"] = max_tokens
        if config is None:
            return
        for key in ("temperature", "top_p", "top_k"):
            value = getattr(config, key)
            if value is not None:
                payload[key] = value
        for name, (low, high) in _KNOB_RANGES.items():
            value = getattr(config, name)
            if value is not None and not low <= value <= high:
                losses.append(
                    FieldLoss(
                        path=f"config.{name}",
                        disposition=Disposition.APPROXIMATED,
                        severity=0.5,
                        note=(
                            f"config.{name}={value} is outside Anthropic's documented "
                            f"{low}..{high} range; passed verbatim, never clamped — "
                            "the provider may reject it"
                        ),
                    )
                )
        if config.stop_sequences:
            payload["stop_sequences"] = list(config.stop_sequences)
        losses.extend(
            FieldLoss(
                path=f"config.{name}",
                disposition=Disposition.UNSUPPORTED,
                severity=1.0,
                note=f"the Messages API exposes no {name}",
            )
            for name in ("seed", "frequency_penalty", "presence_penalty", "logprobs")
            if getattr(config, name, None) is not None
        )
        if config.parallel_tool_calls is not None:
            # Inverted polarity: canonical opt-IN → wire opt-OUT.
            payload.setdefault("tool_choice", {"type": "auto"})
            payload["tool_choice"]["disable_parallel_tool_use"] = not config.parallel_tool_calls
        reasoning = config.reasoning
        if reasoning is not None:
            if reasoning.budget_tokens is not None:
                payload["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": reasoning.budget_tokens,
                }
            elif reasoning.effort is not None:
                # TODO: map canonical effort levels onto adaptive thinking /
                # output_config.effort and census the approximation.
                losses.append(
                    FieldLoss(
                        path="config.reasoning.effort",
                        disposition=Disposition.APPROXIMATED,
                        severity=0.5,
                        note="effort-to-thinking mapping not yet implemented; field not sent",
                    )
                )
        if config.output is not None:
            if config.output.mode == "json_schema" and config.output.schema is not None:
                schema = config.output.schema
                payload["output_config"] = {
                    "format": {
                        "type": "json_schema",
                        # `Schema` is `JsonSchema | bool`: render the typed
                        # form to its plain wire dict; a boolean passes.
                        "schema": schema.to_dict() if isinstance(schema, JsonSchema) else schema,
                    }
                }
                # The wire format object carries only the schema itself.
                losses.extend(
                    FieldLoss(
                        path=f"config.output.{member}",
                        disposition=Disposition.DROPPED,
                        severity=1.0,
                        note=f"Messages output_config.format has no {member} member",
                    )
                    for member in ("name", "strict")
                    if getattr(config.output, member, None) is not None
                )
            elif config.output.mode != "text":
                losses.append(
                    FieldLoss(
                        path="config.output",
                        disposition=Disposition.UNSUPPORTED,
                        severity=1.0,
                        note="Messages structured output needs a JSON schema (no bare json mode)",
                    )
                )
        # TODO: cache maps to per-block cache_control breakpoints.
        losses.extend(
            FieldLoss(
                path=f"config.{name}",
                disposition=Disposition.DROPPED,
                severity=1.0,
                note=f"config.{name} encoding not yet implemented on this interface",
            )
            for name in ("modalities", "audio", "cache")
            if getattr(config, name, None) is not None
        )

    def decode_request(self, payload: dict[str, Any]) -> EdgeOutput:
        """Decode a Messages request body into a `ChatRequest`.

        The `anthropic/messages → canonical chat.request` edge function —
        the audit direction: re-converting archived wire traffic back into
        the canonical IR with no ability to make network calls (§1), and the
        first hop of every cross-provider request conversion (WU-15). The
        inverse of `encode_request`, with the dialect's signature moves run
        backwards: the top-level `system` field **un-hoists** to a leading
        canonical system message (a declared `SemanticShift(relocation)`),
        `role: user` wire messages carrying `tool_result` blocks re-thread
        as canonical tool turns (the inverse relocation, declared), and
        `tool_use.input` objects serialize to the canonical `args_json`
        wire-truth lane (the declared `anthropic.args_serialized` shift).
        The wire `model` member is **routing data, not canonical content**
        (§3.4): its echo rides `extensions["anthropic.model"]` with an
        `EXTENSIONS` record; re-encoding anywhere binds a fresh resource at
        the front door. Unknown envelope keys sweep into `extensions` —
        total decode, never a raise (rule 6).

        Args:
            payload: The raw archived request body, already JSON-parsed.

        Returns:
            An `EdgeOutput` with the canonical `ChatRequest` and this
            edge's records.
        """
        losses: list[FieldLoss] = []
        shifts: list[SemanticShift] = []
        extensions: dict[str, Any] = {}
        messages: list[Message] = []
        system = payload.get("system")
        if system is not None:
            messages.append(Message(role="system", parts=self._decode_system(system, losses)))
            shifts.append(
                SemanticShift(
                    kind=ShiftKind.RELOCATION,
                    path="system",
                    note="top-level `system` field un-hoists to a leading canonical system message",
                )
            )
        for index, wire_msg in enumerate(_as_list(payload.get("messages"))):
            if not _is_obj(wire_msg):
                continue
            messages.append(self._decode_request_message(index, wire_msg, losses, shifts))
        tools = self._decode_request_tools(payload, extensions, losses)
        tool_choice, parallel = self._decode_request_tool_choice(payload, extensions, losses)
        config = self._decode_request_config(payload, parallel, extensions, losses)
        model = payload.get("model")
        if model is not None:
            extensions[f"{PROVIDER}.model"] = model
            losses.append(
                FieldLoss(
                    path="model",
                    disposition=Disposition.EXTENSIONS,
                    note=(
                        "wire model is routing data (§3.4): the canonical request "
                        "carries no model; the echo rides extensions['anthropic.model']"
                    ),
                )
            )
        for key in sorted(set(payload) - _KNOWN_REQUEST_KEYS):
            extensions[f"{PROVIDER}.{key}"] = payload[key]
            losses.append(
                FieldLoss(
                    path=key,
                    disposition=Disposition.EXTENSIONS,
                    note=f"unmapped envelope key preserved in extensions['{PROVIDER}.{key}']",
                )
            )
        request = ChatRequest(
            messages=messages,
            tools=tools or None,
            tool_choice=tool_choice,
            config=config,
            extensions=extensions,
        )
        return EdgeOutput(request, tuple(losses), tuple(shifts))

    def _decode_system(self, system: Any, losses: list[FieldLoss]) -> list[Part]:
        """Decode the wire `system` field's content into canonical parts.

        The wire accepts a plain string or an array of text blocks; either
        becomes `PartText` parts. A non-text system block is preserved as a
        reported `PartOpaque` — never silenced.

        Args:
            system: The wire `system` value (string or block array).
            losses: The edge's loss accumulator, appended in place.

        Returns:
            The decoded parts of the canonical system message.
        """
        if isinstance(system, str):
            return [PartText(text=system)]
        parts: list[Part] = []
        for j, block in enumerate(_as_list(system)):
            if not _is_obj(block):
                continue
            if block.get("type") == "text":
                parts.append(PartText(text=block.get("text", "")))
                continue
            losses.append(
                FieldLoss(
                    path=f"system[{j}]",
                    disposition=Disposition.EXTENSIONS,
                    note=f"system block type {block.get('type')!r} preserved as PartOpaque",
                )
            )
            parts.append(PartOpaque(kind=f"{PROVIDER}.{block.get('type')}", payload=block))
        return parts

    def _decode_request_message(
        self,
        index: int,
        wire_msg: dict[str, Any],
        losses: list[FieldLoss],
        shifts: list[SemanticShift],
    ) -> Message:
        """Decode one wire request message into a canonical message.

        Content blocks decode through `_decode_request_block`; a `role:
        user` wire message carrying at least one `tool_result` block
        re-threads as a canonical tool turn (the Messages wire has no tool
        role — the inverse of the encode relocation, recorded as a
        `SemanticShift`, data-exact).

        Args:
            index: The wire message's position, used in loss/shift paths.
            wire_msg: The wire request message.
            losses: The edge's loss accumulator, appended in place.
            shifts: The edge's shift accumulator, appended in place.

        Returns:
            The canonical `Message`.
        """
        role = wire_msg.get("role", "user")
        content = wire_msg.get("content")
        parts: list[Part] = []
        has_tool_result = False
        if isinstance(content, str):
            if content:
                parts.append(PartText(text=content))
        elif _is_list(content):
            for j, block in enumerate(content):
                if not _is_obj(block):
                    continue
                part = self._decode_request_block(index, j, block, losses, shifts)
                if isinstance(part, PartToolResult):
                    has_tool_result = True
                parts.append(part)
        if role == "user" and has_tool_result:
            shifts.append(
                SemanticShift(
                    kind=ShiftKind.RELOCATION,
                    path=f"messages[{index}]",
                    note=(
                        "`role: user` wire message carrying tool_result blocks "
                        "re-threads as a canonical tool turn"
                    ),
                )
            )
            return Message(role="tool", parts=parts)
        return Message(role=_ROLE_TO_CANONICAL.get(role, role), parts=parts)

    def _decode_request_block(
        self,
        message_index: int,
        block_index: int,
        block: dict[str, Any],
        losses: list[FieldLoss],
        shifts: list[SemanticShift],
    ) -> Part:
        """Decode one request content block into a typed canonical part.

        The request-side sibling of the response decoder's `_decode_block`
        (kept separate because request paths carry the message coordinate):
        `text` → `PartText`, `tool_use` → `PartToolCall` (the `input` object
        serialized to `args_json` — the declared shift), `tool_result` →
        `PartToolResult` with `is_error` crossing exactly, `thinking` /
        `redacted_thinking` → `PartReasoning` with their REQUIRED anchors.
        Total: unknown block types become reported `PartOpaque`s, never an
        exception (rule 6).

        Args:
            message_index: The wire message's position, used in paths.
            block_index: The block's position within the message.
            block: The wire content block.
            losses: The edge's loss accumulator, appended in place.
            shifts: The edge's shift accumulator, appended in place.

        Returns:
            The decoded canonical part.
        """
        btype = block.get("type")
        path = f"messages[{message_index}].content[{block_index}]"
        if btype == "text":
            return PartText(text=block.get("text", ""))
        if btype == "tool_use":
            # The wire carries a parsed object; canonical truth is the
            # string lane — serialization is a recorded shift, not a loss.
            shifts.append(
                SemanticShift(
                    kind="anthropic.args_serialized",
                    path=f"{path}.input",
                    note="tool_use.input object serialized to canonical args_json",
                )
            )
            return PartToolCall(
                call_id=block.get("id", ""),
                name=block.get("name", ""),
                args_json=json.dumps(block.get("input") or {}),
                status="input_complete",
                executed_by="client",
            )
        if btype == "tool_result":
            nested: list[Part] = []
            nested_content = block.get("content")
            if isinstance(nested_content, str):
                if nested_content:
                    nested.append(PartText(text=nested_content))
            elif _is_list(nested_content):
                for n, item in enumerate(nested_content):
                    if not _is_obj(item):
                        continue
                    if item.get("type") == "text":
                        nested.append(PartText(text=item.get("text", "")))
                        continue
                    # TODO: nested image results are native here; decode onto
                    # the Source union and tighten.
                    losses.append(
                        FieldLoss(
                            path=f"{path}.content[{n}]",
                            disposition=Disposition.EXTENSIONS,
                            note=(
                                f"tool_result content type {item.get('type')!r} "
                                "preserved as PartOpaque"
                            ),
                        )
                    )
                    nested.append(PartOpaque(kind=f"{PROVIDER}.{item.get('type')}", payload=item))
            return PartToolResult(
                call_id=block.get("tool_use_id", ""),
                parts=nested,
                is_error=bool(block.get("is_error", False)),
            )
        if btype == "thinking":
            signature = block.get("signature")
            return PartReasoning(
                text=block.get("thinking", ""),
                signature=_thought_signature(signature) if signature else None,
            )
        if btype == "redacted_thinking":
            return PartReasoning(
                opaque=ProviderRef(
                    provider=PROVIDER,
                    interface=INTERFACE,
                    kind="redacted_thinking",
                    id=block.get("data", ""),
                    replay=Replay.REQUIRED,
                )
            )
        losses.append(
            FieldLoss(
                path=path,
                disposition=Disposition.EXTENSIONS,
                note=f"content block type {btype!r} preserved as PartOpaque",
            )
        )
        return PartOpaque(kind=f"{PROVIDER}.{btype}", payload=block)

    def _decode_request_tools(
        self,
        payload: dict[str, Any],
        extensions: dict[str, Any],
        losses: list[FieldLoss],
    ) -> list[Tool]:
        """Decode the wire `tools` array into canonical `Tool`s.

        Custom tools decode typed (`input_schema` is the rename of the
        canonical `parameters`); server-tool entries (a versioned built-in
        type) are preserved in `extensions["anthropic.tools"]` with a
        reported `EXTENSIONS` record.

        Args:
            payload: The raw request body.
            extensions: The request extensions bag, mutated in place.
            losses: The edge's loss accumulator, appended in place.

        Returns:
            The decoded tools, possibly empty.
        """
        tools: list[Tool] = []
        for i, entry in enumerate(_as_list(payload.get("tools"))):
            if _is_obj(entry) and entry.get("type", "custom") == "custom":
                schema = entry.get("input_schema")
                tools.append(
                    Tool(
                        name=entry.get("name", ""),
                        parameters=JsonSchema.from_dict(schema if _is_obj(schema) else {}),
                        description=entry.get("description"),
                    )
                )
                continue
            extensions.setdefault(f"{PROVIDER}.tools", []).append(entry)
            losses.append(
                FieldLoss(
                    path=f"tools[{i}]",
                    disposition=Disposition.EXTENSIONS,
                    note="non-custom tool entry preserved in extensions['anthropic.tools']",
                )
            )
        return tools

    def _decode_request_tool_choice(
        self,
        payload: dict[str, Any],
        extensions: dict[str, Any],
        losses: list[FieldLoss],
    ) -> tuple[ToolChoice | None, bool | None]:
        """Decode the wire `tool_choice` object.

        The tagged objects map back onto the canonical open modes
        (`{type: any}` → `required` is the rename's inverse), and the
        wire's `disable_parallel_tool_use` rider inverts back onto the
        canonical opt-in `config.parallel_tool_calls` (returned separately —
        it is config data, not tool-choice data). An inexpressible shape is
        preserved in `extensions["anthropic.tool_choice"]`, reported.

        Args:
            payload: The raw request body.
            extensions: The request extensions bag, mutated in place.
            losses: The edge's loss accumulator, appended in place.

        Returns:
            The decoded `ToolChoice` (or None) and the canonical
            `parallel_tool_calls` value (or None when the wire is silent).
        """
        choice = payload.get("tool_choice")
        if not _is_obj(choice):
            return None, None
        parallel: bool | None = None
        disable = choice.get("disable_parallel_tool_use")
        if disable is not None:
            parallel = not disable
        ctype = choice.get("type")
        if isinstance(ctype, str):
            mode = {"auto": "auto", "any": "required", "none": "none"}.get(ctype)
            if mode is not None:
                return ToolChoice(mode=mode), parallel
            if ctype == "tool" and choice.get("name"):
                return ToolChoice(mode="named", name=choice["name"]), parallel
        extensions[f"{PROVIDER}.tool_choice"] = choice
        losses.append(
            FieldLoss(
                path="tool_choice",
                disposition=Disposition.EXTENSIONS,
                note="inexpressible tool_choice preserved in extensions['anthropic.tool_choice']",
            )
        )
        return None, parallel

    def _decode_request_config(
        self,
        payload: dict[str, Any],
        parallel: bool | None,
        extensions: dict[str, Any],
        losses: list[FieldLoss],
    ) -> ChatConfig | None:
        """Decode the wire config knobs into a canonical `ChatConfig`.

        The exact inverse of `_encode_config`'s renames (the **required**
        `max_tokens` → `max_output_tokens`, `stop_sequences` verbatim,
        `thinking.budget_tokens` → `reasoning.budget_tokens`,
        `output_config.format` → `output`); values pass verbatim — decode
        has no range opinion (§3.1: the wire already accepted them).

        Args:
            payload: The raw request body.
            parallel: The canonical `parallel_tool_calls` recovered from the
                wire's `tool_choice.disable_parallel_tool_use` rider.
            extensions: The request extensions bag, mutated in place.
            losses: The edge's loss accumulator, appended in place.

        Returns:
            The decoded `ChatConfig`, or None when the wire set no knob
            (unreachable on well-formed traffic — `max_tokens` is required
            here — but decode stays total).
        """
        knobs: dict[str, Any] = {
            key: payload.get(key) for key in ("temperature", "top_p", "top_k")
        }
        knobs["max_output_tokens"] = payload.get("max_tokens")
        knobs["parallel_tool_calls"] = parallel
        stop = payload.get("stop_sequences")
        if _is_list(stop):
            knobs["stop_sequences"] = list(stop)
        thinking = payload.get("thinking")
        if _is_obj(thinking):
            if thinking.get("type") == "enabled":
                knobs["reasoning"] = ReasoningConfig(budget_tokens=thinking.get("budget_tokens"))
            else:
                extensions[f"{PROVIDER}.thinking"] = thinking
                losses.append(
                    FieldLoss(
                        path="thinking",
                        disposition=Disposition.EXTENSIONS,
                        note="non-enabled thinking config preserved in extensions",
                    )
                )
        output_config = payload.get("output_config")
        if _is_obj(output_config):
            fmt = output_config.get("format")
            if _is_obj(fmt) and fmt.get("type") == "json_schema":
                schema = fmt.get("schema")
                knobs["output"] = OutputFormat(
                    mode="json_schema",
                    schema=decode_schema(schema) if schema is not None else None,
                )
            else:
                extensions[f"{PROVIDER}.output_config"] = output_config
                losses.append(
                    FieldLoss(
                        path="output_config",
                        disposition=Disposition.EXTENSIONS,
                        note="unrecognized output_config preserved in extensions",
                    )
                )
        if all(value is None for value in knobs.values()):
            return None
        return ChatConfig(**knobs)

    def decode_response(self, payload: dict[str, Any]) -> EdgeOutput:
        """Decode a Messages response body into a `ChatResponse`.

        The `anthropic/messages → canonical chat.response` edge function.
        Every content block becomes a typed part (the honesty upgrade over the
        old text-only adapter): `text` → `PartText`, `thinking` →
        `PartReasoning` with its REQUIRED signature anchor,
        `redacted_thinking` → `PartReasoning` with an opaque anchor,
        `tool_use` → `PartToolCall` (the `input` object serialized to
        `args_json` — a recorded shift, since the string form is canonical
        truth), `server_tool_use`/`*_tool_result` → the server-tool spine
        with byte-faithful payloads, and anything unrecognized →
        `PartOpaque`, reported — this decoder never raises on unknown input
        (rule 6).

        Args:
            payload: The raw response body, already JSON-parsed.

        Returns:
            An `EdgeOutput` with the canonical `ChatResponse` and this
            edge's records.
        """
        losses: list[FieldLoss] = []
        shifts: list[SemanticShift] = []
        extensions: dict[str, Any] = {}
        parts: list[Part] = []
        for i, block in enumerate(_as_list(payload.get("content"))):
            if not _is_obj(block):
                continue
            parts.append(self._decode_block(i, block, losses, shifts))
        role: str = payload.get("role", "assistant")
        message = Message(role=_ROLE_TO_CANONICAL.get(role, role), parts=parts)
        finish = self._decode_finish(payload, extensions, losses)
        usage = _usage(payload.get("usage"))
        info = self._decode_info(payload)
        for key in sorted(set(payload) - _KNOWN_RESPONSE_KEYS):
            extensions[f"anthropic.{key}"] = payload[key]
            losses.append(
                FieldLoss(
                    path=key,
                    disposition=Disposition.EXTENSIONS,
                    note=f"unmapped envelope key preserved in extensions['anthropic.{key}']",
                )
            )
        response = ChatResponse(
            message=message,
            finish=finish,
            usage=usage,
            info=info,
            raw=payload,
            extensions=extensions,
        )
        return EdgeOutput(response, tuple(losses), tuple(shifts))

    def _decode_info(self, payload: dict[str, Any]) -> ResponseInfo:
        """Decode the response envelope's identity keys into `ResponseInfo`.

        `id` becomes an interface-scoped `ProviderRef` (kind
        `"response_id"`) — the scoped-crossing rule then reports it
        `UNSUPPORTED` if it ever leaves `anthropic/messages`; `model` is the
        provider's echo, verbatim. This wire carries no creation timestamp.

        Args:
            payload: The raw response body, already JSON-parsed.

        Returns:
            The canonical `ResponseInfo`.
        """
        raw_id = payload.get("id")
        return ResponseInfo(
            id=(
                ProviderRef(
                    provider=PROVIDER,
                    interface=INTERFACE,
                    kind="response_id",
                    id=raw_id,
                )
                if isinstance(raw_id, str)
                else None
            ),
            model=payload.get("model"),
        )

    def _decode_block(
        self,
        index: int,
        block: dict[str, Any],
        losses: list[FieldLoss],
        shifts: list[SemanticShift],
    ) -> Part:
        """Decode one response content block into a typed canonical part.

        Total: unknown block types become census-reported `PartOpaque`s (the
        deliberate provider-unique lane, §3.1), never an exception.

        Args:
            index: The block's position, used in loss paths.
            block: The wire content block.
            losses: The edge's loss accumulator, appended in place.
            shifts: The edge's shift accumulator, appended in place.

        Returns:
            The decoded canonical part.
        """
        btype = block.get("type")
        path = f"content[{index}]"
        if btype == "text":
            if block.get("citations"):
                # TODO: re-anchor citations onto PartText.annotations once
                # span offsets validate against the decoded text (§3.1).
                losses.append(
                    FieldLoss(
                        path=f"{path}.citations",
                        disposition=Disposition.EXTENSIONS,
                        note="citations ride raw/extensions pending span validation",
                    )
                )
            return PartText(text=block.get("text", ""))
        if btype == "thinking":
            signature = block.get("signature")
            return PartReasoning(
                text=block.get("thinking", ""),
                signature=_thought_signature(signature) if signature else None,
            )
        if btype == "redacted_thinking":
            return PartReasoning(
                opaque=ProviderRef(
                    provider=PROVIDER,
                    interface=INTERFACE,
                    kind="redacted_thinking",
                    id=block.get("data", ""),
                    replay=Replay.REQUIRED,
                )
            )
        if btype == "tool_use":
            # The wire carries a parsed object; canonical truth is the string
            # lane — serialization is a recorded shift, not a loss.
            shifts.append(
                SemanticShift(
                    kind="anthropic.args_serialized",
                    path=f"{path}.input",
                    note="tool_use.input object serialized to canonical args_json",
                )
            )
            return PartToolCall(
                call_id=block.get("id", ""),
                name=block.get("name", ""),
                args_json=json.dumps(block.get("input") or {}),
                status="input_complete",
                executed_by="client",
            )
        if btype == "server_tool_use":
            return PartServerToolCall(
                kind=block.get("name", ""),
                call_id=block.get("id", ""),
                status="output_available",
                payload=block,
            )
        kind = _SERVER_RESULT_KINDS.get(btype or "")
        if kind is not None:
            return PartServerToolResult(
                kind=kind,
                call_id=block.get("tool_use_id", ""),
                status="output_available",
                payload=block,
            )
        # Deliberate provider-unique content (container_upload, …) and truly
        # unknown tomorrow-blocks: byte-faithful, visible, reported.
        # TODO: census-register each PartOpaque kind in spec/extensions/.
        losses.append(
            FieldLoss(
                path=path,
                disposition=Disposition.EXTENSIONS,
                note=f"content block type {btype!r} preserved as PartOpaque",
            )
        )
        return PartOpaque(kind=f"anthropic.{btype}", payload=block)

    def _decode_finish(
        self,
        payload: dict[str, Any],
        extensions: dict[str, Any],
        losses: list[FieldLoss],
    ) -> FinishInfo | None:
        """Decode `stop_reason`/`stop_details` into a `FinishInfo`.

        The wire value rides verbatim in `native`; a `refusal` stop carries
        its structured `stop_details` as a typed `RefusalDetail`. The matched
        custom `stop_sequence` is preserved in extensions.

        Args:
            payload: The wire response body.
            extensions: The response extensions bag, mutated in place.
            losses: The edge's loss accumulator, appended in place.

        Returns:
            The `FinishInfo`, or `None` when the wire carried no reason.
        """
        native = payload.get("stop_reason")
        if payload.get("stop_sequence") is not None:
            extensions["anthropic.stop_sequence"] = payload["stop_sequence"]
            losses.append(
                FieldLoss(
                    path="stop_sequence",
                    disposition=Disposition.EXTENSIONS,
                    note="matched stop sequence preserved in extensions",
                )
            )
        if native is None:
            return None
        detail = None
        details = payload.get("stop_details")
        if _is_obj(details) and details.get("type") == "refusal":
            detail = RefusalDetail(
                category=details.get("category"),
                explanation=details.get("explanation"),
            )
        return FinishInfo(
            reason=_STOP_REASONS.get(native, "unknown"),
            native=native,
            detail=detail,
        )

    def decode_event(self, event: str | None, data: str) -> ChatChunk | None:
        """Decode one Messages SSE event into its first canonical chunk.

        The single-chunk face of the event decoder — the shape the facade's
        `ChatCodec` protocol declares. Most Messages events carry exactly one
        signal, and this returns it; a multi-signal event (`message_start`
        with usage, `message_delta` with finish and usage) surfaces only its
        *first* chunk here — `decode_frame` is the total, ordered decoder
        the `MessagesStreamTransducer` consumes on the streaming path.

        Args:
            event: The SSE `event:` name (mirrors the payload `type`).
            data: The SSE `data:` payload.

        Returns:
            The event's first canonical chunk, or `None` when the event
            surfaces nothing.
        """
        chunks = self.decode_frame(event, data).value
        return chunks[0] if chunks else None

    def decode_frame(self, event: str | None, data: str) -> EdgeOutput:
        """Decode one Messages SSE event into its ordered canonical chunks.

        The total per-event half of the chunk-shape `StreamEdge` (the WU-10
        pattern replayed on this dialect); the sans-io SSE field parsing
        lives in `ocai.wire.sse` and hands this method the event's name and
        `data` payload, so the plugin never touches a socket. Anthropic types
        each event on the SSE `event:` line and in the payload's `type`, and
        one wire event may carry several signals, each its own chunk in wire
        order:

        - `message_start` → `STREAM_START`, then the opening snapshot's
          cumulative usage as a `USAGE` chunk (`usage_cumulative=True`) —
          the wire's running totals, flagged per the chunk vocabulary;
        - `content_block_start` → `PART_START` with the typed skeleton
          (`tool_use` opens a `PartToolCall` with empty `args_json` and
          `input_streaming` status — the wire's placeholder `input: {}`
          never seeds the string lane; thinking/redacted_thinking/text and
          the server-tool spine decode as in the unary edge);
        - `content_block_delta` → one typed `PART_DELTA` (`text_delta` →
          `DeltaText`, `thinking_delta` → `DeltaReasoning`,
          `input_json_delta` → `DeltaToolArgs` raw fragments parsed once at
          PART_STOP, `signature_delta` → `DeltaSignature`); a delta type
          with no canonical lane yet (`citations_delta`) is dropped with a
          reported `FieldLoss`, recoverable from the event log;
        - `content_block_stop` → a bare `PART_STOP` (this wire carries no
          authoritative final part — the delta accumulation is the only
          carrier, so the fold law's strip-and-refold clause is vacuous);
        - `message_delta` → the accumulating `FINISH` (typed `FinishInfo`;
          a matched `stop_sequence` rides the chunk's censused
          `anthropic.stop_sequence` extension, reported), then the
          cumulative `USAGE` chunk (`usage_cumulative=True` — the wire
          reports running totals for exactly the keys it names);
        - `message_stop` → a bare `STREAM_STOP`; the transducer owns the
          terminal contract and stamps `StreamEnd(usage, finish)` onto it;
        - `ping` → a `PING` keep-alive chunk;
        - `error` → an `ERROR` chunk carrying the wire-shaped `ErrorInfo`
          (canonical taxonomy code + verbatim native payload + retryability,
          rule 8) — see `_stream_error`;
        - any unrecognized event surfaces nothing canonical — never an
          exception (rule 6).

        Args:
            event: The SSE `event:` name (mirrors the payload `type`).
            data: The SSE `data:` payload.

        Returns:
            An `EdgeOutput` whose value is the event's canonical chunks, in
            order (possibly empty), with any drop/extension records.
        """
        raw: dict[str, Any] = json.loads(data)
        etype = raw.get("type")
        chunks: list[ChatChunk] = []
        losses: list[FieldLoss] = []
        if etype == "message_start":
            chunks.append(ChatChunk(type=ChunkType.STREAM_START, raw_event=raw))
            message: dict[str, Any] = raw.get("message") or {}
            usage = _usage(message.get("usage"))
            if usage is not None:
                chunks.append(
                    ChatChunk(
                        type=ChunkType.USAGE, usage=usage, usage_cumulative=True, raw_event=raw
                    )
                )
        elif etype == "content_block_start":
            index = raw.get("index", 0)
            block: dict[str, Any] = raw.get("content_block") or {}
            chunks.append(
                ChatChunk(
                    type=ChunkType.PART_START,
                    index=index,
                    part=self._decode_start_block(index, block, losses),
                    raw_event=raw,
                )
            )
        elif etype == "content_block_delta":
            self._decode_delta_event(raw, chunks, losses)
        elif etype == "content_block_stop":
            chunks.append(
                ChatChunk(type=ChunkType.PART_STOP, index=raw.get("index", 0), raw_event=raw)
            )
        elif etype == "message_delta":
            self._decode_message_delta(raw, chunks, losses)
        elif etype == "message_stop":
            chunks.append(ChatChunk(type=ChunkType.STREAM_STOP, raw_event=raw))
        elif etype == "ping":
            chunks.append(ChatChunk(type=ChunkType.PING, raw_event=raw))
        elif etype == "error":
            err = raw.get("error")
            chunks.append(
                ChatChunk(
                    type=ChunkType.ERROR,
                    error=_stream_error(err if _is_obj(err) else {}),
                    raw_event=raw,
                )
            )
        # Any unrecognized event type surfaces nothing canonical (rule 6);
        # the verbatim event stays on the wire log, never a raise.
        return EdgeOutput(chunks, tuple(losses))

    def _decode_start_block(
        self, index: int, block: dict[str, Any], losses: list[FieldLoss]
    ) -> Part:
        """Decode a `content_block_start` block into its part skeleton.

        A `tool_use` start opens a *streaming* skeleton: empty `args_json`
        (the wire's placeholder `input: {}` is not serialized — the
        authoritative string lane accumulates from `input_json_delta`
        fragments) and `input_streaming` status, advanced to
        `input_complete` when the fold seals the slot. Every other block
        type decodes exactly as the unary `_decode_block` does (thinking
        blocks with their REQUIRED signature anchors, `redacted_thinking`
        arriving complete, the server-tool spine, unknown types as reported
        `PartOpaque`s).

        Args:
            index: The wire block index, used in loss paths.
            block: The wire `content_block` being opened.
            losses: The edge's loss accumulator, appended in place.

        Returns:
            The typed part skeleton for the opening slot.
        """
        if block.get("type") == "tool_use":
            return PartToolCall(
                call_id=block.get("id", ""),
                name=block.get("name", ""),
                args_json="",
                status="input_streaming",
                executed_by="client",
            )
        # Only the tool_use branch of _decode_block records a shift (the
        # args serialization handled above), so the discard list stays empty.
        return self._decode_block(index, block, losses, [])

    def _decode_delta_event(
        self, raw: dict[str, Any], chunks: list[ChatChunk], losses: list[FieldLoss]
    ) -> None:
        """Decode one `content_block_delta` event, appending its chunk.

        Args:
            raw: The whole parsed event, stamped on the chunk's `raw_event`.
            chunks: The event's chunk accumulator, appended in place.
            losses: The edge's loss accumulator, appended in place.
        """
        delta: dict[str, Any] = raw.get("delta") or {}
        dtype = delta.get("type")
        typed: Delta | None = None
        if dtype == "text_delta":
            typed = DeltaText(text=delta.get("text", ""))
        elif dtype == "thinking_delta":
            typed = DeltaReasoning(text=delta.get("thinking", ""))
        elif dtype == "input_json_delta":
            typed = DeltaToolArgs(fragment=delta.get("partial_json", ""))
        elif dtype == "signature_delta":
            typed = DeltaSignature(signature=delta.get("signature", ""))
        if typed is not None:
            chunks.append(
                ChatChunk(
                    type=ChunkType.PART_DELTA,
                    index=raw.get("index", 0),
                    delta=typed,
                    raw_event=raw,
                )
            )
            return
        # TODO: citations_delta → DeltaAnnotation after span validation
        # (§3.1 — never emit a possibly-misattributed span).
        losses.append(
            FieldLoss(
                path=f"content_block_delta.{dtype}",
                disposition=Disposition.DROPPED,
                severity=1.0,
                note=(
                    f"content_block_delta type {dtype!r} has no canonical delta "
                    "lane yet; dropped (recoverable verbatim from the event log)"
                ),
            )
        )

    def _decode_message_delta(
        self, raw: dict[str, Any], chunks: list[ChatChunk], losses: list[FieldLoss]
    ) -> None:
        """Decode one `message_delta` event, appending its ordered chunks.

        The accumulating finish first (`stop_reason` → the typed two-lane
        `FinishInfo`; a matched `stop_sequence` is preserved on the FINISH
        chunk's censused `anthropic.stop_sequence` extension with a reported
        `EXTENSIONS` record — mirroring the unary edge), then the CUMULATIVE
        usage snapshot as a `USAGE` chunk flagged `usage_cumulative=True`:
        the wire reports running totals for exactly the keys it names, so
        the transducer merges per source and the terminal `StreamEnd`
        carries the settled totals.

        Args:
            raw: The whole parsed event, stamped on each chunk's `raw_event`.
            chunks: The event's chunk accumulator, appended in place.
            losses: The edge's loss accumulator, appended in place.
        """
        delta: dict[str, Any] = raw.get("delta") or {}
        native = delta.get("stop_reason")
        if native:
            finish_chunk = ChatChunk(
                type=ChunkType.FINISH,
                finish=FinishInfo(reason=_STOP_REASONS.get(native, "unknown"), native=native),
                raw_event=raw,
            )
            if delta.get("stop_sequence") is not None:
                finish_chunk.extensions[f"{PROVIDER}.stop_sequence"] = delta["stop_sequence"]
                losses.append(
                    FieldLoss(
                        path="message_delta.stop_sequence",
                        disposition=Disposition.EXTENSIONS,
                        note=(
                            "matched stop sequence preserved in the FINISH chunk's "
                            "extensions['anthropic.stop_sequence']"
                        ),
                    )
                )
            chunks.append(finish_chunk)
        usage = _usage(raw.get("usage"))
        if usage is not None:
            chunks.append(
                ChatChunk(type=ChunkType.USAGE, usage=usage, usage_cumulative=True, raw_event=raw)
            )

    def map_error(self, status: int | None, body: dict[str, Any] | None) -> OcaiError | None:
        """Refine an Anthropic error body onto the precise error taxonomy.

        Anthropic returns `{"type": "error", "error": {"type", "message"}}`
        uniformly; `error.type` is the authoritative classifier. Recognized
        types map to the taxonomy (carrying the type as `code`); anything
        else defers to the wire layer's status-based mapping.

        Args:
            status: The HTTP status of the failed response, if known.
            body: The parsed Anthropic error body, if any.

        Returns:
            A precise `OcaiError`, or `None` to defer to the neutral mapping.

        TODO: Anthropic signals context overflow as a generic
            `invalid_request_error` with no distinct code; promoting it to
            `ContextLengthError` would need brittle message matching, so it
            intentionally defers.
        """
        err = (body or {}).get("error")
        if not _is_obj(err):
            return None
        etype = err.get("type")
        if not isinstance(etype, str):
            return None
        cls = _ERROR_TYPES.get(etype)
        if cls is None:
            return None
        return cls(
            err.get("message") or etype,
            status=status,
            code=etype,
            raw=body,
            provider=PROVIDER,
        )


class MessagesStreamTransducer:
    """Streaming transducer: Messages SSE events → canonical chunks.

    The stateful per-stream object the chunk-shape `StreamEdge` manufactures
    (one per stream — transducers are never shared). `feed` maps each wire
    event through `MessagesCodec.decode_frame` (one event may split into
    several canonical chunks, in order), stamps monotonic `seq` numbers, and
    adds the statefulness a well-formed canonical stream needs on this
    dialect:

    - **Cumulative usage settlement.** `message_start` and `message_delta`
      report CUMULATIVE usage snapshots covering exactly the keys each names
      (`message_delta` typically carries only running `output_tokens`), so
      the transducer merges per consumption source — last snapshot wins per
      source, keys a later snapshot omits keep their earlier values — and
      the terminal `StreamEnd.usage` carries the settled totals.
    - **The terminal contract.** `message_stop` is this wire's terminal:
      any still-open slot (a block whose `content_block_stop` never came)
      is sealed first (`PART_STOP`, advancing tool calls to
      `input_complete` in the fold), then the `STREAM_STOP` is enriched
      with `StreamEnd(usage, finish)` — usage from the settled cumulative
      snapshots, finish from the accumulated `message_delta` record. A
      stream that dies before `message_stop` gets **no** terminal chunk:
      synthesizing one would pass accumulated content off as complete, and
      the accumulator's aborted-stream sealing (`extensions
      ["ocai.incomplete"]`) is the honest downstream. A mid-stream `error`
      event passes through as its wire-shaped `ERROR` chunk; the wire then
      closes without a terminal, honestly.

    `flush` hands the graph this edge's `EdgeReport` (extension banks and
    dropped delta lanes) so streaming conversion pays the same visible toll
    as non-streaming (§4.1).
    """

    def __init__(self) -> None:
        """Initialize per-stream state (codec, sequence counter, accumulators)."""
        self._codec = MessagesCodec()
        self._seq = 0
        self._losses: list[FieldLoss] = []
        self._sources: dict[str, Consumption] = {}
        self._finish: FinishInfo | None = None
        self._open_slots: list[int] = []
        self._done = False

    def feed(self, event: Any) -> list[ChatChunk]:
        """Convert one wire SSE event into zero or more canonical chunks.

        Args:
            event: The sans-io SSE event (duck-typed: `event`/`data`
                attributes) produced by the wire layer's `SSEParser`.

        Returns:
            The canonical chunks this event surfaced, `seq`-stamped, in
            order — including, on `message_stop`, any synthesized slot
            seals and the enriched terminal.
        """
        out = self._codec.decode_frame(getattr(event, "event", None), event.data)
        self._losses.extend(out.losses)
        emitted: list[ChatChunk] = []
        for chunk in out.value:
            emitted.extend(self._admit(chunk))
        return emitted

    def _admit(self, chunk: ChatChunk) -> list[ChatChunk]:
        """Track one decoded chunk's stream state and stamp it.

        Args:
            chunk: The next decoded chunk, in event order.

        Returns:
            The chunk (seq-stamped); for the terminal `STREAM_STOP`, any
            synthesized slot seals followed by the enriched terminal.
        """
        if chunk.type == ChunkType.PART_START:
            if chunk.index is not None and chunk.index not in self._open_slots:
                self._open_slots.append(chunk.index)
        elif chunk.type == ChunkType.PART_STOP:
            if chunk.index in self._open_slots:
                self._open_slots.remove(chunk.index)
        elif chunk.type == ChunkType.USAGE and chunk.usage is not None:
            # Cumulative snapshots merge per source: a later snapshot
            # overrides exactly the sources it names, nothing else.
            for consumption in chunk.usage.consumptions:
                self._sources[consumption.source] = consumption
        elif chunk.type == ChunkType.FINISH and chunk.finish is not None:
            self._finish = chunk.finish
        elif chunk.type == ChunkType.STREAM_STOP:
            return self._terminal(chunk)
        return [self._stamp(chunk)]

    def _terminal(self, chunk: ChatChunk) -> list[ChatChunk]:
        """Seal open slots and enrich the terminal with `StreamEnd`.

        Args:
            chunk: The decoded bare `STREAM_STOP` (from `message_stop`).

        Returns:
            The `PART_STOP` seals (slot order) plus the terminal carrying
            `StreamEnd(usage, finish)`; empty if the terminal was already
            emitted (a malformed double `message_stop`).
        """
        if self._done:
            return []
        self._done = True
        emitted = [
            self._stamp(
                ChatChunk(type=ChunkType.PART_STOP, index=slot, raw_event=chunk.raw_event)
            )
            for slot in self._open_slots
        ]
        self._open_slots.clear()
        chunk.end = StreamEnd(usage=self._settled_usage(), finish=self._finish)
        emitted.append(self._stamp(chunk))
        return emitted

    def _settled_usage(self) -> Usage | None:
        """Return the merged cumulative usage, or None when none was reported.

        Returns:
            One `Usage` whose consumptions are the last cumulative value per
            source, in first-appearance order (matching the unary decoder's
            bucket order).
        """
        if not self._sources:
            return None
        return Usage(consumptions=list(self._sources.values()))

    def _stamp(self, chunk: ChatChunk) -> ChatChunk:
        """Stamp the next monotonic `seq` onto `chunk` and return it.

        Args:
            chunk: The chunk to stamp.

        Returns:
            The same chunk, seq-stamped.
        """
        chunk.seq = self._seq
        self._seq += 1
        return chunk

    def flush(self) -> tuple[list[ChatChunk], EdgeReport]:
        """Seal the stream's accounting and report this edge's fidelity.

        The terminal `STREAM_STOP` is emitted by `feed` when `message_stop`
        arrives, so the tail here is always empty: a stream that never
        reached its terminal event was aborted, and synthesizing a terminal
        for it would pass accumulated content off as complete — the
        accumulator's aborted-stream sealing owns that case.

        Returns:
            An empty tail and the edge's `EdgeReport` of accumulated
            records (extension banks, dropped delta lanes).
        """
        report = EdgeReport(
            src=MESSAGES_CHUNK,
            dst=CANONICAL_CHUNK,
            losses=tuple(self._losses),
            shifts=(),
            note="anthropic/messages -> canonical chat.chunk",
        )
        return [], report
