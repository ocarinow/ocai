"""Verify the product in isolated backend/frontend lanes, preserving every check."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class LaneResult:
    """Result and timings for an independently executed platform lane."""

    name: str
    returncode: int
    seconds: float
    steps: tuple[tuple[str, float, int], ...]


def commands_for(no_tests: bool) -> dict[str, list[tuple[str, ...]]]:
    """Keep dependent commands ordered within each lane; lanes share no build outputs."""
    gateway = ("uv", "run", "--directory", "services/gateway", "--frozen")
    backend: list[tuple[str, ...]] = [
        ("uv", "lock", "--check", "--directory", "services/gateway"),
        (*gateway, "ruff", "check"),
        (*gateway, "pyright"),
        (*gateway, "mypy"),
    ]
    frontend: list[tuple[str, ...]] = [
        ("npm", "run", name) for name in ("check:client", "typecheck", "lint")
    ]
    if not no_tests:
        backend.extend([("docker", "info", "--format", "{{.ServerVersion}}"), (*gateway, "pytest")])
        frontend.append(("npm", "test"))
    frontend.append(("npm", "run", "build"))
    if not no_tests:
        frontend.append(("npm", "run", "test:browser"))
    return {"backend": backend, "frontend": frontend}


def run_lane(name: str, commands: list[tuple[str, ...]], cwd: Path, log: Path) -> LaneResult:
    """Execute dependent steps, stopping the lane on failure and retaining its log."""
    started = time.perf_counter()
    timings: list[tuple[str, float, int]] = []
    code = 0
    with log.open("w") as output:
        for command in commands:
            label = " ".join(command)
            print(f"\n--- {name}: {label}", file=output, flush=True)
            before = time.perf_counter()
            try:
                result = subprocess.run(
                    command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT, check=False
                )
                code = result.returncode
            except OSError as exc:
                print(str(exc), file=output)
                code = 1
            timings.append((label, time.perf_counter() - before, code))
            if code:
                break
    return LaneResult(name, code, time.perf_counter() - started, tuple(timings))


def run_lanes(
    lanes: dict[str, list[tuple[str, ...]]],
    cwd: Path,
    *,
    serial: bool = False,
) -> list[LaneResult]:
    """Join all independent lanes, retaining output even when another lane fails."""
    with tempfile.TemporaryDirectory(prefix="ocai-platform-check-") as directory:
        logs = {name: Path(directory) / f"{name}.log" for name in lanes}
        with ThreadPoolExecutor(max_workers=1 if serial else len(lanes)) as pool:
            futures = [
                pool.submit(run_lane, name, commands, cwd, logs[name])
                for name, commands in lanes.items()
            ]
            results = [future.result() for future in futures]
        for result in results:
            print(logs[result.name].read_text(), flush=True)
    return results


def main() -> int:
    """Run both lanes concurrently; any lane failure fails the platform check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-tests", action="store_true")
    parser.add_argument(
        "--serial", action="store_true", help="run lanes sequentially for comparison"
    )
    args = parser.parse_args()
    # Provision once before either lane can invoke the gateway (browser tests use it too).
    sync = subprocess.run(
        ("uv", "sync", "--directory", "services/gateway", "--frozen"),
        cwd=ROOT / "platform",
        check=False,
    )
    if sync.returncode:
        return sync.returncode
    started = time.perf_counter()
    lanes = commands_for(args.no_tests)
    results = run_lanes(lanes, ROOT / "platform", serial=args.serial)
    summary = [
        "### Platform verification",
        "",
        "| Lane / command | Seconds | Exit |",
        "|---|---:|---:|",
    ]
    for result in results:
        summary.append(f"| **{result.name}** | {result.seconds:.1f} | {result.returncode} |")
        for command, seconds, code in result.steps:
            summary.append(f"| `{command}` | {seconds:.1f} | {code} |")
    summary.append(f"\nElapsed after environment setup: {time.perf_counter() - started:.1f}s")
    report = "\n".join(summary) + "\n"
    print(report, flush=True)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(path).open("a") as output:
            output.write(report)
    if any(result.returncode for result in results):
        return 1
    print("platform checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
