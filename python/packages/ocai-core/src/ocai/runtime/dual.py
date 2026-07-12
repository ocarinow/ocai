"""Visible sync/async bridging: `from_sync` / `from_async` port adapters.

The repo-wide convention gives every port a bare-name sync face and an
`a`-prefixed async face (`chat`/`achat`), and a well-behaved implementation
ships both. But some can't: a local adapter over a blocking C library is
sync-only; a port wrapping an async-native service is async-only. ocai never
bridges the two **silently** — silent bridging is how event loops get blocked
and threads get leaked without anyone deciding it. Instead, bridging is a
*visible composition decision*: the caller writes `from_sync(port)` or
`from_async(port)` at composition time, and `Workspace.validate` /
`CompositionError` point here when a face is missing.

- `from_sync(port)` synthesizes the async faces by **thread offload**: each
  `a`-prefixed call runs the underlying blocking method via a worker thread
  (`asyncio.to_thread`), and sync iterators are pumped into async ones
  through a bounded queue.
- `from_async(port)` synthesizes the sync faces through a **portal**: a
  dedicated background thread running a private event loop that the blocking
  caller submits coroutines to (never `asyncio.run` per call — streams need a
  loop that outlives each `__next__`).
"""

from __future__ import annotations

from typing import Any


def from_sync(port: Any) -> Any:
    """Wrap a sync-only port, adding thread-offloaded async faces.

    The returned object exposes the port's own sync faces unchanged and, for
    every bare-name method, an `a`-prefixed twin that offloads the blocking
    call to a worker thread — keeping the caller's event loop responsive at
    the visible cost of one thread hop per call.

    Args:
        port: Any capability port implementation with sync faces
            (e.g. `chat`/`stream`).

    Returns:
        A wrapper satisfying the same port protocol with both faces.

    Raises:
        NotImplementedError: Skeleton stub.
    """
    # TODO: generic proxy — pass sync attrs through; synthesize a-prefixed
    # methods via asyncio.to_thread; bridge sync iterators to async iterators
    # through a bounded queue fed by a worker thread.
    raise NotImplementedError("from_sync is a skeleton stub")


def from_async(port: Any) -> Any:
    """Wrap an async-only port, adding portal-backed sync faces.

    The returned object exposes the port's own async faces unchanged and, for
    every `a`-prefixed method, a bare-name twin that submits the coroutine to
    a dedicated portal thread's event loop and blocks on the result — the
    visible cost is one long-lived background thread per portal, shared by
    all calls and kept alive across streaming iterations.

    Args:
        port: Any capability port implementation with async faces
            (e.g. `achat`/`astream`).

    Returns:
        A wrapper satisfying the same port protocol with both faces.

    Raises:
        NotImplementedError: Skeleton stub.
    """
    # TODO: portal — lazily start a daemon thread running its own event loop;
    # submit coroutines via asyncio.run_coroutine_threadsafe; drive async
    # iterators one __anext__ per blocking __next__; close the loop on close().
    raise NotImplementedError("from_async is a skeleton stub")
