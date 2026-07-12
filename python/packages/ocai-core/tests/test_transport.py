"""Wire: SSE parser correctness + the `HttpxTransport` leaf over recorded traffic.

The SSE parser is sans-io and provider-neutral (sentinels belong to dialects);
the transport does a single send, applies no credential of its own (the driver
applies `Credential.apply` at the leaf), and maps non-2xx onto the shared
taxonomy so policies branch on error types, never status codes (rule 10: respx
recordings, no live keys, no provider-SDK mocks).
"""

from __future__ import annotations

import httpx
import pytest
import respx

from ocai.core import ApiKey
from ocai.core import RateLimitError
from ocai.wire import HttpRequest
from ocai.wire import HttpxTransport
from ocai.wire import SSEParser
from ocai.wire import SSEvent

# --- SSE parser: chunk-boundary safety, comments, [DONE], event/id --------


def test_sse_parser_handles_split_chunks() -> None:
    parser = SSEParser()
    # A single event delivered across three network chunks (split mid-line).
    assert parser.feed('data: {"a":') == []
    assert parser.feed("1}\n") == []
    assert parser.feed("\n") == [SSEvent(data='{"a":1}')]


def test_sse_parser_ignores_comments_and_is_sentinel_agnostic() -> None:
    # The parser knows nothing about end-of-stream: a provider sentinel like
    # OpenAI's [DONE] is emitted as an ordinary frame for the codec to recognize.
    parser = SSEParser()
    out = parser.feed(': keep-alive\n\ndata: {"x":1}\n\ndata: [DONE]\n\n')
    assert out == [SSEvent(data='{"x":1}'), SSEvent(data="[DONE]")]
    assert not hasattr(parser, "done")


def test_sse_parser_joins_multiline_data() -> None:
    parser = SSEParser()
    assert parser.feed("data: line1\ndata: line2\n\n") == [SSEvent(data="line1\nline2")]


def test_sse_parser_captures_event_and_id() -> None:
    # Anthropic-style: the event type rides on the `event:` line.
    parser = SSEParser()
    out = parser.feed('event: content_block_delta\nid: 7\ndata: {"d":1}\n\n')
    assert out == [SSEvent(data='{"d":1}', event="content_block_delta", id="7")]


# --- HttpxTransport: real wire, no SDK, no live key ------------------------

URL = "https://api.example.test/v1/chat"


@respx.mock
async def test_async_send_returns_detached_response() -> None:
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"ok": True}))

    request = HttpRequest.from_json("POST", URL, {"model": "m"})
    # Credential applied at the leaf, per attempt (rule 13) — by the caller
    # (the driver), never by the transport itself.
    ApiKey("sk-test").apply(request)
    transport = HttpxTransport()
    response = await transport.send(request)
    await transport.aclose()

    assert response.status == 200
    assert response.json() == {"ok": True}
    sent = route.calls.last.request
    assert sent.headers["authorization"] == "Bearer sk-test"
    assert sent.headers["content-type"] == "application/json"


@respx.mock
def test_sync_send_maps_429_to_rate_limit_error() -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(
            429, headers={"retry-after": "1.5"}, json={"error": "slow down"}
        )
    )
    transport = HttpxTransport(provider="openai")
    with pytest.raises(RateLimitError) as exc:
        transport.send_sync(HttpRequest.from_json("POST", URL, {"model": "m"}))
    transport.close()
    assert exc.value.status == 429
    assert exc.value.retry_after == 1.5
    assert exc.value.provider == "openai"


@respx.mock
async def test_async_send_maps_429_too() -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(429, headers={"retry-after": "2"}, json={"error": "later"})
    )
    async with HttpxTransport() as transport:
        with pytest.raises(RateLimitError) as exc:
            await transport.send(HttpRequest.from_json("POST", URL, {"model": "m"}))
    assert exc.value.retry_after == 2.0
