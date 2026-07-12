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

from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import ChunkType
from ocai.chat.types import Consumption
from ocai.chat.types import DeltaReasoning
from ocai.chat.types import DeltaSignature
from ocai.chat.types import DeltaText
from ocai.chat.types import DeltaToolArgs
from ocai.chat.types import FinishInfo
from ocai.chat.types import Message
from ocai.chat.types import Part
from ocai.chat.types import PartOpaque
from ocai.chat.types import PartReasoning
from ocai.chat.types import PartServerToolCall
from ocai.chat.types import PartServerToolResult
from ocai.chat.types import PartText
from ocai.chat.types import PartToolCall
from ocai.chat.types import PartToolResult
from ocai.chat.types import RefusalDetail
from ocai.chat.types import ResponseInfo
from ocai.chat.types import Tool
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
from ocai.core.refs import ProviderRef
from ocai.core.refs import Replay
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
    with no codec change (rule 14).

    Returns:
        The interface's `DialectTraits`.
    """
    return DialectTraits(
        vendor=PROVIDER,
        first_party_headers={"anthropic-version": ANTHROPIC_VERSION},
        cloud_body_version=("anthropic_version", ANTHROPIC_VERTEX_VERSION),
    )


def _usage(raw: dict[str, Any] | None) -> Usage | None:
    """Map an Anthropic `usage` object onto the dimensional model.

    Buckets per the documented disjoint-bucket rule for this provider:
    `input_tokens` → input (NOT including cache reads — Anthropic's buckets
    are disjoint, unlike OpenAI's), `output_tokens` → output,
    `cache_read_input_tokens` → cached, and
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
    _add("reasoning", (raw.get("output_tokens_details") or {}).get("thinking_tokens"))
    # TODO: cache_creation_input_tokens needs a censused dimension (a write,
    # not a read — billed differently).
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

    def encode_request(self, request: ChatRequest) -> EdgeOutput:
        """Encode a canonical `ChatRequest` into a Messages body.

        The `canonical chat.request → anthropic/messages` edge function.
        Leading system messages relocate to the top-level `system` field (a
        `SemanticShift`, data-exact); mid-conversation system messages have
        no wire home and ride the censused `anthropic.mid_conv_system`
        extension lane with reported loss. `max_tokens` is required by the
        wire: an omitted `config.max_output_tokens` gets `DEFAULT_MAX_TOKENS`
        with a reported shift, never silently.

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
        payload: dict[str, Any] = {"model": request.model, "messages": messages}
        if system_texts:
            payload["system"] = "".join(system_texts)
        if request.tools:
            payload["tools"] = [self._encode_tool(tool) for tool in request.tools]
        self._encode_tool_choice(request, payload, losses)
        self._encode_config(request, payload, losses, shifts)
        # Lane 3: expand only OUR destination namespace (three-lane law §3.4).
        own = (request.provider_options or {}).get(f"{PROVIDER}.{INTERFACE}")
        if isinstance(own, dict):
            payload.update(own)
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
        object), `PartToolResult` → `tool_result` (native here — no
        relocation, unlike chat_completions), `PartReasoning` → `thinking`
        with its REQUIRED signature anchor replayed verbatim. Parts with no
        lane are reported, never silenced.

        Args:
            index: The message's position, used in loss paths.
            message: The canonical message to encode.
            losses: The edge's loss accumulator, appended in place.
            shifts: The edge's shift accumulator, appended in place.

        Returns:
            The wire message dict.
        """
        blocks: list[dict[str, Any]] = []
        for p, part in enumerate(message.parts):
            path = f"messages[{index}].parts[{p}]"
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
        return {"role": _ROLE_FROM_CANONICAL.get(message.role, message.role), "content": blocks}

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
        if part.is_error is not None:
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
            "input_schema": tool.parameters.to_dict()
            if tool.parameters is not None
            else {"type": "object"},
        }
        if tool.description is not None:
            entry["description"] = tool.description
        return entry

    def _encode_tool_choice(
        self, request: ChatRequest, payload: dict[str, Any], losses: list[FieldLoss]
    ) -> None:
        """Encode the canonical `tool_choice` onto the payload.

        Canonical open modes map to Anthropic's tagged objects:
        `auto` → `{"type": "auto"}`, `required` → `{"type": "any"}` (a
        rename), `none` → `{"type": "none"}`; a forced named tool becomes
        `{"type": "tool", "name": ...}`.

        Args:
            request: The canonical request carrying `tool_choice`.
            payload: The wire payload, mutated in place.
            losses: The edge's loss accumulator, appended in place.
        """
        choice = request.tool_choice
        if choice is None:
            return
        if isinstance(choice, str):
            wire = {"auto": "auto", "required": "any", "none": "none"}.get(choice)
            if wire is not None:
                payload["tool_choice"] = {"type": wire}
                return
            losses.append(
                FieldLoss(
                    path="tool_choice",
                    disposition=Disposition.DROPPED,
                    severity=1.0,
                    note=f"unrecognized tool_choice mode {choice!r}",
                )
            )
            return
        name = getattr(choice, "name", None)
        if name:
            payload["tool_choice"] = {"type": "tool", "name": name}
            return
        # TODO: align with the canonical ToolChoice shape once it lands.
        losses.append(
            FieldLoss(
                path="tool_choice",
                disposition=Disposition.DROPPED,
                severity=1.0,
                note=f"unrecognized tool_choice shape {type(choice).__name__!r}",
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
        encoder runs, §2.5). `max_output_tokens` renames to the **required**
        `max_tokens`; sampling knobs Anthropic lacks (`seed`, penalties,
        `logprobs`) are reported `UNSUPPORTED`. Values pass verbatim — never
        rescaled, never clamped.

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
        # TODO: emit APPROXIMATED FieldLoss for out-of-range values
        # (temperature > 1.0 here, unlike OpenAI's 2.0) — verbatim always.
        for key in ("temperature", "top_p", "top_k"):
            value = getattr(config, key)
            if value is not None:
                payload[key] = value
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
                payload["output_config"] = {
                    "format": {"type": "json_schema", "schema": config.output.schema}
                }
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
        for i, block in enumerate(payload.get("content") or []):
            if not isinstance(block, dict):
                continue
            parts.append(self._decode_block(i, block, losses, shifts))
        role = payload.get("role", "assistant")
        message = Message(role=_ROLE_TO_CANONICAL.get(role, role), parts=parts)
        finish = self._decode_finish(payload, extensions, losses)
        usage = _usage(payload.get("usage"))
        info = ResponseInfo(id=payload.get("id"), model=payload.get("model"))
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
        if isinstance(details, dict) and details.get("type") == "refusal":
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
        """Decode one Messages SSE event into a canonical `ChatChunk`.

        Anthropic types each event on the SSE `event:` line and in the
        payload's `type`. Lifecycle events map to
        `STREAM_START`/`PART_START`/`PART_STOP`/`STREAM_STOP`;
        `content_block_delta` fans out by delta type (`text_delta` →
        `DeltaText`, `thinking_delta` → `DeltaReasoning`, `input_json_delta`
        → `DeltaToolArgs` raw fragments parsed once at PART_STOP,
        `signature_delta` → `DeltaSignature`); `message_delta` becomes a
        `FINISH` chunk carrying the typed `FinishInfo` and cumulative usage;
        keep-alive `ping`s and unknown events return `None` — never an
        exception (rule 6).

        Args:
            event: The SSE `event:` name (mirrors the payload `type`).
            data: The SSE `data:` payload.

        Returns:
            The canonical chunk, or `None` when the frame surfaces nothing.
        """
        raw = json.loads(data)
        etype = raw.get("type")
        if etype == "message_start":
            return ChatChunk(type=ChunkType.STREAM_START, raw_event=raw)
        if etype == "content_block_start":
            block = raw.get("content_block") or {}
            part = self._decode_block(raw.get("index", 0), block, [], [])
            return ChatChunk(
                type=ChunkType.PART_START,
                index=raw.get("index", 0),
                part=part,
                raw_event=raw,
            )
        if etype == "content_block_delta":
            delta = raw.get("delta") or {}
            dtype = delta.get("type")
            index = raw.get("index", 0)
            if dtype == "text_delta":
                return ChatChunk(
                    type=ChunkType.PART_DELTA,
                    index=index,
                    delta=DeltaText(text=delta.get("text", "")),
                    raw_event=raw,
                )
            if dtype == "thinking_delta":
                return ChatChunk(
                    type=ChunkType.PART_DELTA,
                    index=index,
                    delta=DeltaReasoning(text=delta.get("thinking", "")),
                    raw_event=raw,
                )
            if dtype == "input_json_delta":
                return ChatChunk(
                    type=ChunkType.PART_DELTA,
                    index=index,
                    delta=DeltaToolArgs(fragment=delta.get("partial_json", "")),
                    raw_event=raw,
                )
            if dtype == "signature_delta":
                return ChatChunk(
                    type=ChunkType.PART_DELTA,
                    index=index,
                    delta=DeltaSignature(signature=delta.get("signature", "")),
                    raw_event=raw,
                )
            # TODO: citations_delta → DeltaAnnotation after span validation.
            return None
        if etype == "content_block_stop":
            return ChatChunk(type=ChunkType.PART_STOP, index=raw.get("index", 0), raw_event=raw)
        if etype == "message_delta":
            native = (raw.get("delta") or {}).get("stop_reason")
            finish = (
                FinishInfo(reason=_STOP_REASONS.get(native, "unknown"), native=native)
                if native
                else None
            )
            return ChatChunk(
                type=ChunkType.FINISH,
                finish=finish,
                usage=_usage(raw.get("usage")),
                raw_event=raw,
            )
        if etype == "message_stop":
            return ChatChunk(type=ChunkType.STREAM_STOP, raw_event=raw)
        if etype == "error":
            # TODO: typed mid-stream error shape (canonical code + native +
            # retryable, rule 8) instead of the bare raw_event.
            return ChatChunk(type=ChunkType.ERROR, raw_event=raw)
        # ping and any unrecognized event: nothing canonical to surface.
        return None

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
        if not isinstance(err, dict):
            return None
        etype = err.get("type")
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

    The stateful per-stream object the chunk-shape `StreamEdge` manufactures.
    `feed` maps each wire event through `MessagesCodec.decode_event` and
    stamps monotonic `seq` numbers; `flush` seals the stream and reports the
    edge's accumulated fidelity so streaming pays the same visible toll as
    non-streaming (§4.1).
    """

    def __init__(self) -> None:
        """Initialize per-stream state (codec, sequence counter, losses)."""
        self._codec = MessagesCodec()
        self._seq = 0
        self._losses: list[FieldLoss] = []

    def feed(self, event: Any) -> list[ChatChunk]:
        """Convert one wire SSE event into zero or more canonical chunks.

        Args:
            event: The sans-io SSE event (duck-typed: `event`/`data`
                attributes) produced by the wire layer's `SSEParser`.

        Returns:
            The canonical chunks this event surfaced, `seq`-stamped.
        """
        chunk = self._codec.decode_event(getattr(event, "event", None), event.data)
        if chunk is None:
            return []
        chunk.seq = self._seq
        self._seq += 1
        return [chunk]

    def flush(self) -> tuple[list[ChatChunk], EdgeReport]:
        """Seal the stream and report this edge's accumulated fidelity.

        Returns:
            The terminal chunks (a `STREAM_STOP` carrying `StreamEnd` once
            the terminal contract is implemented) and the edge's report.
        """
        # TODO: fold message_delta usage/finish into the terminal
        # StreamEnd(usage, finish, report); seal open parts as incomplete;
        # verify PART_STOP parts equal their delta accumulation (fold law).
        report = EdgeReport(
            src=MESSAGES_CHUNK,
            dst=CANONICAL_CHUNK,
            losses=tuple(self._losses),
            shifts=(),
            note="anthropic/messages -> canonical chat.chunk",
        )
        return [], report
