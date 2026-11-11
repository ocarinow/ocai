"""`EdgeContract.certify` — the certification gate (WU-04).

Exercises the normative semantics stated in the `certify` docstring: the
severity partial order over `Disposition` (same-band substitution is a
violation, milder is clean), census path matching (`[]` wildcards and
selector tokens vs concrete indices, exact-path precedence, no prefix
matching), declared-but-unexercised entries, and runtime `SemanticShift`
certification against `semantic_shifts`.

The echo-example criterion: the `ocai-contrib-echo` template is not a
workspace member and its wiring predates the current API (it constructs
`EdgeContract(fields=...)` and calls a `check_edge` helper that never
shipped), so — per the WU note — the equivalent identity-edge certification
case is built HERE from the example's own golden fixture:
`examples/ocai-contrib-echo/fixtures/echo_chat_request.json` is loaded, an
identity `Edge` with the same empty (lossless) contract is run over it, and
`conformance.certify_edge` must return `[]`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from ocai.convert import DeclaredDisposition
from ocai.convert import Edge
from ocai.convert import EdgeContract
from ocai.convert import EdgeOutput
from ocai.convert import conformance
from ocai.core import CHAT_REQUEST
from ocai.core import Disposition
from ocai.core import FieldLoss
from ocai.core import NodeId
from ocai.core import Origin
from ocai.core import SemanticShift
from ocai.core import ShiftKind
from ocai.core import semantic_equal

ORIGIN = Origin(distribution="ocai-tests", version="0.0.0")


def _loss(path: str, disposition: Disposition) -> FieldLoss:
    return FieldLoss(path=path, disposition=disposition)


def _census(**entries: Disposition) -> dict[str, DeclaredDisposition]:
    """Build a census from `path=disposition` pairs (dots spelled as `__`)."""
    return {path.replace("__", "."): DeclaredDisposition(d) for path, d in entries.items()}


# --- Severity partial order ---------------------------------------------------


def test_empty_census_certifies_empty_runtime() -> None:
    assert EdgeContract().certify([]) == []


def test_undeclared_path_is_violation() -> None:
    violations = EdgeContract().certify([_loss("config.top_k", Disposition.DROPPED)])
    assert len(violations) == 1
    violation = violations[0]
    assert violation.path == "config.top_k"
    assert violation.actual is Disposition.DROPPED
    assert violation.declared is None
    assert violation.shift_kind is None


def test_undeclared_exact_record_is_clean() -> None:
    # Paths not in the census are implicitly declared EXACT, so a runtime
    # EXACT record at an undeclared path is exactly within declaration.
    assert EdgeContract().certify([_loss("model", Disposition.EXACT)]) == []


def test_dropped_where_approximated_declared_is_violation() -> None:
    contract = EdgeContract(census=_census(config__temperature=Disposition.APPROXIMATED))
    violations = contract.certify([_loss("config.temperature", Disposition.DROPPED)])
    assert len(violations) == 1
    assert violations[0].actual is Disposition.DROPPED
    assert violations[0].declared is Disposition.APPROXIMATED


def test_milder_than_declared_is_clean() -> None:
    contract = EdgeContract(
        census=_census(a=Disposition.DROPPED, b=Disposition.APPROXIMATED, c=Disposition.RENAMED)
    )
    assert (
        contract.certify(
            [
                _loss("a", Disposition.APPROXIMATED),  # band 2 < band 3
                _loss("b", Disposition.EXTENSIONS),  # band 1 < band 2
                _loss("c", Disposition.EXACT),  # band 0 < band 1
            ]
        )
        == []
    )


def test_equal_disposition_is_clean() -> None:
    contract = EdgeContract(census=_census(x=Disposition.UNSUPPORTED))
    assert contract.certify([_loss("x", Disposition.UNSUPPORTED)]) == []


def test_same_band_substitution_is_violation() -> None:
    # Same-band dispositions are incomparable: declaring one never licenses
    # running the other (they occupy different LossGrade slots).
    contract = EdgeContract(
        census=_census(a=Disposition.APPROXIMATED, b=Disposition.RENAMED, c=Disposition.DROPPED)
    )
    violations = contract.certify(
        [
            _loss("a", Disposition.EMULATED),
            _loss("b", Disposition.EXTENSIONS),
            _loss("c", Disposition.UNSUPPORTED),
        ]
    )
    assert [v.path for v in violations] == ["a", "b", "c"]


# --- Path matching ------------------------------------------------------------


def test_wildcard_matches_concrete_indices() -> None:
    contract = EdgeContract(
        census={"messages[].parts[].text": DeclaredDisposition(Disposition.APPROXIMATED)}
    )
    assert contract.certify([_loss("messages[2].parts[0].text", Disposition.APPROXIMATED)]) == []
    violations = contract.certify([_loss("messages[2].parts[0].text", Disposition.DROPPED)])
    assert len(violations) == 1
    assert violations[0].declared is Disposition.APPROXIMATED


def test_selector_bracket_matches_any_index() -> None:
    # Non-numeric selector tokens (the `parts[reasoning]` census style) match
    # any concrete runtime index — a path cannot discriminate content types.
    contract = EdgeContract(
        census={"messages[].parts[reasoning]": DeclaredDisposition(Disposition.DROPPED)}
    )
    assert contract.certify([_loss("messages[0].parts[3]", Disposition.DROPPED)]) == []


def test_concrete_index_matches_only_itself() -> None:
    contract = EdgeContract(
        census={"choices[0].message.content": DeclaredDisposition(Disposition.RENAMED)}
    )
    assert contract.certify([_loss("choices[0].message.content", Disposition.RENAMED)]) == []
    violations = contract.certify([_loss("choices[1].message.content", Disposition.RENAMED)])
    assert len(violations) == 1
    assert violations[0].declared is None  # choices[1] is undeclared territory


def test_exact_path_precedence_over_wildcard() -> None:
    # The verbatim entry alone governs its path, even when a broader wildcard
    # entry would have permitted the runtime disposition.
    contract = EdgeContract(
        census={
            "messages[].parts[]": DeclaredDisposition(Disposition.DROPPED),
            "messages[0].parts[0]": DeclaredDisposition(Disposition.RENAMED),
        }
    )
    violations = contract.certify([_loss("messages[0].parts[0]", Disposition.DROPPED)])
    assert len(violations) == 1
    assert violations[0].declared is Disposition.RENAMED
    # Off the exact path, the wildcard entry still permits the drop.
    assert contract.certify([_loss("messages[1].parts[2]", Disposition.DROPPED)]) == []


def test_any_matching_wildcard_entry_permits() -> None:
    # Overlapping selector entries: within declaration if ANY match bounds it.
    contract = EdgeContract(
        census={
            "messages[].parts[text]": DeclaredDisposition(Disposition.RENAMED),
            "messages[].parts[image]": DeclaredDisposition(Disposition.DROPPED),
        }
    )
    assert contract.certify([_loss("messages[0].parts[1]", Disposition.DROPPED)]) == []
    # But nothing matching permits UNSUPPORTED (same band as DROPPED,
    # incomparable): still a violation, reported against the loosest bound.
    violations = contract.certify([_loss("messages[0].parts[1]", Disposition.UNSUPPORTED)])
    assert len(violations) == 1
    assert violations[0].declared is Disposition.DROPPED


def test_no_prefix_matching() -> None:
    contract = EdgeContract(census=_census(config=Disposition.DROPPED))
    violations = contract.certify([_loss("config.top_k", Disposition.DROPPED)])
    assert len(violations) == 1
    assert violations[0].declared is None


def test_unexercised_census_entries_are_clean() -> None:
    # Declared-but-never-exercised entries produce no violation: the census
    # is an upper bound, not an exercise checklist.
    contract = EdgeContract(
        census=_census(
            a=Disposition.DROPPED,
            b=Disposition.APPROXIMATED,
            **{"messages[].parts[audio]": Disposition.UNSUPPORTED},
        ),
        semantic_shifts=(SemanticShift(kind=ShiftKind.RELOCATION, path="messages[]"),),
    )
    assert contract.certify([], []) == []


# --- Semantic-shift certification ----------------------------------------------


def test_undeclared_shift_is_violation() -> None:
    shift = SemanticShift(kind=ShiftKind.RELOCATION, path="messages[0].parts[2]")
    violations = EdgeContract().certify([], [shift])
    assert len(violations) == 1
    violation = violations[0]
    assert violation.shift_kind == ShiftKind.RELOCATION
    assert violation.path == "messages[0].parts[2]"
    assert violation.actual is None
    assert violation.declared is None


def test_declared_shift_selector_path_covers_runtime_shift() -> None:
    contract = EdgeContract(
        semantic_shifts=(
            SemanticShift(kind=ShiftKind.RELOCATION, path="messages[].parts[tool_result]"),
        )
    )
    runtime = SemanticShift(
        kind=ShiftKind.RELOCATION,
        path="messages[0].parts[2]",
        note="tool result relocated to a sibling `role: tool` wire message",
    )
    assert contract.certify([], [runtime]) == []


def test_declared_shift_empty_path_covers_any_location() -> None:
    contract = EdgeContract(semantic_shifts=(SemanticShift(kind=ShiftKind.EMULATION),))
    assert contract.certify([], [SemanticShift(kind=ShiftKind.EMULATION, path="messages[7]")]) == []


def test_shift_kind_mismatch_is_violation() -> None:
    contract = EdgeContract(
        semantic_shifts=(SemanticShift(kind=ShiftKind.RELOCATION, path="messages[]"),)
    )
    violations = contract.certify([], [SemanticShift(ShiftKind.ID_REGENERATED, "messages[3]")])
    assert len(violations) == 1
    assert violations[0].shift_kind == ShiftKind.ID_REGENERATED


def test_located_declared_shift_does_not_cover_unlocated_runtime_shift() -> None:
    # A runtime shift with no location is only covered by a kind-matching
    # declaration whose path is also empty.
    contract = EdgeContract(
        semantic_shifts=(SemanticShift(kind=ShiftKind.RELOCATION, path="messages[]"),)
    )
    violations = contract.certify([], [SemanticShift(kind=ShiftKind.RELOCATION)])
    assert len(violations) == 1


# --- certify_edge integration + the echo-example criterion ---------------------


ECHO_FIXTURE = "examples/ocai-contrib-echo/fixtures/echo_chat_request.json"


def _identity(payload: Any) -> EdgeOutput:
    return EdgeOutput(payload)


def _echo_node(ref: dict[str, str]) -> NodeId:
    assert ref["shape"] == "chat.request"
    return NodeId(ref["provider"], ref["interface"], ref["tag"], CHAT_REQUEST, date(2026, 7, 1))


def test_certify_edge_over_echo_fixture_returns_empty(repo_root: Path) -> None:
    # The echo template's own test wiring predates the current API, so this
    # is the WU-04 echo criterion rebuilt on the real API: identity edges
    # with the empty (declared-lossless) contract, certified over the echo
    # example's golden fixture.
    fixture = conformance.load_fixture(repo_root / ECHO_FIXTURE)
    src = _echo_node(fixture["src"])
    dst = _echo_node(fixture["dst"])
    for edge in (
        Edge(src, dst, _identity, EdgeContract(), ORIGIN, "echo decode (identity)"),
        Edge(dst, src, _identity, EdgeContract(), ORIGIN, "echo encode (identity)"),
    ):
        assert conformance.certify_edge(edge, [fixture["input"]]) == []
    # The identity edge also reproduces the fixture's expected output.
    assert semantic_equal(_identity(fixture["input"]).value, fixture["expect"])
    assert fixture["expect_losses"] == [] and fixture["expect_shifts"] == []


def test_certify_edge_catches_a_lying_edge() -> None:
    # An edge claiming lossless (empty census) that drops a field at run
    # time cannot ship — the exact dishonesty the gate exists to prevent.
    def _lying(payload: Any) -> EdgeOutput:
        return EdgeOutput(payload, losses=(_loss("config.top_k", Disposition.DROPPED),))

    node_a = NodeId("acme", "chat", "v1", CHAT_REQUEST, date(2026, 1, 1))
    node_b = NodeId("acme", "chat", "v2", CHAT_REQUEST, date(2026, 6, 1))
    edge = Edge(node_a, node_b, _lying, EdgeContract(), ORIGIN)
    violations = conformance.certify_edge(edge, [{"config": {"top_k": 4}}])
    assert len(violations) == 1
    assert violations[0].actual is Disposition.DROPPED
    assert violations[0].declared is None
