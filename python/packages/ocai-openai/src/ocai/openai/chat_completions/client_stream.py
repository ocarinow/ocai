"""Incremental canonical-to-client semantics, with no HTTP or SSE framing."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from typing import Protocol

from ocai.chat.types import ChatChunk
from ocai.chat.types import ChunkType
from ocai.chat.types import DeltaRefusal
from ocai.chat.types import DeltaText
from ocai.chat.types import DeltaToolArgs
from ocai.chat.types import Part
from ocai.chat.types import PartRefusal
from ocai.chat.types import PartText
from ocai.chat.types import PartToolCall
from ocai.core.errors import StreamProtocolError
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import EdgeReport
from ocai.core.fidelity import FieldLoss
from ocai.core.fidelity import SemanticShift
from ocai.core.finish import FinishInfo
from ocai.core.usage import Usage
from ocai.openai.chat_completions.client import client_finish
from ocai.openai.chat_completions.client import client_usage
from ocai.openai.chat_completions.client import part_evidence
from ocai.openai.chat_completions.codec import CANONICAL_CHUNK
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_CHUNK


class _Digest(Protocol):
    def update(self, data: bytes, /) -> None: ...
    def digest(self) -> bytes: ...


@dataclass
class _Slot:
    kind: str
    checksum: _Digest
    tool_index: int | None = None
    identity: tuple[str, str] | None = None
    closed: bool = False


def _text(part: Part) -> str:
    if isinstance(part, (PartText, PartRefusal)):
        return part.text
    if isinstance(part, PartToolCall):
        return part.args_json
    return ""


def _frame(delta: dict[str, Any], finish: str | None = None) -> dict[str, Any]:
    return {
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }


class ClientStreamTransducer:
    """Map events without buffering response text or tool arguments.

    Only part identities, rolling checksums, finish and usage remain in memory.
    Successful finish/usage frames require a canonical StreamEnd. Flush on abort
    produces evidence but no completion. The gateway emits its DONE framing only
    after it has accepted the conversion report and upstream terminal outcome.
    """

    def __init__(self) -> None:
        """Start a fresh isolated client conversion."""
        self._slots: dict[int, _Slot] = {}
        self._losses: list[FieldLoss] = []
        self._shifts: list[SemanticShift] = []
        self._usage: Usage | None = None
        self._finish: FinishInfo | None = None
        self._done = False
        self._flushed = False
        self._failed = False
        self._started = False
        self._tool_count = 0
        self._textual = False

    def _reject(self, message: str) -> None:
        self._failed = True
        raise StreamProtocolError(message)

    def _loss(self, path: str) -> None:
        self._losses.append(
            FieldLoss(
                path=path,
                disposition=Disposition.UNSUPPORTED,
                note="outside the qualified client stream contract",
            )
        )

    def feed(self, event: Any) -> list[dict[str, Any]]:
        """Convert one canonical chunk into zero or more client JSON events."""
        if self._done or self._flushed or self._failed:
            self._reject("client conversion already terminated")
        if not isinstance(event, ChatChunk):
            self._reject("client conversion requires canonical chunks")
            return []
        if event.info is not None:
            self._loss("chunk.info")
        if event.type == ChunkType.METADATA and event.info is not None:
            if event.extensions or event.provider_options:
                self._loss("chunk.extensions")
            return []
        if event.extensions or event.provider_options:
            self._loss("chunk.extensions")
        if event.type == ChunkType.ERROR:
            self._reject("upstream stream reported failure")
        if event.type == ChunkType.STREAM_START:
            if self._started:
                self._reject("duplicate stream start")
            self._started = True
            return [_frame({"role": "assistant"})]
        if event.type == ChunkType.PART_START:
            return self._start_part(event)
        if event.type == ChunkType.PART_DELTA:
            return self._delta(event)
        if event.type == ChunkType.PART_STOP:
            self._stop_part(event)
            return []
        if event.type == ChunkType.FINISH:
            self._finish = deepcopy(event.finish)
            return []
        if event.type == ChunkType.USAGE:
            if event.usage is not None:
                if event.usage_cumulative is True or self._usage is None:
                    self._usage = deepcopy(event.usage)
                else:
                    self._usage.consumptions.extend(deepcopy(event.usage.consumptions))
            return []
        if event.type == ChunkType.STREAM_STOP:
            if event.end is None:
                self._reject("stream stop has no terminal record")
                return []
            self._done = True
            if event.end.extensions or event.end.provider_options:
                self._loss("chunk.extensions")
            if len(self._slots) > 1 and self._textual:
                self._shifts.append(
                    SemanticShift(
                        kind="relocation",
                        path="message.parts",
                        note="ordered parts grouped into client message lanes",
                    )
                )
            finish = event.end.finish or self._finish
            usage = event.end.usage if event.end.usage is not None else self._usage
            result = [_frame({}, client_finish(finish, self._losses))]
            encoded_usage = client_usage(usage, self._losses)
            if encoded_usage is not None:
                result.append(
                    {"object": "chat.completion.chunk", "choices": [], "usage": encoded_usage}
                )
            return result
        self._loss("chunk.type")
        return []

    def _start_part(self, event: ChatChunk) -> list[dict[str, Any]]:
        if event.index is None or event.part is None or event.index in self._slots:
            self._reject("invalid or duplicate part start")
            return []
        if self._slots and event.index < max(self._slots):
            self._reject("part starts must follow canonical order")
        part = event.part
        path = f"message.parts[{event.index}]"
        part_evidence(part, path, self._losses, streaming=True)
        slot = _Slot(kind=part.type, checksum=sha256(_text(part).encode()))
        self._slots[event.index] = slot
        if isinstance(part, PartToolCall):
            slot.tool_index = self._tool_count
            slot.identity = (part.call_id, part.name)
            self._tool_count += 1
            return [
                _frame(
                    {
                        "tool_calls": [
                            {
                                "index": slot.tool_index,
                                "id": part.call_id,
                                "type": "function",
                                "function": {"name": part.name, "arguments": part.args_json},
                            }
                        ]
                    }
                )
            ]
        if isinstance(part, (PartText, PartRefusal)):
            self._textual = True
            if part.text:
                return [_frame({"content" if isinstance(part, PartText) else "refusal": part.text})]
            return []
        self._loss(path)
        return []

    def _delta(self, event: ChatChunk) -> list[dict[str, Any]]:
        slot = self._slots.get(event.index) if event.index is not None else None
        if slot is None or slot.closed:
            self._reject("delta has no open part")
            return []
        delta = event.delta
        if delta is not None and (delta.extensions or delta.provider_options):
            self._loss("chunk.delta")
        if isinstance(delta, DeltaToolArgs) and slot.tool_index is not None:
            slot.checksum.update(delta.fragment.encode())
            return [
                _frame(
                    {
                        "tool_calls": [
                            {"index": slot.tool_index, "function": {"arguments": delta.fragment}}
                        ]
                    }
                )
            ]
        if isinstance(delta, (DeltaText, DeltaRefusal)) and slot.kind == delta.type:
            slot.checksum.update(delta.text.encode())
            return [_frame({"content" if isinstance(delta, DeltaText) else "refusal": delta.text})]
        self._loss("chunk.delta")
        return []

    def _stop_part(self, event: ChatChunk) -> None:
        slot = self._slots.get(event.index) if event.index is not None else None
        if slot is None or slot.closed:
            self._reject("part stop has no open part")
            return
        part = event.part
        if part is not None:
            evidence: list[FieldLoss] = []
            part_evidence(part, f"message.parts[{event.index}]", evidence)
            self._losses.extend(loss for loss in evidence if loss not in self._losses)
            if part.type != slot.kind or sha256(_text(part).encode()).digest() != (
                slot.checksum.digest()
            ):
                self._reject("final part differs from delivered deltas")
            if isinstance(part, PartToolCall) and slot.identity != (part.call_id, part.name):
                self._reject("final tool identity differs from delivered identity")
        slot.closed = True

    def flush(self) -> tuple[list[dict[str, Any]], EdgeReport]:
        """Finalize evidence exactly once, never synthesize a successful terminal."""
        if self._flushed:
            raise RuntimeError("client conversion already flushed")
        self._flushed = True
        if not self._done or self._failed:
            self._loss("termination")
        return [], EdgeReport(
            src=CANONICAL_CHUNK,
            dst=CHAT_COMPLETIONS_CHUNK,
            losses=tuple(self._losses),
            shifts=tuple(self._shifts),
        )
