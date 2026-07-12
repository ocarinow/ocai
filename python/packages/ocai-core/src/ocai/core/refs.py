"""Provider-anchored state: names for things that live on a provider's side.

A `ProviderRef` (architecture §2.4) names state held by a provider rather
than carried in the payload: `previous_response_id`, uploaded file handles,
reasoning thought signatures, audio ids. IR parts carry them as `anchor` /
`signature` / `opaque` fields, and `SourceRef` wraps one for provider-hosted
media.

The structural honesty rule the conversion graph enforces around this type:
**a `ProviderRef` crossing any other `(provider, interface)` boundary is
`UNSUPPORTED` — reported, never silently dropped.** A ref is meaningless
outside the interface that minted it, so pretending otherwise would be a
silent lie in a "lossless" report.

`replay` distinguishes anchors that are merely useful from anchors the
provider *requires back*: dropping a `REQUIRED` anchor (Gemini
`thoughtSignature`, Anthropic thinking signatures) produces a 400 on replay,
not degraded output, so the planner weights it as breakage, not mere loss.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Self


class Replay(str, Enum):
    """Whether a provider requires an anchor to be replayed verbatim.

    Attributes:
        OPTIONAL: The anchor is useful context (an id the caller *may* reuse);
            losing it degrades continuity but requests still succeed.
        REQUIRED: The provider rejects follow-up requests that omit the
            anchor. Planner cost treats dropping it as breakage.
    """

    OPTIONAL = "optional"
    REQUIRED = "required"


@dataclass(frozen=True, slots=True)
class ProviderRef:
    """A name for state that lives on one provider interface's side.

    Scoped by `(provider, interface)` because that is the boundary the ref is
    valid within — the graph consults exactly those two fields to decide
    whether a ref survives a conversion or must be reported `UNSUPPORTED`.

    Attributes:
        provider: The provider that minted the ref (e.g. `"openai"`).
        interface: The interface within the provider (e.g. `"responses"`).
        kind: An open code for what the ref names — canonical constants
            include `"response_id"`, `"file"`, `"thought_signature"`,
            `"audio_id"`.
        id: The provider's opaque identifier, verbatim.
        replay: Whether the provider requires the ref back on follow-ups.
    """

    provider: str
    interface: str
    kind: str
    id: str
    replay: Replay = Replay.OPTIONAL

    def __str__(self) -> str:
        """Return the compact label `provider/interface:kind:id`."""
        return f"{self.provider}/{self.interface}:{self.kind}:{self.id}"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the ref to a plain JSON-compatible dict.

        Returns:
            A dict with `provider`, `interface`, `kind`, `id`, and the
            `replay` string value.
        """
        return {
            "provider": self.provider,
            "interface": self.interface,
            "kind": self.kind,
            "id": self.id,
            "replay": self.replay.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `ProviderRef` from a serialized dict, totally.

        Tolerant per the total-decode rule: an unknown `replay` value falls
        back to `Replay.OPTIONAL` rather than raising.

        Args:
            data: A mapping with `provider`, `interface`, `kind`, `id`, and
                an optional `replay`.

        Returns:
            The decoded `ProviderRef`.
        """
        raw_replay = data.get("replay", Replay.OPTIONAL.value)
        try:
            replay = Replay(raw_replay)
        except ValueError:
            # TODO: unknown replay values need a reporting channel instead of
            # a silent OPTIONAL fallback.
            replay = Replay.OPTIONAL
        return cls(
            provider=data.get("provider", ""),
            interface=data.get("interface", ""),
            kind=data.get("kind", ""),
            id=data.get("id", ""),
            replay=replay,
        )
