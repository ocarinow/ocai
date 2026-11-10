"""Cross-conversion fidelity proof — flagship demo #1 (WU-15).

Pure `ocai.convert`, **no wire, no credentials, no network**: this is the
audit-tool posture — recorded provider traffic re-converted through the
canonical backbone, with every cost of the move visible in the
`FidelityReport`. Three legs:

1. A recorded `openai/chat_completions` request converts to an
   `anthropic/messages` request — the planner's 2-hop path through the
   canonical IR. Watch the system turn get hoisted to the Messages
   `system` field (a declared relocation, data-exact) and the wire `model`
   get banked as routing data.
2. The reverse: a recorded `anthropic/messages` request converts to
   `openai/chat_completions` — and the tool result's `is_error: true` is
   honestly **dropped** (chat_completions has no wire lane for it), never
   silently.
3. A recorded `anthropic/messages` *response* decodes to the canonical IR
   and its report is **merged** onto leg 1's, exactly as the facade folds a
   call's request and response legs into one report. (Encode-response
   edges do not exist yet, so the response leg runs in the decode
   direction only — the honest current scope, recorded in the WU-15 plan.)

Run it:

    uv run python examples/cross_conversion_demo.py

The printed report is asserted in
`python/packages/ocai-core/tests/test_cross_conversion.py` — the demo can
never drift from what the library actually reports.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import ocai.anthropic
import ocai.openai
from ocai.anthropic.messages.codec import MESSAGES_REQUEST
from ocai.anthropic.messages.codec import MESSAGES_RESPONSE
from ocai.chat import CANONICAL_CHAT_RESPONSE
from ocai.convert.catalog import Catalog
from ocai.convert.graph import ConversionError
from ocai.core.fidelity import FidelityReport
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_REQUEST


def _repo_root() -> Path:
    """Walk upward from this file to the directory containing `spec/fixtures/`."""
    start = Path(__file__).resolve()
    for parent in [start, *start.parents]:
        if (parent / "spec" / "fixtures").is_dir():
            return parent
    raise RuntimeError("could not locate repo root (no spec/fixtures/ found)")


def _fixture(relative: str) -> dict[str, Any]:
    """Load one golden fixture by its path under `spec/fixtures/`."""
    fixture: dict[str, Any] = json.loads(
        (_repo_root() / "spec" / "fixtures" / relative).read_text()
    )
    return fixture


def render_report(title: str, report: FidelityReport) -> str:
    """Render a `FidelityReport` human-readably, one line per record.

    Args:
        title: The heading naming what was converted.
        report: The report to render.

    Returns:
        The rendered block, ready to print.
    """
    lines = [f"=== {title} ==="]
    lines.append("path:     " + "  ->  ".join(str(node) for node in report.path))
    lines.append(f"lossless: {'yes' if report.lossless else 'NO'}")
    for edge in report.edges:
        lines.append(f"edge {edge.src}  ->  {edge.dst}")
        lines.extend(
            f"  loss  [{loss.disposition.value}] {loss.path} — {loss.note}"
            for loss in edge.losses
        )
        lines.extend(
            f"  shift ({shift.kind}) {shift.path} — {shift.note}" for shift in edge.shifts
        )
        if not edge.losses and not edge.shifts:
            lines.append("  (clean)")
    return "\n".join(lines)


def main() -> str:
    """Run the three demo legs and return the full printed report.

    Returns:
        The rendered demo output (also printed when run as a script).
    """
    catalog = Catalog.of(ocai.openai.FRAGMENT, ocai.anthropic.FRAGMENT)
    blocks: list[str] = []

    # Leg 1 — recorded openai/chat_completions request -> anthropic/messages,
    # two hops through the canonical backbone (there is no direct edge; the
    # canonical IR is the interchange every interface connects to).
    openai_request = _fixture("cross/request_openai_to_anthropic.json")["input"]
    leg1 = catalog.convert(openai_request, CHAT_COMPLETIONS_REQUEST, MESSAGES_REQUEST)
    blocks.append(
        render_report("request: openai/chat_completions -> anthropic/messages", leg1.report)
    )

    # Leg 2 — the reverse direction: the is_error flag that crossed EXACTLY
    # onto the Messages wire has no chat_completions lane and is DROPPED,
    # reported, never silent.
    anthropic_request = _fixture("cross/request_anthropic_to_openai.json")["input"]
    leg2 = catalog.convert(anthropic_request, MESSAGES_REQUEST, CHAT_COMPLETIONS_REQUEST)
    blocks.append(
        render_report("request: anthropic/messages -> openai/chat_completions", leg2.report)
    )

    # Leg 3 — a recorded anthropic/messages RESPONSE decodes to canonical and
    # merges onto leg 1's report, exactly as the facade folds a call's request
    # and response legs into the one report on CallResult.report.
    anthropic_response = _fixture("anthropic/messages/response_tool_use.json")["input"]
    response_leg = catalog.convert(anthropic_response, MESSAGES_RESPONSE, CANONICAL_CHAT_RESPONSE)
    merged = FidelityReport(edges=list(leg1.report.edges)).merge(response_leg.report)
    blocks.append(
        render_report(
            "merged: request leg (openai -> anthropic) + response decode leg", merged
        )
    )

    # The audit posture, stated: the response DECODE direction exists (leg 3
    # just ran it — any archived response converts back to canonical); the
    # encode-response direction does not exist yet — honest scope, not an
    # accident (recorded in the WU-15 plan).
    try:
        catalog.convert(response_leg.value, CANONICAL_CHAT_RESPONSE, MESSAGES_RESPONSE)
    except ConversionError:
        blocks.append(
            "note: canonical -> wire response (encode-response) is not registered yet;\n"
            "the response leg runs in the decode direction only — the honest WU-15 scope."
        )
    return "\n\n".join(blocks)


if __name__ == "__main__":
    print(main())
