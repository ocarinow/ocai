"""Visible sync/async bridging: `from_sync` / `from_async` port adapters.

The repo-wide convention gives every port a bare-name sync face and an
`a`-prefixed async face (`chat`/`achat`), and a well-behaved implementation
ships both. But some can't: a local adapter over a blocking C library is
sync-only; a port wrapping an async-native service is async-only. ocai never
bridges the two **silently** — silent bridging is how event loops get blocked
and threads get leaked without anyone deciding it. Instead, bridging is a
*visible composition decision*: the caller writes `from_sync(port)` or
`from_async(port)` at composition time, and `Binding.validate` /
`CompositionError` point here when a face is missing.

- `from_sync(port)` synthesizes the async faces by **thread offload**: each
  `a`-prefixed call runs the underlying blocking method via a worker thread
  (`asyncio.to_thread`), and blocking iterators the port returns (a
  `ChatStream`) are bridged into async ones — one thread hop per item, never
  a blocked event loop.
- `from_async(port)` synthesizes the sync faces through a **portal**: a
  dedicated background thread running a private event loop that the blocking
  caller submits coroutines to (never `asyncio.run` per call — streams need a
  loop that outlives each `__next__`).

Both wrappers are generic attribute proxies over the ChatModel-shaped naming
convention: the port's own faces always pass through unchanged; only a
*missing* face is synthesized from its present twin. Because the synthesis is
dynamic (`__getattr__`), `isinstance` against a `runtime_checkable` protocol
reports False for the wrappers (CPython's protocol instance check uses
`inspect.getattr_static` and never sees dynamic attributes) — the wrappers
conform *behaviorally*: every port face is reachable and callable.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any
from typing import Final

# Sentinel distinguishing "iterator exhausted" from a legitimate item when a
# blocking `next` is offloaded to a worker thread.
_EXHAUSTED: Final = object()


class _AsyncIteratorBridge:
    """An async view over a blocking iterator, one thread hop per item.

    Wraps whatever iterator object a sync port returned (e.g. a
    `ChatStream`), driving its `__next__` via `asyncio.to_thread` so the
    caller's event loop stays responsive. Non-iterating attributes (like a
    stream's `.end`) pass through to the wrapped object.
    """

    def __init__(self, iterator: Any) -> None:
        """Wrap `iterator` (any object with a blocking `__next__`).

        Args:
            iterator: The blocking iterator to bridge.
        """
        self._iterator = iterator

    def __aiter__(self) -> _AsyncIteratorBridge:
        """Return the bridge itself as its async iterator."""
        return self

    async def __anext__(self) -> Any:
        """Offload one blocking `next` to a worker thread.

        Returns:
            The underlying iterator's next item.

        Raises:
            StopAsyncIteration: When the underlying iterator is exhausted.
        """
        item = await asyncio.to_thread(next, self._iterator, _EXHAUSTED)
        if item is _EXHAUSTED:
            raise StopAsyncIteration
        return item

    def __getattr__(self, name: str) -> Any:
        """Pass non-iterating attributes (e.g. `.end`) to the wrapped object."""
        return getattr(self._iterator, name)


class _SyncIteratorBridge:
    """A blocking view over an async iterator, driven through a portal.

    Wraps whatever async iterator an async port returned (e.g. an
    `AsyncChatStream`), submitting one `__anext__` per blocking `__next__`
    to the portal's long-lived event loop. Non-iterating attributes (like a
    stream's `.end`) pass through to the wrapped object.
    """

    def __init__(self, iterator: Any, portal: _Portal) -> None:
        """Wrap `iterator` (any object with an async `__anext__`).

        Args:
            iterator: The async iterator to bridge.
            portal: The portal whose loop drives each step.
        """
        self._iterator = iterator
        self._portal = portal

    def __iter__(self) -> _SyncIteratorBridge:
        """Return the bridge itself as its iterator."""
        return self

    def __next__(self) -> Any:
        """Block on one `__anext__` submitted to the portal loop.

        Returns:
            The underlying iterator's next item.

        Raises:
            StopIteration: When the underlying async iterator is exhausted.
        """
        try:
            return self._portal.call(self._iterator.__anext__())
        except StopAsyncIteration:
            raise StopIteration from None

    def __getattr__(self, name: str) -> Any:
        """Pass non-iterating attributes (e.g. `.end`) to the wrapped object."""
        return getattr(self._iterator, name)


class _Portal:
    """A dedicated daemon thread running a private event loop.

    The blocking side of `from_async`: coroutines are submitted with
    `asyncio.run_coroutine_threadsafe` and their results awaited by the
    calling thread. One portal (one thread, one loop) is shared by all calls
    on a wrapper and outlives each streaming `__next__` — the reason this is
    a portal and not `asyncio.run` per call.
    """

    def __init__(self) -> None:
        """Create the portal; the thread and loop start lazily on first use."""
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        """Start the daemon loop thread once and return the running loop."""
        with self._lock:
            if self._loop is None:
                loop = asyncio.new_event_loop()
                thread = threading.Thread(
                    target=loop.run_forever, name="ocai-dual-portal", daemon=True
                )
                thread.start()
                self._loop = loop
        return self._loop

    def call(self, coro: Any) -> Any:
        """Run `coro` on the portal loop and block for its result.

        Args:
            coro: The coroutine to execute.

        Returns:
            The coroutine's result.

        Raises:
            BaseException: Whatever the coroutine raised, re-raised in the
                calling thread.
        """
        return asyncio.run_coroutine_threadsafe(coro, self._ensure_loop()).result()


def _bridge_sync_result(result: Any) -> Any:
    """Wrap a blocking iterator result in an async bridge; pass others through."""
    if hasattr(result, "__next__") and not hasattr(result, "__anext__"):
        return _AsyncIteratorBridge(result)
    return result


def _bridge_async_result(result: Any, portal: _Portal) -> Any:
    """Wrap an async iterator result in a blocking bridge; pass others through."""
    if hasattr(result, "__anext__") and not hasattr(result, "__next__"):
        return _SyncIteratorBridge(result, portal)
    return result


class _FromSync:
    """The `from_sync` proxy: sync faces pass through, async faces offload."""

    def __init__(self, port: Any) -> None:
        """Wrap `port` (any object with bare-name sync faces).

        Args:
            port: The sync-only port implementation.
        """
        self._port = port

    def __getattr__(self, name: str) -> Any:
        """Delegate to the port; synthesize a missing `a`-prefixed twin.

        Args:
            name: The attribute being looked up.

        Returns:
            The port's own attribute when present; otherwise a synthesized
            async method offloading the bare-name sync face.

        Raises:
            AttributeError: If the port has neither the attribute nor a
                bare-name sync face to synthesize it from.
        """
        port = self._port
        try:
            return getattr(port, name)
        except AttributeError:
            pass
        sync_face = None
        if name.startswith("a") and len(name) > 1:
            sync_face = getattr(port, name[1:], None)
        if not callable(sync_face):
            raise AttributeError(
                f"{type(port).__name__} has no attribute {name!r} and no "
                "bare-name sync face to offload it from"
            )

        async def offloaded(*args: Any, **kwargs: Any) -> Any:
            result = await asyncio.to_thread(sync_face, *args, **kwargs)
            return _bridge_sync_result(result)

        offloaded.__name__ = name
        return offloaded


class _FromAsync:
    """The `from_async` proxy: async faces pass through, sync faces portal."""

    def __init__(self, port: Any) -> None:
        """Wrap `port` (any object with `a`-prefixed async faces).

        Args:
            port: The async-only port implementation.
        """
        self._port = port
        self._portal = _Portal()

    def __getattr__(self, name: str) -> Any:
        """Delegate to the port; synthesize a missing bare-name twin.

        Args:
            name: The attribute being looked up.

        Returns:
            The port's own attribute when present; otherwise a synthesized
            blocking method submitting the `a`-prefixed face to the portal.

        Raises:
            AttributeError: If the port has neither the attribute nor an
                `a`-prefixed async face to synthesize it from.
        """
        port = self._port
        try:
            return getattr(port, name)
        except AttributeError:
            pass
        async_face = getattr(port, f"a{name}", None)
        if not callable(async_face):
            raise AttributeError(
                f"{type(port).__name__} has no attribute {name!r} and no async face 'a{name}'"
            )
        portal = self._portal

        def blocking(*args: Any, **kwargs: Any) -> Any:
            result = portal.call(async_face(*args, **kwargs))
            return _bridge_async_result(result, portal)

        blocking.__name__ = name
        return blocking


def from_sync(port: Any) -> Any:
    """Wrap a sync-only port, adding thread-offloaded async faces.

    The returned object exposes the port's own attributes unchanged and, for
    every missing `a`-prefixed method, synthesizes an async twin that
    offloads the bare-name blocking call to a worker thread
    (`asyncio.to_thread`) — keeping the caller's event loop responsive at
    the visible cost of one thread hop per call. A blocking iterator the
    offloaded call returns (a `ChatStream`) is bridged into an async
    iterator, one thread hop per item, with its other attributes (`.end`)
    passing through.

    Args:
        port: Any capability port implementation with sync faces
            (e.g. `chat`/`stream`).

    Returns:
        A wrapper satisfying the same port protocol with both faces.
    """
    return _FromSync(port)


def from_async(port: Any) -> Any:
    """Wrap an async-only port, adding portal-backed sync faces.

    The returned object exposes the port's own attributes unchanged and, for
    every missing bare-name method, synthesizes a blocking twin that submits
    the `a`-prefixed coroutine to a dedicated portal thread's event loop and
    blocks on the result — the visible cost is one long-lived daemon thread
    per wrapper, shared by all calls and kept alive across streaming
    iterations. An async iterator the call returns (an `AsyncChatStream`) is
    bridged into a blocking iterator, one portal round-trip per item, with
    its other attributes (`.end`) passing through.

    Args:
        port: Any capability port implementation with async faces
            (e.g. `achat`/`astream`).

    Returns:
        A wrapper satisfying the same port protocol with both faces.
    """
    return _FromAsync(port)
