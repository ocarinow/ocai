"""The `openai/chat_completions` interface codec — identity + payload mapping.

This module is the meeting point of the interface's three concerns:

- **Identity** — the three `NodeId`s (`CHAT_COMPLETIONS_REQUEST` /
  `CHAT_COMPLETIONS_RESPONSE` / `CHAT_COMPLETIONS_CHUNK`) that name this
  interface's shapes in every `Catalog`, `Route`, and `EdgeReport`. The tag is
  an opaque dated revision (`2023-11`, the chat-completions GA wire), never
  parsed.
- **Mapping** — `ChatCompletionsCodec.encode_request` / `decode_response` /
  `decode_event`, the conversion logic the edge definitions in
  `ocai.openai.chat_completions.edges` wrap into graph `Edge`s. Every mapping
  returns an `EdgeOutput` carrying its loss/shift records: nothing is silently dropped,
  approximated, or clamped (CLAUDE rule 5).
- **Wire hygiene** — `map_error` (body-based refinement onto the shared error
  taxonomy) and `native_path` (the first-party endpoint the wire layer's
  `EndpointSpec`/`Host` machinery reads; the codec itself never performs I/O).

The codec is keyed by **interface, never by host** (rule 14): the same codec
serves api.openai.com and any OpenAI-compatible gateway; hosting is resolved
below the graph at send time by `ocai.wire.hosting`.
"""

from __future__ import annotations

import json
from datetime import UTC
from datetime import date
from datetime import datetime
from typing import Any

from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import ChunkType
from ocai.chat.types import Consumption
from ocai.chat.types import DeltaRefusal
from ocai.chat.types import DeltaText
from ocai.chat.types import DeltaToolArgs
from ocai.chat.types import FinishInfo
from ocai.chat.types import Message
from ocai.chat.types import Part
from ocai.chat.types import PartReasoning
from ocai.chat.types import PartRefusal
from ocai.chat.types import PartText
from ocai.chat.types import PartToolCall
from ocai.chat.types import PartToolResult
from ocai.chat.types import ResponseInfo
from ocai.chat.types import Tool
from ocai.chat.types import Usage
from ocai.convert.graph import EdgeOutput
from ocai.core.errors import ContentFilterError
from ocai.core.errors import ContextLengthError
from ocai.core.errors import OcaiError
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
from ocai.core.traits import DialectTraits

# Interface coordinates. `TAG` is an opaque dated revision token — the GA wire
# of `/v1/chat/completions` — ordered by `released`, never parsed.
PROVIDER = "openai"
INTERFACE = "chat_completions"
TAG = "2023-11"
_RELEASED = date(2023, 11, 6)

# First-party origin and endpoint. Hosting (Direct/Custom/…) lives in
# `ocai.wire.hosting` and composes these below the graph.
OPENAI_BASE_URL = "https://api.openai.com"
CHAT_COMPLETIONS_PATH = "/v1/chat/completions"

# The interface's three graph nodes — one per message shape (a node is one
# message schema; the request, response, and chunk are distinct data models).
CHAT_COMPLETIONS_REQUEST = NodeId(
    provider=PROVIDER,
    interface=INTERFACE,
    tag=TAG,
    shape=CHAT_REQUEST,
    released=_RELEASED,
    status=Status.STABLE,
)
CHAT_COMPLETIONS_RESPONSE = NodeId(
    provider=PROVIDER,
    interface=INTERFACE,
    tag=TAG,
    shape=CHAT_RESPONSE,
    released=_RELEASED,
    status=Status.STABLE,
)
CHAT_COMPLETIONS_CHUNK = NodeId(
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

# OpenAI's end-of-stream data sentinel. Lives HERE (the interface), not in the
# wire layer's SSE parser — Anthropic terminates differently (`message_stop`).
_DONE = "[DONE]"

# Wire `finish_reason` → canonical open `FinishInfo.reason` code. Unknown wire
# values decode to `"unknown"` with the verbatim value preserved in `native`
# (rule 6) — enum growth is structurally crash-proof.
_FINISH_REASONS = {
    "stop": "complete",
    "length": "max_tokens",
    "tool_calls": "tool_call",
    "function_call": "tool_call",
    "content_filter": "content_filter",
}

# Wire role ↔ canonical role. Roles are open codes normalized exactly once at
# this codec boundary; unrecognized roles pass through verbatim.
_ROLE_TO_CANONICAL = {"assistant": "model"}
_ROLE_FROM_CANONICAL = {"model": "assistant"}

# Response envelope keys the decoder maps explicitly; every other key is swept
# into namespaced `extensions` (tolerant reader, rule 6).
_KNOWN_RESPONSE_KEYS = frozenset({"id", "object", "created", "model", "choices", "usage"})

# OpenAI's documented inclusive ranges for the range-limited sampling knobs
# (https://developers.openai.com/api/reference — chat.completions create).
# Out-of-range values pass VERBATIM with an APPROXIMATED FieldLoss — never
# rescaled, never clamped, never silent (§3.1 honesty rule).
_KNOB_RANGES: dict[str, tuple[float, float]] = {
    "temperature": (0.0, 2.0),
    "top_p": (0.0, 1.0),
    "frequency_penalty": (-2.0, 2.0),
    "presence_penalty": (-2.0, 2.0),
}


def dialect_traits() -> DialectTraits:
    """Build the hosting traits the wire layer composes for this interface.

    OpenAI first-party auth is a plain `Bearer` token with no extra headers or
    body fields, so the traits carry only the vendor tag. Consumed by
    `ocai.wire.hosting` hosts (`Direct`/`Custom`) at composition time.

    Returns:
        The interface's `DialectTraits`.
    """
    return DialectTraits(vendor="openai")


def _usage(raw: dict[str, Any] | None) -> Usage | None:
    """Map an OpenAI `usage` object onto the dimensional `Consumption` model.

    Buckets follow the documented disjoint-bucket normalization rule:
    `prompt_tokens` → input, `completion_tokens` → output,
    `prompt_tokens_details.cached_tokens` → cached, and
    `completion_tokens_details.reasoning_tokens` → reasoning. Note OpenAI's
    cached/reasoning details are *subsets* of the prompt/completion totals —
    the per-provider bucket rule is documented on the edge contract.

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

    _add("input", raw.get("prompt_tokens"))
    _add("output", raw.get("completion_tokens"))
    _add("cached", (raw.get("prompt_tokens_details") or {}).get("cached_tokens"))
    _add("reasoning", (raw.get("completion_tokens_details") or {}).get("reasoning_tokens"))
    return Usage(consumptions=consumptions)


class ChatCompletionsCodec:
    """The `openai/chat_completions` dialect codec — pure mapping, no I/O.

    The conversion half the edge definitions wrap into graph `Edge`s
    (encode/decode) and the error/endpoint half the driver consults
    (`map_error`/`native_path`). Stateless and cheap to construct; the module
    functions in `edges.py` share one instance.

    Every conversion method returns an `EdgeOutput(value, losses, shifts)` so the graph
    can accumulate a `FidelityReport` — the codec never silences a field it
    cannot map (rule 5).
    """

    provider = PROVIDER
    interface = INTERFACE
    request_node = CHAT_COMPLETIONS_REQUEST
    response_node = CHAT_COMPLETIONS_RESPONSE
    chunk_node = CHAT_COMPLETIONS_CHUNK

    def native_path(self, model: str) -> str:
        """Return the first-party endpoint path for a chat call.

        Args:
            model: The target model name (unused; the model travels in the
                request body on this interface).

        Returns:
            The chat-completions path, joined to a host origin by the wire
            layer's endpoint resolution.
        """
        return CHAT_COMPLETIONS_PATH

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

    def encode_request(self, request: ChatRequest) -> EdgeOutput:
        """Encode a canonical `ChatRequest` into a chat-completions body.

        The `canonical chat.request → openai/chat_completions` edge function.
        Messages are flattened part-by-part (tool results become sibling
        `role: tool` wire messages — a structural relocation recorded as a
        `SemanticShift`), config knobs map per the edge contract's census, and
        only this interface's own `provider_options` namespace
        (`"openai.chat_completions"`) is expanded onto the payload — foreign
        namespaces are never forwarded (three-lane law, §3.4).

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
        messages: list[dict[str, Any]] = []
        for index, message in enumerate(request.messages):
            messages.extend(self._encode_message(index, message, losses, shifts))
        payload: dict[str, Any] = {"messages": messages}
        if request.tools:
            payload["tools"] = [self._encode_tool(tool) for tool in request.tools]
        self._encode_tool_choice(request, payload, losses)
        self._encode_config(request, payload, losses)
        # Lane 3: expand only OUR destination namespace; foreign namespaces are
        # scoped to their own destination and must never leak through us.
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
    ) -> list[dict[str, Any]]:
        """Encode one canonical message into one or more wire messages.

        Text parts concatenate into `content`; `PartToolCall`s become the
        assistant message's `tool_calls`; each `PartToolResult` is relocated
        into its own sibling `role: tool` message correlated by
        `tool_call_id` (a `SemanticShift`, not a loss); `PartRefusal` maps to
        the assistant `refusal` field. Parts this interface cannot carry are
        reported, never silenced.

        Args:
            index: The message's position, used in loss paths.
            message: The canonical message to encode.
            losses: The edge's loss accumulator, appended in place.
            shifts: The edge's shift accumulator, appended in place.

        Returns:
            The wire messages this canonical message expands into.
        """
        role = _ROLE_FROM_CANONICAL.get(message.role, message.role)
        texts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        tool_results: list[dict[str, Any]] = []
        refusal: str | None = None
        for p, part in enumerate(message.parts):
            path = f"messages[{index}].parts[{p}]"
            if isinstance(part, PartText):
                texts.append(part.text)
            elif isinstance(part, PartToolCall):
                tool_calls.append(
                    {
                        "id": part.call_id,
                        "type": "function",
                        "function": {"name": part.name, "arguments": part.args_json},
                    }
                )
            elif isinstance(part, PartRefusal):
                refusal = part.text
            elif isinstance(part, PartToolResult):
                # Chat Completions carries results as sibling `role: tool`
                # messages, not nested content — a relocation, honestly shifted.
                tool_results.append(self._encode_tool_result(path, part, losses))
                shifts.append(
                    SemanticShift(
                        kind=ShiftKind.RELOCATION,
                        path=path,
                        note="tool result relocated to a sibling `role: tool` wire message",
                    )
                )
            elif isinstance(part, PartReasoning):
                # No reasoning-replay lane on chat_completions; a REQUIRED
                # anchor would be breakage on the minting interface's side.
                losses.append(
                    FieldLoss(
                        path=path,
                        disposition=Disposition.DROPPED,
                        severity=1.0,
                        note="chat_completions has no reasoning replay lane (use openai/responses)",
                    )
                )
            else:
                # TODO: encode PartImage/Audio/Document via the Source union
                # (image_url / input_audio / file parts) — needs Source decode.
                losses.append(
                    FieldLoss(
                        path=path,
                        disposition=Disposition.DROPPED,
                        severity=1.0,
                        note=f"part type {type(part).__name__!r} not yet encoded on this interface",
                    )
                )
        wire_message: dict[str, Any] = {"role": role}
        if texts or not (tool_calls or refusal is not None or tool_results):
            wire_message["content"] = "".join(texts)
        if tool_calls:
            wire_message["tool_calls"] = tool_calls
        if refusal is not None:
            wire_message["refusal"] = refusal
        if len(wire_message) == 1:
            # The turn carried only tool results: every part became a sibling
            # `role: tool` message and an empty husk would be wire-invalid
            # (a `tool` role message REQUIRES tool_call_id on this interface).
            return tool_results
        return [wire_message, *tool_results]

    def _encode_tool_result(
        self, path: str, part: PartToolResult, losses: list[FieldLoss]
    ) -> dict[str, Any]:
        """Encode a `PartToolResult` as a `role: tool` wire message.

        Nested text parts concatenate into the message content; non-text
        nested parts (images, documents) have no home on this interface and
        are reported `DROPPED`.

        Args:
            path: The loss path prefix for this part.
            part: The canonical tool result, correlated by `call_id`.
            losses: The edge's loss accumulator, appended in place.

        Returns:
            The `role: tool` wire message.
        """
        texts: list[str] = []
        for n, nested in enumerate(part.parts or []):
            if isinstance(nested, PartText):
                texts.append(nested.text)
            else:
                losses.append(
                    FieldLoss(
                        path=f"{path}.parts[{n}]",
                        disposition=Disposition.DROPPED,
                        severity=1.0,
                        note="non-text tool-result content has no chat_completions lane",
                    )
                )
        if part.is_error:
            # TODO: OpenAI has no is_error flag on tool messages; decide a
            # censused convention (prefix? extensions echo?) and declare it.
            losses.append(
                FieldLoss(
                    path=f"{path}.is_error",
                    disposition=Disposition.DROPPED,
                    severity=0.5,
                    note="tool-result error flag has no chat_completions field",
                )
            )
        return {
            "role": "tool",
            "tool_call_id": part.call_id,
            "content": "".join(texts),
        }

    def _encode_tool(self, tool: Tool) -> dict[str, Any]:
        """Encode one canonical `Tool` as a function-tool definition.

        Args:
            tool: The canonical tool (name, description, `parameters` schema).

        Returns:
            The wire `{"type": "function", "function": {...}}` entry.
        """
        function: dict[str, Any] = {"name": tool.name}
        if tool.description is not None:
            function["description"] = tool.description
        if tool.parameters is not None:
            function["parameters"] = tool.parameters.to_dict()
        return {"type": "function", "function": function}

    def _encode_tool_choice(
        self, request: ChatRequest, payload: dict[str, Any], losses: list[FieldLoss]
    ) -> None:
        """Encode the canonical `ToolChoice` onto the payload.

        The canonical open modes map onto this wire's idiom: `auto`, `none`,
        and `required` are the same string codes; `named` becomes the
        named-tool-choice object around `ToolChoice.name`. A mode this
        interface cannot express (an unknown open code, or `named` without a
        name) is reported `DROPPED`, never silenced.

        Args:
            request: The canonical request carrying `tool_choice`.
            payload: The wire payload, mutated in place.
            losses: The edge's loss accumulator, appended in place.
        """
        choice = request.tool_choice
        if choice is None:
            return
        mode = getattr(choice, "mode", None)
        if mode in ("auto", "none", "required"):
            payload["tool_choice"] = mode
            return
        name = getattr(choice, "name", None)
        if mode == "named" and name:
            payload["tool_choice"] = {"type": "function", "function": {"name": name}}
            return
        losses.append(
            FieldLoss(
                path="tool_choice",
                disposition=Disposition.DROPPED,
                severity=1.0,
                note=f"tool_choice mode {mode!r} has no chat_completions expression",
            )
        )

    def _encode_config(
        self, request: ChatRequest, payload: dict[str, Any], losses: list[FieldLoss]
    ) -> None:
        """Encode `ChatConfig` knobs onto the payload, censused per field.

        Values pass **verbatim** — never rescaled, never clamped; a value
        outside a documented range (`_KNOB_RANGES`) is the provider's to
        reject and ours to report with an `APPROXIMATED` `FieldLoss`.
        Renames (`max_output_tokens` → `max_completion_tokens`,
        `stop_sequences` → `stop`) are recorded on the edge contract, not
        re-reported per call.

        Args:
            request: The canonical request carrying `config`.
            payload: The wire payload, mutated in place.
            losses: The edge's loss accumulator, appended in place.
        """
        config = request.config
        if config is None:
            return
        exact = {
            "temperature": config.temperature,
            "top_p": config.top_p,
            "seed": config.seed,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
            "parallel_tool_calls": config.parallel_tool_calls,
        }
        payload.update({key: value for key, value in exact.items() if value is not None})
        for name, (low, high) in _KNOB_RANGES.items():
            value = exact[name]
            if value is not None and not low <= value <= high:
                losses.append(
                    FieldLoss(
                        path=f"config.{name}",
                        disposition=Disposition.APPROXIMATED,
                        severity=0.5,
                        note=(
                            f"config.{name}={value} is outside OpenAI's documented "
                            f"{low}..{high} range; passed verbatim, never clamped — "
                            "the provider may reject it"
                        ),
                    )
                )
        if config.max_output_tokens is not None:
            payload["max_completion_tokens"] = config.max_output_tokens
        if config.stop_sequences:
            payload["stop"] = list(config.stop_sequences)
        if config.top_k is not None:
            losses.append(
                FieldLoss(
                    path="config.top_k",
                    disposition=Disposition.UNSUPPORTED,
                    severity=1.0,
                    note="chat_completions exposes no top_k",
                )
            )
        if config.logprobs is not None:
            # TODO: split canonical logprobs config into logprobs/top_logprobs.
            payload["logprobs"] = config.logprobs
        reasoning = config.reasoning
        if reasoning is not None:
            if reasoning.effort is not None:
                payload["reasoning_effort"] = reasoning.effort
            if reasoning.budget_tokens is not None:
                losses.append(
                    FieldLoss(
                        path="config.reasoning.budget_tokens",
                        disposition=Disposition.UNSUPPORTED,
                        severity=1.0,
                        note="chat_completions takes effort levels, not token budgets",
                    )
                )
        if config.output is not None:
            payload["response_format"] = self._encode_output(config.output)
        # TODO: modalities/audio map to wire fields; cache maps to
        # prompt_cache_key — implement and tighten the census.
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

    def _encode_output(self, output: Any) -> dict[str, Any]:
        """Encode the canonical `OutputFormat` as a `response_format` object.

        Args:
            output: The canonical output format (`mode`, `name`, `schema`,
                `strict`).

        Returns:
            The wire `response_format` selector.
        """
        if output.mode == "json_schema":
            json_schema: dict[str, Any] = {"name": output.name or "response"}
            schema = output.schema
            if schema is not None:
                # `Schema` is `JsonSchema | bool`: render the typed form to
                # its plain wire dict; a boolean schema passes through.
                json_schema["schema"] = schema.to_dict() if hasattr(schema, "to_dict") else schema
            if output.strict is not None:
                json_schema["strict"] = output.strict
            return {"type": "json_schema", "json_schema": json_schema}
        if output.mode == "json":
            return {"type": "json_object"}
        return {"type": "text"}

    def decode_response(self, payload: dict[str, Any]) -> EdgeOutput:
        """Decode a chat-completions response body into a `ChatResponse`.

        The `openai/chat_completions → canonical chat.response` edge function.
        The honesty upgrades over the old adapter: `tool_calls` become typed
        `PartToolCall`s, `refusal` becomes `PartRefusal`, `finish_reason`
        becomes a `FinishInfo` with the verbatim native lane, `choices[1:]`
        land in the censused `openai.choices` extension with reported loss
        (single message forever, §3.1), and unknown envelope keys sweep into
        `extensions` — this decoder never raises on unknown input (rule 6).

        Args:
            payload: The raw response body, already JSON-parsed.

        Returns:
            An `EdgeOutput` with the canonical `ChatResponse` and this
            edge's records.
        """
        losses: list[FieldLoss] = []
        extensions: dict[str, Any] = {}
        choices = payload.get("choices") or []
        choice: dict[str, Any] = choices[0] if choices else {}
        if len(choices) > 1:
            extensions["openai.choices"] = choices[1:]
            losses.append(
                FieldLoss(
                    path="choices[1:]",
                    disposition=Disposition.EXTENSIONS,
                    note="single-message IR; extra choices ride extensions['openai.choices']",
                )
            )
        message = self._decode_message(choice.get("message") or {}, losses, extensions)
        finish = self._decode_finish(choice, extensions, losses)
        usage = _usage(payload.get("usage"))
        info = self._decode_info(payload)
        for key in sorted(set(payload) - _KNOWN_RESPONSE_KEYS):
            extensions[f"openai.{key}"] = payload[key]
            losses.append(
                FieldLoss(
                    path=key,
                    disposition=Disposition.EXTENSIONS,
                    note=f"unmapped envelope key preserved in extensions['openai.{key}']",
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
        return EdgeOutput(response, tuple(losses))

    def _decode_info(self, payload: dict[str, Any]) -> ResponseInfo:
        """Decode the response envelope's identity keys into `ResponseInfo`.

        `id` becomes an interface-scoped `ProviderRef` (kind
        `"response_id"`) — the scoped-crossing rule then reports it
        `UNSUPPORTED` if it ever leaves `openai/chat_completions`; `model`
        is the provider's echo, verbatim; `created` (Unix seconds) maps to
        the typed UTC timestamp (an exact, reversible rename recorded on
        the edge contract, not re-reported per call).

        Args:
            payload: The raw response body, already JSON-parsed.

        Returns:
            The canonical `ResponseInfo`.
        """
        raw_id = payload.get("id")
        raw_created = payload.get("created")
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
            created=(
                datetime.fromtimestamp(raw_created, tz=UTC)
                if isinstance(raw_created, (int, float)) and not isinstance(raw_created, bool)
                else None
            ),
        )

    def _decode_message(
        self,
        wire_msg: dict[str, Any],
        losses: list[FieldLoss],
        extensions: dict[str, Any],
    ) -> Message:
        """Decode a wire assistant message into a canonical parts message.

        `content` → `PartText`, `tool_calls` → `PartToolCall` (arguments kept
        as the authoritative `args_json` wire string, parsed on read),
        `refusal` → `PartRefusal`. Annotations, audio, and the deprecated
        `function_call` are preserved in censused extensions with reported
        dispositions — nothing is silenced.

        Args:
            wire_msg: The choice's `message` object.
            losses: The edge's loss accumulator, appended in place.
            extensions: The response extensions bag, mutated in place.

        Returns:
            The canonical `Message`.
        """
        parts: list[Part] = []
        content = wire_msg.get("content")
        if content:
            parts.append(PartText(text=content))
        for i, call in enumerate(wire_msg.get("tool_calls") or []):
            function = call.get("function") or {}
            parts.append(
                PartToolCall(
                    call_id=call.get("id", ""),
                    name=function.get("name", ""),
                    args_json=function.get("arguments", ""),
                    status="input_complete",
                    executed_by="client",
                )
            )
            losses.append(
                FieldLoss(
                    path=f"choices[0].message.tool_calls[{i}]",
                    disposition=Disposition.EXACT,
                    note="typed PartToolCall; arguments kept verbatim as args_json",
                )
            )
        refusal = wire_msg.get("refusal")
        if refusal:
            parts.append(PartRefusal(text=refusal))
        if wire_msg.get("annotations"):
            # TODO: re-anchor url_citation annotations onto PartText.annotations
            # once span offsets are validated against the decoded text — never
            # emit a possibly-misattributed span (§3.1).
            extensions["openai.annotations"] = wire_msg["annotations"]
            losses.append(
                FieldLoss(
                    path="choices[0].message.annotations",
                    disposition=Disposition.EXTENSIONS,
                    note="citations preserved verbatim pending span validation",
                )
            )
        if wire_msg.get("audio") is not None:
            # TODO: decode to PartAudio + ProviderRef audio id anchor.
            extensions["openai.audio"] = wire_msg["audio"]
            losses.append(
                FieldLoss(
                    path="choices[0].message.audio",
                    disposition=Disposition.EXTENSIONS,
                    note="audio output preserved verbatim pending PartAudio decode",
                )
            )
        if wire_msg.get("function_call") is not None:
            extensions["openai.function_call"] = wire_msg["function_call"]
            losses.append(
                FieldLoss(
                    path="choices[0].message.function_call",
                    disposition=Disposition.EXTENSIONS,
                    note="deprecated wire lane preserved; superseded by tool_calls",
                )
            )
        role = wire_msg.get("role", "assistant")
        return Message(role=_ROLE_TO_CANONICAL.get(role, role), parts=parts)

    def _decode_finish(
        self,
        choice: dict[str, Any],
        extensions: dict[str, Any],
        losses: list[FieldLoss],
    ) -> FinishInfo | None:
        """Decode a choice's `finish_reason` into a `FinishInfo`.

        The canonical `reason` is an open code; the wire value rides verbatim
        in the `native` lane so an unknown tomorrow-value decodes to
        `"unknown"` without losing anything. Choice `logprobs` are preserved
        in extensions.

        Args:
            choice: The wire choice object.
            extensions: The response extensions bag, mutated in place.
            losses: The edge's loss accumulator, appended in place.

        Returns:
            The `FinishInfo`, or `None` when the wire carried no reason.
        """
        if choice.get("logprobs") is not None:
            extensions["openai.logprobs"] = choice["logprobs"]
            losses.append(
                FieldLoss(
                    path="choices[0].logprobs",
                    disposition=Disposition.EXTENSIONS,
                    note="logprobs preserved verbatim pending a typed lane",
                )
            )
        native = choice.get("finish_reason")
        if native is None:
            return None
        return FinishInfo(reason=_FINISH_REASONS.get(native, "unknown"), native=native)

    def decode_event(self, event: str | None, data: str) -> ChatChunk | None:
        """Decode one chat-completions SSE frame into a canonical `ChatChunk`.

        The per-event half of the chunk-shape `StreamEdge`; the sans-io SSE
        field parsing itself lives in `ocai.wire.sse` and hands this method
        the frame's `event` name and `data` payload, so the plugin never
        touches a socket. Text deltas become `PART_DELTA(DeltaText)`,
        tool-call argument fragments become `PART_DELTA(DeltaToolArgs)` (raw
        string fragments, parsed once at PART_STOP), refusal fragments become
        `DeltaRefusal`, the opening role-only delta becomes `STREAM_START`, a
        `finish_reason` becomes a `FINISH` chunk with a typed `FinishInfo`,
        and the usage-only final frame becomes a `USAGE` chunk. The `[DONE]`
        sentinel returns `None`; the transducer emits the terminal
        `STREAM_STOP`/`StreamEnd`.

        Args:
            event: The SSE `event:` field, if the frame carried one (OpenAI
                does not use named events on this interface).
            data: The SSE `data:` payload.

        Returns:
            The canonical chunk, or `None` when the frame surfaces nothing.
        """
        if data.strip() == _DONE:
            return None
        raw = json.loads(data)
        choices = raw.get("choices") or []
        if not choices:
            usage = _usage(raw.get("usage"))
            if usage is not None:
                return ChatChunk(type=ChunkType.USAGE, usage=usage, raw_event=raw)
            return None
        choice = choices[0]
        # TODO: choices[1:] in streams — reject n>1 at admission (§3.1); until
        # then extra streamed choices are not surfaced here.
        index = choice.get("index", 0)
        delta = choice.get("delta") or {}
        content = delta.get("content")
        if content is not None:
            return ChatChunk(
                type=ChunkType.PART_DELTA,
                index=index,
                delta=DeltaText(text=content),
                raw_event=raw,
            )
        if delta.get("refusal") is not None:
            return ChatChunk(
                type=ChunkType.PART_DELTA,
                index=index,
                delta=DeltaRefusal(text=delta["refusal"]),
                raw_event=raw,
            )
        tool_calls = delta.get("tool_calls") or []
        if tool_calls:
            call = tool_calls[0]
            function = call.get("function") or {}
            if call.get("id"):
                # First frame for this tool call: open the part with its
                # identity; argument fragments follow as DeltaToolArgs.
                return ChatChunk(
                    type=ChunkType.PART_START,
                    index=index,
                    part=PartToolCall(
                        call_id=call["id"],
                        name=function.get("name", ""),
                        args_json="",
                        status="input_streaming",
                        executed_by="client",
                    ),
                    raw_event=raw,
                )
            # TODO: a single frame can carry id AND an arguments fragment, and
            # multiple tool_calls entries — the transducer must split those
            # into multiple canonical chunks (feed returns a list).
            return ChatChunk(
                type=ChunkType.PART_DELTA,
                index=index,
                delta=DeltaToolArgs(fragment=function.get("arguments", "")),
                raw_event=raw,
            )
        if delta.get("role"):
            return ChatChunk(type=ChunkType.STREAM_START, index=index, raw_event=raw)
        native = choice.get("finish_reason")
        if native is not None:
            return ChatChunk(
                type=ChunkType.FINISH,
                index=index,
                finish=FinishInfo(reason=_FINISH_REASONS.get(native, "unknown"), native=native),
                raw_event=raw,
            )
        return None

    def map_error(self, status: int | None, body: dict[str, Any] | None) -> OcaiError | None:
        """Refine an OpenAI error body onto the precise error taxonomy.

        OpenAI returns `{"error": {"type", "code", "message"}}` on every
        endpoint, and the precise meaning lives in `code`/`type`, not the HTTP
        status (a context-length overflow is a 400, not a 413). The driver
        applies this refinement on top of the wire layer's neutral
        status-based mapping; returning `None` defers to that coarse error.

        Args:
            status: The HTTP status of the failed response, if known.
            body: The parsed OpenAI error body, if any.

        Returns:
            A precise `OcaiError`, or `None` to defer to the neutral mapping.
        """
        err = (body or {}).get("error")
        if not isinstance(err, dict):
            return None
        code = err.get("code") or err.get("type")
        message = err.get("message") or str(code)
        if code in ("context_length_exceeded", "string_above_max_length"):
            return ContextLengthError(
                message, status=status, code=code, raw=body, provider=PROVIDER
            )
        if code == "content_filter":
            return ContentFilterError(
                message, status=status, code=code, raw=body, provider=PROVIDER
            )
        return None


class ChatCompletionsStreamTransducer:
    """Streaming transducer: chat-completions SSE frames → canonical chunks.

    The stateful per-stream object a chunk-shape `StreamEdge` manufactures
    (one per stream — transducers are never shared). `feed` maps each wire
    frame through `ChatCompletionsCodec.decode_event` and stamps monotonic
    `seq` numbers; `flush` seals the stream and hands the graph this edge's
    `EdgeReport` so streaming conversion pays the same visible toll as
    non-streaming (§4.1).
    """

    def __init__(self) -> None:
        """Initialize per-stream state (codec, sequence counter, losses)."""
        self._codec = ChatCompletionsCodec()
        self._seq = 0
        self._losses: list[FieldLoss] = []

    def feed(self, event: Any) -> list[ChatChunk]:
        """Convert one wire SSE event into zero or more canonical chunks.

        Args:
            event: The sans-io SSE event (duck-typed: `event`/`data`
                attributes) produced by the wire layer's `SSEParser`.

        Returns:
            The canonical chunks this frame surfaced, `seq`-stamped.
        """
        # TODO: split multi-signal frames (role+content, id+arguments,
        # several tool_calls entries) into multiple chunks; today decode_event
        # surfaces at most one chunk per frame.
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
        # TODO: emit the terminal STREAM_STOP chunk with
        # StreamEnd(usage, finish, report) — needs the accumulated usage and
        # finish tracked across feed() calls; seal open parts as incomplete.
        report = EdgeReport(
            src=CHAT_COMPLETIONS_CHUNK,
            dst=CANONICAL_CHUNK,
            losses=tuple(self._losses),
            shifts=(),
            note="openai/chat_completions -> canonical chat.chunk",
        )
        return [], report
