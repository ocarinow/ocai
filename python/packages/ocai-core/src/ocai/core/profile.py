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
    `model_pattern`s; the catalog picks the most specific match.

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
    features: dict[str, Support] = field(default_factory=dict)

    def matches(self, model: str) -> bool:
        """Return whether this profile's `model_pattern` covers `model`.

        Args:
            model: The concrete model name from the request.

        Returns:
            True when `model` falls inside `model_pattern`.
        """
        raise NotImplementedError  # TODO: fnmatch.fnmatchcase(model, self.model_pattern)

    def resolve(self, feature: str, model: str) -> Support:
        """Return the declared support level for `feature` on `model`.

        The feature gate's single entry point: called before payload
        conversion so an `ABSENT` feature can be refused (strict) or
        loss-recorded (annotate) without ever building a doomed request.

        Args:
            feature: The namespaced feature key (e.g.
                `"chat.config.temperature"`).
            model: The concrete model name the request targets.

        Returns:
            The declared `Support` for the feature.

        Raises:
            LookupError: When `model` does not match this profile's pattern.
        """
        # TODO: check matches(model); look up `feature` in `features`; decide
        # and document the default for undeclared feature keys (likely NATIVE
        # with a "undeclared" annotation, so profiles stay additive).
        raise NotImplementedError
