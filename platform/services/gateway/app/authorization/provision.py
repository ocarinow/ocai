"""Explicit development/operator model provisioning; request paths never create stores."""

import asyncio
import json
import os
from typing import cast

import httpx

from app.authorization.openfga import MODEL
from app.authorization.openfga import AuthorizationUnavailable
from app.authorization.openfga import FGASettings
from app.authorization.openfga import OpenFGA


async def provision() -> dict[str, str]:
    """Create a store/model only when no configured pair exists, returning non-secret IDs."""
    store = os.environ.get("OCAI_FGA_STORE_ID", "")
    model = os.environ.get("OCAI_FGA_MODEL_ID", "")
    if bool(store) != bool(model):
        raise ValueError("Both authorization identifiers are required.")
    local = os.environ.get("OCAI_LOCAL_DEVELOPMENT", "0")
    if local not in {"0", "1"}:
        raise ValueError("Invalid development profile.")
    endpoint = os.environ.get("OCAI_FGA_ENDPOINT", "")
    token = os.environ.get("OCAI_FGA_TOKEN", "")
    # Validate endpoint/credential before the first operator request.
    settings = FGASettings(endpoint, store or "0" * 26, model or "0" * 26, token, local == "1")
    async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
        if not store:

            async def create(path: str, payload: dict[str, object], key: str) -> str:
                async with asyncio.timeout(2):
                    async with client.stream(
                        "POST",
                        endpoint.rstrip("/") + path,
                        json=payload,
                        headers={"Authorization": "Bearer " + token},
                        follow_redirects=False,
                    ) as response:
                        if response.status_code != 201:
                            raise AuthorizationUnavailable("Authorization provisioning failed.")
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > 65536:
                                raise ValueError("Oversized provisioning response.")
                value: object = json.loads(body)
                if not isinstance(value, dict):
                    raise ValueError("Invalid provisioning response.")
                identifier = cast(dict[str, object], value).get(key)
                if not isinstance(identifier, str):
                    raise ValueError("Invalid provisioning identifier.")
                return identifier

            store = await create("/stores", {"name": "ocai-platform"}, "id")
            # Validate before interpolating an upstream value into a path.
            settings = FGASettings(endpoint, store, "0" * 26, token, local == "1")
            model = await create(
                f"/stores/{settings.store_id}/authorization-models", MODEL, "authorization_model_id"
            )
            settings = FGASettings(endpoint, store, model, token, local == "1")
        await OpenFGA(settings, client).open()
    return {"OCAI_FGA_STORE_ID": store, "OCAI_FGA_MODEL_ID": model}


def main() -> int:
    """Print only non-secret deployment IDs after exact model validation."""
    try:
        identifiers = asyncio.run(provision())
    except (ValueError, AuthorizationUnavailable, TimeoutError, httpx.HTTPError):
        print(
            "Authorization provisioning failed; verify explicit settings and service availability."
        )
        return 1
    print(json.dumps(identifiers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
