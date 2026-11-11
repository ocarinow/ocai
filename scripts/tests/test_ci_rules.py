"""Ruleset reconciliation must never erase unrelated protections."""

import copy
from typing import Any

import pytest
from ci_rules import RENAMED
from ci_rules import REQUIRED
from ci_rules import reconcile


def test_update_preserves_other_rules_checks_and_bindings() -> None:
    current: dict[str, Any] = {
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
                    "required_status_checks": [
                        {"context": "custom", "integration_id": 42},
                        {"context": "python", "integration_id": 15368},
                    ],
                    "strict_required_status_checks_policy": True,
                },
            },
        ],
    }
    original = copy.deepcopy(current)
    desired = reconcile(current)
    assert current == original
    assert "id" not in desired
    assert desired["rules"][0] == current["rules"][0]
    assert desired["conditions"] == current["conditions"]
    checks = desired["rules"][1]["parameters"]["required_status_checks"]
    assert checks[0] == {"context": "custom", "integration_id": 42}
    assert checks[1] == {"context": "Code checks / python", "integration_id": 15368}
    assert set(REQUIRED) <= {check["context"] for check in checks}
    assert reconcile(desired) == desired


def test_missing_rule_is_not_silently_created() -> None:
    with pytest.raises(ValueError, match="No required"):
        reconcile({"rules": []})


def test_every_legacy_quality_check_is_renamed_one_for_one() -> None:
    current: dict[str, Any] = {
        "rules": [
            {
                "type": "required_status_checks",
                "parameters": {
                    "required_status_checks": [
                        {"context": name, "integration_id": 15368}
                        for name in [*RENAMED, "privacy", "pr-hygiene"]
                    ],
                    "strict_required_status_checks_policy": True,
                },
            }
        ]
    }
    desired = reconcile(current)
    checks = desired["rules"][0]["parameters"]["required_status_checks"]
    assert len(checks) == 9
    assert {check["context"] for check in checks} == set(REQUIRED)
    assert all(check["integration_id"] == 15368 for check in checks)
    assert desired["rules"][0]["parameters"]["strict_required_status_checks_policy"] is True
