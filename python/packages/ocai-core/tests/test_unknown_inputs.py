"""The unknown-X vectors run against the chat IR decoders (WU-05).

Exercises `conformance.check_unknown_inputs` / `assert_unknown_vector` over
`spec/fixtures/unknown/` — the normative total-decode vectors every language
port must pass (rule 6). Vectors are grouped per decoder by filename pattern
(`message_*`, `chat_request_*`, `deltas_*`, `finish_*`), a coverage test
proves no vector is silently skipped, direct pins tie each mandated behavior
to its concrete fallback type, and the bite tests prove the harness fails on
decoders that raise, mistype a fallback, or drop material.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from ocai.chat.types.finish import DetailOpaque
from ocai.chat.types.finish import FinishInfo
from ocai.chat.types.message import Message
from ocai.chat.types.parts import PartText
from ocai.chat.types.parts import PartUnknown
from ocai.chat.types.request import ChatRequest
from ocai.chat.types.stream import DeltaUnknown
from ocai.chat.types.stream import cast_delta
from ocai.convert.conformance import assert_unknown_vector
from ocai.convert.conformance import check_unknown_inputs


def _find_repo_root(start: Path) -> Path:
    """Walk upward from `start` to the directory containing `spec/fixtures/`."""
    for parent in [start, *start.parents]:
        if (parent / "spec" / "fixtures").is_dir():
            return parent
    raise RuntimeError("could not locate repo root (no spec/fixtures/ found)")


UNKNOWN_DIR = _find_repo_root(Path(__file__).resolve()) / "spec" / "fixtures" / "unknown"

# One decoder per vector family, selected by filename pattern — the wiring a
# plugin's suite mirrors for its own wire-side vectors.
DECODERS: list[tuple[str, Callable[[dict[str, Any]], Any]]] = [
    ("message_*.json", Message.from_dict),
    ("chat_request_*.json", ChatRequest.from_dict),
    ("deltas_*.json", cast_delta),
    ("finish_*.json", FinishInfo.from_dict),
]


def _vector(name: str) -> dict[str, Any]:
    """Load one unknown vector by filename."""
    return json.loads((UNKNOWN_DIR / name).read_text())


# ---------------------------------------------------------------------------
# The normative vectors pass against the chat IR decoders.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("pattern", "decode"), DECODERS, ids=[p for p, _ in DECODERS])
def test_unknown_vectors_pass(pattern: str, decode: Callable[[dict[str, Any]], Any]) -> None:
    """Every vector in the family decodes totally and round-trips honestly."""
    assert check_unknown_inputs(UNKNOWN_DIR, decode=decode, pattern=pattern)


def test_every_vector_in_the_directory_is_exercised() -> None:
    """No vector is silently skipped by the pattern wiring."""
    checked: set[Path] = set()
    for pattern, decode in DECODERS:
        checked.update(check_unknown_inputs(UNKNOWN_DIR, decode=decode, pattern=pattern))
    assert checked == set(UNKNOWN_DIR.glob("*.json"))


# ---------------------------------------------------------------------------
# Direct pins: each mandated behavior lands on its concrete fallback.
# ---------------------------------------------------------------------------


def test_unknown_part_tag_decodes_to_part_unknown() -> None:
    """An unrecognized part tag falls back to `PartUnknown`, byte-faithful."""
    document = _vector("message_unknown_part_tag.json")["document"]
    message = Message.from_dict(document)
    part = message.parts[1]
    assert isinstance(part, PartUnknown)
    assert part.type == "holographic_frame"
    assert part.to_dict() == document["parts"][1]


def test_unknown_delta_tag_decodes_to_delta_unknown() -> None:
    """An unrecognized delta tag falls back to `DeltaUnknown`, byte-faithful."""
    document = _vector("deltas_unknown_delta_tag.json")["document"]
    delta = cast_delta(document)
    assert isinstance(delta, DeltaUnknown)
    assert delta.to_dict() == document


def test_unknown_envelope_keys_sweep_to_their_owners_extensions() -> None:
    """Undeclared members sweep into the extensions bag of their own object."""
    document = _vector("chat_request_unknown_envelope_key.json")["document"]
    request = ChatRequest.from_dict(document)
    assert request.extensions["routing_tier"] == "priority-express"
    assert request.extensions["watermark"] == {"enabled": True, "profile": "wm-3"}
    assert request.messages[0].extensions["mood"] == "wistful"


def test_unknown_finish_reason_keeps_the_native_lane() -> None:
    """The two-lane form survives: reason `"unknown"`, native verbatim."""
    document = _vector("finish_unknown_reason.json")["document"]
    finish = FinishInfo.from_dict(document)
    assert finish.reason == "unknown"
    assert finish.native == "quantum_decoherence"


def test_unknown_finish_detail_tag_decodes_to_detail_opaque() -> None:
    """An unrecognized detail tag falls back to `DetailOpaque`, byte-faithful."""
    document = _vector("finish_unknown_detail_tag.json")["document"]
    finish = FinishInfo.from_dict(document)
    assert isinstance(finish.detail, DetailOpaque)
    assert finish.detail.to_dict() == document["detail"]


def test_unknown_role_is_preserved_verbatim() -> None:
    """A role core has never seen is never coerced to a sentinel."""
    document = _vector("message_unknown_role.json")["document"]
    assert Message.from_dict(document).role == "narrator"


# ---------------------------------------------------------------------------
# The harness bites: bad decoders fail loudly.
# ---------------------------------------------------------------------------


def test_raising_decoder_violates_total_decode() -> None:
    """A decoder that raises on unknown input is a rule-6 violation."""

    def explode(document: dict[str, Any]) -> Any:
        raise ValueError("boom")

    with pytest.raises(AssertionError, match="total decode violated"):
        assert_unknown_vector({"document": {"type": "x"}, "expect": {}}, decode=explode)


def test_wrong_fallback_type_is_reported() -> None:
    """A fallback landing on the wrong type fails the vector."""
    fixture = {
        "document": {"type": "waveform"},
        "expect": {"fallbacks": [{"path": "", "type": "PartUnknown"}]},
    }
    with pytest.raises(AssertionError, match="PartUnknown"):
        assert_unknown_vector(fixture, decode=cast_delta)  # decodes to DeltaUnknown


def test_undeclared_sweep_fails_the_round_trip() -> None:
    """A sweep the vector did not declare is reported as reshaped material."""
    fixture = {
        "document": {"version": "2026-07", "text": "hi", "type": "text", "mystery": {"a": 1}},
        "expect": {},  # no sweep declared: the round trip must be verbatim
    }
    with pytest.raises(AssertionError, match="lost or reshaped"):
        assert_unknown_vector(fixture, decode=PartText.from_dict)


def test_declared_sweep_makes_the_same_decoder_pass() -> None:
    """Declaring the sweep turns the previous failure into conformance."""
    fixture = {
        "document": {"version": "2026-07", "text": "hi", "type": "text", "mystery": {"a": 1}},
        "expect": {"extensions": [{"owner": "", "key": "mystery"}]},
    }
    assert_unknown_vector(fixture, decode=PartText.from_dict)


def test_unswept_declared_key_is_reported() -> None:
    """A declared sweep whose key stays a plain member fails the vector."""
    fixture = {
        "document": {"version": "2026-07", "text": "hi", "type": "text"},
        "expect": {"extensions": [{"owner": "", "key": "text"}]},
    }
    with pytest.raises(AssertionError, match="sweep"):
        assert_unknown_vector(fixture, decode=PartText.from_dict)


def test_empty_directory_fails(tmp_path: Path) -> None:
    """An empty vector set silently passing would defeat the drift alarm."""
    with pytest.raises(AssertionError, match="nothing was checked"):
        check_unknown_inputs(tmp_path, decode=cast_delta)
