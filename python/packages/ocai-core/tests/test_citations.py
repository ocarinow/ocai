"""WU-40: citations retain evidence without inventing positional attribution."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import respx

import ocai.chat
import ocai.openai
from ocai.chat.types import Annotation
from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import ChunkType
from ocai.chat.types import Message
from ocai.chat.types import PartText
from ocai.chat.types import SourceResultRef
from ocai.chat.types import Span
from ocai.chat.types import StreamAccumulator
from ocai.convert import Catalog
from ocai.convert.conformance import assert_fold_triple
from ocai.convert.conformance import load_fixture
from ocai.core import ApiKey
from ocai.core.fidelity import Disposition
from ocai.core.ir import is_json_object
from ocai.wire.transport import HttpxTransport

LoadHttp = Callable[[str], dict[str, Any]]


@pytest.mark.parametrize("name", ["unicode_citations", "invalid_bounds"])
def test_canonical_citation_fold_and_final_part_agree(spec_dir: Path, name: str) -> None:
    fixture = load_fixture(spec_dir / "fixtures" / "canonical" / "citations" / f"{name}.json")

    def fold(chunks: list[dict[str, Any]]) -> dict[str, Any]:
        return StreamAccumulator.fold(ChatChunk.from_dict(chunk) for chunk in chunks).to_dict()

    assert_fold_triple(fixture, fold=fold)
    assert ChatResponse.from_dict(fixture["response"]).to_dict() == fixture["response"]
    # Decode a unary response containing the same final, unvalidated annotations.
    final = next(chunk["part"] for chunk in fixture["chunks"] if chunk["type"] == "partStop")
    unary = ChatResponse.from_dict({"message": {"role": "model", "parts": [final]}})
    assert unary.to_dict() == fixture["response"]
    accumulator = StreamAccumulator()
    for raw in fixture["chunks"]:
        chunk = ChatChunk.from_dict(raw)
        accumulator.feed(chunk)
        if chunk.type == ChunkType.PART_STOP:
            assert chunk.part and chunk.part.to_dict() == fixture["response"]["message"]["parts"][0]


@pytest.mark.parametrize(
    "raw",
    [
        {"start": "1", "end": 2},
        {"start": True, "end": 2},
        {"start": 1.5, "end": 2},
        {"start": None, "end": 2},
        {"end": 2},
        {"start": [], "end": {}},
        [],
        "bad",
        3,
    ],
)
def test_malformed_spans_are_total_and_unpositioned(raw: Any) -> None:
    annotation = Annotation.from_dict(
        {"kind": "url_citation", "span": raw, "url": "https://example.test"}
    )
    assert annotation.span is None
    assert annotation.extensions["ocai.annotation_invalid_span"] == [
        {"span": raw, "reason": "malformed span"}
    ]
    assert annotation.validated("abc").to_dict() == annotation.to_dict()
    assert Annotation.from_dict(annotation.to_dict()).to_dict() == annotation.to_dict()
    if is_json_object(raw):
        span = Span.from_dict(raw)
        assert not span.valid_for("abc")
        assert span.extensions["ocai.invalid_span"] == raw


@pytest.mark.parametrize("start,end", [(-1, 1), (3, 1), (0, 6)])
def test_invalid_bounds_keep_verbatim_span_evidence(start: int, end: int) -> None:
    annotation = Annotation(span=Span(start, end), kind="url_citation")
    checked = annotation.validated("A😀e\u0301Z")
    assert checked.span is None
    assert checked.extensions["ocai.annotation_invalid_span"][0]["span"] == {
        "start": start,
        "end": end,
    }
    assert annotation.span == Span(start, end)  # caller data is not rewritten


def test_unicode_validation_never_guesses_offset_units_or_normalizes_text() -> None:
    text = "A😀e\u0301Z"
    assert Span(1, 2).valid_for(text, attributed_text="😀")
    assert Span(2, 4).valid_for(text, attributed_text="e\u0301")
    assert not Span(2, 4).valid_for("A😀éZ", attributed_text="e\u0301")
    assert not Span(1, 3).valid_for(text, attributed_text="😀")  # UTF-16 offsets
    assert not Span(1, 5).valid_for(text, attributed_text="😀")  # UTF-8 offsets
    source_quote = Annotation(span=Span(1, 2), cited_text="different source wording")
    assert source_quote.validated(text).span == Span(1, 2)
    assert source_quote.validated(text, attributed_text="wrong").span is None
    assert Annotation(url="https://example.test").validated(text).span is None


def test_legacy_unknown_kinds_and_local_references_remain_open() -> None:
    legacy = Annotation(span=Span(0, 1), url="https://example.test")
    assert "kind" not in legacy.to_dict() and "source_result" not in legacy.to_dict()
    annotation = Annotation.from_dict(
        {
            "kind": "future_kind",
            "span": {"start": 0, "end": 1, "future_span": 9},
            "source_result": {"call_id": "search-test", "pointer": "/results/0", "future_ref": 8},
            "future_annotation": 7,
        }
    )
    assert annotation.kind == "future_kind"
    assert annotation.span and annotation.span.extensions["future_span"] == 9
    assert annotation.source_result and annotation.source_result.extensions["future_ref"] == 8
    assert annotation.extensions["future_annotation"] == 7
    assert Annotation.from_dict(annotation.to_dict()).to_dict() == annotation.to_dict()
    assert SourceResultRef("search-test", "").pointer == ""
    malformed = Annotation.from_dict({"source_result": ["future"]})
    assert malformed.source_result is None
    assert malformed.extensions["ocai.annotation_unparsed_source"] == ["future"]


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_unqualified_provider_citations_remain_reported_wire_evidence(
    load_http: LoadHttp,
    asynchronous: bool,
) -> None:
    pair = load_http("openai_chat_citation_unqualified.json")
    transport = HttpxTransport(provider="openai")
    model = ocai.chat.model(
        "openai/" + pair["request"]["json"]["model"],
        credentials=ApiKey("sk-test"),
        transport=transport,
        catalog=Catalog.of(ocai.openai.FRAGMENT),
    )
    request = ChatRequest(
        messages=[
            Message.system(pair["request"]["json"]["messages"][0]["content"]),
            Message.user(pair["request"]["json"]["messages"][1]["content"]),
        ]
    )
    try:
        with respx.mock as router:
            route = router.post(pair["request"]["url"]).respond(
                pair["response"]["status"], json=pair["response"]["json"]
            )
            result = await model.achat(request) if asynchronous else model.chat(request)
            assert json.loads(route.calls.last.request.content) == pair["request"]["json"]
            native = pair["response"]["json"]["choices"][0]["message"]["annotations"]
            assert result.value.extensions["openai.annotations"] == native
            assert all(
                not part.annotations
                for part in result.value.message.parts
                if isinstance(part, PartText)
            )
            assert result.report is not None
            assert any(
                loss.path == "choices[0].message.annotations"
                and loss.disposition == Disposition.EXTENSIONS
                for edge in result.report.edges
                for loss in edge.losses
            )
    finally:
        transport.close()
        await transport.aclose()
