"""Explicit installation bootstrap and projection commands; never exposed as HTTP endpoints."""

import argparse
import asyncio
import os
from uuid import UUID
from uuid import uuid4

import httpx

from app.authorization.openfga import AuthorizationUnavailable
from app.authorization.openfga import FGASettings
from app.authorization.openfga import OpenFGA
from app.authorization.service import AccessDenied
from app.authorization.service import Authorization
from app.identity.issuer import IssuerSettings
from app.storage.database import Database
from app.storage.database import StorageError
from app.storage.repository import BootstrapConsumed
from app.storage.settings import DatabaseSettings


def fga_settings(*, local: bool) -> FGASettings:
    """Read one explicitly requested authorization deployment."""
    return FGASettings(
        endpoint=os.environ.get("OCAI_FGA_ENDPOINT", ""),
        store_id=os.environ.get("OCAI_FGA_STORE_ID", ""),
        model_id=os.environ.get("OCAI_FGA_MODEL_ID", ""),
        token=os.environ.get("OCAI_FGA_TOKEN", ""),
        local=local,
    )


async def operate(args: argparse.Namespace) -> None:
    """Run the operator-selected transaction against explicit runtime credentials."""
    local = bool(args.local)
    database = Database(DatabaseSettings.from_env("OCAI_DATABASE_URL", local=local))
    try:
        await database.open()
        if args.operation == "status":
            async with database.transaction() as repository:
                state = await repository.installation()
            print(f"Installation: {state.installation_id}")
            print("Bootstrap: " + ("available" if state.organization_id is None else "consumed"))
            return
        async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
            fga = OpenFGA(fga_settings(local=local), client)
            await fga.open()
            if args.operation == "bootstrap":
                issuer = IssuerSettings(
                    os.environ.get("OCAI_IDENTITY_ISSUER", ""),
                    os.environ.get("OCAI_IDENTITY_AUDIENCE", ""),
                    os.environ.get("OCAI_CONSOLE_CLIENT_ID", ""),
                    local=local,
                )
                if not args.installation or not args.subject or not args.name:
                    raise ValueError("Bootstrap requires installation, subject and name.")
                async with database.transaction() as repository:
                    organization = await repository.bootstrap(
                        UUID(args.installation),
                        issuer=issuer.issuer,
                        subject=str(args.subject),
                        display_name=str(args.name),
                        store_id=fga.settings.store_id,
                        model_id=fga.settings.model_id,
                        request_id=uuid4(),
                    )
                print(f"Organization: {organization.id}; owner created, projection pending.")
            else:
                if not args.organization:
                    raise ValueError("Reconcile requires an organization.")
                applied = await Authorization(database, fga).reconcile(UUID(args.organization))
                print(f"Authorization revisions applied: {applied}; rerun to drain remaining work.")
    finally:
        await database.close()


def main() -> int:
    """Keep operator failures sanitized; no token, DSN or provider claim dumps."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("status", "bootstrap", "reconcile"))
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--installation")
    parser.add_argument(
        "--subject", help="Exact subject inspected by the operator in the trusted IdP"
    )
    parser.add_argument("--name", help="Initial organization display name")
    parser.add_argument("--organization")
    args = parser.parse_args()
    try:
        asyncio.run(operate(args))
    except BootstrapConsumed:
        print("Bootstrap is unavailable or already consumed; no owner was created.")
        return 1
    except (ValueError, StorageError, AuthorizationUnavailable, AccessDenied):
        print("Operator action failed; verify explicit settings, service availability and state.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
