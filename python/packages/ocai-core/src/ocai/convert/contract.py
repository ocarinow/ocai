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
    """One certified breach: runtime loss that exceeds the declared census.

    Produced by `EdgeContract.certify`. A violation is a shipping blocker,
    not a report entry: the conformance harness fails the build on any
    non-empty violation list, because an undeclared loss is exactly the
    silent dishonesty the contract system exists to prevent.

    Attributes:
        path: The field path the runtime loss was recorded at.
        actual: The disposition the edge actually applied at run time.
        declared: The disposition the census declared for the path, or None
            when the path was not in the census at all.
        note: A human-readable explanation of the breach.
    """

    path: str
    actual: Disposition
    declared: Disposition | None = None
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

    def certify(self, runtime_losses: Iterable[FieldLoss]) -> list[ContractViolation]:
        """Check runtime loss records against this declaration.

        The certification half of the contract: called by the conformance
        harness (`ocai.convert.conformance.certify_edge`) with the
        `FieldLoss` records an edge function actually emitted over golden
        fixtures. A runtime loss *exceeds* the declaration when its path is
        not in the census at all, or when its disposition is more severe
        than the declared one (e.g. declared `APPROXIMATED`, ran `DROPPED`).
        Runtime records milder than declared are fine — a contract is an
        upper bound, not an exact prediction.

        Args:
            runtime_losses: The field-level records one or more runs of the
                edge function emitted.

        Returns:
            The violations found, empty when the runtime stayed within the
            declaration. Non-empty means the edge cannot ship.
        """
        # TODO: needs a severity partial order over Disposition (EXACT <
        # RENAMED/EXTENSIONS < APPROXIMATED/EMULATED < DROPPED/UNSUPPORTED),
        # path matching that understands `[]` wildcards vs concrete indices,
        # and the matching rule for declared-but-never-exercised entries.
        raise NotImplementedError
