"""Check documentation audience, navigation, source links and repository coverage."""

from __future__ import annotations

import re
import subprocess
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from typing import cast
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
USER = ROOT / "docs/user"


def documentation_files() -> list[Path]:
    """Return owned Markdown files, including new files and excluding vendored skills."""
    proc = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(
        {
            ROOT / name
            for name in proc.stdout.splitlines()
            if name.endswith(".md")
            and not name.startswith((".agents/skills/", ".claude/", ".codex/"))
            and (ROOT / name).is_file()
        }
    )


def nav_paths(value: Any) -> list[str]:
    """Collect explicit Markdown page paths from nested Zensical navigation."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        children = cast("Sequence[Any]", value)
        return [p for child in children for p in nav_paths(child)]
    if isinstance(value, dict):
        return [p for child in cast("dict[str, Any]", value).values() for p in nav_paths(child)]
    raise ValueError("Unknown navigation value")


def check() -> list[str]:
    """Return broken links, audience-boundary failures and unclassified pages."""
    findings: list[str] = []
    project = tomllib.loads((ROOT / "zensical.toml").read_text())["project"]
    if project.get("docs_dir") != "docs/user":
        findings.append("Zensical must publish only docs/user")
    pages = nav_paths(project["nav"])
    if len(set(pages)) != len(pages):
        findings.append("Navigation includes duplicate pages")
    for page in pages:
        path = (USER / page).resolve()
        if not path.is_relative_to(USER) or not path.is_file():
            findings.append(f"Invalid public navigation target: {page}")
    findings.extend(
        f"User page missing from navigation: {path.relative_to(USER)}"
        for path in USER.rglob("*.md")
        if path.relative_to(USER).as_posix() not in pages
    )
    for path in documentation_files():
        text = path.read_text(encoding="utf-8")
        # Literal examples may contain Markdown syntax and are not document links.
        text = re.sub(r"(?ms)^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", "", text)
        text = re.sub(r"`[^`]+`", "", text)
        for match in re.finditer(r"\]\(([^\s)]+)\)", text):
            url = match.group(1)
            if re.match(r"[a-zA-Z][\w+.-]*:|//|#", url):
                continue
            target = (path.parent / unquote(url.split("#", 1)[0])).resolve()
            if not target.exists():
                findings.append(f"{path.relative_to(ROOT)}: missing link {url}")
            elif path.is_relative_to(USER) and not target.is_relative_to(USER):
                findings.append(
                    f"{path.relative_to(ROOT)}: user link escapes published root: {url}"
                )
    return findings


def main() -> int:
    """Print documentation contract findings and return a verification status."""
    findings = check()
    for finding in findings:
        print(f"docs contract: {finding}")
    if findings:
        return 1
    print(f"docs contract: ok ({len(documentation_files())} Markdown sources; user-only site)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
