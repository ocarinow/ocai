"""Workspace consistency: every distribution under python/packages is wired everywhere it must be.

Adding a distribution touches lists that no tool globs for us: knope's package
table, uv's workspace sources, mypy's search path and portions, import-linter's
root packages and role-specific import contracts, plus codec convenience extras. A
package missing from any of them is silently unreleased, untyped, unchecked, or
uninstallable through `ocai[<provider>]`. This script makes the wiring a gate
step (``scripts/check.py`` and the CI ``python`` job)::

    uv run python scripts/workspace_check.py

It also checks the per-distribution invariants that no other step tests: no
``ocai/__init__.py`` at the namespace root (rule 1), ``py.typed`` in every
portion (rule 16), a bounded ``ocai`` dependency range in external packages, the
license identifier, the project URLs, and that ``python/README.md`` lists the
distribution. Every finding names the file to fix.
"""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import cast

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ROOT / "python" / "packages"
PYPROJECT = ROOT / "pyproject.toml"
KNOPE = ROOT / "knope.toml"
PYTHON_README = ROOT / "python" / "README.md"
CORE = "ocai"
LICENSE = "FSL-1.1-ALv2"
REPO_URL = "https://github.com/ocarinow/ocai"
DOCS_URL = "https://ocarinow.github.io/ocai/"
PLUGIN_CONTRACT = "Plugins never import ocai.wire, ocai.runtime, or httpx"


@dataclass(frozen=True, slots=True)
class Distribution:
    """One distribution under ``python/packages``.

    Attributes:
        name: The ``[project] name`` (also the knope package key).
        path: The distribution directory.
        project: The parsed ``[project]`` table.
        portions: Dotted namespace portions it ships, such as ``ocai.deepseek``.
        role: Validated build responsibility, independent of provider identity.
    """

    name: str
    path: Path
    project: dict[str, Any]
    portions: tuple[str, ...]
    role: str = "codec"

    @property
    def rel(self) -> str:
        """The directory relative to the repo root, with forward slashes."""
        return self.path.relative_to(ROOT).as_posix()

    @property
    def is_plugin(self) -> bool:
        """Whether this is an external distribution rather than the kernel."""
        return self.name != CORE

    @property
    def is_codec(self) -> bool:
        """Whether semantic plugin obligations apply to this distribution."""
        return self.role == "codec"

    @property
    def provider(self) -> str:
        """The provider part of a plugin name (``ocai-deepseek`` → ``deepseek``)."""
        return self.name.removeprefix(f"{CORE}-")


def _table(data: object, *keys: str) -> dict[str, Any]:
    """Walk nested TOML tables, returning ``{}`` when a key is missing.

    Args:
        data: The parsed TOML document or a table inside it.
        *keys: The table path to follow.

    Returns:
        The table at the path, or an empty dict.
    """
    node: object = data
    for key in keys:
        if not isinstance(node, dict):
            return {}
        node = cast("dict[str, object]", node).get(key)
    return cast("dict[str, Any]", node) if isinstance(node, dict) else {}


def _strings(value: object) -> list[str]:
    """Coerce a TOML array into a list of strings (non-strings dropped).

    Args:
        value: The raw TOML value.

    Returns:
        The string items, or an empty list when the value is not an array.
    """
    if not isinstance(value, list):
        return []
    return [item for item in cast("list[object]", value) if isinstance(item, str)]


def _tables(value: object) -> list[dict[str, Any]]:
    """Coerce a TOML array of tables into a list of dicts (non-tables dropped).

    Args:
        value: The raw TOML value.

    Returns:
        The table items, or an empty list when the value is not an array.
    """
    if not isinstance(value, list):
        return []
    items = cast("list[object]", value)
    return [cast("dict[str, Any]", item) for item in items if isinstance(item, dict)]


def distributions() -> list[Distribution]:
    """Discover every distribution under ``python/packages``.

    Returns:
        The distributions sorted by directory name.
    """
    found: list[Distribution] = []
    for pyproject in sorted(PACKAGES.glob("*/pyproject.toml")):
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        project = _table(data, "project")
        src = pyproject.parent / "src" / "ocai"
        portions = tuple(
            f"ocai.{child.name}"
            for child in sorted(src.iterdir())
            if child.is_dir() and (child / "__init__.py").exists()
        )
        found.append(
            Distribution(
                str(project.get("name", "")),
                pyproject.parent,
                project,
                portions,
                str(
                    _table(data, "tool", "ocai").get(
                        "role", "kernel" if project.get("name") == CORE else "codec"
                    )
                ),
            )
        )
    return found


def check_distribution(dist: Distribution) -> list[str]:
    """Per-distribution invariants (rules 1, 16, 15 and the plugin range).

    Args:
        dist: The distribution to check.

    Returns:
        One finding per violated invariant.
    """
    problems: list[str] = []
    if dist.role not in {"kernel", "codec", "credential", "host"} or (
        (dist.name == CORE) != (dist.role == "kernel")
    ):
        problems.append(f"{dist.rel}/pyproject.toml: invalid tool.ocai.role {dist.role!r}")
    if (dist.path / "src" / "ocai" / "__init__.py").exists():
        problems.append(f"{dist.rel}/src/ocai/__init__.py exists: PEP 420 namespace root (rule 1)")
    if not dist.portions:
        problems.append(f"{dist.rel}: no namespace portion under src/ocai/")
    for portion in dist.portions:
        marker = dist.path / "src" / Path(*portion.split(".")) / "py.typed"
        if not marker.exists():
            problems.append(f"{marker.relative_to(ROOT).as_posix()} missing (rule 16)")
    problems.extend(
        f"{dist.rel}/{required} missing"
        for required in ("README.md", "CHANGELOG.md")
        if not (dist.path / required).exists()
    )
    if dist.project.get("license") != LICENSE:
        problems.append(f"{dist.rel}/pyproject.toml: license must be {LICENSE!r} (rule 15)")
    urls = _table(dist.project, "urls")
    expected_urls = {
        "Homepage": REPO_URL,
        "Source": REPO_URL,
        "Documentation": DOCS_URL,
        "Changelog": f"{REPO_URL}/blob/main/{dist.rel}/CHANGELOG.md",
    }
    for key, want in expected_urls.items():
        if urls.get(key) != want:
            problems.append(f"{dist.rel}/pyproject.toml: [project.urls] {key} must be {want}")
    if dist.is_plugin:
        deps = _strings(dist.project.get("dependencies"))
        core_dep = next(
            (d for d in deps if d == CORE or d.startswith(f"{CORE}>") or d.startswith(f"{CORE}<")),
            None,
        )
        if core_dep is None or "<" not in core_dep:
            problems.append(
                f"{dist.rel}/pyproject.toml: plugin must pin a bounded core range "
                "such as 'ocai>=0.1,<0.2'"
            )
        if dist.is_codec and not _table(dist.project, "entry-points", "ocai.fragments"):
            problems.append(
                f'{dist.rel}/pyproject.toml: no [project.entry-points."ocai.fragments"]'
            )
    return problems


def check_wiring(dists: list[Distribution]) -> list[str]:
    """Cross-file wiring: knope, uv sources, mypy, import-linter, core extras, README.

    Args:
        dists: Every discovered distribution.

    Returns:
        One finding per missing wire.
    """
    problems: list[str] = []
    root = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    knope = tomllib.loads(KNOPE.read_text(encoding="utf-8"))
    readme = PYTHON_README.read_text(encoding="utf-8")
    core = next((d for d in dists if not d.is_plugin), None)
    extras = _table(core.project, "optional-dependencies") if core else {}
    all_extra = " ".join(_strings(extras.get("all")))

    sources = _table(root, "tool", "uv", "sources")
    mypy_path = _strings(_table(root, "tool", "mypy").get("mypy_path"))
    mypy_packages = _strings(_table(root, "tool", "mypy").get("packages"))
    linter = _table(root, "tool", "importlinter")
    linter_roots = _strings(linter.get("root_packages"))
    plugin_sources: list[str] = []
    for contract in _tables(linter.get("contracts")):
        if contract.get("name") == PLUGIN_CONTRACT:
            plugin_sources = _strings(contract.get("source_modules"))

    for dist in dists:
        spec = _table(knope, "packages", dist.name)
        if f"{dist.rel}/pyproject.toml" not in _strings(spec.get("versioned_files")):
            problems.append(
                f"knope.toml: [packages.{dist.name}] missing or not versioning "
                f"{dist.rel}/pyproject.toml"
            )
        if spec.get("changelog") != f"{dist.rel}/CHANGELOG.md":
            problems.append(
                f"knope.toml: [packages.{dist.name}] changelog must be {dist.rel}/CHANGELOG.md"
            )
        if _table(sources, dist.name).get("workspace") is not True:
            problems.append(
                f"pyproject.toml: [tool.uv.sources] {dist.name} = {{ workspace = true }} missing"
            )
        if f"{dist.rel}/src" not in mypy_path:
            problems.append(f"pyproject.toml: [tool.mypy] mypy_path lacks {dist.rel}/src")
        for portion in dist.portions:
            if portion not in mypy_packages:
                problems.append(f"pyproject.toml: [tool.mypy] packages lacks {portion}")
            if portion not in linter_roots:
                problems.append(
                    f"pyproject.toml: [tool.importlinter] root_packages lacks {portion}"
                )
            if dist.is_codec and portion not in plugin_sources:
                problems.append(
                    f"pyproject.toml: contract {PLUGIN_CONTRACT!r} source_modules lacks {portion}"
                )
        if dist.role in {"credential", "host"}:
            required = {"httpx", "ocai.wire.transport"}
            if dist.role == "credential":
                required.update({"ocai.chat", "ocai.convert", "ocai.runtime"})
            boundaries = [
                contract
                for contract in _tables(linter.get("contracts"))
                if contract.get("type") == "forbidden" and contract.get("name")
            ]
            problems.extend(
                f"pyproject.toml: {dist.role} boundary missing for {portion}; "
                f"must forbid {sorted(required)}"
                for portion in dist.portions
                if not any(
                    portion in _strings(contract.get("source_modules"))
                    and required <= set(_strings(contract.get("forbidden_modules")))
                    for contract in boundaries
                )
            )
        if dist.is_codec:
            if _strings(extras.get(dist.provider)) != [dist.name]:
                problems.append(
                    f"python/packages/ocai-core/pyproject.toml: extra {dist.provider} = "
                    f'["{dist.name}"] missing'
                )
            if dist.provider not in all_extra:
                problems.append(
                    "python/packages/ocai-core/pyproject.toml: extra `all` does not include "
                    f"{dist.provider}"
                )
        if f"| `{dist.name}` |" not in readme:
            problems.append(f"python/README.md: distributions table has no row for `{dist.name}`")
    return problems


def main() -> int:
    """Entry point.

    Returns:
        0 when every distribution is fully wired, 1 otherwise.
    """
    dists = distributions()
    problems: list[str] = []
    for dist in dists:
        problems.extend(check_distribution(dist))
    problems.extend(check_wiring(dists))
    if problems:
        print(f"WORKSPACE: {len(problems)} finding(s) across {len(dists)} distribution(s)")
        for problem in problems:
            print("  - " + problem)
        return 1
    names = ", ".join(d.name for d in dists)
    print(f"workspace: ok ({len(dists)} distributions: {names})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
