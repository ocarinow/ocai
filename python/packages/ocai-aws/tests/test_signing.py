"""Published AWS vectors exercise the real signer through the ocai credential."""

from __future__ import annotations

import json
import logging
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from ocai.aws import SigV4Credential
from ocai.core.credentials import Credential
from ocai.core.credentials import CredentialError
from ocai.wire.http import HttpRequest

ROOT = Path(__file__).parent
VECTORS: list[dict[str, Any]] = json.loads((ROOT / "aws_vectors.json").read_text())


def _request(text: str) -> HttpRequest:
    head, _, body = text.partition("\n\n")
    line, _, fields = head.partition("\n")
    method, _, target = line.partition(" ")
    target = target.removesuffix(" HTTP/1.1")
    headers = dict(line.split(":", 1) for line in fields.splitlines() if line)
    return HttpRequest(
        method, "https://" + headers["Host"] + target, headers, body.encode() or None
    )


@pytest.mark.parametrize("vector", VECTORS, ids=[v["name"] for v in VECTORS])
def test_official_vectors(vector: dict[str, Any], caplog: pytest.LogCaptureFixture) -> None:
    context = vector["context"]
    keys = context["credentials"]
    when = datetime.fromisoformat(context["timestamp"])
    credential: Credential = SigV4Credential(
        keys["access_key_id"],
        keys["secret_access_key"],
        session_token=keys.get("token"),
        region=context["region"],
        service=context["service"],
        clock=lambda: when,
    )
    request = _request(vector["request"])
    before = (request.method, request.url, request.body)
    with caplog.at_level(logging.DEBUG):
        credential.apply(request)
    expected = _request(vector["signed_request"])
    actual = {key.lower(): value for key, value in request.headers.items()}
    assert actual["authorization"] == expected.headers["Authorization"]
    assert (request.method, request.url, request.body) == before
    for value in keys.values():
        assert value not in repr(credential)
        assert value not in caplog.text
    # Reapplication replaces signatures instead of appending a second credential.
    credential.apply(request)
    assert {k.lower(): v for k, v in request.headers.items()} == actual


@pytest.mark.parametrize("field", ["access_key", "secret_key", "region", "session_token"])
@pytest.mark.parametrize("value", ["", " ", "\r\n"])
def test_empty_credentials_fail_without_echo(field: str, value: str) -> None:
    args = {
        "access_key": "synthetic-access",
        "secret_key": "synthetic-secret",
        "region": "us-east-1",
        "session_token": "synthetic-token",
    }
    args[field] = value
    with pytest.raises(CredentialError) as error:
        SigV4Credential(
            args["access_key"],
            args["secret_key"],
            region=args["region"],
            session_token=args["session_token"],
        )
    assert "synthetic" not in str(error.value)


@pytest.mark.parametrize(
    "url",
    [
        "not a URL",
        "https://user:secret@example.com/",
        "https://example.com/#fragment",
        "https://example.com:bad/",
        "https://example.com/?X-Amz-Signature=synthetic-secret",
    ],
)
def test_invalid_signing_does_not_expose_sdk_exception(url: str) -> None:
    credential = SigV4Credential("synthetic-access", "synthetic-secret", region="us-east-1")
    request = HttpRequest("POST", url, {"X-Test": "safe"}, b"{}")
    with pytest.raises(CredentialError) as error:
        credential.apply(request)
    assert str(error.value) == "AWS request signing failed"
    assert error.value.__context__ is None and error.value.__cause__ is None
    assert request.headers == {"X-Test": "safe"}


def test_clock_failure_and_naive_clock_are_sanitized() -> None:
    def fail() -> datetime:
        raise RuntimeError("synthetic-secret-token")

    for clock in (fail, lambda: datetime(2026, 1, 1)):
        credential = SigV4Credential("access", "secret", region="us-east-1", clock=clock)
        with pytest.raises(CredentialError) as error:
            credential.apply(HttpRequest("GET", "https://example.com"))
        assert error.value.__context__ is None
        assert "synthetic-secret" not in str(error.value)


def test_body_and_post_policy_header_are_signed() -> None:
    credential = SigV4Credential(
        "access", "secret", region="us-east-1", clock=lambda: datetime(2026, 1, 1, tzinfo=UTC)
    )
    signatures: list[str] = []
    for body, value in ((b"one", "first"), (b"two", "first"), (b"two", "second")):
        request = HttpRequest(
            "POST", "https://example.com/model/a%3A0/invoke?z=2&a=1", {"X-Test": value}, body
        )
        credential.apply(request)
        headers = {key.lower(): value for key, value in request.headers.items()}
        signatures.append(headers["authorization"])
        assert "x-test" in headers["authorization"]
        assert "x-amz-content-sha256" not in headers
    assert len(set(signatures)) == 3
