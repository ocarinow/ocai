"""A pull request body is short, complete, and never a pasted template."""

from __future__ import annotations

import pytest
from pr_check import MANDATORY_SECTIONS
from pr_check import OPTIONAL_SECTIONS
from pr_check import TEMPLATE
from pr_check import Pull
from pr_check import check
from pr_check import template_headings

BODY = """\
## Goal

Remove the board so nothing has to be kept in step with the plan.

## How

The synchronization script loses its GitHub half; callers use the new name.

## Impact

None beyond the files changed.
"""


def test_template_holds_exactly_the_known_sections() -> None:
    assert template_headings() == [*MANDATORY_SECTIONS, *OPTIONAL_SECTIONS]


def test_three_sections_are_enough() -> None:
    assert check(Pull("Tooling: remove the board", BODY, draft=False)) == []


@pytest.mark.parametrize("heading", MANDATORY_SECTIONS)
def test_each_mandatory_section_is_required_even_in_a_draft(heading: str) -> None:
    body = BODY.replace(heading, "## Something else")

    findings = check(Pull("Tooling: remove the board", body, draft=True))

    assert findings == [f"body is missing mandatory sections: {heading}"]


def test_untouched_template_passes_as_draft_and_fails_as_ready() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")

    assert check(Pull("Tooling: remove the board", template, draft=True)) == []
    findings = check(Pull("Tooling: remove the board", template, draft=False))
    assert "## Goal has no content: fill it" in findings
    assert "## Open questions has no content: fill it or delete the section" in findings
    assert "ready for review but template placeholders remain (<…>)" in findings


def test_optional_section_without_content_is_a_finding() -> None:
    body = BODY + "\n## Open questions\n\n"

    findings = check(Pull("Tooling: remove the board", body, draft=False))

    assert findings == ["## Open questions has no content: fill it or delete the section"]


def test_code_is_never_mistaken_for_a_placeholder() -> None:
    body = BODY.replace(
        "The synchronization script",
        "```python\nvalues: Mapping<str, Any> = {}\n## not a heading\n```\n\n"
        "`Result<T, E>` stays. The synchronization script",
    )

    assert check(Pull("Tooling: remove the board", body, draft=False)) == []


def test_stacked_pull_request_names_its_parent() -> None:
    title = "Tooling: remove the board"

    assert check(Pull(title, BODY, draft=False, base="parent-branch")) == [
        "base is `parent-branch`: the body must say `Stacked on #N`"
    ]
    assert check(Pull(title, "Stacked on #12\n\n" + BODY, draft=False, base="parent-branch")) == []


@pytest.mark.parametrize(
    ("title", "ok"),
    [
        ("WU-49: Parse bounded frames", True),
        ("Tooling: remove the board", True),
        ("remove the board", False),
        ("tooling: remove the board", False),
    ],
)
def test_title_names_a_topic(title: str, ok: bool) -> None:
    findings = check(Pull(title, BODY, draft=False))

    assert (findings == []) is ok


@pytest.mark.parametrize(
    ("title", "author"),
    [
        ("Deps: Bump anyio from 4.13.0 to 4.14.2", "dependabot[bot]"),
        ("Release: bump versions and changelogs from change files", "someone"),
    ],
)
def test_generated_pull_requests_are_checked_on_title_only(title: str, author: str) -> None:
    assert check(Pull(title, "generated body", draft=False, author=author)) == []
