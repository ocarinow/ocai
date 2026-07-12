"""The §1 layer map is executable: `lint-imports` runs, checks, and bites.

Architecture §1 says an import against the dependency arrows is a build
failure. This suite is the proof that the enforcement is real, not aspirational:

1. The repo's own contracts (root `pyproject.toml`, `[tool.importlinter]`)
   pass, **and** the expected number of contracts was actually loaded and
   checked — a config typo that silently checked nothing would fail here.
2. Proof-it-bites: the same tool, pointed at a deliberately violated contract
   over the same namespace portions, exits non-zero and names the break. If
   import-linter ever stopped seeing the PEP 420 namespace split, this test —
   not a production regression — is what turns red.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# tests/ -> ocai-core -> packages -> python -> repo root.
REPO_ROOT = Path(__file__).resolve().parents[4]

# The number of contracts declared in [tool.importlinter]; keep in sync with
# the root pyproject.toml. Asserted exactly so a lost contract fails loudly.
DECLARED_CONTRACTS = 3

# A config exercising the same namespace portions as the real one, but with a
# contract the codebase deliberately violates everywhere: ocai.convert *must*
# import ocai.core (catalog/graph/contract all do). If lint-imports fails to
# flag this, it is not really analyzing the ocai namespace.
_VIOLATED_CONFIG = """\
[tool.importlinter]
root_packages = ["ocai.core", "ocai.convert"]

[[tool.importlinter.contracts]]
name = "Deliberately violated: convert may not import core"
type = "forbidden"
source_modules = ["ocai.convert"]
forbidden_modules = ["ocai.core"]
"""


def _lint_imports(*args: str) -> subprocess.CompletedProcess[str]:
    """Run this venv's `lint-imports` from the repo root and capture output.

    Args:
        args: Extra command-line arguments appended after `--no-cache`.

    Returns:
        The completed process, with stdout/stderr decoded.
    """
    executable = Path(sys.executable).parent / "lint-imports"
    assert executable.exists(), f"lint-imports not installed next to {sys.executable}"
    return subprocess.run(
        [str(executable), "--no-cache", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_repo_import_contracts_pass_and_are_actually_checked() -> None:
    result = _lint_imports()
    assert result.returncode == 0, f"lint-imports failed:\n{result.stdout}\n{result.stderr}"
    # Proof the run checked something: the summary line reports every declared
    # contract as kept. "Contracts: 0 kept, 0 broken." would pass the exit
    # code but fail here.
    summary = re.search(r"Contracts: (\d+) kept, (\d+) broken", result.stdout)
    assert summary is not None, f"no contract summary in output:\n{result.stdout}"
    kept, broken = int(summary.group(1)), int(summary.group(2))
    assert kept == DECLARED_CONTRACTS, f"expected {DECLARED_CONTRACTS} contracts, kept={kept}"
    assert broken == 0


def test_lint_imports_bites_on_a_violated_contract(tmp_path: Path) -> None:
    config = tmp_path / "violated.toml"
    config.write_text(_VIOLATED_CONFIG, encoding="utf-8")
    result = _lint_imports("--config", str(config))
    assert result.returncode != 0, f"violated contract not flagged:\n{result.stdout}"
    summary = re.search(r"Contracts: (\d+) kept, (\d+) broken", result.stdout)
    assert summary is not None, f"no contract summary in output:\n{result.stdout}"
    assert int(summary.group(2)) == 1  # exactly the planted violation
    assert "Deliberately violated" in result.stdout
