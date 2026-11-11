"""Render tasks/README.md, the task catalogue, from `task --list-all --json`.

The catalogue is what a human or a coding agent reads to know which command
exists for which job; it must never drift from the Taskfiles, so it is
generated::

    task tasks:readme          # rewrite tasks/README.md
    task tasks:check           # exit 1 if it is stale (reviewers run it on Taskfile changes)

Every task's one-line `desc` is the documentation; argument conventions are
in the `desc` itself (`task x -- ARGS`). Keep descriptions honest and short.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "tasks" / "README.md"

DOMAINS: dict[str, str] = {
    "": "Root — aliases and setup",
    "py": "Python workspace — environment, lint, types, tests, the gate",
    "docs": "Zensical site — preview, build, link checks",
    "privacy": "Privacy guard — nothing from a session goes public",
    "pr": "Branches, worktrees, pull requests, reviews",
    "board": "The GitHub Project board — cards, sync, maintainer handoffs",
    "serve": "Local platform — services, dependencies and lifecycle",
    "spec": "spec/ — schema and fixture validation",
    "release": "Versions and releases — changesets, bumps, changelogs (ADR 0010)",
}

HEADER = """# Tasks

Every development command, one verb per job, grouped by domain. Generated
from the Taskfiles by `task tasks:readme`; do not edit by hand. Requires
[Task](https://taskfile.dev) (`brew install go-task` on macOS).

How to read a line: `task <domain>:<verb>` runs it; `-- ARGS` passes
arguments where the description shows them. `task` alone prints this list
from the live definitions; `task --summary <name>` prints one task's details.

Two rules hold for every task here, from `AGENTS.md`:

- the Taskfiles **wrap** the canonical commands and never add a check CI
  does not run — the gate has one definition, `scripts/check.py`
  (`task check`);
- every task that publishes anything (`pr:*`, `board:*`) runs the privacy
  guard first; a leak fails the task before `gh` is called.

For a coding agent: `task check` before every claim of done, `task
privacy:text -- FILE` before every PR body, review, or issue you post,
`task pr:draft` at the first commit of a WU so its card is In progress,
`task board:decision` instead of asking the maintainer in chat.
"""


def render() -> str:
    """Build the catalogue text from the live task list."""
    raw = subprocess.run(
        ["task", "--list-all", "--json"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    tasks = json.loads(raw)["tasks"]
    groups: dict[str, list[tuple[str, str]]] = {k: [] for k in DOMAINS}
    for item in tasks:
        name = str(item["name"])
        domain = name.split(":", 1)[0] if ":" in name else ""
        groups.setdefault(domain, []).append((name, str(item.get("desc", "")).strip()))
    out = [HEADER]
    for domain, title in DOMAINS.items():
        rows = sorted(groups.get(domain, []))
        if not rows:
            continue
        out.append(f"\n## {title}\n\n| Task | Does |\n|---|---|\n")
        out.extend(f"| `task {name}` | {desc} |\n" for name, desc in rows)
    extra = [d for d in groups if d not in DOMAINS and groups[d]]
    for domain in sorted(extra):
        out.append(f"\n## {domain}\n\n| Task | Does |\n|---|---|\n")
        out.extend(f"| `task {name}` | {desc} |\n" for name, desc in sorted(groups[domain]))
    return "".join(out)


def main(argv: list[str] | None = None) -> int:
    """Entry point: write the catalogue, or with `--check` verify it is current."""
    args = argv if argv is not None else sys.argv[1:]
    text = render()
    if "--check" in args:
        current = README.read_text(encoding="utf-8") if README.exists() else ""
        if current != text:
            print("tasks/README.md is stale: run `task tasks:readme`")
            return 1
        print("tasks/README.md is current")
        return 0
    README.write_text(text, encoding="utf-8")
    print(f"wrote {README.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
