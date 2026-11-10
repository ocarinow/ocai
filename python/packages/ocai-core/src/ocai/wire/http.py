"""HTTP wire value objects — the contract crossing the `Transport` port.

These sit **below** the canonical IR: they are *not* `IRObject`s and carry no
`version` / `provider_options` / `extensions`. They are plain, detached,
picklable value objects so policies, interceptors, and observers can inspect,
key on, and store them without touching a live connection.

They are also the **audit-archive contract shape**: a `WireTap` policy
captures post-redaction `(HttpRequest, HttpResponse)` pairs in exactly this
form, and content-addressed archive satellites persist them — which is why an
offline audit tool (plugins depend on core+convert only, never on this
package's transports) can still re-convert archived traffic from these
records.

ocai owns its own request/response types rather than exposing
`httpx.Request` / `httpx.Response` through the port, so that:

- the `Transport` port stays client-agnostic (a fake transport is just
  `HttpResponse(200, {}, b"...")` — no httpx needed, rule 10);
- nothing above the `HttpxTransport` leaf imports httpx (rule 12);
- a response is a fully-read, detached snapshot, not bound to a stream.

The bodies are **bytes** on purpose: deterministic cache keys, honest payload
sizes for tracing, and a uniform shape with the byte stream from `stream`.
"""

from __future__ import annotations

import json as _json
from dataclasses import dataclass
from dataclasses import field
from typing import Any

_JSON_CONTENT_TYPE = "application/json"


@dataclass
class HttpRequest:
    """An outgoing HTTP request, already serialized to the wire.

    Built by the drivers (`ocai.runtime.drivers`) from the host's endpoint,
    envelope-wrapped body, and merged headers; judged by every
    `WirePolicy.on_request` while still unauthenticated; then copied with independent headers for
    `Credential.apply` at the driver leaf. Only this transport-only copy
    acquires authentication; the original remains safe for retained references
    and outcome hooks.

    `body` is the encoded payload (or `None`). Build a JSON request with
    `from_json`, which serializes the payload and sets `Content-Type`.
    """

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict[str, str])
    body: bytes | None = None
    stream: bool = False
    timeout: float | None = None

    @classmethod
    def from_json(
        cls,
        method: str,
        url: str,
        payload: dict[str, Any] | None,
        *,
        headers: dict[str, str] | None = None,
        stream: bool = False,
        timeout: float | None = None,
    ) -> HttpRequest:
        """Build a request whose body is `payload` JSON-encoded to bytes.

        Args:
            method: The HTTP method.
            url: The fully-qualified URL.
            payload: The JSON body, or `None` for a bodiless request.
            headers: Initial headers; `Content-Type` is set when a body is
                present and not already given.
            stream: Whether the response will be consumed as a stream.
            timeout: An optional per-request timeout override in seconds.

        Returns:
            The built request.
        """
        hdrs = dict(headers or {})
        body: bytes | None = None
        if payload is not None:
            body = _json.dumps(payload).encode("utf-8")
            hdrs.setdefault("Content-Type", _JSON_CONTENT_TYPE)
        return cls(method=method, url=url, headers=hdrs, body=body, stream=stream, timeout=timeout)


@dataclass
class HttpResponse:
    """A fully-read HTTP response: status, headers, and the body bytes.

    Returned by `Transport.send` / `SyncTransport.send_sync` on 2xx (non-2xx
    raises the shared taxonomy instead, so policies branch on error types,
    never on status codes). Rides `Outcome.response` through the on-outcome
    hooks, may be synthesized by a `Return` decision (a wire-cache hit), and
    pairs with its `HttpRequest` as the archived exchange record.
    """

    status: int
    headers: dict[str, str] = field(default_factory=dict[str, str])
    body: bytes = b""

    def json(self) -> Any:
        """Parse the body as JSON (`None` for an empty body).

        Returns:
            The decoded JSON value, or `None` when the body is empty.
        """
        return _json.loads(self.body) if self.body else None
