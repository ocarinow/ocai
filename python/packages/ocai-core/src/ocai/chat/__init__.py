"""`ocai.chat` — the chat capability contract (architecture §3).

The port (`ChatModel`), the canonical chat IR (`ocai.chat.types`), the
canonical graph nodes (`ocai.chat.canonical`), and the wire-backed facade
(`WireChatModel`). Everything except `model.py` depends on `ocai.core`
only; `model.py` is the one designated module that composes
convert/runtime/wire behind the port.

The curated exports below are the user-facing surface: build a
`ChatRequest` from `Message`s and `Tool`s, call any `ChatModel`, receive a
`CallResult[ChatResponse]` or a `ChatStream` of `ChatChunk`s.
"""

from ocai.chat.canonical import CANONICAL_CHAT_CHUNK
from ocai.chat.canonical import CANONICAL_CHAT_REQUEST
from ocai.chat.canonical import CANONICAL_CHAT_RESPONSE
from ocai.chat.canonical import OCAI_INTERFACE
from ocai.chat.canonical import REVISION
from ocai.chat.model import WireChatModel
from ocai.chat.protocol import ChatModel
from ocai.chat.types import AsyncChatStream
from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatConfig
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import ChatStream
from ocai.chat.types import FinishInfo
from ocai.chat.types import Message
from ocai.chat.types import Part
from ocai.chat.types import Role
from ocai.chat.types import StreamAccumulator
from ocai.chat.types import StreamEnd
from ocai.chat.types import Tool
from ocai.chat.types import ToolChoice
from ocai.chat.types import Usage

__all__ = [
    "CANONICAL_CHAT_CHUNK",
    "CANONICAL_CHAT_REQUEST",
    "CANONICAL_CHAT_RESPONSE",
    "OCAI_INTERFACE",
    "REVISION",
    "AsyncChatStream",
    "ChatChunk",
    "ChatConfig",
    "ChatModel",
    "ChatRequest",
    "ChatResponse",
    "ChatStream",
    "FinishInfo",
    "Message",
    "Part",
    "Role",
    "StreamAccumulator",
    "StreamEnd",
    "Tool",
    "ToolChoice",
    "Usage",
    "WireChatModel",
]
