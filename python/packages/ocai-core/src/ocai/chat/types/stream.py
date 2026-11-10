"""The canonical streaming surface (architecture §3.1, `types/stream.py`).

One event type — `ChatChunk` — carries every streamed occurrence; its `type`
says which optional lanes are populated. The typed `Delta` union mirrors the
part algebra one-to-one, and the **streaming-first ratchet** is normative:
no new part type is admissible without its delta type, its fold law here,
and paired chunks/response fixtures in the same change.

The fold law (normative): `complete(request) == fold(stream(request))`.
`StreamAccumulator.fold` is that law's executable half — the conformance
harness runs fold triples (wire event log → canonical chunks → folded
response) against it with `canonjson.semantic_equal`.

Streams end with a terminal `STREAM_STOP` chunk carrying `StreamEnd(usage,
finish, report)` — the authoritative usage/finish and the stream's
`FidelityReport` (its one home on the streaming path). Mid-stream errors
have a *wire shape* (`ErrorInfo`), not just a Python exception, so a
recorded stream replays identically to a live one.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import ClassVar
from typing import Final
from typing import Literal
from typing import Self

from ocai.chat.canonical import CANONICAL_CHAT_CHUNK
from ocai.chat.canonical import CANONICAL_CHAT_RESPONSE
from ocai.chat.types.annotations import Annotation
from ocai.chat.types.finish import FinishInfo
from ocai.chat.types.message import Message
from ocai.chat.types.parts import Part
from ocai.chat.types.parts import PartReasoning
from ocai.chat.types.parts import PartRefusal
from ocai.chat.types.parts import PartText
from ocai.chat.types.parts import PartToolCall
from ocai.chat.types.parts import ToolCallStatus
from ocai.chat.types.parts import cast_part
from ocai.chat.types.response import ChatResponse
from ocai.chat.types.role import Role
from ocai.chat.types.usage import Usage
from ocai.core.errors import StreamProtocolError
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import EdgeReport
from ocai.core.fidelity import FidelityReport
from ocai.core.fidelity import FieldLoss
from ocai.core.identity import NodeId
from ocai.core.ir import IRObject
from ocai.core.ir import TagRegistry
from ocai.core.ir import is_json_object

# The censused extension key sealed onto every part an aborted stream left
# open (no terminal STREAM_STOP arrived): the part's content is whatever had
# accumulated when the stream died, explicitly marked rather than silently
# passed off as complete. Registered in spec/extensions/.
INCOMPLETE_EXTENSION: Final = "ocai.incomplete"

# The censused extension key preserving accumulated reasoning-signature
# fragments on a sealed part when no codec-minted `ProviderRef` arrived: the
# accumulator has no (provider, interface) context to mint one, so the
# verbatim concatenation rides the bag — recoverable, never dropped.
# Registered in spec/extensions/.
SIGNATURE_BUFFER_EXTENSION: Final = "ocai.signature_buffer"


class ChunkType(str, Enum):
    """The kind of a streamed `ChatChunk` event.

    The wire vocabulary of the canonical chunk stream. `STREAM_STOP` is the
    terminal event and carries `ChatChunk.end` — a stream that ends without
    one was aborted, and the accumulator seals its parts `incomplete`.

    Attributes:
        STREAM_START: The stream has begun.
        STREAM_STOP: The terminal event; carries the authoritative
            `StreamEnd`.
        PART_START: A new content part is starting; carries the part
            skeleton in `ChatChunk.part`.
        PART_DELTA: An incremental update; carries `ChatChunk.delta`.
        PART_STOP: The current part is complete; may carry the final part,
            which MUST equal the delta accumulation (fold law).
        USAGE: A usage update; `ChatChunk.usage_cumulative` says whether it
            replaces or extends previous updates.
        FINISH: The generation finished; carries `ChatChunk.finish`.
        METADATA: A metadata-bearing event.
        ERROR: A mid-stream error; carries the wire-shaped
            `ChatChunk.error`.
        RAW: An untouched provider event passed through.
        PING: A keep-alive ping.
    """

    STREAM_START = "streamStart"
    STREAM_STOP = "streamStop"
    PART_START = "partStart"
    PART_DELTA = "partDelta"
    PART_STOP = "partStop"
    USAGE = "usage"
    FINISH = "finish"
    METADATA = "metadata"
    ERROR = "error"
    RAW = "raw"
    PING = "ping"


class DeltaType(str, Enum):
    """Canonical discriminator tags for the core `Delta` variants.

    Constants for the tags core ships — the union stays open through
    `DELTA_REGISTRY` (unknown tags decode to `DeltaUnknown`).

    Attributes:
        UNDEFINED: No delta kind set (the unknown/placeholder tag).
        TEXT: A text fragment (`DeltaText`).
        TOOL_ARGS: A tool-argument string fragment (`DeltaToolArgs`).
        REASONING: A reasoning fragment (`DeltaReasoning`).
        SIGNATURE: A reasoning-signature fragment (`DeltaSignature`).
        ANNOTATION: A completed citation (`DeltaAnnotation`).
        REFUSAL: A refusal-text fragment (`DeltaRefusal`).
        BLOB: A binary/base64 media fragment (`DeltaBlob`).
    """

    UNDEFINED = "undefined"
    TEXT = "text"
    TOOL_ARGS = "tool_args"
    REASONING = "reasoning"
    SIGNATURE = "signature"
    ANNOTATION = "annotation"
    REFUSAL = "refusal"
    BLOB = "blob"


@dataclass
class DeltaText(IRObject):
    """A text fragment appended to the open `PartText`.

    Attributes:
        text: The fragment, appended verbatim.
        type: The delta discriminator, fixed to `DeltaType.TEXT`.
    """

    text: str = ""
    type: Literal[DeltaType.TEXT] = field(default=DeltaType.TEXT)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `DeltaText` from a serialized dict, totally.

        Args:
            data: A mapping with `text` and the common IR envelope keys.

        Returns:
            The decoded `DeltaText`.
        """
        return cls(text=data.get("text", ""), **cls._from_dict_common(data))


@dataclass
class DeltaToolArgs(IRObject):
    """A tool-argument fragment appended to the open `PartToolCall`.

    The fragment is a **raw string** — every interface streams argument
    JSON as string pieces — concatenated onto `args_json` and parsed once,
    at `PART_STOP`, never per-fragment (fragments are rarely valid JSON on
    their own).

    Attributes:
        fragment: The raw argument-string fragment, appended verbatim.
        type: The delta discriminator, fixed to `DeltaType.TOOL_ARGS`.
    """

    fragment: str = ""
    type: Literal[DeltaType.TOOL_ARGS] = field(default=DeltaType.TOOL_ARGS)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `DeltaToolArgs` from a serialized dict, totally.

        Args:
            data: A mapping with `fragment` and the common IR envelope
                keys.

        Returns:
            The decoded `DeltaToolArgs`.
        """
        return cls(fragment=data.get("fragment", ""), **cls._from_dict_common(data))


@dataclass
class DeltaReasoning(IRObject):
    """A reasoning fragment appended to the open `PartReasoning`.

    Mirrors the part's two textual lanes: raw thinking text and provider
    summaries stream independently on some interfaces.

    Attributes:
        text: A raw reasoning-text fragment, when streamed.
        summary: A summary fragment, when streamed.
        type: The delta discriminator, fixed to `DeltaType.REASONING`.
    """

    text: str | None = None
    summary: str | None = None
    type: Literal[DeltaType.REASONING] = field(default=DeltaType.REASONING)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `DeltaReasoning` from a serialized dict, totally.

        Args:
            data: A mapping with the optional `text`/`summary` and the
                common IR envelope keys.

        Returns:
            The decoded `DeltaReasoning`.
        """
        return cls(
            text=data.get("text"),
            summary=data.get("summary"),
            **cls._from_dict_common(data),
        )


@dataclass
class DeltaSignature(IRObject):
    """A reasoning-signature fragment for the open `PartReasoning`.

    Signatures (Anthropic `signature_delta`, Gemini `thoughtSignature`)
    stream as opaque string fragments; the codec's transducer mints the
    final `ProviderRef` on the sealed part.

    Attributes:
        signature: The signature fragment, verbatim.
        type: The delta discriminator, fixed to `DeltaType.SIGNATURE`.
    """

    signature: str = ""
    type: Literal[DeltaType.SIGNATURE] = field(default=DeltaType.SIGNATURE)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `DeltaSignature` from a serialized dict, totally.

        Args:
            data: A mapping with `signature` and the common IR envelope
                keys.

        Returns:
            The decoded `DeltaSignature`.
        """
        return cls(signature=data.get("signature", ""), **cls._from_dict_common(data))


@dataclass
class DeltaAnnotation(IRObject):
    """A completed citation appended to the open `PartText`.

    Annotations arrive whole (providers emit them as units, not fragments)
    and are appended to the part's `annotations` list in arrival order.

    Attributes:
        annotation: The completed span-anchored citation.
        type: The delta discriminator, fixed to `DeltaType.ANNOTATION`.
    """

    annotation: Annotation | None = None
    type: Literal[DeltaType.ANNOTATION] = field(default=DeltaType.ANNOTATION)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `DeltaAnnotation` from a serialized dict, totally.

        Args:
            data: A mapping with the nested `annotation` and the common IR
                envelope keys.

        Returns:
            The decoded `DeltaAnnotation`.
        """
        annotation = data.get("annotation")
        return cls(
            annotation=Annotation.from_dict(annotation) if is_json_object(annotation) else None,
            **cls._from_dict_common(data),
        )


@dataclass
class DeltaRefusal(IRObject):
    """A refusal-text fragment appended to the open `PartRefusal`.

    Attributes:
        text: The fragment, appended verbatim.
        type: The delta discriminator, fixed to `DeltaType.REFUSAL`.
    """

    text: str = ""
    type: Literal[DeltaType.REFUSAL] = field(default=DeltaType.REFUSAL)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `DeltaRefusal` from a serialized dict, totally.

        Args:
            data: A mapping with `text` and the common IR envelope keys.

        Returns:
            The decoded `DeltaRefusal`.
        """
        return cls(text=data.get("text", ""), **cls._from_dict_common(data))


@dataclass
class DeltaBlob(IRObject):
    """A base64 media fragment appended to the open media part.

    Streams audio/image output (e.g. OpenAI audio deltas) as base64 string
    pieces; the sealed part's inline `SourceBase64` is their concatenation.

    Attributes:
        data: The base64 fragment, appended verbatim.
        type: The delta discriminator, fixed to `DeltaType.BLOB`.
    """

    data: str = ""
    type: Literal[DeltaType.BLOB] = field(default=DeltaType.BLOB)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `DeltaBlob` from a serialized dict, totally.

        Args:
            data: A mapping with the base64 `data` and the common IR
                envelope keys.

        Returns:
            The decoded `DeltaBlob`.
        """
        return cls(data=data.get("data", ""), **cls._from_dict_common(data))


@dataclass
class DeltaUnknown(IRObject):
    """Decoder fallback for a delta tag this revision does not know.

    Preserves the payload verbatim, mirroring `PartUnknown` — a future
    canonical delta survives decode/encode untouched. Total decode's
    safety net for the streaming lane.

    Attributes:
        data: The verbatim serialized payload, including its original tag.
        type: The unrecognized discriminator value, preserved verbatim.
    """

    data: dict[str, Any] = field(default_factory=dict[str, Any])
    type: str = DeltaType.UNDEFINED.value

    def to_dict(self) -> dict[str, Any]:
        """Serialize back to the verbatim payload this instance preserved.

        Returns:
            A copy of the original serialized mapping, untouched.
        """
        return dict(self.data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Preserve an unrecognized delta payload verbatim.

        Args:
            data: The serialized mapping whose tag no registered delta
                matched.

        Returns:
            A new `DeltaUnknown` carrying the payload untouched.
        """
        tag = data.get("type")
        return cls(
            data=dict(data),
            type=tag if isinstance(tag, str) else DeltaType.UNDEFINED.value,
        )


type Delta = (
    DeltaText
    | DeltaToolArgs
    | DeltaReasoning
    | DeltaSignature
    | DeltaAnnotation
    | DeltaRefusal
    | DeltaBlob
    | DeltaUnknown
)

# The open registry for the Delta union. Unknown tags fall back to
# DeltaUnknown — decoding a delta never raises.
DELTA_REGISTRY: TagRegistry[Any] = TagRegistry(unknown=DeltaUnknown)
DELTA_REGISTRY.register(DeltaType.TEXT.value, DeltaText)
DELTA_REGISTRY.register(DeltaType.TOOL_ARGS.value, DeltaToolArgs)
DELTA_REGISTRY.register(DeltaType.REASONING.value, DeltaReasoning)
DELTA_REGISTRY.register(DeltaType.SIGNATURE.value, DeltaSignature)
DELTA_REGISTRY.register(DeltaType.ANNOTATION.value, DeltaAnnotation)
DELTA_REGISTRY.register(DeltaType.REFUSAL.value, DeltaRefusal)
DELTA_REGISTRY.register(DeltaType.BLOB.value, DeltaBlob)


def cast_delta(data: dict[str, Any]) -> Delta:
    """Decode a serialized delta into its concrete `Delta` variant.

    Dispatches on the `type` tag via `DELTA_REGISTRY`; unknown tags decode
    to `DeltaUnknown` — this function never raises on unknown input.

    Args:
        data: The serialized delta mapping, including its `type`
            discriminator.

    Returns:
        The decoded `Delta` variant.
    """
    decoded: Delta = DELTA_REGISTRY.decode(data)
    return decoded


@dataclass(frozen=True, slots=True)
class ErrorInfo:
    """A mid-stream error in wire shape — data, not just an exception.

    Carried on `ChatChunk.error` so a recorded stream replays identically
    to a live one; the driver *also* raises the mapped taxonomy exception,
    but the stream's own record is this value.

    Attributes:
        code: The canonical error-taxonomy code (`"rate_limit"`, `"auth"`,
            `"context_length"`, `"content_filter"`, `"transient"`,
            `"unknown"`), open.
        native: The provider's verbatim error payload.
        retryable: Whether retrying the call could succeed, when the
            taxonomy mapping knows.
    """

    code: str
    native: Any | None = None
    retryable: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the error to a plain JSON-compatible dict.

        Returns:
            A dict with `code` and the optional `native`/`retryable` when
            set.
        """
        out: dict[str, Any] = {"code": self.code}
        if self.native is not None:
            out["native"] = self.native
        if self.retryable is not None:
            out["retryable"] = self.retryable
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build an `ErrorInfo` from a serialized dict, totally.

        Args:
            data: A mapping with `code` and the optional
                `native`/`retryable`.

        Returns:
            The decoded `ErrorInfo`.
        """
        return cls(
            code=data.get("code", "unknown"),
            native=data.get("native"),
            retryable=data.get("retryable"),
        )


@dataclass
class StreamEnd(IRObject):
    """The authoritative terminal record of a stream.

    Carried by the `STREAM_STOP` chunk. Its `usage` and `finish` override
    any mid-stream updates in the fold, and `report` is the stream's
    `FidelityReport` — the streaming path's one report home, mirroring
    `CallResult.report` on the blocking path.

    Attributes:
        usage: The final consumption record, when reported.
        finish: The final stop record, when reported.
        report: The fidelity account of the stream's conversion legs.
    """

    usage: Usage | None = None
    finish: FinishInfo | None = None
    report: FidelityReport | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `StreamEnd` from a serialized dict, totally.

        Args:
            data: A mapping with the nested `usage`/`finish`/`report` and
                the common IR envelope keys.

        Returns:
            The decoded `StreamEnd`.
        """
        usage = data.get("usage")
        finish = data.get("finish")
        report = data.get("report")
        return cls(
            usage=Usage.from_dict(usage) if is_json_object(usage) else None,
            finish=FinishInfo.from_dict(finish) if is_json_object(finish) else None,
            report=FidelityReport.from_dict(report) if is_json_object(report) else None,
            **cls._from_dict_common(data),
        )


@dataclass
class ChatChunk(IRObject):
    """The one canonical streaming event — every provider frame becomes one.

    Emitted by dialect codecs (via `StreamEdge` transducers in the graph),
    consumed by user code through `ChatStream`/`AsyncChatStream`, and folded
    into a `ChatResponse` by `StreamAccumulator`. `type` says which lanes
    are populated; everything else is None.

    Attributes:
        type: The event kind; unknown wire kinds decode to their verbatim
            string (total decode).
        seq: The chunk's zero-based position in the canonical stream,
            stamped by the emitting codec — the replay/fold ordering key.
        index: The content-part slot this event concerns, for the
            `PART_*` types.
        part: The part skeleton (`PART_START`) or authoritative final part
            (`PART_STOP`).
        delta: The incremental update (`PART_DELTA`).
        usage: A consumption update (`USAGE`).
        usage_cumulative: Whether `usage` replaces (True) or extends
            (False) previous updates; None when unspecified.
        finish: The stop record (`FINISH`).
        error: The wire-shaped mid-stream error (`ERROR`).
        end: The authoritative terminal record (`STREAM_STOP`).
        raw_event: The untouched provider frame this chunk was decoded
            from, for power users and the wiretap archive. Keyword-only.
    """

    object: ClassVar[str] = "chat.chunk"
    __node__: ClassVar[NodeId] = CANONICAL_CHAT_CHUNK

    type: ChunkType | str
    seq: int | None = None
    index: int | None = None
    part: Part | None = None
    delta: Delta | None = None
    usage: Usage | None = None
    usage_cumulative: bool | None = None
    finish: FinishInfo | None = None
    error: ErrorInfo | None = None
    end: StreamEnd | None = None
    raw_event: Any | None = field(default=None, kw_only=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `ChatChunk` from a serialized dict, totally.

        An unknown `type` string is preserved verbatim rather than raised
        on; every nested lane decodes through its own total decoder.

        Args:
            data: A mapping with `type` and any populated lanes plus the
                common IR envelope keys.

        Returns:
            The decoded `ChatChunk`.
        """
        raw_type = data.get("type", "")
        try:
            chunk_type: ChunkType | str = ChunkType(raw_type)
        except ValueError:
            chunk_type = raw_type
        part = data.get("part")
        delta = data.get("delta")
        usage = data.get("usage")
        finish = data.get("finish")
        error = data.get("error")
        end = data.get("end")
        return cls(
            type=chunk_type,
            seq=data.get("seq"),
            index=data.get("index"),
            part=cast_part(part) if is_json_object(part) else None,
            delta=cast_delta(delta) if is_json_object(delta) else None,
            usage=Usage.from_dict(usage) if is_json_object(usage) else None,
            usage_cumulative=data.get("usage_cumulative"),
            finish=FinishInfo.from_dict(finish) if is_json_object(finish) else None,
            error=ErrorInfo.from_dict(error) if is_json_object(error) else None,
            end=StreamEnd.from_dict(end) if is_json_object(end) else None,
            raw_event=data.get("raw_event"),
            **cls._from_dict_common(data),
        )


class StreamAccumulator:
    """Folds a canonical chunk stream into the equivalent `ChatResponse`.

    The executable half of the fold law: `fold(stream(request))` must be
    semantically equal to `complete(request)`, and `PART_STOP`'s final part
    must equal its delta accumulation — the conformance harness asserts
    both over fold-triple fixtures.

    Mechanics per chunk type: `PART_START` opens a *slot* holding the part
    skeleton; `PART_DELTA` applies the typed delta to the open slot
    (append semantics per delta type); `PART_STOP` *seals* the slot,
    preferring the authoritative final part when the codec sent one;
    `USAGE`/`FINISH` track the latest mid-stream records; `STREAM_STOP`
    records the authoritative `StreamEnd`, which overrides them.

    The fold has its own honesty channel: a delta it cannot apply (a
    mismatched delta/part pair, a `DeltaUnknown`, an unaccumulated blob) is
    never silently swallowed — each records a `FieldLoss`, surfaced as one
    `EdgeReport` via `report` and merged into the terminal
    `StreamEnd.report` at `finalize`.

    Use it incrementally (`feed` per chunk, then `finalize`) or in one shot
    via the `fold` classmethod.
    """

    def __init__(self) -> None:
        """Create an empty accumulator ready to receive a stream."""
        self._slots: dict[int, Part] = {}
        self._order: list[int] = []
        self._sealed: set[int] = set()
        self._signatures: dict[int, str] = {}
        self._losses: list[FieldLoss] = []
        self._usage: Usage | None = None
        self._finish: FinishInfo | None = None
        self._error: ErrorInfo | None = None
        self._end: StreamEnd | None = None
        self._reported = False

    def feed(self, chunk: ChatChunk) -> None:
        """Apply one chunk to the accumulation state.

        Args:
            chunk: The next canonical chunk, in `seq` order.
        """
        if chunk.type == ChunkType.PART_START:
            self._start(chunk)
        elif chunk.type == ChunkType.PART_DELTA:
            self._apply_delta(chunk)
        elif chunk.type == ChunkType.PART_STOP:
            self._seal(chunk)
        elif chunk.type == ChunkType.USAGE:
            # TODO: non-cumulative usage updates need summing, not
            # replacement; today every recorded provider reports cumulative.
            self._usage = chunk.usage or self._usage
        elif chunk.type == ChunkType.FINISH:
            self._finish = chunk.finish or self._finish
        elif chunk.type == ChunkType.ERROR:
            self._error = chunk.error
        elif chunk.type == ChunkType.STREAM_STOP:
            self._end = chunk.end
        # STREAM_START / METADATA / RAW / PING carry no fold state.

    def _start(self, chunk: ChatChunk) -> None:
        """Open the slot at `chunk.index` with the part skeleton.

        Args:
            chunk: The `PART_START` chunk carrying the skeleton.
        """
        index = chunk.index if chunk.index is not None else len(self._order)
        skeleton: Part = chunk.part if chunk.part is not None else PartText()
        if index not in self._slots:
            self._order.append(index)
        self._slots[index] = skeleton
        if isinstance(skeleton, PartToolCall):
            skeleton.status = ToolCallStatus.INPUT_STREAMING

    def _apply_delta(self, chunk: ChatChunk) -> None:
        """Apply the chunk's typed delta to its open slot.

        Append semantics per delta type — the fold law's per-part half:
        the sealed part must equal the concatenation applied here.

        Args:
            chunk: The `PART_DELTA` chunk carrying the delta.
        """
        index = chunk.index if chunk.index is not None else (self._order[-1] if self._order else 0)
        part = self._slots.get(index)
        delta = chunk.delta
        if delta is None:
            return
        if part is None:
            # Tolerate streams that skip PART_START: open an implicit slot.
            self._start(ChatChunk(type=ChunkType.PART_START, index=index))
            part = self._slots[index]
        if isinstance(delta, DeltaText) and isinstance(part, PartText):
            part.text += delta.text
        elif isinstance(delta, DeltaToolArgs) and isinstance(part, PartToolCall):
            part.args_json += delta.fragment
        elif isinstance(delta, DeltaReasoning) and isinstance(part, PartReasoning):
            if delta.text is not None:
                part.text = (part.text or "") + delta.text
            if delta.summary is not None:
                part.summary = (part.summary or "") + delta.summary
        elif isinstance(delta, DeltaAnnotation) and isinstance(part, PartText):
            if delta.annotation is not None:
                part.annotations.append(delta.annotation)
        elif isinstance(delta, DeltaRefusal) and isinstance(part, PartRefusal):
            part.text += delta.text
        elif isinstance(delta, DeltaSignature) and isinstance(part, PartReasoning):
            # Signature fragments buffer as an opaque string per slot; the
            # codec's transducer is the only party with the (provider,
            # interface) context to mint a ProviderRef, so `_seal` prefers a
            # codec-minted `signature` on the final part and otherwise
            # preserves the buffer verbatim in the extensions bag.
            self._signatures[index] = self._signatures.get(index, "") + delta.signature
        elif isinstance(delta, DeltaBlob):
            # TODO: accumulate base64 fragments into the media part's
            # SourceBase64 once an audio-output edge exercises this path.
            # Until then the drop is reported, never silent.
            self._lose(
                index,
                f"blob delta not accumulated into {self._part_tag(part)!r} "
                "(no audio-output edge exercises this path yet); fragment dropped",
            )
        else:
            self._lose(
                index,
                f"delta {self._delta_tag(delta)!r} does not apply to open part "
                f"{self._part_tag(part)!r}; delta dropped",
            )

    @staticmethod
    def _delta_tag(delta: Delta) -> str:
        """Return the delta's discriminator tag as a plain string.

        Args:
            delta: The delta whose tag is wanted.

        Returns:
            The verbatim tag (`"text"`, an unknown tag, …).
        """
        tag = delta.type
        return tag.value if isinstance(tag, Enum) else tag

    @staticmethod
    def _part_tag(part: Part) -> str:
        """Return the part's discriminator tag as a plain string.

        Args:
            part: The part whose tag is wanted.

        Returns:
            The verbatim tag (`"text"`, an unknown tag, …).
        """
        tag = part.type
        return tag.value if isinstance(tag, Enum) else tag

    def _lose(
        self,
        index: int,
        note: str,
        *,
        disposition: Disposition = Disposition.DROPPED,
        severity: float = 1.0,
    ) -> None:
        """Record one fold loss on the accumulator's honesty channel.

        Args:
            index: The content-part slot the loss concerns.
            note: The human-readable explanation.
            disposition: What happened to the data.
            severity: The diagnostic information-cost weight.
        """
        self._losses.append(
            FieldLoss(
                path=f"message.parts[{index}]",
                disposition=disposition,
                severity=severity,
                note=note,
            )
        )

    def _seal(self, chunk: ChatChunk) -> None:
        """Seal the slot at `chunk.index`.

        The authoritative final part on the chunk wins when present (the
        fold law requires it to equal the accumulation — asserting that is
        the conformance harness's job, not the fold's). A sealed tool call
        advances to `INPUT_COMPLETE`, and any buffered signature fragments
        settle per `_settle_signature`.

        Args:
            chunk: The `PART_STOP` chunk, optionally carrying the final
                part.
        """
        index = chunk.index if chunk.index is not None else (self._order[-1] if self._order else 0)
        if chunk.part is not None:
            if index not in self._slots:
                self._order.append(index)
            self._slots[index] = chunk.part
        part = self._slots.get(index)
        if isinstance(part, PartToolCall) and part.status == ToolCallStatus.INPUT_STREAMING:
            part.status = ToolCallStatus.INPUT_COMPLETE
        self._sealed.add(index)
        self._settle_signature(index)

    def _settle_signature(self, index: int) -> None:
        """Settle the buffered signature fragments for one sealing slot.

        A codec-minted `signature` ref on the sealed part subsumes the
        buffer (the codec is the authority; the fragments were its raw
        material). Otherwise the verbatim concatenation is preserved under
        `extensions[SIGNATURE_BUFFER_EXTENSION]` with an `EXTENSIONS`
        record — recoverable, reported, never dropped.

        Args:
            index: The slot being sealed.
        """
        buffered = self._signatures.pop(index, "")
        part = self._slots.get(index)
        if not buffered or part is None:
            return
        if isinstance(part, PartReasoning) and part.signature is not None:
            return
        part.extensions[SIGNATURE_BUFFER_EXTENSION] = buffered
        self._lose(
            index,
            "signature fragments preserved verbatim under "
            f"extensions[{SIGNATURE_BUFFER_EXTENSION!r}]; only the dialect codec's "
            "transducer has the (provider, interface) context to mint the ProviderRef",
            disposition=Disposition.EXTENSIONS,
            severity=0.0,
        )

    @property
    def report(self) -> FidelityReport:
        """The fold's own fidelity account, freshly assembled.

        Empty when every delta applied cleanly; otherwise one `EdgeReport`
        (canonical chunk node → canonical response node) carrying the
        recorded `FieldLoss`es in arrival order. `finalize` merges the same
        edge into the terminal `StreamEnd.report`; this property is the
        report's home when a stream aborted before its `STREAM_STOP`.
        """
        if not self._losses:
            return FidelityReport()
        return FidelityReport(edges=[self._fold_edge()])

    def _fold_edge(self) -> EdgeReport:
        """Assemble the fold's `EdgeReport` from the recorded losses.

        Returns:
            The edge report spanning the canonical chunk and response
            nodes.
        """
        return EdgeReport(
            src=CANONICAL_CHAT_CHUNK,
            dst=CANONICAL_CHAT_RESPONSE,
            losses=tuple(self._losses),
            note="stream fold (StreamAccumulator)",
        )

    def finalize(self) -> ChatResponse:
        """Assemble the folded `ChatResponse` from the accumulated state.

        The terminal `StreamEnd`'s usage/finish are authoritative over
        mid-stream updates. An aborted stream (no `STREAM_STOP` arrived)
        still folds, but every slot it left open is sealed with an explicit
        `extensions[INCOMPLETE_EXTENSION]` marker — accumulated content is
        never passed off as complete. Any fold losses merge into the
        terminal `StreamEnd.report` (once, however many times `finalize`
        runs); an aborted stream's losses stay reachable via `report`.

        Returns:
            The response the equivalent blocking call would have returned.
        """
        if self._end is None:
            for index, part in self._slots.items():
                if index in self._sealed:
                    continue
                self._settle_signature(index)
                part.extensions[INCOMPLETE_EXTENSION] = True
        if self._losses and self._end is not None and not self._reported:
            if self._end.report is None:
                self._end.report = FidelityReport()
            self._end.report.merge(FidelityReport(edges=[self._fold_edge()]))
            self._reported = True
        usage = self._end.usage if self._end and self._end.usage else self._usage
        finish = self._end.finish if self._end and self._end.finish else self._finish
        parts = [self._slots[index] for index in sorted(self._slots)]
        return ChatResponse(
            message=Message(role=Role.MODEL, parts=parts),
            finish=finish,
            usage=usage,
        )

    @classmethod
    def fold(cls, chunks: Iterable[ChatChunk]) -> ChatResponse:
        """Fold a whole chunk stream into its equivalent response.

        The normative law's entry point: `fold(stream(request))` must be
        semantically equal to `complete(request)`.

        Args:
            chunks: The canonical chunks, in stream order.

        Returns:
            The folded `ChatResponse`.
        """
        accumulator = cls()
        for chunk in chunks:
            accumulator.feed(chunk)
        return accumulator.finalize()


@dataclass(frozen=True)
class StreamOutcome:
    """Execution evidence, separate from the successful canonical StreamEnd.

    Missing usage means unknown, never zero. An incomplete or failed outcome
    may retain usage and conversion findings without claiming completion.
    This is a local execution contract, not a new canonical chunk or revision.
    """

    status: Literal["completed", "closed", "cancelled", "failed", "incomplete"]
    usage: Usage | None = None
    report: FidelityReport | None = None
    error: BaseException | None = None


class _StreamState:
    """Shared constant-content-space lifecycle for both stream faces."""

    def __init__(self, report: Callable[[], FidelityReport | None] | None) -> None:
        self.end: StreamEnd | None = None
        self.outcome: StreamOutcome | None = None
        self.usage: Usage | None = None
        self.error: StreamProtocolError | None = None
        self.report = report
        self.callbacks: list[Callable[[StreamOutcome], None]] = []

    def feed(self, chunk: ChatChunk) -> None:
        if self.end is not None:
            raise StreamProtocolError("content after terminal stream record")
        if chunk.usage is not None:
            self.usage = deepcopy(chunk.usage)
        if chunk.type == ChunkType.ERROR:
            self.error = StreamProtocolError("stream reported an error", code=(
                chunk.error.code if chunk.error else None))
        if chunk.type == ChunkType.STREAM_STOP:
            if chunk.end is None:
                raise StreamProtocolError("terminal stream record has no StreamEnd")
            self.end = chunk.end
            self.usage = deepcopy(chunk.end.usage) if chunk.end.usage else self.usage

    def finish(self, status: Literal["completed", "closed", "cancelled", "failed", "incomplete"],
               error: BaseException | None = None) -> None:
        if self.outcome is not None:
            return
        report = self.report() if self.report is not None else None
        if self.end is not None and self.end.report is not None:
            report = self.end.report
        if self.error is not None:
            status, error = "failed", self.error
        self.outcome = StreamOutcome(status, self.usage, deepcopy(report), error)
        if status != "completed":
            self.end = None
        for callback in self.callbacks:
            self.notify(callback)
        self.callbacks.clear()

    def notify(self, callback: Callable[[StreamOutcome], None]) -> None:
        if self.outcome is not None:
            try:
                callback(self.outcome)
            except Exception:
                # Passive lifetime notifications cannot change execution.
                pass


class ChatStream:
    """An owned synchronous stream; use `with` or close explicitly on early exit.

    Normal exhaustion preserves `.end`. `.outcome` also records aborted
    execution and known accounting; it never synthesizes successful StreamEnd.
    A stream created but never consumed is pending until explicitly closed.
    Garbage collection is not a lifecycle or durable-audit guarantee.
    """

    def __init__(self, chunks: Iterator[ChatChunk], *,
                 report: Callable[[], FidelityReport | None] | None = None) -> None:
        """Wrap chunks and an optional snapshot of conversion evidence."""
        self._chunks = chunks
        self._state = _StreamState(report)

    @property
    def end(self) -> StreamEnd | None:
        """The successful terminal record, or None for pending/aborted streams."""
        return self._state.end

    @property
    def outcome(self) -> StreamOutcome | None:
        """The single execution outcome once exhaustion or close finalizes it."""
        return self._state.outcome

    def on_termination(self, callback: Callable[[StreamOutcome], None]) -> None:
        """Register a passive notification; failures are isolated, never admission."""
        if self.outcome is None:
            self._state.callbacks.append(callback)
        else:
            self._state.notify(callback)

    def __iter__(self) -> Iterator[ChatChunk]:
        """Return this stream as its iterator."""
        return self

    def __next__(self) -> ChatChunk:
        """Pull one chunk, release upstream on every terminal path."""
        if self.outcome is not None:
            raise StopIteration
        if self._state.error is not None:
            self._finish("failed", self._state.error)
            raise StopIteration
        try:
            chunk = next(self._chunks)
            self._state.feed(chunk)
            return chunk
        except StopIteration:
            if self.end is None:
                error = StreamProtocolError("stream exhausted without a terminal record")
                self._finish("incomplete", error)
                raise error from None
            self._finish("completed")
            raise
        except BaseException as error:
            self._finish("cancelled" if isinstance(error, (GeneratorExit, KeyboardInterrupt))
                         else "failed", error)
            raise

    def _finish(self, status: Literal["completed", "closed", "cancelled", "failed", "incomplete"],
                error: BaseException | None = None) -> None:
        if self.outcome is not None:
            return
        try:
            close = getattr(self._chunks, "close", None)
            if close is not None:
                close()
        except BaseException as cleanup_error:
            self._state.finish("failed", error or cleanup_error)
            if error is None:
                raise
        else:
            self._state.finish(status, error)

    def close(self) -> None:
        """Release upstream promptly and finalize once; repeated closes are inert."""
        self._finish("completed" if self.end is not None else "closed")

    def __enter__(self) -> Self:
        """Take ownership of this stream for a `with` block."""
        return self

    def __exit__(self, exc_type: object, exc: BaseException | None, tb: object) -> None:
        """Release upstream on normal exit or consumer failure."""
        if exc is None:
            self.close()
        else:
            self._finish("cancelled" if isinstance(exc, (GeneratorExit, KeyboardInterrupt))
                         else "failed", exc)

    def fold(self) -> ChatResponse:
        """Drain and fold the remaining chunks; failed streams still raise."""
        return StreamAccumulator.fold(self)


class AsyncChatStream:
    """Owned async stream; `async with` guarantees close on consumer cancellation."""

    def __init__(self, chunks: AsyncIterator[ChatChunk], *,
                 report: Callable[[], FidelityReport | None] | None = None) -> None:
        """Wrap async chunks and optional conversion evidence without buffering."""
        self._chunks = chunks
        self._state = _StreamState(report)

    @property
    def end(self) -> StreamEnd | None:
        """The successful terminal record, or None for pending/aborted streams."""
        return self._state.end

    @property
    def outcome(self) -> StreamOutcome | None:
        """The single execution outcome once exhaustion or close finalizes it."""
        return self._state.outcome

    def on_termination(self, callback: Callable[[StreamOutcome], None]) -> None:
        """Register a passive notification; required audit must use middleware."""
        if self.outcome is None:
            self._state.callbacks.append(callback)
        else:
            self._state.notify(callback)

    def __aiter__(self) -> AsyncIterator[ChatChunk]:
        """Return this stream as its async iterator."""
        return self

    async def __anext__(self) -> ChatChunk:
        """Pull one chunk and release upstream on exhaustion, error or cancellation."""
        if self.outcome is not None:
            raise StopAsyncIteration
        if self._state.error is not None:
            await self._finish("failed", self._state.error)
            raise StopAsyncIteration
        try:
            chunk = await anext(self._chunks)
            self._state.feed(chunk)
            return chunk
        except StopAsyncIteration:
            if self.end is None:
                error = StreamProtocolError("stream exhausted without a terminal record")
                await self._finish("incomplete", error)
                raise error from None
            await self._finish("completed")
            raise
        except BaseException as error:
            await self._finish("cancelled" if isinstance(error, (asyncio.CancelledError,
                                                               GeneratorExit, KeyboardInterrupt))
                               else "failed", error)
            raise

    async def _finish(
        self, status: Literal["completed", "closed", "cancelled", "failed", "incomplete"],
        error: BaseException | None = None,
    ) -> None:
        if self.outcome is not None:
            return
        try:
            close = getattr(self._chunks, "aclose", None)
            if close is not None:
                await close()
        except BaseException as cleanup_error:
            self._state.finish("failed", error or cleanup_error)
            if error is None:
                raise
        else:
            self._state.finish(status, error)

    async def aclose(self) -> None:
        """Release upstream promptly and finalize once; repeated closes are inert."""
        await self._finish("completed" if self.end is not None else "closed")

    async def __aenter__(self) -> Self:
        """Take ownership for an `async with` block."""
        return self

    async def __aexit__(self, exc_type: object, exc: BaseException | None, tb: object) -> None:
        """Release upstream even when cancellation occurs in consumer code."""
        if exc is None:
            await self.aclose()
        else:
            await self._finish("cancelled" if isinstance(exc, (asyncio.CancelledError,
                                                             GeneratorExit, KeyboardInterrupt))
                               else "failed", exc)

    async def fold(self) -> ChatResponse:
        """Drain and fold the remaining chunks without hiding stream failure."""
        accumulator = StreamAccumulator()
        async for chunk in self:
            accumulator.feed(chunk)
        return accumulator.finalize()
