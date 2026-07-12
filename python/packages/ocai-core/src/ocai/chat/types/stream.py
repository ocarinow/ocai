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

from collections.abc import AsyncIterator
from collections.abc import Iterable
from collections.abc import Iterator
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import ClassVar
from typing import Literal
from typing import Self

from ocai.chat.canonical import CANONICAL_CHAT_CHUNK
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
from ocai.core.fidelity import FidelityReport
from ocai.core.identity import NodeId
from ocai.core.ir import IRObject
from ocai.core.ir import TagRegistry


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
            annotation=Annotation.from_dict(annotation) if isinstance(annotation, dict) else None,
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

    data: dict[str, Any] = field(default_factory=dict)
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
        # TODO: FidelityReport needs a from_dict for recorded-stream replay;
        # until then a serialized report decodes to None.
        return cls(
            usage=Usage.from_dict(usage) if isinstance(usage, dict) else None,
            finish=FinishInfo.from_dict(finish) if isinstance(finish, dict) else None,
            report=None,
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
            part=cast_part(part) if isinstance(part, dict) else None,
            delta=cast_delta(delta) if isinstance(delta, dict) else None,
            usage=Usage.from_dict(usage) if isinstance(usage, dict) else None,
            usage_cumulative=data.get("usage_cumulative"),
            finish=FinishInfo.from_dict(finish) if isinstance(finish, dict) else None,
            error=ErrorInfo.from_dict(error) if isinstance(error, dict) else None,
            end=StreamEnd.from_dict(end) if isinstance(end, dict) else None,
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

    Use it incrementally (`feed` per chunk, then `finalize`) or in one shot
    via the `fold` classmethod.
    """

    def __init__(self) -> None:
        """Create an empty accumulator ready to receive a stream."""
        self._slots: dict[int, Part] = {}
        self._order: list[int] = []
        self._usage: Usage | None = None
        self._finish: FinishInfo | None = None
        self._error: ErrorInfo | None = None
        self._end: StreamEnd | None = None

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
            # TODO: signature fragments accumulate as opaque strings; the
            # codec's transducer mints the final ProviderRef on PART_STOP —
            # buffer-and-mint here needs the (provider, interface) context.
            pass
        elif isinstance(delta, DeltaBlob):
            # TODO: accumulate base64 fragments into the media part's
            # SourceBase64 once an audio-output edge exercises this path.
            pass
        else:
            # TODO: mismatched delta/part pairs and DeltaUnknown need a
            # reporting channel (an EdgeReport on StreamEnd.report).
            pass

    def _seal(self, chunk: ChatChunk) -> None:
        """Seal the slot at `chunk.index`.

        The authoritative final part on the chunk wins when present (the
        fold law requires it to equal the accumulation — asserting that is
        the conformance harness's job, not the fold's). A sealed tool call
        advances to `INPUT_COMPLETE`.

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

    def finalize(self) -> ChatResponse:
        """Assemble the folded `ChatResponse` from the accumulated state.

        The terminal `StreamEnd`'s usage/finish are authoritative over
        mid-stream updates. An aborted stream (no `STREAM_STOP`) still
        folds — its parts seal as-is.

        Returns:
            The response the equivalent blocking call would have returned.
        """
        # TODO: aborted streams must seal open parts with an explicit
        # incomplete marker (extensions["ocai.incomplete"]) per the blueprint.
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


class ChatStream:
    """The synchronous stream a `ChatModel.stream` call returns.

    A thin iterator wrapper over canonical chunks that watches for the
    terminal `STREAM_STOP` and exposes its `StreamEnd` as `.end` once the
    stream is exhausted — so callers iterate naturally and still get the
    authoritative usage/finish/report without re-buffering the stream.

    Attributes:
        end: The terminal record, available after exhaustion; None while
            streaming or if the stream aborted without a terminal chunk.
    """

    def __init__(self, chunks: Iterator[ChatChunk]) -> None:
        """Wrap an iterator of canonical chunks.

        Args:
            chunks: The underlying chunk iterator (typically the driver's
                decoded SSE pump).
        """
        self._chunks = chunks
        self.end: StreamEnd | None = None

    def __iter__(self) -> Iterator[ChatChunk]:
        """Return the stream itself as its iterator."""
        return self

    def __next__(self) -> ChatChunk:
        """Yield the next chunk, capturing the terminal `StreamEnd`.

        Returns:
            The next canonical chunk.

        Raises:
            StopIteration: When the underlying stream is exhausted.
        """
        chunk = next(self._chunks)
        if chunk.type == ChunkType.STREAM_STOP:
            self.end = chunk.end
        return chunk

    def fold(self) -> ChatResponse:
        """Drain the remaining chunks and fold them into a response.

        Convenience over `StreamAccumulator.fold` for callers who started
        streaming and decided they want the blocking shape after all.

        Returns:
            The folded `ChatResponse` of the *remaining* stream.
        """
        return StreamAccumulator.fold(self)


class AsyncChatStream:
    """The asynchronous stream a `ChatModel.astream` call returns.

    The `a`-twin of `ChatStream`, with identical semantics over an async
    iterator: iterate chunks with `async for`, read `.end` after
    exhaustion.

    Attributes:
        end: The terminal record, available after exhaustion; None while
            streaming or if the stream aborted without a terminal chunk.
    """

    def __init__(self, chunks: AsyncIterator[ChatChunk]) -> None:
        """Wrap an async iterator of canonical chunks.

        Args:
            chunks: The underlying chunk iterator (typically the driver's
                decoded SSE pump).
        """
        self._chunks = chunks
        self.end: StreamEnd | None = None

    def __aiter__(self) -> AsyncIterator[ChatChunk]:
        """Return the stream itself as its async iterator."""
        return self

    async def __anext__(self) -> ChatChunk:
        """Yield the next chunk, capturing the terminal `StreamEnd`.

        Returns:
            The next canonical chunk.

        Raises:
            StopAsyncIteration: When the underlying stream is exhausted.
        """
        chunk = await self._chunks.__anext__()
        if chunk.type == ChunkType.STREAM_STOP:
            self.end = chunk.end
        return chunk

    async def fold(self) -> ChatResponse:
        """Drain the remaining chunks and fold them into a response.

        Returns:
            The folded `ChatResponse` of the *remaining* stream.
        """
        accumulator = StreamAccumulator()
        async for chunk in self:
            accumulator.feed(chunk)
        return accumulator.finalize()
