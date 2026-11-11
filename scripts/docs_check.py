"""Build the documentation site and fail on any warning.

Zensical reports a missing nav page or a broken internal link as an issue and
still exits 0, so the build output is inspected for its "No issues found"
line. This is the one definition of the docs check: `scripts/check.py` runs
it when `docs/` or `zensical.toml` changed, `task docs:check` wraps it, and
the CI `docs` job runs the same command::

    uv run python scripts/docs_check.py

The site is rendered into ./site (gitignored) with the `docs` dependency
group, exactly as the deploy job does.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUCCESS_MARKER = "No issues found"


def main() -> int:
    """Entry point.

    Returns:
        0 when the site builds with no issues, 1 otherwise.
    """
    proc = subprocess.run(
        ["uv", "run", "--group", "docs", "zensical", "build", "--clean"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = proc.stdout + proc.stderr
    print(output, end="" if output.endswith("\n") else "\n")
    if proc.returncode != 0:
        print(f"docs: zensical exited {proc.returncode}")
        return 1
    if SUCCESS_MARKER not in output:
        print(f"docs: build reported issues (no {SUCCESS_MARKER!r} line)")
        return 1
    print("docs: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
