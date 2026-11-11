"""Preserve future native fields and malformed containers before shared decoding."""

from copy import deepcopy
from datetime import UTC
from datetime import datetime
from typing import Any

from ocai.core.ir import is_json_array
from ocai.core.ir import is_json_object

type Evidence = list[dict[str, Any]]


def retain(evidence: Evidence, path: str, value: Any) -> None:
    """Bank one native value with its exact source location."""
    evidence.append({"path": path, "value": deepcopy(value)})


def fields(raw: dict[str, Any], known: set[str], path: str, evidence: Evidence) -> dict[str, Any]:
    """Copy known fields and retain everything else by path."""
    for key in sorted(raw.keys() - known):
        retain(evidence, f"{path}.{key}" if path else key, raw[key])
    return {key: deepcopy(value) for key, value in raw.items() if key in known}


def tool_calls(raw: Any, path: str, evidence: Evidence) -> list[dict[str, Any]]:
    """Only assert typed tool identity when the native function record is complete."""
    if raw is None:
        return []
    if not is_json_array(raw):
        retain(evidence, path, raw)
        return []
    result: list[dict[str, Any]] = []
    for index, call in enumerate(raw):
        current = f"{path}[{index}]"
        if not is_json_object(call) or call.get("type", "function") != "function":
            retain(evidence, current, call)
            continue
        function = call.get("function")
        if (
            not is_json_object(function)
            or not isinstance(call.get("id"), str)
            or not isinstance(function.get("name"), str)
            or not isinstance(function.get("arguments"), str)
        ):
            retain(evidence, current, call)
            continue
        clean = fields(call, {"id", "type", "function"}, current, evidence)
        clean["function"] = fields(function, {"name", "arguments"}, current + ".function", evidence)
        result.append(clean)
    return result


def response_payload(raw: Any) -> tuple[dict[str, Any], Evidence]:
    """Return a safe compatible response plus native evidence, without manufacturing content."""
    evidence: Evidence = []
    if not is_json_object(raw):
        retain(evidence, "$", raw)
        return {}, evidence
    clean = fields(raw, {"id", "object", "created", "model", "choices", "usage"}, "", evidence)
    for key in ("id", "model"):
        if key in clean and not isinstance(clean[key], str):
            retain(evidence, key, clean.pop(key))
    if "created" in clean:
        timestamp = clean["created"]
        try:
            if type(timestamp) not in (int, float):
                raise ValueError("timestamp must be numeric")
            datetime.fromtimestamp(timestamp, UTC)
        except (ValueError, OverflowError, OSError):
            retain(evidence, "created", clean.pop("created"))
    choices = clean.get("choices")
    if not is_json_array(choices):
        if choices is not None:
            retain(evidence, "choices", choices)
        clean["choices"] = []
        return clean, evidence
    if len(choices) > 1:
        retain(evidence, "choices[1:]", choices[1:])
    if not choices or not is_json_object(choices[0]):
        if choices:
            retain(evidence, "choices[0]", choices[0])
        clean["choices"] = []
        return clean, evidence
    choice = fields(
        choices[0], {"index", "message", "finish_reason", "logprobs"}, "choices[0]", evidence
    )
    finish = choice.get("finish_reason")
    if finish is not None and not isinstance(finish, str):
        retain(evidence, "choices[0].finish_reason", choice.pop("finish_reason"))
    message = choice.get("message")
    if not is_json_object(message):
        retain(evidence, "choices[0].message", message)
        message = {}
    message = fields(
        message,
        {"role", "content", "reasoning_content", "tool_calls"},
        "choices[0].message",
        evidence,
    )
    for key in ("role", "content", "reasoning_content"):
        if key in message and message[key] is not None and not isinstance(message[key], str):
            retain(evidence, "choices[0].message." + key, message.pop(key))
            if key == "role":
                message[key] = "unknown"
    if message.get("role") is None:
        message.pop("role", None)
    calls = tool_calls(message.get("tool_calls"), "choices[0].message.tool_calls", evidence)
    if calls:
        message["tool_calls"] = calls
    else:
        message.pop("tool_calls", None)
    choice["message"] = message
    clean["choices"] = [choice]
    return clean, evidence
