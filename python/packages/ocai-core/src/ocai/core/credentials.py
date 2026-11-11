"""Credentials: explicit-only, never ambient (rule 13).

ocai **never** auto-discovers credentials. It does not read `OPENAI_API_KEY`,
`~/.aws`, or any config file on its own. A credential enters the system only
when the caller passes one explicitly. The named constructors
`ApiKey.from_env` and `ApiKey.from_file` are the *only* places the
environment or filesystem is read — and only because the caller asked for that
source by name.

Credentials are applied **lazily, per attempt**, by the driver at the leaf of
the pipeline via `Credential.apply` — after every policy hook has seen the
request, so no hook, cache, or log can ever see a secret. The secret is never
written into the `raw` response, the `FidelityReport`, logs, or
`provider_options`, and `repr` / `str` redact it.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol
from typing import runtime_checkable

if TYPE_CHECKING:
    from ocai.wire.http import HttpRequest

_REDACTED = "***redacted***"


class CredentialError(OSError):
    """Raised when a credential cannot be supplied or located.

    A subclass of `OSError` (not `ocai.core.errors.OcaiError`)
    because it is a *configuration* problem at construction time, not a provider
    request failure.
    """


@runtime_checkable
class Credential(Protocol):
    """A credential that knows how to authenticate an outgoing request.

    Implementations mutate the transport-only request's headers in place
    (typically setting an auth header). Drivers copy the request and its mutable
    headers first; this object is never the one exposed to hooks. `apply` is
    called **once per attempt**, just before send, so
    a short-lived/rotating credential can resolve its current value at send time.
    Because it is applied at the driver leaf, the secret never enters a policy
    hook, an interceptor, the `raw` response, the `FidelityReport`, or logs.
    """

    def apply(self, request: HttpRequest) -> None:
        """Inject auth into `request` (an `HttpRequest`) in place."""
        ...


class NoCredential:
    """Explicit anonymous execution; never discover or inject authentication."""

    __slots__ = ()

    def apply(self, request: HttpRequest) -> None:
        """Leave the transport request unchanged."""

    def __repr__(self) -> str:
        """Return an unambiguous representation of the caller's explicit choice."""
        return "NoCredential()"


class ApiKey:
    """A bearer/API-key credential.

    Construct it explicitly — `ApiKey("sk-...")` — or via an opt-in named
    source: `ApiKey.from_env("OPENAI_API_KEY")` / `ApiKey.from_file(path)`.
    Constructing it with an empty key raises immediately; ocai never treats a
    missing key as "anonymous".
    """

    __slots__ = ("_key", "_header", "_scheme")

    def __init__(self, key: str, *, header: str = "Authorization", scheme: str = "Bearer") -> None:
        """Construct a bearer/API-key credential.

        Args:
            key: The secret key. Must be a non-empty, non-whitespace string;
                anything else raises immediately.
            header: The request header to set when applying the credential.
                Defaults to `"Authorization"`.
            scheme: The auth scheme prefix written before the key (e.g.
                `"Bearer <key>"`). Pass an empty string to send the bare key with
                no prefix. Defaults to `"Bearer"`.

        Raises:
            CredentialError: If `key` is empty, not a string, or only whitespace.
        """
        # The docstring promises `CredentialError`, not `AttributeError`, when an
        # untyped caller passes a non-string, so the guard stays.
        if not key or not isinstance(key, str) or not key.strip():  # pyright: ignore[reportUnnecessaryIsInstance]
            raise CredentialError(
                "ApiKey requires a non-empty key string. Pass one explicitly, e.g. "
                "ApiKey('sk-...'), or read it from a named source with "
                "ApiKey.from_env('OPENAI_API_KEY') or ApiKey.from_file(path)."
            )
        self._key = key
        self._header = header
        self._scheme = scheme

    @classmethod
    def from_env(cls, var: str, **kwargs: Any) -> ApiKey:
        """Read the key from environment variable `var` (the only env read)."""
        # Imported lazily and locally so merely importing this module never
        # touches the environment — the read happens only when from_env is called.
        import os

        value = os.environ.get(var)
        if not value:
            raise CredentialError(
                f"environment variable {var!r} is not set or empty. "
                f"Set it, or pass the key explicitly as ApiKey('...')."
            )
        return cls(value, **kwargs)

    @classmethod
    def from_file(cls, path: str | Path, **kwargs: Any) -> ApiKey:
        """Read the key from a file (the only filesystem read), stripped."""
        p = Path(path)
        try:
            value = p.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise CredentialError(f"could not read credential file {p}: {exc}") from exc
        if not value:
            raise CredentialError(f"credential file {p} is empty.")
        return cls(value, **kwargs)

    def apply(self, request: HttpRequest) -> None:
        """Inject the auth header into `request` in place.

        Sets `request.headers[header]` to `"<scheme> <key>"`, or to the bare key
        when `scheme` is empty. Called once per attempt by the driver at the
        leaf so the secret never enters a hook or interceptor.

        Args:
            request: The outgoing `HttpRequest` whose headers are mutated.
        """
        request.headers[self._header] = (
            f"{self._scheme} {self._key}" if self._scheme else self._key
        )

    # --- Redaction: a secret must never leak through repr/str/logging. -------
    def __repr__(self) -> str:
        """Return a redacted representation that never exposes the key."""
        return f"ApiKey({_REDACTED})"

    __str__ = __repr__

    def __eq__(self, other: object) -> bool:
        """Return whether `other` is an `ApiKey` wrapping the same secret."""
        return isinstance(other, ApiKey) and other._key == self._key

    def __hash__(self) -> int:
        """Return a hash based on object identity, never the secret."""
        # Hash the identity, not the secret, to avoid exposing it via hashing.
        return object.__hash__(self)


def require_credential(credentials: Credential | None) -> Credential:
    """Return `credentials` or raise a clear error naming how to supply one.

    Adapters call this in their constructor so that omitting a credential fails
    loudly instead of silently producing an unauthenticated client.
    """
    if credentials is None:
        raise CredentialError(
            "no credential supplied. Pass credentials=ApiKey('sk-...') (or use "
            "ApiKey.from_env('PROVIDER_API_KEY') / ApiKey.from_file(path)). "
            "ocai never reads credentials from the environment on its own."
        )
    return credentials
