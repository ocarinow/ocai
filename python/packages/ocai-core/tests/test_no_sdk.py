"""ocai owns the wire: no provider SDK is imported anywhere (rule 12)."""

from __future__ import annotations

import importlib
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

# The whole public surface, imported before the SDK check below.
_SURFACE = (
    "ocai.anthropic",
    "ocai.chat",
    "ocai.convert",
    "ocai.core",
    "ocai.openai",
    "ocai.runtime",
    "ocai.wire",
)


def test_provider_sdks_not_imported_by_core_or_plugins() -> None:
    # Import the whole surface, then assert no provider SDK got pulled in.
    for module in _SURFACE:
        importlib.import_module(module)

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
