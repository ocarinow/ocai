"""ocai owns the wire: no provider SDK is imported anywhere (rule 12)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Patterns are built at runtime so this test file contains no literal
# "import <sdk>" string (keeps the repo-wide acceptance grep clean). The regex
# anchors right after `import`/`from`, so `ocai.openai` never false-positives.
_SDKS = ("openai", "anthropic", "google.generativeai", "genai", "mistralai", "cohere")
_FORBIDDEN = re.compile(
    r"^\s*(?:import|from)\s+(" + "|".join(re.escape(sdk) for sdk in _SDKS) + r")\b",
    re.MULTILINE,
)


def test_provider_sdks_not_imported_by_core_or_plugins() -> None:
    # Import the whole surface, then assert no provider SDK got pulled in.
    import ocai.anthropic  # noqa: F401
    import ocai.chat  # noqa: F401
    import ocai.convert  # noqa: F401
    import ocai.core  # noqa: F401
    import ocai.openai  # noqa: F401
    import ocai.runtime  # noqa: F401
    import ocai.wire  # noqa: F401

    assert sys.modules.get("openai") is None, "ocai must not import the openai SDK"
    assert sys.modules.get("anthropic") is None, "ocai must not import the anthropic SDK"


def test_source_trees_have_no_provider_sdk_import(
    core_src: Path, openai_src: Path, anthropic_src: Path
) -> None:
    # Static guard: no source file in any distribution imports a provider SDK.
    hits: list[str] = []
    for src in (core_src, openai_src, anthropic_src):
        for path in sorted(src.rglob("*.py")):
            hits.extend(
                f"{path}: {match.group(0).strip()}"
                for match in _FORBIDDEN.finditer(path.read_text(encoding="utf-8"))
            )
    assert not hits, f"forbidden provider-SDK import(s): {hits}"
