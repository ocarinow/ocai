# `ocai.runtime` API reference

Generated from the checked-out package sources. Signatures, declared fields,
methods, type aliases and explicit re-exports are checked for drift. Inherited
members follow their named base class; a type's presence does not establish
provider execution support. See [supported features](../provider-feature-matrix.md).

## `ocai.runtime`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/runtime/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-runtime-binding"></span>`Binding` | [`ocai.runtime.binding.Binding`](ocai-runtime.md#ocai-runtime-binding-binding) |
| <span id="ocai-runtime-compositionerror"></span>`CompositionError` | [`ocai.runtime.binding.CompositionError`](ocai-runtime.md#ocai-runtime-binding-compositionerror) |
| <span id="ocai-runtime-mode"></span>`Mode` | [`ocai.runtime.binding.Mode`](ocai-runtime.md#ocai-runtime-binding-mode) |
| <span id="ocai-runtime-asyncbackend"></span>`AsyncBackend` | [`ocai.runtime.decisions.AsyncBackend`](ocai-runtime.md#ocai-runtime-decisions-asyncbackend) |
| <span id="ocai-runtime-decision"></span>`Decision` | [`ocai.runtime.decisions.Decision`](ocai-runtime.md#ocai-runtime-decisions-decision) |
| <span id="ocai-runtime-fail"></span>`Fail` | [`ocai.runtime.decisions.Fail`](ocai-runtime.md#ocai-runtime-decisions-fail) |
| <span id="ocai-runtime-outcome"></span>`Outcome` | [`ocai.runtime.decisions.Outcome`](ocai-runtime.md#ocai-runtime-decisions-outcome) |
| <span id="ocai-runtime-proceed"></span>`Proceed` | [`ocai.runtime.decisions.Proceed`](ocai-runtime.md#ocai-runtime-decisions-proceed) |
| <span id="ocai-runtime-retry"></span>`Retry` | [`ocai.runtime.decisions.Retry`](ocai-runtime.md#ocai-runtime-decisions-retry) |
| <span id="ocai-runtime-return"></span>`Return` | [`ocai.runtime.decisions.Return`](ocai-runtime.md#ocai-runtime-decisions-return) |
| <span id="ocai-runtime-syncbackend"></span>`SyncBackend` | [`ocai.runtime.decisions.SyncBackend`](ocai-runtime.md#ocai-runtime-decisions-syncbackend) |
| <span id="ocai-runtime-wirepolicy"></span>`WirePolicy` | [`ocai.runtime.decisions.WirePolicy`](ocai-runtime.md#ocai-runtime-decisions-wirepolicy) |
| <span id="ocai-runtime-asyncdriver"></span>`AsyncDriver` | [`ocai.runtime.drivers.AsyncDriver`](ocai-runtime.md#ocai-runtime-drivers-asyncdriver) |
| <span id="ocai-runtime-errorrefiner"></span>`ErrorRefiner` | [`ocai.runtime.drivers.ErrorRefiner`](ocai-runtime.md#ocai-runtime-drivers-errorrefiner) |
| <span id="ocai-runtime-syncdriver"></span>`SyncDriver` | [`ocai.runtime.drivers.SyncDriver`](ocai-runtime.md#ocai-runtime-drivers-syncdriver) |
| <span id="ocai-runtime-from-async"></span>`from_async` | [`ocai.runtime.dual.from_async`](ocai-runtime.md#ocai-runtime-dual-from-async) |
| <span id="ocai-runtime-from-sync"></span>`from_sync` | [`ocai.runtime.dual.from_sync`](ocai-runtime.md#ocai-runtime-dual-from-sync) |
| <span id="ocai-runtime-asyncnexthandler"></span>`AsyncNextHandler` | [`ocai.runtime.interceptors.AsyncNextHandler`](ocai-runtime.md#ocai-runtime-interceptors-asyncnexthandler) |
| <span id="ocai-runtime-call"></span>`Call` | [`ocai.runtime.interceptors.Call`](ocai-runtime.md#ocai-runtime-interceptors-call) |
| <span id="ocai-runtime-callinterceptor"></span>`CallInterceptor` | [`ocai.runtime.interceptors.CallInterceptor`](ocai-runtime.md#ocai-runtime-interceptors-callinterceptor) |
| <span id="ocai-runtime-nexthandler"></span>`NextHandler` | [`ocai.runtime.interceptors.NextHandler`](ocai-runtime.md#ocai-runtime-interceptors-nexthandler) |
| <span id="ocai-runtime-acompose"></span>`acompose` | [`ocai.runtime.interceptors.acompose`](ocai-runtime.md#ocai-runtime-interceptors-acompose) |
| <span id="ocai-runtime-compose"></span>`compose` | [`ocai.runtime.interceptors.compose`](ocai-runtime.md#ocai-runtime-interceptors-compose) |
| <span id="ocai-runtime-callfinished"></span>`CallFinished` | [`ocai.runtime.observe.CallFinished`](ocai-runtime.md#ocai-runtime-observe-callfinished) |
| <span id="ocai-runtime-callstarted"></span>`CallStarted` | [`ocai.runtime.observe.CallStarted`](ocai-runtime.md#ocai-runtime-observe-callstarted) |
| <span id="ocai-runtime-observeevent"></span>`ObserveEvent` | [`ocai.runtime.observe.ObserveEvent`](ocai-runtime.md#ocai-runtime-observe-observeevent) |
| <span id="ocai-runtime-observer"></span>`Observer` | [`ocai.runtime.observe.Observer`](ocai-runtime.md#ocai-runtime-observe-observer) |
| <span id="ocai-runtime-wireexchanged"></span>`WireExchanged` | [`ocai.runtime.observe.WireExchanged`](ocai-runtime.md#ocai-runtime-observe-wireexchanged) |

## `ocai.runtime.binding`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/runtime/binding.py)

### `Mode` { #ocai-runtime-binding-mode }

```python
type Mode = Literal['sync', 'async']
```

### `CompositionError` { #ocai-runtime-binding-compositionerror }

```python
class CompositionError(OcaiError)
```

````text
A composed stack cannot serve the requested execution mode.

Raised by `Binding.validate` (and the §3.4 front doors) at composition
time — never mid-request — and its message names the offending component
and the face it lacks, so the fix (bind a dual-face transport, wrap the
port via `ocai.runtime.dual`, swap the backend) is immediate.
````

### `Binding` { #ocai-runtime-binding-binding }

```python
class Binding:
    host: Host
    credentials: Credential
    transport: Transport | SyncTransport
    extra_headers: Mapping[str, str] = field(default_factory=dict[str, str])
```

````text
The reusable, capability-neutral remote nucleus.

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
        so they win on case-insensitive conflict. Copied on construction;
        authentication headers require credentials instead. Defaults to empty.
````

#### `Binding.validate` { #ocai-runtime-binding-binding-validate }

```python
def validate(self, mode: Mode='sync') -> None
```

````text
Check this binding can serve `mode`, at composition time.

Verifies the transport structurally offers the face `mode` needs:
`send_sync`/`stream_sync`/`close` (`SyncTransport`) for sync,
`send`/`stream`/`aclose` (`Transport`) for async.

Args:
    mode: The execution mode the binding will be driven in.

Raises:
    CompositionError: If the transport lacks the required face; the
        message names the transport type and the missing face.
````

## `ocai.runtime.deadline`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/runtime/deadline.py)

### `Deadline` { #ocai-runtime-deadline-deadline }

```python
class Deadline
```

````text
Translate an aware wall-clock deadline once, then use monotonic time.

Sync operations cooperate via request timeouts and checks before/after I/O;
arbitrary blocking Python cannot be preempted. Late output is never accepted.
Async drivers additionally cancel each pending operation at the remaining bound.
````

#### `Deadline.__init__` { #ocai-runtime-deadline-deadline---init-- }

```python
def __init__(self, ctx: CallContext | None=None) -> None
```

````text
Capture the remaining window; reject ambiguous naive datetimes.
````

#### `Deadline.remaining` { #ocai-runtime-deadline-deadline-remaining }

```python
def remaining(self) -> float | None
```

````text
Return the remaining seconds, raising when the budget has expired.
````

#### `Deadline.delay` { #ocai-runtime-deadline-deadline-delay }

```python
def delay(self, seconds: float | None) -> float
```

````text
Validate a retry wait without allowing it to extend the deadline.
````

#### `Deadline.sleep` { #ocai-runtime-deadline-deadline-sleep }

```python
def sleep(self, seconds: float | None) -> None
```

````text
Wait synchronously within the remaining budget.
````

#### `Deadline.asleep` { #ocai-runtime-deadline-deadline-asleep }

```python
async def asleep(self, seconds: float | None) -> None
```

````text
Wait asynchronously within the remaining budget.
````

## `ocai.runtime.decisions`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/runtime/decisions.py)

### `Proceed` { #ocai-runtime-decisions-proceed }

```python
class Proceed
```

````text
Continue the pipeline: the policy has no objection.

The neutral decision. A driver consults each policy in order and moves to
the next stage only when every policy returned `Proceed`; the first
non-`Proceed` decision short-circuits the phase.
````

### `Retry` { #ocai-runtime-decisions-retry }

```python
class Retry:
    after: float | None = None
```

````text
Re-run the attempt after an optional delay.

Returned by a policy's `on_outcome` (e.g. `RetryPolicy` on a
`TransientError`) or `on_request` (e.g. a rate limiter deferring
admission). The driver executes the wait — `time.sleep` in `SyncDriver`,
`asyncio.sleep` in `AsyncDriver` — then rebuilds the request and re-runs
every `on_request` hook, re-applying the credential fresh for the new
attempt.

Attributes:
    after: Seconds to wait before the next attempt; `None` means retry
        immediately.
````

### `Fail` { #ocai-runtime-decisions-fail }

```python
class Fail:
    error: OcaiError
```

````text
Abort the call: the driver raises `error` without sending (or resending).

How a policy vetoes — a governance hook refusing a destination, a rate
limiter whose budget is exhausted, a retry policy converting repeated
transient failures into a terminal one.

Attributes:
    error: The taxonomy error the driver raises to the caller.
````

### `Return` { #ocai-runtime-decisions-return }

```python
class Return:
    response: HttpResponse
```

````text
Short-circuit with a synthesized response: the driver skips the send.

How a wire-tier cache serves a hit: the policy returns the stored
`HttpResponse` and the driver treats it exactly as if the transport had
produced it (envelope unwrap included), so downstream decode cannot tell
the difference.

Attributes:
    response: The wire response to return in place of a network send.
````

### `Decision` { #ocai-runtime-decisions-decision }

```python
type Decision = Proceed | Retry | Fail | Return
```

### `Outcome` { #ocai-runtime-decisions-outcome }

```python
class Outcome:
    request: HttpRequest
    attempt: int
    response: HttpResponse | None = None
    error: OcaiError | None = None
```

````text
What one send attempt produced — the input to `WirePolicy.on_outcome`.

Built by the driver after each attempt, carrying *either* a successful
`response` *or* a taxonomy `error` (exactly one is set). The `error` is
already two-layer refined (transport's status-based classification, then
the dialect's body-aware `map_error`), so a retry policy branching on
`TransientError` sees the precise error and its `retry_after` hint.
`attempt` is zero-based, which lets policies stay **stateless**: backoff
math derives from the outcome, so one policy instance is safely shared
across concurrent calls and both drivers.

Attributes:
    request: The safe post-hook request. Authentication is applied only
        to a detached transport copy; retained hook references stay safe.
    attempt: The zero-based index of this attempt.
    response: The successful wire response, when the attempt succeeded.
    error: The refined taxonomy error, when the attempt failed.
````

#### `Outcome.ctx` { #ocai-runtime-decisions-outcome-ctx }

```python
@property
def ctx(self) -> CallContext | None
```

````text
The logical call context, never provider payload or credentials.
````

### `WirePolicy` { #ocai-runtime-decisions-wirepolicy }

```python
class WirePolicy(Protocol)
```

````text
A wire-tier hook: sees requests and outcomes, returns `Decision`s.

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
````

#### `WirePolicy.on_request` { #ocai-runtime-decisions-wirepolicy-on-request }

```python
def on_request(self, request: HttpRequest) -> Decision
```

````text
Judge an outgoing request before it is sent.

Called once per attempt, before `Credential.apply` — the request never
carries a secret here. Return `Proceed` to admit, `Retry` to defer,
`Fail` to veto, or `Return` to serve a synthesized response.

Args:
    request: The safe wire request. Its ctx is the per-call snapshot;
        attempt counts physical I/O and admission counts deferred checks.

Returns:
    The policy's decision for this attempt.
````

#### `WirePolicy.on_outcome` { #ocai-runtime-decisions-wirepolicy-on-outcome }

```python
def on_outcome(self, outcome: Outcome) -> Decision
```

````text
Judge the result of a send attempt.

Return `Proceed` to accept the outcome as final (the driver then
returns the response or raises the error), `Retry` to re-attempt,
`Fail` to replace the error, or `Return` to substitute a response.

Args:
    outcome: The attempt's result — response or refined error.

Returns:
    The policy's decision for what happens next.
````

### `SyncBackend` { #ocai-runtime-decisions-syncbackend }

```python
class SyncBackend(Protocol)
```

````text
The blocking face an effectful policy backend declares.

A structural marker checked with `isinstance` at composition-time
validation: a component offering this face can run under `SyncDriver`.
The anchor method is `close` — mirroring the transport convention
(`SyncTransport.close`), so transports and policy backends are validated
by one rule. A *pure* policy (e.g. `RetryPolicy`) declares neither face
and passes validation in both modes.
````

#### `SyncBackend.close` { #ocai-runtime-decisions-syncbackend-close }

```python
def close(self) -> None
```

````text
Release the backend's blocking-I/O resources.
````

### `AsyncBackend` { #ocai-runtime-decisions-asyncbackend }

```python
class AsyncBackend(Protocol)
```

````text
The async face an effectful policy backend declares.

The async twin of `SyncBackend`, anchored on `aclose` (mirroring
`Transport.aclose`). A component declaring *only* this face fails
`validate(mode="sync")` with a `CompositionError` naming it — the
mid-request `TypeError` class of bug dies at composition time.
````

#### `AsyncBackend.aclose` { #ocai-runtime-decisions-asyncbackend-aclose }

```python
async def aclose(self) -> None
```

````text
Release the backend's async-I/O resources.
````

## `ocai.runtime.drivers`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/runtime/drivers.py)

### `ErrorRefiner` { #ocai-runtime-drivers-errorrefiner }

```python
type ErrorRefiner = Callable[[OcaiError], OcaiError | None]
```

### `build_request` { #ocai-runtime-drivers-build-request }

```python
def build_request(binding: Binding, spec: EndpointSpec, payload: dict[str, Any]) -> tuple[EnvelopeTransform, HttpRequest]
```

````text
Build the wire request for one attempt — steps 3 of the pipeline.

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
````

### `SyncDriver` { #ocai-runtime-drivers-syncdriver }

```python
class SyncDriver
```

````text
The blocking executor of the one pipeline.

Owns the sync effects the sans-io policies describe: `time.sleep` for
`Retry` decisions and `SyncTransport.send_sync`/`stream_sync` for the
physical call. Everything else — request building, decision phases, error
refinement — is the shared pure logic above, identical to `AsyncDriver`'s.

Constructed by the wire-backed facade from a `Binding` and the wire
policies; `Binding.validate(mode="sync")` should have admitted the stack
at composition time, so the transport-face check here is a backstop.
````

#### `SyncDriver.__init__` { #ocai-runtime-drivers-syncdriver---init-- }

```python
def __init__(self, binding: Binding, *, policies: Sequence[WirePolicy]=(), observers: Sequence[Observer]=()) -> None
```

````text
Bind the driver to its nucleus and hook chain.

Args:
    binding: The host + credential + transport composition to execute
        against.
    policies: The wire-tier hooks, consulted in order on every attempt.
    observers: Passive metadata-only physical attempt observers.
````

#### `SyncDriver.execute` { #ocai-runtime-drivers-syncdriver-execute }

```python
def execute(self, *, spec: EndpointSpec, payload: dict[str, Any], ctx: CallContext | None=None, budget: Deadline | None=None, request_guard: Callable[[HttpRequest], None] | None=None, refine_error: ErrorRefiner | None=None, error_mapping: HostErrorMapper | None=None) -> dict[str, Any]
```

````text
Return the legacy payload; execute_response also preserves HTTP evidence.
````

#### `SyncDriver.execute_response` { #ocai-runtime-drivers-syncdriver-execute-response }

```python
def execute_response(self, *, spec: EndpointSpec, payload: dict[str, Any], ctx: CallContext | None=None, budget: Deadline | None=None, request_guard: Callable[[HttpRequest], None] | None=None, refine_error: ErrorRefiner | None=None, error_mapping: HostErrorMapper | None=None) -> DriverResponse
```

````text
Run one non-streaming operation through the full pipeline (blocking).

Loops attempts: build request → on-request hooks → credential at the
leaf → send → refine errors → on-outcome hooks; a `Retry` decision
sleeps and loops, `Return` short-circuits with the policy's response,
`Fail` raises. When every policy proceeds, the attempt's own result
stands: return detached response evidence, or raise the refined error.

Args:
    spec: The endpoint spec the facade assembled from the codec.
    payload: The already-encoded dialect request body.
    ctx: Trusted per-call facts; never encoded into provider requests.
    budget: Shared whole-call budget, or derived from ctx.
    request_guard: Enforce an approved wire snapshot before authentication.
    refine_error: The dialect's layer-2 error refiner, if any.
    error_mapping: Approved host mapping snapshot, or select from the host.

Returns:
    DriverResponse containing the selected HTTP snapshot and unwrapped body;
    host adaptation and graph decode are the facade's job.

Raises:
    OcaiError: The refined taxonomy error when the final attempt
        fails, a policy `Fail`s, or the attempt ceiling is hit.
````

#### `SyncDriver.stream` { #ocai-runtime-drivers-syncdriver-stream }

```python
def stream(self, *, spec: EndpointSpec, payload: dict[str, Any], ctx: CallContext | None=None, budget: Deadline | None=None, request_guard: Callable[[HttpRequest], None] | None=None, refine_error: ErrorRefiner | None=None, error_mapping: HostErrorMapper | None=None, pipeline: StreamPipeline | None=None, framing: StreamFraming | None=None) -> Iterator[Any]
```

````text
Run one streaming operation, yielding stream events (blocking).

Admission runs the same on-request phase as `execute` (a rate limiter
may defer a stream with `Retry`; admission retries happen before any
byte flows, so the pipeline is never fed on a discarded attempt), the
credential is applied at the leaf, then bytes are pumped through the
host-selected sans-io decoder. When a `pipeline` is bound, each parsed frame is
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
    ctx: Trusted per-call facts; never encoded into provider requests.
    budget: Shared whole-call budget, or derived from ctx.
    request_guard: Enforce an approved wire snapshot before authentication.
    refine_error: The dialect's layer-2 error refiner, if any.
    error_mapping: Approved host mapping snapshot, or select from the host.
    pipeline: The composite transducer the facade built for THIS
        traversal via `Catalog.stream_converter` (fresh per stream,
        never reused), or None to yield raw frames.
    framing: Approved framing snapshot, or None to select from the host.

Yields:
    The selected framing's events (SSE by default) when `pipeline` is None;
    the pipeline's converted events (canonical `ChatChunk`s when the
    planned path ends at the canonical chunk node) otherwise.

Raises:
    OcaiError: The refined taxonomy error on wire failure, or a
        policy `Fail`.
````

### `AsyncDriver` { #ocai-runtime-drivers-asyncdriver }

```python
class AsyncDriver
```

````text
The async executor of the one pipeline.

The exact twin of `SyncDriver` differing only in the effects: `asyncio.
sleep` for `Retry` decisions and `Transport.send`/`stream` for the
physical call. The shared helpers guarantee the two drivers can never
drift in request building, decision semantics, or error refinement.
````

#### `AsyncDriver.__init__` { #ocai-runtime-drivers-asyncdriver---init-- }

```python
def __init__(self, binding: Binding, *, policies: Sequence[WirePolicy]=(), observers: Sequence[Observer]=()) -> None
```

````text
Bind the driver to its nucleus and hook chain.

Args:
    binding: The host + credential + transport composition to execute
        against.
    policies: The wire-tier hooks, consulted in order on every attempt.
    observers: Passive metadata-only physical attempt observers.
````

#### `AsyncDriver.execute` { #ocai-runtime-drivers-asyncdriver-execute }

```python
async def execute(self, *, spec: EndpointSpec, payload: dict[str, Any], ctx: CallContext | None=None, budget: Deadline | None=None, request_guard: Callable[[HttpRequest], None] | None=None, refine_error: ErrorRefiner | None=None, error_mapping: HostErrorMapper | None=None) -> dict[str, Any]
```

````text
Return the legacy payload; execute_response also preserves HTTP evidence.
````

#### `AsyncDriver.execute_response` { #ocai-runtime-drivers-asyncdriver-execute-response }

```python
async def execute_response(self, *, spec: EndpointSpec, payload: dict[str, Any], ctx: CallContext | None=None, budget: Deadline | None=None, request_guard: Callable[[HttpRequest], None] | None=None, refine_error: ErrorRefiner | None=None, error_mapping: HostErrorMapper | None=None) -> DriverResponse
```

````text
Run one non-streaming operation through the full pipeline (async).

Same attempt loop as `SyncDriver.execute`; see its docstring for the
decision semantics. Only the sleep and the send await.

Args:
    spec: The endpoint spec the facade assembled from the codec.
    payload: The already-encoded dialect request body.
    ctx: Trusted per-call facts; never encoded into provider requests.
    budget: Shared whole-call budget, or derived from ctx.
    request_guard: Enforce an approved wire snapshot before authentication.
    refine_error: The dialect's layer-2 error refiner, if any.
    error_mapping: Approved host mapping snapshot, or select from the host.

Returns:
    DriverResponse containing the selected HTTP snapshot and unwrapped body.

Raises:
    OcaiError: The refined taxonomy error when the final attempt
        fails, a policy `Fail`s, or the attempt ceiling is hit.
````

#### `AsyncDriver.stream` { #ocai-runtime-drivers-asyncdriver-stream }

```python
async def stream(self, *, spec: EndpointSpec, payload: dict[str, Any], ctx: CallContext | None=None, budget: Deadline | None=None, request_guard: Callable[[HttpRequest], None] | None=None, refine_error: ErrorRefiner | None=None, error_mapping: HostErrorMapper | None=None, pipeline: StreamPipeline | None=None, framing: StreamFraming | None=None) -> AsyncIterator[Any]
```

````text
Run one streaming operation, yielding stream events (async).

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
    ctx: Trusted per-call facts; never encoded into provider requests.
    budget: Shared whole-call budget, or derived from ctx.
    request_guard: Enforce an approved wire snapshot before authentication.
    refine_error: The dialect's layer-2 error refiner, if any.
    error_mapping: Approved host mapping snapshot, or select from the host.
    pipeline: The composite transducer the facade built for THIS
        traversal via `Catalog.stream_converter` (fresh per stream,
        never reused), or None to yield raw frames.
    framing: Approved framing snapshot, or None to select from the host.

Yields:
    The selected framing's events (SSE by default) when `pipeline` is None;
    the pipeline's converted events otherwise.

Raises:
    OcaiError: The refined taxonomy error on wire failure, or a
        policy `Fail`.
````

## `ocai.runtime.dual`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/runtime/dual.py)

### `from_sync` { #ocai-runtime-dual-from-sync }

```python
def from_sync(port: Any) -> Any
```

````text
Wrap a sync-only port, adding thread-offloaded async faces.

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
````

### `from_async` { #ocai-runtime-dual-from-async }

```python
def from_async(port: Any) -> Any
```

````text
Wrap an async-only port, adding portal-backed sync faces.

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
````

## `ocai.runtime.interceptors`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/runtime/interceptors.py)

### `Call` { #ocai-runtime-interceptors-call }

```python
class Call:
    request: Any
    ctx: CallContext | None = None
```

````text
One canonical invocation traveling down an interceptor chain.

Pairs the capability request payload with the per-request governance
context so interceptors can gate on `ctx` (classification, tenant,
deadline) without the payload and context traveling out of band. The
request stays `Any` at this tier because interceptors are
capability-neutral — a chain serves `ChatRequest` and an embedding
request with the same code.

Attributes:
    request: The canonical request payload (e.g. a `ChatRequest`).
    ctx: The governance carrier riding along with the call, if any.
````

### `NextHandler` { #ocai-runtime-interceptors-nexthandler }

```python
type NextHandler = Callable[[Call], CallResult[Any]]
```

### `AsyncNextHandler` { #ocai-runtime-interceptors-asyncnexthandler }

```python
type AsyncNextHandler = Callable[[Call], Awaitable[CallResult[Any]]]
```

### `CallInterceptor` { #ocai-runtime-interceptors-callinterceptor }

```python
class CallInterceptor(Protocol)
```

````text
Port-tier middleware over canonical calls, with sync and async faces.

Both faces express the same behavior; the driver mode selects which one
runs. A pure interceptor implements both by sharing its logic; an
interceptor bound to effectful backends declares the matching
`SyncBackend`/`AsyncBackend` faces (`ocai.runtime.decisions`) so
composition-time validation can reject an impossible composition up
front.
````

#### `CallInterceptor.intercept` { #ocai-runtime-interceptors-callinterceptor-intercept }

```python
def intercept(self, call: Call, next: NextHandler) -> CallResult[Any]
```

````text
Handle `call`, delegating inward via `next` as needed (sync face).

Args:
    call: The canonical call traveling down the chain.
    next: The continuation for the rest of the chain; call it zero
        times to short-circuit, once to pass through, or several
        times (e.g. fallback across targets).

Returns:
    The `CallResult` to hand back up the chain — `next`'s result,
    or a replacement.
````

#### `CallInterceptor.aintercept` { #ocai-runtime-interceptors-callinterceptor-aintercept }

```python
async def aintercept(self, call: Call, next: AsyncNextHandler) -> CallResult[Any]
```

````text
Handle `call`, delegating inward via `next` as needed (async face).

Args:
    call: The canonical call traveling down the chain.
    next: The async continuation for the rest of the chain.

Returns:
    The `CallResult` to hand back up the chain.
````

### `compose` { #ocai-runtime-interceptors-compose }

```python
def compose(interceptors: Sequence[CallInterceptor], terminal: NextHandler) -> NextHandler
```

````text
Fold `interceptors` over `terminal` into one sync handler.

The first interceptor in the sequence is the outermost layer: it sees the
call first and the result last. An empty sequence returns `terminal`
unchanged.

Args:
    interceptors: The chain, outermost first.
    terminal: The innermost handler — typically the port's own call.

Returns:
    A single handler running the whole onion.
````

### `acompose` { #ocai-runtime-interceptors-acompose }

```python
def acompose(interceptors: Sequence[CallInterceptor], terminal: AsyncNextHandler) -> AsyncNextHandler
```

````text
Fold `interceptors` over `terminal` into one async handler.

The async twin of `compose`, dispatching through each interceptor's
`aintercept` face.

Args:
    interceptors: The chain, outermost first.
    terminal: The innermost async handler.

Returns:
    A single async handler running the whole onion.
````

### `SyncStream` { #ocai-runtime-interceptors-syncstream }

```python
class SyncStream(Protocol)
```

````text
Capability-neutral owned iterator returned by streaming middleware.
````

#### `SyncStream.close` { #ocai-runtime-interceptors-syncstream-close }

```python
def close(self) -> None
```

````text
Close upstream, including when no event has been consumed.
````

#### `SyncStream.outcome` { #ocai-runtime-interceptors-syncstream-outcome }

```python
@property
def outcome(self) -> StreamOutcome | None
```

````text
Available terminal execution evidence, or None while pending.
````

### `AsyncStream` { #ocai-runtime-interceptors-asyncstream }

```python
class AsyncStream(Protocol)
```

````text
Async twin of the capability-neutral owned stream.
````

#### `AsyncStream.aclose` { #ocai-runtime-interceptors-asyncstream-aclose }

```python
async def aclose(self) -> None
```

````text
Close upstream, including an unconsumed stream.
````

#### `AsyncStream.outcome` { #ocai-runtime-interceptors-asyncstream-outcome }

```python
@property
def outcome(self) -> StreamOutcome | None
```

````text
Available terminal execution evidence, or None while pending.
````

### `NextStreamHandler` { #ocai-runtime-interceptors-nextstreamhandler }

```python
type NextStreamHandler = Callable[[Call], SyncStream]
```

### `AsyncNextStreamHandler` { #ocai-runtime-interceptors-asyncnextstreamhandler }

```python
type AsyncNextStreamHandler = Callable[[Call], Awaitable[AsyncStream]]
```

### `StreamInterceptor` { #ocai-runtime-interceptors-streaminterceptor }

```python
class StreamInterceptor(Protocol)
```

````text
Explicit stream admission/wrapping contract, distinct from unary results.

Admission runs eagerly before delegating. Wrappers own and close their
continuation's stream, preserve terminal accounting, and must not buffer
the full response. Never restart generation after exposing an event.
Implement alongside CallInterceptor to govern all four capability faces.
````

#### `StreamInterceptor.intercept_stream` { #ocai-runtime-interceptors-streaminterceptor-intercept-stream }

```python
def intercept_stream(self, call: Call, next: NextStreamHandler) -> SyncStream
```

````text
Admit, reject or wrap the owned synchronous continuation stream.
````

#### `StreamInterceptor.aintercept_stream` { #ocai-runtime-interceptors-streaminterceptor-aintercept-stream }

```python
async def aintercept_stream(self, call: Call, next: AsyncNextStreamHandler) -> AsyncStream
```

````text
Admit, reject or wrap the owned asynchronous continuation stream.
````

### `compose_stream` { #ocai-runtime-interceptors-compose-stream }

```python
def compose_stream(interceptors: Sequence[StreamInterceptor], terminal: NextStreamHandler) -> NextStreamHandler
```

````text
Compose a streaming onion, outermost first, without pulling any events.
````

### `acompose_stream` { #ocai-runtime-interceptors-acompose-stream }

```python
def acompose_stream(interceptors: Sequence[StreamInterceptor], terminal: AsyncNextStreamHandler) -> AsyncNextStreamHandler
```

````text
Compose the async streaming onion with the same admission order.
````

## `ocai.runtime.observe`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/runtime/observe.py)

### `CallStarted` { #ocai-runtime-observe-callstarted }

```python
class CallStarted:
    call_id: str
    capability: Capability = CHAT
    ctx: CallContext | None = None
    streaming: bool = False
```

````text
One invocation starts eagerly, before admission and lazy stream I/O.
````

### `CallFinished` { #ocai-runtime-observe-callfinished }

```python
class CallFinished:
    call_id: str
    status: str
    usage: Usage | None = None
    report: FidelityReport | None = None
    route: Route | None = None
    error_type: str | None = None
    duration_s: float | None = None
```

````text
Exactly one invocation outcome; accounting never implies output success.
````

### `WireStarted` { #ocai-runtime-observe-wirestarted }

```python
class WireStarted:
    call_id: str
    attempt: int
    node: NodeId
    streaming: bool = False
```

````text
A physical attempt starts; admission waits never emit this event.
````

### `WireExchanged` { #ocai-runtime-observe-wireexchanged }

```python
class WireExchanged:
    call_id: str
    attempt: int
    status: str
    node: NodeId
    http_status: int | None = None
    error_type: str | None = None
    duration_s: float | None = None
```

````text
A physical attempt ended, independently of logical conversion/admission.
````

### `ObserveEvent` { #ocai-runtime-observe-observeevent }

```python
type ObserveEvent = CallStarted | CallFinished | WireStarted | WireExchanged
```

### `Observer` { #ocai-runtime-observe-observer }

```python
class Observer(Protocol)
```

````text
A fast passive sink; each observer receives an independent event snapshot.
````

#### `Observer.on_event` { #ocai-runtime-observe-observer-on-event }

```python
def on_event(self, event: ObserveEvent) -> None
```

````text
Observe metadata; exceptions are isolated and cannot enforce policy.
````

### `dispatch` { #ocai-runtime-observe-dispatch }

```python
def dispatch(observers: Sequence[Observer], event: ObserveEvent) -> None
```

````text
Isolate callback failures and mutations without logging sensitive exceptions.
````

### `failure_status` { #ocai-runtime-observe-failure-status }

```python
def failure_status(error: BaseException) -> str
```

````text
Classify cancellation without exporting exception text or provider bodies.
````

### `Invocation` { #ocai-runtime-observe-invocation }

```python
class Invocation
```

````text
Per-invocation lifecycle state, explicitly carried by a capability wrapper.
````

#### `Invocation.__init__` { #ocai-runtime-observe-invocation---init-- }

```python
def __init__(self, observers: Sequence[Observer], ctx: CallContext | None, *, streaming: bool=False) -> None
```

````text
Snapshot context and emit start before any admission policy executes.
````

#### `Invocation.finish` { #ocai-runtime-observe-invocation-finish }

```python
def finish(self, *, status: str='completed', usage: Usage | None=None, report: FidelityReport | None=None, route: Route | None=None, error: BaseException | None=None) -> None
```

````text
Emit once, after cleanup; error objects never enter the event.
````

### `Attempt` { #ocai-runtime-observe-attempt }

```python
class Attempt
```

````text
Per-physical-attempt observations, correlated by explicit CallContext.
````

#### `Attempt.__init__` { #ocai-runtime-observe-attempt---init-- }

```python
def __init__(self, observers: Sequence[Observer], ctx: CallContext | None, node: NodeId, attempt: int, *, streaming: bool=False) -> None
```

````text
Emit immediately before calling the transport, after credential setup.
````

#### `Attempt.finish` { #ocai-runtime-observe-attempt-finish }

```python
def finish(self, error: BaseException | None=None, http_status: int | None=None) -> None
```

````text
Close the attempt once; a successful HTTP stream may still be malformed.
````
