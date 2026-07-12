"""Provider-anchored state: names for things that live on a provider's side.

A `ProviderRef` (architecture §2.4) names state held by a provider rather
than carried in the payload: `previous_response_id`, uploaded file handles,
reasoning thought signatures, audio ids. IR parts carry them as `anchor` /
`signature` / `opaque` fields, and `SourceRef` wraps one for provider-hosted
media.

The structural honesty rule the conversion graph enforces around this type
is **scoped** by the ref's `scope` (an open code; canonical constants on
`RefScope`):

- **interface-scoped** refs (the default) are `UNSUPPORTED` crossing any
  other `(provider, interface)` — reported, never silently dropped.
- **provider-scoped** refs survive same-provider sibling-interface crossings
  unreported (an OpenAI file id is valid across `chat_completions`,
  `responses`, and `batch`); crossing to another provider is `UNSUPPORTED`.
- **model-scoped** refs are additionally **breakage** when the bound
  resource changes (Gemini `cachedContents` are minted against one model);
  `qualifier` names the bound resource.

`replay` distinguishes anchors that are merely useful from anchors the
provider *requires back*: dropping a `REQUIRED` anchor (Gemini
`thoughtSignature`, Anthropic thinking signatures) produces a 400 on replay,
not degraded output, so the planner weights it as breakage, not mere loss.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import Final
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


class RefScope:
    """Canonical constants for the open `ProviderRef.scope` code.

    The scope names the boundary a ref is valid within, and therefore which
    conversions must report crossing it (the scoped honesty rule in the
    module docstring). Open: unknown scopes pass through verbatim and are
    treated as interface-scoped — the narrowest, most honest reading.

    Attributes:
        INTERFACE: Valid within the one `(provider, interface)` that minted
            it (response ids, thought signatures) — the default.
        PROVIDER: Valid across the provider's sibling interfaces (OpenAI
            file ids work from `chat_completions`, `responses`, and
            `batch`).
        MODEL: Bound to one resource below the interface (Gemini
            `cachedContents`); `ProviderRef.qualifier` names it.
    """

    INTERFACE: Final = "interface"
    PROVIDER: Final = "provider"
    MODEL: Final = "model"


@dataclass(frozen=True, slots=True)
class ProviderRef:
    """A name for state that lives on one provider's side.

    `scope` declares the validity boundary, and the graph enforces the
    scoped honesty rule against it: an interface-scoped ref is `UNSUPPORTED`
    crossing any other `(provider, interface)`; a provider-scoped ref
    survives same-provider sibling-interface crossings unreported and is
    `UNSUPPORTED` across providers; a model-scoped ref is additionally
    breakage when the bound resource (`qualifier`) changes.

    Attributes:
        provider: The provider that minted the ref (e.g. `"openai"`).
        interface: The interface within the provider (e.g. `"responses"`).
        kind: An open code for what the ref names — canonical constants
            include `"response_id"`, `"file"`, `"thought_signature"`,
            `"audio_id"`.
        id: The provider's opaque identifier, verbatim.
        replay: Whether the provider requires the ref back on follow-ups.
        scope: The open validity-scope code; constants on `RefScope`.
            Defaults to interface-scoped, the narrowest reading.
        qualifier: The bound resource for model-scoped refs (e.g. the model
            name a Gemini `cachedContent` was minted against); None for
            wider scopes.
    """

    provider: str
    interface: str
    kind: str
    id: str
    replay: Replay = Replay.OPTIONAL
    scope: str = RefScope.INTERFACE
    qualifier: str | None = field(default=None, kw_only=True)

    def __str__(self) -> str:
        """Return the compact label `provider/interface:kind:id`."""
        return f"{self.provider}/{self.interface}:{self.kind}:{self.id}"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the ref to a plain JSON-compatible dict, omit-absent.

        The default `scope` (`"interface"`) and an unset `qualifier` are
        omitted — the exact inverse of `from_dict`'s absent-means-interface
        reading, so pre-scope payloads round-trip byte-identically.

        Returns:
            A dict with `provider`, `interface`, `kind`, `id`, the `replay`
            string value, and the non-default `scope`/`qualifier` when set.
        """
        out: dict[str, Any] = {
            "provider": self.provider,
            "interface": self.interface,
            "kind": self.kind,
            "id": self.id,
            "replay": self.replay.value,
        }
        if self.scope != RefScope.INTERFACE:
            out["scope"] = self.scope
        if self.qualifier is not None:
            out["qualifier"] = self.qualifier
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `ProviderRef` from a serialized dict, totally.

        Tolerant per the total-decode rule: an unknown `replay` value falls
        back to `Replay.OPTIONAL` rather than raising, and `scope` is an
        open code — unknown values are kept verbatim; an absent scope reads
        as `"interface"` (the narrowest boundary).

        Args:
            data: A mapping with `provider`, `interface`, `kind`, `id`, and
                the optional `replay`/`scope`/`qualifier`.

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
            scope=data.get("scope", RefScope.INTERFACE),
            qualifier=data.get("qualifier"),
        )
