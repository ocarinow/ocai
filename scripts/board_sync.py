"""Board sync: the GitHub Project is a view of the plan and the PRs, nothing more.

Cards are **draft items** on the project (never issues): one per open work
unit, titled `WU-NN: <title>` exactly as the plan row. Status is derived,
never dragged::

    uv run python scripts/board_sync.py sync                   # report, exit 1 when out of sync
    uv run python scripts/board_sync.py sync --apply           # create missing cards, set statuses
    uv run python scripts/board_sync.py add wu "WU-NN: title"  # one card now (sync does it too)
    uv run python scripts/board_sync.py add decision "Decision: …" --body-file F
    uv run python scripts/board_sync.py add gap "Gap: …" --body-file F
    uv run python scripts/board_sync.py set WU-NN --owner Claude --tier "1 chat …"

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
ROW_RE = re.compile(r"^\|\s*(WU-[0-9A-Za-z]+)\s*\|\s*(.+?)\s*\|.*\|\s*(.+?)\s*\|\s*$")
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


def read_plan() -> list[PlanRow]:
    """Parse the WU rows of the plan table."""
    rows: list[PlanRow] = []
    for line in PLAN.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if m:
            rows.append(PlanRow(m.group(1), m.group(2), "✅" in m.group(3)))
    return rows


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
    """Derive the status a WU card must show."""
    if row.done or (pull is not None and pull.state == "MERGED"):
        return "Done"
    if current == "Blocked on maintainer":
        return current
    if pull is not None and pull.state == "OPEN":
        return "In progress" if pull.draft else "In review"
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
              ... on ProjectV2SingleSelectField { id name options { id name } } } }
            items(first:100, after:$after) { pageInfo { hasNextPage endCursor } nodes { id
              fieldValueByName(name:"Status") {
                ... on ProjectV2ItemFieldSingleSelectValue { name } }
              content { __typename ... on DraftIssue { title } ... on Issue { title }
                        ... on PullRequest { title } } } } } } }"""
        self.items: dict[str, Item] = {}
        after = ""
        while True:
            variables: dict[str, str | int] = {"org": ORG, "num": number}
            if after:
                variables["after"] = after
            project = _graphql(query, **variables)["organization"]["projectV2"]
            self.id: str = project["id"]
            self.fields: dict[str, tuple[str, dict[str, str]]] = {
                f["name"]: (f["id"], {o["name"]: o["id"] for o in f["options"]})
                for f in project["fields"]["nodes"]
                if f.get("name")
            }
            nodes: list[dict[str, Any]] = project["items"]["nodes"]
            for node in nodes:
                content: dict[str, Any] = node.get("content") or {}
                title = str(content.get("title") or "")
                status_value: dict[str, Any] = node.get("fieldValueByName") or {}
                status_name = status_value.get("name")
                self.items[title] = Item(
                    str(node["id"]),
                    title,
                    None if status_name is None else str(status_name),
                    str(content.get("__typename", "")),
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


def _find(board: Board, wu: str) -> Item | None:
    """Find the card whose title starts with the WU id."""
    for title, item in board.items.items():
        m = ID_RE.match(title)
        if m and m.group(1) == wu:
            return item
    return None


def cmd_sync(args: argparse.Namespace) -> int:
    """Reconcile plan rows, PRs, and cards; create and move cards with --apply."""
    rows = read_plan()
    pulls = read_pulls()
    board = Board(args.project)
    print(f"plan rows: {len(rows)}; cards: {len(board.items)}; WU-titled PRs: {len(pulls)}")
    findings: list[str] = []
    known: set[str] = set()
    for row in rows:
        known.add(row.wu)
        pull = pulls.get(row.wu)
        card = _find(board, row.wu)
        if card is None:
            if row.done:
                continue  # completed before the board existed; no card needed
            if not args.apply:
                findings.append(f"{row.wu}: no card (run with --apply)")
                continue
            card = board.add_draft(
                f"{row.wu}: {row.title}", f"Plan: docs/plans/README.md — {row.wu}"
            )
            print(f"created card for {row.wu}")
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
    for title in board.items:
        m = ID_RE.match(title)
        if m and m.group(1) not in known:
            findings.append(f"{m.group(1)}: card has no plan row")
    if findings:
        print("\nBOARD OUT OF SYNC:")
        for f in findings:
            print("  " + f)
        return 1
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
    print(f"added {args.kind} card: {args.title} [{status}]")
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
    p_sync.set_defaults(func=cmd_sync)
    p_add = sub.add_parser("add", help="add one card")
    p_add.add_argument("kind", choices=("wu", "decision", "gap"))
    p_add.add_argument("title")
    p_add.add_argument("--body-file")
    p_add.set_defaults(func=cmd_add)
    p_set = sub.add_parser("set", help="set Owner / Tier on a WU card")
    p_set.add_argument("wu")
    p_set.add_argument("--owner")
    p_set.add_argument("--tier")
    p_set.set_defaults(func=cmd_set)
    args = parser.parse_args(argv)
    if not args.project:
        print("no project number: pass --project or set BOARD_PROJECT_NUMBER")
        return 2
    try:
        return int(args.func(args))
    except RuntimeError as exc:
        print(f"board: {str(exc).splitlines()[0] if str(exc) else 'gh failed'}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
