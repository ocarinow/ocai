"""`Binding` (the remote nucleus) and `Workspace` (the tenancy unit).

A `Binding` freezes the three remote axes — *where* (`Host`), *who*
(`Credential`), *how* (`Transport`) — plus static caller headers into one
reusable value. One binding can back several capability facades at once (a
chat model and an embedding model sharing the same Vertex project, credential,
and connection pool). The credential is **not** applied here: the driver
applies it at the leaf, per attempt, after every hook (`ocai.runtime.drivers`).

A `Workspace` is the application-level composition root: the governed
conversion `Catalog`, the named bindings, the port-tier interceptor chain, the
observers, and default call context. Its factories (`chat`, …) assemble the
wire-backed facades so user code composes once and calls many times.

Both carry a `validate` that checks the composed stack against the requested
driver mode at **composition time**: requesting sync execution over a
component that only has an async face raises `CompositionError` naming the
offender — the mid-request `TypeError` class of bug dies here.
"""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Literal

from ocai.core.credentials import Credential
from ocai.core.errors import OcaiError
from ocai.core.result import CallContext
from ocai.runtime.decisions import AsyncBackend
from ocai.runtime.decisions import SyncBackend
from ocai.runtime.interceptors import CallInterceptor
from ocai.runtime.observe import Observer

if TYPE_CHECKING:
    from ocai.chat.protocol import ChatModel
    from ocai.convert.catalog import Catalog
    from ocai.wire.hosting import Host
    from ocai.wire.transport import SyncTransport
    from ocai.wire.transport import Transport


# The execution mode a composition is validated against: "sync" for the bare
# port methods run by SyncDriver, "async" for the a-prefixed ones.
type Mode = Literal["sync", "async"]


class CompositionError(OcaiError):
    """A composed stack cannot serve the requested execution mode.

    Raised by `Binding.validate` / `Workspace.validate` at composition time —
    never mid-request — and its message names the offending component and the
    face it lacks, so the fix (bind a dual-face transport, wrap the port via
    `ocai.runtime.dual`, swap the backend) is immediate.
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
    extra_headers: Mapping[str, str] = field(default_factory=dict)

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


@dataclass(frozen=True, slots=True)
class Workspace:
    """The tenancy unit: catalog + bindings + interceptors + observers.

    The composition root user code builds once per application (or per
    tenant): every model minted by its factories shares the same governed
    `Catalog` (so every `Route` carries the same lockfile hash), runs inside
    the same interceptor chain, reports to the same observers, and inherits
    `defaults` as the base `CallContext` merged under each call's own.

    Attributes:
        catalog: The immutable conversion catalog resolution and conversion
            run against; `None` until one is composed in.
        bindings: Named remote nuclei, keyed by a caller-chosen label
            (typically the provider name) that factories look up.
        interceptors: The port-tier chain applied around every minted model,
            outermost first.
        observers: Passive event sinks notified of every call and wire
            exchange.
        defaults: Workspace-wide governance defaults (tenant, tags, …) merged
            under each call's own `CallContext`.
    """

    catalog: Catalog | None = None
    bindings: Mapping[str, Binding] = field(default_factory=dict)
    interceptors: Sequence[CallInterceptor] = ()
    observers: Sequence[Observer] = ()
    defaults: CallContext | None = None

    def chat(
        self,
        provider: str,
        model: str,
        *,
        interface: str | None = None,
        tag: str | None = None,
    ) -> ChatModel:
        """Mint a chat port bound to `provider`'s binding through this workspace.

        The factory that assembles the full stack of architecture §8: resolve
        the target `NodeId` via `Catalog.resolve(chat, provider, pins)`, build
        the `WireChatModel(codec, binding, catalog)` facade over the binding
        named `provider`, and wrap it in this workspace's interceptor chain —
        returning a plain `ChatModel` the caller cannot distinguish from a
        local adapter.

        Args:
            provider: The binding label and provider to resolve against.
            model: The provider model id the facade will target.
            interface: Optional interface pin (e.g. `"responses"`); default is
                catalog resolution (latest `STABLE`).
            tag: Optional revision-tag pin for the chosen interface.

        Returns:
            The composed, interceptor-wrapped chat port.

        Raises:
            NotImplementedError: Skeleton stub.
        """
        # TODO: needs Catalog.resolve + the WireChatModel facade (ocai.chat.model)
        # to land; then: resolve -> facade -> compose(self.interceptors, facade).
        raise NotImplementedError("Workspace.chat is a skeleton stub")

    def validate(self, mode: Mode = "sync") -> None:
        """Check every composed component can serve `mode`, naming offenders.

        Validates each binding's transport, then checks every interceptor and
        observer's declared backend faces: a component declaring *only* the
        `AsyncBackend` face fails `mode="sync"` (and vice versa); a pure
        component declaring neither face passes in both modes.

        Args:
            mode: The execution mode the workspace will be driven in.

        Raises:
            CompositionError: Naming the first offending binding or component
                and the face it lacks.
        """
        for name, binding in self.bindings.items():
            try:
                binding.validate(mode)
            except CompositionError as err:
                raise CompositionError(f"binding {name!r}: {err}") from err
        for member in (*self.interceptors, *self.observers):
            self._check_faces(member, mode)

    @staticmethod
    def _check_faces(member: object, mode: Mode) -> None:
        """Raise if `member` declares only the face opposite to `mode`."""
        is_sync = isinstance(member, SyncBackend)
        is_async = isinstance(member, AsyncBackend)
        if mode == "sync" and is_async and not is_sync:
            raise CompositionError(
                f"{type(member).__name__} declares only an async backend face "
                "(aclose) but sync execution was requested. Provide a sync face "
                "or run this workspace in async mode."
            )
        if mode == "async" and is_sync and not is_async:
            raise CompositionError(
                f"{type(member).__name__} declares only a sync backend face "
                "(close) but async execution was requested. Provide an async "
                "face or run this workspace in sync mode."
            )
