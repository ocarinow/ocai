"""Pure conversions for a fictional interface using canonical JSON on the wire.

This example registers no live chat component or streaming adapter. A serving
codec must additionally satisfy the current ChatCodec protocol in ocai.chat.facade.
"""

from __future__ import annotations

from typing import Any

from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse


class EchoChatCodec:
    """Translate canonical JSON documents to and from typed chat objects."""

    def encode(self, request: ChatRequest) -> dict[str, Any]:
        """Serialize a canonical request into the fictional wire format."""
        return request.to_dict()

    def decode_request(self, raw: dict[str, Any]) -> ChatRequest:
        """Read a canonical request document, retaining unknown part tags."""
        return ChatRequest.from_dict(raw)

    def decode(self, raw: dict[str, Any]) -> ChatResponse:
        """Read a canonical response document, retaining unknown part tags."""
        return ChatResponse.from_dict(raw)
