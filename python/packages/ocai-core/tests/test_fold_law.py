"""The fold law, hardened (WU-08): `complete(request) == fold(stream(request))`.

Exercises the four accumulator corners this WU closed — aborted-stream
sealing (`extensions["ocai.incomplete"]`), the mismatched-delta /
`DeltaUnknown` reporting channel (an `EdgeReport` on `StreamEnd.report`),
`DeltaSignature` buffering (`extensions["ocai.signature_buffer"]`), and
`FidelityReport.from_dict` for recorded-`StreamEnd` replay — plus the
conformance harness's `assert_fold_triple` / `check_fold_triples`, including
the PART_STOP-final-part-MUST-equal-accumulation clause, all under
`canonjson.semantic_equal`.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from ocai.chat.canonical import CANONICAL_CHAT_CHUNK
from ocai.chat.canonical import CANONICAL_CHAT_RESPONSE
from ocai.chat.types import INCOMPLETE_EXTENSION
from ocai.chat.types import SIGNATURE_BUFFER_EXTENSION
from ocai.chat.types import ChatChunk
from ocai.chat.types import ChunkType
from ocai.chat.types import Consumption
from ocai.chat.types import DeltaSignature
from ocai.chat.types import DeltaText
from ocai.chat.types import DeltaToolArgs
from ocai.chat.types import FinishInfo
from ocai.chat.types import PartReasoning
from ocai.chat.types import PartText
from ocai.chat.types import StreamAccumulator
from ocai.chat.types import StreamEnd
from ocai.chat.types import Usage
from ocai.convert.conformance import assert_fold_triple
from ocai.convert.conformance import check_fold_triples
from ocai.convert.conformance import load_fixture
from ocai.core import CHAT_CHUNK
from ocai.core import Disposition
from ocai.core import EdgeReport
from ocai.core import FidelityReport
from ocai.core import FieldLoss
from ocai.core import NodeId
from ocai.core import SemanticShift
from ocai.core import semantic_equal
from ocai.core.refs import ProviderRef

# --- Helpers -----------------------------------------------------------------


def _usage(output_tokens: int) -> Usage:
    """Build a two-bucket usage record with `output_tokens` output tokens."""
    return Usage(
        consumptions=[
            Consumption(modality="text", unit="tokens", source="input", value=12),
            Consumption(modality="text", unit="tokens", source="output", value=output_tokens),
        ]
    )


def _fold_dicts(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """The dict-speaking fold the conformance harness is handed."""
    return StreamAccumulator.fold(ChatChunk.from_dict(chunk) for chunk in chunks).to_dict()


def _text_stream() -> list[ChatChunk]:
    """A complete minimal text stream: start, one part, finish, streamStop."""
    return [
        ChatChunk(type=ChunkType.STREAM_START),
        ChatChunk(type=ChunkType.PART_START, index=0, part=PartText(text="")),
        ChatChunk(type=ChunkType.PART_DELTA, index=0, delta=DeltaText(text="Hello")),
        ChatChunk(type=ChunkType.PART_DELTA, index=0, delta=DeltaText(text=" world")),
        ChatChunk(type=ChunkType.PART_STOP, index=0, part=PartText(text="Hello world")),
        ChatChunk(
            type=ChunkType.STREAM_STOP,
            end=StreamEnd(usage=_usage(2), finish=FinishInfo(reason="complete", native="stop")),
        ),
    ]


# --- The fold law ------------------------------------------------------------


def test_fold_reproduces_the_blocking_shape() -> None:
    response = StreamAccumulator.fold(_text_stream())

    assert [part.text for part in response.message.parts] == ["Hello world"]  # type: ignore[union-attr]
    assert response.finish is not None and response.finish.reason == "complete"
    assert response.usage is not None and response.usage.output_tokens == 2


def test_implicit_part_start_tolerance() -> None:
    # A stream that never sends PART_START still folds: the accumulator
    # opens an implicit text slot for the first delta.
    chunks = [
        ChatChunk(type=ChunkType.PART_DELTA, delta=DeltaText(text="Hello")),
        ChatChunk(type=ChunkType.PART_DELTA, delta=DeltaText(text=" world")),
        ChatChunk(type=ChunkType.STREAM_STOP, end=StreamEnd()),
    ]
    response = StreamAccumulator.fold(chunks)

    (part,) = response.message.parts
    assert isinstance(part, PartText)
    assert part.text == "Hello world"
    assert INCOMPLETE_EXTENSION not in part.extensions  # streamStop arrived


def test_part_stop_authoritative_part_wins() -> None:
    # The codec's final part on PART_STOP replaces the accumulation; whether
    # the two were equal is the conformance harness's business, not the fold's.
    chunks = [
        ChatChunk(type=ChunkType.PART_START, index=0, part=PartText(text="")),
        ChatChunk(type=ChunkType.PART_DELTA, index=0, delta=DeltaText(text="hi")),
        ChatChunk(type=ChunkType.PART_STOP, index=0, part=PartText(text="HI")),
        ChatChunk(type=ChunkType.STREAM_STOP, end=StreamEnd()),
    ]
    response = StreamAccumulator.fold(chunks)

    (part,) = response.message.parts
    assert isinstance(part, PartText)
    assert part.text == "HI"


def test_stream_end_overrides_midstream_usage_and_finish() -> None:
    midstream_finish = FinishInfo(reason="max_tokens", native="length")
    final_finish = FinishInfo(reason="complete", native="stop")
    chunks = [
        ChatChunk(type=ChunkType.USAGE, usage=_usage(3), usage_cumulative=True),
        ChatChunk(type=ChunkType.FINISH, finish=midstream_finish),
        ChatChunk(
            type=ChunkType.STREAM_STOP,
            end=StreamEnd(usage=_usage(7), finish=final_finish),
        ),
    ]
    response = StreamAccumulator.fold(chunks)

    assert response.usage is not None and response.usage.output_tokens == 7
    assert response.finish is final_finish

    # ... and mid-stream records survive when the terminal StreamEnd is bare.
    bare = StreamAccumulator.fold(
        [
            ChatChunk(type=ChunkType.USAGE, usage=_usage(3)),
            ChatChunk(type=ChunkType.FINISH, finish=midstream_finish),
            ChatChunk(type=ChunkType.STREAM_STOP, end=StreamEnd()),
        ]
    )
    assert bare.usage is not None and bare.usage.output_tokens == 3
    assert bare.finish is midstream_finish


# --- Aborted-stream sealing ----------------------------------------------------


def test_aborted_stream_seals_open_parts_incomplete() -> None:
    # No STREAM_STOP ever arrives: the sealed part stays clean, the open
    # part is explicitly marked — never passed off as complete.
    chunks = [
        ChatChunk(type=ChunkType.PART_START, index=0, part=PartText(text="")),
        ChatChunk(type=ChunkType.PART_DELTA, index=0, delta=DeltaText(text="done")),
        ChatChunk(type=ChunkType.PART_STOP, index=0),
        ChatChunk(type=ChunkType.PART_START, index=1, part=PartText(text="")),
        ChatChunk(type=ChunkType.PART_DELTA, index=1, delta=DeltaText(text="cut off")),
    ]
    response = StreamAccumulator.fold(chunks)

    sealed, aborted = response.message.parts
    assert INCOMPLETE_EXTENSION not in sealed.extensions
    assert aborted.extensions[INCOMPLETE_EXTENSION] is True
    assert isinstance(aborted, PartText) and aborted.text == "cut off"


def test_completed_stream_has_no_incomplete_marker() -> None:
    response = StreamAccumulator.fold(_text_stream())

    (part,) = response.message.parts
    assert INCOMPLETE_EXTENSION not in part.extensions


# --- The reporting channel -----------------------------------------------------


def test_mismatched_delta_is_reported_dropped() -> None:
    accumulator = StreamAccumulator()
    accumulator.feed(ChatChunk(type=ChunkType.PART_START, index=0, part=PartText(text="")))
    accumulator.feed(
        ChatChunk(type=ChunkType.PART_DELTA, index=0, delta=DeltaToolArgs(fragment='{"x":1}'))
    )
    end = StreamEnd()
    accumulator.feed(ChatChunk(type=ChunkType.STREAM_STOP, end=end))
    accumulator.finalize()

    assert end.report is not None
    (loss,) = end.report.losses
    assert loss.disposition is Disposition.DROPPED
    assert loss.path == "message.parts[0]"
    assert not end.report.lossless
    (edge,) = end.report.edges
    assert edge.src == CANONICAL_CHAT_CHUNK
    assert edge.dst == CANONICAL_CHAT_RESPONSE

    # finalize is idempotent on the channel: no duplicate edge on re-run.
    accumulator.finalize()
    assert len(end.report.edges) == 1


def test_unknown_delta_is_reported_dropped_and_never_raises() -> None:
    chunk = ChatChunk.from_dict(
        {
            "type": "partDelta",
            "index": 0,
            "delta": {"type": "quantum_hint", "payload": [1, 2, 3]},
        }
    )
    accumulator = StreamAccumulator()
    accumulator.feed(ChatChunk(type=ChunkType.PART_START, index=0, part=PartText(text="")))
    accumulator.feed(chunk)  # total: never a raise
    response = accumulator.finalize()

    (part,) = response.message.parts
    assert isinstance(part, PartText) and part.text == ""
    (loss,) = accumulator.report.losses
    assert loss.disposition is Disposition.DROPPED
    assert "quantum_hint" in loss.note
    # The stream aborted (no STREAM_STOP): the losses stay reachable here.
    assert not accumulator.report.lossless


# --- DeltaSignature buffering ---------------------------------------------------


def test_signature_fragments_preserved_under_extensions() -> None:
    chunks = [
        ChatChunk(type=ChunkType.PART_START, index=0, part=PartReasoning()),
        ChatChunk(type=ChunkType.PART_DELTA, index=0, delta=DeltaSignature(signature="abc")),
        ChatChunk(type=ChunkType.PART_DELTA, index=0, delta=DeltaSignature(signature="def")),
        ChatChunk(type=ChunkType.PART_STOP, index=0),
    ]
    accumulator = StreamAccumulator()
    for chunk in chunks:
        accumulator.feed(chunk)
    end = StreamEnd()
    accumulator.feed(ChatChunk(type=ChunkType.STREAM_STOP, end=end))
    response = accumulator.finalize()

    (part,) = response.message.parts
    assert part.extensions[SIGNATURE_BUFFER_EXTENSION] == "abcdef"
    assert end.report is not None
    (loss,) = end.report.losses
    assert loss.disposition is Disposition.EXTENSIONS
    assert end.report.lossless  # EXTENSIONS preserves — recoverable, reported


def test_codec_minted_signature_subsumes_the_buffer() -> None:
    minted = ProviderRef(
        provider="anthropic", interface="messages", kind="thought_signature", id="sig-1"
    )
    chunks = [
        ChatChunk(type=ChunkType.PART_START, index=0, part=PartReasoning()),
        ChatChunk(type=ChunkType.PART_DELTA, index=0, delta=DeltaSignature(signature="abc")),
        ChatChunk(type=ChunkType.PART_STOP, index=0, part=PartReasoning(signature=minted)),
        ChatChunk(type=ChunkType.STREAM_STOP, end=StreamEnd()),
    ]
    accumulator = StreamAccumulator()
    for chunk in chunks:
        accumulator.feed(chunk)
    response = accumulator.finalize()

    (part,) = response.message.parts
    assert isinstance(part, PartReasoning)
    assert part.signature is minted
    assert SIGNATURE_BUFFER_EXTENSION not in part.extensions
    assert accumulator.report.lossless and not accumulator.report.losses


def test_aborted_reasoning_part_keeps_buffer_and_incomplete_marker() -> None:
    chunks = [
        ChatChunk(type=ChunkType.PART_START, index=0, part=PartReasoning()),
        ChatChunk(type=ChunkType.PART_DELTA, index=0, delta=DeltaSignature(signature="abc")),
    ]
    response = StreamAccumulator.fold(chunks)

    (part,) = response.message.parts
    assert part.extensions[INCOMPLETE_EXTENSION] is True
    assert part.extensions[SIGNATURE_BUFFER_EXTENSION] == "abc"


# --- FidelityReport replay (from_dict) -------------------------------------------


def _sample_report() -> FidelityReport:
    wire = NodeId(
        provider="openai",
        interface="chat_completions",
        tag="2026-01",
        shape=CHAT_CHUNK,
        released=date(2026, 1, 1),
    )
    return FidelityReport(
        edges=[
            EdgeReport(
                src=wire,
                dst=CANONICAL_CHAT_CHUNK,
                losses=(
                    FieldLoss(
                        path="choices[1]",
                        disposition=Disposition.DROPPED,
                        severity=1.0,
                        note="single message forever",
                    ),
                ),
                shifts=(SemanticShift(kind="relocation", path="system", note="hoisted"),),
                note="decode leg",
            )
        ]
    )


def test_fidelity_report_from_dict_round_trip() -> None:
    report = _sample_report()
    data = report.to_dict()
    replayed = FidelityReport.from_dict(data)

    assert semantic_equal(replayed.to_dict(), data)
    assert replayed.path == report.path  # NodeId labels decode back whole
    assert replayed.losses == report.losses
    assert replayed.shifts == report.shifts


def test_replayed_report_recomputes_derived_views() -> None:
    data = _sample_report().to_dict()
    data["lossless"] = True  # a replayed report cannot assert fidelity...
    data["total_cost"] = 0.0
    data["edges"][0]["cost"] = 0.0  # ...its records contradict
    replayed = FidelityReport.from_dict(data)

    assert not replayed.lossless
    assert replayed.total_cost == 1.0


def test_unknown_disposition_decodes_conservatively() -> None:
    loss = FieldLoss.from_dict({"path": "x", "disposition": "teleported"})

    assert loss.disposition is Disposition.DROPPED  # overstate, never understate
    assert loss.lossy


def test_recorded_stream_stop_replays_with_report() -> None:
    report = _sample_report()
    recorded = ChatChunk(
        type=ChunkType.STREAM_STOP,
        end=StreamEnd(usage=_usage(7), finish=FinishInfo(reason="complete"), report=report),
    ).to_dict()
    replayed = ChatChunk.from_dict(recorded)

    assert replayed.end is not None and replayed.end.report is not None
    assert semantic_equal(replayed.end.report.to_dict(), report.to_dict())
    assert semantic_equal(replayed.to_dict(), recorded)


# --- The conformance harness: fold triples -----------------------------------------


def test_assert_fold_triple_passes_on_the_spec_fixture(spec_dir: Path) -> None:
    fixture = load_fixture(spec_dir / "fixtures" / "canonical" / "chat_stream_fold.json")

    assert_fold_triple(fixture, fold=_fold_dicts)  # decode leg absent by design


def test_assert_fold_triple_enforces_part_stop_accumulation_clause() -> None:
    # The final part on partStop ("HI") does not equal the accumulation
    # ("hi"): the intact fold matches the response, but the strip-and-refold
    # clause catches the divergence.
    chunks = [
        ChatChunk(type=ChunkType.PART_START, index=0, part=PartText(text="")).to_dict(),
        ChatChunk(type=ChunkType.PART_DELTA, index=0, delta=DeltaText(text="hi")).to_dict(),
        ChatChunk(type=ChunkType.PART_STOP, index=0, part=PartText(text="HI")).to_dict(),
        ChatChunk(type=ChunkType.STREAM_STOP, end=StreamEnd()).to_dict(),
    ]
    fixture = {"chunks": chunks, "response": _fold_dicts(chunks)}

    with pytest.raises(AssertionError, match="accumulation"):
        assert_fold_triple(fixture, fold=_fold_dicts)


def test_assert_fold_triple_decode_leg() -> None:
    chunks = [chunk.to_dict() for chunk in _text_stream()]
    fixture = {
        "chunks": chunks,
        "response": _fold_dicts(chunks),
        "wire_events": [json.dumps(chunk) for chunk in chunks],  # identity wire
    }

    assert_fold_triple(
        fixture,
        decode_event=lambda event: [json.loads(event)],
        fold=_fold_dicts,
    )
    # wire_events present but no decoder supplied: the leg cannot be skipped
    # silently.
    with pytest.raises(AssertionError, match="decode_event"):
        assert_fold_triple(fixture, fold=_fold_dicts)
    # A decoder that drops an event is caught by the count check.
    with pytest.raises(AssertionError, match="number of chunks"):
        assert_fold_triple(
            fixture,
            decode_event=lambda event: [],
            fold=_fold_dicts,
        )


def test_check_fold_triples_walks_and_refuses_empty(spec_dir: Path, tmp_path: Path) -> None:
    source = spec_dir / "fixtures" / "canonical" / "chat_stream_fold.json"
    target = tmp_path / "triple.json"
    target.write_text(source.read_text())

    assert check_fold_triples(tmp_path, fold=_fold_dicts) == [target]

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(AssertionError, match="no fold triples"):
        check_fold_triples(empty, fold=_fold_dicts)
