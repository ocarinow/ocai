"""AWS-owned SigV4 signing at the detached transport credential boundary."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC
from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from ocai.aws import _sdk
from ocai.core.credentials import CredentialError

if TYPE_CHECKING:
    from ocai.wire.http import HttpRequest

_AUTH_HEADERS = frozenset(
    {"authorization", "x-amz-date", "x-amz-security-token", "x-amz-content-sha256"}
)


def _now() -> datetime:
    return datetime.now(UTC)


def _valid(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not any(c in value for c in "\r\n\0")


class SigV4Credential:
    """Sign a serialized request with explicit AWS credentials using AWS CRT.

    No default chain, environment, profile, network client or token refresh is
    used. The default service is Bedrock; region must be supplied explicitly.
    General SigV4 header signing is supported, not S3-specific signing, SigV4a,
    presigned URLs or streamed request bodies. Response streaming is supported.
    """

    __slots__ = ("_auth", "_http", "_provider", "_region", "_service", "_clock")

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        *,
        region: str,
        session_token: str | None = None,
        service: str = "bedrock",
        clock: Callable[[], datetime] = _now,
    ) -> None:
        """Create a credential without discovering or retrieving any secrets.

        Args:
            access_key: Explicit AWS access key identifier.
            secret_key: Explicit AWS secret access key.
            region: Region used in the signature scope.
            session_token: Optional explicit temporary session token.
            service: AWS signing service name; defaults to bedrock.
            clock: Aware UTC-compatible time source, read once per attempt.

        Raises:
            CredentialError: If inputs are empty or SDK initialization fails.
        """
        if not all(_valid(v) for v in (access_key, secret_key, region, service)) or (
            session_token is not None and not _valid(session_token)
        ):
            raise CredentialError("AWS credentials require non-empty, single-line values")
        self._region = region
        self._service = service
        self._clock = clock
        self._auth, self._http = _sdk.load()
        provider: object | None = None
        try:
            provider = self._auth.AwsCredentialsProvider.new_static(
                access_key, secret_key, session_token
            )
        except Exception:
            # Do not propagate SDK text or retain the original exception as context.
            provider = None
        if provider is None:
            raise CredentialError("AWS static credential initialization failed")
        self._provider = provider

    def apply(self, request: HttpRequest) -> None:
        """Sign a private SDK request, then copy its headers to the transport copy.

        The drivers must supply their independent transport request. Authentication
        headers are replaced on repeated application; request body, URL, timeout,
        attempt and governance context are not modified or passed to the SDK.

        Args:
            request: The detached, fully serialized transport request.

        Raises:
            CredentialError: If the URL, clock or signing operation is invalid.
        """
        signed: dict[str, str] | None = None
        try:
            url = urlsplit(request.url)
            if (
                url.scheme not in ("http", "https")
                or not url.hostname
                or url.username is not None
                or url.password is not None
                or url.fragment
            ):
                raise ValueError("invalid signing URL")
            host = url.hostname
            if ":" in host:
                host = f"[{host}]"
            if url.port is not None and url.port != (443 if url.scheme == "https" else 80):
                host += f":{url.port}"
            for key, value in request.headers.items():
                if key.lower() == "host" and value.lower() != host.lower():
                    raise ValueError("host header disagrees with signing URL")
            headers = {
                key: value
                for key, value in request.headers.items()
                if key.lower() not in _AUTH_HEADERS and key.lower() != "host"
            }
            headers["Host"] = host
            path = url.path or "/"
            if url.query:
                path += "?" + url.query
            when = self._clock()
            if when.tzinfo is None or when.utcoffset() is None:
                raise ValueError("signing clock must be timezone-aware")
            sdk_request = self._http.HttpRequest(
                method=request.method,
                path=path,
                headers=self._http.HttpHeaders(list(headers.items())),
                body_stream=BytesIO(request.body or b""),
            )
            config = self._auth.AwsSigningConfig(
                credentials_provider=self._provider,
                region=self._region,
                service=self._service,
                date=when.astimezone(UTC),
            )
            self._auth.aws_sign_request(sdk_request, config).result()
            signed = dict(sdk_request.headers)
        except Exception:
            # Signing may mention headers or keys in upstream exception messages.
            # Raise outside the handler so no secret-bearing exception is chained.
            signed = None
        if signed is None:
            raise CredentialError("AWS request signing failed")
        request.headers.clear()
        request.headers.update(signed)

    def __repr__(self) -> str:
        """Redact all credential material, including the access key identifier."""
        return "SigV4Credential(***redacted***)"
