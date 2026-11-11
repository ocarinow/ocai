"""Host-effect accounting is enforceable without pretending a graph edge ran."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

import ocai.openai
from ocai.chat import CANONICAL_CHAT_RESPONSE
from ocai.chat.types import ChatChunk
from ocai.chat.types import StreamAccumulator
from ocai.chat.types import StreamEnd
from ocai.convert import Catalog
from ocai.core import Disposition
from ocai.core import FidelityReport
from ocai.core import FieldLoss
from ocai.core import HostEffectReport
from ocai.core import SemanticShift
from ocai.core.fidelity import FidelityPolicy
from ocai.core.fidelity import FidelityPolicyError
from ocai.core.usage import Usage
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_RESPONSE

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "spec").is_dir())
GOLDEN = ROOT / "spec/fixtures/fidelity/host-effects.json"


def _report() -> FidelityReport:
    document = json.loads(GOLDEN.read_text())["document"]
    return FidelityReport.from_dict(document["end"]["report"])


def test_host_only_shift_is_lossless_but_enforceable() -> None:
    report = _report()
    assert report.lossless and not report.path and not report.edges
    assert report.shifts == list(report.hosts[0].shifts)
    with pytest.raises(FidelityPolicyError) as raised:
        FidelityPolicy(forbidden_shifts=frozenset({"test.masking"})).enforce(
            report, phase="response"
        )
    assert raised.value.report.to_dict() == report.to_dict()
    assert raised.value.report is not report
    assert raised.value.usage is None
    assert raised.value.raw is None


@pytest.mark.parametrize("predicate", [False, True])
@pytest.mark.parametrize("semantic", [False, True])
def test_host_loss_and_shift_policy_retains_provenance_and_accounting(
    predicate: bool,
    semantic: bool,
) -> None:
    report = _report()
    report.hosts.append(
        HostEffectReport(
            "other-host",
            "adapter@2",
            "declaration-2",
            "response",
            losses=(FieldLoss("tool.id", Disposition.DROPPED, 2.0, "Synthetic host effect"),),
        )
    )
    usage = Usage.from_dict(
        {"consumptions": [{"modality": "text", "unit": "tokens", "source": "input", "value": 7}]}
    )
    policy = (
        FidelityPolicy(allow_shift=lambda shift: shift.kind != "test.masking")
        if predicate and semantic
        else FidelityPolicy(allow_loss=lambda loss: loss.disposition != Disposition.DROPPED)
        if predicate
        else FidelityPolicy(forbidden_shifts=frozenset({"test.masking"}))
        if semantic
        else FidelityPolicy(forbidden_dispositions=frozenset({Disposition.DROPPED}))
    )
    with pytest.raises(FidelityPolicyError) as raised:
        policy.enforce(report, phase="response", usage=usage, delivered_events=3)
    assert not report.lossless and report.total_cost == 2.0
    assert report.dropped == [report.hosts[1].losses[0]]
    assert raised.value.usage == usage and raised.value.usage is not usage
    assert raised.value.usage and raised.value.usage.total_tokens == 7
    assert raised.value.partial and raised.value.delivered_events == 3
    assert raised.value.report.hosts[1].contract_id == "declaration-2"
    report.hosts.clear()
    assert len(raised.value.report.hosts) == 2


def test_host_report_merge_preserves_real_conversion_path() -> None:
    pair = json.loads((Path(__file__).parent / "http/openai_chat_completion.json").read_text())
    decoded = Catalog.of(ocai.openai.FRAGMENT).convert(
        pair["response"]["json"], CHAT_COMPLETIONS_RESPONSE, CANONICAL_CHAT_RESPONSE
    )
    report = decoded.report
    original = deepcopy(report)
    host_report = _report()
    assert report.merge(host_report) is report
    assert report.path == original.path and report.edges == original.edges
    assert report.losses == original.losses
    assert report.shifts == original.shifts + host_report.shifts
    assert report.hosts == host_report.hosts
    # Equal records may represent distinct effects: merge must not silently deduplicate.
    report.merge(host_report)
    assert report.hosts == host_report.hosts * 2


def test_golden_terminal_round_trip_and_schema_fields() -> None:
    document = json.loads(GOLDEN.read_text())["document"]
    chunk = ChatChunk.from_dict(document)
    assert chunk.to_dict() == document
    assert chunk.end and chunk.end.report
    assert chunk.end.report.hosts[0].adapter == "filter-response@1"
    assert StreamEnd.from_dict(chunk.end.to_dict()).to_dict() == chunk.end.to_dict()
    schema = json.loads((ROOT / "spec/schema/stream_end.schema.json").read_text())
    properties = schema["$defs"]["hostEffectReport"]["properties"]
    assert {item.name for item in fields(HostEffectReport)} | {"cost"} == set(properties)
    assert set(schema["$defs"]["fidelityReport"]["properties"]) == {
        "path",
        "lossless",
        "total_cost",
        "edges",
        "hosts",
    }


def test_old_reports_keep_wire_form_and_positional_constructor() -> None:
    for report in (FidelityReport(), FidelityReport([])):
        wire: dict[str, Any] = {"path": [], "lossless": True, "total_cost": 0, "edges": []}
        assert report.to_dict() == wire
        assert FidelityReport.from_dict(wire).to_dict() == wire
        assert not report.hosts


def test_open_codes_and_derived_values_are_not_reinterpreted() -> None:
    wire = _report().to_dict()
    host = wire["hosts"][0]
    host["phase"] = "future.phase"
    host["shifts"][0]["kind"] = "future.behavior"
    host["cost"] = 999
    host["losses"] = [{"path": "future", "disposition": "future.kind", "severity": 3}]
    wire.update(path=["invented/node"], lossless=True, total_cost=999)
    report = FidelityReport.from_dict(wire)
    assert report.hosts[0].phase == "future.phase"
    assert report.shifts[0].kind == "future.behavior"
    assert report.losses[0].disposition == Disposition.DROPPED
    assert not report.lossless and report.total_cost == 3
    assert not report.path and report.hosts[0].cost == 3


@pytest.mark.parametrize("value", [None, False, 3, "future", [], {"future": True}])
def test_malformed_host_lanes_decode_without_raising(value: Any) -> None:
    assert not FidelityReport.from_dict({"hosts": value}).hosts
    host = HostEffectReport.from_dict({"losses": value, "shifts": value})
    assert host.losses == () and host.shifts == ()


def test_raising_predicate_cannot_approve_host_findings() -> None:
    def unavailable(shift: SemanticShift) -> bool:
        raise RuntimeError("private policy state")

    with pytest.raises(FidelityPolicyError) as raised:
        FidelityPolicy(allow_shift=unavailable).enforce(_report(), phase="response")
    assert "private policy state" not in str(raised.value)


def test_host_evidence_does_not_change_fold_payload_or_duplicate_on_finalize() -> None:
    triple = json.loads((ROOT / "spec/fixtures/canonical/chat_stream_fold.json").read_text())
    chunks = [ChatChunk.from_dict(chunk) for chunk in triple["chunks"]]
    terminal = chunks[-1]
    assert terminal.end is not None
    terminal.end.report = _report()
    accumulator = StreamAccumulator()
    for chunk in chunks:
        accumulator.feed(chunk)
    assert accumulator.finalize().to_dict() == triple["response"]
    assert accumulator.finalize().to_dict() == triple["response"]
    assert terminal.end.report.hosts == _report().hosts
