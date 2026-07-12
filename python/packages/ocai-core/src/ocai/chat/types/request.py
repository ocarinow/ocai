"""The canonical chat request (architecture §3.1).

`ChatRequest` is what user code builds and what the conversion graph encodes
into a provider wire payload: the target model, the conversation, the tools
the model may call, the tool-choice policy, and the typed `ChatConfig`.

Its `from_dict` is a **true inverse** of `to_dict`: every nested payload
(messages, tools, tool choice, config) decodes back into its typed form, so
`ChatRequest.from_dict(req.to_dict())` is semantically equal to `req` under
`canonjson.semantic_equal` — the property the round-trip fixtures assert.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import ClassVar
from typing import Self

from ocai.chat.canonical import CANONICAL_CHAT_REQUEST
from ocai.chat.types.config import ChatConfig
from ocai.chat.types.message import Message
from ocai.chat.types.tools import Tool
from ocai.chat.types.tools import ToolChoice
from ocai.core.identity import NodeId
from ocai.core.ir import IRObject


@dataclass
class ChatRequest(IRObject):
    """A provider-neutral chat generation request — a pure graph payload.

    Enters the lifecycle at the port (`ChatModel.chat(request)`), rides the
    interceptor chain unchanged, and is encoded by the conversion graph from
    `CANONICAL_CHAT_REQUEST` to the resolved provider node. Single-response
    forever: there is no `n` — a request for multiple candidates fails
    admission at the codec.

    Attributes:
        model: The identifier of the model to invoke, passed to the
            provider verbatim.
        messages: The conversation so far, in order.
        tools: The tools the model may call, if any.
        tool_choice: The whether/which tool policy, if constrained.
        config: The typed generation configuration, if any.
    """

    object: ClassVar[str] = "chat.request"
    __node__: ClassVar[NodeId] = CANONICAL_CHAT_REQUEST

    model: str
    messages: list[Message]
    tools: list[Tool] | None = None
    tool_choice: ToolChoice | None = None
    config: ChatConfig | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `ChatRequest` from a serialized dict, totally.

        The true inverse of `to_dict`: `messages`, `tools`, `tool_choice`,
        and `config` all decode through their typed `from_dict`s (the old
        scaffold left tools/config as raw dicts — that asymmetry is dead).

        Args:
            data: A mapping with the request fields plus the common IR
                envelope keys; unknown keys sweep to `extensions`.

        Returns:
            The decoded `ChatRequest`.
        """
        tools = data.get("tools")
        choice = data.get("tool_choice")
        config = data.get("config")
        return cls(
            model=data.get("model", ""),
            messages=[
                Message.from_dict(item)
                for item in data.get("messages") or []
                if isinstance(item, dict)
            ],
            tools=(
                [Tool.from_dict(item) for item in tools if isinstance(item, dict)]
                if isinstance(tools, list)
                else None
            ),
            tool_choice=ToolChoice.from_dict(choice) if isinstance(choice, dict) else None,
            config=ChatConfig.from_dict(config) if isinstance(config, dict) else None,
            **cls._from_dict_common(data),
        )
