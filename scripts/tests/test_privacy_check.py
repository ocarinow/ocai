"""A personal email address must never reach a public surface, and never a public log."""

from __future__ import annotations

import pytest
from privacy_check import email_findings
from privacy_check import is_public_email_domain

# Assembled at run time so this file does not itself hold a personal-looking address.
PERSONAL = "jane.doe@" + "gmail.com"


@pytest.mark.parametrize(
    "text",
    [
        f"Signed-off-by: Jane Doe <{PERSONAL}>",
        f"Jane Doe <{PERSONAL}> jdoe <{PERSONAL}>",
        f"contact {PERSONAL.upper()} for access",
    ],
)
def test_personal_address_is_reported_without_repeating_it(text: str) -> None:
    findings = email_findings(text, "sample")

    assert findings
    assert all("personal email address" in finding for finding in findings)
    assert all("jane.doe" not in finding.lower() for finding in findings)


@pytest.mark.parametrize(
    "text",
    [
        "12345678+octocat@users.noreply.github.com",
        "Signed-off-by: dependabot[bot] <support@github.com>",
        "noreply@github.com",
        "operator@example.com",
        "admin@identity.test",
        "nobody@example.invalid",
    ],
)
def test_addresses_that_identify_nobody_pass(text: str) -> None:
    assert email_findings(text, "sample") == []


@pytest.mark.parametrize(
    "text",
    [
        "uses: actions/checkout@v7.0.1",
        "openapi-typescript@7.9.0",
        "postgresql://service:secret@localhost:5432/db",
        "@pytest.mark.parametrize",
    ],
)
def test_text_that_only_resembles_an_address_passes(text: str) -> None:
    assert email_findings(text, "sample") == []


def test_finding_names_the_line() -> None:
    findings = email_findings(f"first line\nsecond line {PERSONAL}\n", "body.md")

    assert findings == ["body.md:2: personal email address: 'j…@gmail.com'"]


@pytest.mark.parametrize(
    ("domain", "public"),
    [
        ("users.noreply.github.com", True),
        ("GitHub.com", True),
        ("example.org", True),
        ("service.test", True),
        ("gmail.com", False),
        ("notgithub.com", False),
        ("github.com.attacker.io", False),
    ],
)
def test_public_domains_are_exact_or_subdomains(domain: str, public: bool) -> None:
    assert is_public_email_domain(domain) is public
