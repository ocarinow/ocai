"""Why generation stopped: `FinishInfo` and its detail union (architecture §2).

This is **cross-capability vocabulary**, hoisted from `ocai.chat` pre-freeze
(the capability stress-test): every capability that runs to a terminal state
reports *why it stopped* in the same two-lane shape — a chat turn hitting
`max_tokens`, an image generation cut off by a safety system, an async job
reaching a terminal state — so `FinishInfo` lives in core beside `Usage`,
not inside any one capability.

Finish handling follows the two-lane honesty pattern: `reason` is the
canonical **open** code (constants on `FinishReason`), and `native` carries
the provider's verbatim value — so an unknown wire value decodes to
`reason == "unknown"` with the native lane preserved, and enum growth is
structurally crash-proof (rule 6).

`detail` is a tagged union with its own open `TagRegistry`
(`DETAIL_REGISTRY`): typed elaborations for the reasons that need one
(safety ratings, refusal categories, mid-generation errors), with
`DetailOpaque` as both the deliberate opaque member and the unknown-tag
fallback.

Boundary rule (normative): a *mid-generation* refusal or filter stop is a
**response** carrying this info; a *pre-generation* block (Gemini
`promptFeedback`) is a `ContentFilterError` — no response existed to report
on.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import ClassVar
from typing import Final
from typing import Literal
from typing import Self

from ocai.core.ir import IRObject
from ocai.core.ir import TagRegistry


class FinishReason:
    """Canonical constants for the open `FinishInfo.reason` code.

    Attributes:
        COMPLETE: The model finished its turn naturally.
        MAX_TOKENS: The output token ceiling was hit; the reply is
            truncated.
        STOP_SEQUENCE: A configured stop sequence was emitted.
        TOOL_CALL: The model stopped to have tools executed.
        CONTENT_FILTER: Generation was cut off by a safety system
            mid-stream (`detail` typically carries a `SafetyDetail`).
        REFUSAL: The model refused mid-generation (pairs with
            `PartRefusal`).
        RECITATION: Output was stopped for reciting training/source
            material (Gemini's recitation stop).
        PAUSED: The provider paused a long-running turn for the caller to
            resume (Anthropic `pause_turn`).
        MALFORMED: The model produced output the provider could not
            represent (e.g. a malformed function call).
        ERROR: Generation ended in a provider-reported error (`detail`
            carries an `ErrorDetail`).
        UNKNOWN: The wire value was not recognized; `FinishInfo.native`
            preserves it verbatim.
    """

    COMPLETE: Final = "complete"
    MAX_TOKENS: Final = "max_tokens"
    STOP_SEQUENCE: Final = "stop_sequence"
    TOOL_CALL: Final = "tool_call"
    CONTENT_FILTER: Final = "content_filter"
    REFUSAL: Final = "refusal"
    RECITATION: Final = "recitation"
    PAUSED: Final = "paused"
    MALFORMED: Final = "malformed"
    ERROR: Final = "error"
    UNKNOWN: Final = "unknown"


class DetailType(str, Enum):
    """Canonical discriminator tags for the core `FinishDetail` variants.

    Constants for the tags core ships — the union stays open through
    `DETAIL_REGISTRY` (unknown tags decode to `DetailOpaque`).

    Attributes:
        UNDEFINED: No detail kind set (the unknown/placeholder tag).
        SAFETY: A safety-system elaboration (`SafetyDetail`).
        REFUSAL: A refusal elaboration (`RefusalDetail`).
        INCOMPLETE: An incomplete-output elaboration (`IncompleteDetail`).
        ERROR: A mid-generation error elaboration (`ErrorDetail`).
    """

    UNDEFINED = "undefined"
    SAFETY = "safety"
    REFUSAL = "refusal"
    INCOMPLETE = "incomplete"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class SafetyRating:
    """One per-category safety assessment inside a `SafetyDetail`.

    Attributes:
        category: The open safety-category code, provider-verbatim
            (e.g. `"HARM_CATEGORY_DANGEROUS_CONTENT"`).
        level: The open severity/probability code, provider-verbatim
            (e.g. `"HIGH"`), or None when the provider gives none.
        blocked: Whether this category triggered the block, when the
            provider says so.
    """

    category: str
    level: str | None = None
    blocked: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the rating to a plain JSON-compatible dict.

        Returns:
            A dict with `category` and the optional `level`/`blocked` when
            set.
        """
        out: dict[str, Any] = {"category": self.category}
        if self.level is not None:
            out["level"] = self.level
        if self.blocked is not None:
            out["blocked"] = self.blocked
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `SafetyRating` from a serialized dict, totally.

        Args:
            data: A mapping with `category` and the optional
                `level`/`blocked`.

        Returns:
            The decoded `SafetyRating`.
        """
        return cls(
            category=data.get("category", ""),
            level=data.get("level"),
            blocked=data.get("blocked"),
        )


@dataclass
class SafetyDetail(IRObject):
    """Elaboration for safety-driven stops (`reason == "content_filter"`).

    Attributes:
        ratings: The per-category assessments the provider reported.
        block_source: The open code for which safety layer blocked
            (e.g. `"provider"`, `"platform"`), when distinguishable.
        type: The detail discriminator, fixed to `DetailType.SAFETY`.
    """

    ratings: list[SafetyRating] = field(default_factory=list)
    block_source: str | None = None
    type: Literal[DetailType.SAFETY] = field(default=DetailType.SAFETY)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `SafetyDetail` from a serialized dict, totally.

        Args:
            data: A mapping with `ratings`, an optional `block_source`, and
                the common IR envelope keys.

        Returns:
            The decoded `SafetyDetail`.
        """
        return cls(
            ratings=[
                SafetyRating.from_dict(item)
                for item in data.get("ratings") or []
                if isinstance(item, dict)
            ],
            block_source=data.get("block_source"),
            **cls._from_dict_common(data),
        )


@dataclass
class RefusalDetail(IRObject):
    """Elaboration for refusal stops (`reason == "refusal"`).

    Attributes:
        category: The open refusal-category code, provider-verbatim, when
            given.
        explanation: The provider's human-readable explanation, when given.
        type: The detail discriminator, fixed to `DetailType.REFUSAL`.
    """

    category: str | None = None
    explanation: str | None = None
    type: Literal[DetailType.REFUSAL] = field(default=DetailType.REFUSAL)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `RefusalDetail` from a serialized dict, totally.

        Args:
            data: A mapping with the optional `category`/`explanation` and
                the common IR envelope keys.

        Returns:
            The decoded `RefusalDetail`.
        """
        return cls(
            category=data.get("category"),
            explanation=data.get("explanation"),
            **cls._from_dict_common(data),
        )


@dataclass
class IncompleteDetail(IRObject):
    """Elaboration for truncated/paused stops (`max_tokens`, `paused`).

    Attributes:
        note: The provider's explanation of what was cut short or how to
            resume, when given.
        type: The detail discriminator, fixed to `DetailType.INCOMPLETE`.
    """

    # TODO: grow a typed resume handle (ProviderRef) once Anthropic
    # pause_turn resumption is exercised through a real edge.
    note: str | None = None
    type: Literal[DetailType.INCOMPLETE] = field(default=DetailType.INCOMPLETE)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build an `IncompleteDetail` from a serialized dict, totally.

        Args:
            data: A mapping with the optional `note` and the common IR
                envelope keys.

        Returns:
            The decoded `IncompleteDetail`.
        """
        return cls(note=data.get("note"), **cls._from_dict_common(data))


@dataclass
class ErrorDetail(IRObject):
    """Elaboration for error stops (`reason == "error"`).

    Distinct from the exception taxonomy: this is a *finish record* on a
    response that partially exists; a call that produced nothing raises
    instead.

    Attributes:
        code: The canonical error-taxonomy code, when mappable
            (e.g. `"transient"`).
        message: The provider's error message, verbatim.
        type: The detail discriminator, fixed to `DetailType.ERROR`.
    """

    code: str | None = None
    message: str | None = None
    type: Literal[DetailType.ERROR] = field(default=DetailType.ERROR)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build an `ErrorDetail` from a serialized dict, totally.

        Args:
            data: A mapping with the optional `code`/`message` and the
                common IR envelope keys.

        Returns:
            The decoded `ErrorDetail`.
        """
        return cls(
            code=data.get("code"),
            message=data.get("message"),
            **cls._from_dict_common(data),
        )


@dataclass
class DetailOpaque(IRObject):
    """Verbatim finish detail: deliberate opaque AND the unknown fallback.

    Serves two jobs the way `PartOpaque`/`PartUnknown` split them — kept as
    one type here because finish details are terminal metadata, never
    re-encoded into requests: a codec may deliberately park a
    provider-unique elaboration here, and `DETAIL_REGISTRY` falls back to it
    for tags this revision does not know. Byte-faithful through `to_dict`.

    Attributes:
        data: The verbatim serialized payload, including its original tag.
        type: The original discriminator value, preserved verbatim.
    """

    data: dict[str, Any] = field(default_factory=dict)
    type: str = DetailType.UNDEFINED.value

    def to_dict(self) -> dict[str, Any]:
        """Serialize back to the verbatim payload this instance preserved.

        Returns:
            A copy of the original serialized mapping, untouched.
        """
        return dict(self.data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Preserve a finish-detail payload verbatim.

        Args:
            data: The serialized mapping whose tag no registered detail
                matched (or that a codec deliberately parked here).

        Returns:
            A new `DetailOpaque` carrying the payload untouched.
        """
        tag = data.get("type")
        return cls(
            data=dict(data),
            type=tag if isinstance(tag, str) else DetailType.UNDEFINED.value,
        )


type FinishDetail = SafetyDetail | RefusalDetail | IncompleteDetail | ErrorDetail | DetailOpaque

# The open registry for the FinishDetail union. Unknown tags fall back to
# DetailOpaque — decoding a detail never raises.
DETAIL_REGISTRY: TagRegistry[Any] = TagRegistry(unknown=DetailOpaque)
DETAIL_REGISTRY.register(DetailType.SAFETY.value, SafetyDetail)
DETAIL_REGISTRY.register(DetailType.REFUSAL.value, RefusalDetail)
DETAIL_REGISTRY.register(DetailType.INCOMPLETE.value, IncompleteDetail)
DETAIL_REGISTRY.register(DetailType.ERROR.value, ErrorDetail)


def cast_detail(data: dict[str, Any]) -> FinishDetail:
    """Decode a serialized detail into its concrete `FinishDetail` variant.

    Dispatches on the `type` tag via `DETAIL_REGISTRY`; unknown tags decode
    to `DetailOpaque` — this function never raises on unknown input.

    Args:
        data: The serialized detail mapping, including its `type`
            discriminator.

    Returns:
        The decoded `FinishDetail` variant.
    """
    decoded: FinishDetail = DETAIL_REGISTRY.decode(data)
    return decoded


@dataclass
class FinishInfo(IRObject):
    """Why generation stopped — canonical code, native value, typed detail.

    Delivered on `ChatResponse.finish` and, for streams, on the terminal
    `StreamEnd.finish` (the authoritative one). The `StreamAccumulator`
    carries the last-seen finish into the folded response.

    Attributes:
        reason: The canonical open stop code; constants on `FinishReason`.
            Unknown wire values decode to `"unknown"`.
        native: The provider's verbatim wire value (e.g. `"length"`,
            `"end_turn"`, `"RECITATION"`), always preserved.
        detail: The typed elaboration, when the reason warrants one.
    """

    object: ClassVar[str] = "finish"

    reason: str = FinishReason.UNKNOWN
    native: str | None = None
    detail: FinishDetail | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `FinishInfo` from a serialized dict, totally.

        Args:
            data: A mapping with `reason`, the optional `native`, the
                nested `detail`, and the common IR envelope keys.

        Returns:
            The decoded `FinishInfo`.
        """
        detail = data.get("detail")
        return cls(
            reason=data.get("reason", FinishReason.UNKNOWN),
            native=data.get("native"),
            detail=cast_detail(detail) if isinstance(detail, dict) else None,
            **cls._from_dict_common(data),
        )
