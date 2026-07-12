"""The sans-io policy vocabulary: hooks decide, drivers execute (architecture §5).

Wire policies (retry, rate-limit, wiretap — `ocai.wire.policies`) are **pure
decision makers**: they receive plain value objects (`HttpRequest` on the way
out, `Outcome` on the way back) and return a `Decision` — never sleeping,
never sending, never touching a socket themselves. The two drivers
(`ocai.runtime.drivers`) are the only executors: a `Retry(after=2.0)` is
*performed* by `SyncDriver` with `time.sleep` and by `AsyncDriver` with
`asyncio.sleep`, so one policy implementation serves both call paths and a
policy can be unit-tested as a pure function of its inputs.

Because policies run **before** `Credential.apply` (the driver applies the
credential at the leaf, per attempt, after every hook has seen the request),
no policy, cache, or log built on this vocabulary can ever see a secret.

Effectful policies (a redis-backed cache, a distributed rate limiter) keep the
decision pure but delegate their I/O to a *backend* that declares a sync
and/or async face (`SyncBackend` / `AsyncBackend`). `Binding.validate` /
`Workspace.validate` check those faces against the requested driver mode at
composition time, so a sync call over an async-only backend fails with a
`CompositionError` naming the offender — never a mid-request `TypeError`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Protocol
from typing import runtime_checkable

from ocai.core.errors import OcaiError

if TYPE_CHECKING:
    from ocai.wire.http import HttpRequest
    from ocai.wire.http import HttpResponse


@dataclass(frozen=True, slots=True)
class Proceed:
    """Continue the pipeline: the policy has no objection.

    The neutral decision. A driver consults each policy in order and moves to
    the next stage only when every policy returned `Proceed`; the first
    non-`Proceed` decision short-circuits the phase.
    """


@dataclass(frozen=True, slots=True)
class Retry:
    """Re-run the attempt after an optional delay.

    Returned by a policy's `on_outcome` (e.g. `RetryPolicy` on a
    `TransientError`) or `on_request` (e.g. a rate limiter deferring
    admission). The driver executes the wait — `time.sleep` in `SyncDriver`,
    `asyncio.sleep` in `AsyncDriver` — then rebuilds the request and re-runs
    every `on_request` hook, re-applying the credential fresh for the new
    attempt.

    Attributes:
        after: Seconds to wait before the next attempt; `None` means retry
            immediately.
    """

    after: float | None = None


@dataclass(frozen=True, slots=True)
class Fail:
    """Abort the call: the driver raises `error` without sending (or resending).

    How a policy vetoes — a governance hook refusing a destination, a rate
    limiter whose budget is exhausted, a retry policy converting repeated
    transient failures into a terminal one.

    Attributes:
        error: The taxonomy error the driver raises to the caller.
    """

    error: OcaiError


@dataclass(frozen=True, slots=True)
class Return:
    """Short-circuit with a synthesized response: the driver skips the send.

    How a wire-tier cache serves a hit: the policy returns the stored
    `HttpResponse` and the driver treats it exactly as if the transport had
    produced it (envelope unwrap included), so downstream decode cannot tell
    the difference.

    Attributes:
        response: The wire response to return in place of a network send.
    """

    response: HttpResponse


# What every policy hook returns. Pure data: the driver pattern-matches on the
# variant and performs the effect (sleep, raise, short-circuit, or continue).
type Decision = Proceed | Retry | Fail | Return


@dataclass(frozen=True, slots=True)
class Outcome:
    """What one send attempt produced — the input to `WirePolicy.on_outcome`.

    Built by the driver after each attempt, carrying *either* a successful
    `response` *or* a taxonomy `error` (exactly one is set). The `error` is
    already two-layer refined (transport's status-based classification, then
    the dialect's body-aware `map_error`), so a retry policy branching on
    `TransientError` sees the precise error and its `retry_after` hint.
    `attempt` is zero-based, which lets policies stay **stateless**: backoff
    math derives from the outcome, so one policy instance is safely shared
    across concurrent calls and both drivers.

    Attributes:
        request: The request that was sent (post-hooks; auth header applied by
            the driver at the leaf — policies received it *before* that).
        attempt: The zero-based index of this attempt.
        response: The successful wire response, when the attempt succeeded.
        error: The refined taxonomy error, when the attempt failed.
    """

    request: HttpRequest
    attempt: int
    response: HttpResponse | None = None
    error: OcaiError | None = None


@runtime_checkable
class WirePolicy(Protocol):
    """A wire-tier hook: sees requests and outcomes, returns `Decision`s.

    Sans-io by contract: implementations must not sleep, send, or block on the
    decision path — they *describe* the effect and the driver performs it.
    This is what makes one policy implementation serve both `SyncDriver` and
    `AsyncDriver`, and what makes policies debuggable (a decision log is a
    list of plain value objects).

    Wire policies operate on `HttpRequest`/`Outcome` — bytes-adjacent, remote
    concerns (retry, rate-limit, exchange capture). Concerns that are
    meaningful for *local* adapters too (fallback, semantic cache, cost,
    tracing) belong at the port tier instead: `ocai.runtime.interceptors`.

    Effectful implementations (redis, distributed limiters) hold a backend
    declaring `SyncBackend` and/or `AsyncBackend`; the workspace validates the
    faces against the requested mode at composition time.
    """

    def on_request(self, request: HttpRequest) -> Decision:
        """Judge an outgoing request before it is sent.

        Called once per attempt, before `Credential.apply` — the request never
        carries a secret here. Return `Proceed` to admit, `Retry` to defer,
        `Fail` to veto, or `Return` to serve a synthesized response.

        Args:
            request: The built (unauthenticated) wire request.

        Returns:
            The policy's decision for this attempt.
        """
        ...

    def on_outcome(self, outcome: Outcome) -> Decision:
        """Judge the result of a send attempt.

        Return `Proceed` to accept the outcome as final (the driver then
        returns the response or raises the error), `Retry` to re-attempt,
        `Fail` to replace the error, or `Return` to substitute a response.

        Args:
            outcome: The attempt's result — response or refined error.

        Returns:
            The policy's decision for what happens next.
        """
        ...


@runtime_checkable
class SyncBackend(Protocol):
    """The blocking face an effectful policy backend declares.

    A structural marker checked with `isinstance` by `Binding.validate` /
    `Workspace.validate`: a component offering this face can run under
    `SyncDriver`. The anchor method is `close` — mirroring the transport
    convention (`SyncTransport.close`), so transports and policy backends are
    validated by one rule. A *pure* policy (e.g. `RetryPolicy`) declares
    neither face and passes validation in both modes.
    """

    def close(self) -> None:
        """Release the backend's blocking-I/O resources."""
        ...


@runtime_checkable
class AsyncBackend(Protocol):
    """The async face an effectful policy backend declares.

    The async twin of `SyncBackend`, anchored on `aclose` (mirroring
    `Transport.aclose`). A component declaring *only* this face fails
    `validate(mode="sync")` with a `CompositionError` naming it — the
    mid-request `TypeError` class of bug dies at composition time.
    """

    async def aclose(self) -> None:
        """Release the backend's async-I/O resources."""
        ...
