"""Offline workspace CLI fixtures distinguish codecs from auth and service hosts."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[4] / "scripts/workspace_check.py"


def _run(
    root: Path,
    *,
    role: str | None,
    fragment: bool = False,
    extras: bool = False,
    boundary: bool = True,
    typed: bool = True,
) -> subprocess.CompletedProcess[str]:
    (root / "scripts").mkdir()
    shutil.copyfile(SCRIPT, root / "scripts/workspace_check.py")
    for name, portion in (("ocai", "core"), ("ocai-example", "example")):
        directory = "ocai-core" if name == "ocai" else name
        dist = root / "python/packages" / directory
        package = dist / "src/ocai" / portion
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("")
        if typed or name == "ocai":
            (package / "py.typed").write_text("")
        (dist / "README.md").write_text("Synthetic packaging fixture.")
        (dist / "CHANGELOG.md").write_text("Synthetic changelog.")
        body = f'''[project]
name = "{name}"
license = "FSL-1.1-ALv2"
dependencies = ['ocai>=0.1,<0.2']
[project.urls]
Homepage = "https://github.com/ocarinow/ocai"
Source = "https://github.com/ocarinow/ocai"
Documentation = "https://ocarinow.github.io/ocai/"
Changelog = "https://github.com/ocarinow/ocai/blob/main/python/packages/{directory}/CHANGELOG.md"
'''
        if name != "ocai":
            if role is not None:
                body += "\n[tool.ocai]\nrole = " + json.dumps(role) + "\n"
            if fragment:
                body += (
                    '\n[project.entry-points."ocai.fragments"]\nexample = "ocai.example:FRAGMENT"\n'
                )
        elif extras:
            body += (
                '\n[project.optional-dependencies]\nexample = ["ocai-example"]\n'
                'all = ["ocai[example]"]\n'
            )
        (dist / "pyproject.toml").write_text(body)
    (root / "python/README.md").write_text("| `ocai` |\n| `ocai-example` |\n")
    (root / "knope.toml").write_text("""[packages.ocai]
versioned_files = ["python/packages/ocai-core/pyproject.toml"]
changelog = "python/packages/ocai-core/CHANGELOG.md"
[packages.ocai-example]
versioned_files = ["python/packages/ocai-example/pyproject.toml"]
changelog = "python/packages/ocai-example/CHANGELOG.md"
""")
    config = """[tool.uv.sources]
ocai = {workspace = true}
ocai-example = {workspace = true}
[tool.mypy]
mypy_path = ["python/packages/ocai-core/src", "python/packages/ocai-example/src"]
packages = ["ocai.core", "ocai.example"]
[tool.importlinter]
root_packages = ["ocai.core", "ocai.example"]
[[tool.importlinter.contracts]]
name = "Plugins never import ocai.wire, ocai.runtime, or httpx"
source_modules = ["ocai.example"]
"""
    if boundary:
        config += """[[tool.importlinter.contracts]]
name = "Explicit pure adapter boundary"
type = "forbidden"
source_modules = ["ocai.example"]
forbidden_modules = ["httpx", "ocai.wire.transport", "ocai.chat", "ocai.convert", "ocai.runtime"]
"""
    (root / "pyproject.toml").write_text(config)
    return subprocess.run(
        [sys.executable, str(root / "scripts/workspace_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("role", [None, "codec"])
def test_codecs_keep_fragment_and_extra_requirements(tmp_path: Path, role: str | None) -> None:
    failed = _run(tmp_path, role=role)
    assert failed.returncode == 1
    assert "ocai.fragments" in failed.stdout and "extra example" in failed.stdout


@pytest.mark.parametrize("role", [None, "codec", "credential", "host"])
def test_valid_roles_keep_shared_packaging_checks(tmp_path: Path, role: str | None) -> None:
    codec = role in (None, "codec")
    result = _run(tmp_path, role=role, fragment=codec, extras=codec)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("role", ["credential", "host"])
def test_adapters_require_explicit_import_boundary(tmp_path: Path, role: str) -> None:
    result = _run(tmp_path, role=role, boundary=False)
    assert result.returncode == 1 and "boundary missing" in result.stdout
    assert "ocai.fragments" not in result.stdout and "extra example" not in result.stdout


@pytest.mark.parametrize("role", ["credential", "host"])
def test_adapters_still_require_typing_marker(tmp_path: Path, role: str) -> None:
    result = _run(tmp_path, role=role, typed=False)
    assert result.returncode == 1 and "py.typed missing" in result.stdout


@pytest.mark.parametrize("role", ["credetial", "satellite", "kernel"])
def test_unknown_or_misplaced_role_cannot_disable_gate(tmp_path: Path, role: str) -> None:
    result = _run(tmp_path, role=role)
    assert result.returncode == 1 and "invalid tool.ocai.role" in result.stdout
