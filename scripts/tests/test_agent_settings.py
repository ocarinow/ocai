"""The shared agent settings must keep harness attribution switched off."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def test_claude_code_attribution_is_off() -> None:
    settings: dict[str, Any] = json.loads(
        (ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")
    )

    assert settings["attribution"] == {"commit": "", "pr": "", "sessionUrl": False}
