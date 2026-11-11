"""The shared error taxonomy and its layered mapping.

Every failure ocai raises is one of these neutral classes (rule 8) so caller
code, policy hooks, and interceptors (retry, fallback) branch on a neutral type,
never a provider exception. Mapping a raw failure onto the taxonomy happens in
**two layers**, mirroring the streaming split (neutral parser + dialect codec):

1. **Neutral, status-based** — `error_from_response` here maps an HTTP status onto
   the coarse taxonomy (429 → `RateLimitError`, 5xx → `TransientError`, …). It is
   genuinely provider-agnostic (status codes are an HTTP universal) and is applied
   by the wire layer so retry policies can branch on `TransientError` immediately.
2. **Dialect-specific, body-based** — a codec's `map_error` (each provider
   interface subpackage ships one, e.g. `ocai.openai.chat_completions.codec`)
   refines that coarse error using the provider's error *body*, where the precise
   meaning actually lives (`context_length_exceeded`, content-filter blocks —
   conditions status alone cannot express). The driver applies it on top of the
   coarse error when an optional host mapper has not claimed classification.

`OcaiError.code` carries the provider's machine-readable code, the extensibility
hatch: a rare condition that doesn't merit its own subclass surfaces as a plain
`OcaiError(code=...)` while the named subclasses below stay stable and catchable.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from ocai.core.evidence import HostEvidence
    from ocai.core.fidelity import FidelityReport
    from ocai.core.usage import Usage


class OcaiError(Exception):
    """Base class for every error ocai raises.

    Carries optional neutral context so callers/middleware can inspect a failure
    without parsing a message string. `provider` / `status` / `retry_after`
    are populated by the transport when available. `raw` holds the provider's
    parsed error body when one was returned — **never** an auth header or secret.

    Attributes:
        provider: The provider name the failure came from, if known.
        status: The HTTP status code associated with the failure, if any.
        retry_after: Seconds to wait before retrying, when the provider supplied
            a `Retry-After` hint.
        code: The provider's machine-readable error code, when a dialect mapper
            extracted one (e.g. `"context_length_exceeded"`). The extension point
            for conditions that don't have a dedicated subclass.
        raw: The provider's parsed error body, when one was returned. Never holds
            an outgoing auth header or secret.
        response_headers: Detached incoming HTTP headers, or None if unavailable.
            Application evidence; never automatically exported to observers.
        response_body: Exact incoming body bytes, or None if unavailable.
        report: Known conversion/host accounting for a rejected execution.
        usage: Known consumption for a rejected execution; None means unknown.
        host_evidence: Optional detached host outcome evidence for application use.
    """

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        status: int | None = None,
        retry_after: float | None = None,
        code: str | None = None,
        raw: dict[str, Any] | None = None,
        response_headers: Mapping[str, str] | None = None,
        response_body: bytes | None = None,
        report: FidelityReport | None = None,
        usage: Usage | None = None,
        host_evidence: HostEvidence | None = None,
    ) -> None:
        """Construct an error with optional neutral provider context.

        Args:
            message: The human-readable error message passed to `Exception`.
            provider: The provider name the failure came from, if known.
            status: The HTTP status code associated with the failure, if any.
            retry_after: Seconds to wait before retrying, when known.
            code: The provider's machine-readable error code, if known.
            raw: The provider's parsed error body, if one was returned. Must
                never contain an auth header or secret.
            response_headers: Detached native response headers, or None when unavailable.
                Never outgoing authentication headers; not automatically logged.
            response_body: Exact native response bytes, or None when unavailable.
            report: Known conversion and host findings on a rejected outcome.
            usage: Known consumption on a rejected outcome, never assumed zero.
            host_evidence: Detached host outcome evidence, never automatically logged.
        """
        super().__init__(message)
        self.provider = provider
        self.status = status
        self.retry_after = retry_after
        self.code = code
        self.raw = raw
        self.response_headers = dict(response_headers) if response_headers is not None else None
        self.response_body = response_body
        self.report = deepcopy(report)
        self.usage = deepcopy(usage)
        self.host_evidence = deepcopy(host_evidence)


class StreamProtocolError(OcaiError):
    """A stream failed, was malformed, or ended without successful termination."""


class DeadlineExceededError(OcaiError):
    """The whole-call execution budget expired; retrying cannot extend it."""


class TransientError(OcaiError):
    """A retryable failure: 5xx, connection reset, timeout, overloaded (529)."""


class RateLimitError(TransientError):
    """Rate limited (HTTP 429). Retryable; honor `retry_after` when present."""


class AuthError(OcaiError):
    """Authentication/authorization failed (HTTP 401/403). Not retryable."""


class ContextLengthError(OcaiError):
    """The request exceeded the model's context window. Not retryable as-is."""


class ContentFilterError(OcaiError):
    """The request/response was blocked by a provider content filter/safety system."""


class UnsupportedFeatureError(OcaiError):
    """A profile-gated feature is declared `ABSENT` for the bound model.

    Raised by the facade's feature gate in **strict** mode, before the
    request is encoded and before any wire attempt — the request never
    leaves the process. The gate checked the request's feature keys against
    the catalog's `CapabilityProfile` facts for the resolved
    `(provider, interface)` and the bound model name, and at least one key
    resolved to `Support.ABSENT`. Annotate mode (the default) records the
    same facts as `UNSUPPORTED` field losses on the call's `FidelityReport`
    instead of raising.

    Attributes:
        features: The namespaced feature keys that resolved `ABSENT`.
        model: The bound model name the profile facts were checked against.
    """

    def __init__(
        self,
        message: str,
        *,
        features: tuple[str, ...] = (),
        model: str | None = None,
        provider: str | None = None,
    ) -> None:
        """Construct the strict-mode refusal.

        Args:
            message: The human-readable error message, naming the features
                and the model.
            features: The namespaced feature keys that resolved `ABSENT`.
            model: The bound model name the facts were checked against.
            provider: The provider the resolved route targets.
        """
        super().__init__(message, provider=provider)
        self.features = features
        self.model = model


def _retry_after_seconds(value: str | None) -> float | None:
    """Parse a `Retry-After` header value (delta-seconds form) to float."""
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        # TODO: support the HTTP-date form of Retry-After if a provider uses it.
        return None


def error_from_response(
    status: int,
    body: dict[str, Any] | None,
    *,
    provider: str | None = None,
    retry_after: str | None = None,
) -> OcaiError:
    """Map an HTTP status onto the coarse taxonomy — the neutral layer.

    The provider-agnostic, status-based half of error mapping (layer 1). It is the
    single source of truth for status → taxonomy and is what the wire layer raises,
    so retry policies can branch on `TransientError` without re-reading codes. A
    dialect's `map_error` refines the result from the body afterward (layer 2); it
    does not re-map status here.

    Args:
        status: The HTTP status code of the failed response.
        body: The provider's parsed error body, if any (attached as `raw`).
        provider: The provider name to stamp onto the error, if known.
        retry_after: The raw `Retry-After` header value, if present.

    Returns:
        The coarse `OcaiError` (subclass) for `status`.
    """
    ra = _retry_after_seconds(retry_after)
    kw: dict[str, Any] = {"provider": provider, "status": status, "raw": body}
    if status == 429:
        return RateLimitError("rate limited", retry_after=ra, **kw)
    if status in (401, 403):
        return AuthError("authentication failed", **kw)
    if status == 413:
        return ContextLengthError("request too large for the model context", **kw)
    if status == 529 or status >= 500:
        return TransientError("provider transiently unavailable", retry_after=ra, **kw)
    return OcaiError(f"provider request failed with status {status}", **kw)
