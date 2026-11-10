"""Board sync: keep the GitHub Project in step with the plan table and the PRs.

The plan table in `docs/plans/README.md` is the definition of every work
unit (WU). The board is a view of it. This script reconciles the two from
facts it can read with `gh`::

    uv run python scripts/board_sync.py                 # report only, exit 1 on findings
    uv run python scripts/board_sync.py --apply         # also create missing cards and set statuses
    uv run python scripts/board_sync.py --project 3     # project number (or BOARD_PROJECT_NUMBER)

Rules (also stated in AGENTS.md, "The board"):

- every open plan row has one card: an open or closed issue labelled
  `work-unit` whose title starts with the WU id (rows already ✅ before the
  board existed need none);
- a card's status is derived, never dragged: no PR → Defined; draft PR →
  In progress; PR ready for review → In review; merged (or closed card) →
  Done; `blocked-maintainer` label → Blocked on maintainer;
- the plan row and the card must agree: a ✅ row needs a merged PR or a
  closed card; an open card with a ✅ row, or a closed card with a ⬜ row,
  is a finding;
- an In progress card whose PR has not moved for `--stale-days` is a finding.

Project access needs a token with the `project` scope (CI: `BOARD_TOKEN`).
Without it the script still checks plan ↔ cards and skips the status step.
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
STATUS_FIELD = "Status"
STATUSES = ("Defined", "In progress", "In review", "Blocked on maintainer", "Done")
ROW_RE = re.compile(r"^\|\s*(WU-[0-9A-Za-z]+)\s*\|\s*(.+?)\s*\|.*\|\s*(.+?)\s*\|\s*$")
ID_RE = re.compile(r"^(WU-[0-9A-Za-z]+)\b")
CLOSES_RE = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)", re.IGNORECASE)


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
class Card:
    """One board card (a `work-unit` issue).

    Attributes:
        wu: The WU id parsed from the title.
        number: Issue number.
        state: `OPEN` or `CLOSED`.
        labels: Label names.
        updated_at: Last update timestamp.
    """

    wu: str
    number: int
    state: str
    labels: tuple[str, ...]
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Pull:
    """One pull request linked to a WU.

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


def read_cards() -> dict[str, Card]:
    """Fetch `work-unit` issues keyed by WU id."""
    raw: list[dict[str, Any]] = json.loads(
        _gh(
            "issue",
            "list",
            "-R",
            REPO,
            "--label",
            "work-unit",
            "--state",
            "all",
            "--limit",
            "500",
            "--json",
            "number,title,state,labels,updatedAt",
        )
    )
    cards: dict[str, Card] = {}
    for item in raw:
        m = ID_RE.match(str(item["title"]))
        if not m:
            continue
        labels = tuple(str(lab["name"]) for lab in item["labels"])
        cards[m.group(1)] = Card(
            m.group(1),
            int(item["number"]),
            str(item["state"]),
            labels,
            _when(str(item["updatedAt"])),
        )
    return cards


def read_pulls(cards: dict[str, Card]) -> dict[str, Pull]:
    """Fetch PRs and key the most recent one per WU (by title prefix or `Closes #N`)."""
    by_issue = {c.number: c.wu for c in cards.values()}
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
            "number,title,state,isDraft,updatedAt,body",
        )
    )
    pulls: dict[str, Pull] = {}
    for item in raw:
        wu: str | None = None
        m = ID_RE.match(str(item["title"]))
        if m:
            wu = m.group(1)
        for ref in CLOSES_RE.findall(str(item.get("body") or "")):
            wu = wu or by_issue.get(int(ref))
        if wu is None:
            continue
        pull = Pull(
            int(item["number"]),
            str(item["state"]),
            bool(item["isDraft"]),
            _when(str(item["updatedAt"])),
        )
        prev = pulls.get(wu)
        if prev is None or pull.state == "MERGED" or pull.updated_at > prev.updated_at:
            pulls[wu] = pull
    return pulls


def desired_status(card: Card | None, pull: Pull | None) -> str:
    """Derive the status a card must show from the facts."""
    if card is not None and "blocked-maintainer" in card.labels:
        return "Blocked on maintainer"
    if (card is not None and card.state == "CLOSED") or (
        pull is not None and pull.state == "MERGED"
    ):
        return "Done"
    if pull is not None and pull.state == "OPEN":
        return "In progress" if pull.draft else "In review"
    return "Defined"


def create_card(row: PlanRow) -> int:
    """Create the board card for a plan row and return its issue number."""
    body = (
        "### Plan entry\n\nhttps://github.com/ocarinow/ocai/blob/main/docs/plans/README.md\n\n"
        "### Owner\n\nunassigned\n\n### Tier\n\nprogram\n"
    )
    out = _gh(
        "issue",
        "create",
        "-R",
        REPO,
        "--label",
        "work-unit",
        "--title",
        f"{row.wu}: {row.title}",
        "--body",
        body,
    )
    return int(out.strip().rsplit("/", 1)[-1])


class Board:
    """Thin GraphQL client for the project's Status field."""

    def __init__(self, number: int) -> None:
        """Load the project, its Status field, and its items.

        Args:
            number: The project number under the organization.
        """
        query = """
        query($org:String!, $num:Int!) {
          organization(login:$org) { projectV2(number:$num) { id
            fields(first:50) { nodes {
              ... on ProjectV2SingleSelectField { id name options { id name } } } }
            items(first:500) { nodes { id content { ... on Issue { number } } } } } } }"""
        data: dict[str, Any] = json.loads(
            _gh(
                "api",
                "graphql",
                "-f",
                f"query={query}",
                "-F",
                f"org={REPO.split('/')[0]}",
                "-F",
                f"num={number}",
            )
        )
        project = data["data"]["organization"]["projectV2"]
        self.id: str = project["id"]
        field = next(f for f in project["fields"]["nodes"] if f.get("name") == STATUS_FIELD)
        self.field_id: str = field["id"]
        self.options: dict[str, str] = {o["name"]: o["id"] for o in field["options"]}
        self.items: dict[int, str] = {
            int(n["content"]["number"]): n["id"]
            for n in project["items"]["nodes"]
            if n.get("content") and "number" in n["content"]
        }

    def add(self, issue_number: int) -> str:
        """Add an issue to the project and return the item id."""
        node: dict[str, Any] = json.loads(_gh("api", f"repos/{REPO}/issues/{issue_number}"))
        mutation = """
        mutation($p:ID!, $c:ID!) {
          addProjectV2ItemById(input:{projectId:$p, contentId:$c}) { item { id } } }"""
        data: dict[str, Any] = json.loads(
            _gh(
                "api",
                "graphql",
                "-f",
                f"query={mutation}",
                "-F",
                f"p={self.id}",
                "-F",
                f"c={node['node_id']}",
            )
        )
        item_id = str(data["data"]["addProjectV2ItemById"]["item"]["id"])
        self.items[issue_number] = item_id
        return item_id

    def set_status(self, item_id: str, status: str) -> None:
        """Set the Status single-select field of an item."""
        mutation = """
        mutation($p:ID!, $i:ID!, $f:ID!, $o:String!) {
          updateProjectV2ItemFieldValue(input:{projectId:$p, itemId:$i, fieldId:$f,
            value:{singleSelectOptionId:$o}}) { projectV2Item { id } } }"""
        _gh(
            "api",
            "graphql",
            "-f",
            f"query={mutation}",
            "-F",
            f"p={self.id}",
            "-F",
            f"i={item_id}",
            "-F",
            f"f={self.field_id}",
            "-F",
            f"o={self.options[status]}",
        )

    def status_of(self, issue_number: int) -> str | None:
        """Read the current Status of an issue's item, or None if absent."""
        item_id = self.items.get(issue_number)
        if item_id is None:
            return None
        query = """
        query($id:ID!) { node(id:$id) { ... on ProjectV2Item {
          fieldValueByName(name:"Status") {
            ... on ProjectV2ItemFieldSingleSelectValue { name } } } } }"""
        data: dict[str, Any] = json.loads(
            _gh("api", "graphql", "-f", f"query={query}", "-F", f"id={item_id}")
        )
        value = data["data"]["node"].get("fieldValueByName")
        return None if value is None else str(value.get("name"))


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Command-line arguments, defaulting to `sys.argv[1:]`.

    Returns:
        0 when plan, cards, and board agree; 1 when any finding remains.
    """
    parser = argparse.ArgumentParser(
        description="Reconcile the plan table, WU cards, and the board."
    )
    parser.add_argument(
        "--apply", action="store_true", help="create missing cards and set statuses"
    )
    parser.add_argument(
        "--project", type=int, default=int(os.environ.get("BOARD_PROJECT_NUMBER", "0"))
    )
    parser.add_argument("--stale-days", type=int, default=7)
    args = parser.parse_args(argv)

    findings: list[str] = []
    rows = read_plan()
    cards = read_cards()
    pulls = read_pulls(cards)
    print(f"plan rows: {len(rows)}; cards: {len(cards)}; linked PRs: {len(pulls)}")

    for row in rows:
        card = cards.get(row.wu)
        pull = pulls.get(row.wu)
        if card is None:
            if row.done:
                continue  # historical row completed before the board existed: no card needed
            if args.apply:
                number = create_card(row)
                card = Card(row.wu, number, "OPEN", ("work-unit",), datetime.now(UTC))
                cards[row.wu] = card
                print(f"created card #{number} for {row.wu}")
            else:
                findings.append(f"{row.wu}: no board card (run with --apply to create)")
                continue
        status = desired_status(card, pull)
        if row.done and status != "Done":
            findings.append(
                f"{row.wu}: plan says ✅ but card #{card.number} is {status} "
                "(no merged PR, card open)"
            )
        if not row.done and card.state == "CLOSED":
            findings.append(f"{row.wu}: card #{card.number} is closed but the plan row is not ✅")
        if status == "In progress" and pull is not None:
            age = datetime.now(UTC) - pull.updated_at
            if age > timedelta(days=args.stale_days):
                findings.append(
                    f"{row.wu}: PR #{pull.number} is a draft untouched for {age.days} days"
                )
    for wu, card in cards.items():
        if all(r.wu != wu for r in rows):
            findings.append(f"{wu}: card #{card.number} has no plan row")

    if args.project:
        try:
            board = Board(args.project)
        except RuntimeError as exc:
            reason = str(exc).splitlines()[0] if str(exc) else "no access"
            print(f"board: skipped ({reason}) — needs a token with the project scope")
        else:
            for row in rows:
                card = cards.get(row.wu)
                if card is None:
                    continue
                want = desired_status(card, pulls.get(row.wu))
                item_id = board.items.get(card.number)
                if item_id is None:
                    if not args.apply:
                        findings.append(f"{row.wu}: card #{card.number} is not on the board")
                        continue
                    item_id = board.add(card.number)
                    print(f"added #{card.number} to the board")
                have = board.status_of(card.number)
                if have != want:
                    if args.apply:
                        board.set_status(item_id, want)
                        print(f"{row.wu}: #{card.number} {have} -> {want}")
                    else:
                        findings.append(f"{row.wu}: board shows {have}, facts say {want}")
    else:
        print("board: no project number given; status step skipped")

    if findings:
        print("\nBOARD OUT OF SYNC:")
        for f in findings:
            print("  " + f)
        return 1
    print("board: in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
