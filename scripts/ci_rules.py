"""Prepare a minimal ruleset update after the CI workflows have landed.

Default: check drift without mutation. --output writes the exact reviewable
request body; applying it remains an explicit repository administration action.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
from pathlib import Path
from typing import Any

REQUIRED = (
    "python",
    "python-next",
    "privacy",
    "pr-hygiene",
    "platform",
    "docs",
    "workflows",
    "semgrep",
    "dependency-review",
)


def reconcile(current: dict[str, Any]) -> dict[str, Any]:
    """Preserve existing rules/check bindings while adding missing quality gates."""
    result = {
        key: copy.deepcopy(current[key])
        for key in ("name", "target", "enforcement", "bypass_actors", "conditions", "rules")
        if key in current
    }
    for rule in result["rules"]:
        if rule["type"] != "required_status_checks":
            continue
        parameters = rule["parameters"]
        checks = parameters["required_status_checks"]
        names = {check["context"] for check in checks}
        checks.extend({"context": name} for name in REQUIRED if name not in names)
        parameters["strict_required_status_checks_policy"] = True
        return result
    raise ValueError("No required-status-checks rule found; refusing to invent a ruleset")


def main() -> int:
    """Check live enforcement and optionally write a reviewable PUT body."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="ocarinow/ocai")
    parser.add_argument("--ruleset", type=int, default=26964282)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    raw = subprocess.check_output(
        ("gh", "api", f"repos/{args.repo}/rulesets/{args.ruleset}"), text=True
    )
    current: dict[str, Any] = json.loads(raw)
    desired = reconcile(current)
    changed = any(current.get(key) != value for key, value in desired.items())
    if args.output:
        args.output.write_text(json.dumps(desired, indent=2) + "\n")
    print("Required checks: " + ", ".join(REQUIRED))
    print("ruleset: drift (review and apply after merge)" if changed else "ruleset: current")
    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
