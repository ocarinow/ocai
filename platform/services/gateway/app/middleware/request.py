"""Stream-transparent ASGI request identity and allowlisted diagnostics."""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import asdict
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp
from starlette.types import Message
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send

from app.middleware.errors import error_response

_LOGGER = logging.getLogger("ocarinow.http")
_METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}


@dataclass(frozen=True, slots=True)
class RequestCompleted:
    """Diagnostic metadata, never durable audit or payload evidence."""

    request_id: str
    method: str
    route: str
    status: int | None
    outcome: Literal["completed", "failed", "interrupted", "cancelled"]
    duration_ms: float


def log_completion(event: RequestCompleted) -> None:
    """Log fixed metadata fields; logging setup belongs to the service."""
    _LOGGER.info(json.dumps(asdict(event), separators=(",", ":")))


class ResponseInterrupted(RuntimeError):
    """A response failed after headers; its original exception is not public."""


class RequestMiddleware:
    """Apply correlation and safe errors without reading or buffering bodies.

    Args:
        app: The next ASGI application.
        observer: A synchronous passive diagnostic sink. Its failures are isolated.
    """

    def __init__(
        self, app: ASGIApp, observer: Callable[[RequestCompleted], None] = log_completion
    ) -> None:
        self.app = app
        self.observer = observer

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Inbound correlation headers never establish server identity or authority.
        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.monotonic()
        status: int | None = None
        response_started = False
        response_complete = False
        outcome: Literal["completed", "failed", "interrupted", "cancelled"] = "interrupted"

        async def send_response(message: Message) -> None:
            nonlocal status, response_started, response_complete
            if message["type"] == "http.response.start":
                status = int(message["status"])
                headers = MutableHeaders(scope=message)
                headers["x-request-id"] = request_id
                headers["cache-control"] = "no-store"
                headers["x-content-type-options"] = "nosniff"
                response_started = True
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                response_complete = True

        try:
            await self.app(scope, receive, send_response)
            if response_complete:
                outcome = "completed" if status is not None and status < 500 else "failed"
        except asyncio.CancelledError:
            outcome = "cancelled"
            raise
        except Exception:
            if response_started:
                outcome = "interrupted"
                # Never splice JSON or a success event into an already started stream.
                raise ResponseInterrupted("Response interrupted.") from None
            outcome = "failed"
            response = error_response(
                500, "internal_error", "An internal error occurred.", request_id
            )
            await response(scope, receive, send_response)
        finally:
            method = str(scope.get("method", ""))
            route = getattr(scope.get("route"), "path", None)
            event = RequestCompleted(
                request_id=request_id,
                method=method if method in _METHODS else "OTHER",
                route=route if isinstance(route, str) else "unmatched",
                status=status,
                outcome=outcome,
                duration_ms=round((time.monotonic() - started) * 1000, 3),
            )
            try:
                self.observer(event)
            except Exception:
                _LOGGER.warning("Request diagnostic delivery failed.")
