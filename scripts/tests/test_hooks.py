"""The git hooks stay local, pinned by the lockfile, and keep privacy at every stage."""

from __future__ import annotations

import re
from pathlib import Path

CONFIG = (Path(__file__).resolve().parents[2] / ".pre-commit-config.yaml").read_text(
    encoding="utf-8"
)
HOOK_RE = re.compile(r"^      - id: (?P<id>[a-z-]+)\n(?P<body>(?:        .*\n|\n)+)", re.MULTILINE)


def hooks() -> dict[str, str]:
    """Each hook id mapped to the text of its definition."""
    return {match["id"]: match["body"] for match in HOOK_RE.finditer(CONFIG)}


def stage(body: str) -> str:
    """The stage a hook runs at; the configured default when it names none."""
    found = re.search(r"stages: \[([a-z-]+)\]", body)
    return found[1] if found else "pre-commit"


def test_every_hook_is_local_and_runs_the_locked_tools() -> None:
    assert re.findall(r"^  - repo: (.+)$", CONFIG, re.MULTILINE) == ["local"]
    for name, body in hooks().items():
        assert "language: system" in body, name
        assert re.search(r"entry: (uv run |uv lock |uvx --from [a-z]+==)", body), name


def test_privacy_guard_runs_at_commit_on_the_message_and_at_push() -> None:
    stages = {stage(body) for name, body in hooks().items() if name.startswith("privacy-")}

    assert stages == {"pre-commit", "commit-msg", "pre-push"}


def test_all_three_hook_types_are_installed_by_default() -> None:
    assert "default_install_hook_types: [pre-commit, commit-msg, pre-push]" in CONFIG


def test_slow_checks_wait_for_the_push() -> None:
    by_stage = {name: stage(body) for name, body in hooks().items()}

    assert by_stage["tests"] == "pre-push"
    assert by_stage["change-files"] == "pre-push"
    assert by_stage["ruff"] == "pre-commit"
    assert by_stage["pyright"] == "pre-commit"
