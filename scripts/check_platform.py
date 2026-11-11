"""Verify the product in its own Python and JavaScript dependency environments."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    """Run platform checks, returning failure when any command fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-tests", action="store_true")
    args = parser.parse_args()
    gateway = ("uv", "run", "--directory", "services/gateway", "--frozen")
    commands: list[tuple[str, ...]] = [
        (*gateway, "ruff", "check"),
        (*gateway, "pyright"),
        (*gateway, "mypy"),
        ("npm", "run", "check:client"),
        ("npm", "run", "typecheck"),
        ("npm", "run", "typecheck:sessions"),
    ]
    if not args.no_tests:
        commands.extend(
            [
                ("docker", "info", "--format", "{{.ServerVersion}}"),
                (*gateway, "pytest"),
                ("npm", "test"),
            ]
        )
    commands.append(("npm", "run", "build"))
    if not args.no_tests:
        commands.append(("npm", "run", "test:browser"))
        commands.append(("npm", "run", "test:sessions"))
    for command in commands:
        print(f"\n--- platform: {' '.join(command)}", flush=True)
        result = subprocess.run(command, cwd=ROOT / "platform", check=False)
        if result.returncode:
            return result.returncode
    print("platform checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
