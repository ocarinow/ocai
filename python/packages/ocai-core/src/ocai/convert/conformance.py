"""The conformance harness: the moat, shipped as a product (§4.5).

Plugins validate their conversion logic against the **same** contracts
ocai's first-party fragments use — this module is what makes rule 9
("every edge ships an EdgeContract + golden fixtures") executable rather
than prose. It is pure stdlib (no pytest, no third-party deps), so it runs
under any test runner (or none) and raises plain `AssertionError` on
mismatch. Every equality assertion is `ocai.core.canonjson.semantic_equal`
— the one normative predicate — never `==` on raw dicts.

Five kinds of check, mirroring the promises an edge makes:

- **Edge fixtures** (`check_edge`): the per-edge golden contract of
  `spec/README.md` — running the edge on the fixture's `input` yields a
  value `semantic_equal` to `expect`, and the runtime
  `FieldLoss`/`SemanticShift` records match `expect_losses`/`expect_shifts`
  exactly.
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
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ocai.convert.catalog import Catalog
from ocai.convert.catalog import CatalogFragment
from ocai.convert.contract import ContractViolation
from ocai.convert.graph import Edge
from ocai.convert.graph import EdgeOutput
from ocai.core.canonjson import canonical
from ocai.core.canonjson import semantic_equal
from ocai.core.fidelity import FidelityReport
from ocai.core.identity import NodeId
from ocai.core.ir import is_json_object

# A golden fixture: one of the JSON shapes documented in `spec/README.md` —
# edge fixtures carry `{description, src, dst, input, expect, expect_losses,
# expect_shifts}`; legacy conversion fixtures carry `{raw, canonical}`; fold
# triples carry `{node, chunks, response}` plus an optional `wire_events`
# (absent on canonical-node triples, whose chunks are already canonical and
# need no decode leg).
type Fixture = dict[str, Any]


def _matches(node: NodeId, coordinate: dict[str, Any]) -> bool:
    """Match fixture coordinates, including optional release metadata."""
    return (
        (node.provider, node.interface, node.tag, str(node.shape))
        == tuple(coordinate.get(key) for key in ("provider", "interface", "tag", "shape"))
        and coordinate.get("released", node.released.isoformat()) == node.released.isoformat()
        and coordinate.get("status", node.status.value) == node.status.value
    )


def check_fragment(
    fragment: CatalogFragment,
    fixtures: Iterable[Fixture],
    *,
    decode_inputs: Mapping[NodeId, Callable[[dict[str, Any]], Any]] | None = None,
    bind_outputs: Mapping[NodeId, Callable[[Any], Any]] | None = None,
) -> int:
    """Check every payload edge against independently authored fixtures.

    Args:
        fragment: The fragment to admit and check. Streaming edges still
            require their dedicated fold triples.
        fixtures: Edge fixtures, such as a loaded resource bundle's values.
        decode_inputs: Optional typed decoders keyed by source node.
        bind_outputs: Optional post-conversion finishers keyed by destination.

    Returns:
        The number of checked fixtures.

    Raises:
        AssertionError: If a fixture names no unique edge, an edge has no
            fixture, expected output/records differ, or a declaration is exceeded.
    """
    Catalog.of(fragment)
    covered: set[tuple[NodeId, NodeId]] = set()
    count = 0
    for fixture in fixtures:
        matches = [
            edge
            for edge in fragment.edges
            if _matches(edge.src, fixture.get("src", {}))
            and _matches(edge.dst, fixture.get("dst", {}))
        ]
        # Catalog admission already rejects competing definitions; identical
        # duplicate registrations describe the same directed edge.
        assert matches, "fixture must identify exactly one fragment edge"
        edge = matches[0]
        out = check_edge(
            edge,
            fixture,
            decode_input=(decode_inputs or {}).get(edge.src),
            bind=(bind_outputs or {}).get(edge.dst),
        )
        violations = edge.contract.certify(out.losses, out.shifts)
        assert not violations, f"edge exceeds its declared contract: {violations}"
        covered.add((edge.src, edge.dst))
        count += 1
    missing = {(edge.src, edge.dst) for edge in fragment.edges} - covered
    assert not missing, f"fragment edges without fixtures: {missing}"
    return count


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
    fixture: Fixture = json.loads(Path(path).read_text())
    return fixture


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


def _expected_loss_keys(entries: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Extract the comparable `(path, disposition)` keys from `expect_losses`.

    Args:
        entries: The fixture's `expect_losses` entries.

    Returns:
        The sorted comparison keys.
    """
    return sorted((str(entry["path"]), str(entry["disposition"])) for entry in entries)


def _expected_shift_keys(entries: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Extract the comparable `(kind, path)` keys from `expect_shifts`.

    Args:
        entries: The fixture's `expect_shifts` entries.

    Returns:
        The sorted comparison keys.
    """
    return sorted((str(entry["kind"]), str(entry.get("path", ""))) for entry in entries)


def check_edge(
    edge: Edge,
    fixture: Fixture,
    *,
    decode_input: Callable[[dict[str, Any]], Any] | None = None,
    bind: Callable[[Any], Any] | None = None,
) -> EdgeOutput:
    """Assert one edge fixture: output equality plus exact loss/shift match.

    The executable form of the edge-fixture contract in `spec/README.md`
    (clauses 1 and 2; clause 3 — runtime loss never exceeding the declared
    census — is `certify_edge`'s job, fed with the same fixture payloads):

    1. Running `edge.fn` on the fixture's `input` yields a value
       `semantic_equal` to `expect`.
    2. The runtime `FieldLoss` records match `expect_losses` and the runtime
       `SemanticShift` records match `expect_shifts` **exactly** — same
       multiset, nothing extra, nothing missing. Records compare on
       `(path, disposition)` / `(kind, path)`; notes and severities are
       prose/diagnostics and are never compared (mirroring
       `EdgeContract.certify`). `expect_losses` must be present even when
       empty — the honest part of a fixture is never absent by accident;
       `expect_shifts` defaults to empty.

    The harness stays capability-neutral: fixtures store payloads as plain
    JSON, so a canonical-source fixture supplies `decode_input` (typically a
    `from_dict`) to lift `input` into the IR object the edge function takes,
    and an output exposing `to_dict` is rendered through it for comparison.

    Args:
        edge: The contracted edge under test; the fixture's `src`/`dst`
            coordinates must name its endpoints (the caller selects the
            edge; this helper does not resolve catalogs).
        fixture: An edge fixture carrying `input`, `expect`, and
            `expect_losses` (plus optional `expect_shifts`).
        decode_input: Lifts the fixture's `input` payload into the edge's
            source representation; None when the input is already the raw
            payload the edge function takes (wire-source fixtures).
        bind: A post-edge finisher applied to the output value before
            comparison — the facade seam below the graph (e.g. injecting the
            bound model via a codec's `bind_resource`); None for edges whose
            output is already the complete `expect` payload.

    Returns:
        The `EdgeOutput` of the run, so callers can feed the same payload
        set to `certify_edge` or inspect the records further.

    Raises:
        AssertionError: If the output diverges from `expect`, the records
            diverge from the expectations, or `expect_losses` is missing.
    """
    assert _matches(edge.src, fixture.get("src", {})), "fixture src does not match edge"
    assert _matches(edge.dst, fixture.get("dst", {})), "fixture dst does not match edge"
    payload: Any = fixture["input"]
    if decode_input is not None:
        payload = decode_input(payload)
    out = edge.fn(payload)
    value = bind(out.value) if bind is not None else out.value
    rendered = value.to_dict() if hasattr(value, "to_dict") else value
    assert semantic_equal(rendered, fixture["expect"]), (
        "running the edge on `input` did not match the fixture's `expect`.\n"
        f"  expected: {canonical(fixture['expect'])}\n"
        f"  actual:   {canonical(rendered)}"
    )
    assert "expect_losses" in fixture, (
        "edge fixture carries no `expect_losses` — the block may be empty, "
        "never absent-by-accident (spec/README.md)"
    )
    actual_losses = sorted((loss.path, loss.disposition.value) for loss in out.losses)
    expected_losses = _expected_loss_keys(fixture["expect_losses"])
    assert actual_losses == expected_losses, (
        "runtime FieldLoss records do not match expect_losses exactly.\n"
        f"  expected: {expected_losses}\n"
        f"  actual:   {actual_losses}"
    )
    actual_shifts = sorted((shift.kind, shift.path) for shift in out.shifts)
    expected_shifts = _expected_shift_keys(fixture.get("expect_shifts") or [])
    assert actual_shifts == expected_shifts, (
        "runtime SemanticShift records do not match expect_shifts exactly.\n"
        f"  expected: {expected_shifts}\n"
        f"  actual:   {actual_shifts}"
    )
    return out


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


def _strip_authoritative_finals(chunks: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    """Strip the authoritative final part from every delta-fed `partStop`.

    The mechanical half of the ratchet's second clause: for each part slot
    that received at least one `partDelta`, the `partStop`'s final part is
    removed, so re-folding the stripped stream yields the *pure delta
    accumulation* for that slot. A `partStop` whose slot saw no deltas
    keeps its part — with nothing accumulated, the clause is vacuous and
    the final is simply the part's only carrier.

    The chunk vocabulary read here (`type`, `index`, `part`, and the
    `partStart`/`partDelta`/`partStop` codes) is the spec's canonical
    chunk-stream contract (`spec/schema/chat_chunk.schema.json`), not a
    capability import; index resolution mirrors the normative accumulator
    (explicit `index`, else the most recently started slot, else 0).

    Args:
        chunks: The fixture's canonical chunk dicts, in stream order.

    Returns:
        The stripped chunk list, or None when no chunk was stripped (the
        clause has nothing to check).
    """
    order: list[int] = []
    seen: set[int] = set()
    fed: set[int] = set()
    stripped: list[dict[str, Any]] = []
    stripped_any = False
    for chunk in chunks:
        chunk_type = chunk.get("type")
        explicit = chunk.get("index")
        if chunk_type == "partStart":
            index = explicit if isinstance(explicit, int) else len(order)
            if index not in seen:
                seen.add(index)
                order.append(index)
        elif chunk_type == "partDelta":
            index = explicit if isinstance(explicit, int) else (order[-1] if order else 0)
            if index not in seen:
                seen.add(index)
                order.append(index)
            fed.add(index)
        elif chunk_type == "partStop" and "part" in chunk:
            index = explicit if isinstance(explicit, int) else (order[-1] if order else 0)
            if index in fed:
                chunk = {key: value for key, value in chunk.items() if key != "part"}
                stripped_any = True
        stripped.append(chunk)
    return stripped if stripped_any else None


def assert_fold_triple(
    fixture: Fixture,
    *,
    decode_event: Callable[[Any], list[dict[str, Any]]] | None = None,
    fold: Callable[[list[dict[str, Any]]], dict[str, Any]],
) -> None:
    """Assert one fold-triple fixture: wire events → chunks → folded response.

    The executable form of the streaming law
    `fold(stream(request)) == complete(request)` (rule 7). A fold triple
    carries correlated views of one streamed call:

    - `wire_events` — the recorded wire event log, *optional*: absent on
      canonical-node triples whose chunks are already canonical,
    - `chunks` — the canonical `ChatChunk` dicts those events must decode
      to,
    - `response` — the canonical response dict the chunks must fold to.

    Three clauses, all under `semantic_equal`:

    1. **Decode leg** (only when `wire_events` is present): the events
       decode, in order, to exactly the expected chunks.
    2. **Fold leg** (mandatory): folding the chunks reproduces the
       response.
    3. **The ratchet's second clause**: each `partStop`'s authoritative
       final part MUST equal its delta accumulation — checked by stripping
       the finals from every delta-fed `partStop`
       (`_strip_authoritative_finals`) and asserting the re-fold still
       reproduces the response.

    `decode_event` and `fold` are parameters (typically wrapping the
    codec's `decode_event` and `StreamAccumulator.fold`) so this harness
    never imports a capability package; both speak plain dicts.

    Args:
        fixture: A fold-triple fixture carrying `chunks`, `response`, and
            optionally `wire_events`.
        decode_event: The codec's wire-event → canonical-chunk-dicts
            function (one event may yield zero or more chunks); required
            exactly when the fixture carries `wire_events`.
        fold: The capability's normative accumulator, folding a canonical
            chunk-dict sequence into the complete response dict.

    Raises:
        AssertionError: If any clause diverges from the fixture, or the
            fixture carries `wire_events` but no `decode_event` was
            supplied.
    """
    expected_chunks: list[dict[str, Any]] = fixture["chunks"]
    wire_events = fixture.get("wire_events")
    if wire_events is not None:
        assert decode_event is not None, (
            "fixture carries wire_events but no decode_event was supplied — "
            "the decode leg cannot be verified"
        )
        decoded: list[dict[str, Any]] = []
        for event in wire_events:
            decoded.extend(decode_event(event))
        assert len(decoded) == len(expected_chunks), (
            "decode_event(wire_events) yielded a different number of chunks "
            f"than the fixture expects: {len(decoded)} != {len(expected_chunks)}"
        )
        pairs = zip(decoded, expected_chunks, strict=True)
        for position, (actual, expected) in enumerate(pairs):
            assert semantic_equal(actual, expected), (
                f"decoded chunk [{position}] did not match the fixture.\n"
                f"  expected: {canonical(expected)}\n"
                f"  actual:   {canonical(actual)}"
            )
    folded = fold(list(expected_chunks))
    assert semantic_equal(folded, fixture["response"]), (
        "fold(chunks) did not reproduce the fixture's response (the fold law).\n"
        f"  expected: {canonical(fixture['response'])}\n"
        f"  actual:   {canonical(folded)}"
    )
    stripped = _strip_authoritative_finals(expected_chunks)
    if stripped is not None:
        refolded = fold(stripped)
        assert semantic_equal(refolded, fixture["response"]), (
            "a partStop's authoritative final part does not equal its delta "
            "accumulation (the ratchet's second clause): re-folding with the "
            "finals stripped diverged from the response.\n"
            f"  expected: {canonical(fixture['response'])}\n"
            f"  actual:   {canonical(refolded)}"
        )


def check_fold_triples(
    directory: str | Path,
    *,
    decode_event: Callable[[Any], list[dict[str, Any]]] | None = None,
    fold: Callable[[list[dict[str, Any]]], dict[str, Any]],
    pattern: str = "*.json",
) -> list[Path]:
    """Run `assert_fold_triple` over every fixture in `directory`.

    The per-streaming-edge companion of `check_codec`: every streaming edge
    ships fold triples, and this walker refuses to "pass" on an empty
    folder.

    Args:
        directory: The folder of fold-triple fixtures to check.
        decode_event: The codec's wire-event → canonical-chunk-dicts
            function; required for fixtures carrying `wire_events`.
        fold: The capability's normative accumulator, folding a canonical
            chunk-dict sequence into the complete response dict.
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


def _split_path(path: str) -> list[str | int]:
    """Parse the unknown-vector path grammar into name and index segments.

    The grammar (`spec/README.md`, "Normative unknown-X fixtures"):
    dot-separated member names with zero-based `[i]` indexing
    (`messages[0].parts[1]`); the empty string names the root.

    Args:
        path: The fixture path expression.

    Returns:
        The segments in order — member names as strings, indices as ints.
    """
    segments: list[str | int] = []
    for token in path.split("."):
        if not token:
            continue
        name, bracket, rest = token.partition("[")
        if name:
            segments.append(name)
        while bracket:
            index_text, _, rest = rest.partition("]")
            segments.append(int(index_text))
            _, bracket, rest = rest.partition("[")
    return segments


def _walk(root: Any, segments: list[str | int]) -> Any:
    """Resolve path `segments` against a document dict or a decoded object.

    Integer segments index into sequences; string segments read mapping keys
    on dicts and attributes on anything else — so one walker serves both the
    fixture `document` and the decoded IR object graph.

    Args:
        root: The value to walk from.
        segments: The parsed path segments.

    Returns:
        The value at the path.

    Raises:
        AssertionError: If a segment cannot be resolved — the value is
            missing material the fixture addresses.
    """
    resolved: Any = root
    for segment in segments:
        try:
            if isinstance(segment, int):
                resolved = resolved[segment]
            elif is_json_object(resolved):
                resolved = resolved[segment]
            else:
                resolved = getattr(resolved, segment)
        except (KeyError, IndexError, AttributeError, TypeError) as exc:
            raise AssertionError(
                f"path segment {segment!r} cannot be resolved on {type(resolved).__name__}: {exc}"
            ) from exc
    return resolved


def _apply_sweeps(document: dict[str, Any], sweeps: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a copy of `document` with each declared extensions sweep applied.

    Builds the round-trip expectation for an unknown vector: every swept key
    is removed from its owner object and re-homed under the owner's
    `extensions` bag, exactly as the tolerant reader does.

    Args:
        document: The vector's canonical document.
        sweeps: The vector's `expect.extensions` entries
            (`{"owner": <path>, "key": <member>}`).

    Returns:
        The expected re-encoded document.

    Raises:
        AssertionError: If a sweep's owner is not an object or its key is
            not present in the document — a malformed vector.
    """
    expected: dict[str, Any] = json.loads(json.dumps(document))
    for sweep in sweeps:
        owner = _walk(expected, _split_path(sweep["owner"]))
        key = sweep["key"]
        assert is_json_object(owner) and key in owner, (
            f"malformed vector: sweep key {key!r} is not a member of the "
            f"document object at {sweep['owner']!r}"
        )
        owner.setdefault("extensions", {})[key] = owner.pop(key)
    return expected


def assert_unknown_vector(fixture: Fixture, *, decode: Callable[[dict[str, Any]], Any]) -> None:
    """Assert one unknown-X vector: total decode, fallback typing, no loss.

    The executable form of rule 6 for a single vector (the fixture shape and
    `expect` vocabulary are normative in `spec/README.md`, "Normative
    unknown-X fixtures"). Four assertions:

    1. **Total decode** — `decode(document)` never raises, whatever unknown
       material the document carries.
    2. **Fallback typing** — every `expect.fallbacks` path decodes to the
       canonical fallback type it names. Types are compared by *name*
       (`PartUnknown`, `DeltaUnknown`, `DetailOpaque`, `SourceUnknown`) so
       this module never imports a capability package and the vocabulary
       stays language-neutral.
    3. **Sweeps and preservation** — every `expect.extensions` key lands
       verbatim in its owner's `extensions` bag (and only there), and every
       `expect.preserved` path re-encodes `semantic_equal` to the document's
       value.
    4. **Round trip** — `to_dict()` of the decoded value is `semantic_equal`
       to the document with the declared sweeps applied; verbatim when none
       are declared.

    Args:
        fixture: An unknown vector carrying `document` and `expect`.
        decode: The decoder under test (canonical document dict → IR object
            exposing `to_dict`).

    Raises:
        AssertionError: If decoding raises, a fallback lands on the wrong
            type, a sweep or preservation expectation fails, or the round
            trip loses material.
    """
    document = fixture["document"]
    expect: dict[str, Any] = fixture.get("expect") or {}
    try:
        decoded = decode(document)
    except Exception as exc:  # total decode: NOTHING may escape the decoder.
        raise AssertionError(
            f"total decode violated: decode raised {type(exc).__name__}: {exc}"
        ) from exc
    fallbacks: list[dict[str, Any]] = expect.get("fallbacks") or []
    for entry in fallbacks:
        target = _walk(decoded, _split_path(entry["path"]))
        assert type(target).__name__ == entry["type"], (
            f"expected {entry['path'] or '<root>'} to decode to the "
            f"{entry['type']} fallback, got {type(target).__name__}"
        )
    reencoded = decoded.to_dict()
    sweeps: list[dict[str, Any]] = expect.get("extensions") or []
    for entry in sweeps:
        owner_segments = _split_path(entry["owner"])
        key = entry["key"]
        document_owner = _walk(document, owner_segments)
        reencoded_owner = _walk(reencoded, owner_segments)
        bag: dict[str, Any] = reencoded_owner.get("extensions") or {}
        assert key in bag and semantic_equal(bag[key], document_owner[key]), (
            f"expected key {key!r} at {entry['owner'] or '<root>'} to sweep "
            f"verbatim into its owner's extensions bag; bag holds {sorted(bag)}"
        )
        assert key not in reencoded_owner, (
            f"swept key {key!r} must not also survive as a member of its owner"
        )
    preserved: list[dict[str, Any]] = expect.get("preserved") or []
    for entry in preserved:
        segments = _split_path(entry["path"])
        expected_value = _walk(document, segments)
        actual_value = _walk(reencoded, segments)
        assert semantic_equal(actual_value, expected_value), (
            f"expected {entry['path']!r} to re-encode verbatim.\n"
            f"  expected: {canonical(expected_value)}\n"
            f"  actual:   {canonical(actual_value)}"
        )
    expected_document = _apply_sweeps(document, sweeps)
    assert semantic_equal(reencoded, expected_document), (
        "re-encoding the decoded value lost or reshaped material.\n"
        f"  expected: {canonical(expected_document)}\n"
        f"  actual:   {canonical(reencoded)}"
    )


def check_unknown_inputs(
    directory: str | Path,
    *,
    decode: Callable[[dict[str, Any]], Any],
    pattern: str = "*.json",
) -> list[Path]:
    """Run the normative unknown-X vectors: total decode, never a raise.

    The executable form of rule 6, and part of the cross-language
    conformance bar (TS/Go ports run the same fixtures). Each vector's
    `document` contains deliberately unknown material — unknown part/delta/
    detail tags, unknown envelope keys, unknown open codes — and the runner
    asserts, per `assert_unknown_vector`: the decoder (a) never raises,
    (b) lands unknown tags on the registered Unknown fallback types,
    (c) sweeps unknown envelope keys into `extensions`, and (d) preserves
    everything verbatim through a `to_dict()` round trip (`semantic_equal`),
    so nothing is lost on the way to a future revision that names it. The
    vector shape and `expect` vocabulary are documented in `spec/README.md`
    ("Normative unknown-X fixtures").

    Args:
        directory: The folder of unknown-X vectors to check.
        decode: The decoder under test (canonical document dict → IR
            object); use `pattern` to select the vectors this decoder
            handles (e.g. `"message_*.json"`).
        pattern: The glob selecting vector files.

    Returns:
        The list of vector paths that were checked.

    Raises:
        AssertionError: If any vector fails, or none are found.
    """
    checked: list[Path] = []
    for path, fixture in iter_fixtures(directory, pattern=pattern):
        try:
            assert_unknown_vector(fixture, decode=decode)
        except AssertionError as exc:
            raise AssertionError(f"{path}: {exc}") from exc
        checked.append(path)
    assert checked, f"no unknown-X vectors found in {directory!r} — nothing was checked"
    return checked
