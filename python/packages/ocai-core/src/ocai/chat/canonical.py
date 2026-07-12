"""The canonical chat graph nodes (architecture §2.1, §3).

The canonical IR is **just another interface** — provider `ocai`, interface
`ocai` — with dated revisions. These constants name the three canonical chat
nodes at the current revision; conversion edges to/from every provider
interface terminate on them, and IR self-migration (`ocai@2026-07 →
ocai@2027-01`) is ordinary edge traversal between two such node sets.

The chat IR dataclasses stamp these on `__node__`, and `WireChatModel` uses
them as the fixed end of every request/response/chunk conversion.
"""

from __future__ import annotations

from typing import Final

from ocai.core.identity import CANONICAL_INTERFACE
from ocai.core.identity import CANONICAL_REVISION
from ocai.core.identity import CHAT_CHUNK
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import CHAT_RESPONSE
from ocai.core.identity import NodeId
from ocai.core.identity import canonical_node

# The interface name of the canonical IR — canonical is not a special case:
# it is provider "ocai" publishing interface "ocai".
OCAI_INTERFACE: Final[str] = CANONICAL_INTERFACE

# The current canonical chat revision tag — a dated token on the `ocai`
# interface ("2026-07"), never the library semver, never a provider tag.
REVISION: Final[str] = CANONICAL_REVISION

# The canonical chat nodes at the current revision — the fixed endpoints of
# every chat conversion path.
CANONICAL_CHAT_REQUEST: Final[NodeId] = canonical_node(CHAT_REQUEST, REVISION)
CANONICAL_CHAT_RESPONSE: Final[NodeId] = canonical_node(CHAT_RESPONSE, REVISION)
CANONICAL_CHAT_CHUNK: Final[NodeId] = canonical_node(CHAT_CHUNK, REVISION)
