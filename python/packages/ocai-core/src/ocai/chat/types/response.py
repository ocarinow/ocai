"""The canonical chat response (architecture §3.1).

`ChatResponse` is a **pure graph payload**: the model's message, why it
stopped, what it consumed, and the provider anchors that identify it. It has
**no report field** — the `FidelityReport` lives on `CallResult.report` and
only there (one home, not two). Single message forever: decoded
`choices[1:]` land in a censused extension with reported loss, never in the
canonical shape.

`ResponseInfo` carries the response's provider anchors: the id as a
`ProviderRef` (directly reusable as `previous_response_id` on interfaces
with server-side threads) and the provider's echo of which model actually
served the call.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any
from typing import ClassVar
from typing import Self

from ocai.chat.canonical import CANONICAL_CHAT_RESPONSE
from ocai.chat.types.finish import FinishInfo
from ocai.chat.types.message import Message
from ocai.chat.types.parts import PartText
from ocai.chat.types.usage import Usage
from ocai.core.identity import NodeId
from ocai.core.ir import IRObject
from ocai.core.ir import is_json_object
from ocai.core.refs import ProviderRef


@dataclass
class ResponseInfo(IRObject):
    """The provider anchors identifying one response.

    Attributes:
        id: The response's provider-side identity as a `ProviderRef`
            (kind `"response_id"`), reusable as a follow-up anchor; crossing
            another `(provider, interface)` is reported `UNSUPPORTED`.
        model: The provider's echo of the model that actually served the
            call (which may be more specific than the requested alias).
        created: When the provider says the response was created.
    """

    id: ProviderRef | None = None
    model: str | None = None
    created: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `ResponseInfo` from a serialized dict, totally.

        Args:
            data: A mapping with the nested `id`, the optional `model`, an
                ISO-8601 `created`, and the common IR envelope keys.

        Returns:
            The decoded `ResponseInfo`.
        """
        safe = deepcopy(data)
        unparsed: dict[str, Any] = {}
        known = {"id", "model", "created", "version", "extensions", "provider_options"}
        for name in list(safe):
            if name not in known:
                unparsed[name] = safe.pop(name)
        for name in ("extensions", "provider_options"):
            if name in safe and not is_json_object(safe[name]):
                unparsed[name] = safe.pop(name)
        if "version" in safe and not isinstance(safe["version"], str):
            unparsed["version"] = safe.pop("version")
        ref = safe.get("id")
        identity: ProviderRef | None = None
        if ref is not None:
            keys = {"provider", "interface", "kind", "id"}
            optional = {"replay", "scope", "qualifier"}
            if (
                is_json_object(ref)
                and all(isinstance(ref.get(k), str) for k in keys)
                and all(isinstance(ref[k], str) for k in optional if k in ref)
                and ref.get("replay", "optional") in ("optional", "required")
                and not set(ref) - keys - optional
            ):
                identity = ProviderRef.from_dict(ref)
            else:
                unparsed["id"] = ref
        model = safe.get("model")
        if model is not None and not isinstance(model, str):
            unparsed["model"] = model
            model = None
        raw_created = safe.get("created")
        created: datetime | None = None
        if raw_created is not None:
            try:
                if not isinstance(raw_created, str):
                    raise ValueError("expected an ISO timestamp")
                created = datetime.fromisoformat(raw_created)
            except ValueError:
                unparsed["created"] = raw_created
        common = cls._from_dict_common(safe)
        if unparsed:
            extensions = common["extensions"]
            previous = extensions.get("ocai.response_info_unparsed")
            # Preserve even a collision with caller-supplied fallback evidence.
            if previous is not None:
                unparsed["extensions[ocai.response_info_unparsed]"] = previous
            extensions["ocai.response_info_unparsed"] = unparsed
        return cls(id=identity, model=model, created=created, **common)


@dataclass
class ChatResponse(IRObject):
    """A non-streaming chat result — pure payload, no report.

    Produced by the response leg of the conversion graph (provider node →
    `CANONICAL_CHAT_RESPONSE`) or by `StreamAccumulator.fold`, whose output
    must equal it (the fold law). Delivered to callers inside
    `CallResult.value`; the route, report, and untouched provider body ride
    the `CallResult`, keeping this type identical whether it came from a
    live call, a fold, or a fixture.

    Attributes:
        message: The model's reply turn.
        finish: Why generation stopped, when reported.
        usage: What the call consumed, when reported.
        info: The response's provider anchors, when reported.
        raw: The provider's untouched response body for power users — never
            contains credentials. Kept keyword-only and off the positional
            construction path.
    """

    object: ClassVar[str] = "chat.response"
    __node__: ClassVar[NodeId] = CANONICAL_CHAT_RESPONSE

    message: Message
    finish: FinishInfo | None = None
    usage: Usage | None = None
    info: ResponseInfo | None = None
    raw: Any | None = field(default=None, kw_only=True)

    def validated_annotations(self) -> Self:
        """Detach the final response and validate citations against each text part."""
        result = deepcopy(self)
        for part in result.message.parts:
            if isinstance(part, PartText):
                part.annotations = [
                    annotation.validated(part.text) for annotation in part.annotations
                ]
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `ChatResponse` from a serialized dict, totally.

        Args:
            data: A mapping with the nested `message`, `finish`, `usage`,
                `info`, an optional `raw`, and the common IR envelope keys.

        Returns:
            The decoded `ChatResponse`.
        """
        message: dict[str, Any] = data.get("message") or {}
        finish = data.get("finish")
        usage = data.get("usage")
        info = data.get("info")
        return cls(
            message=Message.from_dict(message),
            finish=FinishInfo.from_dict(finish) if is_json_object(finish) else None,
            usage=Usage.from_dict(usage) if is_json_object(usage) else None,
            info=ResponseInfo.from_dict(info) if is_json_object(info) else None,
            raw=data.get("raw"),
            **cls._from_dict_common(data),
        ).validated_annotations()
