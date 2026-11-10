"""Explicit pinned-model OpenFGA adapter with bounded, fail-closed HTTP operations."""

import asyncio
import json
import re
from dataclasses import dataclass
from dataclasses import field
from typing import Literal
from typing import cast
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from app.storage.repository import AuthorizationRecord

MODEL: dict[str, object] = {
    "schema_version": "1.1",
    "conditions": {},
    "type_definitions": [
        {"type": "principal", "relations": {}, "metadata": None},
        {
            "type": "organization",
            "relations": {
                "owner": {"this": {}},
                "viewer": {"this": {}},
                "can_read": {
                    "union": {
                        "child": [
                            {"computedUserset": {"object": "", "relation": "owner"}},
                            {"computedUserset": {"object": "", "relation": "viewer"}},
                        ]
                    }
                },
                "can_update": {"computedUserset": {"object": "", "relation": "owner"}},
            },
            "metadata": {
                "module": "",
                "source_info": None,
                "relations": {
                    role: {
                        "directly_related_user_types": [{"type": "principal", "condition": ""}],
                        "module": "",
                        "source_info": None,
                    }
                    for role in ("owner", "viewer")
                },
            },
        },
    ],
}


class AuthorizationUnavailable(Exception):
    """Current authorization cannot be established; never convert this to permission."""


@dataclass(frozen=True)
class FGASettings:
    endpoint: str
    store_id: str
    model_id: str
    token: str = field(repr=False)
    local: bool = False

    def __post_init__(self) -> None:
        try:
            endpoint = urlsplit(self.endpoint)
            valid = (
                self.endpoint.isascii()
                and len(self.endpoint) <= 512
                and bool(endpoint.hostname)
                and not (
                    endpoint.username or endpoint.password or endpoint.query or endpoint.fragment
                )
                and endpoint.path in {"", "/"}
                and (
                    endpoint.scheme == "https"
                    or (
                        self.local
                        and endpoint.scheme == "http"
                        and endpoint.hostname in {"127.0.0.1", "localhost", "::1"}
                    )
                )
                and bool(re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", self.store_id))
                and bool(re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", self.model_id))
                and 32 <= len(self.token) <= 4096
                and self.token.isascii()
                and not any(character.isspace() for character in self.token)
            )
            _ = endpoint.port
            if not valid:
                raise ValueError
        except ValueError:
            raise ValueError("Invalid authorization configuration.") from None


class OpenFGA:
    """Use a model verified at startup, never the server's latest model implicitly."""

    def __init__(self, settings: FGASettings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self._client = client
        self._ready = False

    async def _request(
        self, method: str, path: str, body: dict[str, object] | None = None
    ) -> dict[str, object]:
        try:
            async with asyncio.timeout(2):
                async with self._client.stream(
                    method,
                    self.settings.endpoint.rstrip("/") + "/stores/" + self.settings.store_id + path,
                    json=body,
                    headers={"Authorization": "Bearer " + self.settings.token},
                    follow_redirects=False,
                ) as response:
                    if response.status_code not in {200, 204}:
                        raise ValueError
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > 65536:
                            raise ValueError
            document: object = json.loads(data) if data else {}
            if not isinstance(document, dict):
                raise ValueError
            return cast(dict[str, object], document)
        except (ValueError, TypeError, TimeoutError, httpx.HTTPError):
            raise AuthorizationUnavailable(
                "Authorization service is temporarily unavailable."
            ) from None

    async def open(self) -> None:
        """Require the exact reviewed model before any checks or tuple writes."""
        self._ready = False
        document = await self._request("GET", "/authorization-models/" + self.settings.model_id)
        model = document.get("authorization_model")
        if not isinstance(model, dict):
            raise AuthorizationUnavailable("Authorization model is not qualified.")
        actual = cast(dict[str, object], model)
        expected = {"id": self.settings.model_id, **MODEL}
        if actual != expected:
            raise AuthorizationUnavailable("Authorization model is not qualified.")
        self._ready = True

    def _require_ready(self) -> None:
        if not self._ready:
            raise AuthorizationUnavailable("Authorization model is not qualified.")

    async def project(self, change: AuthorizationRecord) -> None:
        """Confirm one idempotent write; the caller owns ordering and durable acknowledgement."""
        self._require_ready()
        if change.role not in {"owner", "viewer"} or change.operation not in {"grant", "revoke"}:
            raise AuthorizationUnavailable("Authorization change is not qualified.")
        key = {
            "user": f"principal:{change.principal_id}",
            "relation": change.role,
            "object": f"organization:{change.organization_id}",
        }
        operation = "writes" if change.operation == "grant" else "deletes"
        conflict = "on_duplicate" if change.operation == "grant" else "on_missing"
        await self._request(
            "POST",
            "/write",
            {
                "authorization_model_id": self.settings.model_id,
                operation: {"tuple_keys": [key], conflict: "ignore"},
            },
        )

    async def check(
        self, organization_id: UUID, principal_id: UUID, action: Literal["read", "update"]
    ) -> bool:
        """Obtain a fresh decision without trusting it as a cross-database transaction."""
        self._require_ready()
        result = await self._request(
            "POST",
            "/check",
            {
                "authorization_model_id": self.settings.model_id,
                "consistency": "HIGHER_CONSISTENCY",
                "tuple_key": {
                    "user": f"principal:{principal_id}",
                    "relation": f"can_{action}",
                    "object": f"organization:{organization_id}",
                },
            },
        )
        allowed = result.get("allowed")
        if type(allowed) is not bool:
            raise AuthorizationUnavailable("Authorization decision is invalid.")
        return allowed
