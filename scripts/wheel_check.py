"""Build every distribution and verify the wheels, not just the source tree.

Rules 1 and 16 are about what ships: no `ocai/__init__.py` at the namespace
root of any wheel (PEP 420, so sibling distributions merge into one `ocai`),
`py.typed` inside every namespace portion, and metadata that names the real
project (license expression, project URLs). Those invariants hold in `src/`
today, but a build-backend misconfiguration would break them only in the
artifact, which no other gate step opens. This script builds each
distribution into a scratch directory with `uv build` and inspects the wheel::

    uv run python scripts/wheel_check.py

It is a path-aware step of `scripts/check.py` (runs when `python/packages/`
changed) and a step of the CI `python` job.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ROOT / "python" / "packages"
LICENSE = "FSL-1.1-ALv2"
REQUIRED_URLS = ("Homepage", "Source", "Documentation", "Changelog")


def build(dist: Path, out: Path) -> list[str]:
    """Build one distribution into `out`; return findings (empty on success)."""
    proc = subprocess.run(
        ["uv", "build", "--project", str(dist), "--out-dir", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-3:]
        return [f"{dist.name}: uv build failed: " + " | ".join(tail)]
    return []


def inspect_wheel(dist: Path, wheel: Path) -> list[str]:
    """Open the wheel and check the namespace, typing markers, and metadata."""
    findings: list[str] = []
    rel = dist.relative_to(ROOT).as_posix()
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
        metadata = next((n for n in names if n.endswith(".dist-info/METADATA")), None)
        text = zf.read(metadata).decode("utf-8") if metadata else ""
    if "ocai/__init__.py" in names:
        findings.append(f"{wheel.name}: ships ocai/__init__.py (PEP 420 namespace root, rule 1)")
    portions = sorted(
        {n.split("/")[1] for n in names if n.startswith("ocai/") and n.count("/") >= 2}
    )
    findings.extend(
        f"{wheel.name}: ocai/{portion}/ has no py.typed (rule 16)"
        for portion in portions
        if f"ocai/{portion}/py.typed" not in names
    )
    if not portions:
        findings.append(f"{wheel.name}: no ocai/<portion>/ package inside")
    if f"License-Expression: {LICENSE}" not in text:
        findings.append(f"{wheel.name}: METADATA lacks `License-Expression: {LICENSE}` (rule 15)")
    findings.extend(
        f"{wheel.name}: METADATA lacks Project-URL {key}"
        for key in REQUIRED_URLS
        if f"Project-URL: {key}, " not in text
    )
    if "Classifier: License :: OSI Approved" in text:
        findings.append(
            f"{wheel.name}: carries an OSI classifier; ocai is not open source (rule 15)"
        )
    readme = (dist / "README.md").exists()
    if readme and "Description-Content-Type: text/markdown" not in text:
        findings.append(f"{rel}: README.md exists but the wheel has no Markdown description")
    return findings


def main() -> int:
    """Entry point.

    Returns:
        0 when every wheel passes, 1 otherwise.
    """
    dists = sorted(p.parent for p in PACKAGES.glob("*/pyproject.toml"))
    findings: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ocai-wheels-") as tmp:
        out = Path(tmp)
        for dist in dists:
            name = str(
                tomllib.loads((dist / "pyproject.toml").read_text("utf-8"))["project"]["name"]
            )
            findings.extend(build(dist, out))
            wheels = list(out.glob(f"{name.replace('-', '_')}-*.whl"))
            if len(wheels) != 1:
                findings.append(f"{dist.name}: expected one wheel, found {len(wheels)}")
                continue
            findings.extend(inspect_wheel(dist, wheels[0]))
    if findings:
        print(f"WHEELS: {len(findings)} finding(s) across {len(dists)} distribution(s)")
        for f in findings:
            print("  - " + f)
        return 1
    print(f"wheels: ok ({len(dists)} distributions built and inspected)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
