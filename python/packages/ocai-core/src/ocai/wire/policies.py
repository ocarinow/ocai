"""Wire-tier policies: Decision-based retry, rate-limit, and exchange capture.

These implement the `WirePolicy` hook (`ocai.runtime.decisions`) — the
wire-tier counterpart of port-tier `CallInterceptor`s. A policy here is
**sans-io on the decision path**: it inspects an `HttpRequest` or an
`Outcome` and returns a `Decision`; the driver performs the sleep, the raise,
or the short-circuit. That is what lets one implementation serve both
`SyncDriver` and `AsyncDriver`, and what makes every policy unit-testable as
a pure function.

Policies here see requests **before** the credential is applied (the driver
applies it at the leaf, per attempt, after all hooks), so nothing in this
module can ever observe a secret.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ocai.core.errors import TransientError
from ocai.runtime.decisions import Decision
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.decisions import Retry

if TYPE_CHECKING:
    from ocai.wire.http import HttpRequest


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry transient failures with exponential backoff, as pure decisions.

    The Decision-model rework of the old transport `RetryMiddleware`: instead
    of looping around a send itself, it judges each `Outcome` and returns
    `Retry(after=…)` — the driver executes the wait and re-attempts (with a
    fresh request and freshly applied credential). It reacts only to
    `TransientError` (the transport raises it for 5xx/429/connection
    failures), honors a server-provided `retry_after` when present, and
    otherwise backs off exponentially from `base_delay`.

    The policy is **stateless**: backoff derives from `Outcome.attempt`, so
    one frozen instance is safely shared across concurrent calls and both
    drivers. Streams are not retried after the first byte — the drivers do
    not run outcome-phase retries for streams, since a partially consumed
    stream cannot be safely replayed.

    Attributes:
        attempts: The maximum number of send attempts (including the first).
            Defaults to 3.
        base_delay: The base backoff delay in seconds, doubled per attempt
            when the server gives no `retry_after`. Defaults to 0.1.
    """

    attempts: int = 3
    base_delay: float = 0.1

    def on_request(self, request: HttpRequest) -> Decision:
        """Admit every request — retry is purely an outcome concern.

        Args:
            request: The outgoing (unauthenticated) wire request.

        Returns:
            `Proceed`, always.
        """
        return Proceed()

    def on_outcome(self, outcome: Outcome) -> Decision:
        """Return `Retry` with the computed delay for a retryable failure.

        Retries when the outcome carries a `TransientError` and attempts
        remain, sleeping the server's `retry_after` when present, else
        `base_delay * 2**attempt`. Anything else — success, a non-transient
        error, or an exhausted budget — proceeds, letting the driver return
        the response or raise the (refined) error.

        Args:
            outcome: The attempt's result — response or refined error.

        Returns:
            `Retry(after=…)` while budget remains for a transient failure,
            else `Proceed`.
        """
        error = outcome.error
        if not isinstance(error, TransientError):
            return Proceed()
        if outcome.attempt >= self.attempts - 1:
            return Proceed()
        # Honor a server-provided Retry-After; else exponential backoff.
        # TODO: add jitter to avoid thundering-herd retries.
        delay = (
            error.retry_after
            if error.retry_after is not None
            else self.base_delay * (2**outcome.attempt)
        )
        return Retry(after=delay)


class RateLimitPolicy:
    """Client-side rate limiting via `Retry`/`Fail` admission decisions [stub].

    Will meter requests against a token bucket and defer admission with
    `Retry(after=…)` (or veto with `Fail` when a deadline makes waiting
    pointless). The bucket itself is an effectful *backend* declaring
    `SyncBackend`/`AsyncBackend` faces — an in-process bucket for a single
    node, a redis/distributed one for a fleet — so the decision stays pure
    while the state lives wherever the deployment needs it.
    """

    def on_request(self, request: HttpRequest) -> Decision:
        """Decide whether to admit, defer, or veto `request` against the budget.

        Args:
            request: The outgoing (unauthenticated) wire request.

        Returns:
            The admission decision.

        Raises:
            NotImplementedError: Skeleton stub.
        """
        # TODO: consult a token-bucket backend (SyncBackend/AsyncBackend faces)
        # and return Proceed / Retry(after) / Fail on exhausted budget.
        raise NotImplementedError("RateLimitPolicy is a skeleton stub")

    def on_outcome(self, outcome: Outcome) -> Decision:
        """Feed provider rate signals back into the budget.

        Args:
            outcome: The attempt's result — response or refined error.

        Returns:
            `Proceed`, always (the limiter never overrides an outcome).

        Raises:
            NotImplementedError: Skeleton stub.
        """
        # TODO: parse provider rate headers (x-ratelimit-*) / RateLimitError
        # retry_after into the bucket so client pacing tracks server truth.
        raise NotImplementedError("RateLimitPolicy is a skeleton stub")


class WireTap:
    """Post-redaction exchange capture feeding archive satellites [stub].

    Records each attempt's `(HttpRequest, HttpResponse | error)` pair — the
    audit-archive contract shape (`ocai.wire.http`) — and hands it to a
    content-addressed archive sink (a future `ocai-archive-*` satellite).
    Because every `WirePolicy` runs **before** `Credential.apply`, the
    captured request is structurally guaranteed to be the unauthenticated,
    post-redaction shape: a tap cannot leak a secret even by accident.

    A tap observes and never steers: `on_request` always proceeds, and
    `on_outcome` will capture-and-proceed once implemented.
    """

    def on_request(self, request: HttpRequest) -> Decision:
        """Admit every request — a tap never vetoes.

        Args:
            request: The outgoing (unauthenticated) wire request.

        Returns:
            `Proceed`, always.
        """
        return Proceed()

    def on_outcome(self, outcome: Outcome) -> Decision:
        """Capture the completed exchange, then proceed.

        Args:
            outcome: The attempt's result — response or refined error.

        Returns:
            `Proceed`, always (after capture).

        Raises:
            NotImplementedError: Skeleton stub.
        """
        # TODO: content-address the exchange (canonical bytes → hash) and hand
        # it to an archive sink protocol; needs the archive satellite contract.
        raise NotImplementedError("WireTap is a skeleton stub")
