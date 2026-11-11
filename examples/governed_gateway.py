"""Public-API integration building blocks; no authentication or HTTP server.

Callers supply an already-governed model, trusted CallContext, conversion policy
and serving metadata. See docs/gateway-integration.md. The context manager owns
stream cleanup even when its event iterator is never consumed.
"""

from __future__ import annotations

from collections.abc import Generator
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from ocai.chat import CANONICAL_CHAT_CHUNK
from ocai.chat import CANONICAL_CHAT_REQUEST
from ocai.chat import CANONICAL_CHAT_RESPONSE
from ocai.chat.facade import InterceptedChatModel
from ocai.chat.facade import ObservedChatModel
from ocai.chat.facade import PreparedChatCall
from ocai.chat.facade import WireChatModel
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChunkType
from ocai.convert.catalog import Catalog
from ocai.core.fidelity import FidelityPolicy
from ocai.core.fidelity import FidelityReport
from ocai.core.result import CallContext
from ocai.core.result import CallResult
from ocai.core.result import StreamOutcome
from ocai.core.usage import Usage
from ocai.openai.chat_completions.client import ClientMetadata
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_CHUNK
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_REQUEST
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_RESPONSE

type GovernedModel = WireChatModel | InterceptedChatModel | ObservedChatModel


def _prepare(
    payload: dict[str, Any],
    model: GovernedModel,
    catalog: Catalog,
    policy: FidelityPolicy,
    streaming: bool,
) -> tuple[PreparedChatCall, FidelityReport]:
    ingress = catalog.convert(payload, CHAT_COMPLETIONS_REQUEST, CANONICAL_CHAT_REQUEST)
    policy.enforce(ingress.report, phase="client_request")
    if not isinstance(ingress.value, ChatRequest):
        raise TypeError("client decode did not produce a canonical request")
    prepared = model.prepare(ingress.value, streaming=streaming)
    policy.enforce(
        prepared.inspection.request_report, phase="request", route=prepared.inspection.route
    )
    return prepared, ingress.report


def client_complete(
    payload: dict[str, Any],
    *,
    model: GovernedModel,
    catalog: Catalog,
    policy: FidelityPolicy,
    metadata: ClientMetadata,
    ctx: CallContext,
) -> CallResult[dict[str, Any]]:
    """Execute all four conversion legs and return one complete fidelity ledger."""
    prepared, ingress = _prepare(payload, model, catalog, policy, False)
    result = prepared.chat(ctx=ctx)
    egress = catalog.convert(result.value, CANONICAL_CHAT_RESPONSE, CHAT_COMPLETIONS_RESPONSE)
    report = FidelityReport(
        edges=[*ingress.edges, *(result.report or FidelityReport()).edges, *egress.report.edges]
    )
    policy.enforce(report, phase="client_response", usage=result.usage, route=result.route)
    return CallResult(
        value=metadata.bind(egress.value), route=result.route, report=report, usage=result.usage
    )


@dataclass
class ClientDelivery:
    """A context-owned JSON-event iterator and its eventual delivery evidence."""

    events: Iterator[dict[str, Any]] = field(default_factory=lambda: iter(()))
    report: FidelityReport = field(default_factory=FidelityReport)
    usage: Usage | None = None
    outcome: StreamOutcome | None = None


@contextmanager
def client_stream(
    payload: dict[str, Any],
    *,
    model: GovernedModel,
    catalog: Catalog,
    policy: FidelityPolicy,
    metadata: ClientMetadata,
    ctx: CallContext,
) -> Generator[ClientDelivery]:
    """Own upstream and conversion resources; accept terminal evidence before delivery.

    Events are JSON documents. The HTTP adapter frames SSE and emits DONE only
    when delivery.outcome is completed after leaving this context. No body is
    buffered; only the terminal finish/usage events wait for policy acceptance.
    """
    prepared, ingress = _prepare(payload, model, catalog, policy, True)
    upstream = prepared.stream(ctx=ctx)
    pipeline = catalog.stream_converter(CANONICAL_CHAT_CHUNK, CHAT_COMPLETIONS_CHUNK)
    delivery = ClientDelivery()
    complete = False
    error: BaseException | None = None

    def account() -> None:
        source = upstream.outcome
        provider_report = source.report if source else None
        if provider_report is None and upstream.end is not None:
            provider_report = upstream.end.report
        provider_report = provider_report or prepared.inspection.request_report
        delivery.report = FidelityReport(
            edges=[*ingress.edges, *provider_report.edges, *(pipeline.reports or ())]
        )
        delivery.usage = source.usage if source else (upstream.end.usage if upstream.end else None)

    def events() -> Generator[dict[str, Any]]:
        nonlocal complete, error
        delivered = 0
        terminal: list[dict[str, Any]] = []
        try:
            for chunk in upstream:
                converted = pipeline.feed(chunk)
                if chunk.type == ChunkType.STREAM_STOP:
                    terminal.extend(converted)
                else:
                    for event in converted:
                        delivered += 1
                        yield metadata.bind(event)
            tail, _ = pipeline.flush()
            terminal.extend(tail)
            account()
            policy.enforce(
                delivery.report,
                phase="client_response",
                usage=delivery.usage,
                route=prepared.inspection.route,
                delivered_events=delivered,
            )
            for event in terminal:
                yield metadata.bind(event)
            complete = True
        except GeneratorExit:
            raise
        except BaseException as caught:
            error = caught
            raise

    iterator = events()
    delivery.events = iterator
    try:
        yield delivery
    finally:
        try:
            iterator.close()
        finally:
            upstream.close()
            if pipeline.reports is None:
                pipeline.flush()
            account()
            delivery.outcome = StreamOutcome(
                status="failed" if error else "completed" if complete else "closed",
                report=delivery.report,
                usage=delivery.usage,
                error=error,
            )
