"""The `openai/responses` interface codec — identity + mapping [stub].

Declares the `/responses` interface's three `NodeId`s (its graph identity is
real even while its mapping is stubbed — the catalog must know the interface
exists for pinning and resolution) and the codec skeleton whose method
contracts mirror `ocai.openai.chat_completions.codec.ChatCompletionsCodec`.

This sibling interface is the target of the flagship interface-migration WU:
`Catalog.resolve` steering a chat call from `openai/chat_completions` to
`openai/responses` with **no user code change**, every difference visible in
the `FidelityReport`. The mapping is item-model-shaped (see
`ocai.openai.responses.wire`): items carry stable ids → part `id` fields;
`previous_response_id` and `encrypted_content` are `ProviderRef` anchors that
must be reported `UNSUPPORTED` when they cross any other interface (§2.4).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatRequest
from ocai.convert.graph import EdgeOutput
from ocai.core.errors import OcaiError
from ocai.core.identity import CHAT_CHUNK
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import CHAT_RESPONSE
from ocai.core.identity import NodeId
from ocai.core.identity import Status
from ocai.core.identity import canonical_node

# Interface coordinates. Sibling of chat_completions, NOT a version of it —
# the coordinate the old SchemaVersion was missing (§2.1).
PROVIDER = "openai"
INTERFACE = "responses"
TAG = "2025-03"
_RELEASED = date(2025, 3, 11)

RESPONSES_PATH = "/v1/responses"

# The interface's three graph nodes — one per message shape.
RESPONSES_REQUEST = NodeId(
    provider=PROVIDER,
    interface=INTERFACE,
    tag=TAG,
    shape=CHAT_REQUEST,
    released=_RELEASED,
    status=Status.STABLE,
)
RESPONSES_RESPONSE = NodeId(
    provider=PROVIDER,
    interface=INTERFACE,
    tag=TAG,
    shape=CHAT_RESPONSE,
    released=_RELEASED,
    status=Status.STABLE,
)
RESPONSES_CHUNK = NodeId(
    provider=PROVIDER,
    interface=INTERFACE,
    tag=TAG,
    shape=CHAT_CHUNK,
    released=_RELEASED,
    status=Status.STABLE,
)

# The canonical endpoints this interface's edges will connect to.
CANONICAL_REQUEST = canonical_node(CHAT_REQUEST)
CANONICAL_RESPONSE = canonical_node(CHAT_RESPONSE)
CANONICAL_CHUNK = canonical_node(CHAT_CHUNK)


class ResponsesCodec:
    """The `openai/responses` dialect codec — pure mapping, no I/O [stub].

    Same shape and obligations as `ChatCompletionsCodec`: every conversion
    returns an `EdgeOutput` with its loss/shift records, unknown input never raises,
    and the codec expands only its own `provider_options` namespace
    (`"openai.responses"`).
    """

    provider = PROVIDER
    interface = INTERFACE
    request_node = RESPONSES_REQUEST
    response_node = RESPONSES_RESPONSE
    chunk_node = RESPONSES_CHUNK

    def native_path(self, model: str) -> str:
        """Return the first-party endpoint path for a Responses call.

        Args:
            model: The target model name (travels in the request body).

        Returns:
            The Responses API path.
        """
        return RESPONSES_PATH

    def encode_request(self, request: ChatRequest) -> EdgeOutput:
        """Encode a canonical `ChatRequest` into a `/responses` body.

        Args:
            request: The canonical request to encode.

        Returns:
            An `EdgeOutput` with the wire request dict and this edge's records.
        """
        # TODO: messages → input items (message / function_call /
        # function_call_output); PartReasoning.opaque → encrypted_content;
        # ResponseInfo anchor → previous_response_id; config.output →
        # text.format; config.reasoning → reasoning.
        raise NotImplementedError

    def decode_response(self, payload: dict[str, Any]) -> EdgeOutput:
        """Decode a `/responses` body into a canonical `ChatResponse`.

        Args:
            payload: The raw response body, already JSON-parsed.

        Returns:
            An `EdgeOutput` with the canonical `ChatResponse` and this
            edge's records.
        """
        # TODO: output items → parts (message → PartText/PartRefusal;
        # function_call → PartToolCall; reasoning → ONE PartReasoning with
        # summary + opaque ProviderRef; built-in calls → PartServerToolCall);
        # response id → ResponseInfo ProviderRef anchor (kind="response_id").
        raise NotImplementedError

    def decode_event(self, event: str | None, data: str) -> ChatChunk | None:
        """Decode one `/responses` semantic SSE event into a `ChatChunk`.

        Args:
            event: The SSE `event:` name (`response.output_text.delta`, …).
            data: The SSE `data:` payload.

        Returns:
            The canonical chunk, or `None` when the frame surfaces nothing.
        """
        # TODO: response.output_item.added → PART_START;
        # response.output_text.delta → DeltaText; response.completed →
        # FINISH/usage; unknown event names must degrade, never raise.
        raise NotImplementedError

    def map_error(self, status: int | None, body: dict[str, Any] | None) -> OcaiError | None:
        """Refine a Responses error body onto the precise error taxonomy.

        Args:
            status: The HTTP status of the failed response, if known.
            body: The parsed error body, if any.

        Returns:
            A precise `OcaiError`, or `None` to defer to the neutral mapping.
        """
        # TODO: same {"error": {...}} envelope as chat_completions — share the
        # refinement once this interface is exercised.
        raise NotImplementedError
