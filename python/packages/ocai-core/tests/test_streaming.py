"""Streaming: recorded SSE bodies → neutral frames → canonical `ChatChunk`s.

Proves the layering the rewrite settled (§6, §7): the wire layer's `SSEParser`
emits neutral frames with no provider knowledge, and each dialect codec's
`decode_event` turns them into canonical `ChatChunk`s — recognizing OpenAI's
`[DONE]` sentinel and Anthropic's `message_stop` event itself. The chunk-shape
`StreamEdge` transducers wrap the same decode and stamp monotonic `seq`
numbers, so streaming conversion joins the graph instead of bypassing it.
"""

from __future__ import annotations

from typing import Any

from ocai.anthropic.messages.codec import MessagesCodec
from ocai.chat.types import ChatChunk
from ocai.chat.types import ChunkType
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.openai.chat_completions.codec import ChatCompletionsStreamTransducer
from ocai.wire import SSEParser

# --- Recorded SSE bodies --------------------------------------------------

OPENAI_SSE = (
    b'data: {"choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}\n\n'
    b'data: {"choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}\n\n'
    b'data: {"choices":[{"index":0,"delta":{"content":" world"},"finish_reason":null}]}\n\n'
    b'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n'
    b"data: [DONE]\n\n"
)

ANTHROPIC_SSE = (
    b'event: message_start\ndata: {"type":"message_start","message":{"role":"assistant"}}\n\n'
    b"event: content_block_start\n"
    b'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}\n\n'
    b'event: ping\ndata: {"type":"ping"}\n\n'
    b"event: content_block_delta\n"
    b'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}\n\n'
    b"event: content_block_delta\n"
    b'data: {"type":"content_block_delta","index":0,'
    b'"delta":{"type":"text_delta","text":" there"}}\n\n'
    b'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n'
    b'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"}}\n\n'
    b'event: message_stop\ndata: {"type":"message_stop"}\n\n'
)


def _decode(codec: Any, body: bytes) -> list[ChatChunk]:
    """Pump one recorded SSE body through the parser and the codec."""
    chunks: list[ChatChunk] = []
    for frame in SSEParser().feed(body):
        chunk = codec.decode_event(frame.event, frame.data)
        if chunk is not None:
            chunks.append(chunk)
    return chunks


def _text(chunks: list[ChatChunk]) -> str:
    return "".join(c.delta.text for c in chunks if c.type == ChunkType.PART_DELTA)


# --- OpenAI ----------------------------------------------------------------


def test_openai_sse_decodes_to_canonical_chunks() -> None:
    chunks = _decode(ChatCompletionsCodec(), OPENAI_SSE)

    types = [c.type for c in chunks]
    assert types == [
        ChunkType.STREAM_START,
        ChunkType.PART_DELTA,
        ChunkType.PART_DELTA,
        ChunkType.FINISH,
    ]  # the [DONE] sentinel decoded to None and was skipped
    assert _text(chunks) == "Hello world"
    finish = chunks[-1].finish
    assert finish is not None
    assert finish.reason == "complete"  # canonical open code...
    assert finish.native == "stop"  # ...with the verbatim native lane


def test_openai_transducer_stamps_seq_and_reports() -> None:
    # The StreamEdge factory product: same decode, plus seq stamping and the
    # per-traversal EdgeReport handed back at flush (honesty parity, §4.1).
    transducer = ChatCompletionsStreamTransducer()
    chunks = [chunk for frame in SSEParser().feed(OPENAI_SSE) for chunk in transducer.feed(frame)]
    tail, report = transducer.flush()

    assert [c.seq for c in chunks] == [0, 1, 2, 3]
    assert tail == []  # terminal StreamEnd chunk is TODO in the skeleton
    assert report.lossless


# --- Anthropic ---------------------------------------------------------------


def test_anthropic_sse_decodes_to_canonical_chunks() -> None:
    chunks = _decode(MessagesCodec(), ANTHROPIC_SSE)

    types = [c.type for c in chunks]
    assert types == [
        ChunkType.STREAM_START,
        ChunkType.PART_START,
        # ping decoded to None and was skipped
        ChunkType.PART_DELTA,
        ChunkType.PART_DELTA,
        ChunkType.PART_STOP,
        ChunkType.FINISH,
        ChunkType.STREAM_STOP,
    ]
    assert _text(chunks) == "Hi there"
    finish = next(c for c in chunks if c.type == ChunkType.FINISH).finish
    assert finish is not None
    assert finish.reason == "complete"
    assert finish.native == "end_turn"
