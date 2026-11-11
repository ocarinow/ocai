"""Reference-profile verification with adversarial signed credentials and bounded HTTP."""

import asyncio
import base64
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

import httpx
import pytest
from fastapi import Depends
from fastapi import FastAPI
from joserfc import jwt
from joserfc.jwk import RSAKey

from app.identity.dependencies import authenticated_identity
from app.identity.issuer import ExternalIdentity
from app.identity.issuer import IdentityUnavailable
from app.identity.issuer import InvalidToken
from app.identity.issuer import IssuerSettings
from app.identity.issuer import TokenVerifier
from app.main import create_app

ISSUER = "https://identity.example.test/realms/ocai"
SETTINGS = IssuerSettings(ISSUER, "ocai-management", "ocai-console")


def protected_app(verifier: TokenVerifier | None = None) -> FastAPI:
    """Exercise the real dependency without adding a product endpoint prematurely."""
    app = create_app()
    if verifier is not None:
        app.state.identity_verifier = verifier

    @app.get("/test/protected")
    async def protected(
        identity: Annotated[ExternalIdentity, Depends(authenticated_identity)],
    ) -> dict[str, str]:
        return {"issuer": identity.issuer, "subject": identity.subject}

    return app


@dataclass
class Issuer:
    key: RSAKey
    clock: float = 1000
    calls: int = 0
    fail: bool = False
    external: bool = False
    malformed: bool = False
    redirect: bool = False
    oversized: bool = False

    def request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        if self.fail:
            raise httpx.ConnectError("private infrastructure details")
        if self.redirect:
            return httpx.Response(302, headers={"location": "https://attacker.test/keys"})
        if self.oversized:
            return httpx.Response(200, content=b" " * 65537)
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "jwks_uri": "https://attacker.test/keys" if self.external else ISSUER + "/keys",
                },
            )
        assert str(request.url) == ISSUER + "/keys"
        return httpx.Response(200, json={"keys": [{}] if self.malformed else [self.key.as_dict()]})

    def token(self, **changes: object) -> str:
        claims: dict[str, object] = {
            "iss": ISSUER,
            "aud": ["account", "ocai-management"],
            "sub": "subject-one",
            "azp": "ocai-console",
            "typ": "Bearer",
            "iat": int(self.clock),
            "exp": int(self.clock) + 300,
        }
        claims.update(changes)
        return jwt.encode({"alg": "RS256", "kid": self.key.kid}, claims, self.key)


@pytest.fixture
def issuer() -> Issuer:
    return Issuer(key=RSAKey.generate_key(2048, parameters={"kid": "first"}))


@pytest.fixture
async def verifier(issuer: Issuer) -> AsyncIterator[TokenVerifier]:
    async with httpx.AsyncClient(transport=httpx.MockTransport(issuer.request)) as client:
        yield TokenVerifier(
            SETTINGS, client, monotonic=lambda: issuer.clock, now=lambda: int(issuer.clock)
        )


async def test_valid_identity_and_fresh_keys(issuer: Issuer, verifier: TokenVerifier) -> None:
    identity = await verifier.verify(issuer.token())
    assert identity == ExternalIdentity(ISSUER, "subject-one", "ocai-console", 1300)
    issuer.fail = True
    assert await verifier.verify(issuer.token()) == identity
    assert issuer.calls == 2


@pytest.mark.parametrize(
    "changes",
    [
        {"iss": "https://attacker.test"},
        {"aud": "another-api"},
        {"exp": 900},
        {"iat": 1100},
        {"exp": 2000},
        {"exp": True},
        {"iat": "1000"},
        {"typ": "ID"},
        {"azp": "another-client"},
        {"sub": ""},
        {"sub": 1},
        {"sub": "a" * 256},
        {"nbf": 2000},
    ],
)
async def test_signed_but_invalid_claims(
    issuer: Issuer,
    verifier: TokenVerifier,
    changes: dict[str, object],
) -> None:
    with pytest.raises(InvalidToken, match="Invalid access credential"):
        await verifier.verify(issuer.token(**changes))


@pytest.mark.parametrize("credential", ["", "a.b.c", "a" * 16385, "e30.e30.", "💥.x.x"])
async def test_malformed_never_fetches(
    issuer: Issuer,
    verifier: TokenVerifier,
    credential: str,
) -> None:
    with pytest.raises(InvalidToken):
        await verifier.verify(credential)
    assert issuer.calls == 0


async def test_untrusted_headers_and_wrong_signature(
    issuer: Issuer,
    verifier: TokenVerifier,
) -> None:
    for field in ("jku", "x5u", "jwk", "crit"):
        header = {"alg": "RS256", "kid": "first", field: "attacker"}
        token = base64.urlsafe_b64encode(json.dumps(header).encode()).decode() + ".e30.fake"
        with pytest.raises(InvalidToken):
            await verifier.verify(token)
    token = jwt.encode({"alg": "RS512", "kid": "first"}, {}, issuer.key, algorithms=["RS512"])
    with pytest.raises(InvalidToken):
        await verifier.verify(token)
    assert issuer.calls == 0
    wrong = RSAKey.generate_key(2048, parameters={"kid": "first"})
    token = jwt.encode({"alg": "RS256", "kid": "first"}, {}, wrong)
    with pytest.raises(InvalidToken):
        await verifier.verify(token)


async def test_rotation_single_flight_and_refresh_limit(
    issuer: Issuer,
    verifier: TokenVerifier,
) -> None:
    await verifier.verify(issuer.token())
    issuer.key = RSAKey.generate_key(2048, parameters={"kid": "second"})
    token = issuer.token()
    results = await asyncio.gather(
        *(verifier.verify(token) for _ in range(20)), return_exceptions=True
    )
    assert all(isinstance(result, InvalidToken) for result in results)
    assert issuer.calls == 2
    issuer.clock += 6
    verified = await asyncio.gather(*(verifier.verify(token) for _ in range(20)))
    assert all(identity.subject == "subject-one" for identity in verified)
    assert issuer.calls == 4


async def test_stale_cache_and_outage_fail_closed(
    issuer: Issuer,
    verifier: TokenVerifier,
) -> None:
    await verifier.verify(issuer.token())
    issuer.fail = True
    issuer.clock += 301
    for _ in range(3):
        with pytest.raises(IdentityUnavailable):
            await verifier.verify(issuer.token())
    assert issuer.calls == 3
    issuer.fail = False
    issuer.clock += 6
    assert (await verifier.verify(issuer.token())).subject == "subject-one"


@pytest.mark.parametrize("fault", ["external", "malformed", "redirect", "oversized"])
async def test_untrusted_discovery_rejected(
    issuer: Issuer,
    verifier: TokenVerifier,
    fault: str,
) -> None:
    setattr(issuer, fault, True)
    with pytest.raises(IdentityUnavailable):
        await verifier.verify(issuer.token())
    assert issuer.calls == (2 if fault == "malformed" else 1)


async def test_dependency_has_no_header_fallback(issuer: Issuer, verifier: TokenVerifier) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=protected_app(verifier)), base_url="http://test"
    ) as client:
        for headers in (
            {"X-User-ID": "admin", "X-Organization-ID": "other"},
            {"Authorization": "Basic forged"},
            {"Authorization": "Bearer malformed"},
            [("Authorization", "Bearer " + issuer.token()), ("Authorization", "Bearer forged")],
        ):
            response = await client.get("/test/protected", headers=headers)
            assert response.status_code == 401
            assert response.headers["www-authenticate"] == "Bearer"
            assert "forged" not in response.text
        response = await client.get(
            "/test/protected",
            headers={
                "Authorization": "Bearer " + issuer.token(),
                "X-User-ID": "admin",
            },
        )
        assert response.json()["subject"] == "subject-one"
        issuer.clock += 301
        issuer.fail = True
        response = await client.get(
            "/test/protected",
            headers={
                "Authorization": "Bearer " + issuer.token(),
            },
        )
        assert response.status_code == 503
        assert "private infrastructure" not in response.text


async def test_unconfigured_dependency_fails_closed_and_lifecycle() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=protected_app()), base_url="http://test"
    ) as client:
        response = await client.get("/test/protected", headers={"Authorization": "Bearer a.b.c"})
        assert response.status_code == 503
    app = create_app(identity=SETTINGS)
    assert not hasattr(app.state, "identity_verifier")
    async with app.router.lifespan_context(app):
        assert isinstance(app.state.identity_verifier, TokenVerifier)
    assert not hasattr(app.state, "identity_verifier")


@pytest.mark.parametrize(
    "issuer,local",
    [
        ("http://identity.test", False),
        ("http://identity.test", True),
        ("https://user:password@identity.test", False),
        (ISSUER + "?x=1", False),
        (ISSUER + "#fragment", False),
        ("http://localhost:invalid", True),
    ],
)
def test_unsafe_configuration(issuer: str, local: bool) -> None:
    with pytest.raises(ValueError, match="Invalid identity-provider configuration"):
        IssuerSettings(issuer, "api", "console", local=local)
