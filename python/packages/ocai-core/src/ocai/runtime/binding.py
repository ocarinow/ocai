"""`Binding` — the reusable remote nucleus.

A `Binding` freezes the three remote axes — *where* (`Host`), *who*
(`Credential`), *how* (`Transport`) — plus static caller headers into one
reusable value. One binding can back several capability facades at once (a
chat model and an embedding model sharing the same Vertex project, credential,
and connection pool). The credential is **not** applied here: the driver
applies it at the leaf, per attempt, after every hook (`ocai.runtime.drivers`).

Bindings are normally composed *internally* by the `ocai.chat.model()` front
door (§3.4); power users build them by hand. There is deliberately no
`Workspace`/container object above them: per-tenant isolation is several
models built from different credentials/catalogs — plain Python, not a
framework concept.

`Binding.validate` checks the composed stack against the requested driver
mode at **composition time**: requesting sync execution over a component that
only has an async face raises `CompositionError` naming the offender — the
mid-request `TypeError` class of bug dies here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Literal

from ocai.core.credentials import Credential
from ocai.core.errors import OcaiError

if TYPE_CHECKING:
    from ocai.wire.hosting import Host
    from ocai.wire.transport import SyncTransport
    from ocai.wire.transport import Transport


# The execution mode a composition is validated against: "sync" for the bare
# port methods run by SyncDriver, "async" for the a-prefixed ones.
type Mode = Literal["sync", "async"]


class CompositionError(OcaiError):
    """A composed stack cannot serve the requested execution mode.

    Raised by `Binding.validate` (and the §3.4 front doors) at composition
    time — never mid-request — and its message names the offending component
    and the face it lacks, so the fix (bind a dual-face transport, wrap the
    port via `ocai.runtime.dual`, swap the backend) is immediate.
    """


@dataclass(frozen=True, slots=True)
class Binding:
    """The reusable, capability-neutral remote nucleus.

    Passed to a driver (`SyncDriver`/`AsyncDriver`), which reads the axes in
    pipeline order: `host` shapes envelope/endpoint/headers, `extra_headers`
    are merged over the host's, `credentials` is applied at the leaf per
    attempt, and `transport` performs the one physical send. Frozen so a
    binding can be shared across facades and threads without defensive
    copying.

    Attributes:
        host: The hosting target (`Direct`/`Custom`/`Vertex`, …) deciding
            where the request goes and how its body/headers are shaped.
        credentials: The credential the driver applies per attempt, after all
            hooks — never visible to policies, caches, or logs.
        transport: The wire port the send goes through; a dual-face transport
            (e.g. `HttpxTransport`) serves both drivers.
        extra_headers: Static caller headers merged *over* the host's headers,
            so they win on conflict. Defaults to empty.
    """

    host: Host
    credentials: Credential
    transport: Transport | SyncTransport
    extra_headers: Mapping[str, str] = field(default_factory=dict[str, str])

    def validate(self, mode: Mode = "sync") -> None:
        """Check this binding can serve `mode`, at composition time.

        Verifies the transport structurally offers the face `mode` needs:
        `send_sync`/`stream_sync`/`close` (`SyncTransport`) for sync,
        `send`/`stream`/`aclose` (`Transport`) for async.

        Args:
            mode: The execution mode the binding will be driven in.

        Raises:
            CompositionError: If the transport lacks the required face; the
                message names the transport type and the missing face.
        """
        # Imported here, not at module top: runtime stays import-light and the
        # wire package already depends on runtime (the arrow points up).
        from ocai.wire.transport import SyncTransport
        from ocai.wire.transport import Transport

        transport = self.transport
        if mode == "sync" and not isinstance(transport, SyncTransport):
            raise CompositionError(
                f"{type(transport).__name__} has no sync face "
                "(send_sync/stream_sync/close) but sync execution was requested. "
                "Bind a sync-capable transport (HttpxTransport implements both "
                "faces) or use the async API (achat/astream/…)."
            )
        if mode == "async" and not isinstance(transport, Transport):
            raise CompositionError(
                f"{type(transport).__name__} has no async face (send/stream/aclose) "
                "but async execution was requested. Bind an async-capable "
                "transport (HttpxTransport implements both faces) or use the "
                "sync API (chat/stream/…)."
            )
