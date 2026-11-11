"""Response identity survives folding, malformed metadata and interrupted delivery."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from ocai.chat.types import ChatChunk
from ocai.chat.types import ChunkType
from ocai.chat.types import ResponseInfo
from ocai.chat.types import StreamAccumulator
from ocai.chat.types import StreamEnd
from ocai.convert.conformance import assert_fold_triple
from ocai.core.refs import ProviderRef


def test_partial_repeated_late_metadata_is_detached_and_idempotent() -> None:
    accumulator = StreamAccumulator()
    identity = ProviderRef("openai", "chat_completions", "response_id", "response-synthetic")
    first = ResponseInfo(id=identity)
    accumulator.feed(ChatChunk(type=ChunkType.METADATA, info=first))
    first.model = "caller-mutated"
    later = ResponseInfo(model="actual-model", created=datetime(2026, 1, 1, tzinfo=UTC))
    accumulator.feed(ChatChunk(type=ChunkType.METADATA, info=later))
    accumulator.feed(ChatChunk(type=ChunkType.METADATA, info=deepcopy(later)))
    later.model = "also-mutated"
    end = StreamEnd()
    accumulator.feed(ChatChunk(type=ChunkType.STREAM_STOP, end=end))
    folded = accumulator.finalize()
    assert folded.info == ResponseInfo(id=identity, model="actual-model",
                                       created=datetime(2026, 1, 1, tzinfo=UTC))
    assert not accumulator.report.losses
    assert folded.info is not None
    folded.info.model = "result-mutated"
    assert accumulator.finalize().info == ResponseInfo(
        id=identity, model="actual-model", created=datetime(2026, 1, 1, tzinfo=UTC))


def test_conflict_keeps_first_value_and_reports_distinct_alternative_once() -> None:
    accumulator = StreamAccumulator()
    accumulator.feed(ChatChunk(type=ChunkType.METADATA, info=ResponseInfo(model="first")))
    for _ in range(2):
        accumulator.feed(ChatChunk(type=ChunkType.METADATA, info=ResponseInfo(model="second")))
    end = StreamEnd()
    accumulator.feed(ChatChunk(type=ChunkType.STREAM_STOP, end=end))
    response = accumulator.finalize()
    assert response.info is not None and response.info.model == "first"
    assert response.info.extensions["ocai.response_info_conflicts"] == [
        {"path": "info.model", "value": "second"}]
    assert end.report is not None
    assert [loss.path for loss in end.report.losses] == ["info.model"]
    accumulator.finalize()
    assert len(end.report.edges) == 1


@pytest.mark.parametrize("value", [[], 1, "opaque", {"future": [1, None]}])
def test_malformed_info_never_disappears(value: Any) -> None:
    chunk = ChatChunk.from_dict({"type": "metadata", "info": value})
    accumulator = StreamAccumulator()
    accumulator.feed(chunk)
    response = accumulator.finalize()  # no successful terminal was supplied
    assert response.info is not None
    evidence = response.info.extensions["ocai.response_info_unparsed"]
    assert evidence == (value if isinstance(value, dict) else {"$chunk_info": value})
    assert accumulator.report.losses
    assert response.finish is None and response.usage is None


@pytest.mark.parametrize("data", [
    {"created": "not-a-date"}, {"created": 10**300}, {"model": ["future"]},
    {"id": {"provider": "openai", "interface": [], "kind": "response_id", "id": 1}},
    {"id": {"provider": "openai", "interface": "chat_completions", "kind": "response_id",
            "id": "response-synthetic", "replay": []}},
    {"extensions": "opaque"}, {"provider_options": [1]}, {"version": 3},
])
def test_response_info_reader_preserves_malformed_fields(data: dict[str, Any]) -> None:
    info = ResponseInfo.from_dict(data)
    assert info.extensions["ocai.response_info_unparsed"] == data
    assert ResponseInfo.from_dict(info.to_dict()).to_dict() == info.to_dict()


def test_absence_and_interruption_do_not_invent_identity_or_success() -> None:
    assert StreamAccumulator.fold([]).info is None
    accumulator = StreamAccumulator()
    # The lane can arrive on start or metadata; incomplete execution keeps it.
    accumulator.feed(ChatChunk(type=ChunkType.STREAM_START, info=ResponseInfo(model="known")))
    result = accumulator.finalize()
    assert result.info == ResponseInfo(model="known")
    assert result.finish is None and result.usage is None
    assert not accumulator.report.losses


def test_canonical_metadata_fold_fixture() -> None:
    root = Path(__file__).resolve().parents[4]
    fixture = json.loads((root / "spec/fixtures/canonical/response_info_fold.json").read_text())
    assert_fold_triple(fixture, fold=lambda chunks: StreamAccumulator.fold(
        ChatChunk.from_dict(chunk) for chunk in chunks).to_dict())


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_malformed_stream_metadata_is_reported_by_its_edge(provider: str) -> None:
    from ocai.anthropic.messages.codec import MessagesCodec
    from ocai.anthropic.messages.edges import DECODE_CHUNK_CONTRACT as ANTHROPIC
    from ocai.openai.chat_completions.codec import ChatCompletionsCodec
    from ocai.openai.chat_completions.edges import DECODE_CHUNK_CONTRACT as OPENAI

    if provider == "openai":
        raw: dict[str, Any] = {"id": 7, "model": ["future"], "created": "invalid", "choices": []}
        result = ChatCompletionsCodec().decode_frame(None, json.dumps(raw))
        contract = OPENAI
    else:
        raw = {"type": "message_start", "message": {"id": 7, "model": ["future"]}}
        result = MessagesCodec().decode_frame("message_start", json.dumps(raw))
        contract = ANTHROPIC
    chunks: list[ChatChunk] = result.value
    metadata = next(chunk for chunk in chunks if chunk.type == ChunkType.METADATA)
    assert metadata.info is not None and metadata.info.id is None and metadata.info.model is None
    assert metadata.info.extensions["ocai.response_info_unparsed"]["id"] == 7
    assert [loss.path for loss in result.losses] == ["response_info"]
    assert contract.certify(result.losses, result.shifts) == []
