"""The echo chat codec — the four-method translation surface (architecture §7).

A codec converts between one provider interface's wire format and the
canonical chat IR. It is pure meaning: it never makes network calls, never
imports `ocai.wire` or httpx — the `WireChatModel` facade hands its output to
a driver, and the driver hands raw response bodies / SSE event data back.
That split is what lets an offline audit tool re-convert archived traffic
with this plugin installed and no network capability at all.

echo's wire format is, by construction, canonical ocai JSON — so `encode` and
`decode` are the omit-absent `to_dict` / tolerant `from_dict` pair, and the
honest work a real provider does here (field mapping, three-lane routing of
knobs, total decode of unknown tags) is documented per method instead.

TEMPLATE STATUS: pending completion of the re-architected `ocai.chat` types —
imports name the settled contract (architecture §3).
"""

from __future__ import annotations

from typing import Any

from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.core.errors import OcaiError


class EchoChatCodec:
    """Encode/decode the `echo/chat` interface against the canonical IR.

    Instances are stateless and shared: `WireChatModel(codec, binding,
    catalog)` composes one with a `Binding` (where bytes go) and a `Catalog`
    (which conversions exist). The codec speaks only documents; the fragment's
    edges (`fragment.py`) wrap the same mappings for the conversion graph.
    """

    def encode(self, request: ChatRequest) -> dict[str, Any]:
        """Encode a canonical request into the echo wire document.

        Rules a real implementation must honor: every `ChatConfig` knob is
        either mapped (first-class lane), preserved as a censused extension,
        or expanded from `provider_options["echo.chat"]` — this codec expands
        only its own namespace and never forwards a foreign one. Out-of-range
        values pass verbatim (the edge records `APPROXIMATED`; the codec
        never rescales or clamps).

        Args:
            request: The canonical chat request.

        Returns:
            The echo wire request body (canonical JSON, since echo's wire is
            the canonical form).
        """
        return request.to_dict()

    def decode(self, raw: dict[str, Any]) -> ChatResponse:
        """Decode an echo wire response body into the canonical IR.

        Decode is total: unknown part tags fall back to `PartUnknown`,
        unknown envelope keys sweep into `extensions`, unknown finish reasons
        decode to `reason="unknown"` with the wire value preserved in the
        `native` lane. No input may make this raise.

        Args:
            raw: The JSON-decoded echo response body.

        Returns:
            The canonical chat response (a pure graph payload — the
            `FidelityReport` lives on `CallResult`, never here).
        """
        return ChatResponse.from_dict(raw)

    def decode_event(self, event: dict[str, Any]) -> ChatChunk | None:
        """Decode one JSON-decoded SSE event into a canonical chunk.

        The driver owns the SSE framing (`ocai.wire.sse`) and calls this per
        event; returning `None` drops keep-alive/no-op events. A real
        implementation emits the canonical `ChatChunk` algebra — typed deltas
        mirroring the part taxonomy, a terminal chunk carrying
        `StreamEnd(usage, finish, report)` — and must satisfy the fold law
        `fold(stream(request)) == complete(request)` pinned by fold-triple
        fixtures.

        Args:
            event: One JSON-decoded wire event.

        Returns:
            The canonical chunk, or `None` for events with no canonical
            meaning.

        Raises:
            NotImplementedError: echo does not stream yet (its
                `CapabilityProfile` declares `streaming: ABSENT`).
        """
        # TODO: implement alongside a StreamEdge transducer + fold triples
        # when echo grows streaming; profile gate refuses before this is hit.
        raise NotImplementedError("echo does not stream yet")

    def map_error(self, status: int, body: dict[str, Any]) -> OcaiError:
        """Map an echo error response onto the shared error taxonomy.

        Every provider error becomes one of `ocai.core.errors`' types
        (`RateLimitError`, `AuthError`, `ContextLengthError`,
        `ContentFilterError`, `TransientError`, or bare `OcaiError`) so user
        retry/fallback logic is provider-neutral. The driver calls this with
        the HTTP status and JSON-decoded body; the returned error is raised
        (or, mid-stream, surfaced as the stream's error event).

        Args:
            status: The HTTP status code.
            body: The JSON-decoded error body.

        Returns:
            The taxonomy error to raise.

        Raises:
            NotImplementedError: The template maps no errors yet.
        """
        # TODO: map echo's error codes (429→RateLimitError, 401→AuthError, …)
        # once the fictional wire defines them.
        raise NotImplementedError("echo error mapping not implemented yet")
