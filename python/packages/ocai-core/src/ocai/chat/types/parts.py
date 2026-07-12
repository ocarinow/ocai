"""The full canonical part taxonomy (architecture §3.1).

A `Message` body is a list of `Part`s — a tagged union discriminated on
`type` and kept **open** through `PART_REGISTRY`: core registers its bare
tags at import of this module; plugins register namespaced tags
(`"anthropic.mid_conv_system"`) from their `CatalogFragment`; an unknown tag
decodes to `PartUnknown`, never raises (total decode, rule 6).

Two look-alike types are deliberately distinct:

- `PartOpaque` — *deliberate* provider-unique content, census-registered in
  `spec/extensions/`. Chosen by an author or codec on purpose.
- `PartUnknown` — the decoder *fallback* for a future canonical tag this
  revision does not know. Never constructed deliberately; upgradeable later
  via IR self-migration edges.

Every part shares three universal optionals on `PartBase`: `id` (stable part
identity — the lesson of OpenAI's item model), `anchor` (a `ProviderRef` to
provider-side state backing the part), and `cache_hint` (a per-part caching
marker). The streaming ratchet (normative): **no new part type is admissible
without its `Delta` type, its fold law in `StreamAccumulator`, and paired
chunks/response fixtures in the same change.**
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import ClassVar
from typing import Final
from typing import Literal
from typing import Self

from ocai.chat.types.annotations import Annotation
from ocai.chat.types.config import CacheHint
from ocai.core.ir import IRObject
from ocai.core.ir import TagRegistry
from ocai.core.refs import ProviderRef
from ocai.core.sources import Source
from ocai.core.sources import cast_source


class PartType(str, Enum):
    """Canonical discriminator tags for the core `Part` variants.

    Constants for the tags core ships — the union itself stays open through
    `PART_REGISTRY` (unknown tags decode to `PartUnknown`; plugins register
    namespaced tags).

    Attributes:
        UNDEFINED: No part kind set (the unknown/placeholder tag).
        TEXT: A text part (`PartText`).
        IMAGE: An image part (`PartImage`).
        AUDIO: An audio part (`PartAudio`).
        VIDEO: A video part (`PartVideo`).
        DOCUMENT: A document part (`PartDocument`).
        REASONING: A model-reasoning part (`PartReasoning`).
        TOOL_CALL: A client-executed tool invocation (`PartToolCall`).
        TOOL_RESULT: The result of a client-executed tool (`PartToolResult`).
        SERVER_TOOL_CALL: A provider-executed built-in tool invocation
            (`PartServerToolCall`).
        SERVER_TOOL_RESULT: A provider-executed built-in tool result
            (`PartServerToolResult`).
        REFUSAL: A refusal part (`PartRefusal`).
        OPAQUE: Deliberate provider-unique content (`PartOpaque`).
    """

    UNDEFINED = "undefined"
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    REASONING = "reasoning"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SERVER_TOOL_CALL = "server_tool_call"
    SERVER_TOOL_RESULT = "server_tool_result"
    REFUSAL = "refusal"
    OPAQUE = "opaque"


class ToolCallStatus:
    """Canonical constants for the open tool-call lifecycle code.

    Shared between `PartToolCall.status`, `PartServerToolCall.status`, and
    their result siblings — the same lifecycle the streaming deltas advance:
    `input_streaming → input_complete → executing →
    output_available | output_error`. Open: providers may surface states
    core has not named, preserved verbatim.

    Attributes:
        INPUT_STREAMING: Argument fragments are still arriving.
        INPUT_COMPLETE: The arguments are complete; the call is ready to
            execute.
        EXECUTING: The tool is running (meaningful for provider-executed
            tools; client executions live outside the transcript).
        OUTPUT_AVAILABLE: The result is present.
        OUTPUT_ERROR: Execution failed; the result carries the error.
    """

    INPUT_STREAMING: Final = "input_streaming"
    INPUT_COMPLETE: Final = "input_complete"
    EXECUTING: Final = "executing"
    OUTPUT_AVAILABLE: Final = "output_available"
    OUTPUT_ERROR: Final = "output_error"


class ExecutedBy:
    """Canonical constants for the open `PartToolCall.executed_by` code.

    Attributes:
        CLIENT: The caller runs the tool and replies with a
            `PartToolResult` (the classic function-calling loop).
        PROVIDER: The provider runs the tool server-side (built-in tools);
            results arrive as `PartServerToolResult`s.
    """

    CLIENT: Final = "client"
    PROVIDER: Final = "provider"


class ServerToolKind:
    """Canonical constants for the open `PartServerToolCall.kind` code.

    An open vocabulary over the industry's fastest-moving surface — these
    name the kinds core recognizes today; unrecognized kinds are preserved
    verbatim and remain visible and reportable.

    Attributes:
        WEB_SEARCH: A provider-side web search.
        CODE_EXECUTION: Provider-side code execution.
        MCP_CALL: A provider-brokered MCP tool call.
    """

    WEB_SEARCH: Final = "web_search"
    CODE_EXECUTION: Final = "code_execution"
    MCP_CALL: Final = "mcp_call"


@dataclass
class PartBase(IRObject):
    """The shared base of every canonical part — the universal optionals.

    Concrete parts extend this and add their payload fields plus a fixed
    `type` tag. The three fields here are cross-cutting: they exist on every
    part so codecs, the accumulator, and conversion edges can address parts
    uniformly.

    Attributes:
        id: The part's stable identity within its message, when the provider
            (or ocai) assigned one. Preserving it is what lets `/responses`
            item semantics round-trip.
        anchor: Provider-side state backing this part (an item id, a file
            handle); inherits `ProviderRef`'s cross-interface `UNSUPPORTED`
            rule.
        cache_hint: A per-part prompt-caching marker [provisional].
    """

    object: ClassVar[str] = "part"

    id: str | None = field(default=None, kw_only=True)
    anchor: ProviderRef | None = field(default=None, kw_only=True)
    cache_hint: CacheHint | None = field(default=None, kw_only=True)

    @classmethod
    def _from_dict_base(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Extract the shared part kwargs plus the IR envelope from `data`.

        The part-level half of tolerant decode: subclasses splat the result
        into their constructor after decoding their own payload fields.

        Args:
            data: The full serialized part mapping being decoded.

        Returns:
            Kwargs for `id`, `anchor`, `cache_hint`, and the `IRObject`
            envelope fields.
        """
        anchor = data.get("anchor")
        cache_hint = data.get("cache_hint")
        return {
            "id": data.get("id"),
            "anchor": ProviderRef.from_dict(anchor) if isinstance(anchor, dict) else None,
            "cache_hint": CacheHint.from_dict(cache_hint) if isinstance(cache_hint, dict) else None,
            **cls._from_dict_common(data),
        }


@dataclass
class PartText(PartBase):
    """A run of text, with its citations anchored on it.

    The workhorse part. Citations are span-anchored `Annotation`s carried
    *here*, never in a side channel, so text and its attributions move
    together through slicing, folding, and conversion.

    Attributes:
        text: The text content.
        annotations: The span-anchored citations attributing ranges of
            `text` to sources.
        type: The part discriminator, fixed to `PartType.TEXT`.
    """

    text: str = ""
    annotations: list[Annotation] = field(default_factory=list)
    type: Literal[PartType.TEXT] = field(default=PartType.TEXT)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `PartText` from a serialized dict, totally.

        Args:
            data: A mapping with `text`, optional `annotations`, and the
                shared part/envelope keys.

        Returns:
            The decoded `PartText`.
        """
        return cls(
            text=data.get("text", ""),
            annotations=[
                Annotation.from_dict(item)
                for item in data.get("annotations") or []
                if isinstance(item, dict)
            ],
            **cls._from_dict_base(data),
        )


@dataclass
class PartImage(PartBase):
    """An image, referenced through the `Source` union.

    Attributes:
        source: Where the image bytes live — inline base64, a URL, or a
            provider-hosted `SourceRef`.
        type: The part discriminator, fixed to `PartType.IMAGE`.
    """

    source: Source | None = None
    type: Literal[PartType.IMAGE] = field(default=PartType.IMAGE)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `PartImage` from a serialized dict, totally.

        Args:
            data: A mapping with the nested `source` and the shared
                part/envelope keys.

        Returns:
            The decoded `PartImage`.
        """
        source = data.get("source")
        return cls(
            source=cast_source(source) if isinstance(source, dict) else None,
            **cls._from_dict_base(data),
        )


@dataclass
class PartAudio(PartBase):
    """An audio clip, referenced through the `Source` union.

    Attributes:
        source: Where the audio bytes live — inline base64, a URL, or a
            provider-hosted `SourceRef` (e.g. an OpenAI audio id via its
            `ProviderRef`).
        type: The part discriminator, fixed to `PartType.AUDIO`.
    """

    source: Source | None = None
    type: Literal[PartType.AUDIO] = field(default=PartType.AUDIO)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `PartAudio` from a serialized dict, totally.

        Args:
            data: A mapping with the nested `source` and the shared
                part/envelope keys.

        Returns:
            The decoded `PartAudio`.
        """
        source = data.get("source")
        return cls(
            source=cast_source(source) if isinstance(source, dict) else None,
            **cls._from_dict_base(data),
        )


@dataclass
class PartVideo(PartBase):
    """A video, referenced through the `Source` union.

    The clipping/sampling metadata (Gemini `videoMetadata`) rides as per-part
    optionals here; interfaces without it report the fields `ABSENT` via
    their `CapabilityProfile` rather than dropping them silently.

    Attributes:
        source: Where the video bytes live — inline base64, a URL, or a
            provider-hosted `SourceRef`.
        start_offset: Where playback/sampling starts, as a provider-shaped
            duration token (e.g. `"20s"`), verbatim.
        end_offset: Where playback/sampling ends, same form as
            `start_offset`.
        fps: The frame-sampling rate requested for the model.
        type: The part discriminator, fixed to `PartType.VIDEO`.
    """

    source: Source | None = None
    start_offset: str | None = None
    end_offset: str | None = None
    fps: float | None = None
    type: Literal[PartType.VIDEO] = field(default=PartType.VIDEO)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `PartVideo` from a serialized dict, totally.

        Args:
            data: A mapping with the nested `source`, the optional video
                metadata, and the shared part/envelope keys.

        Returns:
            The decoded `PartVideo`.
        """
        source = data.get("source")
        return cls(
            source=cast_source(source) if isinstance(source, dict) else None,
            start_offset=data.get("start_offset"),
            end_offset=data.get("end_offset"),
            fps=data.get("fps"),
            **cls._from_dict_base(data),
        )


@dataclass
class PartDocument(PartBase):
    """A document (PDF and friends), referenced through the `Source` union.

    The citation-support metadata (Anthropic document `title`/`context`)
    rides as per-part optionals; `Annotation.document_index` points back at
    documents by position.

    Attributes:
        source: Where the document bytes live — inline base64, a URL, or a
            provider-hosted `SourceRef`.
        title: The document's title, surfaced to the model for citations.
        context: Caller-supplied context about the document, surfaced to the
            model but never quoted as content.
        type: The part discriminator, fixed to `PartType.DOCUMENT`.
    """

    source: Source | None = None
    title: str | None = None
    context: str | None = None
    type: Literal[PartType.DOCUMENT] = field(default=PartType.DOCUMENT)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `PartDocument` from a serialized dict, totally.

        Args:
            data: A mapping with the nested `source`, the optional
                title/context, and the shared part/envelope keys.

        Returns:
            The decoded `PartDocument`.
        """
        source = data.get("source")
        return cls(
            source=cast_source(source) if isinstance(source, dict) else None,
            title=data.get("title"),
            context=data.get("context"),
            **cls._from_dict_base(data),
        )


@dataclass
class PartReasoning(PartBase):
    """Model reasoning — ONE merged shape for every provider's idiom.

    An OpenAI `/responses` reasoning item (summary + encrypted content), an
    Anthropic thinking block (text + signature), and a Gemini thought
    (text + thoughtSignature) are all **one part each**, never two
    correlated ones — correlation-by-adjacency does not survive conversion.

    Replay rules (per `ProviderRef.replay`): `signature` and `opaque` marked
    `REQUIRED` are weighted as *breakage* in planning — dropping them
    produces a 400 on replay, not degraded output.

    Attributes:
        text: The raw reasoning text, when the provider surfaces it.
        summary: The provider-generated summary of the reasoning, when that
            is what the interface returns instead of (or besides) raw text.
        signature: The provider's integrity signature over the reasoning,
            required back on replay by some interfaces.
        opaque: Encrypted/opaque reasoning state (OpenAI
            `encrypted_content`) that must ride along verbatim.
        type: The part discriminator, fixed to `PartType.REASONING`.
    """

    text: str | None = None
    summary: str | None = None
    signature: ProviderRef | None = None
    opaque: ProviderRef | None = None
    type: Literal[PartType.REASONING] = field(default=PartType.REASONING)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `PartReasoning` from a serialized dict, totally.

        Args:
            data: A mapping with any of the reasoning lanes and the shared
                part/envelope keys.

        Returns:
            The decoded `PartReasoning`.
        """
        signature = data.get("signature")
        opaque = data.get("opaque")
        return cls(
            text=data.get("text"),
            summary=data.get("summary"),
            signature=ProviderRef.from_dict(signature) if isinstance(signature, dict) else None,
            opaque=ProviderRef.from_dict(opaque) if isinstance(opaque, dict) else None,
            **cls._from_dict_base(data),
        )


@dataclass
class PartToolCall(PartBase):
    """The model's request to invoke a named tool.

    `args_json` is **the authoritative wire truth**: every first-party
    interface streams tool arguments as string fragments, so the canonical
    form is the raw string, parsed on read via `args()` — never re-serialized
    through a dict that could reorder or renormalize what the model wrote.

    Cross-provider conversion regenerates `call_id`s (providers reject
    foreign id shapes); that is recorded as a `SemanticShift`
    (`ID_REGENERATED`), never silent.

    Attributes:
        call_id: The id correlating this call with its `PartToolResult`
            sibling.
        name: The tool name, matching a request `Tool.name`.
        args_json: The arguments as the verbatim JSON string the model
            produced.
        status: The open lifecycle code shared with streaming; constants on
            `ToolCallStatus`.
        executed_by: Who runs the tool; constants on `ExecutedBy`.
        type: The part discriminator, fixed to `PartType.TOOL_CALL`.
    """

    call_id: str = ""
    name: str = ""
    args_json: str = ""
    status: str = ToolCallStatus.INPUT_COMPLETE
    executed_by: str = ExecutedBy.CLIENT
    type: Literal[PartType.TOOL_CALL] = field(default=PartType.TOOL_CALL)

    def args(self) -> Any:
        """Parse `args_json` on read.

        Parse-on-read keeps the wire string authoritative: the parsed form
        is a *view*, never stored, so canonical equality (`canonjson`) can
        apply its parse-compare/preserve-verbatim rule to the string lane.

        Returns:
            The parsed JSON value (typically a dict of arguments); `None`
            when `args_json` is empty.

        Raises:
            json.JSONDecodeError: If `args_json` is not valid JSON — a
                *read-time* error by design; decode never parses it.
        """
        if not self.args_json:
            return None
        return json.loads(self.args_json)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `PartToolCall` from a serialized dict, totally.

        `args_json` passes through verbatim — it is never parsed at decode
        time.

        Args:
            data: A mapping with the call fields and the shared
                part/envelope keys.

        Returns:
            The decoded `PartToolCall`.
        """
        return cls(
            call_id=data.get("call_id", ""),
            name=data.get("name", ""),
            args_json=data.get("args_json", ""),
            status=data.get("status", ToolCallStatus.INPUT_COMPLETE),
            executed_by=data.get("executed_by", ExecutedBy.CLIENT),
            **cls._from_dict_base(data),
        )


@dataclass
class PartToolResult(PartBase):
    """The caller's answer to a `PartToolCall`, correlated by `call_id`.

    A *sibling* of the call in the transcript, never nested inside it —
    nesting is a provider idiom (Gemini) that codecs flatten. The result
    body is itself a list of parts, so tools can return text, images, and
    documents without a parallel content model.

    Attributes:
        call_id: The id of the `PartToolCall` this answers.
        parts: The result content (text/image/document parts nest here).
        is_error: Whether the tool execution failed; the parts then carry
            the error content.
        type: The part discriminator, fixed to `PartType.TOOL_RESULT`.
    """

    call_id: str = ""
    parts: list[Part] = field(default_factory=list)
    is_error: bool = False
    type: Literal[PartType.TOOL_RESULT] = field(default=PartType.TOOL_RESULT)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `PartToolResult` from a serialized dict, totally.

        Nested `parts` are decoded through `PART_REGISTRY`, so unknown
        nested tags fall back to `PartUnknown` like everywhere else.

        Args:
            data: A mapping with `call_id`, nested `parts`, `is_error`, and
                the shared part/envelope keys.

        Returns:
            The decoded `PartToolResult`.
        """
        return cls(
            call_id=data.get("call_id", ""),
            parts=[cast_part(item) for item in data.get("parts") or [] if isinstance(item, dict)],
            is_error=bool(data.get("is_error", False)),
            **cls._from_dict_base(data),
        )


@dataclass
class PartServerToolCall(PartBase):
    """A provider-executed built-in tool invocation — the typed spine.

    Built-in tools (web search, code execution, MCP) are the industry's
    fastest-moving surface, so this part types only the spine — kind, id,
    lifecycle — and keeps the provider payload **verbatim and
    byte-faithful**: visible and reportable without freezing shapes that
    change monthly.

    Attributes:
        kind: The open tool-kind code; constants on `ServerToolKind`.
        call_id: The id correlating this call with its
            `PartServerToolResult` sibling.
        status: The open lifecycle code shared with `ToolCallStatus`.
        payload: The provider's invocation payload, verbatim.
        type: The part discriminator, fixed to
            `PartType.SERVER_TOOL_CALL`.
    """

    kind: str = ""
    call_id: str = ""
    status: str = ToolCallStatus.EXECUTING
    payload: dict[str, Any] = field(default_factory=dict)
    type: Literal[PartType.SERVER_TOOL_CALL] = field(default=PartType.SERVER_TOOL_CALL)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `PartServerToolCall` from a serialized dict, totally.

        Args:
            data: A mapping with the spine fields, the verbatim `payload`,
                and the shared part/envelope keys.

        Returns:
            The decoded `PartServerToolCall`.
        """
        payload = data.get("payload")
        return cls(
            kind=data.get("kind", ""),
            call_id=data.get("call_id", ""),
            status=data.get("status", ToolCallStatus.EXECUTING),
            payload=dict(payload) if isinstance(payload, dict) else {},
            **cls._from_dict_base(data),
        )


@dataclass
class PartServerToolResult(PartBase):
    """A provider-executed built-in tool result, correlated by `call_id`.

    The result half of the `PartServerToolCall` spine; same design — typed
    identity and lifecycle over a verbatim payload.

    Attributes:
        kind: The open tool-kind code; constants on `ServerToolKind`.
        call_id: The id of the `PartServerToolCall` this answers.
        status: The open lifecycle code; typically `OUTPUT_AVAILABLE` or
            `OUTPUT_ERROR`.
        payload: The provider's result payload, verbatim and byte-faithful.
        type: The part discriminator, fixed to
            `PartType.SERVER_TOOL_RESULT`.
    """

    kind: str = ""
    call_id: str = ""
    status: str = ToolCallStatus.OUTPUT_AVAILABLE
    payload: dict[str, Any] = field(default_factory=dict)
    type: Literal[PartType.SERVER_TOOL_RESULT] = field(default=PartType.SERVER_TOOL_RESULT)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `PartServerToolResult` from a serialized dict, totally.

        Args:
            data: A mapping with the spine fields, the verbatim `payload`,
                and the shared part/envelope keys.

        Returns:
            The decoded `PartServerToolResult`.
        """
        payload = data.get("payload")
        return cls(
            kind=data.get("kind", ""),
            call_id=data.get("call_id", ""),
            status=data.get("status", ToolCallStatus.OUTPUT_AVAILABLE),
            payload=dict(payload) if isinstance(payload, dict) else {},
            **cls._from_dict_base(data),
        )


@dataclass
class PartRefusal(PartBase):
    """A refusal surfaced as content (OpenAI's refusal lane).

    Pairs with `FinishInfo.reason == "refusal"`. Boundary rule: a
    *mid-generation* refusal is a response (this part); a *pre-generation*
    block is a `ContentFilterError`, not a response at all.

    Attributes:
        text: The refusal text.
        type: The part discriminator, fixed to `PartType.REFUSAL`.
    """

    text: str = ""
    type: Literal[PartType.REFUSAL] = field(default=PartType.REFUSAL)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `PartRefusal` from a serialized dict, totally.

        Args:
            data: A mapping with `text` and the shared part/envelope keys.

        Returns:
            The decoded `PartRefusal`.
        """
        return cls(text=data.get("text", ""), **cls._from_dict_base(data))


@dataclass
class PartOpaque(PartBase):
    """*Deliberate* provider-unique content, census-registered.

    The escape hatch for content a codec understands but canonical cannot
    (yet) represent first-class. Every `kind` must be schema-registered in
    `spec/extensions/` — an unregistered kind is a CI failure — so the
    opaque lane can never silently become the real schema. Strictly distinct
    from `PartUnknown`, which is the decoder fallback for *future canonical*
    tags.

    Attributes:
        kind: The namespaced, censused content key
            (e.g. `"anthropic.mid_conv_system"`).
        payload: The provider content, verbatim.
        type: The part discriminator, fixed to `PartType.OPAQUE`.
    """

    kind: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    type: Literal[PartType.OPAQUE] = field(default=PartType.OPAQUE)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `PartOpaque` from a serialized dict, totally.

        Args:
            data: A mapping with the censused `kind`, the verbatim
                `payload`, and the shared part/envelope keys.

        Returns:
            The decoded `PartOpaque`.
        """
        payload = data.get("payload")
        return cls(
            kind=data.get("kind", ""),
            payload=dict(payload) if isinstance(payload, dict) else {},
            **cls._from_dict_base(data),
        )


@dataclass
class PartUnknown(PartBase):
    """Decoder fallback for a part tag this revision does not know.

    Preserves the payload verbatim (byte-faithful through `to_dict`) so a
    *future* canonical part survives decode/encode untouched and can be
    upgraded later via IR self-migration edges. Total decode's safety net —
    never constructed deliberately (that is `PartOpaque`'s job).

    Attributes:
        data: The verbatim serialized payload, including its original tag.
        type: The unrecognized discriminator value, preserved verbatim.
    """

    data: dict[str, Any] = field(default_factory=dict)
    type: str = PartType.UNDEFINED.value

    def to_dict(self) -> dict[str, Any]:
        """Serialize back to the verbatim payload this instance preserved.

        Returns:
            A copy of the original serialized mapping, untouched.
        """
        return dict(self.data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Preserve an unrecognized part payload verbatim.

        Args:
            data: The serialized mapping whose tag no registered part
                matched.

        Returns:
            A new `PartUnknown` carrying the payload untouched.
        """
        tag = data.get("type")
        return cls(
            data=dict(data),
            type=tag if isinstance(tag, str) else PartType.UNDEFINED.value,
        )


type Part = (
    PartText
    | PartImage
    | PartAudio
    | PartVideo
    | PartDocument
    | PartReasoning
    | PartToolCall
    | PartToolResult
    | PartServerToolCall
    | PartServerToolResult
    | PartRefusal
    | PartOpaque
    | PartUnknown
)

# The open registry for the Part union. Core registers its bare tags here;
# plugins register namespaced tags from their CatalogFragment. Unknown tags
# fall back to PartUnknown — decoding a part never raises.
PART_REGISTRY: TagRegistry[Any] = TagRegistry(unknown=PartUnknown)
PART_REGISTRY.register(PartType.TEXT.value, PartText)
PART_REGISTRY.register(PartType.IMAGE.value, PartImage)
PART_REGISTRY.register(PartType.AUDIO.value, PartAudio)
PART_REGISTRY.register(PartType.VIDEO.value, PartVideo)
PART_REGISTRY.register(PartType.DOCUMENT.value, PartDocument)
PART_REGISTRY.register(PartType.REASONING.value, PartReasoning)
PART_REGISTRY.register(PartType.TOOL_CALL.value, PartToolCall)
PART_REGISTRY.register(PartType.TOOL_RESULT.value, PartToolResult)
PART_REGISTRY.register(PartType.SERVER_TOOL_CALL.value, PartServerToolCall)
PART_REGISTRY.register(PartType.SERVER_TOOL_RESULT.value, PartServerToolResult)
PART_REGISTRY.register(PartType.REFUSAL.value, PartRefusal)
PART_REGISTRY.register(PartType.OPAQUE.value, PartOpaque)


def cast_part(data: dict[str, Any]) -> Part:
    """Decode a serialized part into its concrete `Part` variant.

    Dispatches on the `type` tag via `PART_REGISTRY`; unknown tags decode to
    `PartUnknown` — this function never raises on unknown input.

    Args:
        data: The serialized part mapping, including its `type`
            discriminator.

    Returns:
        The decoded `Part` variant.
    """
    decoded: Part = PART_REGISTRY.decode(data)
    return decoded
