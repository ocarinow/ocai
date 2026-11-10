"""Generation configuration: `ChatConfig` and its typed sub-configs (§3.1).

`ChatConfig` ships **full** — the empty-scaffold failure is over. Every field
here passed the three-lane knob law's first-class checklist (§3.4): supported
congruently by at least two or three interfaces, durable, and mappable with a
declarable `EdgeContract` disposition on every dialect. Provider-unique knobs
ride censused `extensions`; destination-specific passthrough rides
`provider_options` — the bags can never silently become the real schema.

Honesty rule (normative): out-of-range values pass **verbatim** with an
`APPROXIMATED` report — never rescaled, never clamped, never silent. The
codec's job is translation, not opinion.

`CacheHint` (per-part) and `CacheConfig` (per-request) are [provisional]:
provider caching surfaces are still converging and these freeze only after
they carry real traffic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Final
from typing import Self

from ocai.core.ir import IRObject
from ocai.core.ir import is_json_object
from ocai.core.jsonschema import Schema
from ocai.core.jsonschema import decode_schema
from ocai.core.refs import ProviderRef


class OutputMode:
    """Canonical constants for the open `OutputFormat.mode` code.

    Attributes:
        TEXT: Free-form text generation (the default).
        JSON: Provider-enforced syntactically-valid JSON, no schema.
        JSON_SCHEMA: Provider-enforced conformance to `OutputFormat.schema`.
    """

    TEXT: Final = "text"
    JSON: Final = "json"
    JSON_SCHEMA: Final = "json_schema"


class ReasoningEffort:
    """Canonical constants for the open `ReasoningConfig.effort` code.

    Attributes:
        LOW: Minimal reasoning budget.
        MEDIUM: Moderate reasoning budget.
        HIGH: Maximal reasoning budget.
    """

    LOW: Final = "low"
    MEDIUM: Final = "medium"
    HIGH: Final = "high"


@dataclass
class ReasoningConfig(IRObject):
    """How much the model should think, and whether thoughts are surfaced.

    Bridges the two native idioms — effort levels (OpenAI `/responses`) and
    token budgets (Anthropic, Gemini) — as sibling optionals: a request sets
    the one its author thinks in, and the codec maps or `APPROXIMATED`-reports
    the translation to the destination's idiom.

    Attributes:
        effort: The open effort code; canonical constants on
            `ReasoningEffort` (`low | medium | high`).
        budget_tokens: The maximum tokens the model may spend thinking.
        include_thoughts: Whether reasoning content should be surfaced as
            `PartReasoning` parts in the response.
    """

    effort: str | None = None
    budget_tokens: int | None = None
    include_thoughts: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `ReasoningConfig` from a serialized dict, totally.

        Args:
            data: A mapping with any of the reasoning fields plus the common
                IR envelope keys.

        Returns:
            The decoded `ReasoningConfig`.
        """
        return cls(
            effort=data.get("effort"),
            budget_tokens=data.get("budget_tokens"),
            include_thoughts=data.get("include_thoughts"),
            **cls._from_dict_common(data),
        )


@dataclass
class OutputFormat(IRObject):
    """The structured-output contract for a generation.

    Attributes:
        mode: The open output-mode code; canonical constants on `OutputMode`
            (`text | json | json_schema`).
        name: The schema's name, where the destination requires one (OpenAI
            `json_schema.name`).
        schema: The JSON Schema the output must conform to when `mode` is
            `json_schema`.
        strict: Whether the provider must enforce the schema exactly rather
            than best-effort.
    """

    mode: str = OutputMode.TEXT
    name: str | None = None
    schema: Schema | None = None
    strict: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build an `OutputFormat` from a serialized dict, totally.

        Args:
            data: A mapping with any of the output fields plus the common IR
                envelope keys; `schema` is decoded via `decode_schema`.

        Returns:
            The decoded `OutputFormat`.
        """
        raw_schema = data.get("schema")
        return cls(
            mode=data.get("mode", OutputMode.TEXT),
            name=data.get("name"),
            schema=decode_schema(raw_schema) if raw_schema is not None else None,
            strict=data.get("strict"),
            **cls._from_dict_common(data),
        )


@dataclass
class CacheHint(IRObject):
    """[provisional] A per-part prompt-caching marker.

    Carried on any part's `cache_hint` field (the shared part base); marks
    the position up to which the provider should cache the prompt prefix
    (Anthropic `cache_control` is the model). Interfaces with implicit
    caching report it `EMULATED` or `ABSENT` per their `CapabilityProfile`.

    Attributes:
        ttl: The requested cache lifetime as an open provider-shaped token
            (e.g. `"5m"`, `"1h"`), or None for the provider default.
    """

    # TODO: provisional — field set converges once OpenAI/Anthropic/Gemini
    # caching semantics are exercised through real edges.
    ttl: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `CacheHint` from a serialized dict, totally.

        Args:
            data: A mapping with an optional `ttl` plus the common IR
                envelope keys.

        Returns:
            The decoded `CacheHint`.
        """
        return cls(ttl=data.get("ttl"), **cls._from_dict_common(data))


@dataclass
class CacheConfig(IRObject):
    """[provisional] Request-level prompt-caching configuration.

    The request-scoped complement to per-part `CacheHint`s: it selects the
    caching regime and can name an existing provider-side cache to reuse.

    Attributes:
        mode: The open caching-mode code (`"auto" | "explicit" | "off"`),
            or None for the provider default.
        ref: An existing provider-side cache handle to generate against
            (Gemini `cachedContent`); a `ProviderRef`, so crossing another
            `(provider, interface)` is reported `UNSUPPORTED`.
    """

    # TODO: provisional — freeze after cache hits/misses are visible in Usage
    # (`UsageSource.CACHED`) across at least two providers.
    mode: str | None = None
    ref: ProviderRef | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `CacheConfig` from a serialized dict, totally.

        Args:
            data: A mapping with the optional `mode` and nested `ref` plus
                the common IR envelope keys.

        Returns:
            The decoded `CacheConfig`.
        """
        ref = data.get("ref")
        return cls(
            mode=data.get("mode"),
            ref=ProviderRef.from_dict(ref) if is_json_object(ref) else None,
            **cls._from_dict_common(data),
        )


@dataclass
class AudioOutputConfig(IRObject):
    """[provisional] Configuration for audio output generation.

    Consulted only when `"audio"` is among `ChatConfig.modalities`; the pair
    ships provisional because only one first-party interface (OpenAI
    `audio`) exercises it today.

    Attributes:
        voice: The provider voice identifier, verbatim.
        format: The requested audio container/encoding (e.g. `"wav"`,
            `"mp3"`, `"pcm16"`), as an open code.
    """

    # TODO: provisional — promoted to frozen once a second interface ships
    # congruent audio-output semantics.
    voice: str | None = None
    format: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build an `AudioOutputConfig` from a serialized dict, totally.

        Args:
            data: A mapping with the optional audio fields plus the common
                IR envelope keys.

        Returns:
            The decoded `AudioOutputConfig`.
        """
        return cls(
            voice=data.get("voice"),
            format=data.get("format"),
            **cls._from_dict_common(data),
        )


@dataclass
class ChatConfig(IRObject):
    """Provider-neutral generation configuration for a `ChatRequest`.

    Every field is optional; None means "provider default", and the codec
    emits nothing for it (omit-absent). `top_k` and `logprobs` are
    profile-gated: the feature gate consults the destination's
    `CapabilityProfile` before conversion, so an unsupported knob is refused
    (strict) or loss-reported (annotate) instead of silently dropped.

    Attributes:
        temperature: Sampling temperature, passed verbatim — out-of-range
            values are `APPROXIMATED`-reported, never clamped.
        top_p: Nucleus-sampling probability mass.
        max_output_tokens: The output token ceiling, reasoning included
            where the provider counts it that way (dialect codecs own the
            per-interface accounting shift).
        stop_sequences: Sequences that end generation when emitted.
        seed: Best-effort determinism seed.
        frequency_penalty: Repetition penalty scaled by frequency.
        presence_penalty: Repetition penalty for mere presence.
        parallel_tool_calls: Whether the model may emit several tool calls
            in one turn.
        top_k: Profile-gated top-k sampling cutoff.
        logprobs: Profile-gated count of top logprobs to return per token;
            None disables.
        modalities: The open output-modality codes requested
            (e.g. `["text", "audio"]`); None means text.
        audio: Audio-output settings, meaningful when `"audio"` is in
            `modalities` [provisional].
        reasoning: How much to think and whether thoughts are surfaced.
        output: The structured-output contract.
        cache: Request-level caching configuration [provisional].
    """

    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int | None = None
    stop_sequences: list[str] | None = None
    seed: int | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    parallel_tool_calls: bool | None = None
    top_k: int | None = None
    logprobs: int | None = None
    modalities: list[str] | None = None
    audio: AudioOutputConfig | None = None
    reasoning: ReasoningConfig | None = None
    output: OutputFormat | None = None
    cache: CacheConfig | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `ChatConfig` from a serialized dict, totally.

        The typed sub-configs (`audio`, `reasoning`, `output`, `cache`) are
        decoded through their own `from_dict`; scalar knobs pass through.

        Args:
            data: A mapping with any of the config fields plus the common IR
                envelope keys; unknown keys sweep to `extensions`.

        Returns:
            The decoded `ChatConfig`.
        """
        audio = data.get("audio")
        reasoning = data.get("reasoning")
        output = data.get("output")
        cache = data.get("cache")
        return cls(
            temperature=data.get("temperature"),
            top_p=data.get("top_p"),
            max_output_tokens=data.get("max_output_tokens"),
            stop_sequences=data.get("stop_sequences"),
            seed=data.get("seed"),
            frequency_penalty=data.get("frequency_penalty"),
            presence_penalty=data.get("presence_penalty"),
            parallel_tool_calls=data.get("parallel_tool_calls"),
            top_k=data.get("top_k"),
            logprobs=data.get("logprobs"),
            modalities=data.get("modalities"),
            audio=AudioOutputConfig.from_dict(audio) if is_json_object(audio) else None,
            reasoning=ReasoningConfig.from_dict(reasoning) if is_json_object(reasoning) else None,
            output=OutputFormat.from_dict(output) if is_json_object(output) else None,
            cache=CacheConfig.from_dict(cache) if is_json_object(cache) else None,
            **cls._from_dict_common(data),
        )
