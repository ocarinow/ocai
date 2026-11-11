"""Pure configuration for independently qualified Chat Completions variants."""

from dataclasses import dataclass

from ocai.core.identity import CHAT_CHUNK
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import CHAT_RESPONSE
from ocai.core.identity import NodeId
from ocai.core.traits import DialectTraits


@dataclass(frozen=True)
class ChatCompletionsVariant:
    """Select identity and compatible field lanes without inheriting edge contracts.

    The owning plugin must publish its own census, fixtures and profiles. This
    configuration registers no catalog component and performs no provider I/O.
    """

    request_node: NodeId
    response_node: NodeId
    chunk_node: NodeId
    traits: DialectTraits
    path: str
    reasoning_field: str | None = None
    max_tokens_field: str = "max_completion_tokens"
    knob_ranges: tuple[tuple[str, float, float], ...] | None = None
    finish_reasons: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        """Reject inconsistent identities rather than minting mixed-provider evidence."""
        nodes = (self.request_node, self.response_node, self.chunk_node)
        identity = {(node.provider, node.interface, node.tag) for node in nodes}
        if len(identity) != 1 or tuple(node.shape for node in nodes) != (
            CHAT_REQUEST,
            CHAT_RESPONSE,
            CHAT_CHUNK,
        ):
            raise ValueError("a compatible variant requires one identity and all three chat shapes")
        if self.traits.vendor != self.request_node.provider:
            raise ValueError("variant traits must preserve the publishing provider")
