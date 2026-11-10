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
    """

    vendor: str
    first_party_headers: Mapping[str, str] = field(default_factory=dict[str, str])
    cloud_body_version: tuple[str, str] | None = None
    first_party_base_url: str | None = None
