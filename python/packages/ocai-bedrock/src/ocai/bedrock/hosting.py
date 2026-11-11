"""External Bedrock hosting; semantic codecs and AWS authentication stay separate."""

from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from ocai.bedrock.outcomes import error_mapping
from ocai.bedrock.outcomes import response_mapping
from ocai.core import UnsupportedFeatureError
from ocai.wire.hosting import Custom
from ocai.wire.hosting import EndpointSpec
from ocai.wire.hosting import EnvelopeTransform
from ocai.wire.outcomes import HostErrorMapper
from ocai.wire.outcomes import HostResponseAdapter


@dataclass(frozen=True)
class _InvokeEnvelope:
    spec: EndpointSpec
    beta: tuple[str, ...]
    guardrail_config: Mapping[str, Any] | None

    def wrap(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = deepcopy(payload)
        if result.get("stream"):
            raise UnsupportedFeatureError("Bedrock streaming is not qualified yet")
        if "model" in result and result["model"] != self.spec.resource:
            raise ValueError("payload model conflicts with the endpoint resource")
        result.pop("model", None)
        result.pop("stream", None)
        additions: dict[str, Any] = dict(self.spec.traits.body_fields("bedrock"))
        if self.beta:
            if "anthropic_beta" in additions and additions["anthropic_beta"] != list(self.beta):
                raise ValueError("conflicting Bedrock beta declarations")
            additions["anthropic_beta"] = list(self.beta)
        if self.guardrail_config is not None:
            additions["amazon-bedrock-guardrailConfig"] = deepcopy(dict(self.guardrail_config))
        for key, value in additions.items():
            if key in result and result[key] != value:
                raise ValueError(f"conflicting Bedrock body declaration: {key}")
            result[key] = value
        return result

    def unwrap(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload


@dataclass(frozen=True)
class Bedrock:
    """Host the qualified Anthropic Messages unary surface on InvokeModel.

    Region and credentials are explicit; this value performs no discovery or I/O.
    Pass it to ocai.chat.model with a separately supplied ocai credential. Optional
    endpoint_url is explicit deployment configuration, not a discovery mechanism.
    """

    region: str
    endpoint_url: str | None = None
    beta: tuple[str, ...] = ()
    guardrail_identifier: str | None = None
    guardrail_version: str | None = None
    guardrail_config: Mapping[str, Any] | None = None
    trace: str | None = None
    performance_latency: str | None = None
    service_tier: str | None = None
    static_headers: Mapping[str, str] = field(default_factory=dict[str, str])
    profile_aliases: Mapping[str, str] = field(default_factory=dict[str, str])

    def __post_init__(self) -> None:
        """Validate explicit configuration and detach caller-owned maps."""
        if not re.fullmatch(r"[a-z]{2}(?:-[a-z0-9]+)+-[0-9]+", self.region):
            raise ValueError("an explicit AWS region name is required")
        if (self.guardrail_identifier is None) != (self.guardrail_version is None):
            raise ValueError("guardrail identifier and version must be supplied together")
        if self.guardrail_config is not None and self.guardrail_identifier is None:
            raise ValueError("guardrail body configuration requires identifier and version")
        if any(
            key.lower() in {"anthropic-version", "anthropic-beta"} for key in self.static_headers
        ):
            raise ValueError("use declared body versions and beta, not static Anthropic headers")
        object.__setattr__(self, "beta", tuple(self.beta))
        object.__setattr__(self, "static_headers", dict(self.static_headers))
        object.__setattr__(self, "profile_aliases", dict(self.profile_aliases))
        object.__setattr__(self, "guardrail_config", deepcopy(self.guardrail_config))
        self._target()

    def _target(self) -> Custom:
        suffix = "amazonaws.com.cn" if self.region.startswith("cn-") else "amazonaws.com"
        origin = self.endpoint_url or f"https://bedrock-runtime.{self.region}.{suffix}"
        headers = dict(self.static_headers)
        headers.setdefault("accept", "application/json")
        for name, value in (
            ("x-amzn-bedrock-guardrailidentifier", self.guardrail_identifier),
            ("x-amzn-bedrock-guardrailversion", self.guardrail_version),
            ("x-amzn-bedrock-trace", self.trace),
            ("x-amzn-bedrock-performanceconfig-latency", self.performance_latency),
            ("x-amzn-bedrock-service-tier", self.service_tier),
        ):
            if value is not None:
                if name in headers and headers[name] != value:
                    raise ValueError(f"conflicting Bedrock header declaration: {name}")
                headers[name] = value
        return Custom(
            origin,
            paths={"generative": "/model/{resource}/invoke"},
            static_headers=headers,
            profile_aliases=self.profile_aliases,
        )

    @staticmethod
    def _qualify(spec: EndpointSpec) -> None:
        if spec.op.streaming:
            raise UnsupportedFeatureError("Bedrock streaming is not qualified yet")
        if (spec.dialect.provider, spec.dialect.interface, spec.op.kind) != (
            "anthropic",
            "messages",
            "generative",
        ):
            raise UnsupportedFeatureError("only Anthropic Messages InvokeModel is qualified")
        if spec.traits.host_body_versions.get("bedrock") is None:
            raise UnsupportedFeatureError("dialect has no explicit Bedrock version declaration")

    def endpoint(self, spec: EndpointSpec) -> str:
        """Place the unchanged resource in one encoded InvokeModel path segment."""
        self._qualify(spec)
        return self._target().endpoint(spec)

    def headers(self, spec: EndpointSpec) -> dict[str, str]:
        """Use trait-declared relocations and explicit non-secret host headers."""
        self._qualify(spec)
        result = self._target().headers(spec)
        relocated = {key.lower() for key in spec.traits.version_headers}
        relocated.update(
            rule.header for rule in spec.traits.host_feature_body_mappings.get("bedrock", ())
        )
        return {key: value for key, value in result.items() if key.lower() not in relocated}

    def envelope(self, spec: EndpointSpec) -> EnvelopeTransform:
        """Relocate provider-bound resource/version fields without copying codecs."""
        self._qualify(spec)
        config = self.guardrail_config
        if self.guardrail_identifier is not None and config is None:
            config = dict[str, Any]()
        return _InvokeEnvelope(spec, self.beta, config)

    def profile_key(self, resource: str) -> str:
        """Use explicit aliases only; a cloud model identifier is not qualification."""
        return self._target().profile_key(resource)

    def error_mapper(self, spec: EndpointSpec) -> HostErrorMapper:
        """Select public native error adaptation for this qualified operation."""
        self._qualify(spec)
        return error_mapping()

    def response_adapter(self, spec: EndpointSpec) -> HostResponseAdapter:
        """Select declared unary metadata and guardrail effects."""
        self._qualify(spec)
        return response_mapping()
