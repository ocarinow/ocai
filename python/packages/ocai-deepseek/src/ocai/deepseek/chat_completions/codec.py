"""DeepSeek unary semantics over the shared, explicitly configured compatible codec."""

from copy import deepcopy
from dataclasses import replace
from typing import Any

from ocai.chat.types import ChatRequest
from ocai.chat.types import Part
from ocai.chat.types import PartText
from ocai.chat.types import PartUnknown
from ocai.convert.graph import EdgeOutput
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import FieldLoss
from ocai.core.ir import is_json_array
from ocai.core.ir import is_json_object
from ocai.deepseek.chat_completions import descriptor
from ocai.deepseek.chat_completions.evidence import Evidence
from ocai.deepseek.chat_completions.evidence import fields
from ocai.deepseek.chat_completions.evidence import response_payload
from ocai.deepseek.chat_completions.evidence import retain
from ocai.deepseek.chat_completions.evidence import tool_calls
from ocai.deepseek.chat_completions.policy import NAMESPACE
from ocai.deepseek.chat_completions.policy import inspect_request
from ocai.deepseek.chat_completions.usage import decode_usage
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.openai.chat_completions.variant import ChatCompletionsVariant

VARIANT = ChatCompletionsVariant(
    request_node=descriptor.CHAT_COMPLETIONS_REQUEST,
    response_node=descriptor.CHAT_COMPLETIONS_RESPONSE,
    chunk_node=descriptor.CHAT_COMPLETIONS_CHUNK,
    traits=descriptor.TRAITS,
    path=descriptor.PATH,
    reasoning_field="reasoning_content",
    max_tokens_field="max_tokens",
    knob_ranges=(("temperature", 0.0, 2.0),),
    finish_reasons=(("insufficient_system_resource", "error"), ("aborted", "error")),
)
_REQUEST_FIELDS = {
    "model",
    "messages",
    "tools",
    "tool_choice",
    "temperature",
    "top_p",
    "seed",
    "frequency_penalty",
    "presence_penalty",
    "parallel_tool_calls",
    "logprobs",
    "max_completion_tokens",
    "max_tokens",
    "stop",
    "reasoning_effort",
    "response_format",
    "thinking",
}


def _bank(extensions: dict[str, Any], evidence: Evidence, key: str) -> dict[str, Any]:
    """Collect native extension values without minting unregistered tomorrow-keys."""
    for name, value in extensions.items():
        retain(evidence, name.removeprefix("deepseek."), value)
    evidence.sort(key=lambda record: record["path"])
    return {key: evidence} if evidence else {}


def _notes(losses: list[FieldLoss]) -> tuple[FieldLoss, ...]:
    return tuple(replace(loss, note=loss.note.replace("openai.", "deepseek.")) for loss in losses)


class DeepSeekCodec(ChatCompletionsCodec):
    """Qualify text, tools, JSON-object and reasoning without enabling execution yet."""

    def __init__(self) -> None:
        """Use DeepSeek coordinates and field lanes, never OpenAI routing identity."""
        super().__init__(VARIANT)

    def encode_request(self, request: ChatRequest) -> EdgeOutput:
        """Apply semantic findings to the effective shared-codec output before provider I/O."""
        out = super().encode_request(request)
        losses, shifts = list(out.losses), list(out.shifts)
        inspect_request(request, out.value, losses, shifts)
        return EdgeOutput(out.value, _notes(losses), tuple(shifts))

    def decode_request(self, payload: dict[str, Any]) -> EdgeOutput:
        """Decode compatible request data and retain unknown native fields by source path."""
        evidence: Evidence = []
        raw: Any = payload
        if not is_json_object(raw):
            retain(evidence, "$", raw)
            raw = {}
        safe = fields(raw, _REQUEST_FIELDS, "", evidence)
        thinking = safe.pop("thinking", None)
        messages = safe.get("messages")
        if is_json_array(messages):
            for index, message in enumerate(messages):
                if not is_json_object(message):
                    continue  # shared tolerant reader retains the malformed entry
                role = message.get("role")
                if not isinstance(role, str):
                    retain(evidence, f"messages[{index}].role", role)
                    message["role"] = "unknown"
                if "tool_calls" in message:
                    message["tool_calls"] = tool_calls(
                        message["tool_calls"], f"messages[{index}].tool_calls", evidence
                    )
        out = super().decode_request(safe)
        request = out.value
        additional_evidence = bool(evidence)
        request.extensions = _bank(request.extensions, evidence, "deepseek.request_unmapped")
        if "thinking" in raw:
            request.provider_options[NAMESPACE] = {"thinking": deepcopy(thinking)}
        losses = list(out.losses)
        if additional_evidence and not any(loss.path == "unmapped" for loss in losses):
            losses.append(
                FieldLoss(
                    "unmapped",
                    Disposition.EXTENSIONS,
                    note="unknown native request data retained by source path",
                )
            )
        return EdgeOutput(request, _notes(losses), out.shifts)

    def _decode_request_content(
        self, index: int, wire_msg: dict[str, Any], losses: list[FieldLoss]
    ) -> list[Part]:
        """Keep future native content tags as unknown parts, without inventing media support."""
        content = wire_msg.get("content")
        if not is_json_array(content):
            return super()._decode_request_content(index, wire_msg, losses)
        parts: list[Part] = []
        for position, item in enumerate(content):
            if not is_json_object(item):
                continue  # the shared request evidence sweep retains malformed scalar entries
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(PartText(text=item["text"]))
            else:
                parts.append(PartUnknown.from_dict(deepcopy(item)))
                losses.append(
                    FieldLoss(
                        f"messages[{index}].content[{position}]",
                        Disposition.EXTENSIONS,
                        note="unqualified native content preserved as PartUnknown",
                    )
                )
        return parts

    def decode_response(self, payload: dict[str, Any]) -> EdgeOutput:
        """Preserve reasoning, native identity and disjoint measured usage through total decode."""
        safe, evidence = response_payload(payload)
        native_usage = safe.pop("usage", None)
        out = super().decode_response(safe)
        response = out.value
        losses = list(out.losses)
        response.usage = decode_usage(native_usage, losses)
        response.raw = deepcopy(payload)
        additional_evidence = bool(evidence)
        response.extensions = _bank(response.extensions, evidence, "deepseek.response_unmapped")
        if additional_evidence:
            losses.append(
                FieldLoss(
                    "unmapped",
                    Disposition.EXTENSIONS,
                    note="unknown native response data retained by source path",
                )
            )
        return EdgeOutput(response, _notes(losses), out.shifts)
