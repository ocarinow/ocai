"""`ocai.openai` — the OpenAI plugin distribution (`ocai-openai`).

Ships in the same `ocai` PEP 420 namespace as the core distribution but as a
separate dist, organized **one subpackage per interface** (§7):

- `ocai.openai.chat_completions` — the `/v1/chat/completions` wire protocol,
- `ocai.openai.responses` — the `/v1/responses` wire protocol [stub],

which are *concurrent sibling interfaces* of the one chat capability, not
versions of each other. Each subpackage carries its own wire models, codec,
contract-censused edges, and per-interface `FRAGMENT`.

This module composes them into the distribution-level `FRAGMENT` an
application opts into — `Catalog.of(ocai.openai.FRAGMENT)` — with **no
import-time registration** anywhere (rule 14; the old process-global
`register()` side effect is gone). Importing this package is inert. The
plugin depends on `ocai.core` + `ocai.convert` + `ocai.chat` only — never on
`ocai.wire` or httpx — so archived traffic can be re-converted by tooling
with no ability to make network calls.
"""

from __future__ import annotations

from ocai.convert.catalog import CatalogFragment
from ocai.openai import chat_completions
from ocai.openai import responses
from ocai.openai.chat_completions.edges import ORIGIN

__all__ = [
    "FRAGMENT",
    "chat_completions",
    "responses",
]

# The composed distribution fragment: everything both interfaces publish,
# under one provenance stamp. Compose the per-interface fragments instead
# when an application wants only one wire protocol in its catalog.
FRAGMENT = CatalogFragment(
    origin=ORIGIN,
    nodes=chat_completions.FRAGMENT.nodes + responses.FRAGMENT.nodes,
    edges=chat_completions.FRAGMENT.edges + responses.FRAGMENT.edges,
    transducers=chat_completions.FRAGMENT.transducers + responses.FRAGMENT.transducers,
    profiles=chat_completions.FRAGMENT.profiles + responses.FRAGMENT.profiles,
    traits=chat_completions.FRAGMENT.traits + responses.FRAGMENT.traits,
)
