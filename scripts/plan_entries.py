"""Plan entries: read and check the work-unit entries under `docs/plans/`.

The plan table in `docs/plans/README.md` links each WU to its entry in a plan
file. This script parses those entries, checks them against
`docs/plans/WU-TEMPLATE.md`, and pre-fills a PR body from one::

    uv run python scripts/plan_entries.py lint                  # a gate step, offline
    uv run python scripts/plan_entries.py entry WU-NN [--json]  # one entry's bullets
    uv run python scripts/plan_entries.py pr-body WU-NN [--stacked-on N]

Nothing here talks to GitHub: the project board and its synchronization were
removed, and the plan files are the only record of planned work.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "docs" / "plans" / "README.md"
ROW_RE = re.compile(
    r"^\|\s*(WU-[0-9A-Za-z]+)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.+?)\s*\|\s*$"
)
LINK_RE = re.compile(r"\(([^)]+\.md)\)")
HEADING_RE = re.compile(r"^##\s+(WU-[0-9A-Za-z]+)\s*[—-]+\s*(.+?)\s*$")
BULLET_RE = re.compile(r"^- (?:\[[ x]\] )?\*\*([^:*]+?)(?: \(([^)]*)\))?:\*\*\s*(.*)$")
# Entries from this WU number on are held to the full template (the v2
# bullets); older open entries only need a Done bullet until they are
# backfilled. Lower this constant as entries are brought up to date.
TEMPLATE_V2_FROM = 82
MANDATORY_V2 = (
    "Status",
    "Context",
    "Goal",
    "Scope",
    "Non-goals",
    "Acceptance",
    "Done",
    "Deps",
    "Architecture",
    "Integration",
    "Design sketch",
    "Freeze",
    "Decision",
    "Risks",
    "Open",
    "Evidence",
    "Area",
    "Priority",
    "Tier",
    "Owner",
)
ADR_RE = re.compile(r"\bADR\s*\d{4}\b")
TEST_PATH_RE = re.compile(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.(?:py|json|yaml|yml|md)")
ID_RE = re.compile(r"^(WU-[0-9A-Za-z]+)\b")


@dataclass(frozen=True, slots=True)
class PlanRow:
    """One row of the plan table.

    Attributes:
        wu: The WU id, e.g. `WU-21`.
        title: The row title.
        done: Whether the status cell marks it ✅.
    """

    wu: str
    title: str
    done: bool
    milestone: str = ""
    file: str = ""


@dataclass(frozen=True, slots=True)
class Entry:
    """A parsed WU entry from a plan file.

    Attributes:
        sections: Bullet name → text (multi-line, fenced blocks kept), in file order.
        anchor: GitHub heading anchor of the entry.
    """

    sections: dict[str, str]
    anchor: str


def plan_text(ref: str | None) -> str:
    """The plan table text: from a git ref (`origin/main`) when given, else the working tree."""
    if ref:
        rel = PLAN.relative_to(ROOT).as_posix()
        return _gh_git("show", f"{ref}:{rel}")
    return PLAN.read_text(encoding="utf-8")


def _gh_git(*args: str) -> str:
    """Run git in the repo root and return stdout (raises on failure)."""
    proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def read_plan(ref: str | None = None) -> list[PlanRow]:
    """Parse the WU rows of the plan table (from `ref` when given)."""
    rows: list[PlanRow] = []
    for line in plan_text(ref).splitlines():
        m = ROW_RE.match(line)
        if m:
            link = LINK_RE.search(m.group(4))
            rows.append(
                PlanRow(
                    m.group(1),
                    m.group(2),
                    "✅" in m.group(5),
                    m.group(3).strip(),
                    link.group(1) if link else "",
                )
            )
    return rows


def _anchor(heading: str) -> str:
    """GitHub's slug for a Markdown heading."""
    text = re.sub(r"[^\w\s-]", "", heading.lower().replace("`", ""))
    return re.sub(r"\s", "-", text.strip())


def read_entry(row: PlanRow, ref: str | None = None) -> Entry | None:
    """Parse the WU's entry (heading + bullets) from the plan file the table row links."""
    if not row.file:
        return None
    if ref:
        try:
            text = _gh_git("show", f"{ref}:{(PLAN.parent / row.file).relative_to(ROOT).as_posix()}")
        except RuntimeError:
            return None
    else:
        path = PLAN.parent / row.file
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next(
        (i for i, ln in enumerate(lines) if (m := HEADING_RE.match(ln)) and m.group(1) == row.wu),
        None,
    )
    if start is None:
        return None
    sections: dict[str, str] = {}
    current: str | None = None
    fenced = False
    for ln in lines[start + 1 :]:
        if ln.startswith("```"):
            fenced = not fenced
        if not fenced and ln.startswith("## "):
            break
        m = None if fenced else BULLET_RE.match(ln)
        if m:
            name = m.group(1).strip()
            key = name if name not in sections else f"{name} ({m.group(2) or len(sections)})"
            topic = m.group(2) or ""
            sections[key] = (f"**{topic}** " if topic else "") + m.group(3).strip()
            current = key
        elif current is not None and (
            ln.startswith("  ") or fenced or ln.strip() == "" or ln.startswith("```")
        ):
            sections[current] += "\n" + (ln[2:] if ln.startswith("  ") and not fenced else ln)
    return Entry({k: v.strip() for k, v in sections.items()}, _anchor(lines[start].lstrip("# ")))


def wu_number(wu: str) -> int:
    """The numeric part of a WU id (`WU-44b` → 44; 0 when absent)."""
    m = re.search(r"(\d+)", wu)
    return int(m.group(1)) if m else 0


def _has(entry: Entry, name: str) -> bool:
    """Whether the entry has a bullet `name` (or `name (topic)`) with content."""
    return any(
        (k == name or k.startswith(name + " (")) and v.strip() for k, v in entry.sections.items()
    )


def lint_entry(row: PlanRow, entry: Entry | None) -> list[str]:
    """Findings for one WU entry against docs/plans/WU-TEMPLATE.md.

    Open rows (⬜/🔄) numbered from `TEMPLATE_V2_FROM` on must carry every
    mandatory bullet, a Design sketch with a code block (or an explicit
    "n/a"), an Acceptance list that names a test or fixture path, and an
    Alternatives considered bullet when a Decision is not backed by an ADR.
    Older open rows only need a Done bullet. Completed rows held to the
    template must carry Evidence with the gate line.

    Args:
        row: The plan table row.
        entry: The parsed entry, or None when the heading was not found.

    Returns:
        One finding per violation; empty when the entry complies.
    """
    if entry is None:
        # Completed rows from before the template have no entry; only open work is held to it.
        return [] if row.done else [f"{row.wu}: no entry heading in docs/plans/{row.file or '?'}"]
    v2 = wu_number(row.wu) >= TEMPLATE_V2_FROM
    if not v2:
        return [] if row.done or _has(entry, "Done") else [f"{row.wu}: entry has no Done bullet"]
    findings: list[str] = []
    if row.done:
        evidence = entry.sections.get("Evidence", "")
        if "gate:" not in evidence:
            findings.append(f"{row.wu}: row is ✅ but Evidence has no `gate: <sha>` line")
        return findings
    for name in MANDATORY_V2:
        if name == "Evidence":
            if "Evidence" not in entry.sections:
                findings.append(f"{row.wu}: entry has no Evidence bullet (write the placeholder)")
        elif not _has(entry, name):
            findings.append(f"{row.wu}: entry has no {name} bullet")
    sketch = entry.sections.get("Design sketch", "")
    if sketch and "```" not in sketch and not sketch.lower().startswith("n/a"):
        findings.append(f"{row.wu}: Design sketch needs a fenced code block or an explicit n/a")
    acceptance = entry.sections.get("Acceptance", "")
    if acceptance and not TEST_PATH_RE.search(acceptance):
        findings.append(f"{row.wu}: Acceptance names no test module, fixture, or recorded pair")
    decisions = [
        v for k, v in entry.sections.items() if k == "Decision" or k.startswith("Decision (")
    ]
    if (
        decisions
        and not all(ADR_RE.search(d) for d in decisions)
        and not _has(entry, "Alternatives considered")
    ):
        findings.append(
            f"{row.wu}: a Decision bullet is not backed by an ADR; add Alternatives considered"
        )
    return findings


def _first(entry: Entry | None, name: str) -> str:
    """First line of a bullet, stripped, or empty."""
    if entry is None:
        return ""
    return entry.sections.get(name, "").split("\n")[0].strip("` ").strip()


def _fill(body: str, heading: str, text: str) -> str:
    """Replace the placeholder paragraph under `## heading` with `text` (no-op when empty)."""
    if not text:
        return body
    marker = f"## {heading}\n"
    start = body.find(marker)
    if start < 0:
        return body
    start += len(marker)
    end = body.find("\n## ", start)
    end = len(body) if end < 0 else end
    section = body[start:end]
    lines = section.split("\n")
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("<") and s.endswith(">"):
            lines[i] = text
            break
    return body[:start] + "\n".join(lines) + body[end:]


def _section(entry: Entry | None, name: str) -> str:
    """Full text of a bullet (or the concatenation of its topics), or empty."""
    if entry is None:
        return ""
    parts = [v for k, v in entry.sections.items() if k == name or k.startswith(name + " (")]
    return "\n\n".join(p for p in parts if p.strip())


def cmd_entry(args: argparse.Namespace) -> int:
    """Print a WU entry's bullets (JSON with --json), for other scripts and for a quick look."""
    rows = {r.wu: r for r in read_plan()}
    row = rows.get(args.wu)
    entry = read_entry(row) if row else None
    if entry is None:
        print("{}" if args.json else f"no entry for {args.wu}")
        return 1
    if args.json:
        print(json.dumps(entry.sections, ensure_ascii=False))
    else:
        for key, text in entry.sections.items():
            print(f"### {key}\n{text}\n")
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    """Check every plan entry against the template, offline (a gate step)."""
    findings: list[str] = []
    rows = read_plan()
    for row in rows:
        findings.extend(lint_entry(row, read_entry(row)))
    if findings:
        print(f"PLAN ENTRIES: {len(findings)} finding(s) (docs/plans/WU-TEMPLATE.md)")
        for f in findings:
            print("  - " + f)
        return 1
    held = sum(1 for r in rows if wu_number(r.wu) >= TEMPLATE_V2_FROM)
    print(f"plan entries: ok ({len(rows)} rows; {held} held to the full template)")
    return 0


def cmd_pr_body(args: argparse.Namespace) -> int:
    """Print a PR body from the template, pre-filled from the WU entry."""
    rows = {r.wu: r for r in read_plan()}
    row = rows.get(args.wu)
    if row is None:
        print(f"no plan row for {args.wu}")
        return 1
    entry = read_entry(row)
    body = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    anchor = entry.anchor if entry else "wu-__"
    body = body.replace(
        "WU-__ — <title from docs/plans/>. Entry: docs/plans/<file>.md#wu-__.",
        f"{row.wu} — {row.title}. Entry: docs/plans/{row.file or '<file>.md'}#{anchor}.",
    )
    why = "\n\n".join(x for x in (_section(entry, "Context"), _section(entry, "Goal")) if x)
    body = _fill(body, "Why", why)
    body = _fill(body, "What did not change", _section(entry, "Non-goals"))
    body = _fill(body, "Design", _section(entry, "Design sketch"))
    body = _fill(body, "Before / after", _section(entry, "Before / after"))
    body = _fill(body, "Try it", _section(entry, "Reproduce"))
    body = _fill(body, "Alternatives considered", _section(entry, "Alternatives considered"))
    acceptance = [
        ln.strip()[2:]
        for ln in _section(entry, "Acceptance").splitlines()
        if ln.strip().startswith("- ")
    ]
    if acceptance:
        boxes = "\n".join(f"- [ ] {item}" for item in acceptance)
        body = re.sub(
            r"- \[ \] <behavior>[^\n]*\n(?:- \[ \] <behavior>[^\n]*\n)*", boxes + "\n", body
        )
    arch = _first(entry, "Architecture")
    if arch:
        body = body.replace("§__", arch)
    if args.stacked_on:
        body = body.replace(
            "<!-- Stacked on #N  (keep this line only when the base branch is not main) -->",
            f"Stacked on #{args.stacked_on}.",
        )
    print(body)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Command-line arguments, defaulting to `sys.argv[1:]`.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Read and check the plan entries.")
    sub = parser.add_subparsers(dest="command", required=True)
    p_body = sub.add_parser("pr-body", help="print a PR body pre-filled from the WU entry")
    p_body.add_argument("wu")
    p_body.add_argument("--stacked-on", type=int, default=0, help="parent PR number when stacked")
    p_body.set_defaults(func=cmd_pr_body)
    p_lint = sub.add_parser("lint", help="check every plan entry against the template (offline)")
    p_lint.set_defaults(func=cmd_lint)
    p_entry = sub.add_parser("entry", help="print one WU entry's bullets (offline)")
    p_entry.add_argument("wu")
    p_entry.add_argument("--json", action="store_true")
    p_entry.set_defaults(func=cmd_entry)
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except RuntimeError as exc:
        print(f"plan: {str(exc).splitlines()[0] if str(exc) else 'git failed'}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
