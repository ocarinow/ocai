"""Real Authorization Code + PKCE qualification against disposable reference Keycloak."""

import base64
import hashlib
import json
import runpy
import secrets
import subprocess
import time
from collections.abc import Callable
from collections.abc import Iterator
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import pytest
from joserfc import jwt
from joserfc.jwk import RSAKey

from app.identity.issuer import InvalidToken
from app.identity.issuer import IssuerSettings
from app.identity.issuer import TokenVerifier
from tests.test_identity import protected_app

ROOT = Path(__file__).resolve().parents[4]
REDIRECT = "http://localhost:3000/auth/callback"


def docker(*args: str) -> str:
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=False, timeout=120
    )
    if result.returncode:
        pytest.fail(f"Isolated Keycloak {args[0]} failed (details suppressed).", pytrace=False)
    return result.stdout.strip()


@dataclass(repr=False)
class Keycloak:
    issuer: str
    secret: str
    password: str


class LoginForm(HTMLParser):
    action: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "form" and attributes.get("id") == "kc-form-login":
            self.action = attributes.get("action") or ""


@pytest.fixture(scope="module")
def keycloak(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Keycloak]:
    """Use the development realm recipe; H2 is disposable protocol-test storage only."""
    helper = runpy.run_path(str(ROOT / "scripts/serve_platform.py"))
    recipe = cast(Callable[..., dict[str, object]], helper["realm_document"])
    secret, password = secrets.token_hex(32), secrets.token_hex(32)
    realm = tmp_path_factory.mktemp("identity") / "realm.json"
    realm.write_text(json.dumps(recipe(secret, password, redirect_uri=REDIRECT)))
    realm.chmod(0o644)
    name = "ocai-identity-test-" + uuid4().hex
    image = (ROOT / "platform/deploy/keycloak/image.txt").read_text().strip()
    try:
        docker(
            "create",
            "--name",
            name,
            "--publish",
            "127.0.0.1::8080",
            "--mount",
            f"type=bind,source={realm},target=/opt/keycloak/data/import/realm.json,readonly",
            image,
            "start-dev",
            "--import-realm",
        )
        docker("start", name)
        port = int(docker("port", name, "8080/tcp").rsplit(":", 1)[1])
        issuer = f"http://127.0.0.1:{port}/realms/ocai"
        with httpx.Client(timeout=2, trust_env=False, follow_redirects=False) as client:
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                try:
                    response = client.get(issuer + "/.well-known/openid-configuration")
                    if response.status_code == 200 and response.json().get("issuer") == issuer:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.5)
            else:
                pytest.fail("Isolated Keycloak did not become ready.", pytrace=False)
        yield Keycloak(issuer, secret, password)
    finally:
        subprocess.run(
            ["docker", "rm", "--force", "--volumes", name],
            capture_output=True,
            timeout=30,
            check=False,
        )
        realm.unlink(missing_ok=True)


async def login(keycloak: Keycloak) -> dict[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    state = secrets.token_urlsafe(32)
    endpoint = keycloak.issuer + "/protocol/openid-connect"
    async with httpx.AsyncClient(timeout=10, trust_env=False, follow_redirects=False) as client:
        page = await client.get(
            endpoint + "/auth",
            params={
                "client_id": "ocai-console",
                "response_type": "code",
                "scope": "openid",
                "redirect_uri": REDIRECT,
                "state": state,
                "nonce": secrets.token_urlsafe(32),
                "code_challenge": challenge.rstrip(b"=").decode(),
                "code_challenge_method": "S256",
            },
        )
        assert page.status_code == 200
        form = LoginForm()
        form.feed(page.text)
        assert urlsplit(form.action).netloc == urlsplit(keycloak.issuer).netloc
        # Browsers permit Secure cookies on trustworthy loopback origins. HTTPX
        # does not; reproduce that local-only behavior in this protocol fixture.
        for cookie in client.cookies.jar:
            cookie.secure = False
        result = await client.post(
            form.action,
            data={
                "username": "developer",
                "password": keycloak.password,
                "credentialId": "",
            },
        )
        assert result.status_code == 302, "Reference login must finish without required actions."
        location = result.headers["location"]
        assert location.startswith(REDIRECT + "?")
        parameters = parse_qs(urlsplit(location).query)
        assert parameters["state"] == [state]
        exchange = await client.post(
            endpoint + "/token",
            data={
                "grant_type": "authorization_code",
                "code": parameters["code"][0],
                "redirect_uri": REDIRECT,
                "code_verifier": verifier,
            },
            auth=httpx.BasicAuth("ocai-console", keycloak.secret),
        )
        assert exchange.status_code == 200
        # This endpoint's response is independently checked by the verifier below.
        return cast(dict[str, str], exchange.json())


@pytest.mark.identity
async def test_real_authorization_code_token_and_id_token_rejection(keycloak: Keycloak) -> None:
    credentials = await login(keycloak)
    settings = IssuerSettings(keycloak.issuer, "ocai-management", "ocai-console", local=True)
    async with httpx.AsyncClient(timeout=5, trust_env=False) as network:
        verifier = TokenVerifier(settings, network)
        identity = await verifier.verify(credentials["access_token"])
        assert identity.issuer == keycloak.issuer
        assert identity.subject
        with pytest.raises(InvalidToken):
            await verifier.verify(credentials["id_token"])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=protected_app(verifier)), base_url="http://test"
        ) as api:
            result = await api.get(
                "/test/protected",
                headers={
                    "Authorization": "Bearer " + credentials["access_token"],
                },
            )
            assert result.status_code == 200
            assert result.json()["subject"] == identity.subject
            key = RSAKey.generate_key(2048, parameters={"kid": "forged"})
            forged = jwt.encode({"alg": "RS256", "kid": "forged"}, {}, key)
            result = await api.get("/test/protected", headers={"Authorization": "Bearer " + forged})
            assert result.status_code == 401
