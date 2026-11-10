"""External fixture bundles fail on missing evidence and undeclared losses."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from ocai.convert import CatalogFragment
from ocai.convert import ConformanceResources
from ocai.convert import Edge
from ocai.convert import EdgeContract
from ocai.convert import EdgeOutput
from ocai.convert.conformance import check_edge
from ocai.convert.conformance import check_fragment
from ocai.convert.resources import load_conformance_resources
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import FieldLoss
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import NodeId
from ocai.core.identity import Origin
from ocai.core.identity import canonical_node

ORIGIN = Origin("ocai-external-test", "1")
SOURCE = NodeId("external", "chat", "v1", CHAT_REQUEST, date(2026, 1, 1))
TARGET = canonical_node(CHAT_REQUEST)


def identity(payload: Any) -> EdgeOutput:
    return EdgeOutput(payload)


EDGE = Edge(SOURCE, TARGET, identity, EdgeContract(), ORIGIN)
FRAGMENT = CatalogFragment(
    ORIGIN,
    nodes=(SOURCE,),
    edges=(EDGE,),
    conformance=ConformanceResources("external_resources", extensions="conformance/extensions"),
)


def coordinate(node: NodeId) -> dict[str, str]:
    return {
        "provider": node.provider,
        "interface": node.interface,
        "tag": node.tag,
        "shape": str(node.shape),
    }


def fixture() -> dict[str, Any]:
    return {
        "src": coordinate(SOURCE),
        "dst": coordinate(TARGET),
        "input": {"x": 1},
        "expect": {"x": 1},
        "expect_losses": [],
        "expect_shifts": [],
    }


@pytest.fixture
def packaged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for directory in ("fixtures", "extensions"):
        (tmp_path / "conformance" / directory).mkdir(parents=True)
    (tmp_path / "conformance/fixtures/roundtrip.json").write_text(json.dumps(fixture()))
    schema = {
        "title": "external.example",
        "description": "A synthetic extension.",
        "x-ocai-origin": ORIGIN.distribution,
        "x-ocai-promotion": "none expected",
        "type": "integer",
    }
    (tmp_path / "conformance/extensions/example.schema.json").write_text(json.dumps(schema))

    def package_files(package: str) -> Path:
        return tmp_path

    monkeypatch.setattr("ocai.convert.resources.files", package_files)
    return tmp_path


def test_external_bundle_loads_without_a_repository_census(packaged: Path) -> None:
    bundle = load_conformance_resources(FRAGMENT)
    assert check_fragment(FRAGMENT, bundle.fixtures.values()) == 1
    assert bundle.extensions["external.example"]["type"] == "integer"


def test_identical_resource_declarations_are_idempotent(packaged: Path) -> None:
    bundle = load_conformance_resources(FRAGMENT, FRAGMENT)
    assert len(bundle.fixtures) == len(bundle.extensions) == 1


def test_plugins_without_extensions_need_no_schema_directory(packaged: Path) -> None:
    only_fixtures = replace(FRAGMENT, conformance=ConformanceResources("external_resources"))
    bundle = load_conformance_resources(only_fixtures)
    assert bundle.extensions == {}
    assert check_fragment(only_fixtures, bundle.fixtures.values()) == 1


def test_identical_edge_registration_does_not_require_duplicate_fixtures() -> None:
    assert check_fragment(replace(FRAGMENT, edges=(EDGE, EDGE)), [fixture()]) == 1


@pytest.mark.parametrize("path", ["/etc", "../fixtures", "fixtures/../other", "a\\b", ""])
def test_manifest_rejects_paths_outside_its_package(path: str) -> None:
    with pytest.raises(ValueError, match="package-relative"):
        ConformanceResources("external_resources", fixtures=path)


def test_missing_resource_directory_fails(packaged: Path) -> None:
    assert FRAGMENT.conformance is not None
    manifest = replace(FRAGMENT.conformance, fixtures="missing")
    with pytest.raises(ValueError, match="missing conformance"):
        load_conformance_resources(replace(FRAGMENT, conformance=manifest))


def test_empty_fixture_directory_fails(packaged: Path) -> None:
    (packaged / "conformance/fixtures/roundtrip.json").unlink()
    with pytest.raises(ValueError, match="no conformance fixtures"):
        load_conformance_resources(FRAGMENT)


@pytest.mark.parametrize(
    "change",
    [
        {"title": "bare"},
        {"x-ocai-origin": "another-distribution"},
        {"description": ""},
        {"x-ocai-promotion": None},
    ],
)
def test_extension_metadata_must_match_its_declaring_distribution(
    packaged: Path, change: dict[str, Any]
) -> None:
    path = packaged / "conformance/extensions/example.schema.json"
    schema = json.loads(path.read_text()) | change
    path.write_text(json.dumps(schema))
    with pytest.raises(ValueError):
        load_conformance_resources(FRAGMENT)


def test_conflicting_extension_schemas_fail(packaged: Path) -> None:
    path = packaged / "conformance/extensions/example.schema.json"
    other = json.loads(path.read_text()) | {"type": "string"}
    path.with_name("conflict.schema.json").write_text(json.dumps(other))
    with pytest.raises(ValueError, match="conflicting extension schema"):
        load_conformance_resources(FRAGMENT)


def test_nonobject_resource_is_rejected(packaged: Path) -> None:
    (packaged / "conformance/fixtures/roundtrip.json").write_text("[]")
    with pytest.raises(ValueError, match="JSON object"):
        load_conformance_resources(FRAGMENT)


def test_extension_validation_requires_registration_and_calls_supplied_validator(
    packaged: Path,
) -> None:
    bundle = load_conformance_resources(FRAGMENT)

    def validate(schema: dict[str, Any], value: Any) -> None:
        assert schema["type"] == "integer"
        assert type(value) is int

    bundle.check_extension_bag({"external.example": 3}, validate=validate)
    with pytest.raises(AssertionError):
        bundle.check_extension_bag({"external.example": "3"}, validate=validate)
    with pytest.raises(AssertionError, match="unregistered"):
        bundle.check_extension_bag({"unknown.key": 3}, validate=validate)


def test_fragment_requires_coverage_for_every_payload_edge() -> None:
    with pytest.raises(AssertionError, match="without fixtures"):
        check_fragment(FRAGMENT, [])
    wrong = fixture()
    wrong["src"]["tag"] = "wrong"
    with pytest.raises(AssertionError, match="exactly one"):
        check_fragment(FRAGMENT, [wrong])


def test_check_edge_rejects_mislabeled_fixture_endpoints() -> None:
    wrong = fixture()
    wrong["dst"]["interface"] = "wrong"
    with pytest.raises(AssertionError, match="dst does not match"):
        check_edge(EDGE, wrong)


def test_fragment_rejects_faulty_conversion_even_when_no_loss_is_emitted() -> None:
    def faulty_conversion(payload: Any) -> EdgeOutput:
        return EdgeOutput({})

    faulty = replace(EDGE, fn=faulty_conversion)
    with pytest.raises(AssertionError, match="did not match"):
        check_fragment(replace(FRAGMENT, edges=(faulty,)), [fixture()])


def test_expected_output_does_not_excuse_exceeding_the_declared_census() -> None:
    def lossy(payload: Any) -> EdgeOutput:
        return EdgeOutput({}, losses=(FieldLoss("x", Disposition.DROPPED),))

    faulty = replace(EDGE, fn=lossy)
    expected: dict[str, Any] = fixture() | {
        "expect": {},
        "expect_losses": [{"path": "x", "disposition": "dropped"}],
    }
    with pytest.raises(AssertionError, match="exceeds its declared contract"):
        check_fragment(replace(FRAGMENT, edges=(faulty,)), [expected])


def test_expected_loss_cannot_be_silently_omitted() -> None:
    expected = fixture()
    expected["expect_losses"] = [{"path": "x", "disposition": "dropped"}]
    with pytest.raises(AssertionError, match="FieldLoss records"):
        check_fragment(FRAGMENT, [expected])
