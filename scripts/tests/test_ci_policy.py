"""The workflows keep one decision, one required check per concern, and no masked failure."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from ci_rules import REQUIRED
from ci_scope import PATHS

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github/workflows"
SUITE_JOBS = ("python", "platform", "docs", "workflows", "semgrep")


def workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text()


def jobs(name: str) -> dict[str, str]:
    """Each job key of a workflow mapped to the text of its definition."""
    body = workflow(name).split("\njobs:\n", 1)[1]
    keys = re.findall(r"^  ([\w-]+):\n", body, re.MULTILINE)
    parts = re.split(r"^  [\w-]+:\n", body, flags=re.MULTILINE)[1:]
    return dict(zip(keys, parts, strict=True))


def field(block: str, key: str) -> str:
    match = re.search(rf"^    {key}: (.+)$", block, re.MULTILINE)
    assert match, key
    return match[1]


def triggers(name: str) -> set[str]:
    head = workflow(name).split("\njobs:\n", 1)[0]
    return set(re.findall(r"^  (\w+):", head.split("\non:\n", 1)[1], re.MULTILINE)) - {
        "contents",
        "group",
    }


def test_suites_are_selected_once_and_every_suite_reads_that_decision() -> None:
    assert set(SUITE_JOBS) == set(PATHS)
    assert workflow("ci.yml").count("scripts/ci_scope.py") == 2  # one comment, one command
    changes = jobs("ci.yml")["changes"]
    assert "fetch-depth: 0" in changes
    for suite in SUITE_JOBS:
        assert f"      {suite}: ${{{{ steps.scope.outputs.{suite} }}}}" in changes
        block = jobs("ci.yml")[suite]
        assert field(block, "needs") == "changes"
        # `!= 'false'`: a failed or empty selection runs the suite.
        assert field(block, "if") == (
            f"${{{{ !cancelled() && needs.changes.outputs.{suite} != 'false' }}}}"
        )


@pytest.mark.parametrize(
    ("name", "check", "covered"),
    [
        ("ci.yml", "ci", None),
        ("pr-metadata.yml", "pr", {"pr-hygiene", "privacy"}),
    ],
)
def test_one_required_check_per_workflow_sees_every_job(
    name: str, check: str, covered: set[str] | None
) -> None:
    blocks = jobs(name)
    aggregate = blocks[check]
    needs = set(re.findall(r"[\w-]+", field(aggregate, "needs")))

    assert needs == (covered if covered is not None else set(blocks) - {check})
    assert field(aggregate, "name") == check
    assert "always()" in field(aggregate, "if")
    assert "toJSON(needs.*.result)" in aggregate
    assert "(failure|cancelled)" in aggregate
    assert REQUIRED == ("ci", "pr")


def test_no_job_tolerates_a_failure() -> None:
    for name in ("ci.yml", "pr-metadata.yml", "docs.yml"):
        assert "continue-on-error" not in workflow(name)


def test_editing_pull_request_text_rechecks_the_text_but_never_the_code() -> None:
    code = re.search(r"pull_request:\n    types: \[(.+)\]", workflow("ci.yml"))
    text = re.search(r"pull_request:\n    types: \[(.+)\]", workflow("pr-metadata.yml"))

    assert code and text
    assert "edited" not in code[1]
    assert {"opened", "synchronize", "reopened"} <= set(code[1].split(", "))
    assert {"edited", "ready_for_review", "converted_to_draft"} <= set(text[1].split(", "))


def test_full_runs_remain_and_nothing_is_published_by_a_merge() -> None:
    assert {"push", "schedule", "workflow_dispatch", "pull_request"} == triggers("ci.yml")
    assert {"push", "pull_request"} == triggers("pr-metadata.yml")
    assert {"push", "workflow_dispatch"} == triggers("docs.yml")
    assert {"workflow_dispatch"} == triggers("prerelease.yml")


def test_job_names_are_the_plain_job_keys() -> None:
    blocks = jobs("ci.yml")
    for job in ("changes", "platform", "docs", "workflows", "semgrep", "dependency-review", "ci"):
        assert field(blocks[job], "name") == job
    assert field(blocks["python"], "name") == "${{ matrix.name }}"
    assert re.findall(r"name: (python[\w-]*),", blocks["python"]) == ["python", "python-next"]


def test_documentation_permissions_remain_scoped_to_deployment() -> None:
    blocks = jobs("docs.yml")
    assert "    permissions:\n      contents: read" in blocks["docs"]
    assert "pages: write" not in blocks["docs"] and "id-token: write" not in blocks["docs"]
    assert "pages: write" in blocks["deploy"] and "id-token: write" in blocks["deploy"]
