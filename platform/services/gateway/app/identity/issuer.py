"""Bounded Keycloak-profile access-token verification using established JOSE primitives."""

import asyncio
import base64
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast
from urllib.parse import urlsplit

import httpx
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet
from joserfc.jwk import KeySetSerialization


class InvalidToken(Exception):
    """The supplied credential is invalid for this API."""


class IdentityUnavailable(Exception):
    """Required issuer metadata or verification keys cannot be established."""


@dataclass(frozen=True)
class IssuerSettings:
    issuer: str
    audience: str
    console_client_id: str
    local: bool = False

    def __post_init__(self) -> None:
        try:
            parsed = urlsplit(self.issuer)
            valid = (
                self.issuer.isascii()
                and 1 <= len(self.issuer) <= 512
                and bool(parsed.hostname)
                and not (parsed.username or parsed.password or parsed.query or parsed.fragment)
                and parsed.scheme == "https"
            )
            if self.local:
                valid = (
                    self.issuer.isascii()
                    and 1 <= len(self.issuer) <= 512
                    and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
                    and parsed.scheme in {"https", "http"}
                    and not (parsed.username or parsed.password or parsed.query or parsed.fragment)
                )
            if not valid or not self.audience or not self.console_client_id:
                raise ValueError
            _ = parsed.port
        except ValueError:
            raise ValueError("Invalid identity-provider configuration.") from None

    def permits(self, endpoint: str) -> bool:
        """Allow only the configured issuer's origin; never follow redirects."""
        try:
            issuer, target = urlsplit(self.issuer), urlsplit(endpoint)
            return (issuer.scheme, issuer.hostname, issuer.port) == (
                target.scheme,
                target.hostname,
                target.port,
            ) and not (target.username or target.password or target.fragment)
        except ValueError:
            return False


@dataclass(frozen=True)
class ExternalIdentity:
    issuer: str
    subject: str
    client_id: str
    expires_at: int


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("Expected an object.")
    # JSON object keys are strings; the cast narrows json.loads' untyped boundary.
    return cast(dict[str, object], value)


def _header(token: str) -> dict[str, object]:
    if not 1 <= len(token) <= 16384 or token.count(".") != 2:
        raise ValueError("Invalid compact token.")
    part = token.split(".", 1)[0]
    return _object(json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))))


class TokenVerifier:
    """Verify access credentials; possession does not establish platform membership."""

    def __init__(
        self,
        settings: IssuerSettings,
        client: httpx.AsyncClient,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        now: Callable[[], int] = lambda: int(time.time()),
    ) -> None:
        self._settings = settings
        self._client = client
        self._monotonic = monotonic
        self._now = now
        self._keys: KeySet | None = None
        self._loaded = float("-inf")
        self._attempted = float("-inf")
        self._lock = asyncio.Lock()
        self._failed = False

    async def _document(self, url: str) -> dict[str, object]:
        if not self._settings.permits(url):
            raise ValueError("Issuer endpoint is outside the configured origin.")
        async with asyncio.timeout(5):
            async with self._client.stream("GET", url, follow_redirects=False) as response:
                response.raise_for_status()
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 65536:
                        raise ValueError("Issuer document exceeds the size limit.")
        return _object(json.loads(body))

    async def _refresh(self) -> None:
        self._attempted = self._monotonic()
        try:
            metadata = await self._document(
                self._settings.issuer.rstrip("/") + "/.well-known/openid-configuration"
            )
            endpoint = metadata.get("jwks_uri")
            if metadata.get("issuer") != self._settings.issuer or not isinstance(endpoint, str):
                raise ValueError("Invalid issuer metadata.")
            document = await self._document(endpoint)
            raw_keys = document.get("keys")
            if not isinstance(raw_keys, list):
                raise ValueError("Invalid issuer key set.")
            entries = cast(list[object], raw_keys)
            if not 1 <= len(entries) <= 32:
                raise ValueError("Invalid issuer key set.")
            selected: list[dict[str, object]] = []
            kids: set[str] = set()
            for raw in entries:
                key = _object(raw)
                if key.get("kty") != "RSA" or key.get("use", "sig") != "sig":
                    continue
                if key.get("alg", "RS256") != "RS256":
                    continue
                kid, modulus = key.get("kid"), key.get("n")
                if (
                    not isinstance(kid, str)
                    or not 1 <= len(kid) <= 256
                    or kid in kids
                    or not isinstance(modulus, str)
                    or any(k in key for k in ("d", "p", "q", "dp", "dq", "qi", "oth"))
                ):
                    raise ValueError("Invalid issuer signing key.")
                bits = int.from_bytes(
                    base64.urlsafe_b64decode(modulus + "=" * (-len(modulus) % 4))
                ).bit_length()
                if not 2048 <= bits <= 8192:
                    raise ValueError("Unsupported RSA key strength.")
                kids.add(kid)
                selected.append(key)
            if not selected:
                raise ValueError("No qualified signing keys.")
            # The JOSE library validates the remaining JWK fields and key operations.
            keys = KeySet.import_key_set(cast(KeySetSerialization, {"keys": selected}))
        except (httpx.HTTPError, TimeoutError, ValueError, JoseError, TypeError, KeyError):
            self._failed = True
            raise IdentityUnavailable("Identity verification is temporarily unavailable.") from None
        self._keys = keys
        self._loaded = self._monotonic()
        self._failed = False

    async def _keyset(self, kid: str) -> KeySet:
        async with self._lock:
            fresh = self._monotonic() - self._loaded < 300
            known = self._keys is not None and any(key.kid == kid for key in self._keys.keys)
            if fresh and known:
                assert self._keys is not None
                return self._keys
            if self._monotonic() - self._attempted >= 5:
                await self._refresh()
            elif self._failed or not fresh:
                raise IdentityUnavailable("Identity verification is temporarily unavailable.")
            if self._keys is None or not any(key.kid == kid for key in self._keys.keys):
                raise InvalidToken("Invalid access credential.")
            return self._keys

    async def verify(self, credential: str) -> ExternalIdentity:
        """Verify the reference profile, returning only explicitly trusted identity fields.

        Raises:
            InvalidToken: The credential fails signature, profile or claim validation.
            IdentityUnavailable: Fresh verification keys cannot be established.
        """
        try:
            header = _header(credential)
            kid = header.get("kid")
            if (
                header.get("alg") != "RS256"
                or not isinstance(kid, str)
                or not 1 <= len(kid) <= 256
                or any(name in header for name in ("jku", "x5u", "jwk", "crit"))
            ):
                raise ValueError("Invalid protected header.")
        except (ValueError, TypeError):
            raise InvalidToken("Invalid access credential.") from None
        keys = await self._keyset(kid)
        try:
            token = jwt.decode(credential, keys, algorithms=["RS256"])
            claims = token.claims
            jwt.JWTClaimsRegistry(
                now=self._now,
                leeway=30,
                iss={"essential": True, "value": self._settings.issuer},
                aud={"essential": True, "value": self._settings.audience},
                exp={"essential": True},
                iat={"essential": True},
                sub={"essential": True},
            ).validate(claims)
            subject, expiry, issued = claims["sub"], claims["exp"], claims["iat"]
            if (
                not isinstance(subject, str)
                or not 1 <= len(subject) <= 255
                or type(expiry) is not int
                or type(issued) is not int
                or not 0 < expiry - issued <= 300
                or claims.get("typ") != "Bearer"
                or claims.get("azp") != self._settings.console_client_id
            ):
                raise ValueError("Invalid access-token profile.")
            return ExternalIdentity(
                self._settings.issuer, subject, self._settings.console_client_id, expiry
            )
        except (JoseError, ValueError, TypeError, KeyError):
            raise InvalidToken("Invalid access credential.") from None
