"""Recorded binary vectors qualify framing, independently of provider semantics."""

from __future__ import annotations

import base64
import json
from collections.abc import AsyncGenerator
from collections.abc import AsyncIterator
from collections.abc import Generator
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID
from zlib import crc32

import httpx
import pytest
import respx

from ocai.core import ApiKey
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import NodeId
from ocai.core.traits import DialectTraits
from ocai.runtime.binding import Binding
from ocai.runtime.drivers import AsyncDriver
from ocai.runtime.drivers import SyncDriver
from ocai.wire.eventstream import EventStreamFrame
from ocai.wire.eventstream import EventStreamParser
from ocai.wire.eventstream import EventStreamProtocolError
from ocai.wire.eventstream import eventstream_framing
from ocai.wire.hosting import Direct
from ocai.wire.hosting import EndpointSpec
from ocai.wire.hosting import Operation
from ocai.wire.transport import HttpxTransport

PAIR: dict[str, Any] = json.loads(
    (Path(__file__).parent / "http/eventstream_frames.json").read_text()
)
WIRE = base64.b64decode(PAIR["response"]["body"]["data"], validate=True)


def _plain(frame: EventStreamFrame) -> dict[str, Any]:
    return {
        "headers": [
            {
                "name": header.name,
                "type_code": header.type_code,
                "value": {"hex": header.value.hex()}
                if isinstance(header.value, bytes)
                else {"uuid": str(header.value)}
                if isinstance(header.value, UUID)
                else header.value,
            }
            for header in frame.headers
        ],
        "payload_hex": frame.payload.hex(),
    }


@pytest.mark.parametrize("split", range(len(WIRE) + 1))
def test_every_split_preserves_typed_frames(split: int) -> None:
    parser = EventStreamParser()
    frames = parser.feed(WIRE[:split]) + parser.feed(WIRE[split:]) + parser.finish()
    assert [_plain(frame) for frame in frames] == PAIR["expected"]
    assert parser.buffered_bytes == 0 and parser.finish() == []
    parser.close()


def test_one_byte_chunks_and_independent_factories() -> None:
    selection = eventstream_framing()
    left, right = selection.build(), selection.build()
    assert left is not right
    frames: list[EventStreamFrame] = []
    for value in WIRE:
        frames.extend(left.feed(bytes([value])))
    assert [_plain(frame) for frame in frames] == PAIR["expected"]
    assert right.finish() == []
    assert selection.configuration_id != eventstream_framing(1024).configuration_id
    left.close()
    right.close()


@pytest.mark.parametrize("vector", PAIR["corrupt"], ids=lambda value: value["name"])
def test_corrupt_frames_fail_with_verified_prefix(vector: dict[str, Any]) -> None:
    prefix = WIRE[: PAIR["frame_sizes"][0]]
    broken = base64.b64decode(vector["body"]["data"], validate=True)
    for split in range(len(broken) + 1):
        parser = EventStreamParser()
        accepted: list[EventStreamFrame] = []
        with pytest.raises(EventStreamProtocolError) as exc:
            accepted.extend(parser.feed(prefix + broken[:split]))
            accepted.extend(parser.feed(broken[split:]))
            parser.finish()
        assert [_plain(frame) for frame in (*accepted, *exc.value.completed)] == PAIR["expected"][
            :1
        ]
        assert parser.buffered_bytes == 0
        with pytest.raises(EventStreamProtocolError):
            parser.feed(WIRE)
        with pytest.raises(EventStreamProtocolError):
            parser.finish()
        parser.close()


@pytest.mark.parametrize("length", range(1, PAIR["frame_sizes"][0]))
def test_each_truncation_rejects_eof(length: int) -> None:
    parser = EventStreamParser()
    assert parser.feed(WIRE[:length]) == []
    with pytest.raises(EventStreamProtocolError, match="truncated"):
        parser.finish()
    assert parser.buffered_bytes == 0


def test_local_limit_is_enforced_at_validated_prelude() -> None:
    prelude = (100_000_000).to_bytes(4, "big") + bytes(4)
    checked = prelude + crc32(prelude).to_bytes(4, "big")
    parser = EventStreamParser(1024)
    with pytest.raises(EventStreamProtocolError) as exc:
        parser.feed(checked + bytes(2048))
    assert exc.value.code == "eventstream_resource_limit"
    assert parser.buffered_bytes == 0
    parser = EventStreamParser(1024)
    with pytest.raises(EventStreamProtocolError, match="prelude CRC"):
        parser.feed(prelude + bytes(4))
    assert parser.buffered_bytes == 0


def test_close_discards_bytes_without_success() -> None:
    parser = EventStreamParser()
    assert parser.feed(WIRE[:5]) == [] and parser.buffered_bytes == 5
    parser.close()
    parser.close()
    assert parser.buffered_bytes == 0
    with pytest.raises(EventStreamProtocolError):
        parser.finish()


@pytest.mark.parametrize("limit", [0, 15, -1, True, 2**32])
def test_invalid_local_limits_rejected(limit: int) -> None:
    with pytest.raises(ValueError):
        EventStreamParser(limit)
    with pytest.raises(ValueError):
        eventstream_framing(limit)


class Body(httpx.SyncByteStream, httpx.AsyncByteStream):
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.closed = 0

    def __iter__(self) -> Iterator[bytes]:
        for offset in range(0, len(self.data), 7):
            yield self.data[offset : offset + 7]

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self:
            yield chunk

    def close(self) -> None:
        self.closed += 1

    async def aclose(self) -> None:
        self.closed += 1


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("mode", ["complete", "close", "truncated"])
@respx.mock
async def test_driver_framing_and_upstream_ownership(asynchronous: bool, mode: str) -> None:
    body = Body(WIRE[:-1] if mode == "truncated" else WIRE)
    seen: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert json.loads(request.content) == PAIR["request"]["json"]
        return httpx.Response(200, headers=PAIR["response"]["headers"], stream=body)

    respx.post(PAIR["request"]["url"]).mock(side_effect=respond)
    transport = HttpxTransport()
    binding = Binding(Direct("https://framing.example.test"), ApiKey("synthetic-key"), transport)
    spec = EndpointSpec(
        NodeId("test", "events", "2026-11", CHAT_REQUEST, date(2026, 11, 1)),
        DialectTraits(vendor="test"),
        Operation("chat", "generative", streaming=True),
        "synthetic",
        "/events",
    )
    frames: list[EventStreamFrame] = []
    failed = False
    try:
        if asynchronous:
            stream = AsyncDriver(binding).stream(
                spec=spec, payload=PAIR["request"]["json"], framing=eventstream_framing()
            )
            try:
                async for frame in stream:
                    frames.append(frame)
                    if mode == "close":
                        break
            finally:
                assert isinstance(stream, AsyncGenerator)
                await stream.aclose()
        else:
            sync_stream = SyncDriver(binding).stream(
                spec=spec, payload=PAIR["request"]["json"], framing=eventstream_framing()
            )
            try:
                for frame in sync_stream:
                    frames.append(frame)
                    if mode == "close":
                        break
            finally:
                assert isinstance(sync_stream, Generator)
                sync_stream.close()
    except EventStreamProtocolError:
        failed = True
    finally:
        transport.close()
        await transport.aclose()
    assert failed == (mode == "truncated")
    assert body.closed == 1 and len(seen) == 1
    assert [_plain(frame) for frame in frames] == PAIR["expected"][
        : 1 if mode == "close" else 2 if mode == "truncated" else 3
    ]
