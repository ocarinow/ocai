"""Typed view of the narrow AWS CRT public signing API (upstream is untyped).

These protocols describe upstream call signatures, not an alternative signer.
The real library is exercised by official vectors and recorded driver tests.
No SDK objects escape through the public ocai API.
"""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import Future
from datetime import datetime
from importlib import import_module
from io import BytesIO
from typing import Protocol
from typing import cast


class Headers(Protocol):
    def __iter__(self) -> Iterator[tuple[str, str]]: ...


class Request(Protocol):
    @property
    def headers(self) -> Headers: ...


class ProviderFactory(Protocol):
    def new_static(
        self, access_key_id: str, secret_access_key: str, session_token: str | None = None
    ) -> object: ...


class AuthModule(Protocol):
    AwsCredentialsProvider: ProviderFactory

    def AwsSigningConfig(
        self, *, credentials_provider: object, region: str, service: str, date: datetime
    ) -> object: ...

    def aws_sign_request(
        self, http_request: Request, signing_config: object
    ) -> Future[Request]: ...


class HttpModule(Protocol):
    def HttpHeaders(self, name_value_pairs: list[tuple[str, str]]) -> Headers: ...

    def HttpRequest(
        self, *, method: str, path: str, headers: Headers, body_stream: BytesIO
    ) -> Request: ...


def load() -> tuple[AuthModule, HttpModule]:
    """Load only public SDK value/signing modules, with their documented types."""
    return (
        cast(AuthModule, import_module("awscrt.auth")),
        cast(HttpModule, import_module("awscrt.http")),
    )
