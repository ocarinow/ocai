"""The rule-11 conformance test: dataclass fields ↔ schema properties.

`spec/schema/` is the neutral source of truth and the Python dataclasses are
**conformance-tested against it**, never generated from it (rule 11). This
module is that test, in four parts:

1. **Exhaustive field/property comparison** — for every schema'd IR dataclass
   (Message, every part variant, ChatRequest and its config family,
   ChatResponse/ResponseInfo, FinishInfo and its detail variants,
   Usage/Consumption, plus the shared building blocks), the dataclass field
   set must EQUAL the schema property set. A dataclass field without a schema
   property fails (an unschema'd field is a spec bug); a schema property
   without a dataclass field fails (a phantom property is a spec lie).
2. **Verbatim-fallback checks** — `PartUnknown`/`SourceUnknown`/`DetailOpaque`
   are byte-faithful passthroughs, not property-mapped shapes: their fields
   (`data`, `type`) never appear on the wire as such, so they are asserted to
   round-trip payloads untouched instead.
3. **Omit-absent compliance** — minimal objects emit only schema-known keys
   and drop every unset optional/empty bag (`spec/canonical-json.md` §6).
4. **Additive-only guard** — a snapshot of every schema's property set as of
   this revision; removing (or renaming) a property fails, adding one passes.

Schema traversal here is structural (walking `properties`/`allOf`/`$ref`
by hand) — `jsonschema` is not needed and stays confined to the fixture
validation harness (`test_spec_schemas.py`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from dataclasses import fields
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import pytest

from ocai.chat.types.annotations import Annotation
from ocai.chat.types.annotations import Span
from ocai.chat.types.config import AudioOutputConfig
from ocai.chat.types.config import CacheConfig
from ocai.chat.types.config import CacheHint
from ocai.chat.types.config import ChatConfig
from ocai.chat.types.config import OutputFormat
from ocai.chat.types.config import ReasoningConfig
from ocai.chat.types.finish import DetailOpaque
from ocai.chat.types.finish import ErrorDetail
from ocai.chat.types.finish import FinishInfo
from ocai.chat.types.finish import IncompleteDetail
from ocai.chat.types.finish import RefusalDetail
from ocai.chat.types.finish import SafetyDetail
from ocai.chat.types.finish import SafetyRating
from ocai.chat.types.message import Message
from ocai.chat.types.parts import PartAudio
from ocai.chat.types.parts import PartDocument
from ocai.chat.types.parts import PartImage
from ocai.chat.types.parts import PartOpaque
from ocai.chat.types.parts import PartReasoning
from ocai.chat.types.parts import PartRefusal
from ocai.chat.types.parts import PartServerToolCall
from ocai.chat.types.parts import PartServerToolResult
from ocai.chat.types.parts import PartText
from ocai.chat.types.parts import PartToolCall
from ocai.chat.types.parts import PartToolResult
from ocai.chat.types.parts import PartUnknown
from ocai.chat.types.parts import PartVideo
from ocai.chat.types.request import ChatRequest
from ocai.chat.types.response import ChatResponse
from ocai.chat.types.response import ResponseInfo
from ocai.chat.types.tools import Tool
from ocai.chat.types.tools import ToolChoice
from ocai.chat.types.usage import Consumption
from ocai.chat.types.usage import Usage
from ocai.core.refs import ProviderRef
from ocai.core.sources import SourceBase64
from ocai.core.sources import SourceRef
from ocai.core.sources import SourceUnknown
from ocai.core.sources import SourceUrl

# The base every schema `$id` starts with (see spec/schema/README.md).
SCHEMA_ID_BASE = "https://ocai.dev/spec/schema/"


def _find_repo_root(start: Path) -> Path:
    """Walk upward from `start` to the directory containing `spec/schema/`."""
    for parent in [start, *start.parents]:
        if (parent / "spec" / "schema").is_dir():
            return parent
    raise RuntimeError("could not locate repo root (no spec/schema/ found)")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
SCHEMA_DIR = REPO_ROOT / "spec" / "schema"
FIXTURES_DIR = REPO_ROOT / "spec" / "fixtures"

SCHEMAS_BY_ID: dict[str, dict[str, Any]] = {}
for _path in sorted(SCHEMA_DIR.glob("*.schema.json")):
    _schema = json.loads(_path.read_text())
    SCHEMAS_BY_ID[_schema["$id"]] = _schema


def _resolve(ref: str, base_id: str) -> tuple[Any, str]:
    """Resolve a `$ref` against `base_id` into `(schema node, its base id)`.

    Handles the three forms the spec schemas use: same-document pointers
    (`#/$defs/x`), cross-file document refs (`message.schema.json`), and
    cross-file pointers (`parts.schema.json#/$defs/envelope`).
    """
    doc, _, pointer = ref.partition("#")
    doc_id = urljoin(base_id, doc) if doc else base_id
    node: Any = SCHEMAS_BY_ID[doc_id]
    for token in pointer.split("/"):
        if token:
            node = node[token]
    return node, doc_id


def _property_names(node: Any, base_id: str, *, conditionals: bool = False) -> frozenset[str]:
    """Union the property names a schema node declares, following refs.

    Walks `properties`, every `allOf` member, and `$ref` targets. `if`/`then`
    variant branches are skipped unless `conditionals` is set (the per-variant
    comparisons select their branch explicitly; the additive-only snapshot
    takes the full union).
    """
    if not isinstance(node, dict):
        return frozenset()
    out = set(node.get("properties") or {})
    if "$ref" in node:
        target, target_base = _resolve(node["$ref"], base_id)
        out |= _property_names(target, target_base, conditionals=conditionals)
    for member in node.get("allOf") or []:
        out |= _property_names(member, base_id, conditionals=conditionals)
    if conditionals:
        for key in ("then", "else"):
            if key in node:
                out |= _property_names(node[key], base_id, conditionals=True)
    return frozenset(out)


def _schema_props(ref: str, *, conditionals: bool = False) -> frozenset[str]:
    """Return the effective property-name set of the schema node at `ref`."""
    node, base_id = _resolve(ref, SCHEMA_ID_BASE)
    return _property_names(node, base_id, conditionals=conditionals)


def _variant_props(union_ref: str, tag: str) -> frozenset[str]:
    """Return the effective property set of one tagged-union variant.

    The union's shared properties (discriminator + base + envelope) unioned
    with the `then` branch whose `if` matches `tag`. Fails the running test
    when the union declares no branch for `tag`.
    """
    node, base_id = _resolve(union_ref, SCHEMA_ID_BASE)
    shared = _property_names(node, base_id)
    for member in node.get("allOf") or []:
        condition = member.get("if", {}).get("properties", {}).get("type", {})
        if condition.get("const") == tag:
            return shared | _property_names(member["then"], base_id)
    pytest.fail(f"{union_ref} declares no variant branch for tag {tag!r}")


def _field_names(cls: type) -> frozenset[str]:
    """Return the dataclass field names of `cls` (ClassVars excluded)."""
    return frozenset(f.name for f in fields(cls))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1. Exhaustive dataclass-field ↔ schema-property comparison (rule 11).
# ---------------------------------------------------------------------------

# Every schema'd IR dataclass with a plain (non-tagged-union) schema node.
FIELD_CASES: list[tuple[type, str]] = [
    (Message, "message.schema.json"),
    (ChatRequest, "chat_request.schema.json"),
    (Tool, "chat_request.schema.json#/$defs/tool"),
    (ToolChoice, "chat_request.schema.json#/$defs/toolChoice"),
    (ChatConfig, "chat_request.schema.json#/$defs/chatConfig"),
    (ReasoningConfig, "chat_request.schema.json#/$defs/reasoningConfig"),
    (OutputFormat, "chat_request.schema.json#/$defs/outputFormat"),
    (AudioOutputConfig, "chat_request.schema.json#/$defs/audioOutputConfig"),
    (CacheConfig, "chat_request.schema.json#/$defs/cacheConfig"),
    (ChatResponse, "chat_response.schema.json"),
    (ResponseInfo, "chat_response.schema.json#/$defs/responseInfo"),
    (FinishInfo, "finish.schema.json"),
    (SafetyRating, "finish.schema.json#/$defs/safetyRating"),
    (Usage, "usage.schema.json"),
    (Consumption, "usage.schema.json#/$defs/consumption"),
    (ProviderRef, "parts.schema.json#/$defs/providerRef"),
    (CacheHint, "parts.schema.json#/$defs/cacheHint"),
    (Annotation, "parts.schema.json#/$defs/annotation"),
    (Span, "parts.schema.json#/$defs/span"),
]

# Part variants: dataclass ↔ the parts.schema.json branch selected by tag.
PART_CASES: list[tuple[type, str]] = [
    (PartText, "text"),
    (PartImage, "image"),
    (PartAudio, "audio"),
    (PartVideo, "video"),
    (PartDocument, "document"),
    (PartReasoning, "reasoning"),
    (PartToolCall, "tool_call"),
    (PartToolResult, "tool_result"),
    (PartServerToolCall, "server_tool_call"),
    (PartServerToolResult, "server_tool_result"),
    (PartRefusal, "refusal"),
    (PartOpaque, "opaque"),
]

# Finish-detail variants: dataclass ↔ the finishDetail branch by tag.
DETAIL_CASES: list[tuple[type, str]] = [
    (SafetyDetail, "safety"),
    (RefusalDetail, "refusal"),
    (IncompleteDetail, "incomplete"),
    (ErrorDetail, "error"),
]

# Source variants: dataclass ↔ the source branch by tag.
SOURCE_CASES: list[tuple[type, str]] = [
    (SourceBase64, "base64"),
    (SourceUrl, "url"),
    (SourceRef, "ref"),
]


def _assert_fields_equal_props(cls: type, props: frozenset[str], where: str) -> None:
    """Assert the field set of `cls` equals the schema property set."""
    declared = _field_names(cls)
    unschemad = declared - props
    phantom = props - declared
    assert declared == props, (
        f"{cls.__name__} drifted from {where}: "
        f"dataclass fields without a schema property: {sorted(unschemad)}; "
        f"schema properties without a dataclass field: {sorted(phantom)}"
    )


@pytest.mark.parametrize(("cls", "ref"), FIELD_CASES, ids=lambda v: getattr(v, "__name__", v))
def test_dataclass_fields_match_schema_properties(cls: type, ref: str) -> None:
    """Rule 11: every field is schema'd and every property is implemented."""
    _assert_fields_equal_props(cls, _schema_props(ref), ref)


@pytest.mark.parametrize(("cls", "tag"), PART_CASES, ids=lambda v: getattr(v, "__name__", v))
def test_part_variant_fields_match_schema_branch(cls: type, tag: str) -> None:
    """Each part dataclass matches its parts.schema.json variant branch."""
    _assert_fields_equal_props(cls, _variant_props("parts.schema.json", tag), f"parts:{tag}")


@pytest.mark.parametrize(("cls", "tag"), DETAIL_CASES, ids=lambda v: getattr(v, "__name__", v))
def test_finish_detail_variant_fields_match_schema_branch(cls: type, tag: str) -> None:
    """Each finish-detail dataclass matches its finishDetail variant branch."""
    props = _variant_props("finish.schema.json#/$defs/finishDetail", tag)
    _assert_fields_equal_props(cls, props, f"finishDetail:{tag}")


@pytest.mark.parametrize(("cls", "tag"), SOURCE_CASES, ids=lambda v: getattr(v, "__name__", v))
def test_source_variant_fields_match_schema_branch(cls: type, tag: str) -> None:
    """Each source dataclass matches its source variant branch."""
    props = _variant_props("parts.schema.json#/$defs/source", tag)
    _assert_fields_equal_props(cls, props, f"source:{tag}")


def test_comparison_bites_on_unschemad_field() -> None:
    """The guard demonstrably fails when a field lacks a schema property."""

    @dataclass
    class MessageWithNewField(Message):
        shiny_new_field: str | None = None

    declared = _field_names(MessageWithNewField)
    props = _schema_props("message.schema.json")
    assert declared != props
    assert "shiny_new_field" in declared - props


# ---------------------------------------------------------------------------
# 2. Verbatim fallbacks are byte-faithful, not property-mapped.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cls", [PartUnknown, SourceUnknown, DetailOpaque], ids=lambda c: c.__name__
)
def test_verbatim_fallback_round_trips_untouched(cls: type) -> None:
    """Unknown-tag fallbacks preserve payloads verbatim through to_dict.

    Their `data`/`type` fields are internal carriers, never wire members, so
    they are exempt from the field/property comparison by design: the schema
    validates the *payload* (any object with an unknown tag), and the class
    must reproduce it byte-for-byte.
    """
    payload = {
        "type": "holographic_message",
        "frames": [1, 2, 3],
        "extensions": {"future.lane": True},
    }
    decoded = cls.from_dict(payload)  # type: ignore[attr-defined]
    assert decoded.to_dict() == payload


# ---------------------------------------------------------------------------
# 3. Omit-absent compliance: minimal objects emit only schema-known keys.
# ---------------------------------------------------------------------------


def _minimal_objects() -> list[tuple[Any, frozenset[str]]]:
    """Minimal instances paired with the schema property set that bounds them."""
    return [
        (Message(role="user", parts=[]), _schema_props("message.schema.json")),
        (ChatRequest(messages=[]), _schema_props("chat_request.schema.json")),
        (
            ChatResponse(message=Message(role="model", parts=[])),
            _schema_props("chat_response.schema.json"),
        ),
        (ResponseInfo(), _schema_props("chat_response.schema.json#/$defs/responseInfo")),
        (FinishInfo(), _schema_props("finish.schema.json")),
        (Usage(), _schema_props("usage.schema.json")),
        (PartText(), _variant_props("parts.schema.json", "text")),
        (PartImage(), _variant_props("parts.schema.json", "image")),
        (PartAudio(), _variant_props("parts.schema.json", "audio")),
        (PartVideo(), _variant_props("parts.schema.json", "video")),
        (PartDocument(), _variant_props("parts.schema.json", "document")),
        (PartReasoning(), _variant_props("parts.schema.json", "reasoning")),
        (PartToolCall(), _variant_props("parts.schema.json", "tool_call")),
        (PartToolResult(), _variant_props("parts.schema.json", "tool_result")),
        (PartServerToolCall(), _variant_props("parts.schema.json", "server_tool_call")),
        (PartServerToolResult(), _variant_props("parts.schema.json", "server_tool_result")),
        (PartRefusal(), _variant_props("parts.schema.json", "refusal")),
        (PartOpaque(), _variant_props("parts.schema.json", "opaque")),
    ]


@pytest.mark.parametrize(
    ("obj", "props"),
    _minimal_objects(),
    ids=lambda v: "" if isinstance(v, frozenset) else type(v).__name__,
)
def test_minimal_to_dict_emits_only_schema_known_keys(obj: Any, props: frozenset[str]) -> None:
    """An omit-absent encoder never emits a key the schema does not know."""
    emitted = set(obj.to_dict())
    assert emitted <= props, (
        f"{type(obj).__name__} emitted unschema'd keys: {sorted(emitted - props)}"
    )


def test_minimal_chat_response_omits_absent_members() -> None:
    """Unset optionals and empty bags are dropped, required members stay."""
    minimal = ChatResponse(message=Message(role="model", parts=[]))
    emitted = minimal.to_dict()
    assert set(emitted) == {"version", "message"}
    assert set(emitted["message"]) == {"version", "role", "parts"}
    assert emitted["message"]["parts"] == []


def test_minimal_finish_and_usage_omit_absent_members() -> None:
    """FinishInfo always emits its reason; Usage with no consumptions is bare."""
    assert set(FinishInfo().to_dict()) == {"version", "reason"}
    assert FinishInfo().to_dict()["reason"] == "unknown"
    assert set(Usage().to_dict()) == {"version"}
    assert set(ResponseInfo().to_dict()) == {"version"}


def test_canonical_chat_response_fixture_round_trips_byte_identically() -> None:
    """The fixture document is exactly what the omit-absent encoder emits.

    `from_dict` is a true inverse of `to_dict`, so decoding the canonical
    fixture and re-encoding it must reproduce the document byte-for-byte —
    the strongest wire-accuracy check a hand-authored fixture can carry.
    """
    fixture = json.loads((FIXTURES_DIR / "canonical" / "chat_response.json").read_text())
    document = fixture["document"]
    assert ChatResponse.from_dict(document).to_dict() == document


def test_canonical_chat_request_fixture_round_trips_byte_identically() -> None:
    """Same wire-accuracy law for the WU-02 request fixture."""
    fixture = json.loads((FIXTURES_DIR / "canonical" / "chat_request.json").read_text())
    document = fixture["document"]
    assert ChatRequest.from_dict(document).to_dict() == document


# ---------------------------------------------------------------------------
# 4. Additive-only guard: property removals fail loudly.
# ---------------------------------------------------------------------------

ENVELOPE = frozenset({"version", "provider_options", "extensions"})

# Snapshot of every schema's full property union (variant branches included)
# as of IR revision 2026-07 / WU-03. Additive-only: growing a set is fine and
# does NOT require touching this snapshot; removing or renaming a property
# breaks it — which is the point.
PROPERTY_SNAPSHOT: dict[str, frozenset[str]] = {
    "message.schema.json": ENVELOPE | {"role", "parts"},
    "parts.schema.json": ENVELOPE
    | {
        "type",
        "id",
        "anchor",
        "cache_hint",
        "text",
        "annotations",
        "source",
        "start_offset",
        "end_offset",
        "fps",
        "title",
        "context",
        "summary",
        "signature",
        "opaque",
        "call_id",
        "name",
        "args_json",
        "status",
        "executed_by",
        "parts",
        "is_error",
        "kind",
        "payload",
    },
    "parts.schema.json#/$defs/envelope": ENVELOPE,
    "parts.schema.json#/$defs/providerRef": frozenset(
        {"provider", "interface", "kind", "id", "replay"}
    ),
    "parts.schema.json#/$defs/cacheHint": ENVELOPE | {"ttl"},
    "parts.schema.json#/$defs/span": frozenset({"start", "end"}),
    "parts.schema.json#/$defs/annotation": ENVELOPE
    | {"span", "url", "document_index", "file", "title", "cited_text", "opaque"},
    # Pre-freeze course-correction (2026-07, capability stress-test): the
    # sourceRef branch's `media_type` was renamed `mime_type` to match its
    # base64/url siblings before v0.2 froze the surface; `from_dict` still
    # accepts the old key. The additive-only regime governs from the
    # corrected shape onward.
    "parts.schema.json#/$defs/source": ENVELOPE | {"type", "data", "mime_type", "url", "ref"},
    # WU-05a (pre-freeze course-correction, 2026-07): `model` left the request
    # — routing data binds to the model object (§3.4), never the IR. The
    # additive-only regime governs from the corrected shape onward.
    "chat_request.schema.json": ENVELOPE | {"messages", "tools", "tool_choice", "config"},
    "chat_request.schema.json#/$defs/tool": ENVELOPE
    | {"name", "parameters", "description", "output"},
    "chat_request.schema.json#/$defs/toolChoice": ENVELOPE | {"mode", "name"},
    "chat_request.schema.json#/$defs/chatConfig": ENVELOPE
    | {
        "temperature",
        "top_p",
        "max_output_tokens",
        "stop_sequences",
        "seed",
        "frequency_penalty",
        "presence_penalty",
        "parallel_tool_calls",
        "top_k",
        "logprobs",
        "modalities",
        "audio",
        "reasoning",
        "output",
        "cache",
    },
    "chat_request.schema.json#/$defs/reasoningConfig": ENVELOPE
    | {"effort", "budget_tokens", "include_thoughts"},
    "chat_request.schema.json#/$defs/outputFormat": ENVELOPE
    | {"mode", "name", "schema", "strict"},
    "chat_request.schema.json#/$defs/audioOutputConfig": ENVELOPE | {"voice", "format"},
    "chat_request.schema.json#/$defs/cacheConfig": ENVELOPE | {"mode", "ref"},
    "chat_response.schema.json": ENVELOPE | {"message", "finish", "usage", "info", "raw"},
    "chat_response.schema.json#/$defs/responseInfo": ENVELOPE | {"id", "model", "created"},
    "finish.schema.json": ENVELOPE | {"reason", "native", "detail"},
    "finish.schema.json#/$defs/finishDetail": ENVELOPE
    | {"type", "ratings", "block_source", "category", "explanation", "note", "code", "message"},
    "finish.schema.json#/$defs/safetyRating": frozenset({"category", "level", "blocked"}),
    "usage.schema.json": ENVELOPE | {"consumptions"},
    "usage.schema.json#/$defs/consumption": frozenset({"value", "modality", "unit", "source"}),
}


@pytest.mark.parametrize(
    ("ref", "snapshot"),
    sorted(PROPERTY_SNAPSHOT.items()),
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_schema_properties_are_never_removed(ref: str, snapshot: frozenset[str]) -> None:
    """Additive-only: every snapshotted property must still exist."""
    current = _schema_props(ref, conditionals=True)
    removed = snapshot - current
    assert not removed, (
        f"{ref} lost properties {sorted(removed)} — the spec is additive-only: "
        f"members are never renamed, removed, or repurposed (spec/README.md)"
    )


def test_snapshot_covers_the_chat_unary_schema_files() -> None:
    """The chat unary contract schemas are all under the additive-only guard.

    Scoped to the files this snapshot governs — schema files newer WUs add
    (e.g. streaming deltas) join the snapshot in the WU that authors them.
    """
    snapshotted_files = {ref.partition("#")[0] for ref in PROPERTY_SNAPSHOT}
    governed = {
        "message.schema.json",
        "parts.schema.json",
        "chat_request.schema.json",
        "chat_response.schema.json",
        "finish.schema.json",
        "usage.schema.json",
    }
    missing = governed - snapshotted_files
    assert not missing, f"schema files missing from PROPERTY_SNAPSHOT: {sorted(missing)}"


def test_every_snapshotted_ref_still_resolves() -> None:
    """A vanished snapshot node is an additive-only violation, failing loudly.

    A snapshotted schema node that vanishes (file rename, $defs removal) must
    fail the test, not KeyError.
    """
    for ref in PROPERTY_SNAPSHOT:
        try:
            _resolve(ref, SCHEMA_ID_BASE)
        except KeyError:
            pytest.fail(
                f"snapshotted schema node {ref!r} no longer resolves — "
                f"the spec is additive-only: files and $defs are never renamed or removed"
            )
