"""Sans-io byte framing and host-envelope removal before semantic conversion.

Decoder factories are trusted application code. Options are explicit, non-secret
JSON data; no credentials, request bodies or governance context enter this seam.
"""

from __future__ import annotations

import codecs
import hashlib
from collections.abc import Callable
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Protocol

from ocai.core.canonjson import canonical
from ocai.core.errors import StreamProtocolError
from ocai.wire.sse import SSEParser


class StreamDecoder(Protocol):
    """One stream's owned, synchronous framing/envelope decoder.

    Emit plugin input events, never canonical capability parts. Implementations
    buffer incomplete frames rather than whole responses, and reject malformed
    or truncated frames according to their framing's rules. Factories return fresh
    instances; decoders never perform I/O.
    """

    def feed(self, chunk: bytes) -> list[Any]:
        """Consume raw bytes and emit complete, unwrapped events in wire order."""
        ...

    def finish(self) -> list[Any]:
        """Validate normal EOF and emit remaining complete events, once.

        Never invoked on cancellation, explicit close or failure. EOF alone is
        not provider success; semantic terminal validation stays in the plugin.
        """
        ...

    def close(self) -> None:
        """Discard buffers on every exit, including after finish; never emit events."""
        ...


@dataclass(frozen=True)
class StreamFraming:
    """Explicit framing selection with a fresh decoder factory and copied options.

    Attributes:
        name: Non-secret framing/configuration vocabulary, not an interface tag.
        factory: Stable trusted callable taking detached options and producing a
            fresh decoder. No hidden mutable configuration or ambient discovery.
        options: All effective decoder configuration, as non-secret JSON data.
            Changes invalidate prepared calls; factories receive separate copies.
    """

    name: str
    factory: Callable[[dict[str, Any]], StreamDecoder]
    options: Mapping[str, Any] = field(default_factory=dict[str, Any])

    def __post_init__(self) -> None:
        """Validate and snapshot configuration without constructing a decoder."""
        if not self.name:
            raise ValueError("stream framing requires a name")
        options = deepcopy(dict(self.options))
        canonical(options)
        object.__setattr__(self, "options", options)

    def snapshot(self) -> StreamFraming:
        """Detach configuration while preserving the trusted factory identity."""
        return StreamFraming(self.name, self.factory, self.options)

    def __deepcopy__(self, memo: dict[int, Any]) -> StreamFraming:
        """Copy declaration data without cloning executable factory ownership."""
        result = self.snapshot()
        memo[id(self)] = result
        return result

    @property
    def configuration_id(self) -> str:
        """Fingerprint options and factory identity for in-process preparation.

        Bound methods identify their function and owner, not the temporary bound
        method object. This detects replacement, not changes to executable code or
        hidden factory state; factories must use the declared options exclusively.
        """
        function = getattr(self.factory, "__func__", self.factory)
        owner = getattr(self.factory, "__self__", None)
        return hashlib.sha256(
            canonical(
                {
                    "name": self.name,
                    "options": dict(self.options),
                    "factory": id(function),
                    "owner": id(owner) if owner is not None else None,
                }
            ).encode()
        ).hexdigest()

    def build(self) -> StreamDecoder:
        """Build the one-attempt decoder from an independent configuration copy."""
        return self.factory(deepcopy(dict(self.options)))


class _SSEDecoder:
    """Adapt the legacy SSE parser, including split UTF-8 network chunks."""

    def __init__(self, options: dict[str, Any]) -> None:
        if options:
            raise ValueError("default SSE framing accepts no options")
        self._parser = SSEParser()
        self._utf8 = codecs.getincrementaldecoder("utf-8")()

    def feed(self, chunk: bytes) -> list[Any]:
        try:
            return self._parser.feed(self._utf8.decode(chunk))
        except UnicodeDecodeError as exc:
            raise StreamProtocolError("invalid UTF-8 in SSE framing") from exc

    def finish(self) -> list[Any]:
        try:
            return self._parser.feed(self._utf8.decode(b"", final=True))
        except UnicodeDecodeError as exc:
            raise StreamProtocolError("truncated UTF-8 in SSE framing") from exc

    def close(self) -> None:
        self._parser = SSEParser()
        self._utf8.reset()


def sse_framing() -> StreamFraming:
    """Return legacy SSE selection; no stateful decoder is allocated until I/O."""
    return StreamFraming("sse", _SSEDecoder)
