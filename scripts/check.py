"""The one verification command: privacy guard, lint, import contracts, types, tests.

Every agent and every human runs the same gate before calling a change done,
and CI runs the same steps. Usage (from the repo root)::

    uv run python scripts/check.py            # everything
    uv run python scripts/check.py --no-tests # static checks + platform build

The script prints one line per step and exits non-zero if any step fails.
Platform prerequisites (Node, npm dependencies, and the browser test runtime)
are documented in platform/README.md. The platform uses its own uv environment.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True, slots=True)
class Step:
    """One gate in the check pipeline.

    Attributes:
        name: Short label printed in the summary.
        argv: The command to run, first element resolved on PATH.
    """

    name: str
    argv: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StepResult:
    """Outcome of one step.

    Attributes:
        step: The step that ran.
        returncode: Exit code of the command, or -1 if it was not found.
        seconds: Wall-clock duration.
    """

    step: Step
    returncode: int
    seconds: float

    @property
    def ok(self) -> bool:
        """Whether the step passed."""
        return self.returncode == 0


def _run(step: Step) -> StepResult:
    """Run one step in the repo root, streaming its output.

    Args:
        step: The step to execute.

    Returns:
        The step's result; a missing executable counts as a failure.
    """
    exe = shutil.which(step.argv[0])
    print(f"\n=== {step.name}: {' '.join(step.argv)}", flush=True)
    if exe is None:
        print(f"!!! `{step.argv[0]}` not found on PATH — run through `uv run`.", flush=True)
        return StepResult(step, -1, 0.0)
    started = time.perf_counter()
    proc = subprocess.run([exe, *step.argv[1:]], cwd=ROOT, check=False)
    return StepResult(step, proc.returncode, time.perf_counter() - started)


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Command-line arguments, defaulting to `sys.argv[1:]`.

    Returns:
        Process exit code: 0 when every step passed.
    """
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--no-tests", action="store_true", help="skip pytest")
    args = parser.parse_args(argv)

    steps = [
        Step("privacy guard", ("python", "scripts/privacy_check.py")),
        Step("workspace", ("python", "scripts/workspace_check.py")),
        Step("ruff", ("ruff", "check")),
        Step("format", ("ruff", "format", "--check")),
    ]
    steps.append(Step("import contracts", ("lint-imports",)))
    steps.append(Step("pyright (strict)", ("pyright",)))
    steps.append(Step("mypy (strict)", ("mypy",)))
    if not args.no_tests:
        steps.append(Step("pytest", ("pytest",)))
    platform_args = ("--no-tests",) if args.no_tests else ()
    steps.append(Step("platform", ("python", "scripts/check_platform.py", *platform_args)))

    results = [_run(step) for step in steps]

    print("\n=== summary")
    width = max(len(r.step.name) for r in results)
    for r in results:
        status = "ok  " if r.ok else "FAIL"
        print(f"  {status}  {r.step.name.ljust(width)}  {r.seconds:6.1f}s")
    failed = [r for r in results if not r.ok]
    if failed:
        print(f"\n{len(failed)} step(s) failed.")
        return 1
    print("\nall checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
