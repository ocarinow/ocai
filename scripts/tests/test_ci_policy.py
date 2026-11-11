"""Exercise the actual workflow expressions against representative webhook events.

A deliberately small interpreter supports only the expression syntax used here;
unsupported syntax fails the test rather than silently inventing Actions behavior.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any
from typing import cast

import pytest

ROOT = Path(__file__).resolve().parents[2]


def expression(source: str, context: dict[str, Any]) -> Any:
    text = source.removeprefix("${{").removesuffix("}}").strip()
    text = text.replace("&&", " and ").replace("||", " or ")

    def visit(node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return context.get(node.id)
        if isinstance(node, ast.Attribute):
            parent = visit(node.value)
            return (
                cast("dict[str, Any]", parent).get(node.attr) if isinstance(parent, dict) else None
            )
        if isinstance(node, ast.BoolOp):
            values = [visit(value) for value in node.values]
            if isinstance(node.op, ast.And):
                return next((value for value in values if not value), values[-1])
            return next((value for value in values if value), values[-1])
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = visit(node.left), visit(node.comparators[0])
            if isinstance(node.ops[0], ast.Eq):
                return left == right
            if isinstance(node.ops[0], ast.NotEq):
                return left != right
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "format"
        ):
            template = str(visit(node.args[0]))
            return template.format(*(visit(arg) for arg in node.args[1:]))
        raise AssertionError(f"Unsupported workflow expression: {ast.dump(node)}")

    return visit(ast.parse(text, mode="eval").body)


def workflow_job(workflow: str, job: str) -> str:
    text = (ROOT / ".github/workflows" / workflow).read_text()
    body = text.split(f"\n  {job}:\n", 1)[1]
    return re.split(r"\n  [\w-]+:\n", body, maxsplit=1)[0]


def value(block: str, key: str) -> str:
    match = re.search(rf"^    {key}: (.+)$", block, re.MULTILINE)
    assert match
    return match[1]


@pytest.mark.parametrize(
    "action,changes,is_code",
    [
        ("opened", {}, True),
        ("synchronize", {}, True),
        ("reopened", {}, True),
        ("edited", {"body": {"from": "old"}}, False),
        ("edited", {"title": {"from": "old"}}, False),
        ("edited", {"base": {"ref": {"from": "old"}}}, True),
    ],
)
def test_metadata_cannot_write_code_check_names_or_cancel_code(
    action: str,
    changes: dict[str, Any],
    is_code: bool,
) -> None:
    context: dict[str, Any] = {
        "github": {
            "event_name": "pull_request",
            "run_id": 1,
            "event": {"action": action, "changes": changes, "pull_request": {"number": 123}},
        },
        "matrix": {"name": "python"},
    }
    for workflow, jobs in [
        ("ci.yml", ["python", "platform", "workflows", "semgrep", "dependency-review"]),
        ("docs.yml", ["docs"]),
    ]:
        for job in jobs:
            block = workflow_job(workflow, job)
            assert bool(expression(value(block, "if"), context)) == is_code
            name = expression(value(block, "name"), context)
            assert name == (job if is_code else f"{job} (metadata event)")
        text = (ROOT / ".github/workflows" / workflow).read_text()
        group = re.search(r"^  group: (.+)$", text, re.MULTILINE)
        assert group
        # Evaluate each interpolation in the actual concurrency group.
        rendered = re.sub(
            r"\$\{\{(.*?)\}\}", lambda m, ctx=context: str(expression(m[1], ctx)), group[1]
        )
        assert ("metadata" in rendered) == (not is_code)


def test_ready_events_only_run_metadata_and_board() -> None:
    for workflow in ["ci.yml", "docs.yml"]:
        text = (ROOT / ".github/workflows" / workflow).read_text()
        types = re.search(r"types: \[(.+)\]", text)
        assert types
        assert "ready_for_review" not in types[1]
        assert "converted_to_draft" not in types[1]
    metadata = (ROOT / ".github/workflows/pr-metadata.yml").read_text()
    assert "ready_for_review, converted_to_draft" in metadata
    assert "group: pr-metadata-" in metadata
    assert "ci_scope.py" not in metadata


def test_required_code_jobs_fail_if_selector_fails() -> None:
    # The selector is an ordinary failing step, never continue-on-error, and
    # precedes heavy work. There is no final success job masking a dependency failure.
    for workflow, jobs in [
        ("ci.yml", ["python", "platform", "workflows", "semgrep"]),
        ("docs.yml", ["docs"]),
    ]:
        for job in jobs:
            block = workflow_job(workflow, job)
            assert "continue-on-error" not in block
            assert f"scripts/ci_scope.py --suite {job}" in block
            assert "fetch-depth: 0" in block
            assert (
                "steps.go.outputs.run == 'true'" in block
                or "steps.changes.outputs.run == 'true'" in block
            )


def test_board_skips_body_edits_but_updates_title_and_base() -> None:
    condition = value(workflow_job("board-sync.yml", "sync"), "if")
    for field, expected in [("body", False), ("title", True), ("base", True)]:
        context: dict[str, Any] = {
            "github": {"event": {"action": "edited", "changes": {field: {"from": "old"}}}}
        }
        assert bool(expression(condition, context)) == expected


def test_push_schedule_dispatch_preserve_code_checks() -> None:
    for event in ["push", "schedule", "workflow_dispatch"]:
        context: dict[str, Any] = {
            "github": {"event_name": event, "event": {}},
            "matrix": {"name": "python-next"},
        }
        block = workflow_job("ci.yml", "python")
        assert expression(value(block, "if"), context)
        assert expression(value(block, "name"), context) == "python-next"


def test_board_body_event_cannot_supersede_pending_sync() -> None:
    text = (ROOT / ".github/workflows/board-sync.yml").read_text()
    group = re.search(r"^  group: (.+)$", text, re.MULTILINE)
    assert group
    for field, suffix in [("body", "metadata"), ("title", "updates"), ("base", "updates")]:
        context: dict[str, Any] = {
            "github": {"event": {"action": "edited", "changes": {field: {"from": "old"}}}}
        }
        rendered = re.sub(
            r"\$\{\{(.*?)\}\}", lambda m, ctx=context: str(expression(m[1], ctx)), group[1]
        )
        assert rendered == "board-sync-" + suffix


def test_nightly_docs_does_not_supersede_pages_and_manual_deploy_remains() -> None:
    text = (ROOT / ".github/workflows/docs.yml").read_text()
    group = re.search(r"^  group: (.+)$", text, re.MULTILINE)
    assert group
    for event, expected in [
        ("schedule", "docs-full-7"),
        ("push", "pages"),
        ("workflow_dispatch", "pages"),
    ]:
        context: dict[str, Any] = {
            "github": {"event_name": event, "event": {}, "run_id": 7},
            "needs": {"docs": {"outputs": {"pages_enabled": "true"}}},
        }
        assert expression(group[1], context) == expected
        condition = value(workflow_job("docs.yml", "deploy"), "if")
        assert bool(expression(condition, context)) == (event != "schedule")
