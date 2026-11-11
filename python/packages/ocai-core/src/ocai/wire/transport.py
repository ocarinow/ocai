"""Transports: the twin send ports and the httpx leaf — ocai owns the wire.

No provider SDKs anywhere (rule 12): an adapter builds a request dict, the
driver turns it into an `HttpRequest`, and one of these transports moves the
bytes. `Transport` (async) and `SyncTransport` (sync) are separate ports with
distinct method names so a single concrete class — `HttpxTransport` — can
implement **both**; `Binding.validate` checks the faces against the requested
driver mode at composition time.

This leaf does a **single send with no replay**: retry is a Decision-based
`RetryPolicy` (`ocai.wire.policies`) executed by the drivers, never hidden in
the transport. Credentials are applied by the driver onto the `HttpRequest`
just before send (`Credential.apply` at the leaf, per attempt), so this leaf
never holds a secret. Non-success responses are mapped onto the shared
taxonomy via `error_from_response` (layer 1); the dialect's body-aware
refinement (layer 2) happens above, in the driver.

httpx is imported **lazily** inside `HttpxTransport` and ships behind the
`[http]` extra, so importing `ocai.core` / `ocai.convert` (or running an
offline audit tool) never requires httpx to be installed.
"""

from __future__ import annotations

import json as _json
from collections.abc import AsyncIterator
from collections.abc import Iterator
from typing import Any
from typing import Protocol
from typing import runtime_checkable

from ocai.core.errors import OcaiError
from ocai.core.errors import TransientError
from ocai.core.errors import error_from_response
from ocai.core.ir import is_json_object
from ocai.wire.http import HttpRequest
from ocai.wire.http import HttpResponse


@runtime_checkable
class Transport(Protocol):
    """The async HTTP send port — the boundary `AsyncDriver` sends through.

    A `Transport` turns an `HttpRequest` into an `HttpResponse`. It is
    **provider- and capability-neutral** — chat, embeddings, and vector
    facades all send through one — and **client-agnostic**: the httpx
    implementation (`HttpxTransport`) is one concrete leaf; a fake transport
    for tests is just a class returning canned `HttpResponse`s (rule 10).

    This is the **async** port; the synchronous call path is the separate
    `SyncTransport` port. The split is deliberate: async-ness is confined to
    the one network call, so nothing above the transport is duplicated
    between the sync and async pipelines. Its `aclose` doubles as the
    `AsyncBackend` face anchor, so `Binding.validate` admits it for async
    mode by the same structural rule as any policy backend.

    `send` raises the shared taxonomy (`ocai.core.errors`) on a non-success
    status and returns only on 2xx, so retry policies branch on
    `TransientError` rather than re-reading status codes.
    """

    async def send(self, request: HttpRequest) -> HttpResponse:
        """Send `request`; return the response, or raise the error taxonomy.

        Args:
            request: The authenticated, fully-built wire request.

        Returns:
            The detached 2xx response snapshot.

        Raises:
            OcaiError: The coarse taxonomy classification of any non-2xx
                status or connection failure.
        """
        ...

    def stream(self, request: HttpRequest) -> AsyncIterator[bytes]:
        """Stream the response body as raw byte chunks (framing is above).

        Args:
            request: The authenticated, fully-built wire request.

        Returns:
            An async iterator of raw body chunks; the driver pumps them into
            the host-selected sans-io stream decoder.
        """
        ...

    async def aclose(self) -> None:
        """Release any underlying connection resources."""
        ...


@runtime_checkable
class SyncTransport(Protocol):
    """The synchronous twin of `Transport` — what `SyncDriver` sends through.

    Same contract as `Transport` — turn an `HttpRequest` into an
    `HttpResponse`, raising the shared taxonomy on non-2xx — but blocking, so
    a caller that is not in an event loop (a script, a notebook cell, a sync
    web handler) needs no `asyncio.run`. The method names are distinct from
    the async port (`send_sync`/`stream_sync`/`close`) so one class can
    implement **both** ports without name collisions; everything above the
    transport is shared between the two pipelines. `close` doubles as the
    `SyncBackend` face anchor for composition-time validation.
    """

    def send_sync(self, request: HttpRequest) -> HttpResponse:
        """Send `request` synchronously; return the response, or raise the taxonomy.

        Args:
            request: The authenticated, fully-built wire request.

        Returns:
            The detached 2xx response snapshot.

        Raises:
            OcaiError: The coarse taxonomy classification of any non-2xx
                status or connection failure.
        """
        ...

    def stream_sync(self, request: HttpRequest) -> Iterator[bytes]:
        """Stream the response body as raw byte chunks, synchronously.

        Args:
            request: The authenticated, fully-built wire request.

        Returns:
            An iterator of raw body chunks; the driver pumps them into the
            host-selected sans-io stream decoder.
        """
        ...

    def close(self) -> None:
        """Release any underlying connection resources."""
        ...


class HttpxTransport:
    """The concrete httpx leaf implementing **both** transport ports.

    Implements `Transport` (async: `send`/`stream`/`aclose`) and
    `SyncTransport` (sync: `send_sync`/`stream_sync`/`close`), so a single
    instance serves both drivers. The two underlying httpx clients
    (`AsyncClient`, `Client`) are created **lazily** on first use, so a
    purely-sync program never spins up an async client (and never binds an
    event loop) and vice versa.

    Owns timeout + connection-pool config. Does a single send (no
    retry/replay — compose a `RetryPolicy` for that) and maps non-success
    responses onto the shared taxonomy. Deals only in `HttpRequest` /
    `HttpResponse`; httpx never leaks past this class.
    """

    def __init__(
        self,
        *,
        timeout: float = 60.0,
        max_connections: int = 100,
        provider: str | None = None,
    ) -> None:
        """Configure the transport; httpx clients are created lazily on first use.

        `httpx` is imported lazily (per call) so that importing `ocai.wire`
        never requires httpx to be installed (it ships behind the `[http]`
        extra).

        Args:
            timeout: The request timeout in seconds applied to the client.
                Defaults to 60.0.
            max_connections: The maximum number of pooled connections.
                Defaults to 100.
            provider: An optional provider name stamped onto raised errors for
                context.
        """
        self._provider = provider
        self._timeout = timeout
        self._max_connections = max_connections
        self._aclient: Any = None  # httpx.AsyncClient, created on first async use
        self._sclient: Any = None  # httpx.Client, created on first sync use

    def _async_client(self) -> Any:
        """Return (creating on first use) the lazy `httpx.AsyncClient`."""
        import httpx  # lazy: the [http] extra is needed only when sending

        if self._aclient is None:
            self._aclient = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                limits=httpx.Limits(max_connections=self._max_connections),
            )
        return self._aclient

    def _sync_client(self) -> Any:
        """Return (creating on first use) the lazy `httpx.Client`."""
        import httpx

        if self._sclient is None:
            self._sclient = httpx.Client(
                timeout=httpx.Timeout(self._timeout),
                limits=httpx.Limits(max_connections=self._max_connections),
            )
        return self._sclient

    async def aclose(self) -> None:
        """Close the async httpx client, if one was created."""
        if self._aclient is not None:
            await self._aclient.aclose()

    def close(self) -> None:
        """Close the sync httpx client, if one was created."""
        if self._sclient is not None:
            self._sclient.close()

    async def __aenter__(self) -> HttpxTransport:
        """Enter the async context manager, returning this transport."""
        return self

    async def __aexit__(self, *exc: object) -> None:
        """Exit the async context manager, closing the async client."""
        await self.aclose()

    def __enter__(self) -> HttpxTransport:
        """Enter the sync context manager, returning this transport."""
        return self

    def __exit__(self, *exc: object) -> None:
        """Exit the sync context manager, closing the sync client."""
        self.close()

    def _error(self, status: int, body: bytes | str, headers: Any) -> OcaiError:
        """Map a non-2xx response onto the coarse taxonomy (layer 1)."""
        text = body.decode("utf-8", "replace") if isinstance(body, bytes) else body
        return error_from_response(
            status,
            _safe_json(text),
            provider=self._provider,
            retry_after=headers.get("retry-after"),
        )

    def _ok(self, resp: Any) -> HttpResponse:
        """Snapshot a successful httpx response into a detached `HttpResponse`."""
        return HttpResponse(status=resp.status_code, headers=dict(resp.headers), body=resp.content)

    async def send(self, request: HttpRequest) -> HttpResponse:
        """Send `request` once (async); return the response or raise the taxonomy.

        Args:
            request: The authenticated wire request.

        Returns:
            The detached 2xx response snapshot.

        Raises:
            TransientError: On connect/read/timeout failures.
            OcaiError: The taxonomy classification of a non-2xx status.
        """
        import httpx

        try:
            resp = await self._async_client().request(
                request.method,
                request.url,
                headers=request.headers,
                content=request.body,
                timeout=min(self._timeout, request.timeout)
                if request.timeout is not None
                else self._timeout,
            )
        except httpx.TransportError as exc:  # connect/read/timeout → transient
            raise TransientError(str(exc), provider=self._provider) from exc
        if resp.is_success:
            return self._ok(resp)
        raise self._error(resp.status_code, resp.text, resp.headers)

    def send_sync(self, request: HttpRequest) -> HttpResponse:
        """Send `request` once (sync); return the response or raise the taxonomy.

        Args:
            request: The authenticated wire request.

        Returns:
            The detached 2xx response snapshot.

        Raises:
            TransientError: On connect/read/timeout failures.
            OcaiError: The taxonomy classification of a non-2xx status.
        """
        import httpx

        try:
            resp = self._sync_client().request(
                request.method,
                request.url,
                headers=request.headers,
                content=request.body,
                timeout=min(self._timeout, request.timeout)
                if request.timeout is not None
                else self._timeout,
            )
        except httpx.TransportError as exc:  # connect/read/timeout → transient
            raise TransientError(str(exc), provider=self._provider) from exc
        if resp.is_success:
            return self._ok(resp)
        raise self._error(resp.status_code, resp.text, resp.headers)

    async def stream(self, request: HttpRequest) -> AsyncIterator[bytes]:
        """Stream the response body as raw byte chunks, async (framing is above).

        No retry: a partially consumed stream can't be safely replayed, which
        is also why the drivers ignore outcome-phase `Retry` decisions for
        streams.

        Args:
            request: The authenticated wire request.

        Yields:
            Raw body chunks as they arrive.

        Raises:
            TransientError: On connect/read/timeout failures — at open or
                mid-stream (a wire that dies mid-body maps to the taxonomy
                like any other wire failure, rule 8).
            OcaiError: The taxonomy classification of a non-2xx status.
        """
        import httpx

        try:
            async with self._async_client().stream(
                request.method,
                request.url,
                headers=request.headers,
                content=request.body,
                timeout=min(self._timeout, request.timeout)
                if request.timeout is not None
                else self._timeout,
            ) as resp:
                if not resp.is_success:
                    raise self._error(resp.status_code, await resp.aread(), resp.headers)
                async for chunk in resp.aiter_bytes():
                    yield chunk
        except httpx.TransportError as exc:  # connect/read/timeout → transient
            raise TransientError(str(exc), provider=self._provider) from exc

    def stream_sync(self, request: HttpRequest) -> Iterator[bytes]:
        """Stream the response body as raw byte chunks, synchronously.

        Args:
            request: The authenticated wire request.

        Yields:
            Raw body chunks as they arrive.

        Raises:
            TransientError: On connect/read/timeout failures — at open or
                mid-stream (a wire that dies mid-body maps to the taxonomy
                like any other wire failure, rule 8).
            OcaiError: The taxonomy classification of a non-2xx status.
        """
        import httpx

        try:
            with self._sync_client().stream(
                request.method,
                request.url,
                headers=request.headers,
                content=request.body,
                timeout=min(self._timeout, request.timeout)
                if request.timeout is not None
                else self._timeout,
            ) as resp:
                if not resp.is_success:
                    raise self._error(resp.status_code, resp.read(), resp.headers)
                yield from resp.iter_bytes()
        except httpx.TransportError as exc:  # connect/read/timeout → transient
            raise TransientError(str(exc), provider=self._provider) from exc


def _safe_json(text: str) -> dict[str, Any] | None:
    """Best-effort parse of an error body; never raises."""
    try:
        parsed = _json.loads(text)
    except (ValueError, TypeError):
        return None
    return parsed if is_json_object(parsed) else None
