"""Dialect traits: hosting-relevant facts a dialect declares as pure data.

`DialectTraits` lives in the contract layer — not in `ocai.wire` — because it
is *declared* by plugin interface subpackages (which may only import
`ocai.core` + `ocai.convert`) and merely *read* by the wire layer's hosts.
The dependency arrows stay clean: plugins declare traits as data; hosts
(`ocai.wire.hosting`) consume them generically at composition time.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field


def _headers(values: Mapping[str, str]) -> dict[str, str]:
    """Normalize explicit header names and reject ambiguous case aliases."""
    result: dict[str, str] = {}
    for name, value in values.items():
        key = name.lower()
        if key in result and result[key] != value:
            raise ValueError(f"conflicting header declaration: {key}")
        result[key] = value
    return result


@dataclass(frozen=True)
class HeaderBodyMapping:
    """Declare how one feature header becomes a host body field.

    Attributes:
        header: Feature header name, compared case-insensitively.
        field: Destination top-level body field.
        separator: Split into a string array on this separator, trimming surrounding
            whitespace. None preserves a scalar verbatim. Empty items are invalid.
    """

    header: str
    field: str
    separator: str | None = None

    def __post_init__(self) -> None:
        """Reject ambiguous declarations before composing an endpoint."""
        if not self.header or not self.field or self.separator == "":
            raise ValueError("header/body mapping requires names and a nonempty separator")
        object.__setattr__(self, "header", self.header.lower())


@dataclass(frozen=True)
class DialectTraits:
    """Hosting-relevant facts a dialect declares **as data**, read by any host.

    This is how the genuine (dialect, host) coupling — e.g. "Anthropic on a
    cloud needs `anthropic_version` in the body" — is expressed without a
    per-pair class. A host reads these traits generically, so the coupling
    costs a few fields, not a new combination of code. Plugins ship one
    `DialectTraits` per interface subpackage, registered into their
    `CatalogFragment`.

    Attributes:
        vendor: The publisher/provider identifier a cloud host uses to address
            the dialect (Vertex `publishers/<vendor>`, Bedrock provider id) and
            the default transport `provider` tag. E.g. `"anthropic"`, `"openai"`.
        first_party_headers: Headers the dialect requires when talked to
            directly (first-party), e.g. Anthropic's `anthropic-version`. A
            cloud host is free to ignore these (it owns its own header policy).
        cloud_body_version: An optional `(field, value)` a cloud host injects
            into the request body in place of a first-party version header
            (e.g. `("anthropic_version", "vertex-2023-10-16")`). `None` for
            dialects that need no such injection.
        first_party_base_url: The dialect's first-party API origin (e.g.
            `"https://api.openai.com"`, no trailing slash), or `None` for a
            dialect with no public first-party endpoint. Hosting data riding
            the fragment (§3.4/§7): the core front door composes a `Direct`
            binding from it without ever importing the plugin; a cloud or
            gateway host ignores it.
        version_headers: Explicit first-party wire-version headers; override the
            legacy header bag case-insensitively.
        feature_headers: Explicit opt-in feature headers, separate from versions.
            Empty by default: declaring a mapping never enables a beta feature.
        host_body_versions: Host key to `(field, value)`; an explicit entry wins
            over `cloud_body_version`. A None entry disables the legacy fallback.
        host_feature_body_mappings: Host key to feature-header relocation rules.
            Only declared feature values are relocated; no credentials belong here.
    """

    # New fields are appended to preserve positional construction of legacy traits.
    vendor: str
    first_party_headers: Mapping[str, str] = field(default_factory=dict[str, str])
    cloud_body_version: tuple[str, str] | None = None
    first_party_base_url: str | None = None
    version_headers: Mapping[str, str] = field(default_factory=dict[str, str])
    feature_headers: Mapping[str, str] = field(default_factory=dict[str, str])
    host_body_versions: Mapping[str, tuple[str, str] | None] = field(
        default_factory=dict[str, tuple[str, str] | None]
    )
    host_feature_body_mappings: Mapping[str, tuple[HeaderBodyMapping, ...]] = field(
        default_factory=dict[str, tuple[HeaderBodyMapping, ...]]
    )

    def __post_init__(self) -> None:
        """Snapshot caller maps and reject contradictory explicit declarations."""
        legacy = dict(self.first_party_headers)
        _headers(legacy)
        versions, features = _headers(self.version_headers), _headers(self.feature_headers)
        if versions.keys() & features.keys():
            raise ValueError("a header cannot be both a version and a feature")
        body_versions = dict(self.host_body_versions)
        mappings = {
            host: tuple(sorted(rules, key=lambda rule: (rule.header, rule.field)))
            for host, rules in self.host_feature_body_mappings.items()
        }
        for host, rules in mappings.items():
            version = body_versions.get(host, self.cloud_body_version)
            fields = {version[0]} if version else set[str]()
            headers: set[str] = set()
            for rule in rules:
                if rule.header in versions:
                    raise ValueError("version headers cannot be mapped as features")
                if rule.field in fields or rule.header in headers:
                    raise ValueError(f"conflicting body mapping for host: {host}")
                fields.add(rule.field)
                headers.add(rule.header)
        object.__setattr__(self, "first_party_headers", legacy)
        object.__setattr__(self, "version_headers", versions)
        object.__setattr__(self, "feature_headers", features)
        object.__setattr__(self, "host_body_versions", body_versions)
        object.__setattr__(self, "host_feature_body_mappings", mappings)

    def request_headers(self) -> dict[str, str]:
        """Return detached first-party headers, explicit groups over legacy values.

        Legacy casing is retained when not overridden. Explicit names use lowercase
        so a mixed-case fallback cannot become a second, contradictory header.
        """
        explicit = {**self.version_headers, **self.feature_headers}
        return {
            **{k: v for k, v in self.first_party_headers.items() if k.lower() not in explicit},
            **explicit,
        }

    def body_fields(self, host: str) -> dict[str, str | list[str]]:
        """Resolve detached version and declared feature values for one host.

        Args:
            host: Explicit host key, such as `vertex` or `bedrock`.

        Returns:
            Top-level field values for the host envelope, without modifying input.

        Raises:
            ValueError: A split feature value contains an empty item.
        """
        result: dict[str, str | list[str]] = {}
        version = self.host_body_versions.get(host, self.cloud_body_version)
        if version is not None:
            result[version[0]] = version[1]
        headers = _headers(self.request_headers())
        for rule in self.host_feature_body_mappings.get(host, ()):
            value = headers.get(rule.header)
            if value is None:
                continue
            if rule.separator is None:
                result[rule.field] = value
            else:
                items = [item.strip() for item in value.split(rule.separator)]
                if any(not item for item in items):
                    raise ValueError(f"empty feature item in header: {rule.header}")
                result[rule.field] = items
        return result
