"""Ruleset reconciliation must never erase unrelated protections."""

import copy
from typing import Any

import pytest
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
    assert checks[:2] == current["rules"][1]["parameters"]["required_status_checks"]
    assert set(REQUIRED) <= {check["context"] for check in checks}
    assert reconcile(desired) == desired


def test_missing_rule_is_not_silently_created() -> None:
    with pytest.raises(ValueError, match="No required"):
        reconcile({"rules": []})
