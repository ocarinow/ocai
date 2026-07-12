"""`SyncDriver` / `AsyncDriver` — the two thin executors of the one pipeline.

There is exactly one request pipeline (architecture §8) and these two classes
are its only executors; everything that is not the physical I/O call is
synchronous, pure, and shared between them (the module-level helpers below):

1. **encode** — already done by the facade (`ocai.chat.model.WireChatModel`)
   via the conversion graph; the driver receives an encoded wire payload.
2. **policy hooks** — every `WirePolicy.on_request` judges the (still
   unauthenticated) request; the first non-`Proceed` decision wins and the
   driver executes it (sleep / raise / short-circuit).
3. **host envelope + endpoint + headers** — the `Binding.host` shapes the
   body (`EnvelopeTransform.wrap`), computes the URL, and contributes
   headers; the binding's `extra_headers` are merged over them.
4. **credential.apply at the leaf, PER ATTEMPT, after every hook** — the
   secret lands in the request headers only after all policies have seen it
   and is re-applied freshly on each retry, so no hook, cache, or log can
   ever see a secret and rotating credentials resolve at send time.
5. **send** — the one physical call: `Transport.send`/`SyncTransport.
   send_sync` (or the streaming twins). Errors are refined two-layer: the
   transport's coarse status-based taxonomy error, then the dialect's
   body-aware `map_error` (passed in by the facade as `refine_error`).
6. **pump** — streaming bytes feed the sans-io `SSEParser`; parsed frames
   flow through the facade-built `StreamPipeline` (conversion joins the
   graph, it does not bypass it). The seam (settled in WU-09): the driver
   yields the converted events and flushes the pipeline exactly once at
   end-of-stream (yielding the tail); the flush accounting then surfaces on
   `StreamPipeline.reports`, which the facade folds into the terminal
   `StreamEnd.report`.
7. **outcome hooks** — every `WirePolicy.on_outcome` judges the attempt's
   `Outcome`; `Retry` decisions loop back to step 2 with a fresh request.
8. **decode** — back in the facade, via the graph, assembling `CallResult`.

The drivers deal only in wire-plane values (`EndpointSpec`, payload dicts,
`SSEvent`); they never see canonical IR, codecs, or the catalog — that
separation is what lets `ocai.wire` stay behind an extra and lets local
adapters skip this module entirely.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from collections.abc import Callable
from collections.abc import Iterator
from collections.abc import Sequence
from typing import TYPE_CHECKING
from typing import Any

from ocai.core.errors import OcaiError
from ocai.runtime.binding import Binding
from ocai.runtime.binding import CompositionError
from ocai.runtime.decisions import Decision
from ocai.runtime.decisions import Fail
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.decisions import Retry
from ocai.runtime.decisions import Return
from ocai.runtime.decisions import WirePolicy

if TYPE_CHECKING:
    from ocai.convert.graph import StreamPipeline
    from ocai.wire.hosting import EndpointSpec
    from ocai.wire.hosting import EnvelopeTransform
    from ocai.wire.http import HttpRequest
    from ocai.wire.http import HttpResponse
    from ocai.wire.transport import SyncTransport
    from ocai.wire.transport import Transport

# The dialect's body-aware error refiner (layer 2 of the two-layer mapping):
# the facade closes it over the codec's `map_error`, keeping drivers
# codec-blind. Returning None keeps the transport's coarse classification.
type ErrorRefiner = Callable[[OcaiError], OcaiError | None]

# Defensive ceiling on policy-driven retries: a buggy policy that always
# returns Retry must not spin forever. Policies own *termination* below this.
_ATTEMPT_CAP = 32


def _build_request(
    binding: Binding, spec: EndpointSpec, payload: dict[str, Any]
) -> tuple[EnvelopeTransform, HttpRequest]:
    """Build the wire request for one attempt — steps 3 of the pipeline.

    Ported from the reference `Engine._build`: envelope wrap, endpoint, host
    headers merged under the binding's `extra_headers`. Deliberately does
    **not** apply the credential — that happens in the driver's attempt loop,
    after the policy hooks (step 4). A fresh request is built per attempt so
    retried attempts never accumulate stale headers.

    Args:
        binding: The remote nucleus supplying host and extra headers.
        spec: The endpoint spec (dialect node, traits, operation, resource,
            native path) the facade assembled from the codec.
        payload: The already-encoded dialect request body.

    Returns:
        The host's envelope (kept to `unwrap` the response) and the built,
        unauthenticated request.
    """
    # Deferred import: wire depends on runtime; runtime touches wire's value
    # classes only inside the pipeline, never at module import time.
    from ocai.wire.http import HttpRequest

    host = binding.host
    envelope = host.envelope(spec)
    body = envelope.wrap(payload)
    # Host headers first, then caller overrides from the binding.
    headers = {**host.headers(spec), **binding.extra_headers}
    request = HttpRequest.from_json(
        spec.op.method,
        host.endpoint(spec),
        body,
        headers=headers,
        stream=spec.op.streaming,
    )
    return envelope, request


def _refine(refine_error: ErrorRefiner | None, err: OcaiError) -> OcaiError:
    """Apply the dialect's body-aware refinement (layer 2) to a coarse error.

    Ported from the reference `Engine._reraise_refined`, returning instead of
    raising so the refined error can ride an `Outcome` through the policy
    hooks first. When a refinement happens, the coarse error is chained as
    `__cause__` — equivalent to `raise refined from err`.

    Args:
        refine_error: The facade-provided refiner, or `None` for no layer 2.
        err: The coarse, status-based error the transport raised.

    Returns:
        The refined error, or `err` unchanged when no refinement applies.
    """
    if refine_error is None:
        return err
    refined = refine_error(err)
    if refined is None or refined is err:
        return err
    refined.__cause__ = err
    return refined


def _request_decision(policies: Sequence[WirePolicy], request: HttpRequest) -> Decision:
    """Run the on-request phase: the first non-`Proceed` decision wins."""
    for policy in policies:
        decision = policy.on_request(request)
        if not isinstance(decision, Proceed):
            return decision
    return Proceed()


def _outcome_decision(policies: Sequence[WirePolicy], outcome: Outcome) -> Decision:
    """Run the on-outcome phase: the first non-`Proceed` decision wins."""
    for policy in policies:
        decision = policy.on_outcome(outcome)
        if not isinstance(decision, Proceed):
            return decision
    return Proceed()


def _guard_attempts(attempt: int) -> None:
    """Stop a runaway retry loop at the defensive ceiling."""
    if attempt >= _ATTEMPT_CAP:
        raise OcaiError(
            f"wire policies requested more than {_ATTEMPT_CAP} attempts; "
            "refusing to spin — check the retry/rate-limit policy composition."
        )


class SyncDriver:
    """The blocking executor of the one pipeline.

    Owns the sync effects the sans-io policies describe: `time.sleep` for
    `Retry` decisions and `SyncTransport.send_sync`/`stream_sync` for the
    physical call. Everything else — request building, decision phases, error
    refinement — is the shared pure logic above, identical to `AsyncDriver`'s.

    Constructed by the wire-backed facade from a `Binding` and the wire
    policies; `Binding.validate(mode="sync")` should have admitted the stack
    at composition time, so the transport-face check here is a backstop.
    """

    def __init__(self, binding: Binding, *, policies: Sequence[WirePolicy] = ()) -> None:
        """Bind the driver to its nucleus and hook chain.

        Args:
            binding: The host + credential + transport composition to execute
                against.
            policies: The wire-tier hooks, consulted in order on every attempt.
        """
        self._binding = binding
        self._policies = tuple(policies)

    def _sync_transport(self) -> SyncTransport:
        """Return the binding's transport, asserting its sync face (backstop)."""
        from ocai.wire.transport import SyncTransport

        transport = self._binding.transport
        if not isinstance(transport, SyncTransport):
            raise CompositionError(
                f"{type(transport).__name__} has no sync face; SyncDriver cannot "
                "send. Bind a sync-capable transport (HttpxTransport implements "
                "both faces) or use AsyncDriver."
            )
        return transport

    def execute(
        self,
        *,
        spec: EndpointSpec,
        payload: dict[str, Any],
        refine_error: ErrorRefiner | None = None,
    ) -> dict[str, Any]:
        """Run one non-streaming operation through the full pipeline (blocking).

        Loops attempts: build request → on-request hooks → credential at the
        leaf → send → refine errors → on-outcome hooks; a `Retry` decision
        sleeps and loops, `Return` short-circuits with the policy's response,
        `Fail` raises. When every policy proceeds, the attempt's own result
        stands: return the unwrapped body, or raise the refined error.

        Args:
            spec: The endpoint spec the facade assembled from the codec.
            payload: The already-encoded dialect request body.
            refine_error: The dialect's layer-2 error refiner, if any.

        Returns:
            The raw response dict after the host envelope's `unwrap` — decode
            through the graph is the facade's job.

        Raises:
            OcaiError: The refined taxonomy error when the final attempt
                fails, a policy `Fail`s, or the attempt ceiling is hit.
        """
        transport = self._sync_transport()
        attempt = 0
        while True:
            _guard_attempts(attempt)
            envelope, request = _build_request(self._binding, spec, payload)
            decision = _request_decision(self._policies, request)
            if isinstance(decision, Fail):
                raise decision.error
            if isinstance(decision, Return):
                return envelope.unwrap(decision.response.json())
            if isinstance(decision, Retry):
                time.sleep(decision.after or 0.0)
                attempt += 1
                continue
            # Step 4: the leaf. After every hook, fresh on every attempt.
            self._binding.credentials.apply(request)
            response: HttpResponse | None = None
            try:
                response = transport.send_sync(request)
                outcome = Outcome(request=request, attempt=attempt, response=response)
            except OcaiError as err:
                outcome = Outcome(
                    request=request, attempt=attempt, error=_refine(refine_error, err)
                )
            decision = _outcome_decision(self._policies, outcome)
            if isinstance(decision, Retry):
                time.sleep(decision.after or 0.0)
                attempt += 1
                continue
            if isinstance(decision, Fail):
                raise decision.error
            if isinstance(decision, Return):
                return envelope.unwrap(decision.response.json())
            if outcome.error is not None:
                raise outcome.error
            assert outcome.response is not None
            return envelope.unwrap(outcome.response.json())

    def stream(
        self,
        *,
        spec: EndpointSpec,
        payload: dict[str, Any],
        refine_error: ErrorRefiner | None = None,
        pipeline: StreamPipeline | None = None,
    ) -> Iterator[Any]:
        """Run one streaming operation, yielding stream events (blocking).

        Admission runs the same on-request phase as `execute` (a rate limiter
        may defer a stream with `Retry`; admission retries happen before any
        byte flows, so the pipeline is never fed on a discarded attempt), the
        credential is applied at the leaf, then bytes are pumped through the
        sans-io `SSEParser`. When a `pipeline` is bound, each parsed frame is
        fed through it and the converted events are yielded in its place; at
        end-of-stream the driver flushes the pipeline exactly once and yields
        the tail. The flush accounting then surfaces on `pipeline.reports` —
        the facade's half of the seam is to read it after iteration and stamp
        the terminal `StreamEnd.report`. There is **no outcome-phase retry**:
        a partially consumed stream cannot be safely replayed, so wire errors
        are refined and raised directly — after flushing the pipeline for
        accounting (the tail cannot be delivered on a raising path; the
        accumulator seals aborted parts as incomplete).

        Args:
            spec: The endpoint spec (its operation's `streaming` flag set).
            payload: The already-encoded dialect request body.
            refine_error: The dialect's layer-2 error refiner, if any.
            pipeline: The composite transducer the facade built for THIS
                traversal via `Catalog.stream_converter` (fresh per stream,
                never reused), or None to yield raw frames.

        Yields:
            One raw `SSEvent` per server-sent event when `pipeline` is None;
            the pipeline's converted events (canonical `ChatChunk`s when the
            planned path ends at the canonical chunk node) otherwise.

        Raises:
            OcaiError: The refined taxonomy error on wire failure, or a
                policy `Fail`.
        """
        from ocai.wire.sse import SSEParser

        transport = self._sync_transport()
        attempt = 0
        while True:
            _guard_attempts(attempt)
            _, request = _build_request(self._binding, spec, payload)
            decision = _request_decision(self._policies, request)
            if isinstance(decision, Fail):
                raise decision.error
            if isinstance(decision, Return):
                # TODO: replay a cached streaming body by feeding it through an
                # SSEParser — needs the wire-cache policy to exist first.
                raise NotImplementedError("Return decisions for streams are not supported yet")
            if isinstance(decision, Retry):
                time.sleep(decision.after or 0.0)
                attempt += 1
                continue
            self._binding.credentials.apply(request)
            parser = SSEParser()
            try:
                for chunk in transport.stream_sync(request):
                    for event in parser.feed(chunk):
                        if pipeline is None:
                            yield event
                        else:
                            yield from pipeline.feed(event)
            except OcaiError as err:
                if pipeline is not None and pipeline.reports is None:
                    # Aborted stream: flush anyway (sealing in-flight state)
                    # so the traversal's accounting survives the abort.
                    pipeline.flush()
                raise _refine(refine_error, err) from err
            if pipeline is not None:
                tail, _ = pipeline.flush()
                yield from tail
            return


class AsyncDriver:
    """The async executor of the one pipeline.

    The exact twin of `SyncDriver` differing only in the effects: `asyncio.
    sleep` for `Retry` decisions and `Transport.send`/`stream` for the
    physical call. The shared helpers guarantee the two drivers can never
    drift in request building, decision semantics, or error refinement.
    """

    def __init__(self, binding: Binding, *, policies: Sequence[WirePolicy] = ()) -> None:
        """Bind the driver to its nucleus and hook chain.

        Args:
            binding: The host + credential + transport composition to execute
                against.
            policies: The wire-tier hooks, consulted in order on every attempt.
        """
        self._binding = binding
        self._policies = tuple(policies)

    def _async_transport(self) -> Transport:
        """Return the binding's transport, asserting its async face (backstop)."""
        from ocai.wire.transport import Transport

        transport = self._binding.transport
        if not isinstance(transport, Transport):
            raise CompositionError(
                f"{type(transport).__name__} has no async face; AsyncDriver cannot "
                "send. Bind an async-capable transport (HttpxTransport implements "
                "both faces) or use SyncDriver."
            )
        return transport

    async def execute(
        self,
        *,
        spec: EndpointSpec,
        payload: dict[str, Any],
        refine_error: ErrorRefiner | None = None,
    ) -> dict[str, Any]:
        """Run one non-streaming operation through the full pipeline (async).

        Same attempt loop as `SyncDriver.execute`; see its docstring for the
        decision semantics. Only the sleep and the send await.

        Args:
            spec: The endpoint spec the facade assembled from the codec.
            payload: The already-encoded dialect request body.
            refine_error: The dialect's layer-2 error refiner, if any.

        Returns:
            The raw response dict after the host envelope's `unwrap`.

        Raises:
            OcaiError: The refined taxonomy error when the final attempt
                fails, a policy `Fail`s, or the attempt ceiling is hit.
        """
        transport = self._async_transport()
        attempt = 0
        while True:
            _guard_attempts(attempt)
            envelope, request = _build_request(self._binding, spec, payload)
            decision = _request_decision(self._policies, request)
            if isinstance(decision, Fail):
                raise decision.error
            if isinstance(decision, Return):
                return envelope.unwrap(decision.response.json())
            if isinstance(decision, Retry):
                await asyncio.sleep(decision.after or 0.0)
                attempt += 1
                continue
            # Step 4: the leaf. After every hook, fresh on every attempt.
            self._binding.credentials.apply(request)
            try:
                response = await transport.send(request)
                outcome = Outcome(request=request, attempt=attempt, response=response)
            except OcaiError as err:
                outcome = Outcome(
                    request=request, attempt=attempt, error=_refine(refine_error, err)
                )
            decision = _outcome_decision(self._policies, outcome)
            if isinstance(decision, Retry):
                await asyncio.sleep(decision.after or 0.0)
                attempt += 1
                continue
            if isinstance(decision, Fail):
                raise decision.error
            if isinstance(decision, Return):
                return envelope.unwrap(decision.response.json())
            if outcome.error is not None:
                raise outcome.error
            assert outcome.response is not None
            return envelope.unwrap(outcome.response.json())

    async def stream(
        self,
        *,
        spec: EndpointSpec,
        payload: dict[str, Any],
        refine_error: ErrorRefiner | None = None,
        pipeline: StreamPipeline | None = None,
    ) -> AsyncIterator[Any]:
        """Run one streaming operation, yielding stream events (async).

        The async twin of `SyncDriver.stream`: same admission phase, same
        leaf credential application, same no-replay rule for outcome-phase
        retries, and the same pipeline seam — converted events are yielded,
        the pipeline is flushed exactly once at end-of-stream (tail yielded,
        aborts flushed for accounting), and the flush reports surface on
        `pipeline.reports` for the facade to stamp into the terminal
        `StreamEnd.report`. Exposing the reports on the pipeline (rather
        than returning them) is what keeps the twins identical: an async
        generator cannot return a value.

        Args:
            spec: The endpoint spec (its operation's `streaming` flag set).
            payload: The already-encoded dialect request body.
            refine_error: The dialect's layer-2 error refiner, if any.
            pipeline: The composite transducer the facade built for THIS
                traversal via `Catalog.stream_converter` (fresh per stream,
                never reused), or None to yield raw frames.

        Yields:
            One raw `SSEvent` per server-sent event when `pipeline` is None;
            the pipeline's converted events otherwise.

        Raises:
            OcaiError: The refined taxonomy error on wire failure, or a
                policy `Fail`.
        """
        from ocai.wire.sse import SSEParser

        transport = self._async_transport()
        attempt = 0
        while True:
            _guard_attempts(attempt)
            _, request = _build_request(self._binding, spec, payload)
            decision = _request_decision(self._policies, request)
            if isinstance(decision, Fail):
                raise decision.error
            if isinstance(decision, Return):
                # TODO: replay a cached streaming body by feeding it through an
                # SSEParser — needs the wire-cache policy to exist first.
                raise NotImplementedError("Return decisions for streams are not supported yet")
            if isinstance(decision, Retry):
                await asyncio.sleep(decision.after or 0.0)
                attempt += 1
                continue
            self._binding.credentials.apply(request)
            parser = SSEParser()
            try:
                async for chunk in transport.stream(request):
                    for event in parser.feed(chunk):
                        if pipeline is None:
                            yield event
                        else:
                            for converted in pipeline.feed(event):
                                yield converted
            except OcaiError as err:
                if pipeline is not None and pipeline.reports is None:
                    # Aborted stream: flush anyway (sealing in-flight state)
                    # so the traversal's accounting survives the abort.
                    pipeline.flush()
                raise _refine(refine_error, err) from err
            if pipeline is not None:
                tail, _ = pipeline.flush()
                for converted in tail:
                    yield converted
            return
