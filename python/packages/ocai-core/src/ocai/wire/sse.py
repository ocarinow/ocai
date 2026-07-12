"""Server-Sent Events: the `SSEvent` frame value object and the sans-io parser.

Both sit **below** the canonical IR, like `HttpRequest` / `HttpResponse`
(`ocai.wire.http`): an SSE frame is HTTP framing, not provider-neutral
semantics. The canonical streaming type is `ChatChunk`; a dialect codec's
`decode_event` produces it *from* these frames, and `StreamEdge` transducers
(`ocai.convert`) convert between chunk shapes — nothing here interprets a
payload.

`SSEParser` is deliberately **sans-io**: the drivers (`ocai.runtime.drivers`)
pump transport byte chunks into `feed` and forward the completed frames; the
parser never reads a socket, so it is trivially testable and shared verbatim
by the sync and async pipelines.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class SSEvent:
    """A single Server-Sent Events frame.

    Built by `SSEParser` from the wire (`data` is then the raw payload
    string), and re-serializable back to the `event:`/`data:` wire format
    (used by recorded-fixture tooling). Decoding the payload (typically JSON)
    into a canonical `ChatChunk` is the codec's job, so this stays
    provider-neutral.

    Attributes:
        data: The event payload — the raw `data:` string as parsed from the
            wire, or a dict when an event is constructed for serialization.
        event: The optional SSE event name (the `event:` line), when present.
        id: The optional SSE event id (the `id:` line), when present.
    """

    data: dict[str, Any] | str
    event: str | None = None
    id: str | None = None

    def serialize(self, encoder: Callable[[dict[str, Any]], str] = json.dumps) -> str:
        """Render the event to the SSE wire format.

        Emits an `event:` line and an `id:` line when set, followed by a
        `data:` line terminated by a blank line. Dict payloads are encoded via
        `encoder`; string payloads are written as-is.

        Args:
            encoder: Callable used to encode a dict `data` payload to a
                string; defaults to `json.dumps`.

        Returns:
            The SSE-formatted text for this event.
        """
        chunk = ""
        if self.event:
            chunk += f"event: {self.event}\n"
        if self.id:
            chunk += f"id: {self.id}\n"

        data_str = encoder(self.data) if isinstance(self.data, dict) else self.data
        chunk += f"data: {data_str}\n\n"

        return chunk


class SSEParser:
    """Incremental Server-Sent-Events parser, safe across network chunk splits.

    A **pure** SSE wire parser: feed raw bytes as they arrive, get back
    completed `SSEvent` frames. It handles:

    - **chunk boundaries** — a line split across two `feed` calls is buffered
      until its terminating newline arrives;
    - **comment / keep-alive lines** — lines beginning with `:` are ignored;
    - **multi-line data** — consecutive `data:` lines in one event are joined
      with `\\n` per the SSE spec;
    - **the `event:` / `id:` lines** — captured onto the emitted `SSEvent`.

    It deliberately knows **nothing about end-of-stream**: a provider's
    terminal signal — OpenAI's `[DONE]` data sentinel, Anthropic's
    `message_stop` event — is a *dialect* concern, so it is emitted as an
    ordinary `SSEvent` and recognized by the codec's `decode_event`, never
    special-cased here. Likewise the `data` payload is left as a raw string;
    JSON decoding is the codec's job. That keeps this parser provider-neutral.
    """

    def __init__(self) -> None:
        """Construct a parser with empty buffers."""
        self._buf = ""  # bytes not yet terminated by a newline
        self._data: list[str] = []  # data fields of the in-progress event
        self._event: str | None = None  # event: name of the in-progress event
        self._id: str | None = None  # id: of the in-progress event

    def feed(self, chunk: bytes | str) -> list[SSEvent]:
        """Consume a chunk; return any `SSEvent` frames completed by it.

        Args:
            chunk: The next raw slice of the response body, as delivered by
                the transport (any split point is safe).

        Returns:
            The frames whose terminating blank line arrived within `chunk`.
        """
        text = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
        self._buf += text
        events: list[SSEvent] = []
        # Process only whole lines; keep any trailing partial line in the buffer.
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.rstrip("\r")
            completed = self._consume_line(line)
            if completed is not None:
                events.append(completed)
        return events

    def _consume_line(self, line: str) -> SSEvent | None:
        """Consume one whole line; return a frame if `line` completed one."""
        if line == "":
            # Blank line = event boundary: dispatch what we've accumulated.
            if not self._data:
                return None
            payload = "\n".join(self._data)
            event, ev_id = self._event, self._id
            self._data, self._event, self._id = [], None, None
            return SSEvent(data=payload, event=event, id=ev_id)
        if line.startswith(":"):
            # Comment / keep-alive line — ignore.
            return None
        field, _, value = line.partition(":")
        # A single leading space after the colon is part of the syntax, not data.
        value = value[1:] if value.startswith(" ") else value
        if field == "data":
            self._data.append(value)
        elif field == "event":
            self._event = value
        elif field == "id":
            self._id = value
        # Other fields (retry:) are not needed for LLM streams.
        return None
