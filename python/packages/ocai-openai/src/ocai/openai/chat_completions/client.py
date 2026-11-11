"""Pure client-facing Chat Completions mappings; serving and framing stay outside."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from ocai.chat.types import ChatResponse
from ocai.chat.types import Part
from ocai.chat.types import PartRefusal
from ocai.chat.types import PartText
from ocai.chat.types import PartToolCall
from ocai.convert.graph import EdgeOutput
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import FieldLoss
from ocai.core.fidelity import SemanticShift
from ocai.core.finish import FinishInfo
from ocai.core.ir import IRObject
from ocai.core.refs import ProviderRef
from ocai.core.refs import RefScope
from ocai.core.usage import Usage

_FINISH = {
    "complete": "stop",
    "stop_sequence": "stop",
    "max_tokens": "length",
    "tool_call": "tool_calls",
    "content_filter": "content_filter",
}


@dataclass(frozen=True)
class ClientMetadata:
    """Explicit gateway serving identity, never invented provider provenance."""

    id: str
    model: str
    created: int

    def bind(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Bind serving metadata to a detached response or chunk document."""
        return {**deepcopy(payload), "id": self.id, "model": self.model, "created": self.created}


def _loss(
    losses: list[FieldLoss],
    path: str,
    disposition: Disposition = Disposition.DROPPED,
    note: str = "no lane in the qualified client contract",
) -> None:
    losses.append(FieldLoss(path=path, disposition=disposition, note=note))


def _extras(value: IRObject, path: str, losses: list[FieldLoss]) -> None:
    if value.extensions:
        _loss(losses, f"{path}.extensions")


def _ref_valid(ref: ProviderRef) -> bool:
    return (
        ref.provider == "openai"
        and ref.scope != RefScope.MODEL
        and (ref.interface == "chat_completions" or ref.scope == RefScope.PROVIDER)
    )


def part_evidence(
    part: Part, path: str, losses: list[FieldLoss], *, streaming: bool = False
) -> None:
    """Report part metadata with no client lane, including scoped anchors."""
    _extras(part, path, losses)
    if part.anchor is not None:
        _loss(
            losses,
            f"{path}.anchor",
            Disposition.DROPPED if _ref_valid(part.anchor) else Disposition.UNSUPPORTED,
        )
    if part.id is not None:
        _loss(losses, f"{path}.id")
    if part.cache_hint is not None:
        _loss(losses, f"{path}.cache_hint")
    if isinstance(part, PartText) and part.annotations:
        _loss(losses, f"{path}.annotations")
    if isinstance(part, PartToolCall):
        if part.status != "input_complete" and not (streaming and part.status == "input_streaming"):
            _loss(losses, f"{path}.status", Disposition.UNSUPPORTED)
        if part.executed_by != "client":
            _loss(losses, f"{path}.executed_by", Disposition.UNSUPPORTED)


def client_finish(finish: FinishInfo | None, losses: list[FieldLoss]) -> str | None:
    """Map finish semantics while retaining unknown native values with findings."""
    if finish is None:
        return None
    _extras(finish, "finish", losses)
    if finish.detail:
        _loss(losses, "finish.detail")
    reason = _FINISH.get(finish.reason)
    if reason is None:
        _loss(losses, "finish.reason", Disposition.UNSUPPORTED)
        return finish.native or finish.reason
    if finish.native is not None and finish.native != reason:
        _loss(losses, "finish.native", Disposition.RENAMED, "mapped by canonical finish meaning")
    return reason


def client_usage(usage: Usage | None, losses: list[FieldLoss]) -> dict[str, Any] | None:
    """Invert disjoint token buckets without inventing missing measurements."""
    if usage is None:
        return None
    _extras(usage, "usage", losses)
    buckets: dict[str, int] = {}
    for i, item in enumerate(usage.consumptions):
        if (
            item.unit != "tokens"
            or item.modality != "text"
            or item.source not in {"input", "output", "cached", "reasoning"}
            or not isinstance(item.value, int)
            or isinstance(item.value, bool)
        ):
            _loss(losses, f"usage.consumptions[{i}]", Disposition.UNSUPPORTED)
            continue
        buckets[item.source] = buckets.get(item.source, 0) + item.value
    result: dict[str, Any] = {}
    if "input" in buckets:
        result["prompt_tokens"] = buckets["input"] + buckets.get("cached", 0)
    if "output" in buckets:
        result["completion_tokens"] = buckets["output"] + buckets.get("reasoning", 0)
    if "prompt_tokens" in result and "completion_tokens" in result:
        result["total_tokens"] = result["prompt_tokens"] + result["completion_tokens"]
    if "cached" in buckets:
        result["prompt_tokens_details"] = {"cached_tokens": buckets["cached"]}
    if "reasoning" in buckets:
        result["completion_tokens_details"] = {"reasoning_tokens": buckets["reasoning"]}
    return result or None


def encode_response(response: ChatResponse) -> EdgeOutput:
    """Convert canonical response semantics; callers explicitly bind serving metadata."""
    losses: list[FieldLoss] = []
    shifts: list[SemanticShift] = []
    message: dict[str, Any] = {"role": "assistant", "content": None}
    text: list[str] = []
    refusal: list[str] = []
    calls: list[dict[str, Any]] = []
    if response.message.role not in {"model", "assistant"}:
        _loss(losses, "message.role", Disposition.UNSUPPORTED)
    for i, part in enumerate(response.message.parts):
        path = f"message.parts[{i}]"
        part_evidence(part, path, losses)
        if isinstance(part, PartText):
            text.append(part.text)
        elif isinstance(part, PartRefusal):
            refusal.append(part.text)
        elif isinstance(part, PartToolCall):
            calls.append(
                {
                    "id": part.call_id,
                    "type": "function",
                    "function": {"name": part.name, "arguments": part.args_json},
                }
            )
        else:
            _loss(losses, path, Disposition.UNSUPPORTED)
    if text:
        message["content"] = "".join(text)
    if refusal:
        message["refusal"] = "".join(refusal)
    if calls:
        message["tool_calls"] = calls
    if len(response.message.parts) > 1 and (text or refusal):
        shifts.append(
            SemanticShift(
                kind="relocation",
                path="message.parts",
                note="ordered parts grouped into client message lanes",
            )
        )
    _extras(response.message, "message", losses)
    _extras(response, "response", losses)
    result: dict[str, Any] = {
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": client_finish(response.finish, losses),
            }
        ],
    }
    usage = client_usage(response.usage, losses)
    if usage is not None:
        result["usage"] = usage
    info = response.info
    if info is not None:
        _extras(info, "info", losses)
        if info.id is not None:
            if _ref_valid(info.id):
                result["id"] = info.id.id
            else:
                _loss(losses, "info.id", Disposition.UNSUPPORTED)
        if info.model is not None:
            result["model"] = info.model
        if info.created is not None:
            if info.created.tzinfo is None or info.created.microsecond:
                _loss(losses, "info.created", Disposition.UNSUPPORTED)
            else:
                result["created"] = int(info.created.timestamp())
    return EdgeOutput(result, tuple(losses), tuple(shifts))
