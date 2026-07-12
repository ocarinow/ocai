"""`ocai.contrib.echo` — a worked example third-party ocai plugin.

Shipped by a SEPARATE distribution (`ocai-contrib-echo`) but landing in the
shared `ocai` PEP 420 namespace under the **`ocai.contrib.*`** prefix reserved
for community plugins (first-party plugins live directly under
`ocai.<provider>`).

The entire integration surface is one frozen value: `FRAGMENT`, a
`CatalogFragment` the application composes with `Catalog.of(echo.FRAGMENT)`
or discovers via the `ocai.plugins` entry point. **Nothing happens at import
time** — no global graph mutation, no registration side effects; that pattern
is gone with the July 2026 re-architecture.

TEMPLATE STATUS: structure is settled; behavior is pending completion of the
`ocai.convert` conformance harness.
"""

from __future__ import annotations

from ocai.contrib.echo.codec import EchoChatCodec
from ocai.contrib.echo.fragment import ECHO_CHAT_REQUEST
from ocai.contrib.echo.fragment import ECHO_CHAT_RESPONSE
from ocai.contrib.echo.fragment import ECHO_ORIGIN
from ocai.contrib.echo.fragment import ECHO_PROFILE
from ocai.contrib.echo.fragment import FRAGMENT

__all__ = [
    "ECHO_CHAT_REQUEST",
    "ECHO_CHAT_RESPONSE",
    "ECHO_ORIGIN",
    "ECHO_PROFILE",
    "FRAGMENT",
    "EchoChatCodec",
]
