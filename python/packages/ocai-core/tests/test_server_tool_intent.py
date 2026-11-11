"""WU-41: distinguish server intent and reject unsupported conversion before I/O."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import respx

import ocai.anthropic
import ocai.chat
import ocai.openai
from ocai.chat import ServerTool
from ocai.chat import ServerToolLocation
from ocai.chat import ToolUnknown
from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.chat.types import StreamAccumulator
from ocai.chat.types import Tool
from ocai.convert import Catalog
from ocai.core import ApiKey
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import FidelityPolicy
from ocai.core.fidelity import FidelityPolicyError
from ocai.wire.transport import HttpxTransport

type LoadHttp = Callable[[str], dict[str, Any]]


def test_mixed_tool_roundtrip_is_open_and_preserves_legacy_shape(spec_dir: Path) -> None:
    document = json.loads((spec_dir / "fixtures/canonical/server_tools.json").read_text())[
        "document"
    ]
    request = ChatRequest.from_dict(document)
    assert request.tools
    assert isinstance(request.tools[0], Tool)
    assert isinstance(request.tools[1], ServerTool)
    assert isinstance(request.tools[2], ToolUnknown)
    assert request.to_dict() == document
    assert "type" not in request.tools[0].to_dict()
    assert ServerTool(kind="future_search").kind == "future_search"
    empty = ServerTool("web_search", allowed_domains=[], blocked_domains=[])
    assert empty.to_dict()["allowed_domains"] == []
    assert ServerTool.from_dict(empty.to_dict()).to_dict() == empty.to_dict()
    assert request.tools[1].user_location == ServerToolLocation(country="FR", city="Paris")
    # Unknown payloads and caller-owned mutable domain lists are detached.
    document["tools"][2]["future_payload"]["meaning"].append(4)
    document["tools"][1]["allowed_domains"].append("mutated.test")
    assert request.tools[2].to_dict()["future_payload"]["meaning"] == [1, 2, 3]
    assert request.tools[1].allowed_domains == ["example.test"]


@pytest.mark.parametrize(
    "entry",
    [
        None,
        7,
        [],
        "future",
        {"type": ["future"]},
        {"type": None},
        {"type": "server", "extensions": "opaque"},
        {"name": "legacy", "parameters": 7},
    ],
)
def test_unknown_tool_entries_survive_without_function_semantics(entry: Any) -> None:
    request = ChatRequest.from_dict({"messages": [], "tools": [entry]})
    assert request.tools and isinstance(request.tools[0], ToolUnknown)
    assert request.to_dict()["tools"] == [entry]


def test_server_unknown_fields_and_malformed_location_preserve_evidence() -> None:
    server = ServerTool.from_dict(
        {"kind": "future", "future_control": 7, "user_location": "future"}
    )
    assert server.extensions["future_control"] == 7
    assert server.extensions["ocai.server_tool_unparsed_location"] == "future"
    assert ServerTool.from_dict(server.to_dict()).to_dict() == server.to_dict()
    location = ServerToolLocation.from_dict({"country": "FR", "future_precision": 5})
    assert location.extensions["future_precision"] == 5


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
@pytest.mark.parametrize("mode", ["sync", "async", "stream", "astream"])
async def test_unsupported_server_intent_is_inspectable_and_denied_before_io(
    provider: str,
    mode: str,
) -> None:
    transport = HttpxTransport(provider=provider)
    model = ocai.chat.model(
        provider + ("/gpt-4o" if provider == "openai" else "/claude-opus-4-6"),
        credentials=ApiKey("sk-test"),
        transport=transport,
        catalog=Catalog.of(
            ocai.openai.FRAGMENT if provider == "openai" else ocai.anthropic.FRAGMENT
        ),
        conversion_policy=FidelityPolicy(
            forbidden_dispositions=frozenset({Disposition.UNSUPPORTED})
        ),
    )
    request = ChatRequest(messages=[Message.user("Hello")], tools=[ServerTool("web_search")])
    try:
        prepared = model.prepare(request, streaming="stream" in mode)
        losses = [loss for edge in prepared.inspection.request_report.edges for loss in edge.losses]
        assert any(
            loss.path == "tools[0]" and loss.disposition == Disposition.UNSUPPORTED
            for loss in losses
        )
        assert prepared.request.tools and isinstance(prepared.request.tools[0], ServerTool)
        with respx.mock as router:
            with pytest.raises(FidelityPolicyError):
                if mode == "sync":
                    prepared.chat()
                elif mode == "async":
                    await prepared.achat()
                elif mode == "stream":
                    with prepared.stream() as stream:
                        list(stream)
                else:
                    async with await prepared.astream() as stream:
                        async for _ in stream:
                            pass
            assert not router.calls
    finally:
        transport.close()
        await transport.aclose()


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
@pytest.mark.parametrize("asynchronous", [False, True])
async def test_permitted_loss_preserves_wire_function_and_stream_fold(
    load_http: LoadHttp,
    provider: str,
    asynchronous: bool,
) -> None:
    pair = load_http(provider + "_server_tool_unsupported.json")
    streaming = load_http(provider + "_server_tool_unsupported_stream.json")
    transport = HttpxTransport(provider=provider)
    model = ocai.chat.model(
        provider + "/" + pair["request"]["json"]["model"],
        credentials=ApiKey("sk-test"),
        transport=transport,
        catalog=Catalog.of(
            ocai.openai.FRAGMENT if provider == "openai" else ocai.anthropic.FRAGMENT
        ),
    )
    request = ChatRequest(
        messages=(
            [Message.user("Hello!")]
            if provider == "openai"
            else [Message.system("You are concise."), Message.user("Hello, who are you?")]
        ),
        tools=[
            Tool.from_schema({"type": "object"}, name="lookup"),
            ServerTool("web_search"),
            ToolUnknown({"type": "future_tool"}),
        ],
    )
    try:
        with respx.mock as router:
            route = router.post(pair["request"]["url"]).respond(
                pair["response"]["status"], json=pair["response"]["json"]
            )
            result = await model.achat(request) if asynchronous else model.chat(request)
            assert json.loads(route.calls.last.request.content) == pair["request"]["json"]
            assert result.report
            assert [
                (loss.path, loss.disposition)
                for loss in result.report.edges[0].losses
                if loss.path.startswith("tools[")
            ] == [("tools[1]", Disposition.UNSUPPORTED), ("tools[2]", Disposition.UNSUPPORTED)]
            route.respond(
                streaming["response"]["status"],
                headers=streaming["response"]["headers"],
                content=("\n\n".join(streaming["response"]["sse"]) + "\n\n").encode(),
            )
            chunks: list[ChatChunk] = []
            if asynchronous:
                async with await model.astream(request) as astream:
                    chunks.extend([chunk async for chunk in astream])
                end = astream.end
            else:
                with model.stream(request) as stream:
                    chunks.extend(stream)
                end = stream.end
            assert json.loads(route.calls.last.request.content) == streaming["request"]["json"]
            assert end and end.report
            assert [
                (loss.path, loss.disposition)
                for loss in end.report.edges[0].losses
                if loss.path.startswith("tools[")
            ] == [("tools[1]", Disposition.UNSUPPORTED), ("tools[2]", Disposition.UNSUPPORTED)]
            folded = StreamAccumulator.fold(chunks)
            assert folded.message == result.value.message
            assert folded.finish == result.value.finish
            assert folded.usage == result.value.usage
    finally:
        transport.close()
        await transport.aclose()
