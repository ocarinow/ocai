"""Impact selection must prefer extra validation to missing a dependency."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from ci_scope import PATHS
from ci_scope import affected
from ci_scope import event_paths
from ci_scope import git_paths


@pytest.mark.parametrize(
    "path",
    [
        "pyproject.toml",
        "uv.lock",
        ".node-version",
        ".gitignore",
        "scripts/ci_scope.py",
        ".github/workflows/ci.yml",
        "unknown-new-tool.toml",
    ],
)
def test_shared_or_unknown_inputs_run_everything(path: str) -> None:
    assert all(affected(suite, frozenset({path})) for suite in PATHS)


def test_docs_only_keeps_code_suites_unaffected() -> None:
    changed = frozenset({"docs/guides/example.md"})
    assert affected("docs", changed)
    assert not affected("python", changed)
    assert not affected("platform", changed)
    assert not affected("semgrep", changed)


@pytest.mark.parametrize(
    ("path", "suites"),
    [
        ("python/packages/ocai-core/src/ocai/core/result.py", {"python", "docs", "semgrep"}),
        ("spec/schema/chat.json", {"python"}),
        ("platform/package-lock.json", {"platform", "semgrep"}),
        ("platform/spec/management.openapi.json", {"platform", "docs", "semgrep"}),
        ("scripts/privacy_check.py", {"python", "semgrep"}),
        ("scripts/check_platform.py", {"python", "platform", "semgrep"}),
        (".pre-commit-config.yaml", {"python"}),
        (".github/dependabot.yml", {"workflows", "semgrep"}),
    ],
)
def test_a_change_runs_only_the_suites_that_depend_on_it(path: str, suites: set[str]) -> None:
    assert {suite for suite in PATHS if affected(suite, frozenset({path}))} == suites


@pytest.mark.parametrize(
    "path",
    [
        "Taskfile.yml",
        "tasks/python.Taskfile.yml",
        ".changeset/some-change.md",
        "AGENTS.md",
        ".agents/skills/add-edge/SKILL.md",
        ".claude/settings.json",
    ],
)
def test_task_definitions_change_files_and_instructions_run_no_suite(path: str) -> None:
    assert not any(affected(suite, frozenset({path})) for suite in PATHS)


def test_missing_history_and_forced_events_run_everything(tmp_path: Path) -> None:
    assert git_paths(tmp_path, "missing") is None
    for event in ["workflow_dispatch", "schedule"]:
        assert event_paths(tmp_path, event, {}) is None
    assert all(affected(suite, None) for suite in PATHS)


def test_complete_diff_tracks_renames_deletes_and_local_edits(tmp_path: Path) -> None:
    def git(*args: str) -> str:
        return subprocess.check_output(("git", *args), cwd=tmp_path, text=True).strip()

    git("init", "-q")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Test")
    (tmp_path / "platform").mkdir()
    (tmp_path / "platform/old.txt").write_text("old")
    (tmp_path / "removed.txt").write_text("remove")
    git("add", ".")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    git("mv", "platform/old.txt", "moved.txt")
    git("rm", "removed.txt")
    git("commit", "-qm", "rename and delete")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/new.md").write_text("untracked")
    paths = git_paths(tmp_path, base, working=True)
    assert paths is not None
    assert paths == frozenset({"platform/old.txt", "moved.txt", "removed.txt", "docs/new.md"})
    assert affected("platform", paths)
    # The selector compares against the actual PR base, not hard-coded main.
    head = git("rev-parse", "HEAD")
    event = {"pull_request": {"base": {"sha": base}, "head": {"sha": head}}}
    assert event_paths(tmp_path, "pull_request", event) == paths - {"docs/new.md"}
    assert event_paths(tmp_path, "push", {"before": base, "after": head}) == paths - {"docs/new.md"}


def test_large_diff_is_not_truncated(tmp_path: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(("git", *args), cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Test")
    git("commit", "--allow-empty", "-qm", "base")
    for index in range(3500):
        (tmp_path / f"file-{index}.md").touch()
    git("add", ".")
    paths = git_paths(tmp_path, "HEAD", working=True)
    assert paths is not None
    assert len(paths) == 3500


def test_unknown_suite_is_an_error() -> None:
    with pytest.raises(KeyError):
        affected("typo", frozenset())


def test_selector_error_runs_everything(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ci_scope import main

    event = tmp_path / "event.json"
    event.write_text("invalid JSON")
    output = tmp_path / "output"
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    assert main() == 0
    assert output.read_text() == "".join(f"{suite}=true\n" for suite in PATHS)
