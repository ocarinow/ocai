"""`EdgeContract` — what an edge declares it will do to every field (§4.2).

An edge does not carry an author-declared float weight anymore. It carries a
**per-field disposition census**: for every field path the conversion touches
non-exactly, the contract declares *what will happen to it* (`Disposition`)
and why. Three consumers read the census:

- **The planner** (`ocai.convert.graph.ConversionGraph`) derives its cost from
  `loss_grade()` — a lexicographic tuple that is impossible to game with a
  magic number: an edge is cheaper only by *actually declaring less loss*.
- **The conformance harness** (`ocai.convert.conformance.certify_edge`)
  certifies at build time that the edge's *runtime* `FieldLoss` records never
  exceed the declaration — an edge claiming lossless that drops a field
  cannot ship.
- **Auditors** read the census straight out of `Catalog.lock()`.

Declared `SemanticShift`s live beside the census because field loss and
semantic divergence are different kinds of honesty (`ocai.core.fidelity`):
a contract may be field-lossless yet still declare that it relocates the
system role or regenerates tool-call ids.
"""

from __future__ import annotations

from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field

from ocai.core.fidelity import Disposition
from ocai.core.fidelity import FieldLoss
from ocai.core.fidelity import SemanticShift

# The lexicographic planner cost derived from a contract:
# (unsupported + dropped count, approximated count, emulated count, hops).
# Tuples compare left-to-right, so the planner prefers "breaks/loses nothing"
# over "approximates nothing" over "emulates nothing" over "fewer hops" — the
# hops component (always 1 per edge) replaces the old float HOP_PENALTY: two
# equally-lossy paths still tie-break toward the shorter one, with no float.
type LossGrade = tuple[int, int, int, int]

# The dispositions counted as hard breakage/loss in the leading grade slot.
_BROKEN = frozenset({Disposition.DROPPED, Disposition.UNSUPPORTED})

# The severity bands of the certification partial order (see
# `EdgeContract.certify`, whose docstring is the normative statement):
# EXACT < RENAMED/EXTENSIONS < APPROXIMATED/EMULATED < DROPPED/UNSUPPORTED.
# Distinct dispositions sharing a band are INCOMPARABLE, not equal — they
# occupy different `LossGrade` slots and make different claims to auditors,
# so declaring one never licenses running the other.
_SEVERITY_BAND: Mapping[Disposition, int] = {
    Disposition.EXACT: 0,
    Disposition.RENAMED: 1,
    Disposition.EXTENSIONS: 1,
    Disposition.APPROXIMATED: 2,
    Disposition.EMULATED: 2,
    Disposition.DROPPED: 3,
    Disposition.UNSUPPORTED: 3,
}


def _within(actual: Disposition, declared: Disposition) -> bool:
    """Return whether `actual` is within `declared` under the partial order.

    True iff `actual == declared` or `actual` sits in a strictly lower
    severity band — the executable form of "a contract is an upper bound".

    Args:
        actual: The disposition a run of the edge actually applied.
        declared: The disposition the census declared.

    Returns:
        True when the runtime record does not exceed the declaration.
    """
    return actual == declared or _SEVERITY_BAND[actual] < _SEVERITY_BAND[declared]


# A path token: `(is_bracket, text)`. Names are `(False, "parts")`; bracket
# tokens are `(True, "2")` / `(True, "")` / `(True, "reasoning")`.
type _PathToken = tuple[bool, str]


def _tokenize(path: str) -> tuple[_PathToken, ...]:
    """Split a dotted/bracketed field path into its token sequence.

    `"messages[0].parts[2].is_error"` becomes name `messages`, bracket `0`,
    name `parts`, bracket `2`, name `is_error`. Tolerant, never raises: an
    unterminated `[` consumes the remainder of the path as one bracket
    token.

    Args:
        path: The field path to split.

    Returns:
        The ordered `(is_bracket, text)` tokens.
    """
    tokens: list[_PathToken] = []
    name = ""
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == "[":
            if name:
                tokens.append((False, name))
                name = ""
            end = path.find("]", i + 1)
            if end < 0:
                tokens.append((True, path[i + 1 :]))
                return tuple(tokens)
            tokens.append((True, path[i + 1 : end]))
            i = end + 1
        elif ch == ".":
            if name:
                tokens.append((False, name))
                name = ""
            i += 1
        else:
            name += ch
            i += 1
    if name:
        tokens.append((False, name))
    return tuple(tokens)


def _is_concrete_index(token: str) -> bool:
    """Return whether a bracket token is a concrete index (ASCII digits only).

    Args:
        token: The text between one `[` `]` pair.

    Returns:
        True for tokens like `"0"`/`"12"`; False for the empty wildcard
        `""` and for selector tokens like `"reasoning"` or `"1:"`.
    """
    return token != "" and token.isascii() and token.isdigit()


def _path_matches(declared: str, runtime: str) -> bool:
    """Return whether a declared census path covers a runtime record path.

    The normative matching rule is stated in `EdgeContract.certify`; in
    short: equal token sequences, names verbatim, and a declared bracket
    token constrains the runtime token only when it is a concrete index —
    the empty wildcard `[]` and non-numeric selectors match any runtime
    bracket token. No prefix matching.

    Args:
        declared: The census (or declared-shift) path pattern.
        runtime: The concrete path a runtime record was emitted at.

    Returns:
        True when `declared` covers `runtime`.
    """
    if declared == runtime:
        return True
    declared_tokens = _tokenize(declared)
    runtime_tokens = _tokenize(runtime)
    if len(declared_tokens) != len(runtime_tokens):
        return False
    for (d_bracket, d_text), (r_bracket, r_text) in zip(
        declared_tokens, runtime_tokens, strict=True
    ):
        if d_bracket != r_bracket:
            return False
        if d_text == r_text:
            continue
        if not d_bracket:
            return False  # names must match verbatim
        if _is_concrete_index(d_text):
            return False  # a concrete index matches only itself
    return True


@dataclass(frozen=True, slots=True)
class DeclaredDisposition:
    """One census entry: the declared fate of one field, with its rationale.

    The value side of `EdgeContract.census`. Kept as a named object (not a
    bare `Disposition`) so every declared loss can carry the author's
    explanation — the note surfaces verbatim in lockfiles and audit reviews.

    Attributes:
        disposition: What the edge declares it does to the field.
        note: The author's one-line rationale for the mapping or the loss.
    """

    disposition: Disposition
    note: str = ""


@dataclass(frozen=True, slots=True)
class ContractViolation:
    """One certified breach: a runtime record that exceeds the declaration.

    Produced by `EdgeContract.certify`, for either lane of the contract: a
    `FieldLoss` exceeding the census, or a `SemanticShift` the contract
    never declared. A violation is a shipping blocker, not a report entry:
    the conformance harness fails the build on any non-empty violation
    list, because an undeclared loss is exactly the silent dishonesty the
    contract system exists to prevent.

    Attributes:
        path: The path the runtime record was recorded at.
        actual: The disposition the edge actually applied at run time; None
            on a semantic-shift violation (shifts have no disposition).
        declared: The disposition the census declared for the path — None
            when the path was not in the census at all, or on a
            semantic-shift violation.
        shift_kind: The runtime `SemanticShift.kind` on a shift violation;
            None on a field-loss violation.
        note: A human-readable explanation of the breach.
    """

    path: str
    actual: Disposition | None = None
    declared: Disposition | None = None
    shift_kind: str | None = None
    note: str = ""


@dataclass(frozen=True, slots=True)
class EdgeContract:
    """An edge's declared per-field disposition census (§4.2).

    Attached to every `Edge` and `StreamEdge` in a `CatalogFragment`. Fields
    *not* in the census are implicitly declared `EXACT`: the census names
    only what the edge renames, approximates, emulates, banks in
    `extensions`, drops, or cannot support — so a truly lossless edge ships
    an empty census and grades `(0, 0, 0, 1)`.

    Attributes:
        census: The declared mapping from field path (dotted/bracketed, e.g.
            `"messages[].parts[].args_json"`) to its `DeclaredDisposition`.
        semantic_shifts: The semantics-level divergences the edge declares
            up front (relocations, emulations, id regeneration). Runtime
            `SemanticShift` records are certified against these the same way
            runtime losses are certified against `census`.
        note: A human-readable summary of what the edge converts.
    """

    census: Mapping[str, DeclaredDisposition] = field(default_factory=dict)
    semantic_shifts: tuple[SemanticShift, ...] = ()
    note: str = ""

    def loss_grade(self) -> LossGrade:
        """Derive this edge's lexicographic planner cost from the census.

        The only source of planner weight in the system — there is no
        author-declared number to tune. Counts census entries per lossy
        disposition band; `EXACT`, `RENAMED`, and `EXTENSIONS` entries cost
        nothing (the information survives recoverably). The trailing `1` is
        this edge's hop contribution: path grades are summed elementwise, so
        equally-lossy plans prefer fewer hops.

        Returns:
            The `(unsupported+dropped, approximated, emulated, hops=1)`
            grade for one traversal of this edge.
        """
        broken = 0
        approximated = 0
        emulated = 0
        for declared in self.census.values():
            if declared.disposition in _BROKEN:
                broken += 1
            elif declared.disposition is Disposition.APPROXIMATED:
                approximated += 1
            elif declared.disposition is Disposition.EMULATED:
                emulated += 1
        return (broken, approximated, emulated, 1)

    def certify(
        self,
        runtime_losses: Iterable[FieldLoss],
        runtime_shifts: Iterable[SemanticShift] = (),
    ) -> list[ContractViolation]:
        """Check runtime loss and shift records against this declaration.

        The certification half of the contract: called by the conformance
        harness (`ocai.convert.conformance.certify_edge`) with the
        `FieldLoss` and `SemanticShift` records an edge function actually
        emitted over golden fixtures. Runtime records milder than declared
        are fine — a contract is an upper bound, not an exact prediction —
        and declared-but-unexercised entries (census or shifts) produce no
        violation: a contract is an upper bound, not an exercise checklist.
        The semantics below are **normative** for every language port.

        **Severity partial order.** `actual` is within `declared` iff
        `actual == declared` or `actual` sits in a strictly lower band of
        `EXACT < RENAMED/EXTENSIONS < APPROXIMATED/EMULATED <
        DROPPED/UNSUPPORTED`. Distinct dispositions sharing a band are
        *incomparable*: declaring `APPROXIMATED` never licenses running
        `EMULATED` (they occupy different `LossGrade` slots, so the swap
        would falsify the lockfile's grade), declaring `RENAMED` never
        licenses `EXTENSIONS`, and declaring `DROPPED` never licenses
        `UNSUPPORTED` — same-band substitution is a violation.

        **Path matching.** A path is its token sequence of names and
        bracket tokens (`"messages[0].parts[2].is_error"` is name
        `messages`, bracket `0`, name `parts`, bracket `2`, name
        `is_error`). A census path covers a runtime path iff the sequences
        have the same length and token kinds position by position, every
        name is equal verbatim, and every census bracket token matches the
        runtime one: a concrete index (ASCII digits, e.g. `[0]`) matches
        only the identical token; the empty wildcard `[]` and non-numeric
        selector tokens (e.g. `[reasoning]`, `[1:]`) match any runtime
        bracket token. There is no prefix matching — a census entry for a
        parent path never governs a child path.

        **Reserved recursive-descent token.** The census token `[**]` is
        RESERVED for "this entry covers any suffix below this point" —
        recursive descent, needed for unbounded trees (a vectorstore filter
        tree has no fixed depth). It MUST NOT be used today: the current
        parser would treat `**` as an ordinary non-numeric selector (one
        level, any bracket token), silently under-covering. The
        implementation lands with the vectorstore capability.

        **Resolution per runtime loss.** (1) *Exact-path precedence*: when
        the census holds the runtime path verbatim, that entry alone
        governs. (2) Otherwise the record is within declaration when it is
        within *any* pattern-matching entry — selector entries such as
        `parts[text]`/`parts[reasoning]` deliberately overlap on the same
        index space because a path alone cannot discriminate content
        types, so the census bounds the edge through the most permissive
        matching declaration. (3) Otherwise the path is undeclared and
        therefore implicitly `EXACT`: any non-`EXACT` record is a
        violation carrying `declared=None`.

        **Shift certification.** A runtime `SemanticShift` is within
        declaration iff some declared shift has the same `kind` and its
        path covers the runtime path: a declared empty path covers any
        location; otherwise the declared path must cover the runtime path
        under the path-matching rule above (a runtime shift with an empty
        path is covered only by a kind-matching declaration whose path is
        also empty). Notes are never compared. An uncovered shift is a
        violation carrying `shift_kind` and no dispositions.

        Args:
            runtime_losses: The field-level records one or more runs of the
                edge function emitted.
            runtime_shifts: The semantics-level records the same runs
                emitted, certified against `semantic_shifts`.

        Returns:
            The violations found, empty when the runtime stayed within the
            declaration. Non-empty means the edge cannot ship.
        """
        violations: list[ContractViolation] = []
        for loss in runtime_losses:
            exact = self.census.get(loss.path)
            if exact is not None:
                if not _within(loss.disposition, exact.disposition):
                    violations.append(
                        ContractViolation(
                            path=loss.path,
                            actual=loss.disposition,
                            declared=exact.disposition,
                            note="runtime disposition exceeds the exact-path declaration",
                        )
                    )
                continue
            matches = [
                entry for pattern, entry in self.census.items() if _path_matches(pattern, loss.path)
            ]
            if matches:
                if not any(_within(loss.disposition, entry.disposition) for entry in matches):
                    # Report against the loosest matching bound — the one the
                    # runtime record still managed to exceed.
                    loosest = max(matches, key=lambda entry: _SEVERITY_BAND[entry.disposition])
                    violations.append(
                        ContractViolation(
                            path=loss.path,
                            actual=loss.disposition,
                            declared=loosest.disposition,
                            note="runtime disposition exceeds every matching census declaration",
                        )
                    )
                continue
            if loss.disposition is not Disposition.EXACT:
                violations.append(
                    ContractViolation(
                        path=loss.path,
                        actual=loss.disposition,
                        declared=None,
                        note="path not in the census (undeclared paths are implicitly EXACT)",
                    )
                )
        for shift in runtime_shifts:
            covered = any(
                declared.kind == shift.kind
                and (declared.path == "" or _path_matches(declared.path, shift.path))
                for declared in self.semantic_shifts
            )
            if not covered:
                violations.append(
                    ContractViolation(
                        path=shift.path,
                        shift_kind=shift.kind,
                        note="semantic shift not declared by the contract",
                    )
                )
        return violations
