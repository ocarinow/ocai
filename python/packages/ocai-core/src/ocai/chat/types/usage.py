"""Usage accounting: the dimensional `Consumption` model (§3.1).

The dimensional model survives the re-architecture because it generalizes
across capabilities: a `Consumption` pins one measured value to open-string
dimensions — *what* was consumed (`UsageModality`), *how* it is counted
(`UsageUnit`), and *which bucket* of the call it belongs to (`UsageSource`).
All three dimensions are open codes (constants below), so a provider can
report a dimension core has never named without a release (rule 6).

Normalization rule (normative, per provider): buckets are **disjoint** —
`input` excludes cached input, `output` excludes reasoning where the
provider itemizes it — so `total_tokens` is a plain sum and no token is
ever counted twice. Each dialect codec documents how it maps its wire
fields onto the disjoint buckets.

The `currency` unit is **reserved** for gateway-reported cost (a gateway
that bills in dollars reports dollars); first-party *cost computation*
stays an interceptor's job, never the IR's — stance on record.

`Usage` aggregates consumptions and offers the ergonomic accessors
(`usage.input_tokens`, …) that make the dimensional model pleasant at call
sites. It is delivered on `CallResult.usage` and on streams' terminal
`StreamEnd.usage`.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import ClassVar
from typing import Final
from typing import Self

from ocai.core.ir import IRObject


class UsageModality:
    """Canonical constants for the open `Consumption.modality` code.

    Attributes:
        TEXT: Text content.
        IMAGE: Image content.
        AUDIO: Audio content.
        VIDEO: Video content.
    """

    TEXT: Final = "text"
    IMAGE: Final = "image"
    AUDIO: Final = "audio"
    VIDEO: Final = "video"


class UsageUnit:
    """Canonical constants for the open `Consumption.unit` code.

    Attributes:
        TOKENS: Counted in tokens (was `"token"` in the pre-2026-07 IR; the
            plural is canonical now).
        CHARACTERS: Counted in characters.
        REQUESTS: Counted in requests.
        SAMPLES: Counted in samples.
        CURRENCY: Reserved for gateway-reported cost; the value is an
            amount and the consumption's `extensions` carry the currency
            code. First-party cost stays an interceptor concern.
    """

    TOKENS: Final = "tokens"
    CHARACTERS: Final = "characters"
    REQUESTS: Final = "requests"
    SAMPLES: Final = "samples"
    CURRENCY: Final = "currency"


class UsageSource:
    """Canonical constants for the open `Consumption.source` code.

    The buckets are disjoint by the normalization rule: a token belongs to
    exactly one source.

    Attributes:
        INPUT: Prompt consumption, excluding cache reads.
        OUTPUT: Completion consumption, excluding itemized reasoning.
        REASONING: Reasoning/thinking consumption, where the provider
            itemizes it.
        CACHED: Cache-read input consumption.
    """

    INPUT: Final = "input"
    OUTPUT: Final = "output"
    REASONING: Final = "reasoning"
    CACHED: Final = "cached"


@dataclass(frozen=True, slots=True)
class Consumption:
    """One measured quantity, pinned to the dimensions that give it meaning.

    Attributes:
        modality: The open code for what kind of content was consumed;
            constants on `UsageModality`.
        unit: The open code for how the value is counted; constants on
            `UsageUnit`.
        source: The open code for which disjoint bucket of the call this
            belongs to; constants on `UsageSource`.
        value: The consumed amount.
    """

    modality: str
    unit: str
    source: str
    value: int | float | str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the consumption to a plain JSON-compatible dict.

        Returns:
            A dict with `value`, `modality`, `unit`, and `source`.
        """
        return {
            "value": self.value,
            "modality": self.modality,
            "unit": self.unit,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `Consumption` from a serialized dict, totally.

        The dimensions are open codes, so unknown strings pass through
        verbatim — never coerced, never raised on.

        Args:
            data: A mapping with `value` and the three dimension codes.

        Returns:
            The decoded `Consumption`.
        """
        return cls(
            value=data.get("value", 0),
            modality=data.get("modality", ""),
            unit=data.get("unit", ""),
            source=data.get("source", ""),
        )


@dataclass
class Usage(IRObject):
    """Aggregated consumption for one call — the capability's usage record.

    Built by the response codec (or, for streams, folded by the
    `StreamAccumulator` with the terminal `StreamEnd.usage` authoritative)
    and delivered on `CallResult.usage`. The accessor properties are views
    over the disjoint buckets; they never store anything.

    Attributes:
        consumptions: The measured consumptions for the call, in report
            order.
    """

    object: ClassVar[str] = "usage"

    consumptions: list[Consumption] = field(default_factory=list, kw_only=True)

    def _sum(self, unit: str, source: str | None = None) -> int:
        """Sum the numeric consumptions matching `unit` (and `source`).

        Non-numeric values (gateway strings) are skipped — the accessors
        report counts, and anything stringly stays reachable through
        `consumptions` itself.

        Args:
            unit: The unit code to match.
            source: The source code to match, or None to match every
                source.

        Returns:
            The summed value, as an int (token counts are integral).
        """
        total = 0
        for consumption in self.consumptions:
            if consumption.unit != unit:
                continue
            if source is not None and consumption.source != source:
                continue
            if isinstance(consumption.value, (int, float)):
                total += int(consumption.value)
        return total

    @property
    def input_tokens(self) -> int:
        """Return the non-cached prompt tokens consumed."""
        return self._sum(UsageUnit.TOKENS, UsageSource.INPUT)

    @property
    def output_tokens(self) -> int:
        """Return the completion tokens consumed, excluding reasoning."""
        return self._sum(UsageUnit.TOKENS, UsageSource.OUTPUT)

    @property
    def reasoning_tokens(self) -> int:
        """Return the itemized reasoning tokens consumed."""
        return self._sum(UsageUnit.TOKENS, UsageSource.REASONING)

    @property
    def cached_input_tokens(self) -> int:
        """Return the cache-read input tokens consumed."""
        return self._sum(UsageUnit.TOKENS, UsageSource.CACHED)

    @property
    def total_tokens(self) -> int:
        """Return every token consumed, across all disjoint buckets.

        A plain sum — valid precisely because the normalization rule makes
        the buckets disjoint.
        """
        return self._sum(UsageUnit.TOKENS)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `Usage` from a serialized dict, totally.

        Args:
            data: A mapping with `consumptions` and the common IR envelope
                keys.

        Returns:
            The decoded `Usage`.
        """
        return cls(
            consumptions=[
                Consumption.from_dict(item)
                for item in data.get("consumptions") or []
                if isinstance(item, dict)
            ],
            **cls._from_dict_common(data),
        )
