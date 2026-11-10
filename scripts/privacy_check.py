"""Privacy guard: nothing that leaves this machine may carry session or tool metadata.

The repository is public. This script fails when a commit message, a PR
title or body, or a tracked file contains an AI coding-session link, an AI
attribution footer or trailer, an agent/task identifier, or a path under a
user's home directory. It is one step of `scripts/check.py`, a required CI
job on every pull request, and runnable by hand::

    uv run python scripts/privacy_check.py                 # local commits ahead of origin/main + tracked files
    uv run python scripts/privacy_check.py --range A..B    # explicit commit range
    uv run python scripts/privacy_check.py --text FILE     # also scan a PR title/body saved to FILE

The rule it enforces is in AGENTS.md ("Never publish session or tool
metadata — anywhere"). A hit is fixed by rewriting the message or text,
never by editing the patterns below.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Patterns that identify a leak. Message patterns are broad; file patterns
# are the concrete artifacts (a real session URL, a real home path), so that
# documentation may describe the rule without tripping it.
MESSAGE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("AI session link", r"claude\.ai/code|session_0[A-Za-z0-9]{10,}|chatgpt\.com/codex/|/codex/threads/"),
    ("AI session trailer", r"^\s*(Claude-Session|Codex-Session|Session-Url)\s*:"),
    ("AI attribution trailer", r"^\s*Co-Authored-By:.*(anthropic\.com|openai\.com|noreply@.*claude)"),
    ("AI generated footer", r"Generated with \[?(Claude|Codex|ChatGPT)|🤖 Generated"),
    ("agent/task identifier", r"\b(agentId|task-id|subagent)\b.*[0-9a-f]{12,}"),
    ("home directory path", r"/(Users|home)/[A-Za-z0-9._-]+/"),
)
FILE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("AI session link", r"claude\.ai/code/session_[A-Za-z0-9]{10,}|/codex/threads/[A-Za-z0-9-]{8,}"),
    ("AI session trailer", r"^\s*(Claude-Session|Codex-Session)\s*:\s*https?://"),
    ("home directory path", r"/(Users|home)/[A-Za-z0-9._-]+/[A-Za-z0-9._-]"),
)
TEXT_FILE_SUFFIXES = {".md", ".py", ".toml", ".yml", ".yaml", ".json", ".txt", ".cfg", ".ini", ".sh"}


def _git(*args: str) -> str:
    """Run git in the repo root and return stdout.

    Args:
        *args: Arguments after `git`.

    Returns:
        Captured stdout, stripped.
    """
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False).stdout.strip()


def _scan(text: str, patterns: tuple[tuple[str, str], ...], where: str) -> list[str]:
    """Return one finding line per matching pattern occurrence.

    Args:
        text: The text to scan.
        patterns: (label, regex) pairs.
        where: Human-readable location for the report.

    Returns:
        Finding lines, empty when clean.
    """
    findings: list[str] = []
    for label, regex in patterns:
        for match in re.finditer(regex, text, flags=re.IGNORECASE | re.MULTILINE):
            line_no = text.count("\n", 0, match.start()) + 1
            findings.append(f"{where}:{line_no}: {label}: {match.group(0)[:80]!r}")
    return findings


def _default_range() -> str | None:
    """Commits ahead of origin/main, or None when the ref is unknown."""
    base = _git("merge-base", "HEAD", "origin/main")
    return f"{base}..HEAD" if base else None


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Command-line arguments, defaulting to `sys.argv[1:]`.

    Returns:
        0 when clean, 1 when any finding exists.
    """
    parser = argparse.ArgumentParser(description="Fail on session links, AI footers, or local paths.")
    parser.add_argument("--range", help="git commit range to scan (default: merge-base(origin/main)..HEAD)")
    parser.add_argument("--text", action="append", default=[], help="file holding a PR title/body to scan")
    parser.add_argument("--no-files", action="store_true", help="skip scanning tracked files")
    args = parser.parse_args(argv)

    findings: list[str] = []

    rng = args.range or _default_range()
    if rng:
        shas = _git("rev-list", rng).split()
        for sha in shas:
            message = _git("show", "-s", "--format=%B", sha)
            findings += _scan(message, MESSAGE_PATTERNS, f"commit {sha[:10]}")
        print(f"scanned {len(shas)} commit message(s) in {rng}")
    else:
        print("no origin/main; commit messages not scanned")

    for path in args.text:
        findings += _scan(Path(path).read_text(encoding="utf-8", errors="replace"), MESSAGE_PATTERNS, path)
        print(f"scanned text {path}")

    if not args.no_files:
        files = [f for f in _git("ls-files").split("\n") if f and Path(f).suffix in TEXT_FILE_SUFFIXES]
        for rel in files:
            if rel == "scripts/privacy_check.py":
                continue
            try:
                text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            findings += _scan(text, FILE_PATTERNS, rel)
        print(f"scanned {len(files)} tracked text file(s)")

    if findings:
        print("\nPRIVACY LEAK — remove before publishing (AGENTS.md: never publish session or tool metadata):")
        for f in findings:
            print("  " + f)
        return 1
    print("privacy: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
