"""Shared test fixtures: locating the language-neutral `spec/` directory."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _find_repo_root(start: Path) -> Path:
    """Walk upward until we find the repo root (the dir containing `spec/`)."""
    for parent in [start, *start.parents]:
        if (parent / "spec" / "fixtures").is_dir():
            return parent
    raise RuntimeError("could not locate repo root (no spec/fixtures/ found)")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return _find_repo_root(Path(__file__).resolve())


@pytest.fixture(scope="session")
def spec_dir(repo_root: Path) -> Path:
    return repo_root / "spec"


@pytest.fixture(scope="session")
def core_src(repo_root: Path) -> Path:
    return repo_root / "python" / "packages" / "ocai-core" / "src" / "ocai"


@pytest.fixture(scope="session")
def openai_src(repo_root: Path) -> Path:
    return repo_root / "python" / "packages" / "ocai-openai" / "src" / "ocai"


@pytest.fixture(scope="session")
def anthropic_src(repo_root: Path) -> Path:
    return repo_root / "python" / "packages" / "ocai-anthropic" / "src" / "ocai"


@pytest.fixture
def load_fixture(spec_dir: Path):
    def _load(name: str) -> dict:
        return json.loads((spec_dir / "fixtures" / name).read_text())

    return _load


@pytest.fixture
def load_http():
    """Load a recorded HTTP request/response pair from `tests/http/`.

    These are VCR-style recordings replayed via respx (rule 10): no live API
    keys, no provider-SDK mocks — the real wire is exercised.
    """
    http_dir = Path(__file__).resolve().parent / "http"

    def _load(name: str) -> dict:
        return json.loads((http_dir / name).read_text())

    return _load
