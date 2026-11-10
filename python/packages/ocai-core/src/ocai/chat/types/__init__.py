"""The canonical chat IR (architecture §3.1) — the types the port speaks.

Everything here is a pure-stdlib data contract depending on `ocai.core`
only. The surface, by module:

- `role` — the open role code (`Role`, `decode_role`/`encode_role`).
- `annotations` — span-anchored citations (`Span`, `Annotation`).
- `parts` — the full part taxonomy, its open `PART_REGISTRY`, and the
  lifecycle/kind constant vocabularies.
- `message` — `Message(role, parts)` with constructor sugar and the derived
  `.text` view.
- `tools` — `Tool` (from_function / from_schema / from_dict) and
  `ToolChoice`.
- `config` — the full `ChatConfig` and its typed sub-configs.
- `finish` — `FinishInfo`, `FinishReason`, and the detail union.
- `usage` — the dimensional `Consumption`/`Usage` model.
- `request` / `response` — the pure graph payloads (`ChatRequest`,
  `ChatResponse`, `ResponseInfo`).
- `stream` — `ChatChunk`, the `Delta` union, `StreamEnd`,
  `StreamAccumulator` (the fold law), and the `ChatStream` wrappers.
"""

from ocai.chat.types.annotations import Annotation
from ocai.chat.types.annotations import Span
from ocai.chat.types.config import AudioOutputConfig
from ocai.chat.types.config import CacheConfig
from ocai.chat.types.config import CacheHint
from ocai.chat.types.config import ChatConfig
from ocai.chat.types.config import OutputFormat
from ocai.chat.types.config import OutputMode
from ocai.chat.types.config import ReasoningConfig
from ocai.chat.types.config import ReasoningEffort
from ocai.chat.types.finish import DETAIL_REGISTRY
from ocai.chat.types.finish import DetailOpaque
from ocai.chat.types.finish import DetailType
from ocai.chat.types.finish import ErrorDetail
from ocai.chat.types.finish import FinishDetail
from ocai.chat.types.finish import FinishInfo
from ocai.chat.types.finish import FinishReason
from ocai.chat.types.finish import IncompleteDetail
from ocai.chat.types.finish import RefusalDetail
from ocai.chat.types.finish import SafetyDetail
from ocai.chat.types.finish import SafetyRating
from ocai.chat.types.finish import cast_detail
from ocai.chat.types.message import Message
from ocai.chat.types.parts import PART_REGISTRY
from ocai.chat.types.parts import ExecutedBy
from ocai.chat.types.parts import Part
from ocai.chat.types.parts import PartAudio
from ocai.chat.types.parts import PartBase
from ocai.chat.types.parts import PartDocument
from ocai.chat.types.parts import PartImage
from ocai.chat.types.parts import PartOpaque
from ocai.chat.types.parts import PartReasoning
from ocai.chat.types.parts import PartRefusal
from ocai.chat.types.parts import PartServerToolCall
from ocai.chat.types.parts import PartServerToolResult
from ocai.chat.types.parts import PartText
from ocai.chat.types.parts import PartToolCall
from ocai.chat.types.parts import PartToolResult
from ocai.chat.types.parts import PartType
from ocai.chat.types.parts import PartUnknown
from ocai.chat.types.parts import PartVideo
from ocai.chat.types.parts import ServerToolKind
from ocai.chat.types.parts import ToolCallStatus
from ocai.chat.types.parts import cast_part
from ocai.chat.types.request import ChatRequest
from ocai.chat.types.response import ChatResponse
from ocai.chat.types.response import ResponseInfo
from ocai.chat.types.role import Role
from ocai.chat.types.role import decode_role
from ocai.chat.types.role import encode_role
from ocai.chat.types.stream import DELTA_REGISTRY
from ocai.chat.types.stream import INCOMPLETE_EXTENSION
from ocai.chat.types.stream import SIGNATURE_BUFFER_EXTENSION
from ocai.chat.types.stream import AsyncChatStream
from ocai.chat.types.stream import ChatChunk
from ocai.chat.types.stream import ChatStream
from ocai.chat.types.stream import ChunkType
from ocai.chat.types.stream import Delta
from ocai.chat.types.stream import DeltaAnnotation
from ocai.chat.types.stream import DeltaBlob
from ocai.chat.types.stream import DeltaReasoning
from ocai.chat.types.stream import DeltaRefusal
from ocai.chat.types.stream import DeltaSignature
from ocai.chat.types.stream import DeltaText
from ocai.chat.types.stream import DeltaToolArgs
from ocai.chat.types.stream import DeltaType
from ocai.chat.types.stream import DeltaUnknown
from ocai.chat.types.stream import ErrorInfo
from ocai.chat.types.stream import StreamAccumulator
from ocai.chat.types.stream import StreamEnd
from ocai.chat.types.stream import StreamOutcome
from ocai.chat.types.stream import cast_delta
from ocai.chat.types.tools import Tool
from ocai.chat.types.tools import ToolChoice
from ocai.chat.types.tools import ToolChoiceMode
from ocai.chat.types.usage import Consumption
from ocai.chat.types.usage import Usage
from ocai.chat.types.usage import UsageModality
from ocai.chat.types.usage import UsageSource
from ocai.chat.types.usage import UsageUnit

__all__ = [
    "DELTA_REGISTRY",
    "DETAIL_REGISTRY",
    "INCOMPLETE_EXTENSION",
    "PART_REGISTRY",
    "SIGNATURE_BUFFER_EXTENSION",
    "Annotation",
    "AsyncChatStream",
    "AudioOutputConfig",
    "CacheConfig",
    "CacheHint",
    "ChatChunk",
    "ChatConfig",
    "ChatRequest",
    "ChatResponse",
    "ChatStream",
    "ChunkType",
    "Consumption",
    "Delta",
    "DeltaAnnotation",
    "DeltaBlob",
    "DeltaReasoning",
    "DeltaRefusal",
    "DeltaSignature",
    "DeltaText",
    "DeltaToolArgs",
    "DeltaType",
    "DeltaUnknown",
    "DetailOpaque",
    "DetailType",
    "ErrorDetail",
    "ErrorInfo",
    "ExecutedBy",
    "FinishDetail",
    "FinishInfo",
    "FinishReason",
    "IncompleteDetail",
    "Message",
    "OutputFormat",
    "OutputMode",
    "Part",
    "PartAudio",
    "PartBase",
    "PartDocument",
    "PartImage",
    "PartOpaque",
    "PartReasoning",
    "PartRefusal",
    "PartServerToolCall",
    "PartServerToolResult",
    "PartText",
    "PartToolCall",
    "PartToolResult",
    "PartType",
    "PartUnknown",
    "PartVideo",
    "ReasoningConfig",
    "ReasoningEffort",
    "RefusalDetail",
    "ResponseInfo",
    "Role",
    "SafetyDetail",
    "SafetyRating",
    "ServerToolKind",
    "Span",
    "StreamAccumulator",
    "StreamEnd",
    "StreamOutcome",
    "Tool",
    "ToolCallStatus",
    "ToolChoice",
    "ToolChoiceMode",
    "Usage",
    "UsageModality",
    "UsageSource",
    "UsageUnit",
    "cast_delta",
    "cast_detail",
    "cast_part",
    "decode_role",
    "encode_role",
]
