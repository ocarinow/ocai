"""Release policy: a change file must travel with any change to a published package.

The mechanics (bumping `pyproject.toml`, writing `CHANGELOG.md`, tagging,
GitHub Releases) belong to knope (`knope.toml`, ADR 0010). This script holds
only the repo-specific rule, run by the `pr-hygiene` CI job and locally by
`task release:check`::

    uv run python scripts/release.py check --base origin/main   # change file when a package changed
    uv run python scripts/release.py packages                   # published packages and versions

A change file lives in `.changeset/<id>.md` with `package: level` front matter
and a note (see `.changeset/README.md`). The check validates every pending file
(known package names, levels patch|minor|major, non-empty body) and fails when
a file under a published package changed in this branch without a change file
added in this branch.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGESET = ROOT / ".changeset"
KNOPE = ROOT / "knope.toml"
LEVELS = ("patch", "minor", "major")
FRONT_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


@dataclass(frozen=True, slots=True)
class Package:
    """A published distribution declared in knope.toml.

    Attributes:
        name: Package name (knope key and pyproject `name`).
        path: Directory holding its pyproject.
        version: Current version string.
    """

    name: str
    path: Path
    version: str


def packages() -> dict[str, Package]:
    """The published packages from knope.toml with their current versions."""
    cfg = tomllib.loads(KNOPE.read_text(encoding="utf-8"))
    found: dict[str, Package] = {}
    for name, spec in cfg.get("packages", {}).items():
        files: list[str] = spec.get("versioned_files", [])
        pyproject = ROOT / files[0]
        version = str(tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"])
        found[str(name)] = Package(str(name), pyproject.parent, version)
    return found


def validate_change_files(known: dict[str, Package]) -> list[str]:
    """Return one problem per malformed pending change file."""
    problems: list[str] = []
    for path in sorted(CHANGESET.glob("*.md")):
        if path.name == "README.md":
            continue
        rel = path.relative_to(ROOT)
        m = FRONT_RE.match(path.read_text(encoding="utf-8"))
        if not m:
            problems.append(f"{rel}: missing front matter (--- package: level ---)")
            continue
        for line in m.group(1).splitlines():
            if not line.strip():
                continue
            if ":" not in line:
                problems.append(f"{rel}: bad line {line!r}")
                continue
            pkg, level = (x.strip().strip("'\"") for x in line.split(":", 1))
            if pkg not in known:
                problems.append(
                    f"{rel}: unknown package {pkg!r} (knope.toml knows {sorted(known)})"
                )
            if level not in LEVELS:
                problems.append(f"{rel}: level {level!r} is not one of {LEVELS}")
        if not m.group(2).strip():
            problems.append(f"{rel}: empty body (the changelog note)")
    return problems


def changed_paths(base: str) -> list[str]:
    """Files changed in this branch (committed or not) since the merge base with `base`."""
    proc = subprocess.run(
        ["git", "merge-base", "HEAD", base], capture_output=True, text=True, cwd=ROOT
    )
    mb = proc.stdout.strip()
    if not mb:
        return []
    out = subprocess.run(
        ["git", "diff", "--name-only", mb], capture_output=True, text=True, cwd=ROOT
    )
    return [p for p in out.stdout.split("\n") if p]


def cmd_check(args: argparse.Namespace) -> int:
    """Validate pending change files; require one when a published package changed."""
    known = packages()
    problems = validate_change_files(known)
    changed = changed_paths(args.base)
    touched: set[str] = set()
    for pkg in known.values():
        prefix = str(pkg.path.relative_to(ROOT)) + "/"
        if any(p.startswith(prefix) and not p.endswith("CHANGELOG.md") for p in changed):
            touched.add(pkg.name)
    added = [
        p
        for p in changed
        if p.startswith(".changeset/") and p.endswith(".md") and p != ".changeset/README.md"
    ]
    if touched and not added and not args.release_pr:
        problems.append(
            "published package(s) changed without a change file in this branch: "
            + ", ".join(sorted(touched))
            + "  → add .changeset/<id>.md (package: patch|minor|major + note; docs/releasing.md)"
        )
    if problems:
        print("CHANGE FILES:")
        for pr in problems:
            print("  - " + pr)
        return 1
    kind = "release PR" if args.release_pr else "ok"
    print(f"change files: {kind} (touched: {sorted(touched) or 'none'}; added here: {len(added)})")
    return 0


def cmd_packages(args: argparse.Namespace) -> int:
    """List the published packages and their versions."""
    for p in packages().values():
        print(f"{p.name} {p.version} ({p.path.relative_to(ROOT)})")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Command-line arguments, defaulting to `sys.argv[1:]`.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Change-file policy for releases (ADR 0010).")
    sub = parser.add_subparsers(dest="command", required=True)
    p_check = sub.add_parser("check", help="require a change file when a published package changed")
    p_check.add_argument("--base", default="origin/main")
    p_check.add_argument(
        "--release-pr",
        action="store_true",
        help="the standing Release PR: version/changelog edits need no change file",
    )
    p_check.set_defaults(func=cmd_check)
    sub.add_parser("packages", help="list published packages and versions").set_defaults(
        func=cmd_packages
    )
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
