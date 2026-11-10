"""The example's application-composed catalog contribution.

Empty contracts make a lossless claim for canonical-format documents, checked
against independent fixtures. Importing this module mutates no shared catalog.
"""

from __future__ import annotations

from datetime import date
from importlib.metadata import version
from typing import Any

from ocai.chat.types import ChatRequest
from ocai.contrib.echo.codec import EchoChatCodec
from ocai.convert.catalog import CatalogFragment
from ocai.convert.contract import EdgeContract
from ocai.convert.graph import Edge
from ocai.convert.graph import EdgeOutput
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import CHAT_RESPONSE
from ocai.core.identity import NodeId
from ocai.core.identity import Origin
from ocai.core.identity import canonical_node

ECHO_ORIGIN = Origin(distribution="ocai-contrib-echo", version=version("ocai-contrib-echo"))
ECHO_CHAT_REQUEST = NodeId(
    provider="echo",
    interface="chat",
    tag="2026-07",
    shape=CHAT_REQUEST,
    released=date(2026, 7, 1),
)
ECHO_CHAT_RESPONSE = NodeId(
    provider="echo",
    interface="chat",
    tag="2026-07",
    shape=CHAT_RESPONSE,
    released=date(2026, 7, 1),
)
OCAI_CHAT_REQUEST = canonical_node(CHAT_REQUEST)
OCAI_CHAT_RESPONSE = canonical_node(CHAT_RESPONSE)
_CONTRACT = EdgeContract(census={})
_CODEC = EchoChatCodec()


def _encode_request(payload: ChatRequest) -> EdgeOutput:
    """Convert typed canonical input to echo's JSON representation."""
    return EdgeOutput(value=_CODEC.encode(payload))


def _decode_request(payload: dict[str, Any]) -> EdgeOutput:
    """Convert echo's JSON request to a typed canonical request."""
    return EdgeOutput(value=_CODEC.decode_request(payload))


def _decode_response(payload: dict[str, Any]) -> EdgeOutput:
    """Convert echo's JSON response to a typed canonical response."""
    return EdgeOutput(value=_CODEC.decode(payload))


FRAGMENT = CatalogFragment(
    origin=ECHO_ORIGIN,
    nodes=(ECHO_CHAT_REQUEST, ECHO_CHAT_RESPONSE),
    edges=(
        Edge(OCAI_CHAT_REQUEST, ECHO_CHAT_REQUEST, _encode_request, _CONTRACT, ECHO_ORIGIN),
        Edge(ECHO_CHAT_REQUEST, OCAI_CHAT_REQUEST, _decode_request, _CONTRACT, ECHO_ORIGIN),
        Edge(ECHO_CHAT_RESPONSE, OCAI_CHAT_RESPONSE, _decode_response, _CONTRACT, ECHO_ORIGIN),
    ),
)
