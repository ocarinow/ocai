"""Prepare a one-to-one required-check migration for a verified workflow rollout.

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

# Reusable workflows prefix leaf checks with their static caller label.
# These are one-to-one renames, never an alternative or weaker check set.
RENAMED = {
    "python": "Code checks / python",
    "python-next": "Code checks / python-next",
    "platform": "Code checks / platform",
    "docs": "Documentation / docs",
    "workflows": "Code checks / workflows",
    "semgrep": "Code checks / semgrep",
    "dependency-review": "Code checks / dependency-review",
}
REQUIRED = (*RENAMED.values(), "privacy", "pr-hygiene")


def reconcile(current: dict[str, Any]) -> dict[str, Any]:
    """Rename known checks without changing their bindings or unrelated protections."""
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
        for check in checks:
            check["context"] = RENAMED.get(check["context"], check["context"])
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
    print(
        "ruleset: drift (review the verified workflow rollout)" if changed else "ruleset: current"
    )
    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
