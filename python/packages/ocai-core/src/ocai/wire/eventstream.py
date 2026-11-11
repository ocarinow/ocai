"""Bounded, sans-io Amazon EventStream framing without payload interpretation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID
from zlib import crc32

from ocai.core.errors import StreamProtocolError
from ocai.wire.framing import StreamFraming

_DEFAULT_LIMIT = 64 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class EventStreamHeader:
    """A typed wire header; timestamp values retain exact signed milliseconds."""

    name: str
    type_code: int
    value: bool | int | bytes | str | UUID


@dataclass(frozen=True, slots=True)
class EventStreamFrame:
    """One CRC-verified message, including opaque payload and typed headers."""

    headers: tuple[EventStreamHeader, ...]
    payload: bytes


class EventStreamProtocolError(StreamProtocolError):
    """Framing failure with verified prefix frames from the failed feed only.

    Completed frames are explicit application evidence, never automatic payload
    logs. Frames returned by earlier feed calls are not repeated here.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_eventstream",
        completed: tuple[EventStreamFrame, ...] = (),
    ) -> None:
        """Retain the verified prefix without exposing corrupt bytes in the message."""
        super().__init__(message, code=code)
        self.completed = completed


def _headers(raw: bytes) -> tuple[EventStreamHeader, ...]:
    cursor = 0
    names: set[str] = set()
    headers: list[EventStreamHeader] = []

    def take(size: int) -> bytes:
        nonlocal cursor
        if cursor + size > len(raw):
            raise EventStreamProtocolError("truncated EventStream header")
        value = raw[cursor : cursor + size]
        cursor += size
        return value

    def text(size: int) -> str:
        try:
            return take(size).decode("utf-8")
        except UnicodeDecodeError:
            raise EventStreamProtocolError("invalid EventStream header UTF-8") from None

    while cursor < len(raw):
        length = take(1)[0]
        if length == 0:
            raise EventStreamProtocolError("empty EventStream header name")
        name = text(length)
        if name in names:
            raise EventStreamProtocolError("duplicate EventStream header")
        names.add(name)
        kind = take(1)[0]
        value: bool | int | bytes | str | UUID
        if kind in (0, 1):
            value = kind == 0
        elif kind in (2, 3, 4, 5, 8):
            width = {2: 1, 3: 2, 4: 4, 5: 8, 8: 8}[kind]
            value = int.from_bytes(take(width), "big", signed=True)
        elif kind in (6, 7):
            size = int.from_bytes(take(2), "big")
            value = take(size) if kind == 6 else text(size)
        elif kind == 9:
            value = UUID(bytes=take(16))
        else:
            # Unlike semantic event names, header type codes are not extensible.
            raise EventStreamProtocolError("unknown EventStream header type")
        headers.append(EventStreamHeader(name, kind, value))
    return tuple(headers)


class EventStreamParser:
    """Parse complete frames, buffering at most one configured-size frame.

    max_frame_bytes is a local resource budget, not a service quota. Service-only
    payload/header size limits are deliberately not checked by this client.
    After failure or close, a new parser is required. finish is idempotent after
    successful EOF; it validates framing only, never semantic completion.
    """

    def __init__(self, max_frame_bytes: int = _DEFAULT_LIMIT) -> None:
        """Create an empty parser with an explicit finite frame-memory budget."""
        if type(max_frame_bytes) is not int or not 16 <= max_frame_bytes <= 0xFFFFFFFF:
            raise ValueError("max_frame_bytes must be an integer between 16 and 2**32-1")
        self._limit = max_frame_bytes
        self._buffer = bytearray()
        self._length: int | None = None
        self._closed = False
        self._finished = False

    @property
    def buffered_bytes(self) -> int:
        """Return retained framing bytes, without exposing their content."""
        return len(self._buffer)

    def feed(self, chunk: bytes) -> list[EventStreamFrame]:
        """Consume bytes in order; reject malformed framing and retain its prefix.

        Args:
            chunk: An arbitrary slice of the incoming byte stream.

        Returns:
            Verified frames completed by this slice, in wire order.

        Raises:
            EventStreamProtocolError: On invalid framing, resource exhaustion or
                use after termination. completed contains this feed's valid prefix.
        """
        if self._closed or self._finished:
            raise EventStreamProtocolError("EventStream parser is terminated")
        frames: list[EventStreamFrame] = []
        offset = 0
        view = memoryview(chunk)
        try:
            while offset < len(view):
                target = self._length if self._length is not None else 12
                count = min(target - len(self._buffer), len(view) - offset)
                self._buffer.extend(view[offset : offset + count])
                offset += count
                if len(self._buffer) < target:
                    break
                if self._length is None:
                    if crc32(self._buffer[:8]) != int.from_bytes(self._buffer[8:12], "big"):
                        raise EventStreamProtocolError("invalid EventStream prelude CRC")
                    total = int.from_bytes(self._buffer[:4], "big")
                    header_size = int.from_bytes(self._buffer[4:8], "big")
                    if total < 16 or header_size > total - 16:
                        raise EventStreamProtocolError("invalid EventStream frame lengths")
                    if total > self._limit:
                        raise EventStreamProtocolError(
                            "EventStream frame exceeds local budget",
                            code="eventstream_resource_limit",
                        )
                    self._length = total
                if len(self._buffer) == self._length:
                    raw = bytes(self._buffer)
                    if crc32(raw[:-4]) != int.from_bytes(raw[-4:], "big"):
                        raise EventStreamProtocolError("invalid EventStream message CRC")
                    boundary = 12 + int.from_bytes(raw[4:8], "big")
                    frames.append(EventStreamFrame(_headers(raw[12:boundary]), raw[boundary:-4]))
                    self._buffer.clear()
                    self._length = None
        except EventStreamProtocolError as error:
            self.close()
            error.completed = tuple(frames)
            raise
        return frames

    def finish(self) -> list[EventStreamFrame]:
        """Validate EOF; never emit a synthetic provider terminal record."""
        if self._finished:
            return []
        if self._closed:
            raise EventStreamProtocolError("EventStream parser is terminated")
        if self._buffer:
            self.close()
            raise EventStreamProtocolError("truncated EventStream frame")
        self._finished = True
        return []

    def close(self) -> None:
        """Release partial bytes without interpreting them or emitting anything."""
        self._buffer.clear()
        self._length = None
        self._closed = True


def _parser(options: dict[str, Any]) -> EventStreamParser:
    if set(options) != {"max_frame_bytes"}:
        raise ValueError("EventStream framing requires only max_frame_bytes")
    limit = options["max_frame_bytes"]
    if not isinstance(limit, int):
        raise ValueError("max_frame_bytes must be an integer")
    return EventStreamParser(limit)


def eventstream_framing(max_frame_bytes: int = _DEFAULT_LIMIT) -> StreamFraming:
    """Select independent EventStream decoders with a fingerprinted local budget."""
    # Validate configuration now; decoder allocation remains per attempt.
    if type(max_frame_bytes) is not int or not 16 <= max_frame_bytes <= 0xFFFFFFFF:
        raise ValueError("max_frame_bytes must be an integer between 16 and 2**32-1")
    return StreamFraming("amazon-eventstream", _parser, {"max_frame_bytes": max_frame_bytes})
