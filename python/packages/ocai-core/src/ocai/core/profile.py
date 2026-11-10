"""Declared capability facts: what an interface actually supports (§2.5).

A `CapabilityProfile` declares, as data, which feature keys a provider
interface supports for a family of models — `NATIVE`, `EMULATED`, or
`ABSENT`. It is consulted by the feature gate **before** payload conversion:
strict mode refuses an unsupported feature with a typed error; annotate mode
records the loss in the `FidelityReport` and proceeds.

The `model_pattern` dimension is required because support varies *below*
interface level (Anthropic's newest models reject `temperature`). Feature
keys are namespaced open data (`"chat.config.temperature"`,
`"chat.parts.audio"`), not a frozen taxonomy — a plugin can declare facts
about features core has never heard of.

Profiles ship inside a plugin's `CatalogFragment` and are provisional until
exercised (architecture status: [provisional]).
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class Support(str, Enum):
    """How a provider interface supports one feature for a model family.

    Attributes:
        NATIVE: The interface implements the feature first-class.
        EMULATED: ocai can reproduce the effect by other means; using it
            emits an `EMULATED` disposition (and usually a `SemanticShift`).
        ABSENT: Not available and not emulable; strict mode refuses, annotate
            mode reports the loss.
    """

    NATIVE = "native"
    EMULATED = "emulated"
    ABSENT = "absent"


@dataclass(frozen=True, slots=True)
class CapabilityProfile:
    """Declared feature support for one `(provider, interface, model_pattern)`.

    A frozen fact sheet, registered via a plugin's `CatalogFragment` and
    looked up by the feature gate with the concrete model name at call time.
    Multiple profiles for one interface may coexist with different
    `model_pattern`s; the catalog ranks the matches most-specific-first
    (`Catalog.profiles_for`) and the gate layers them — the first profile
    declaring a feature key wins (`resolve_support`).

    Attributes:
        provider: The provider the facts are about (e.g. `"anthropic"`).
        interface: The interface within the provider (e.g. `"messages"`).
        model_pattern: A glob-style pattern selecting the models the facts
            apply to (e.g. `"claude-4*"`, `"*"` for interface-wide facts).
        features: The declared mapping from namespaced feature key to its
            `Support` level. Treat as immutable — profiles are facts, not
            state.
    """

    provider: str
    interface: str
    model_pattern: str
    features: dict[str, Support] = field(default_factory=dict[str, Support])

    def matches(self, model: str) -> bool:
        """Return whether this profile's `model_pattern` covers `model`.

        Args:
            model: The concrete model name from the request.

        Returns:
            True when `model` falls inside `model_pattern`.
        """
        return fnmatchcase(model, self.model_pattern)

    def check_feature(self, feature: str, model: str) -> Support:
        """Return the declared support level for `feature` on `model`.

        The single-profile half of the feature gate: called before payload
        conversion so an `ABSENT` feature can be refused (strict) or
        loss-recorded (annotate) without ever building a doomed request.

        Undeclared policy (normative): a feature key absent from `features`
        resolves to `Support.NATIVE`. Profiles declare *exceptions* — the
        absence of a declared limitation is not a limitation. Defaulting the
        other way would force every profile to enumerate the whole open
        feature universe (impossible: keys are namespaced open data), and
        this default is what keeps profiles additive — declaring a new fact
        never changes the meaning of the ones already shipped.

        Args:
            feature: The namespaced feature key (e.g.
                `"chat.config.temperature"`).
            model: The concrete model name the request targets.

        Returns:
            The declared `Support` for the feature, or `Support.NATIVE` when
            this profile declares nothing about it.

        Raises:
            LookupError: When `model` does not match this profile's pattern.
        """
        if not self.matches(model):
            raise LookupError(
                f"model {model!r} is outside this profile's pattern "
                f"{self.model_pattern!r} ({self.provider}/{self.interface})"
            )
        return self.features.get(feature, Support.NATIVE)


def resolve_support(profiles: Sequence[CapabilityProfile], feature: str) -> Support:
    """Resolve one feature key across specificity-ranked profiles.

    The layering rule of the feature gate: `profiles` is expected
    most-specific-first (the order `Catalog.profiles_for` returns), the first
    profile that *declares* `feature` wins, and a key no profile declares
    resolves to `Support.NATIVE` — the same undeclared policy as
    `CapabilityProfile.check_feature`, applied across the stack (a specific
    sheet that is silent about a key never masks the interface-wide sheet
    that declares it).

    Args:
        profiles: The matching profiles, most specific first.
        feature: The namespaced feature key to resolve.

    Returns:
        The first declared `Support`, or `Support.NATIVE` when undeclared
        everywhere.
    """
    for profile in profiles:
        declared = profile.features.get(feature)
        if declared is not None:
            return declared
    return Support.NATIVE
