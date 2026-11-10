"""Reverse fold triples prove client unary/stream semantics and abort behavior."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import ocai.openai
from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatResponse
from ocai.chat.types import ChunkType
from ocai.chat.types import DeltaText
from ocai.chat.types import PartText
from ocai.chat.types import PartToolCall
from ocai.chat.types import StreamAccumulator
from ocai.chat.types import StreamEnd
from ocai.convert.catalog import Catalog
from ocai.core.canonjson import semantic_equal
from ocai.core.errors import StreamProtocolError
from ocai.openai.chat_completions.client import ClientMetadata
from ocai.openai.chat_completions.client import encode_response
from ocai.openai.chat_completions.client_stream import ClientStreamTransducer
from ocai.openai.chat_completions.codec import CANONICAL_CHUNK
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_CHUNK
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.openai.chat_completions.codec import ChatCompletionsStreamTransducer
from ocai.openai.chat_completions.edges import ENCODE_CHUNK_CONTRACT
from ocai.wire import SSEvent

FIXTURES = (Path(__file__).resolve().parents[4]
            / "spec/fixtures/openai/chat_completions/gateway/streams")


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.json")), ids=lambda p: p.name)
def test_reverse_fold_triple_and_catalog(path: Path) -> None:
    fixture: dict[str, Any] = json.loads(path.read_text())
    chunks = [ChatChunk.from_dict(item) for item in fixture["chunks"]]
    source_fold = StreamAccumulator.fold(deepcopy(chunks))
    assert semantic_equal(source_fold.to_dict(), fixture["response"])
    pipeline = Catalog.of(ocai.openai.FRAGMENT).stream_converter(
        CANONICAL_CHUNK, CHAT_COMPLETIONS_CHUNK)
    events: list[Any] = []
    for chunk in chunks:
        events.extend(pipeline.feed(chunk))
    tail, reports = pipeline.flush()
    events.extend(tail)
    assert events == fixture["events"]
    assert len(reports) == 1
    report = reports[0]
    assert ENCODE_CHUNK_CONTRACT.certify(report.losses, report.shifts) == []
    assert [(loss.path, loss.disposition.value) for loss in report.losses] == [
        (loss["path"], loss["disposition"]) for loss in fixture["expect_losses"]]
    assert [(shift.kind, shift.path) for shift in report.shifts] == [
        (shift["kind"], shift["path"]) for shift in fixture["expect_shifts"]]
    assert encode_response(ChatResponse.from_dict(fixture["response"])).value == (
        fixture["client_response"])
    metadata = ClientMetadata("chatcmpl-client", "deployment", 1767225600)
    decoder = ChatCompletionsStreamTransducer()
    decoded: list[ChatChunk] = []
    for event in events:
        decoded.extend(decoder.feed(SSEvent(data=json.dumps(metadata.bind(event)))))
    decoded.extend(decoder.feed(SSEvent(data="[DONE]")))
    folded = StreamAccumulator.fold(decoded)
    unary = ChatCompletionsCodec().decode_response(metadata.bind(fixture["client_response"])).value
    assert semantic_equal(folded.message.to_dict(), unary.message.to_dict())
    assert folded.finish == unary.finish
    assert folded.usage == unary.usage


def test_parallel_tool_identity_and_order() -> None:
    encoder = ClientStreamTransducer()
    output: list[dict[str, Any]] = []
    for index, name in enumerate(["alpha", "beta"]):
        output += encoder.feed(ChatChunk(type=ChunkType.PART_START, index=index,
            part=PartToolCall(call_id=f"call_{name}", name=name, args_json="{}")))
    assert [event["choices"][0]["delta"]["tool_calls"][0]["index"] for event in output] == [0, 1]
    assert [event["choices"][0]["delta"]["tool_calls"][0]["id"] for event in output] == [
        "call_alpha", "call_beta"]
    # No finish is advertised without a canonical successful terminal.
    tail, report = encoder.flush()
    assert tail == []
    assert any(loss.path == "termination" for loss in report.losses)
    assert ENCODE_CHUNK_CONTRACT.certify(report.losses, report.shifts) == []


@pytest.mark.parametrize("failure", ["error", "mismatch", "unknown_delta"])
def test_no_success_after_failure(failure: str) -> None:
    encoder = ClientStreamTransducer()
    encoder.feed(ChatChunk(type=ChunkType.PART_START, index=0, part=PartText()))
    encoder.feed(ChatChunk(type=ChunkType.PART_DELTA, index=0, delta=DeltaText(text="hi")))
    if failure == "unknown_delta":
        encoder.feed(ChatChunk.from_dict({"type": "partDelta", "index": 0,
                                         "delta": {"type": "future", "data": True}}))
    else:
        with pytest.raises(StreamProtocolError):
            encoder.feed(ChatChunk(type=ChunkType.ERROR) if failure == "error" else
                         ChatChunk(type=ChunkType.PART_STOP, index=0,
                                   part=PartText(text="changed")))
        with pytest.raises(StreamProtocolError):
            encoder.feed(ChatChunk(type=ChunkType.STREAM_STOP, end=StreamEnd()))
    tail, report = encoder.flush()
    assert tail == []
    assert report.losses
    assert ENCODE_CHUNK_CONTRACT.certify(report.losses, report.shifts) == []
