"""Board sync: the GitHub Project is a view of the plan and the PRs, nothing more.

Cards are project items, never issues. Before a WU has a pull request its
card is a **draft item** titled `WU-NN: <title>` exactly as the plan row;
once a PR titled `WU-NN: …` exists, **the PR itself becomes the WU's item**
(reviewers, checks, and review state are then native on the board) and the
draft is removed. The card body and its
fields (Program, Area, Priority, Tier, Owner, Kind, PR, Plan) are generated
from the WU entry in the plan file (`docs/plans/WU-TEMPLATE.md`); Status is
derived, never dragged::

    uv run python scripts/board_sync.py sync                   # report, exit 1 when out of sync
    uv run python scripts/board_sync.py sync --apply           # create missing cards, set statuses
    uv run python scripts/board_sync.py add wu "WU-NN: title"  # one card now (sync does it too)
    uv run python scripts/board_sync.py add decision "Decision: …" --body-file F
    uv run python scripts/board_sync.py add gap "Gap: …" --body-file F
    uv run python scripts/board_sync.py set WU-NN --owner Claude --tier "1 chat …"
    uv run python scripts/board_sync.py pr-body WU-NN [--stacked-on N]   # PR body from the entry

Derivation for a WU card: plan row ✅ or its PR merged → Done; open draft
PR → In progress; open PR ready for review → In review; otherwise Defined.
A PR belongs to a WU when its title starts with the WU id. A card the
maintainer moved to "Blocked on maintainer" stays there until its PR merges.
Cards whose title does not start with `WU-` (decisions, gaps) are never
moved by the sync. Findings (exit 1): a plan row marked ✅ with no merged PR
and a card that is not Done; a card with no plan row; a draft PR untouched
for `--stale-days`.

Needs a token with the `project` scope (`gh auth refresh -s project`; in CI
the `BOARD_TOKEN` secret) and the project number (`--project` or the
`BOARD_PROJECT_NUMBER` environment variable).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "docs" / "plans" / "README.md"
REPO = "ocarinow/ocai"
ORG = REPO.split("/")[0]
STATUSES = ("Defined", "In progress", "In review", "Blocked on maintainer", "Done")
ROW_RE = re.compile(
    r"^\|\s*(WU-[0-9A-Za-z]+)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.+?)\s*\|\s*$"
)
LINK_RE = re.compile(r"\(([^)]+\.md)\)")
HEADING_RE = re.compile(r"^##\s+(WU-[0-9A-Za-z]+)\s*[—-]+\s*(.+?)\s*$")
BULLET_RE = re.compile(r"^- (?:\[[ x]\] )?\*\*([^:*]+?)(?: \(([^)]*)\))?:\*\*\s*(.*)$")
BLOB = f"https://github.com/{REPO}/blob/main/"
PROGRAMS = {
    "M1": "M1",
    "M2": "M2",
    "M3": "M3",
    "Modernization": "Modernization",
    "Gateway": "Gateway",
    "Integration": "Integration",
    "Platform MVP": "Platform MVP",
    "Platform design": "Platform MVP",
    "Platform": "Platform MVP",
    "Docs": "Docs",
}
AREA_HINTS = (
    ("platform/", "platform"),
    ("docs/", "docs"),
    ("spec/", "spec"),
    ("scripts/", "tooling"),
    ("tasks/", "tooling"),
    (".agents", "tooling"),
    ("ocai.openai", "plugin: openai"),
    ("openai/", "plugin: openai"),
    ("ocai.anthropic", "plugin: anthropic"),
    ("anthropic/", "plugin: anthropic"),
    ("deepseek", "plugin: other"),
    ("qwen", "plugin: other"),
    ("kimi", "plugin: other"),
    ("glm", "plugin: other"),
    ("cohere", "plugin: other"),
    ("bedrock", "plugin: other"),
    ("converse", "plugin: other"),
    ("azure", "plugin: other"),
    ("vertex", "plugin: other"),
    ("vllm", "plugin: other"),
    ("openrouter", "plugin: other"),
    ("groq", "plugin: other"),
    ("satellite", "satellite"),
    ("otel", "satellite"),
    ("opentelemetry", "satellite"),
    ("cost", "satellite"),
    ("ocai.wire", "wire"),
    ("wire/", "wire"),
    ("transport", "wire"),
    ("sigv4", "wire"),
    ("credential", "wire"),
    ("eventstream", "wire"),
    ("runtime/", "runtime"),
    ("ocai.runtime", "runtime"),
    ("observe", "runtime"),
    ("interceptor", "runtime"),
    ("policy", "runtime"),
    ("driver", "runtime"),
    ("ratelimit", "runtime"),
    ("rate-limit", "runtime"),
    ("convert/", "convert"),
    ("ocai.convert", "convert"),
    ("catalog", "convert"),
    ("profile", "convert"),
    ("descriptor", "convert"),
    ("edges", "convert"),
    ("codec", "convert"),
    ("chat/types", "chat IR"),
    ("cachehint", "chat IR"),
    ("cacheconfig", "chat IR"),
    ("chatconfig", "chat IR"),
    ("ocai.chat", "chat IR"),
    ("annotation", "chat IR"),
    ("chatrequest", "chat IR"),
    ("core/", "core"),
    ("ocai.core", "core"),
)
# Card body order = docs/plans/WU-TEMPLATE.md order. Optional bullets render
# only when the entry has them.
BODY_ORDER = (
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
    "Before / after",
    "Alternatives considered",
    "Reproduce",
    "Freeze",
    "Decision",
    "Risks",
    "Dependency impact",
    "Open",
    "Evidence",
)
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


@dataclass(frozen=True, slots=True)
class Pull:
    """One pull request whose title starts with a WU id.

    Attributes:
        number: PR number.
        state: `OPEN`, `MERGED`, or `CLOSED`.
        draft: Whether it is a draft.
        updated_at: Last update timestamp.
    """

    number: int
    state: str
    draft: bool
    updated_at: datetime

    @property
    def url(self) -> str:
        """The PR's GitHub URL."""
        return f"https://github.com/{REPO}/pull/{self.number}"


@dataclass(frozen=True, slots=True)
class Item:
    """One project item.

    Attributes:
        id: The project item node id.
        title: The card title.
        status: The current Status option name, or None.
        kind: `DraftIssue`, `Issue`, or `PullRequest`.
    """

    id: str
    title: str
    status: str | None
    kind: str
    content_id: str = ""
    body: str = ""
    fields: dict[str, str] = field(default_factory=dict[str, str])
    number: int = 0


def _gh(*args: str) -> str:
    """Run `gh` and return stdout, raising on failure.

    Args:
        *args: Arguments after `gh`.

    Returns:
        Captured stdout.

    Raises:
        RuntimeError: When `gh` exits non-zero.
    """
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"gh {' '.join(args)} failed")
    return proc.stdout


def _graphql(query: str, **variables: str | int) -> dict[str, Any]:
    """Run a GraphQL query or mutation through `gh api graphql`."""
    args = ["api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        args += ["-F", f"{key}={value}"]
    data: dict[str, Any] = json.loads(_gh(*args))
    if "errors" in data:
        raise RuntimeError(str(data["errors"]))
    return data["data"]


def _when(value: str) -> datetime:
    """Parse a GitHub ISO timestamp."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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


def infer_area(entry: Entry | None) -> str:
    """The Area bullet, else a guess from the Scope paths."""
    if entry is None:
        return ""
    if entry.sections.get("Area"):
        return entry.sections["Area"].split("\n")[0].strip("` ").lower()
    scope = (entry.sections.get("Scope", "") + " " + entry.sections.get("Goal", "")).lower()
    for hint, area in AREA_HINTS:
        if hint in scope:
            return area
    return ""


def card_body(row: PlanRow, entry: Entry | None, pull: Pull | None) -> str:
    """Render the card body from the entry, in template order."""
    parts: list[str] = []
    if entry is None:
        parts.append(
            f"_No entry found for {row.wu} in `docs/plans/{row.file or '?'}`; "
            "write it with the wu-define skill (docs/plans/WU-TEMPLATE.md)._"
        )
    else:
        for name in BODY_ORDER:
            for key, text in entry.sections.items():
                if key == name or key.startswith(name + " ("):
                    parts.append(f"### {key}\n\n{text}")
    links = [
        f"Plan: {BLOB}docs/plans/{row.file}#{entry.anchor}" if entry and row.file else "",
        f"PR: {pull.url}" if pull else "PR: none yet",
        f"Program: {row.milestone}" if row.milestone else "",
    ]
    parts.append("---\n" + "\n".join(f"- {x}" for x in links if x))
    return "\n\n".join(parts)


def read_pulls() -> dict[str, Pull]:
    """Fetch PRs and keep the most relevant one per WU id (merged wins, else newest)."""
    raw: list[dict[str, Any]] = json.loads(
        _gh(
            "pr",
            "list",
            "-R",
            REPO,
            "--state",
            "all",
            "--limit",
            "500",
            "--json",
            "number,title,state,isDraft,updatedAt",
        )
    )
    pulls: dict[str, Pull] = {}
    for item in raw:
        m = ID_RE.match(str(item["title"]))
        if not m:
            continue
        if str(item["state"]) == "CLOSED":
            continue  # abandoned without merge: the WU falls back to its draft card
        pull = Pull(
            int(item["number"]),
            str(item["state"]),
            bool(item["isDraft"]),
            _when(str(item["updatedAt"])),
        )
        prev = pulls.get(m.group(1))
        if (
            prev is None
            or (pull.state == "MERGED" and prev.state != "MERGED")
            or (prev.state != "MERGED" and pull.updated_at > prev.updated_at)
        ):
            pulls[m.group(1)] = pull
    return pulls


def desired_status(row: PlanRow, pull: Pull | None, current: str | None) -> str:
    """Derive the status a WU card must show.

    An open PR is the strongest fact: a plan row flipped to ✅ before its PR
    merged does not make the card Done.
    """
    if pull is not None and pull.state == "MERGED":
        return "Done"
    if pull is not None and pull.state == "OPEN":
        if current == "Blocked on maintainer":
            return current
        return "In progress" if pull.draft else "In review"
    if row.done:
        return "Done"
    if current == "Blocked on maintainer":
        return current
    return "Defined"


class Board:
    """GraphQL client for one organization project: items, Status, Owner, Tier."""

    def __init__(self, number: int) -> None:
        """Load the project, its single-select fields, and every item (paginated).

        Args:
            number: The project number under the organization.
        """
        query = """
        query($org:String!, $num:Int!, $after:String) {
          organization(login:$org) { projectV2(number:$num) { id
            fields(first:50) { nodes {
              ... on ProjectV2Field { id name dataType }
              ... on ProjectV2SingleSelectField { id name options { id name } } } }
            items(first:100, after:$after) { pageInfo { hasNextPage endCursor } nodes { id
              fieldValues(first:30) { nodes {
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name field { ... on ProjectV2SingleSelectField { name } } }
                ... on ProjectV2ItemFieldTextValue {
                  text field { ... on ProjectV2Field { name } } } } }
              content { __typename ... on DraftIssue { id title body } ... on Issue { title }
                        ... on PullRequest { number title } } } } } } }"""
        self.items: dict[str, Item] = {}
        after = ""
        while True:
            variables: dict[str, str | int] = {"org": ORG, "num": number}
            if after:
                variables["after"] = after
            project = _graphql(query, **variables)["organization"]["projectV2"]
            self.id: str = project["id"]
            field_nodes: list[dict[str, Any]] = project["fields"]["nodes"]
            self.fields: dict[str, tuple[str, dict[str, str]]] = {
                str(f["name"]): (str(f["id"]), {str(o["name"]): str(o["id"]) for o in f["options"]})
                for f in field_nodes
                if f.get("name") and "options" in f
            }
            self.text_fields: dict[str, str] = {
                str(f["name"]): str(f["id"])
                for f in field_nodes
                if f.get("name") and f.get("dataType") == "TEXT"
            }
            nodes: list[dict[str, Any]] = project["items"]["nodes"]
            for node in nodes:
                content: dict[str, Any] = node.get("content") or {}
                title = str(content.get("title") or "")
                values: dict[str, str] = {}
                fv_container: dict[str, Any] = node.get("fieldValues") or {}
                raw_values: list[dict[str, Any]] = fv_container.get("nodes") or []
                for fv in raw_values:
                    fld: dict[str, Any] = fv.get("field") or {}
                    fname = fld.get("name")
                    if fname and "name" in fv:
                        values[str(fname)] = str(fv["name"])
                    elif fname and "text" in fv:
                        values[str(fname)] = str(fv["text"] or "")
                kind = str(content.get("__typename", ""))
                pull_number = int(content.get("number") or 0)
                key = f"PR#{pull_number}" if kind == "PullRequest" else title
                self.items[key] = Item(
                    str(node["id"]),
                    title,
                    values.get("Status"),
                    kind,
                    str(content.get("id") or ""),
                    str(content.get("body") or ""),
                    values,
                    pull_number,
                )
            page = project["items"]["pageInfo"]
            if not page["hasNextPage"]:
                break
            after = str(page["endCursor"])

    def add_draft(self, title: str, body: str) -> Item:
        """Create a draft item and return it."""
        mutation = """
        mutation($p:ID!, $t:String!, $b:String!) {
          addProjectV2DraftIssue(input:{projectId:$p, title:$t, body:$b}) {
            projectItem { id } } }"""
        data = _graphql(mutation, p=self.id, t=title, b=body)
        item = Item(
            str(data["addProjectV2DraftIssue"]["projectItem"]["id"]), title, None, "DraftIssue"
        )
        self.items[title] = item
        return item

    def add_pr(self, number: int) -> Item:
        """Add a pull request to the project as an item and return it."""
        node_id = _gh("pr", "view", str(number), "-R", REPO, "--json", "id", "-q", ".id").strip()
        title = _gh(
            "pr", "view", str(number), "-R", REPO, "--json", "title", "-q", ".title"
        ).strip()
        mutation = """
        mutation($p:ID!, $c:ID!) {
          addProjectV2ItemById(input:{projectId:$p, contentId:$c}) { item { id } } }"""
        data = _graphql(mutation, p=self.id, c=node_id)
        item = Item(
            str(data["addProjectV2ItemById"]["item"]["id"]),
            title,
            None,
            "PullRequest",
            number=number,
        )
        self.items[f"PR#{number}"] = item
        return item

    def delete_item(self, item: Item) -> None:
        """Remove an item from the project (its content is untouched)."""
        mutation = """
        mutation($p:ID!, $i:ID!) {
          deleteProjectV2Item(input:{projectId:$p, itemId:$i}) { deletedItemId } }"""
        _graphql(mutation, p=self.id, i=item.id)
        self.items = {k: v for k, v in self.items.items() if v.id != item.id}

    def update_draft(self, item: Item, title: str, body: str) -> None:
        """Rewrite a draft item's title and body."""
        mutation = """
        mutation($d:ID!, $t:String!, $b:String!) {
          updateProjectV2DraftIssue(input:{draftIssueId:$d, title:$t, body:$b}) {
            draftIssue { id } } }"""
        _graphql(mutation, d=item.content_id, t=title, b=body)

    def set_text(self, item: Item, field_name: str, text: str) -> None:
        """Set a text field of an item."""
        field_id = self.text_fields[field_name]
        mutation = """
        mutation($p:ID!, $i:ID!, $f:ID!, $t:String!) {
          updateProjectV2ItemFieldValue(input:{projectId:$p, itemId:$i, fieldId:$f,
            value:{text:$t}}) { projectV2Item { id } } }"""
        _graphql(mutation, p=self.id, i=item.id, f=field_id, t=text)

    def set_field(self, item: Item, field: str, option: str) -> None:
        """Set a single-select field of an item by option name.

        Raises:
            KeyError: When the field or option does not exist on the project.
        """
        field_id, options = self.fields[field]
        mutation = """
        mutation($p:ID!, $i:ID!, $f:ID!, $o:String!) {
          updateProjectV2ItemFieldValue(input:{projectId:$p, itemId:$i, fieldId:$f,
            value:{singleSelectOptionId:$o}}) { projectV2Item { id } } }"""
        _graphql(mutation, p=self.id, i=item.id, f=field_id, o=options[option])


def _first(entry: Entry | None, name: str) -> str:
    """First line of a bullet, stripped, or empty."""
    if entry is None:
        return ""
    return entry.sections.get(name, "").split("\n")[0].strip("` ").strip()


def _option(board: Board, field_name: str, value: str) -> str:
    """Match a value to an existing single-select option (case-insensitive prefix), else empty."""
    if not value or field_name not in board.fields:
        return ""
    options = board.fields[field_name][1]
    low = value.lower()
    for name in options:
        if name.lower() == low or name.lower().startswith(low) or low.startswith(name.lower()):
            return name
    return ""


def _find(board: Board, wu: str) -> Item | None:
    """Find the WU's draft card (title starts with the WU id)."""
    for item in board.items.values():
        m = ID_RE.match(item.title)
        if m and m.group(1) == wu and item.kind == "DraftIssue":
            return item
    return None


def _find_pr_item(board: Board, number: int) -> Item | None:
    """Find the project item that is this pull request."""
    return board.items.get(f"PR#{number}")


def cmd_sync(args: argparse.Namespace) -> int:
    """Reconcile plan rows, PRs, and cards; create and move cards with --apply."""
    rows = read_plan(args.ref)
    pulls = read_pulls()
    board = Board(args.project)
    notices: list[str] = []
    print(f"plan rows: {len(rows)}; cards: {len(board.items)}; WU-titled PRs: {len(pulls)}")
    findings: list[str] = []
    known: set[str] = set()
    for row in rows:
        known.add(row.wu)
        pull = pulls.get(row.wu)
        draft = _find(board, row.wu)
        card: Item | None = None
        if pull is not None:
            card = _find_pr_item(board, pull.number)
            if card is None and args.apply:
                card = board.add_pr(pull.number)
                print(f"{row.wu}: PR #{pull.number} added as the card")
            if card is not None and draft is not None and args.apply:
                board.delete_item(draft)
                print(f"{row.wu}: draft card replaced by PR #{pull.number}")
                draft = None
        if card is None:
            card = draft
        if card is None:
            if row.done:
                continue  # completed before the board existed; no card needed
            if not args.apply:
                findings.append(f"{row.wu}: no card (run with --apply)")
                continue
            card = board.add_draft(f"{row.wu}: {row.title}", "")
            print(f"created card for {row.wu}")
        entry = read_entry(row, args.ref)
        if row.done and pull is not None and pull.state == "OPEN":
            findings.append(
                f"{row.wu}: plan row is ✅ but PR #{pull.number} is still open "
                "(flip the row in the PR that merges)"
            )
        findings.extend(lint_entry(row, entry))
        title = f"{row.wu}: {row.title}"
        body = card_body(row, entry, pull)
        if card.kind == "DraftIssue" and args.apply and (card.body != body or card.title != title):
            board.update_draft(card, title, body)
            print(f"{row.wu}: body refreshed")
        wanted_fields: dict[str, str] = {
            "Kind": "WU",
            "Program": PROGRAMS.get(row.milestone, ""),
            "Area": _option(board, "Area", infer_area(entry)),
            "Priority": _option(board, "Priority", _first(entry, "Priority")),
            "Tier": _option(board, "Tier", _first(entry, "Tier")),
            "Owner": _option(board, "Owner", _first(entry, "Owner")),
        }
        for fname, value in wanted_fields.items():
            if value and card.fields.get(fname) != value and args.apply:
                board.set_field(card, fname, value)
        plan_url = f"{BLOB}docs/plans/{row.file}#{entry.anchor}" if entry and row.file else ""
        wanted_text = {"PR": pull.url if pull else "", "Plan": plan_url}
        for fname, value in wanted_text.items():
            if value and card.fields.get(fname) != value and args.apply:
                board.set_text(card, fname, value)
        want = desired_status(row, pull, card.status)
        if row.done and want != "Done":
            findings.append(f"{row.wu}: plan says ✅ but the card is {card.status}")
        if want == "In progress" and pull is not None:
            age = datetime.now(UTC) - pull.updated_at
            if age > timedelta(days=args.stale_days):
                findings.append(f"{row.wu}: draft PR #{pull.number} untouched for {age.days} days")
        if card.status != want:
            if args.apply:
                board.set_field(card, "Status", want)
                print(f"{row.wu}: {card.status} -> {want}")
            else:
                findings.append(f"{row.wu}: card shows {card.status}, facts say {want}")
    for item in board.items.values():
        m = ID_RE.match(item.title)
        if m and m.group(1) not in known:
            if item.kind == "PullRequest":
                notices.append(
                    f"{m.group(1)}: PR #{item.number} has no plan row yet (defined in its own PR?)"
                )
            elif args.apply:
                board.delete_item(
                    item
                )  # created from a PR branch's plan table; the row is not on main
                print(f"{m.group(1)}: stray draft card removed (no plan row on main)")
            else:
                findings.append(f"{m.group(1)}: draft card has no plan row")
    for n in notices:
        print("  note: " + n)
    if findings:
        print("\nBOARD OUT OF SYNC:")
        for f in findings:
            print("  " + f)
        return 0 if args.lenient else 1
    print("board: in sync")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    """Add one card: a WU card (status derived) or a decision/gap card."""
    board = Board(args.project)
    if args.title in board.items:
        print(f"already on the board: {args.title}")
        return 0
    body = Path(args.body_file).read_text(encoding="utf-8") if args.body_file else ""
    item = board.add_draft(args.title, body)
    status = {"wu": "Defined", "decision": "Blocked on maintainer", "gap": "Defined"}[args.kind]
    board.set_field(item, "Status", status)
    board.set_field(item, "Kind", {"wu": "WU", "decision": "Decision", "gap": "Gap"}[args.kind])
    print(f"added {args.kind} card: {args.title} [{status}]")
    return 0


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


def cmd_set(args: argparse.Namespace) -> int:
    """Set Owner and/or Tier on a WU card."""
    board = Board(args.project)
    card = _find(board, args.wu)
    if card is None:
        print(f"no card for {args.wu}")
        return 1
    if args.owner:
        board.set_field(card, "Owner", args.owner)
    if args.tier:
        board.set_field(card, "Tier", args.tier)
    print(f"{args.wu}: owner={args.owner or '-'} tier={args.tier or '-'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Command-line arguments, defaulting to `sys.argv[1:]`.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Keep the project board in step with the plan and PRs."
    )
    parser.add_argument(
        "--project", type=int, default=int(os.environ.get("BOARD_PROJECT_NUMBER", "0"))
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_sync = sub.add_parser("sync", help="reconcile; --apply creates cards and sets statuses")
    p_sync.add_argument("--apply", action="store_true")
    p_sync.add_argument("--stale-days", type=int, default=7)
    p_sync.add_argument(
        "--ref", default=None, help="read the plan from this git ref (CI: origin/main)"
    )
    p_sync.add_argument(
        "--lenient", action="store_true", help="report findings but exit 0 (PR events)"
    )
    p_sync.set_defaults(func=cmd_sync)
    p_add = sub.add_parser("add", help="add one card")
    p_add.add_argument("kind", choices=("wu", "decision", "gap"))
    p_add.add_argument("title")
    p_add.add_argument("--body-file")
    p_add.set_defaults(func=cmd_add)
    p_body = sub.add_parser("pr-body", help="print a PR body pre-filled from the WU entry")
    p_body.add_argument("wu")
    p_body.add_argument("--stacked-on", type=int, default=0, help="parent PR number when stacked")
    p_body.set_defaults(func=cmd_pr_body)
    p_set = sub.add_parser("set", help="set Owner / Tier on a WU card")
    p_set.add_argument("wu")
    p_set.add_argument("--owner")
    p_set.add_argument("--tier")
    p_set.set_defaults(func=cmd_set)
    p_lint = sub.add_parser("lint", help="check every plan entry against the template (offline)")
    p_lint.set_defaults(func=cmd_lint)
    p_entry = sub.add_parser("entry", help="print one WU entry's bullets (offline)")
    p_entry.add_argument("wu")
    p_entry.add_argument("--json", action="store_true")
    p_entry.set_defaults(func=cmd_entry)
    args = parser.parse_args(argv)
    if not args.project and args.command not in ("pr-body", "lint", "entry"):
        print("no project number: pass --project or set BOARD_PROJECT_NUMBER")
        return 2
    try:
        return int(args.func(args))
    except RuntimeError as exc:
        print(f"board: {str(exc).splitlines()[0] if str(exc) else 'gh failed'}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
