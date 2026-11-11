"""WU-43: qualified search replay and accounting through recorded public execution."""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import respx

import ocai.anthropic
import ocai.chat
from ocai.anthropic.messages.codec import MessagesCodec
from ocai.anthropic.messages.codec import MessagesStreamTransducer
from ocai.anthropic.messages.edges import DECODE_CHUNK_CONTRACT
from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChunkType
from ocai.chat.types import Message
from ocai.chat.types import PartServerToolResult
from ocai.chat.types import PartText
from ocai.chat.types import ServerTool
from ocai.chat.types import StreamAccumulator
from ocai.convert import Catalog
from ocai.core import ApiKey
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import FidelityPolicy
from ocai.core.fidelity import FidelityPolicyError
from ocai.core.usage import UsageUnit
from ocai.wire.sse import SSEParser
from ocai.wire.transport import HttpxTransport

type LoadHttp = Callable[[str], dict[str, Any]]


def _request(spec_dir: Path) -> ChatRequest:
    path = spec_dir / "fixtures/anthropic/messages/request_web_search.json"
    return ChatRequest.from_dict(json.loads(path.read_text())["input"])


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_search_fold_and_exact_two_turn_replay(
    spec_dir: Path,
    load_http: LoadHttp,
    asynchronous: bool,
) -> None:
    pair = load_http("anthropic_web_search_stream_paired.json")
    streaming = load_http("anthropic_web_search_stream.json")
    replay = load_http("anthropic_web_search_replay.json")
    transport = HttpxTransport(provider="anthropic")
    model = ocai.chat.model(
        "anthropic/claude-opus-4-6",
        credentials=ApiKey("sk-test"),
        transport=transport,
        catalog=Catalog.of(ocai.anthropic.FRAGMENT),
        conversion_policy=FidelityPolicy(
            forbidden_dispositions=frozenset({Disposition.UNSUPPORTED})
        ),
    )
    request = _request(spec_dir)
    before = deepcopy(request.to_dict())
    try:
        with respx.mock as router:
            route = router.post(pair["request"]["url"]).respond(200, json=pair["response"]["json"])
            result = await model.achat(request) if asynchronous else model.chat(request)
            assert json.loads(route.calls.last.request.content) == pair["request"]["json"]
            assert result.usage and result.usage.total_tokens == 27
            assert [(c.unit, c.value) for c in result.usage.consumptions][-1] == (
                UsageUnit.SEARCH_REQUESTS,
                3,
            )
            parts = result.value.message.parts
            assert isinstance(parts[1], PartServerToolResult)
            assert len(parts[1].payload["content"]) == 2
            assert isinstance(parts[2], PartText)
            assert parts[2].annotations[0].span is None
            assert parts[2].annotations[0].opaque
            route.respond(
                200,
                headers=streaming["response"]["headers"],
                content=("\n\n".join(streaming["response"]["sse"]) + "\n\n").encode(),
            )
            chunks: list[ChatChunk] = []
            if asynchronous:
                async with await model.astream(request) as astream:
                    chunks = [chunk async for chunk in astream]
                end = astream.end
            else:
                with model.stream(request) as stream:
                    chunks = list(stream)
                end = stream.end
            assert json.loads(route.calls.last.request.content) == streaming["request"]["json"]
            assert end and end.report and end.usage == result.usage
            assert any(
                shift.kind == "anthropic.search_input_buffered" for shift in end.report.shifts
            )
            folded = StreamAccumulator.fold(chunks)
            assert folded.message == result.value.message
            assert folded.finish == result.value.finish
            assert folded.usage == result.value.usage
            followup = deepcopy(request)
            followup.messages.extend([folded.message, Message.user("Continue.")])
            route.respond(200, json=replay["response"]["json"])
            if asynchronous:
                await model.achat(followup)
            else:
                model.chat(followup)
            assert json.loads(route.calls.last.request.content) == replay["request"]["json"]
            assert request.to_dict() == before
    finally:
        transport.close()
        await transport.aclose()


@pytest.mark.parametrize("mode", ["sync", "async", "stream", "astream"])
@pytest.mark.parametrize("damage", ["foreign", "missing", "ciphertext", "version"])
async def test_unqualified_search_replay_is_denied_before_io(
    spec_dir: Path,
    load_http: LoadHttp,
    mode: str,
    damage: str,
) -> None:
    request = _request(spec_dir)
    response = (
        MessagesCodec()
        .decode_response(load_http("anthropic_web_search_stream_paired.json")["response"]["json"])
        .value
    )
    part = response.message.parts[1]
    assert isinstance(part, PartServerToolResult) and part.anchor
    if damage == "foreign":
        part.anchor = replace(part.anchor, interface="other")
    elif damage == "missing":
        part.anchor = None
    elif damage == "ciphertext":
        del part.payload["content"][0]["encrypted_content"]
    else:
        assert request.tools and isinstance(request.tools[0], ServerTool)
        request.tools[0].provider_options["anthropic.messages"]["type"] = "web_search_20260318"
    request.messages.append(response.message)
    transport = HttpxTransport(provider="anthropic")
    model = ocai.chat.model(
        "anthropic/claude-opus-4-6",
        credentials=ApiKey("sk-test"),
        transport=transport,
        catalog=Catalog.of(ocai.anthropic.FRAGMENT),
        conversion_policy=FidelityPolicy(
            forbidden_dispositions=frozenset({Disposition.UNSUPPORTED})
        ),
    )
    try:
        with respx.mock as router, pytest.raises(FidelityPolicyError):
            try:
                if mode == "sync":
                    model.chat(request)
                elif mode == "async":
                    await model.achat(request)
                elif mode == "stream":
                    with model.stream(request) as stream:
                        list(stream)
                else:
                    async with await model.astream(request) as astream:
                        async for _ in astream:
                            pass
            finally:
                assert not router.calls
    finally:
        transport.close()
        await transport.aclose()


def test_native_request_audit_preserves_search_intent_and_replay(load_http: LoadHttp) -> None:
    pair = load_http("anthropic_web_search_replay.json")
    codec = MessagesCodec()
    decoded = codec.decode_request(pair["request"]["json"])
    encoded = codec.encode_request(decoded.value)
    assert codec.bind_resource(encoded.value, "claude-opus-4-6") == pair["request"]["json"]
    assert [(loss.path, loss.disposition) for loss in encoded.losses] == [
        ("extensions[anthropic.model]", Disposition.DROPPED)
    ]


@pytest.mark.parametrize(
    "raw", [0, [], "future", {"web_search_requests": "unknown"}, {"future_requests": 7}]
)
def test_unknown_search_usage_remains_evidence(load_http: LoadHttp, raw: Any) -> None:
    wire = load_http("anthropic_web_search_stream_paired.json")["response"]["json"]
    wire["usage"]["server_tool_use"] = raw
    decoded = MessagesCodec().decode_response(wire)
    assert decoded.value.usage.extensions["anthropic.server_tool_usage"] == raw
    assert not any(c.unit == UsageUnit.SEARCH_REQUESTS for c in decoded.value.usage.consumptions)
    assert any(loss.path == "usage.server_tool_use" for loss in decoded.losses)


def test_unknown_citations_and_location_metadata_never_raise(load_http: LoadHttp) -> None:
    codec = MessagesCodec()
    wire = load_http("anthropic_web_search_stream_paired.json")["response"]["json"]
    unknown = {"type": "future_citation", "payload": [1, "opaque"]}
    wire["content"][-1]["citations"] = [unknown]
    decoded = codec.decode_response(wire)
    assert (
        decoded.value.message.parts[-1].annotations[0].extensions["anthropic.web_search_citation"]
        == unknown
    )
    request = load_http("anthropic_web_search_replay.json")["request"]["json"]
    request["tools"][0]["user_location"]["extensions"] = "future"
    tool = codec.decode_request(request).value.tools[0]
    assert tool.extensions["anthropic.web_search_unmapped"]["user_location"] == {
        "extensions": "future"
    }


@pytest.mark.parametrize("terminal", [False, True])
def test_interrupted_search_input_retains_fragments_without_success(
    load_http: LoadHttp,
    terminal: bool,
) -> None:
    events = load_http("anthropic_web_search_stream.json")["response"]["sse"][:3]
    if terminal:
        events.append('event: message_stop\ndata: {"type":"message_stop"}')
    transducer = MessagesStreamTransducer()
    chunks: list[ChatChunk] = []
    for text in events:
        for event in SSEParser().feed(text + "\n\n"):
            chunks.extend(transducer.feed(event))
    tail, report = transducer.flush()
    chunks.extend(tail)
    assert not any(chunk.type == ChunkType.STREAM_STOP for chunk in chunks)
    partial = next(chunk.part for chunk in chunks if chunk.type == ChunkType.PART_START)
    assert partial and partial.anchor is None
    assert partial.extensions["anthropic.incomplete_search_input"]["partial_json"] == [
        '{"query": "ocai '
    ]
    assert DECODE_CHUNK_CONTRACT.certify(report.losses, report.shifts) == []
    assert transducer.flush()[0] == []


async def test_in_band_search_error_is_not_a_successful_result(
    spec_dir: Path,
    load_http: LoadHttp,
) -> None:
    pair = load_http("anthropic_web_search_error.json")
    transport = HttpxTransport(provider="anthropic")
    model = ocai.chat.model(
        "anthropic/claude-opus-4-6",
        credentials=ApiKey("sk-test"),
        transport=transport,
        catalog=Catalog.of(ocai.anthropic.FRAGMENT),
    )
    try:
        with respx.mock as router:
            route = router.post(pair["request"]["url"]).respond(200, json=pair["response"]["json"])
            result = await model.achat(_request(spec_dir))
            assert json.loads(route.calls.last.request.content) == pair["request"]["json"]
            part = result.value.message.parts[1]
            assert isinstance(part, PartServerToolResult) and part.status == "output_error"
            assert part.payload["content"]["error_code"] == "max_uses_exceeded"
            assert result.usage and result.usage.consumptions[-1].value == 0
    finally:
        transport.close()
        await transport.aclose()


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_interrupted_search_retains_accounting_and_fidelity(
    spec_dir: Path,
    load_http: LoadHttp,
    asynchronous: bool,
) -> None:
    pair = load_http("anthropic_web_search_interrupted.json")
    transport = HttpxTransport(provider="anthropic")
    model = ocai.chat.model(
        "anthropic/claude-opus-4-6",
        credentials=ApiKey("sk-test"),
        transport=transport,
        catalog=Catalog.of(ocai.anthropic.FRAGMENT),
    )
    try:
        with respx.mock as router:
            route = router.post(pair["request"]["url"]).respond(
                200,
                headers=pair["response"]["headers"],
                content=("\n\n".join(pair["response"]["sse"]) + "\n\n").encode(),
            )
            if asynchronous:
                async with await model.astream(_request(spec_dir)) as astream:
                    chunks = [chunk async for chunk in astream]
                outcome, end = astream.outcome, astream.end
            else:
                with model.stream(_request(spec_dir)) as stream:
                    chunks = list(stream)
                outcome, end = stream.outcome, stream.end
            assert route.call_count == 1
            assert end is None and outcome and outcome.status == "failed"
            assert outcome.usage and outcome.usage.total_tokens == 11
            assert outcome.report
            assert any(
                loss.path == "content_block_delta.input_json_delta"
                for loss in outcome.report.losses
            )
            assert any(chunk.type == ChunkType.ERROR for chunk in chunks)
    finally:
        transport.close()
        await transport.aclose()
