"""Hosting: where a request goes, composed as values — never subclassed.

A usable remote provider is **composed** from independent axes (dialect codec,
`Host`, transport, credential — see `ocai.runtime.binding.Binding`), never
subclassed per (dialect, host) pair. There is no `CloudProvider` base class
and no `AnthropicVertexModel` anywhere: hosting is a value you pass in, and
with *D* dialects and *H* hosts the code written is **D + H** while the usable
combinations are their product.

The pieces:

- `DialectTraits` (defined in `ocai.core.traits`, re-exported here) — the
  hosting-relevant facts a dialect declares **as data**, shipped by each
  plugin interface subpackage alongside its codec.
- `Operation` / `EndpointSpec` — the plain-data unit a driver executes and
  the bundle a host reads; a host never sees a codec, an IR, or an SDK.
- `EnvelopeTransform` / `IdentityEnvelope` — the optional body reshape a host
  applies on top of the dialect payload at send time.
- `Host` protocol with the value implementations `Direct` (first-party),
  `Custom` (self-hosted / gateway), and `Vertex` (Google Cloud
  `:rawPredict`).

Every host is **dialect-agnostic**: it reads the dialect's `DialectTraits`
from the `EndpointSpec` as plain data, so the same host value composes with
every dialect and every capability. The conversion graph operates only on
dialect `NodeId`s — it does not know clouds exist; hosting is resolved below
the graph, at send time, inside the drivers (`ocai.runtime.drivers`).

These hosts contain **no provider SDK and no signing** (rule 12); they are
pure URL/body/header logic. Real cloud auth is a separate `Credential` (e.g.
a Google OAuth/ADC bearer), and any narrow signing library would live in a
dedicated cloud-hosting plugin, never here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Protocol
from typing import runtime_checkable

from ocai.core.identity import NodeId
from ocai.core.traits import DialectTraits


@dataclass(frozen=True)
class Operation:
    """A single callable operation on a composed stack — the unit a driver runs.

    `Operation` is what lets one `Host` serve every capability without knowing
    chat from vectors: a host switches on `kind` (an endpoint family), never
    on a capability's semantics. Chat has one streaming operation; a vector
    store has several (`query`, `upsert`, `delete`).

    Attributes:
        name: The operation name (e.g. `"chat"`, `"embed"`, `"query"`).
        kind: The endpoint family a `Host` switches on (e.g. `"generative"`,
            `"embeddings"`, `"vector.query"`). Distinct from `name` so unrelated
            operations that share a URL shape can share a `kind`.
        method: The HTTP method for the operation. Defaults to `"POST"`.
        streaming: Whether the operation streams its response. Defaults to
            `False`.
    """

    name: str
    kind: str
    method: str = "POST"
    streaming: bool = False


@dataclass(frozen=True)
class EndpointSpec:
    """Everything a `Host` needs to place a request — passed as plain data.

    Assembled by the wire-backed facade (which alone knows the codec) and
    handed to a driver; the host receives it and never sees a codec, a
    capability IR, or an SDK. It carries the dialect identity, the dialect's
    declared traits, the operation being run, the target resource, and the
    dialect's own first-party path (so `Direct` can build a first-party URL
    without dialect-specific code).

    Attributes:
        dialect: The wire dialect's `NodeId` — the conversion-graph node the
            payload was encoded for.
        traits: The dialect's declared `DialectTraits`.
        op: The `Operation` being performed.
        resource: The model or index/collection name the operation targets.
        native_path: The dialect's first-party URL path for `op` (e.g.
            `"/v1/messages"`), used by first-party / gateway hosts.
    """

    dialect: NodeId
    traits: DialectTraits
    op: Operation
    resource: str
    native_path: str


@runtime_checkable
class EnvelopeTransform(Protocol):
    """An optional body reshape applied on top of a dialect payload at send time.

    Cloud hosts wrap/unwrap the dialect body (lift `model` into the URL,
    inject a cloud version field, peel a response envelope). First-party
    hosts use `IdentityEnvelope`. The driver calls `wrap` when building each
    attempt's request and `unwrap` on the response body before handing it
    back to the facade for graph decode.
    """

    def wrap(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Outgoing: dialect payload → host wire payload."""
        ...

    def unwrap(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Incoming: host wire payload → dialect payload."""
        ...


class IdentityEnvelope:
    """The no-op envelope: first-party hosts send the dialect payload as-is."""

    def wrap(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return the outgoing dialect payload unchanged.

        Args:
            payload: The outgoing dialect wire payload.

        Returns:
            The same `payload`, unmodified.
        """
        return payload

    def unwrap(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return the incoming host payload unchanged.

        Args:
            payload: The incoming host wire payload.

        Returns:
            The same `payload`, unmodified.
        """
        return payload


@runtime_checkable
class Host(Protocol):
    """Where a request goes: envelope + endpoint + headers, bundled.

    A host is **dialect-agnostic** — every method takes an `EndpointSpec`
    (plain data) so the same `Vertex(...)` value serves every dialect and
    every capability that Vertex can host. First-party, cloud, and gateway
    targets are all hosts; there is no `CloudProvider` base class. The
    drivers read the three methods in pipeline order: `envelope(spec).wrap`
    on the body, `endpoint(spec)` for the URL, `headers(spec)` merged under
    the binding's `extra_headers`.
    """

    def envelope(self, spec: EndpointSpec) -> EnvelopeTransform:
        """Return the body reshape this host applies for `spec`."""
        ...

    def endpoint(self, spec: EndpointSpec) -> str:
        """Return the fully-qualified URL for `spec`."""
        ...

    def headers(self, spec: EndpointSpec) -> Mapping[str, str]:
        """Return the headers this host contributes for `spec` (before auth)."""
        ...


@dataclass(frozen=True)
class Direct:
    """First-party hosting: the dialect's own URL, headers, and identity body.

    The degenerate composition — what every first-party provider uses. The full
    URL is `base_url` + the dialect's `native_path`; the headers are the
    dialect's declared `first_party_headers` (e.g. Anthropic's `anthropic-version`).

    Attributes:
        base_url: The provider's API origin, e.g. `"https://api.anthropic.com"`
            (no trailing slash; the dialect's `native_path` supplies the path).
    """

    base_url: str

    def envelope(self, spec: EndpointSpec) -> EnvelopeTransform:
        """Return the identity envelope: first-party sends the body unchanged.

        Args:
            spec: The endpoint spec for the request (unused).

        Returns:
            An `IdentityEnvelope`.
        """
        return IdentityEnvelope()

    def endpoint(self, spec: EndpointSpec) -> str:
        """Return `base_url` joined with the dialect's first-party path.

        Args:
            spec: The endpoint spec carrying the dialect's `native_path`.

        Returns:
            The fully-qualified first-party URL.
        """
        return f"{self.base_url}{spec.native_path}"

    def headers(self, spec: EndpointSpec) -> Mapping[str, str]:
        """Return the dialect's declared first-party headers.

        Args:
            spec: The endpoint spec carrying the dialect traits.

        Returns:
            The dialect's `first_party_headers`.
        """
        return spec.traits.first_party_headers


@dataclass(frozen=True)
class Custom:
    """A self-hosted or gateway target speaking a known dialect's wire.

    Covers OpenAI-compatible servers (vLLM, Ollama, LiteLLM), internal proxies,
    and staging endpoints: a fixed origin plus optional per-`kind` path templates.
    A template may interpolate `{resource}` (the model/index name). When no
    template is given for an operation's `kind`, the dialect's `native_path` is
    used, so a Custom host pointed at an OpenAI-compatible server needs no paths
    at all.

    Attributes:
        base_url: The origin to send to, e.g. `"https://vllm.internal"`.
        paths: Optional map of `Operation.kind` → path template. A template may
            contain `{resource}`. Defaults to empty (fall back to `native_path`).
    """

    base_url: str
    paths: Mapping[str, str] = field(default_factory=dict)

    def envelope(self, spec: EndpointSpec) -> EnvelopeTransform:
        """Return the identity envelope: a gateway speaks the dialect verbatim.

        Args:
            spec: The endpoint spec for the request (unused).

        Returns:
            An `IdentityEnvelope`.
        """
        return IdentityEnvelope()

    def endpoint(self, spec: EndpointSpec) -> str:
        """Return `base_url` joined with the per-kind template (or `native_path`).

        Args:
            spec: The endpoint spec carrying the operation kind, resource, and
                the dialect's `native_path`.

        Returns:
            The fully-qualified URL.
        """
        template = self.paths.get(spec.op.kind, spec.native_path)
        return f"{self.base_url}{template.format(resource=spec.resource)}"

    def headers(self, spec: EndpointSpec) -> Mapping[str, str]:
        """Return the dialect's first-party headers (a gateway mimics first-party).

        Args:
            spec: The endpoint spec carrying the dialect traits.

        Returns:
            The dialect's `first_party_headers`.
        """
        return spec.traits.first_party_headers


class _RawPredictEnvelope:
    """The body reshape Vertex AI's `:rawPredict` hosting needs, trait-driven.

    Vertex addresses the model in the URL, so `model` is dropped from the body;
    it signals streaming via the URL verb, so a `stream` flag is dropped; and a
    dialect that needs a cloud version field (its `cloud_body_version`, e.g.
    Anthropic's `anthropic_version`) gets it injected. The response is returned
    verbatim. This single envelope serves every dialect Vertex hosts — the
    per-dialect difference is read from `DialectTraits`, not coded per pair.
    """

    def __init__(self, spec: EndpointSpec) -> None:
        """Construct the envelope for `spec`'s dialect traits.

        Args:
            spec: The endpoint spec carrying the dialect traits to apply.
        """
        self._traits = spec.traits

    def wrap(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Reshape a first-party body into a Vertex `:rawPredict` body.

        Args:
            payload: The dialect's first-party request body.

        Returns:
            A new body with `model`/`stream` removed and any required cloud
            version field injected.
        """
        body = {k: v for k, v in payload.items() if k not in ("model", "stream")}
        if self._traits.cloud_body_version is not None:
            field_name, value = self._traits.cloud_body_version
            body.setdefault(field_name, value)
        return body

    def unwrap(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return the Vertex response unchanged (no response envelope).

        Args:
            payload: The raw Vertex response body.

        Returns:
            The same `payload`, unmodified.
        """
        return payload


@dataclass(frozen=True)
class Vertex:
    """Google Vertex AI hosting via the `:rawPredict` family of endpoints.

    Computes the URL from region/project, the dialect's `vendor` (the Vertex
    *publisher*), and the model; reshapes the body via `_RawPredictEnvelope`. The
    same `Vertex(...)` value hosts any dialect Vertex supports (Anthropic, Gemini,
    Llama, …) — proof that hosting composes rather than multiplies. Authentication
    is a separate Google OAuth/ADC `Credential`, not this host's concern.

    Attributes:
        project: The Google Cloud project id.
        region: The Vertex region, e.g. `"us-east5"`; also selects the regional
            API host.
    """

    project: str
    region: str

    # Vertex `:rawPredict` verb per operation kind. Generative ops use
    # rawPredict; embeddings use predict. Streaming overrides to streamRawPredict.
    _VERB_BY_KIND = {"generative": "rawPredict", "embeddings": "predict"}

    def envelope(self, spec: EndpointSpec) -> EnvelopeTransform:
        """Return the trait-driven `:rawPredict` body reshape for `spec`.

        Args:
            spec: The endpoint spec carrying the dialect traits.

        Returns:
            A `_RawPredictEnvelope` configured for the dialect.
        """
        return _RawPredictEnvelope(spec)

    def endpoint(self, spec: EndpointSpec) -> str:
        """Compute the Vertex `:rawPredict` URL for `spec`.

        Args:
            spec: The endpoint spec carrying the dialect `vendor` (publisher),
                the target model in `resource`, and the operation kind/stream.

        Returns:
            The fully-qualified Vertex prediction URL.
        """
        verb = self._VERB_BY_KIND.get(spec.op.kind, "rawPredict")
        if spec.op.streaming:
            verb = "streamRawPredict"
        return (
            f"https://{self.region}-aiplatform.googleapis.com/v1/projects/"
            f"{self.project}/locations/{self.region}/publishers/"
            f"{spec.traits.vendor}/models/{spec.resource}:{verb}"
        )

    def headers(self, spec: EndpointSpec) -> Mapping[str, str]:
        """Return no host headers — Vertex carries the version in the body.

        First-party version headers are deliberately *not* forwarded: Vertex
        injects the version into the body via the envelope (see
        `_RawPredictEnvelope`) and authenticates with a Google bearer credential.

        Args:
            spec: The endpoint spec for the request (unused).

        Returns:
            An empty mapping.
        """
        return {}
