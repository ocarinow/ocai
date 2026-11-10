"""PR hygiene: a pull request must follow the template, and its title must name its work unit.

Run by the `pr-hygiene` CI job on every pull request event and locally by
`task pr:ready` before a draft is marked ready::

    uv run python scripts/pr_check.py --title T --body-file F [--draft] [--base BRANCH]
    uv run python scripts/pr_check.py --pr 77          # fetch title, body, draft, base with gh

Rules (AGENTS.md "Working alongside other agents" and "The board"):

- the title starts with the WU id, `WU-NN: <imperative title>`, so the board
  card follows it; housekeeping PRs that are not a WU use a `<Topic>: ` prefix;
- the body carries every section of `.github/PULL_REQUEST_TEMPLATE.md`, from
  the first commit (drafts included) — `task pr:draft` generates it;
- a PR that is ready for review has no unchecked box left (`- [ ]`): check it
  or replace it with a one-line reason, and a non-empty Verification block;
- a stacked PR (base other than `main`) says `Stacked on #N` in its body;
- the privacy rule holds for title and body (`scripts/privacy_check.py` runs
  separately in CI).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"
TITLE_RE = re.compile(r"^(WU-[0-9A-Za-z]+): \S|^[A-Z][A-Za-z0-9 /&-]{1,40}: \S")
UNCHECKED_RE = re.compile(r"^\s*- \[ \]", re.MULTILINE)
STACKED_RE = re.compile(r"\bStacked on #\d+", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(
    r"WU-__|§__|<title from docs/plans/>|<two or three sentences[^>]*>|<imperative title>"
)


def template_headings() -> list[str]:
    """The `## ` headings of the PR template, in order."""
    return [
        ln.strip()
        for ln in TEMPLATE.read_text(encoding="utf-8").splitlines()
        if ln.startswith("## ")
    ]


def check(title: str, body: str, draft: bool, base: str) -> list[str]:
    """Return the findings for one PR; empty when it complies."""
    findings: list[str] = []
    if not TITLE_RE.match(title):
        findings.append("title must be `WU-NN: <imperative title>` (housekeeping: `<Topic>: …`)")
    headings = template_headings()
    missing = [h for h in headings if h not in body]
    if missing:
        findings.append("body is missing template sections: " + ", ".join(missing))
    if base and base != "main" and not STACKED_RE.search(body):
        findings.append(f"base is `{base}`: the body must say `Stacked on #N`")
    if not draft:
        if UNCHECKED_RE.search(body):
            findings.append(
                "ready for review but unchecked boxes remain: check or replace with a reason"
            )
        if PLACEHOLDER_RE.search(body):
            findings.append("ready for review but template placeholders remain (<…>, WU-__, §__)")
        ver = body.split("## Verification", 1)
        if len(ver) == 2 and not re.search(r"```[\s\S]*?\S[\s\S]*?```|\bok\b|passed", ver[1]):
            findings.append("Verification section has no pasted gate output")
    return findings


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Command-line arguments, defaulting to `sys.argv[1:]`.

    Returns:
        0 when the PR complies, 1 otherwise.
    """
    parser = argparse.ArgumentParser(description="Check a PR title and body against the template.")
    parser.add_argument("--pr", type=int, help="fetch the PR with gh instead of passing fields")
    parser.add_argument("--title", default="")
    parser.add_argument("--body-file")
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--base", default="main")
    args = parser.parse_args(argv)

    title, body, draft, base = args.title, "", args.draft, args.base
    if args.pr:
        raw = subprocess.run(
            ["gh", "pr", "view", str(args.pr), "--json", "title,body,isDraft,baseRefName"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        data = json.loads(raw)
        title, body = str(data["title"]), str(data["body"] or "")
        draft, base = bool(data["isDraft"]), str(data["baseRefName"])
    elif args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")

    findings = check(title, body, draft, base)
    label = "draft" if draft else "ready"
    if findings:
        print(f"PR HYGIENE ({label}, base {base}): {len(findings)} finding(s)")
        for f in findings:
            print("  - " + f)
        print(
            "Template: .github/PULL_REQUEST_TEMPLATE.md; generate a body with `task pr:body -- WU-NN`."
        )
        return 1
    print(f"pr hygiene: ok ({label}, base {base})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
