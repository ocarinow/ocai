"""`ocai.anthropic` — the Anthropic plugin distribution (`ocai-anthropic`).

Ships in the same `ocai` PEP 420 namespace as the core distribution but as a
separate dist, organized **one subpackage per interface** (§7). Today that is
one interface:

- `ocai.anthropic.messages` — the `/v1/messages` wire protocol,

with room for future siblings as concurrent subpackages (never "versions" of
this one). The distribution-level `FRAGMENT` re-exports the Messages
fragment; an application opts in with `Catalog.of(ocai.anthropic.FRAGMENT)`
— importing this package is inert, with **no import-time registration**
anywhere (rule 14; the old process-global `register()` side effect is gone).
The plugin depends on `ocai.core` + `ocai.convert` + `ocai.chat` only —
never on `ocai.wire` or httpx — so archived traffic can be re-converted by
tooling with no ability to make network calls.

It also re-exports `chat_model`, the sanctioned §3.4 sugar door
(`from ocai.anthropic import chat_model; chat_model("claude-opus-4-6",
credentials=key)`) — a thin wrapper over the same fragment + facade
machinery as the core string door, targeting the `messages` interface.
"""

from __future__ import annotations

from ocai.anthropic import messages
from ocai.anthropic.messages import FRAGMENT
from ocai.anthropic.messages import chat_model

__all__ = [
    "FRAGMENT",
    "chat_model",
    "messages",
]
