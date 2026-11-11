"""Shared conservative impact policy for local verification and GitHub Actions.

Diffs use git, not an API's truncated file list. Renames are represented as a
removal plus an addition. Unknown history or an unclassified path runs everything.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
GLOBAL = (
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    ".node-version",
    ".gitignore",
    ".gitattributes",
    "scripts/ci_scope.py",
    "scripts/check.py",
    "scripts/tests/",
    ".github/workflows/",
)
PATHS: dict[str, tuple[str, ...]] = {
    "python": (
        "python/",
        "spec/",
        "examples/",
        "scripts/",
        "tasks/",
        "Taskfile.yml",
        "knope.toml",
        "LICENSE",
    ),
    "platform": ("platform/", "python/", "spec/", "scripts/", "tasks/", "Taskfile.yml"),
    "docs": ("docs/", "zensical.toml", "scripts/docs_check.py"),
    "workflows": (".github/",),
    "semgrep": ("python/", "platform/", "scripts/", "tasks/", "examples/", ".github/"),
    # Reviewing dependencies is cheap and remains unconditional on code PR events.
    "dependency-review": ("",),
    "wheels": ("python/", "scripts/wheel_check.py", "knope.toml", "LICENSE"),
    "echo": ("python/", "examples/", "spec/", "LICENSE"),
    "plans": ("docs/plans/", "scripts/board_sync.py"),
    "changesets": ("python/", ".changeset/", "knope.toml", "scripts/release.py"),
    "typescript": ("typescript/", "spec/"),
    "go": ("go/", "spec/"),
}
# Explicit non-code paths still receive privacy/hygiene and relevant docs checks.
KNOWN = (
    *GLOBAL,
    *(p for paths in PATHS.values() for p in paths if p),
    "AGENTS.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "README.md",
    "SECURITY.md",
    "LICENSE",
    "NOTICE",
    ".agents/",
    ".claude/",
    ".codex/",
    ".gitignore",
    ".githooks/",
    ".editorconfig",
    ".vscode/",
    "ocai.code-workspace",
)


def matches(path: str, prefixes: tuple[str, ...]) -> bool:
    """Match exact file names and directory prefixes, without partial file matches."""
    return any(not p or path == p or (p.endswith("/") and path.startswith(p)) for p in prefixes)


def affected(suite: str, changed: frozenset[str] | None) -> bool:
    """Run a suite if affected, or all suites when impact cannot be established."""
    paths = PATHS[suite]  # Unknown suite is a configuration error, never a skip.
    if changed is None:
        return True
    return any(not matches(p, KNOWN) or matches(p, (*GLOBAL, *paths)) for p in changed)


def git_paths(
    root: Path, base: str, head: str = "HEAD", *, working: bool = False, merge_base: bool = True
) -> frozenset[str] | None:
    """Read the full diff, including both sides of renames and optional local edits."""

    def git(*args: str) -> str | None:
        result = subprocess.run(
            ("git", *args), cwd=root, capture_output=True, text=True, check=False
        )
        return result.stdout if result.returncode == 0 else None

    start = git("merge-base", base, head) if merge_base else base
    if not start:
        return None
    commands: list[tuple[str, ...]] = [
        ("diff", "--no-renames", "--name-only", "-z", start.strip(), head, "--")
    ]
    if working:
        commands.extend(
            [
                ("diff", "--no-renames", "--name-only", "-z", "--"),
                ("diff", "--no-renames", "--name-only", "-z", "--cached", "--"),
                ("ls-files", "--others", "--exclude-standard", "-z"),
            ]
        )
    parts = [git(*command) for command in commands]
    if any(part is None for part in parts):
        return None
    return frozenset(p for part in parts if part for p in part.split("\0") if p)


def event_paths(root: Path, event_name: str, event: dict[str, Any]) -> frozenset[str] | None:
    """Select against the PR's actual base/head; force full runs on retarget/dispatch."""
    if event_name == "pull_request":
        if event.get("changes", {}).get("base") is not None:
            return None
        pr = event["pull_request"]
        return git_paths(root, str(pr["base"]["sha"]), str(pr["head"]["sha"]))
    if event_name == "push":
        before = event.get("before")
        after = event.get("after")
        if not before or not after or set(str(before)) == {"0"}:
            return None
        return git_paths(root, str(before), str(after), merge_base=False)
    return None


def main() -> int:
    """Emit an explicit Actions output and a human-readable selection reason."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=tuple(PATHS), required=True)
    args = parser.parse_args()
    try:
        event: dict[str, Any] = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        changed = event_paths(ROOT, os.environ["GITHUB_EVENT_NAME"], event)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(f"Impact unavailable ({type(exc).__name__}); running every suite.")
        changed = None
    run = affected(args.suite, changed)
    reason = "full validation" if changed is None else f"{len(changed)} changed paths"
    print(f"{args.suite}: {'run' if run else 'unaffected'} ({reason})")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"run={str(run).lower()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
