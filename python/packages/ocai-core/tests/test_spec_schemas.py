"""The spec validator harness: every fixture validates against its schema.

Implements the fixture-to-schema mapping convention documented in
`spec/README.md` ("How fixtures map to schemas"). In short:

- The canonical schema for shape token `x.y` is `spec/schema/x_y.schema.json`
  (dots become underscores), identified by
  `https://ocai.dev/spec/schema/x_y.schema.json`.
- A **canonical document fixture** (`shape` + `document`) validates its
  `document` against the schema for `shape`.
- An **edge fixture** (`src`/`dst`/`input`/`expect`) validates each side
  whose coordinate names the canonical interface (`provider == "ocai"`).
- A **fold triple** (`node`/`wire_events`/`chunks`/`response`) validates
  `chunks` against `<capability>.chunk` and `response` against
  `<capability>.response`.

The harness fails loudly on a fixture matching no recognized kind and on a
payload mapping to a schema that does not exist — a fixture that cannot be
validated is a spec bug, never a skip.

`jsonschema` (and its `referencing` companion) is a **dev-only** dependency:
nothing under `ocai.*` may import it (rule 11 — the canonical IR stays
zero-third-party-dep stdlib dataclasses).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry
from referencing import Resource

# The base every schema `$id` starts with (see spec/schema/README.md).
SCHEMA_ID_BASE = "https://ocai.dev/spec/schema/"

# The canonical interface's provider label; only payloads on this side of an
# edge fixture are validated against spec/schema/.
CANONICAL_PROVIDER = "ocai"


def _find_repo_root(start: Path) -> Path:
    """Walk upward from `start` to the directory containing `spec/fixtures/`."""
    for parent in [start, *start.parents]:
        if (parent / "spec" / "fixtures").is_dir():
            return parent
    raise RuntimeError("could not locate repo root (no spec/fixtures/ found)")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
SCHEMA_DIR = REPO_ROOT / "spec" / "schema"
FIXTURES_DIR = REPO_ROOT / "spec" / "fixtures"

SCHEMA_PATHS = sorted(SCHEMA_DIR.glob("*.schema.json"))
FIXTURE_PATHS = sorted(FIXTURES_DIR.rglob("*.json"))


def _load_json(path: Path) -> dict[str, Any]:
    """Read `path` and require a JSON object at the top level."""
    data = json.loads(path.read_text())
    assert isinstance(data, dict), f"{path} must contain a JSON object at the top level"
    return data


def _schemas_by_id() -> dict[str, dict[str, Any]]:
    """Load every schema in `spec/schema/`, keyed by its `$id`."""
    out: dict[str, dict[str, Any]] = {}
    for path in SCHEMA_PATHS:
        schema = _load_json(path)
        out[schema["$id"]] = schema
    return out


SCHEMAS_BY_ID = _schemas_by_id()

# One registry holding every spec schema, so relative cross-file $refs
# (e.g. "parts.schema.json#/$defs/envelope") resolve against the $id base.
REGISTRY: Registry = Registry().with_resources(
    (uri, Resource.from_contents(schema)) for uri, schema in SCHEMAS_BY_ID.items()
)


def _schema_id_for_shape(shape: str) -> str:
    """Map a shape token to its schema `$id` (dots become underscores)."""
    return f"{SCHEMA_ID_BASE}{shape.replace('.', '_')}.schema.json"


def _errors_for_shape(shape: str, payload: Any) -> list[ValidationError]:
    """Validate `payload` against the schema for `shape`, returning all errors.

    Fails the running test when no schema exists for `shape` — a payload the
    harness cannot validate is a spec bug, never a skip.
    """
    schema_id = _schema_id_for_shape(shape)
    schema = SCHEMAS_BY_ID.get(schema_id)
    if schema is None:
        pytest.fail(
            f"no schema for shape {shape!r}: expected {schema_id} "
            f"(file {schema_id.removeprefix(SCHEMA_ID_BASE)} in spec/schema/)"
        )
    validator = Draft202012Validator(schema, registry=REGISTRY)
    return list(validator.iter_errors(payload))


def _assert_valid(shape: str, payload: Any, label: str) -> None:
    """Assert `payload` validates against the schema for `shape`."""
    errors = _errors_for_shape(shape, payload)
    detail = "\n".join(f"  - {e.json_path}: {e.message}" for e in errors)
    assert not errors, f"{label} does not validate against the {shape!r} schema:\n{detail}"


def _validatable_payloads(fixture: dict[str, Any], path: Path) -> list[tuple[str, Any, str]]:
    """Extract every `(shape, payload, label)` triple a fixture must validate.

    Dispatches on the fixture's structural kind per the convention in
    `spec/README.md`; fails the running test for a document matching none of
    the three kinds.
    """
    if "shape" in fixture and "document" in fixture:
        return [(fixture["shape"], fixture["document"], "document")]
    if {"src", "dst", "input", "expect"} <= fixture.keys():
        triples: list[tuple[str, Any, str]] = []
        for coordinate_key, payload_key in (("src", "input"), ("dst", "expect")):
            coordinate = fixture[coordinate_key]
            if coordinate.get("provider") == CANONICAL_PROVIDER:
                triples.append((coordinate["shape"], fixture[payload_key], payload_key))
        return triples
    if {"node", "wire_events", "chunks", "response"} <= fixture.keys():
        capability = str(fixture["node"]["shape"]).split(".", 1)[0]
        triples = [
            (f"{capability}.chunk", chunk, f"chunks[{index}]")
            for index, chunk in enumerate(fixture["chunks"])
        ]
        triples.append((f"{capability}.response", fixture["response"], "response"))
        return triples
    pytest.fail(
        f"{path} matches no recognized fixture kind (canonical document, edge "
        f"fixture, or fold triple) — see 'How fixtures map to schemas' in spec/README.md"
    )


# ---------------------------------------------------------------------------
# The schemas themselves are well-formed.
# ---------------------------------------------------------------------------


def test_schema_dir_is_not_empty() -> None:
    """An empty schema set silently passing would defeat the drift alarm."""
    assert SCHEMA_PATHS, f"no *.schema.json found in {SCHEMA_DIR}"


@pytest.mark.parametrize("schema_path", SCHEMA_PATHS, ids=lambda p: p.name)
def test_schema_is_valid_draft_2020_12(schema_path: Path) -> None:
    """Every spec schema is itself a valid Draft 2020-12 schema."""
    schema = _load_json(schema_path)
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("schema_path", SCHEMA_PATHS, ids=lambda p: p.name)
def test_schema_declares_id_and_role_comment(schema_path: Path) -> None:
    """Every spec schema carries the conventional `$id` and a role `$comment`."""
    schema = _load_json(schema_path)
    assert schema.get("$id") == f"{SCHEMA_ID_BASE}{schema_path.name}", (
        f"{schema_path.name} must declare $id {SCHEMA_ID_BASE}{schema_path.name!r}"
    )
    assert schema.get("$comment"), f"{schema_path.name} must carry a top-level $comment"


# ---------------------------------------------------------------------------
# Every fixture validates against its declared schema.
# ---------------------------------------------------------------------------


def test_fixtures_dir_is_not_empty() -> None:
    """An empty fixture set silently passing would defeat the drift alarm."""
    assert FIXTURE_PATHS, f"no fixtures found under {FIXTURES_DIR}"


@pytest.mark.parametrize(
    "fixture_path", FIXTURE_PATHS, ids=lambda p: str(p.relative_to(FIXTURES_DIR))
)
def test_fixture_validates_against_its_schema(fixture_path: Path) -> None:
    """Each canonical payload in the fixture validates against its schema."""
    fixture = _load_json(fixture_path)
    for shape, payload, label in _validatable_payloads(fixture, fixture_path):
        _assert_valid(shape, payload, f"{fixture_path.name}: {label}")


def test_canonical_chat_request_fixture_exercises_parts_tools_config() -> None:
    """The replacement fixture actually covers what WU-02 says it covers."""
    fixture = _load_json(FIXTURES_DIR / "canonical" / "chat_request.json")
    document = fixture["document"]
    part_types = {
        part["type"] for message in document["messages"] for part in message["parts"]
    }
    assert {"text", "image", "reasoning", "tool_call", "tool_result"} <= part_types
    assert document["tools"], "fixture must exercise tools"
    assert document["tool_choice"], "fixture must exercise tool_choice"
    assert document["config"]["reasoning"], "fixture must exercise reasoning config"
    assert document["config"]["output"]["mode"] == "json_schema"


# ---------------------------------------------------------------------------
# The validator bites: open vocabularies admit unknowns, wrong types fail.
# ---------------------------------------------------------------------------


def _errors_for_shape_raw(schema_stem: str, payload: Any) -> list[ValidationError]:
    """Validate against a schema by file stem (for schemas that are not shapes)."""
    schema = SCHEMAS_BY_ID[f"{SCHEMA_ID_BASE}{schema_stem}.schema.json"]
    return list(Draft202012Validator(schema, registry=REGISTRY).iter_errors(payload))


def test_unknown_part_tag_validates() -> None:
    """A future/unknown part tag is legal — it decodes to `PartUnknown`."""
    part = {"version": "2026-07", "type": "holographic_message", "frames": [1, 2, 3]}
    assert not _errors_for_shape_raw("parts", part)


def test_known_part_tag_with_wrong_payload_type_fails() -> None:
    """A known tag with a mistyped payload is rejected — the branch applies."""
    assert _errors_for_shape_raw("parts", {"type": "text", "text": 42})
    assert _errors_for_shape_raw("parts", {"type": "tool_call", "args_json": {"a": 1}})
    assert _errors_for_shape_raw("parts", {"type": "tool_result", "parts": "not-a-list"})


def test_unknown_source_tag_validates_and_known_bites() -> None:
    """The `Source` union is open like the part union."""
    image = {"type": "image", "source": {"type": "torrent", "magnet": "..."}}
    assert not _errors_for_shape_raw("parts", image)
    bad = {"type": "image", "source": {"type": "url", "url": 42}}
    assert _errors_for_shape_raw("parts", bad)


def test_unknown_role_and_open_codes_validate() -> None:
    """Enum-like fields are open string codes, never closed enums."""
    message = {"role": "narrator", "parts": [{"type": "text", "text": "hi"}]}
    assert not _errors_for_shape_raw("message", message)
    request = {
        "model": "m",
        "messages": [],
        "tool_choice": {"mode": "provider_specific_mode"},
        "config": {"reasoning": {"effort": "xtreme"}, "output": {"mode": "yaml"}},
    }
    assert not _errors_for_shape_raw("chat_request", request)


def test_message_requires_role_and_parts() -> None:
    """`role` and `parts` are always emitted, so the schema may require them."""
    assert _errors_for_shape_raw("message", {"parts": []})
    assert _errors_for_shape_raw("message", {"role": "user"})
    assert _errors_for_shape_raw("message", {"role": 42, "parts": []})
    assert not _errors_for_shape_raw("message", {"role": "user", "parts": []})


def test_chat_request_requires_model_and_messages() -> None:
    """`model` and `messages` are always emitted, so the schema may require them."""
    assert _errors_for_shape_raw("chat_request", {"messages": []})
    assert _errors_for_shape_raw("chat_request", {"model": "m"})
    assert not _errors_for_shape_raw("chat_request", {"model": "m", "messages": []})


def test_edge_fixture_convention_maps_canonical_sides_only() -> None:
    """Only the `ocai`-provider sides of an edge fixture are validated."""
    fixture = {
        "description": "synthetic mapping check",
        "src": {"provider": "openai", "interface": "chat_completions", "shape": "chat.request"},
        "dst": {"provider": "ocai", "interface": "ocai", "shape": "chat.request"},
        "input": {"not": "validated"},
        "expect": {"model": "m", "messages": []},
        "expect_losses": [],
    }
    triples = _validatable_payloads(fixture, Path("synthetic.json"))
    assert [(shape, label) for shape, _, label in triples] == [("chat.request", "expect")]
