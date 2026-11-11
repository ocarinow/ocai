"""DeepSeek request semantics, applied to the effective compatible wire payload."""

from dataclasses import fields
from typing import Any

from ocai.chat.types import ChatRequest
from ocai.chat.types import PartReasoning
from ocai.chat.types import PartText
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import FieldLoss
from ocai.core.fidelity import SemanticShift
from ocai.core.ir import IRObject
from ocai.core.ir import is_json_array
from ocai.core.ir import is_json_object

NAMESPACE = "deepseek.chat_completions"
ALIASES = {"minimal": "low", "medium": "high", "xhigh": "high", "ultra": "max"}


def inspect_request(
    request: ChatRequest,
    payload: dict[str, Any],
    losses: list[FieldLoss],
    shifts: list[SemanticShift],
) -> None:
    """Report provider effects after passthrough expansion, so overrides cannot bypass policy."""
    own = request.provider_options.get(NAMESPACE)
    own = own if is_json_object(own) else {}

    def path(key: str) -> str:
        if key in own:
            return f"provider_options[{NAMESPACE}].{key}"
        return {
            "reasoning_effort": "config.reasoning.effort",
            "max_tokens": "config.max_output_tokens",
            "response_format": "config.output",
            "tool_choice": "tool_choice",
        }.get(key, "config." + key)

    def unsupported(key: str, note: str) -> None:
        losses.append(FieldLoss(path(key), Disposition.UNSUPPORTED, note=note))

    _unmapped_envelopes(request, "", losses)
    config = request.config
    if config is not None:
        if config.reasoning is not None and config.reasoning.include_thoughts is not None:
            losses.append(
                FieldLoss(
                    "config.reasoning.include_thoughts",
                    Disposition.UNSUPPORTED,
                    note="the selected wire has no separate thought-visibility control",
                )
            )
        if config.output is not None and config.output.mode not in ("text", "json", "json_schema"):
            losses.append(
                FieldLoss(
                    "config.output",
                    Disposition.UNSUPPORTED,
                    note="unknown canonical output mode has no qualified wire mapping",
                )
            )
    thinking = payload.get("thinking")
    effort = payload.get("reasoning_effort", "high")
    enabled = effort != "none"
    if thinking is not None:
        if is_json_object(thinking) and thinking.get("type") in ("enabled", "disabled"):
            enabled = thinking["type"] == "enabled"
            if set(thinking) != {"type"}:
                unsupported("thinking", "unknown thinking controls are not qualified")
        else:
            unsupported("thinking", "unknown thinking selector is not qualified")
    if thinking is not None and "reasoning_effort" in payload:
        shifts.append(
            SemanticShift(
                kind="deepseek.thinking_override",
                path=path("reasoning_effort"),
                note="explicit thinking selector takes precedence over reasoning_effort",
            )
        )
    if isinstance(effort, str) and effort in ALIASES:
        shifts.append(
            SemanticShift(
                kind="deepseek.effort_alias",
                path=path("reasoning_effort"),
                note=f"provider interprets {effort} as {ALIASES[effort]}; value passes unchanged",
            )
        )
    elif effort not in ("none", "low", "high", "max"):
        unsupported("reasoning_effort", "unknown effort code passes without a qualification claim")
    shifts.extend(
        SemanticShift(
            kind="deepseek.ignored_parameter",
            path=path(key),
            note="provider accepts but ignores this parameter in the selected mode",
        )
        for key in ("temperature", "frequency_penalty", "presence_penalty")
        if key in payload and (enabled or key != "temperature")
    )
    if "top_p" in payload:
        unsupported(
            "top_p",
            "top_p depends on the bound model; this edge cannot qualify it (G-10)",
        )
    for key in ("seed", "parallel_tool_calls", "max_completion_tokens", "n"):
        if key in payload:
            unsupported(key, "parameter is outside the selected documented DeepSeek surface")
    choice = payload.get("tool_choice")
    if enabled and (choice == "required" or is_json_object(choice)):
        unsupported("tool_choice", "required and named tool choices are rejected in thinking mode")
    output = payload.get("response_format")
    if output is not None and (
        not is_json_object(output) or output.get("type") not in ("text", "json_object")
    ):
        unsupported("response_format", "only text and JSON-object response formats are qualified")
    maximum = payload.get("max_tokens")
    if maximum is not None and (type(maximum) is not int or not 1 <= maximum <= 393216):
        losses.append(
            FieldLoss(
                path("max_tokens"),
                Disposition.APPROXIMATED,
                note="out-of-range max_tokens passes verbatim",
            )
        )
    tools = payload.get("tools")
    if tools is not None:
        supported_tools = is_json_array(tools) and all(
            is_json_object(tool)
            and tool.get("type") == "function"
            and set(tool) <= {"type", "function"}
            and is_json_object(tool.get("function"))
            and set(tool["function"]) <= {"name", "description", "parameters"}
            for tool in tools
        )
        if not supported_tools:
            losses.append(
                FieldLoss(
                    "provider_options[deepseek.chat_completions].tools",
                    Disposition.UNSUPPORTED,
                    note="only documented non-beta function definitions are qualified",
                )
            )
    tool_mode = bool(tools)
    messages = payload.get("messages")
    if not is_json_array(messages):
        losses.append(
            FieldLoss(
                "messages",
                Disposition.UNSUPPORTED,
                note="a message array is required for replay qualification",
            )
        )
        return
    for index, message in enumerate(messages):
        if not is_json_object(message) or message.get("role") != "assistant":
            continue
        if "refusal" in message:
            losses.append(
                FieldLoss(
                    f"messages[{index}].parts[refusal]",
                    Disposition.UNSUPPORTED,
                    note="refusal replay has no qualified lane on this interface",
                )
            )
        has_reasoning = isinstance(message.get("reasoning_content"), str)
        prefix = (
            f"provider_options[{NAMESPACE}].messages[{index}].reasoning_content"
            if "messages" in own
            else f"messages[{index}].parts[reasoning]"
        )
        if tool_mode and not has_reasoning:
            losses.append(
                FieldLoss(
                    prefix,
                    Disposition.UNSUPPORTED,
                    note="all assistant turns with tools require original reasoning_content",
                )
            )
        elif not tool_mode and has_reasoning:
            shifts.append(
                SemanticShift(
                    kind="deepseek.reasoning_ignored",
                    path=prefix,
                    note="provider ignores replayed reasoning when no tools are supplied",
                )
            )
    for index, message in enumerate(request.messages):
        for position, part in enumerate(message.parts):
            if isinstance(part, PartReasoning) and part.text is None:
                losses.append(
                    FieldLoss(
                        f"messages[{index}].parts[{position}].text",
                        Disposition.UNSUPPORTED,
                        note="reasoning replay requires original text; none is synthesized",
                    )
                )
            if isinstance(part, PartText) and part.annotations:
                losses.append(
                    FieldLoss(
                        f"messages[{index}].parts[{position}].annotations",
                        Disposition.UNSUPPORTED,
                        note="citation annotations have no qualified request replay lane",
                    )
                )
        if sum(isinstance(part, PartReasoning) for part in message.parts) > 1:
            shifts.append(
                SemanticShift(
                    kind="deepseek.reasoning_concatenated",
                    path=f"messages[{index}].parts[reasoning]",
                    note="reasoning parts concatenate into one reasoning_content field",
                )
            )


def _unmapped_envelopes(value: Any, path: str, losses: list[FieldLoss]) -> None:
    """Report nested IR envelope intent that the shared mapping does not expand."""
    if isinstance(value, IRObject):
        if path:
            losses.extend(
                FieldLoss(
                    f"{path}.extensions[{key}]",
                    Disposition.UNSUPPORTED,
                    note="nested extension has no qualified wire lane",
                )
                for key in sorted(value.extensions)
            )
            if NAMESPACE in value.provider_options:
                losses.append(
                    FieldLoss(
                        f"{path}.provider_options[{NAMESPACE}]",
                        Disposition.UNSUPPORTED,
                        note="nested provider options are not expanded by this codec",
                    )
                )
        for field in fields(value):
            if field.name not in ("extensions", "provider_options"):
                child = f"{path}.{field.name}" if path else field.name
                _unmapped_envelopes(getattr(value, field.name), child, losses)
    elif is_json_array(value):
        for index, item in enumerate(value):
            _unmapped_envelopes(item, f"{path}[{index}]", losses)
