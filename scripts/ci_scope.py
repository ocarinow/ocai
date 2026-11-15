"""Conservative impact policy: which CI suites a change must run.

The first job of `.github/workflows/ci.yml` runs this once and every suite job
reads its flag. Diffs use git, not an API's truncated file list. Renames are
represented as a removal plus an addition. Unknown history or an unclassified
path runs everything.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
# A change to any of these runs every suite.
GLOBAL = (
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    ".node-version",
    ".gitignore",
    ".gitattributes",
    "scripts/ci_scope.py",
    ".github/workflows/",
)
PATHS: dict[str, tuple[str, ...]] = {
    "python": (
        "python/",
        "spec/",
        "examples/",
        "scripts/",
        "knope.toml",
        "LICENSE",
        ".pre-commit-config.yaml",
    ),
    # The gateway declares no dependency on the kernel packages and imports none
    # of them. Add `python/` here on the day it does.
    "platform": ("platform/", "scripts/check_platform.py"),
    "docs": (
        "docs/",
        "zensical.toml",
        "scripts/docs_check.py",
        "scripts/docs_reference.py",
        "scripts/docs_contract.py",
        "python/",
        "platform/spec/",
        "platform/packages/management-client/",
    ),
    "workflows": (".github/",),
    "semgrep": ("python/", "platform/", "scripts/", "examples/", ".github/"),
}
# Paths that are classified and run no suite beyond the ones above: instruction
# files, agent configuration, task definitions, change files, editor settings.
KNOWN = (
    *GLOBAL,
    *(p for paths in PATHS.values() for p in paths),
    "AGENTS.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "README.md",
    "SECURITY.md",
    "NOTICE",
    ".agents/",
    ".claude/",
    ".codex/",
    ".changeset/",
    ".editorconfig",
    ".vscode/",
    "ocai.code-workspace",
    "Taskfile.yml",
    "tasks/",
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
    """Select against the PR's actual base and head; manual and nightly runs are full."""
    if event_name == "pull_request":
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
    """Write one `<suite>=true|false` output per suite, with a readable reason."""
    try:
        event: dict[str, Any] = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        changed = event_paths(ROOT, os.environ["GITHUB_EVENT_NAME"], event)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(f"Impact unavailable ({type(exc).__name__}); running every suite.")
        changed = None
    reason = "full validation" if changed is None else f"{len(changed)} changed paths"
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        for suite in PATHS:
            run = affected(suite, changed)
            print(f"{suite}: {'run' if run else 'unaffected'} ({reason})")
            output.write(f"{suite}={str(run).lower()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
