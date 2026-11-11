"""Qualified DeepSeek frames over the configurable compatible stream machinery."""

from __future__ import annotations

import json
from typing import Any

from ocai.chat.types import ChatChunk
from ocai.chat.types import ChunkType
from ocai.chat.types import DeltaReasoning
from ocai.chat.types import DeltaText
from ocai.chat.types import ErrorInfo
from ocai.chat.types import FinishInfo
from ocai.chat.types import PartToolCall
from ocai.convert.graph import EdgeOutput
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import EdgeReport
from ocai.core.fidelity import FieldLoss
from ocai.core.ir import is_json_array
from ocai.core.ir import is_json_object
from ocai.deepseek.chat_completions.codec import DeepSeekCodec
from ocai.deepseek.chat_completions.evidence import Evidence
from ocai.deepseek.chat_completions.evidence import fields
from ocai.deepseek.chat_completions.evidence import retain
from ocai.deepseek.chat_completions.usage import decode_usage
from ocai.openai.chat_completions.codec import ChatCompletionsStreamTransducer

_FINISH = {"stop": "complete", "length": "max_tokens", "content_filter": "content_filter",
           "tool_calls": "tool_call", "aborted": "error", "insufficient_system_resource": "error"}


def _error(raw: Any = None) -> ChatChunk:
    """Retain an unqualified failure payload without inventing a native error taxonomy."""
    return ChatChunk(type=ChunkType.ERROR, error=ErrorInfo(code="unknown", native=raw),
                     raw_event=raw)


class DeepSeekStreamCodec(DeepSeekCodec):
    """Decode total ordered frame signals; state and terminal validation live below."""

    def decode_frame(self, event: str | None, data: str) -> EdgeOutput:
        """Decode supported frame lanes and preserve every unqualified native field."""
        if data.strip() == "[DONE]":
            return EdgeOutput([])
        try:
            raw: Any = json.loads(data)
        except (ValueError, TypeError):
            return EdgeOutput([_error(data)], (FieldLoss(
                "frame", Disposition.EXTENSIONS, note="invalid JSON retained in error evidence"),))
        if not is_json_object(raw):
            return EdgeOutput([_error(raw)], (FieldLoss(
                "frame", Disposition.EXTENSIONS, note="non-object frame retained in error"),))
        evidence: Evidence = []
        safe = fields(raw, {"id", "model", "created", "object", "system_fingerprint",
                            "choices", "usage", "error"}, "", evidence)
        chunks: list[ChatChunk] = []
        errors: list[ChatChunk] = []
        losses: list[FieldLoss] = []
        choices = safe.get("choices")
        if choices is not None and not is_json_array(choices):
            retain(evidence, "choices", choices)
            errors.append(_error(raw))
        if is_json_array(choices):
            for position, choice in enumerate(choices):
                if not is_json_object(choice) or choice.get("index", 0) != 0:
                    retain(evidence, f"choices[{position}]", choice)
                    continue
                self._choice(choice, raw, chunks, evidence, errors)
        info = self._decode_info(safe)
        malformed_info = bool(info.extensions)
        if "system_fingerprint" in safe:
            info.extensions["deepseek.system_fingerprint"] = safe["system_fingerprint"]
            losses.append(FieldLoss("system_fingerprint", Disposition.EXTENSIONS,
                                    note="provider fingerprint retained as response metadata"))
        if any(safe.get(key) is not None for key in ("id", "model", "created")) or info.extensions:
            index = 1 if chunks and chunks[0].type == ChunkType.STREAM_START else 0
            chunks.insert(index, ChatChunk(type=ChunkType.METADATA, info=info, raw_event=raw))
            if malformed_info:
                losses.append(FieldLoss("response_info", Disposition.EXTENSIONS,
                                        note="malformed response metadata retained"))
        usage = decode_usage(safe.get("usage"), losses)
        if usage is not None:
            chunks.append(ChatChunk(type=ChunkType.USAGE, usage=usage,
                                    usage_cumulative=True, raw_event=raw))
        if safe.get("object", "chat.completion.chunk") != "chat.completion.chunk":
            retain(evidence, "object", safe["object"])
        if event not in (None, "", "message"):
            retain(evidence, "$event", event)
        if "error" in safe or event == "error":
            errors.append(_error(raw))
        if evidence:
            chunks.append(ChatChunk(type=ChunkType.RAW, raw_event=raw,
                                    extensions={"deepseek.stream_unmapped": evidence}))
            losses.append(FieldLoss("unmapped", Disposition.EXTENSIONS,
                                    note="unqualified stream fields retained by source path"))
        chunks.extend(errors)
        return EdgeOutput(chunks, tuple(losses))

    def _choice(self, raw_choice: dict[str, Any], raw: dict[str, Any], chunks: list[ChatChunk],
                evidence: Evidence, errors: list[ChatChunk]) -> None:
        """Split choice zero into reasoning, text, tool, finish and error signals."""
        choice = fields(raw_choice, {"index", "delta", "finish_reason", "logprobs"},
                        "choices[0]", evidence)
        if choice.get("logprobs") is not None:
            retain(evidence, "choices[0].logprobs", choice["logprobs"])
        delta = choice.get("delta")
        if not is_json_object(delta):
            retain(evidence, "choices[0].delta", delta)
            errors.append(_error(raw))
            delta = {}
        delta = fields(delta, {"role", "reasoning_content", "content", "tool_calls"},
                       "choices[0].delta", evidence)
        if delta.get("role") == "assistant":
            chunks.append(ChatChunk(type=ChunkType.STREAM_START, raw_event=raw))
        elif delta.get("role") is not None:
            retain(evidence, "choices[0].delta.role", delta["role"])
        for name, slot in (("reasoning_content", 0), ("content", 1)):
            value = delta.get(name)
            if isinstance(value, str):
                # Unary decoding omits empty content; reasoning is a distinct part even when empty.
                if value or name == "reasoning_content":
                    fragment = DeltaReasoning(text=value) if slot == 0 else DeltaText(text=value)
                    chunks.append(ChatChunk(type=ChunkType.PART_DELTA, index=slot,
                                            delta=fragment, raw_event=raw))
            elif value is not None:
                retain(evidence, f"choices[0].delta.{name}", value)
                errors.append(_error(raw))
        calls = delta.get("tool_calls")
        if is_json_array(calls):
            for position, call in enumerate(calls):
                self._tool(call, position, raw, chunks, evidence, errors)
        elif calls is not None:
            retain(evidence, "choices[0].delta.tool_calls", calls)
            errors.append(_error(raw))
        finish = choice.get("finish_reason")
        if isinstance(finish, str):
            chunks.append(ChatChunk(type=ChunkType.FINISH,
                                    finish=FinishInfo(reason=_FINISH.get(finish, "unknown"),
                                                      native=finish), raw_event=raw))
            if finish in ("aborted", "insufficient_system_resource"):
                errors.append(_error(raw))
        elif finish is not None:
            retain(evidence, "choices[0].finish_reason", finish)
            errors.append(_error(raw))

    def _tool(self, raw_call: Any, position: int, raw: dict[str, Any], chunks: list[ChatChunk],
              evidence: Evidence, errors: list[ChatChunk]) -> None:
        """Reuse compatible tool framing only after validating its partial native shape."""
        path = f"choices[0].delta.tool_calls[{position}]"
        if not is_json_object(raw_call):
            retain(evidence, path, raw_call)
            errors.append(_error(raw))
            return
        call = fields(raw_call, {"index", "id", "type", "function"}, path, evidence)
        function = call.get("function")
        valid = (type(call.get("index")) is int and call["index"] >= 0
                 and call.get("type", "function") == "function" and is_json_object(function))
        if not valid or not is_json_object(function):
            retain(evidence, path, raw_call)
            errors.append(_error(raw))
            return
        function = fields(function, {"name", "arguments"}, path + ".function", evidence)
        if (any(not isinstance(function[key], str) for key in function)
                or ("id" in call and (not isinstance(call["id"], str) or not call["id"]
                                      or not isinstance(function.get("name"), str)))):
            retain(evidence, path, raw_call)
            errors.append(_error(raw))
            return
        if "id" not in call and "name" in function:
            retain(evidence, path, raw_call)
            errors.append(_error(raw))
            return
        call["function"] = function
        mapped: list[ChatChunk] = []
        self._decode_tool_call_frame(call, raw, mapped)
        for chunk in mapped:
            if chunk.index is not None:
                chunk.index += 1  # reason=0, content=1, tools start at 2
        chunks.extend(mapped)


class DeepSeekStreamTransducer(ChatCompletionsStreamTransducer):
    """Use shared slot/sequence machinery with stricter DeepSeek terminal qualification."""

    def __init__(self) -> None:
        super().__init__(DeepSeekStreamCodec())
        self._failed = False
        self._flushed = False

    def _admit(self, chunk: ChatChunk) -> list[ChatChunk]:
        if chunk.type == ChunkType.ERROR:
            self._failed = True
        if chunk.type == ChunkType.PART_START and isinstance(chunk.part, PartToolCall):
            if chunk.index in self._started:
                return self._invalid("tool_order", chunk.raw_event)
        if (chunk.type == ChunkType.PART_DELTA and chunk.index is not None
                and chunk.index >= 2 and chunk.index not in self._started):
            return self._invalid("tool_order", chunk.raw_event)
        return super()._admit(chunk)

    def _invalid(self, path: str, raw: Any = None) -> list[ChatChunk]:
        self._failed = True
        self._losses.append(FieldLoss(path, Disposition.UNSUPPORTED,
                                      note="stream cannot claim complete execution"))
        return [self._stamp(_error(raw))]

    def _terminal(self, sentinel: str) -> list[ChatChunk]:
        if self._done:
            return []
        if self._failed:
            return []
        if self._finish is None or (
            self._finish.reason == "tool_call" and not self._open_tool_slots
        ):
            return self._invalid("termination", sentinel)
        return super()._terminal(sentinel)

    def feed(self, event: Any) -> list[ChatChunk]:
        """Reject trailing data after success; never restart or manufacture completion."""
        if self._done and event.data.strip() != "[DONE]":
            return self._invalid("termination", event.data)
        first_seq = self._seq
        emitted = super().feed(event)
        # Preserve accounting from a multi-signal frame before exposing a failure.
        emitted = ([chunk for chunk in emitted if chunk.type != ChunkType.ERROR]
                   + [chunk for chunk in emitted if chunk.type == ChunkType.ERROR])
        for index, chunk in enumerate(emitted, start=first_seq):
            chunk.seq = index
        distinct: list[FieldLoss] = []
        for loss in self._losses:
            if loss not in distinct:
                distinct.append(loss)
        self._losses = distinct
        return emitted

    def flush(self) -> tuple[list[ChatChunk], EdgeReport]:
        """Preserve terminal evidence on truncation and fail exactly once."""
        if self._flushed:
            raise RuntimeError("stream already flushed")
        self._flushed = True
        tail = [] if self._done or self._failed else self._invalid("termination")
        _, report = super().flush()
        return tail, report
