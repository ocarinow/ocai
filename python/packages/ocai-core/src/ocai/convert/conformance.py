"""The conformance harness: the moat, shipped as a product (§4.5).

Plugins validate their conversion logic against the **same** contracts
ocai's first-party fragments use — this module is what makes rule 9
("every edge ships an EdgeContract + golden fixtures") executable rather
than prose. It is pure stdlib (no pytest, no third-party deps), so it runs
under any test runner (or none) and raises plain `AssertionError` on
mismatch. Every equality assertion is `ocai.core.canonjson.semantic_equal`
— the one normative predicate — never `==` on raw dicts.

Four kinds of check, mirroring the four promises an edge makes:

- **Codec round-trips** (`assert_fixture_roundtrip` / `check_codec`):
  `decode(raw)` matches the fixture's canonical form and
  `encode(canonical)` matches the raw wire payload.
- **Graph round-trips** (`assert_graph_roundtrip`): once registered in a
  `Catalog`, a wire node converts through the canonical backbone and back.
- **Fold triples** (`assert_fold_triple` / `check_fold_triples`): the
  streaming ratchet — wire event log → canonical chunks → folded response,
  asserting `fold(stream) == complete` per fixture.
- **Contract certification** (`certify_edge`): runtime `FieldLoss` never
  exceeds the edge's declared `EdgeContract` census — an edge claiming
  lossless that drops a field cannot ship.

Plus the **unknown-X normative fixtures** (`check_unknown_inputs`): the
total-decode guarantee (unknown tags → Unknown types, unknown keys →
`extensions`, never a raise) that every language port must pass.

The helpers are capability-neutral: they take the codec's functions
(`decode`, `encode`, `decode_event`, `fold`) as parameters, so this module
never imports a capability package and the same harness serves chat,
embedding, and vector-store edges alike.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ocai.convert.catalog import Catalog
from ocai.convert.contract import ContractViolation
from ocai.convert.graph import Edge
from ocai.core.canonjson import canonical
from ocai.core.canonjson import semantic_equal
from ocai.core.fidelity import FidelityReport
from ocai.core.identity import NodeId

# A golden fixture: the JSON object documented in `spec/README.md` —
# `{description, source: {provider, interface, tag}, raw, canonical}` for
# conversion fixtures; fold triples additionally carry
# `{events, chunks, response}`.
type Fixture = dict[str, Any]

# `raw` provider payload -> `canonical` IR dict (as produced by `to_dict()`).
type DecodeFn = Callable[[dict[str, Any]], dict[str, Any]]

# `canonical` IR dict -> `raw` provider payload (the encode inverse).
type EncodeFn = Callable[[dict[str, Any]], dict[str, Any]]


def load_fixture(path: str | Path) -> Fixture:
    """Read a single golden fixture from `path`.

    Args:
        path: The fixture JSON file to read.

    Returns:
        The parsed fixture object.
    """
    return json.loads(Path(path).read_text())


def iter_fixtures(
    directory: str | Path, *, pattern: str = "*.json"
) -> Iterator[tuple[Path, Fixture]]:
    """Yield every golden fixture under `directory`, sorted by filename.

    Args:
        directory: The folder of golden fixtures to walk (non-recursive).
        pattern: The glob selecting fixture files. Defaults to `"*.json"`.

    Yields:
        A `(path, fixture)` pair per matching file, in sorted path order.
    """
    for path in sorted(Path(directory).glob(pattern)):
        yield path, load_fixture(path)


def assert_fixture_roundtrip(fixture: Fixture, *, decode: DecodeFn, encode: EncodeFn) -> None:
    """Assert a codec satisfies the golden-fixture contract for one fixture.

    Checks both directions independently under `semantic_equal`: decoding
    the provider `raw` payload yields the expected `canonical` IR, and
    encoding that `canonical` IR yields the original `raw` back (a lossless
    round-trip, up to canonical-JSON semantics — embedded `*_json` strings
    compare parsed, per the parse-compare rule).

    Args:
        fixture: A golden fixture carrying `raw` and `canonical`.
        decode: The plugin's provider-`raw` → canonical-dict function
            (typically `lambda raw: codec.decode(raw).value.to_dict()`).
        encode: The plugin's canonical-dict → provider-`raw` function
            (typically `lambda c: codec.encode(Type.from_dict(c)).value`).

    Raises:
        AssertionError: If either direction does not match the fixture.
    """
    decoded = decode(fixture["raw"])
    assert semantic_equal(decoded, fixture["canonical"]), (
        "decode(raw) did not match the fixture's canonical form.\n"
        f"  expected: {canonical(fixture['canonical'])}\n"
        f"  actual:   {canonical(decoded)}"
    )
    encoded = encode(fixture["canonical"])
    assert semantic_equal(encoded, fixture["raw"]), (
        "encode(canonical) did not round-trip back to the fixture's raw payload.\n"
        f"  expected: {canonical(fixture['raw'])}\n"
        f"  actual:   {canonical(encoded)}"
    )


def check_codec(directory: str | Path, *, decode: DecodeFn, encode: EncodeFn) -> list[Path]:
    """Run `assert_fixture_roundtrip` over every fixture in `directory`.

    A convenience for a plugin's test suite: point it at the plugin's
    fixture folder and it checks each one, failing loudly if the folder is
    empty (an empty fixture set silently "passing" would defeat the drift
    alarm).

    Args:
        directory: The folder of golden fixtures to check.
        decode: The codec's provider-`raw` → canonical-dict function.
        encode: The codec's canonical-dict → provider-`raw` function.

    Returns:
        The list of fixture paths that were checked.

    Raises:
        AssertionError: If a fixture fails the round-trip, or none are
            found.
    """
    checked: list[Path] = []
    for path, fixture in iter_fixtures(directory):
        assert_fixture_roundtrip(fixture, decode=decode, encode=encode)
        checked.append(path)
    assert checked, f"no fixtures found in {directory!r} — nothing was checked"
    return checked


def assert_graph_roundtrip(
    catalog: Catalog,
    fixture: Fixture,
    *,
    wire: NodeId,
    canonical_node: NodeId,
    canonical_to_dict: Callable[[Any], dict[str, Any]] = lambda v: v.to_dict(),
) -> FidelityReport:
    """Assert a registered wire node round-trips through the canonical backbone.

    Converts the fixture's `raw` payload `wire → canonical_node` via the
    catalog (asserting `semantic_equal` with the fixture's `canonical`) and
    back `canonical_node → wire` (asserting it recovers `raw`). The
    plugin's fragment must be composed into `catalog` first — which also
    means the edges exercised here passed admission, exactly as in
    production.

    Args:
        catalog: The composed catalog holding the plugin's fragment.
        fixture: A golden fixture carrying `raw` and `canonical`.
        wire: The plugin's wire node for one shape (e.g. its
            `chat.request` node).
        canonical_node: The canonical backbone node for the same shape.
        canonical_to_dict: How to render the converted canonical value as a
            dict for comparison; defaults to calling its `to_dict()`.

    Returns:
        The `FidelityReport` from the forward (`wire → canonical_node`)
        conversion, so callers can additionally assert on the chosen path
        and per-field loss.

    Raises:
        AssertionError: If either conversion does not match the fixture.
    """
    forward = catalog.convert(fixture["raw"], wire, canonical_node)
    decoded = canonical_to_dict(forward.value)
    assert semantic_equal(decoded, fixture["canonical"]), (
        f"convert({wire} -> {canonical_node}) did not match the canonical fixture.\n"
        f"  expected: {canonical(fixture['canonical'])}\n"
        f"  actual:   {canonical(decoded)}"
    )
    back = catalog.convert(forward.value, canonical_node, wire)
    assert semantic_equal(back.value, fixture["raw"]), (
        f"convert({canonical_node} -> {wire}) did not round-trip to raw.\n"
        f"  expected: {canonical(fixture['raw'])}\n"
        f"  actual:   {canonical(back.value)}"
    )
    return forward.report


def assert_fold_triple(
    fixture: Fixture,
    *,
    decode_event: Callable[[Any], list[Any]],
    fold: Callable[[list[Any]], Any],
) -> None:
    """Assert one fold-triple fixture: wire events → chunks → folded response.

    The executable form of the streaming law
    `fold(stream(request)) == complete(request)` (rule 7). A fold triple
    carries three correlated views of one streamed call:

    - `events` — the recorded wire event log (decoded SSE data payloads),
    - `chunks` — the canonical `ChatChunk` dicts those events must decode
      to,
    - `response` — the canonical response dict the chunks must fold to.

    The runner asserts both legs with `semantic_equal`: every wire event
    decodes to exactly the expected chunks (including the terminal
    `streamStop` carrying `StreamEnd`), and folding the chunks reproduces
    the response. `fold` is a parameter (typically
    `StreamAccumulator.fold`) so this harness never imports a capability
    package.

    Args:
        fixture: A fold-triple fixture carrying `events`, `chunks`, and
            `response`.
        decode_event: The codec's wire-event → canonical-chunks function
            (one event may yield zero or more chunks).
        fold: The capability's normative accumulator, folding the chunk
            sequence into a complete response object.

    Raises:
        AssertionError: If the decoded chunks or the folded response
            diverge from the fixture.
    """
    # TODO: decode fixture["events"] through decode_event in order, flatten,
    # semantic_equal each chunk's to_dict() against fixture["chunks"]; then
    # fold the decoded chunks and semantic_equal the result's to_dict()
    # against fixture["response"]; also assert PART_STOP finals equal their
    # delta accumulation (the ratchet's second clause).
    raise NotImplementedError


def check_fold_triples(
    directory: str | Path,
    *,
    decode_event: Callable[[Any], list[Any]],
    fold: Callable[[list[Any]], Any],
    pattern: str = "*.json",
) -> list[Path]:
    """Run `assert_fold_triple` over every fixture in `directory`.

    The per-streaming-edge companion of `check_codec`: every streaming edge
    ships fold triples, and this walker refuses to "pass" on an empty
    folder.

    Args:
        directory: The folder of fold-triple fixtures to check.
        decode_event: The codec's wire-event → canonical-chunks function.
        fold: The capability's normative accumulator.
        pattern: The glob selecting fixture files.

    Returns:
        The list of fixture paths that were checked.

    Raises:
        AssertionError: If a triple fails, or none are found.
    """
    checked: list[Path] = []
    for path, fixture in iter_fixtures(directory, pattern=pattern):
        assert_fold_triple(fixture, decode_event=decode_event, fold=fold)
        checked.append(path)
    assert checked, f"no fold triples found in {directory!r} — nothing was checked"
    return checked


def certify_edge(edge: Edge, payloads: Iterable[Any]) -> list[ContractViolation]:
    """Certify an edge's runtime loss against its declared contract.

    The build-time honesty gate (§4.2): runs the edge function over every
    fixture payload, collects the `FieldLoss` and `SemanticShift` records it
    actually emitted, and checks them against the declared census and
    declared shifts via `EdgeContract.certify`.
    A plugin's test suite asserts the result is empty — an edge whose
    runtime loss exceeds its declaration cannot ship, which is what makes a
    "lossless" claim in a lockfile trustworthy.

    Args:
        edge: The contracted edge under certification.
        payloads: Source-node payloads to exercise the edge with —
            typically every relevant fixture's `raw` (or `canonical`) side.

    Returns:
        Every violation found across all payloads; empty means certified.
    """
    violations: list[ContractViolation] = []
    for payload in payloads:
        out = edge.fn(payload)
        violations.extend(edge.contract.certify(out.losses, out.shifts))
    return violations


def check_unknown_inputs(
    directory: str | Path,
    *,
    decode: Callable[[dict[str, Any]], Any],
    pattern: str = "*.json",
) -> list[Path]:
    """Run the normative unknown-X fixtures: total decode, never a raise.

    The executable form of rule 6, and part of the cross-language
    conformance bar (TS/Go ports run the same fixtures). Each fixture's
    `raw` contains deliberately unknown material — unknown part/delta/detail
    tags, unknown envelope keys, unknown enum codes — and the runner asserts
    the decoder (a) never raises, (b) lands unknown tags on the registered
    Unknown fallback types, (c) sweeps unknown envelope keys into
    `extensions`, and (d) preserves everything verbatim through a
    `to_dict()` round trip (`semantic_equal`), so nothing is lost on the
    way to a future revision that names it.

    Args:
        directory: The folder of unknown-X fixtures to check.
        decode: The decoder under test (raw dict → IR object).
        pattern: The glob selecting fixture files.

    Returns:
        The list of fixture paths that were checked.

    Raises:
        AssertionError: If any decode raises, drops unknown material, or
            no fixtures are found.
    """
    # TODO: needs the fixture vocabulary for expectations ("expect" blocks
    # naming which paths must decode to Unknown types vs sweep to
    # extensions) plus the verbatim-preservation round-trip assertion.
    raise NotImplementedError
