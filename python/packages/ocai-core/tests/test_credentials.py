"""Credentials are explicit-only, redacted, and never ambient (rule 13)."""

from __future__ import annotations

import pytest

from ocai.core import ApiKey
from ocai.core import CredentialError
from ocai.core import require_credential
from ocai.wire import HttpRequest


def test_bare_credential_construction_raises() -> None:
    # An empty/missing key is never treated as "anonymous" — it fails loudly.
    with pytest.raises(CredentialError):
        ApiKey("")
    with pytest.raises(CredentialError):
        ApiKey("   ")


def test_repr_and_str_are_redacted() -> None:
    key = ApiKey("sk-supersecret")
    assert "sk-supersecret" not in repr(key)
    assert "sk-supersecret" not in str(key)
    assert "redacted" in repr(key)


def test_apply_sets_auth_header_lazily() -> None:
    request = HttpRequest("POST", "https://example.test")
    ApiKey("sk-xyz").apply(request)
    assert request.headers["Authorization"] == "Bearer sk-xyz"


def test_apply_supports_custom_header_and_bare_scheme() -> None:
    # Anthropic-style: bare key on a custom header, no scheme prefix.
    request = HttpRequest("POST", "https://example.test")
    ApiKey("k", header="x-api-key", scheme="").apply(request)
    assert request.headers["x-api-key"] == "k"


def test_from_env_reads_env_only_when_called(monkeypatch: pytest.MonkeyPatch) -> None:
    # Not set -> clear error naming the variable.
    monkeypatch.delenv("OCAI_TEST_KEY", raising=False)
    with pytest.raises(CredentialError) as exc:
        ApiKey.from_env("OCAI_TEST_KEY")
    assert "OCAI_TEST_KEY" in str(exc.value)

    # Set -> reads it at call time.
    monkeypatch.setenv("OCAI_TEST_KEY", "sk-from-env")
    cred = ApiKey.from_env("OCAI_TEST_KEY")
    req = HttpRequest("POST", "https://example.test")
    cred.apply(req)
    assert req.headers["Authorization"] == "Bearer sk-from-env"


def test_require_credential_raises_with_guidance() -> None:
    with pytest.raises(CredentialError) as exc:
        require_credential(None)
    msg = str(exc.value)
    assert "credentials=" in msg and "from_env" in msg
