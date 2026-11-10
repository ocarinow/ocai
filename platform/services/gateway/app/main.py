"""Initial public, non-sensitive API; no tenant operations or inference yet."""

import logging
from collections.abc import Callable
from typing import Literal

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.middleware.errors import ErrorEnvelope
from app.middleware.errors import error_response
from app.middleware.errors import install_error_handlers
from app.middleware.request import RequestCompleted
from app.middleware.request import RequestMiddleware
from app.middleware.request import log_completion


class SystemStatus(BaseModel):
    service: Literal["ocai-gateway"] = "ocai-gateway"
    stage: Literal["foundation"] = "foundation"
    inference_ready: Literal[False] = False


class Liveness(BaseModel):
    status: Literal["alive"] = "alive"


def create_app(*, observer: Callable[[RequestCompleted], None] = log_completion) -> FastAPI:
    """Construct an isolated service instance with explicit shared infrastructure."""
    app = FastAPI(
        title="Ocarinow management API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    install_error_handlers(app)
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        access_log=False,
        proxy_headers=False,
    )
