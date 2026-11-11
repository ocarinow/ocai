"""Regressions for paginated boards and read-only pull request checks."""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path
from typing import Any

import board_sync
import pytest


@pytest.mark.parametrize("kind,pull_number", [("DraftIssue", 0), ("PullRequest", 135)])
def test_pagination_keeps_project_number(
    monkeypatch: pytest.MonkeyPatch, kind: str, pull_number: int
) -> None:
    requests: list[dict[str, str | int]] = []

    def graphql(_query: str, **variables: str | int) -> dict[str, Any]:
        requests.append(variables)
        assert variables["num"] == 8
        second = "after" in variables
        if second:
            assert variables["after"] == "next-page"
        content: dict[str, Any] = {
            "__typename": "DraftIssue" if second else kind,
            "title": "WU-136: Second page" if second else "WU-135: Documentation",
            "id": "draft-2" if second else "content-1",
        }
        if not second and kind == "PullRequest":
            content["number"] = pull_number
        return {
            "organization": {
                "projectV2": {
                    "id": "project-8",
                    "fields": {"nodes": []},
                    "items": {
                        "nodes": [{"id": "item-2" if second else "item-1", "content": content}],
                        "pageInfo": {"hasNextPage": not second, "endCursor": "next-page"},
                    },
                }
            }
        }

    monkeypatch.setattr(board_sync, "_graphql", graphql)
    board = board_sync.Board(8)
    assert len(requests) == 2
    assert len(board.items) == 2
    key = "PR#135" if kind == "PullRequest" else "WU-135: Documentation"
    assert board.items[key].number == pull_number
    assert board.items["WU-136: Second page"].content_id == "draft-2"


@pytest.mark.parametrize("event", ["pull_request", "push", "schedule"])
def test_workflow_only_applies_authoritative_events(tmp_path: Path, event: str) -> None:
    workflow = Path(__file__).resolve().parents[2] / ".github/workflows/board-sync.yml"
    script = textwrap.dedent(workflow.read_text().split("        run: |\n", 1)[1])
    for name, body in {
        "git": "#!/bin/sh\nexit 0\n",
        "python3": '#!/bin/sh\nprintf "%s\\n" "$@"\n',
    }.items():
        stub = tmp_path / name
        stub.write_text(body)
        stub.chmod(0o755)
    result = subprocess.run(
        ["bash", "-e", "-c", script],
        env={
            **os.environ,
            "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
            "BOARD_TOKEN": "synthetic-test-token",
            "EVENT": event,
        },
        capture_output=True,
        text=True,
        check=True,
    )
    arguments = result.stdout.splitlines()
    assert arguments[:2] == ["scripts/board_sync.py", "sync"]
    assert "origin/main" in arguments
    assert ("--apply" in arguments) == (event != "pull_request")
    assert ("--lenient" in arguments) == (event == "pull_request")
