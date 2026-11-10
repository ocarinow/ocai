"""Explicit, package-local conformance resources; no runtime schema dependency."""

from __future__ import annotations

import json
from collections.abc import Callable
from collections.abc import Iterable
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from ocai.convert.catalog import CatalogFragment


@dataclass(frozen=True, slots=True)
class ConformanceResources:
    """Locations shipped inside an independently installed plugin wheel.

    Catalogs record this manifest without reading it. Only the conformance
    harness loads files. Schema validators are supplied by the test suite.

    Attributes:
        package: Importable package owning the resources.
        fixtures: Relative directory containing JSON edge fixtures.
        extensions: Optional relative directory containing extension value schemas.
    """

    package: str
    fixtures: str = "conformance/fixtures"
    extensions: str | None = None

    def __post_init__(self) -> None:
        if not all(part.isidentifier() for part in self.package.split(".")):
            raise ValueError("conformance package must be a dotted Python package name")
        paths = (self.fixtures,) if self.extensions is None else (self.fixtures, self.extensions)
        for path in paths:
            if (
                ":" in path
                or "\\" in path
                or any(part in {"", ".", ".."} for part in path.split("/"))
            ):
                raise ValueError("conformance paths must be package-relative directories")


@dataclass(frozen=True, slots=True)
class ConformanceBundle:
    """Loaded fixtures and schemas for explicit test-suite use.

    Fixture names include distribution provenance. Extension schemas describe
    one bag value each; callers supply their validator and select canonical
    extension bags, avoiding accidental traversal into arbitrary raw JSON.
    """

    fixtures: dict[str, dict[str, Any]]
    extensions: dict[str, dict[str, Any]]

    def check_extension_bag(
        self,
        bag: dict[str, Any],
        *,
        validate: Callable[[dict[str, Any], Any], None],
    ) -> None:
        """Validate every key/value in one canonical extension bag.

        Args:
            bag: A canonical object's extension bag.
            validate: Test-suite callback accepting schema then instance;
                it must raise on invalid data.

        Raises:
            AssertionError: If a key has no registered schema.
        """
        for key, value in bag.items():
            assert key in self.extensions, f"unregistered extension key {key!r}"
            validate(self.extensions[key], value)


def _documents(directory: Traversable, prefix: str = "") -> Iterable[tuple[str, dict[str, Any]]]:
    """Read JSON objects recursively with deterministic relative names."""
    if not directory.is_dir():
        raise ValueError(f"missing conformance directory: {directory}")
    for child in sorted(directory.iterdir(), key=lambda path: path.name):
        name = prefix + child.name
        if child.is_dir():
            yield from _documents(child, name + "/")
        elif child.name.endswith(".json"):
            document = json.loads(child.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError(f"conformance resource {name} must be a JSON object")
            yield name, document


def load_conformance_resources(*fragments: CatalogFragment) -> ConformanceBundle:
    """Load explicitly declared resources from installed packages.

    No files are fetched from a network and no schema validator is imported.
    Loading resources may import the declared Python package, like ordinary
    entry-point loading; this is not a sandbox or publisher authentication.

    Args:
        fragments: Fragments whose independently packaged resources to load.

    Returns:
        The combined bundle. A fragment without a manifest contributes nothing.

    Raises:
        ValueError: If resources are missing, empty, malformed, or conflicting.
    """
    fixtures: dict[str, dict[str, Any]] = {}
    extensions: dict[str, dict[str, Any]] = {}
    for fragment in fragments:
        manifest = fragment.conformance
        if manifest is None:
            continue
        root = files(manifest.package)
        loaded = list(_documents(root.joinpath(manifest.fixtures)))
        if not loaded:
            raise ValueError(f"{fragment.origin} ships no conformance fixtures")
        for name, fixture in loaded:
            fixture_key = f"{fragment.origin}/{name}"
            if fixture_key in fixtures and fixtures[fixture_key] != fixture:
                raise ValueError(f"conflicting fixture {fixture_key}")
            fixtures[fixture_key] = fixture
        schemas = (
            _documents(root.joinpath(manifest.extensions))
            if manifest.extensions is not None
            else ()
        )
        for name, schema in schemas:
            schema_key = schema.get("title")
            if (
                not isinstance(schema_key, str)
                or "." not in schema_key
                or not all(schema_key.split("."))
            ):
                raise ValueError(f"{name}: extension title must be a namespaced key")
            if schema.get("x-ocai-origin") != fragment.origin.distribution:
                raise ValueError(f"{name}: extension origin does not match fragment")
            for field in ("description", "x-ocai-promotion"):
                if not isinstance(schema.get(field), str) or not schema[field]:
                    raise ValueError(f"{name}: missing {field}")
            if schema_key in extensions and extensions[schema_key] != schema:
                raise ValueError(f"conflicting extension schema {schema_key}")
            extensions[schema_key] = schema
    return ConformanceBundle(fixtures=fixtures, extensions=extensions)
