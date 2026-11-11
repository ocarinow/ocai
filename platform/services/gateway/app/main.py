"""Initial public, non-sensitive API; no tenant operations or inference yet."""

import logging
import os
from collections.abc import AsyncGenerator
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Literal

import httpx
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.authorization.openfga import FGASettings
from app.authorization.openfga import OpenFGA
from app.authorization.operator import fga_settings
from app.authorization.service import Authorization
from app.identity.issuer import IssuerSettings
from app.identity.issuer import TokenVerifier
from app.management.routes import router as management_router
from app.management.service import Management
from app.middleware.errors import ErrorEnvelope
from app.middleware.errors import error_response
from app.middleware.errors import install_error_handlers
from app.middleware.request import RequestCompleted
from app.middleware.request import RequestMiddleware
from app.middleware.request import log_completion
from app.storage.database import Database
from app.storage.settings import DatabaseSettings


class SystemStatus(BaseModel):
    service: Literal["ocai-gateway"] = "ocai-gateway"
    stage: Literal["foundation"] = "foundation"
    inference_ready: Literal[False] = False


class Liveness(BaseModel):
    status: Literal["alive"] = "alive"


def create_app(
    *,
    observer: Callable[[RequestCompleted], None] = log_completion,
    identity: IssuerSettings | None = None,
    database: DatabaseSettings | None = None,
    authorization: FGASettings | None = None,
) -> FastAPI:
    """Construct an isolated service instance with explicit shared infrastructure."""
    if (database is None) != (authorization is None) or (database is not None and identity is None):
        raise ValueError(
            "Management requires explicit identity, storage and authorization settings."
        )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
            if identity is not None:
                application.state.identity_verifier = TokenVerifier(identity, client)
            storage = Database(database) if database is not None else None
            try:
                if storage is not None and authorization is not None:
                    await storage.open()
                    fga = OpenFGA(authorization, client)
                    await fga.open()
                    application.state.management = Management(storage, Authorization(storage, fga))
                yield
            finally:
                if storage is not None:
                    if hasattr(application.state, "management"):
                        del application.state.management
                    await storage.close()
                if identity is not None:
                    del application.state.identity_verifier

    app = FastAPI(
        title="Ocarinow management API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    install_error_handlers(app)
    app.include_router(management_router)
    app.add_middleware(RequestMiddleware, observer=observer)

    @app.get("/health/live", operation_id="get_liveness")
    async def liveness() -> Liveness:
        return Liveness()

    @app.get(
        "/health/ready", status_code=503, response_model=ErrorEnvelope, operation_id="get_readiness"
    )
    async def readiness(request: Request) -> JSONResponse:
        return error_response(
            503,
            "gateway_not_ready",
            "Gateway inference is not configured.",
            request.state.request_id,
        )

    @app.get("/management/v1/status", operation_id="get_system_status")
    async def system_status() -> SystemStatus:
        return SystemStatus()

    return app


def create_configured_app() -> FastAPI:
    """Read explicit deployment settings only when the service entry point runs."""
    issuer = os.environ.get("OCAI_IDENTITY_ISSUER")
    if issuer is None:
        return create_app()
    local = os.environ.get("OCAI_LOCAL_DEVELOPMENT", "0")
    if local not in {"0", "1"}:
        raise ValueError("Invalid local development profile.")
    return create_app(
        database=DatabaseSettings.from_env("OCAI_DATABASE_URL", local=local == "1")
        if os.environ.get("OCAI_DATABASE_URL")
        else None,
        authorization=fga_settings(local=local == "1")
        if os.environ.get("OCAI_DATABASE_URL")
        else None,
        identity=IssuerSettings(
            issuer=issuer,
            audience=os.environ.get("OCAI_IDENTITY_AUDIENCE", ""),
            console_client_id=os.environ.get("OCAI_CONSOLE_CLIENT_ID", ""),
            local=local == "1",
        ),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    uvicorn.run(
        "app.main:create_configured_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        access_log=False,
        proxy_headers=False,
    )
