"""The one verification command: the gate every change passes before it is called done.

Every agent and every human runs the same gate, and CI runs the same steps.
Usage (from the repo root)::

    uv run python scripts/check.py            # the steps this change needs
    uv run python scripts/check.py --all      # every step, whatever changed
    uv run python scripts/check.py --no-tests # static checks only (no pytest, no platform tests)

The kernel steps (privacy, workspace, ruff, format, import contracts, pyright,
mypy, pytest) always run: they finish in seconds. The expensive steps are
**path-aware**: the platform gate (Docker, Node, Playwright), the docs build,
the independently installed plugin, and the change-file policy run only when
the change touches their tree, where "the change" is everything on this branch
since it left `origin/main` plus the working tree (staged, unstaged, and
untracked files). `--all` forces every step; CI always runs every job and
filters inside the job the same way (ADR 0002).

The summary ends with the commit the gate ran on and whether the tree was
dirty, so a pasted summary says exactly what was verified. Platform
prerequisites (Node, npm dependencies, the browser test runtime, Docker) are
documented in platform/README.md; the platform uses its own uv environment.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_REF = "origin/main"


@dataclass(frozen=True, slots=True)
class Step:
    """One gate in the check pipeline.

    Attributes:
        name: Short label printed in the summary.
        argv: The command to run, first element resolved on PATH.
        paths: Path prefixes (repo-relative, forward slashes) that make this
            step relevant. Empty means the step always runs.
    """

    name: str
    argv: tuple[str, ...]
    paths: tuple[str, ...] = field(default=())

    def relevant(self, changed: frozenset[str] | None) -> bool:
        """Whether this step runs for the given change set.

        Args:
            changed: Changed repo-relative paths, or None to run everything.

        Returns:
            True when the step always runs, everything is forced, or a changed
            path lies under one of the step's prefixes.
        """
        if not self.paths or changed is None:
            return True
        return any(p == prefix or p.startswith(prefix) for p in changed for prefix in self.paths)


@dataclass(frozen=True, slots=True)
class StepResult:
    """Outcome of one step.

    Attributes:
        step: The step that ran.
        returncode: Exit code of the command, -1 if it was not found, None if skipped.
        seconds: Wall-clock duration.
    """

    step: Step
    returncode: int | None
    seconds: float

    @property
    def ok(self) -> bool:
        """Whether the step passed (a skipped step counts as passed)."""
        return self.returncode in (0, None)

    @property
    def skipped(self) -> bool:
        """Whether the step was skipped as irrelevant to the change."""
        return self.returncode is None


def _git(*args: str) -> str | None:
    """Run git in the repo root and return stdout, or None when git fails.

    Args:
        *args: Arguments after `git`.

    Returns:
        Captured stdout, stripped, or None on a non-zero exit.
    """
    proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def changed_paths() -> frozenset[str] | None:
    """Everything this change touches: commits since `origin/main` plus the working tree.

    Returns:
        The repo-relative paths, or None when the base cannot be determined
        (no `origin/main`, detached history), in which case every step runs.
    """
    base = _git("merge-base", BASE_REF, "HEAD")
    if base is None:
        return None
    parts = [
        _git("diff", "--name-only", base, "HEAD"),
        _git("diff", "--name-only"),
        _git("diff", "--name-only", "--cached"),
        _git("ls-files", "--others", "--exclude-standard"),
    ]
    if any(p is None for p in parts):
        return None
    return frozenset(line for part in parts if part for line in part.splitlines() if line)


def head_label() -> str:
    """The commit the gate ran on, marked `+dirty` when the tree has local changes."""
    sha = _git("rev-parse", "--short", "HEAD") or "unknown"
    dirty = bool(_git("status", "--porcelain"))
    return f"{sha}+dirty" if dirty else sha


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


def steps_for(no_tests: bool) -> list[Step]:
    """The gate's steps, in order.

    Args:
        no_tests: Skip pytest and the platform's tests (static checks and builds only).

    Returns:
        The ordered steps; path-aware ones carry their prefixes.
    """
    platform_paths = ("platform/", "scripts/check_platform.py")
    steps = [
        Step("privacy guard", ("python", "scripts/privacy_check.py")),
        Step("workspace", ("python", "scripts/workspace_check.py")),
        Step("ruff", ("ruff", "check")),
        Step("format", ("ruff", "format", "--check")),
        Step("import contracts", ("lint-imports",)),
        Step("pyright (strict)", ("pyright",)),
        Step("mypy (strict)", ("mypy",)),
    ]
    if not no_tests:
        steps.append(Step("pytest", ("pytest",)))
    steps.append(
        Step(
            "change files",
            ("python", "scripts/release.py", "check", "--base", BASE_REF),
            paths=("python/packages/", ".changeset/", "knope.toml"),
        )
    )
    steps.append(
        Step(
            "docs build",
            ("python", "scripts/docs_check.py"),
            paths=("docs/", "zensical.toml", "scripts/docs_check.py"),
        )
    )
    steps.append(
        Step(
            "echo plugin (isolated install)",
            (
                "uv",
                "run",
                "--no-cache",
                "--isolated",
                "--no-project",
                "--python",
                "3.13",
                "--with",
                "./python/packages/ocai-core",
                "--with",
                "./examples/ocai-contrib-echo",
                "--with",
                "pytest",
                "--with",
                "jsonschema",
                "python",
                "-m",
                "pytest",
                "-c",
                "/dev/null",
                "--rootdir",
                "examples/ocai-contrib-echo",
                "--import-mode=importlib",
                "examples/ocai-contrib-echo/tests",
                "-q",
            ),
            paths=("examples/ocai-contrib-echo/", "python/packages/ocai-core/", "pyproject.toml"),
        )
    )
    platform_args = ("--no-tests",) if no_tests else ()
    steps.append(
        Step(
            "platform",
            ("python", "scripts/check_platform.py", *platform_args),
            paths=platform_paths,
        )
    )
    return steps


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Command-line arguments, defaulting to `sys.argv[1:]`.

    Returns:
        Process exit code: 0 when every step passed.
    """
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--no-tests", action="store_true", help="skip pytest and platform tests")
    parser.add_argument("--all", action="store_true", help="run every step regardless of the diff")
    args = parser.parse_args(argv)

    changed = None if args.all else changed_paths()
    if changed is None:
        scope = "every step (forced)" if args.all else "every step (no origin/main to diff against)"
    else:
        scope = (
            f"{len(changed)} changed path(s) vs {BASE_REF}; expensive steps run only when touched"
        )
    print(f"=== gate scope: {scope}", flush=True)

    results: list[StepResult] = []
    for step in steps_for(args.no_tests):
        if step.relevant(changed):
            results.append(_run(step))
        else:
            print(
                f"\n=== {step.name}: skipped (no change under {', '.join(step.paths)})", flush=True
            )
            results.append(StepResult(step, None, 0.0))

    print("\n=== summary")
    width = max(len(r.step.name) for r in results)
    for r in results:
        status = "skip" if r.skipped else ("ok  " if r.ok else "FAIL")
        print(f"  {status}  {r.step.name.ljust(width)}  {r.seconds:6.1f}s")
    failed = [r for r in results if not r.ok]
    print(f"\ngate: {head_label()} ({scope})")
    if failed:
        print(f"{len(failed)} step(s) failed.")
        return 1
    print("all checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
