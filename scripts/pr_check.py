"""PR hygiene: a pull request must follow the template, and its title must name its work unit.

Run by the `pr-hygiene` CI job on every pull request event and locally by
`task pr:ready` before a draft is marked ready::

    uv run python scripts/pr_check.py --title T --body-file F [--draft] [--base B] [--author L]
    uv run python scripts/pr_check.py --pr 77   # title, body, draft, base, author, files via gh

Rules (AGENTS.md "Working alongside other agents" and "The board"):

- the title starts with the WU id, `WU-NN: <imperative title>`, so the board
  card follows it; housekeeping PRs that are not a WU use a `<Topic>: ` prefix;
- the body carries every mandatory section of `.github/PULL_REQUEST_TEMPLATE.md`
  from the first commit (drafts included) — `task pr:body` generates it. The
  optional sections (Design, Before / after, Try it, Alternatives considered)
  may be omitted, except Design when the diff touches a frozen-candidate
  surface and Try it when the WU entry has a Reproduce bullet;
- once ready for review every present section has content (not a template
  placeholder), How to review names at least one file of the diff, Evidence
  names at least one test or fixture path that exists, Follow-ups is "none" or
  lists ids — and "none" is a finding when the diff adds a TODO —, no unchecked
  box remains, and the Verification block is a real gate summary: an `ok` line
  for every step the gate would run for these files, `all checks passed`, and a
  `gate: <sha>` line whose commit is an ancestor of the PR head;
- a stacked PR (base other than `main`) says `Stacked on #N` in its body;
- a PR opened by a dependency bot (`dependabot[bot]`) has a generated body:
  only its title is checked (`Deps: …`), the template is not required;
- the privacy rule holds for title and body (`scripts/privacy_check.py` runs
  separately in CI).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from typing import cast

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"
TITLE_RE = re.compile(r"^(WU-[0-9A-Za-z]+): \S|^[A-Z][A-Za-z0-9 /&-]{1,40}: \S")
WU_RE = re.compile(r"^(WU-[0-9A-Za-z]+): ")
UNCHECKED_RE = re.compile(r"^\s*- \[ \]", re.MULTILINE)
STACKED_RE = re.compile(r"\bStacked on #\d+", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"WU-__|§__|#wu-__|<[a-z][^>\n]{3,}>")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
PATH_RE = re.compile(
    r"`?((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.[A-Za-z0-9]+)(?:::[A-Za-z0-9_\[\]\-:.]+)?`?"
)
GATE_LINE_RE = re.compile(r"^gate: ([0-9a-f]{7,40})(\+dirty)?\b", re.MULTILINE)
STEP_LINE_RE = re.compile(r"^\s*(ok|skip|FAIL)\s{2,}(.+?)\s{2,}[0-9.]+s\s*$", re.MULTILINE)
BOT_AUTHORS = frozenset({"dependabot[bot]"})
OPTIONAL_SECTIONS = ("## Design", "## Before / after", "## Try it", "## Alternatives considered")
# Architecture §3.1: the frozen-candidate surfaces. A diff touching them must
# carry a Design section (the surface as it reads in code).
FROZEN_PREFIXES = (
    "spec/schema/",
    "python/packages/ocai-core/src/ocai/core/",
    "python/packages/ocai-core/src/ocai/chat/",
)
TODO_RE = re.compile(r"^\+.*\b(TODO|FIXME|XXX)\b")


@dataclass(frozen=True, slots=True)
class Pull:
    """What the check knows about one pull request.

    Attributes:
        title: The PR title.
        body: The PR body (Markdown).
        draft: Whether the PR is still a draft.
        base: The base branch name.
        author: The author's login (bots get a title-only check).
        files: Repo-relative paths the PR changes, when known.
        added_lines: Added diff lines (`+…`), when known, for the TODO rule.
    """

    title: str
    body: str
    draft: bool
    base: str = "main"
    author: str = ""
    files: tuple[str, ...] = field(default=())
    added_lines: tuple[str, ...] = field(default=())


def template_headings() -> list[str]:
    """The `## ` headings of the PR template, in order."""
    return [
        ln.strip()
        for ln in TEMPLATE.read_text(encoding="utf-8").splitlines()
        if ln.startswith("## ")
    ]


def sections(body: str) -> dict[str, str]:
    """Split a body into `## heading` → content (HTML comments removed)."""
    out: dict[str, str] = {}
    current: str | None = None
    for ln in COMMENT_RE.sub("", body).splitlines():
        if ln.startswith("## "):
            current = ln.strip()
            out[current] = ""
        elif current is not None:
            out[current] += ln + "\n"
    return out


def has_content(text: str) -> bool:
    """Whether a section holds at least one line that is not a template placeholder."""
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("```"):
            continue
        if PLACEHOLDER_RE.fullmatch(s) or (s.startswith("<") and s.endswith(">")):
            continue
        return True
    return False


def paths_in(text: str) -> list[str]:
    """Path-like tokens (optionally with a `::test` suffix) mentioned in a section."""
    return [m.group(1) for m in PATH_RE.finditer(text)]


def _run(argv: list[str]) -> str:
    """Run a command in the repo root and return stdout (empty on failure)."""
    proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=False)
    return proc.stdout if proc.returncode == 0 else ""


def gate_steps() -> list[dict[str, Any]]:
    """The gate's step names and path prefixes, from `scripts/check.py --list-json`."""
    raw = _run([sys.executable, "scripts/check.py", "--list-json"])
    if not raw:
        return []
    data: Any = json.loads(raw)
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []  # pyright: ignore[reportUnknownVariableType]


def entry_sections(wu: str) -> dict[str, str]:
    """The WU entry's bullets, from `scripts/board_sync.py entry WU-NN --json` (empty if none)."""
    raw = _run([sys.executable, "scripts/board_sync.py", "entry", wu, "--json"])
    if not raw:
        return {}
    data: Any = json.loads(raw)
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]


def is_ancestor(sha: str) -> bool:
    """Whether `sha` is reachable from HEAD (the gate ran on this branch's history)."""
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def check_verification(text: str, files: tuple[str, ...]) -> list[str]:
    """The Verification block must be a real gate summary for these files."""
    findings: list[str] = []
    steps = {m.group(2).strip(): m.group(1) for m in STEP_LINE_RE.finditer(text)}
    if not steps or "all checks passed" not in text:
        findings.append(
            "Verification has no pasted gate summary (step lines + `all checks passed`)"
        )
        return findings
    for step in gate_steps():
        name = str(step.get("name", ""))
        prefixes = [str(p) for p in step.get("paths", [])]  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
        relevant = not prefixes or any(f == p or f.startswith(p) for f in files for p in prefixes)
        status = steps.get(name)
        if status is None:
            findings.append(f"Verification is missing the `{name}` step (stale gate output?)")
        elif status == "FAIL":
            findings.append(f"Verification shows `{name}` FAILED")
        elif status == "skip" and relevant and files:
            findings.append(
                f"Verification skipped `{name}` but this PR touches its tree; rerun with --all"
            )
    m = GATE_LINE_RE.search(text)
    if m is None:
        findings.append("Verification has no `gate: <sha>` line (rerun scripts/check.py)")
    else:
        if m.group(2):
            findings.append("Verification ran on a dirty tree (`+dirty`): commit, rerun, repaste")
        if not is_ancestor(m.group(1)):
            findings.append(f"Verification commit {m.group(1)} is not in this PR's history")
    return findings


def check(pull: Pull) -> list[str]:
    """Return the findings for one PR; empty when it complies.

    Args:
        pull: Everything known about the PR.

    Returns:
        One finding per violated rule.
    """
    findings: list[str] = []
    if not TITLE_RE.match(pull.title):
        findings.append("title must be `WU-NN: <imperative title>` (housekeeping: `<Topic>: …`)")
    if pull.author in BOT_AUTHORS:
        return findings
    headings = template_headings()
    present = sections(pull.body)
    missing = [h for h in headings if h not in present and h not in OPTIONAL_SECTIONS]
    if missing:
        findings.append("body is missing template sections: " + ", ".join(missing))
    if pull.base and pull.base != "main" and not STACKED_RE.search(pull.body):
        findings.append(f"base is `{pull.base}`: the body must say `Stacked on #N`")
    touches_frozen = any(f.startswith(p) for f in pull.files for p in FROZEN_PREFIXES)
    if touches_frozen and "## Design" not in present:
        findings.append(
            "diff touches a frozen-candidate surface (spec/schema, ocai.core, ocai.chat): "
            "a `## Design` section is required"
        )
    wu = WU_RE.match(pull.title)
    entry = entry_sections(wu.group(1)) if wu else {}
    if wu and not entry:
        findings.append(
            f"{wu.group(1)} has no entry in docs/plans/ (write it with wu-define first)"
        )
    if entry.get("Reproduce") and "## Try it" not in present:
        findings.append("the WU entry has a Reproduce bullet: a `## Try it` section is required")
    if pull.draft:
        return findings

    for heading, text in present.items():
        if heading == "## Verification":
            continue
        if not has_content(text):
            findings.append(f"{heading} has no content (placeholder or empty)")
    if UNCHECKED_RE.search(pull.body):
        findings.append(
            "ready for review but unchecked boxes remain: check or replace with a reason"
        )
    if PLACEHOLDER_RE.search(COMMENT_RE.sub("", pull.body)):
        findings.append("ready for review but template placeholders remain (<…>, WU-__, §__)")
    review = present.get("## How to review", "")
    review_paths = paths_in(review)
    if not review_paths:
        findings.append("How to review names no file: give the reader a place to start")
    elif pull.files and not any(p in pull.files for p in review_paths):
        findings.append("How to review names no file that this PR changes")
    evidence_paths = paths_in(present.get("## Evidence", ""))
    if not evidence_paths:
        findings.append("Evidence names no test, fixture, or recorded pair")
    else:
        missing_paths = [p for p in evidence_paths if not (ROOT / p).exists()]
        if missing_paths:
            findings.append("Evidence names paths that do not exist: " + ", ".join(missing_paths))
    follow = present.get("## Follow-ups", "").strip().lower()
    adds_todo = any(TODO_RE.match(ln) for ln in pull.added_lines)
    if adds_todo and (not follow or follow.startswith("none")):
        findings.append(
            "the diff adds a TODO/FIXME but Follow-ups says none: list it as a gap or WU"
        )
    findings.extend(check_verification(present.get("## Verification", ""), pull.files))
    return findings


def _diff_against(base: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Changed files and added lines of this branch against `origin/<base>`."""
    names = _run(["git", "diff", "--name-only", f"origin/{base}...HEAD"])
    diff = _run(["git", "diff", "--unified=0", f"origin/{base}...HEAD"])
    added = tuple(ln for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++"))
    return tuple(ln for ln in names.splitlines() if ln), added


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
    parser.add_argument(
        "--author", default="", help="PR author login (bots get a title-only check)"
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="read changed files and added lines from git against origin/<base>",
    )
    args = parser.parse_args(argv)

    if args.pr:
        raw = _run(
            [
                "gh",
                "pr",
                "view",
                str(args.pr),
                "--json",
                "title,body,isDraft,baseRefName,author,files",
            ]
        )
        if not raw:
            print(f"could not fetch PR #{args.pr} with gh")
            return 1
        data: dict[str, Any] = json.loads(raw)
        files_raw: Any = data.get("files", [])
        files: tuple[str, ...] = ()
        if isinstance(files_raw, list):
            files = tuple(
                str(cast("dict[str, Any]", item)["path"])
                for item in cast("list[object]", files_raw)
                if isinstance(item, dict)
            )
        diff = _run(["gh", "pr", "diff", str(args.pr)])
        added = tuple(
            ln for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++")
        )
        author_raw: Any = data.get("author", {})
        pull = Pull(
            title=str(data["title"]),
            body=str(data["body"] or ""),
            draft=bool(data["isDraft"]),
            base=str(data["baseRefName"]),
            author=(
                str(cast("dict[str, Any]", author_raw).get("login", ""))
                if isinstance(author_raw, dict)
                else ""
            ),
            files=files,
            added_lines=added,
        )
    else:
        body = Path(args.body_file).read_text(encoding="utf-8") if args.body_file else ""
        files, added = _diff_against(args.base) if args.diff else ((), ())
        pull = Pull(args.title, body, args.draft, args.base, args.author, files, added)

    findings = check(pull)
    label = "draft" if pull.draft else "ready"
    if pull.author in BOT_AUTHORS:
        label += f", bot {pull.author}"
    if findings:
        print(f"PR HYGIENE ({label}, base {pull.base}): {len(findings)} finding(s)")
        for f in findings:
            print("  - " + f)
        print(
            "Template: .github/PULL_REQUEST_TEMPLATE.md; body generator: `task pr:body -- WU-NN`."
        )
        return 1
    print(f"pr hygiene: ok ({label}, base {pull.base}, {len(pull.files)} file(s) known)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
