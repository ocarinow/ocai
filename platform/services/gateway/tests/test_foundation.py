"""Exercise infrastructure through HTTP/ASGI rather than implementation mocks."""

import ast
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.types import Message
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send

from app.main import create_app
from app.middleware.request import RequestCompleted
from app.middleware.request import RequestMiddleware
from app.middleware.request import ResponseInterrupted

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.asyncio
async def test_status_liveness_and_readiness_are_distinct() -> None:
    events: list[RequestCompleted] = []
    app = create_app(observer=events.append)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        live = await client.get("/health/live")
        status = await client.get("/management/v1/status")
        ready = await client.get("/health/ready")
        missing = await client.get("/management/v1/organizations")
    assert live.json() == {"status": "alive"}
    assert status.json() == {
        "service": "ocai-gateway",
        "stage": "foundation",
        "inference_ready": False,
    }
    assert ready.status_code == 503
    assert ready.json()["error"]["code"] == "gateway_not_ready"
    assert missing.status_code == 404
    assert len(events) == 4
    assert events[2].outcome == "failed"
    for response in (live, status, ready, missing):
        assert UUID(response.headers["x-request-id"]).version == 4
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
    assert ready.json()["error"]["request_id"] == ready.headers["x-request-id"]


@pytest.mark.asyncio
async def test_concurrent_context_is_isolated_and_not_trusted_from_headers() -> None:
    events: list[RequestCompleted] = []
    app = create_app(observer=events.append)

    @app.get("/context")
    async def context(request: Request) -> dict[str, str | bool]:
        initial: str = request.state.request_id
        await asyncio.sleep(0)
        assert request.state.request_id == initial
        return {"request_id": initial, "tenant_present": hasattr(request.state, "tenant")}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        responses = await asyncio.gather(
            *[
                client.get("/context", headers={"x-request-id": "forged", "x-tenant-id": "admin"})
                for _ in range(30)
            ]
        )
    ids = {r.headers["x-request-id"] for r in responses}
    assert len(ids) == 30
    assert ids == {event.request_id for event in events}
    assert all(
        r.json() == {"request_id": r.headers["x-request-id"], "tenant_present": False}
        for r in responses
    )


@pytest.mark.asyncio
async def test_errors_and_diagnostics_exclude_input_and_exception_details(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="ocarinow.http")
    app = create_app()
    secret = "sensitive-test-marker"

    @app.get("/fail/{identifier}")
    async def fail(identifier: str) -> None:
        raise RuntimeError(identifier)

    @app.get("/validate")
    async def validate(count: int) -> int:
        return count

    @app.get("/deny")
    async def deny() -> None:
        raise HTTPException(403, detail=secret, headers={"x-sensitive": secret})

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        responses = [
            await client.get(f"/fail/{secret}?key={secret}", headers={"authorization": secret}),
            await client.get("/validate", params={"count": secret}),
            await client.get("/deny"),
            await client.get(f"/unknown/{secret}"),
        ]
    assert [r.status_code for r in responses] == [500, 422, 403, 404]
    for response in responses:
        assert secret not in response.text
        assert "x-sensitive" not in response.headers
        assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    diagnostic_records = [r for r in caplog.records if r.name == "ocarinow.http"]
    assert len(diagnostic_records) == 4
    assert all(secret not in r.getMessage() for r in diagnostic_records)
    assert json.loads(diagnostic_records[0].message)["route"] == "/fail/{identifier}"
    assert json.loads(diagnostic_records[-1].message)["route"] == "unmatched"


@pytest.mark.asyncio
async def test_passive_observer_failure_cannot_change_response(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def broken(_event: RequestCompleted) -> None:
        raise RuntimeError("private-observer-details")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(create_app(observer=broken)), base_url="http://test"
    ) as client:
        response = await client.get("/health/live")
        wrong_method = await client.post("/health/live")
    assert response.status_code == 200
    assert wrong_method.status_code == 405
    assert "GET" in wrong_method.headers["allow"]
    assert "private-observer-details" not in caplog.text


@pytest.mark.asyncio
async def test_stream_is_forwarded_incrementally_without_reading_request() -> None:
    events: list[RequestCompleted] = []
    messages: list[Message] = []
    first_chunk_delivered = asyncio.Event()

    async def app(_scope: Scope, _receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"first", "more_body": True})
        await asyncio.wait_for(first_chunk_delivered.wait(), timeout=1)
        await send({"type": "http.response.body", "body": b"last", "more_body": False})

    async def receive() -> Message:
        pytest.fail("middleware must not consume request bodies")

    async def send(message: Message) -> None:
        messages.append(message)
        if message.get("body") == b"first":
            first_chunk_delivered.set()

    await RequestMiddleware(app, events.append)({"type": "http", "method": "GET"}, receive, send)
    assert [m.get("body") for m in messages[1:]] == [b"first", b"last"]
    assert events[0].outcome == "completed"


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_stream_failure_does_not_append_success_or_error_body(cancel: bool) -> None:
    messages: list[Message] = []
    events: list[RequestCompleted] = []

    async def app(_scope: Scope, _receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"partial", "more_body": True})
        if cancel:
            raise asyncio.CancelledError
        raise RuntimeError("private-upstream-error")

    async def receive() -> Message:
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        messages.append(message)

    expected = asyncio.CancelledError if cancel else ResponseInterrupted
    with pytest.raises(expected) as error:
        await RequestMiddleware(app, events.append)(
            {"type": "http", "method": "GET"}, receive, send
        )
    assert len(messages) == 2
    assert "private-upstream-error" not in str(error.value)
    assert len(events) == 1
    assert events[0].outcome == ("cancelled" if cancel else "interrupted")
    assert "private-upstream-error" not in json.dumps(asdict(events[0]))


def test_openapi_contract_does_not_drift() -> None:
    expected = json.loads((ROOT / "platform/spec/management.openapi.json").read_text())
    assert create_app().openapi() == expected


def test_deployment_source_runs_without_repository_imports(tmp_path: Path) -> None:
    shutil.copytree(Path(__file__).parents[1] / "app", tmp_path / "app")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.main import create_app; "
            "assert create_app().title == 'Ocarinow management API'",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_public_libraries_do_not_import_platform_and_middleware_has_no_product_dependency() -> None:
    for path in (ROOT / "python/packages").rglob("*.py"):
        if ".venv" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            names = (
                [n.name for n in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            assert not any(n == "app" or n.startswith("app.") for n in names), path
    for path in (Path(__file__).parents[1] / "app/middleware").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(("app.main", "app.api")), path
