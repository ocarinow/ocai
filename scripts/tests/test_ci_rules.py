"""Ruleset reconciliation must never erase unrelated protections."""

import copy
from typing import Any

import pytest
from ci_rules import REQUIRED
from ci_rules import reconcile


def ruleset(checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": 1,
        "name": "main",
        "enforcement": "active",
        "target": "branch",
        "bypass_actors": [],
        "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
        "rules": [
            {"type": "deletion"},
            {
                "type": "required_status_checks",
                "parameters": {
                    "required_status_checks": checks,
                    "strict_required_status_checks_policy": False,
                },
            },
        ],
    }


def test_only_the_aggregate_checks_stay_required_and_other_rules_are_untouched() -> None:
    current = ruleset(
        [
            {"context": "python"},
            {"context": "platform"},
            {"context": "ci", "integration_id": 15368},
        ]
    )
    original = copy.deepcopy(current)

    desired = reconcile(current)

    assert current == original
    assert "id" not in desired
    assert desired["rules"][0] == current["rules"][0]
    assert desired["conditions"] == current["conditions"]
    parameters = desired["rules"][1]["parameters"]
    assert parameters["required_status_checks"] == [
        {"context": "ci", "integration_id": 15368},
        {"context": "pr"},
    ]
    assert parameters["strict_required_status_checks_policy"] is True


def test_reconciling_twice_changes_nothing() -> None:
    once = reconcile(ruleset([{"context": name} for name in REQUIRED]))

    assert reconcile(once) == once


def test_a_ruleset_without_required_checks_is_refused() -> None:
    with pytest.raises(ValueError, match="No required-status-checks rule"):
        reconcile({"rules": [{"type": "deletion"}]})
