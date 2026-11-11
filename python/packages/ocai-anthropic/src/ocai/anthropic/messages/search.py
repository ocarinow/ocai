"""Qualified basic web-search mapping; provider semantics stay inside the plugin."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ocai.chat.types import Annotation
from ocai.chat.types import PartServerToolCall
from ocai.chat.types import PartServerToolResult
from ocai.chat.types import ServerTool
from ocai.chat.types import ServerToolLocation
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import FieldLoss
from ocai.core.ir import is_json_array
from ocai.core.ir import is_json_object
from ocai.core.refs import ProviderRef
from ocai.core.refs import Replay

VERSION = "web_search_20250305"
OPTIONS = "anthropic.messages"
CONTROL = "anthropic.web_search"
CITATION = "anthropic.web_search_citation"


def _loss(path: str, note: str) -> FieldLoss:
    return FieldLoss(path, Disposition.UNSUPPORTED, 2.0, note)


def _ref(kind: str, identifier: str) -> ProviderRef:
    return ProviderRef("anthropic", "messages", kind, identifier, Replay.REQUIRED)


def _valid_ref(ref: ProviderRef | None, kind: str, identifier: str | None = None) -> bool:
    native_id: Any = ref.id if ref is not None else None
    return bool(
        ref is not None
        and ref.provider == "anthropic"
        and ref.interface == "messages"
        and ref.scope != "model"
        and ref.kind == kind
        and isinstance(native_id, str)
        and ref.id
        and (identifier is None or ref.id == identifier)
    )


def encode_tool(tool: ServerTool, path: str, losses: list[FieldLoss]) -> dict[str, Any] | None:
    """Map only the qualified basic direct-search intent, reporting all exclusions."""
    own = tool.provider_options.get(OPTIONS, {})
    control = tool.extensions.get(CONTROL, {})
    if (
        tool.kind != "web_search"
        or not is_json_object(own)
        or not is_json_object(control)
        or own.get("type") != VERSION
        or any(key not in {"type", "allowed_callers"} for key in own)
        or own.get("allowed_callers", ["direct"]) != ["direct"]
    ):
        losses.append(
            _loss(path, "server or unknown tool intent has no qualified mapping on this interface")
        )
        return None
    payload: dict[str, Any] = {"type": VERSION, "name": "web_search"}
    if "allowed_callers" in own:
        payload["allowed_callers"] = ["direct"]
    if tool.allowed_domains is not None:
        payload["allowed_domains"] = deepcopy(tool.allowed_domains)
    if tool.blocked_domains is not None:
        payload["blocked_domains"] = deepcopy(tool.blocked_domains)
    if tool.allowed_domains is not None and tool.blocked_domains is not None:
        losses.append(
            _loss(path, "Anthropic requires allowed_domains or blocked_domains, not both")
        )
    if tool.user_location is not None:
        location = tool.user_location
        payload["user_location"] = {
            "type": "approximate",
            **{
                key: value
                for key, value in (
                    ("country", location.country),
                    ("region", location.region),
                    ("city", location.city),
                    ("timezone", location.timezone),
                )
                if value is not None
            },
        }
        if location.extensions or location.provider_options:
            losses.append(
                _loss(path + ".user_location", "unqualified location metadata is not forwarded")
            )
        if len(payload["user_location"]) == 1:
            losses.append(
                _loss(path + ".user_location", "Anthropic requires at least one location field")
            )
    if "max_uses" in control:
        payload["max_uses"] = deepcopy(control["max_uses"])
        value = control["max_uses"]
        if type(value) is not int or value < 1:
            losses.append(
                FieldLoss(
                    path + ".extensions",
                    Disposition.APPROXIMATED,
                    note="max_uses outside the positive integer range passes verbatim",
                )
            )
    losses.extend(
        _loss(path + ".extensions", "unqualified search controls remain in canonical evidence")
        for key in control
        if key != "max_uses"
    )
    losses.extend(
        _loss(path + ".extensions", "unqualified search metadata is not forwarded")
        for key in tool.extensions
        if key != CONTROL
    )
    return payload


def decode_tool(raw: dict[str, Any], path: str, losses: list[FieldLoss]) -> ServerTool | None:
    """Decode the selected tool version; retain other versions in the caller's fallback."""
    if raw.get("type") != VERSION or raw.get("name") != "web_search":
        return None
    location = raw.get("user_location")
    if location is not None and (
        not is_json_object(location) or location.get("type") != "approximate"
    ):
        return None
    known = {
        "type",
        "name",
        "allowed_domains",
        "blocked_domains",
        "user_location",
        "max_uses",
        "allowed_callers",
    }
    extras = {key: deepcopy(value) for key, value in raw.items() if key not in known}
    extensions: dict[str, Any] = {}
    if "max_uses" in raw:
        extensions[CONTROL] = {"max_uses": deepcopy(raw["max_uses"])}
        losses.append(
            FieldLoss(
                path + ".max_uses",
                Disposition.EXTENSIONS,
                note="max_uses retained in registered search controls",
            )
        )
    if is_json_object(location):
        location_extras = {
            key: deepcopy(value)
            for key, value in location.items()
            if key not in {"type", "country", "region", "city", "timezone"}
        }
        if location_extras:
            extras["user_location"] = location_extras
    if extras:
        extensions["anthropic.web_search_unmapped"] = extras
        losses.append(
            FieldLoss(
                path, Disposition.EXTENSIONS, note="unknown search controls preserved in extensions"
            )
        )
    own: dict[str, Any] = {"type": VERSION}
    if "allowed_callers" in raw:
        own["allowed_callers"] = deepcopy(raw["allowed_callers"])
    return ServerTool(
        "web_search",
        allowed_domains=deepcopy(raw.get("allowed_domains")),
        blocked_domains=deepcopy(raw.get("blocked_domains")),
        user_location=(
            ServerToolLocation(
                country=location.get("country"),
                region=location.get("region"),
                city=location.get("city"),
                timezone=location.get("timezone"),
            )
            if is_json_object(location)
            else None
        ),
        extensions=extensions,
        provider_options={OPTIONS: own},
    )


def decode_call(raw: dict[str, Any]) -> PartServerToolCall:
    """Preserve a native search-call block with a scoped replay identity."""
    identity = raw.get("id", "")
    return PartServerToolCall(
        kind="web_search",
        call_id=identity,
        status="output_available",
        payload=deepcopy(raw),
        anchor=_ref("web_search_call", identity),
    )


def decode_result(raw: dict[str, Any]) -> PartServerToolResult:
    """Keep all native results, including encrypted bytes, under one scoped anchor."""
    content = raw.get("content")
    failed = is_json_object(content) and content.get("type") == "web_search_tool_result_error"
    identity = raw.get("tool_use_id", "")
    return PartServerToolResult(
        kind="web_search",
        call_id=identity,
        status="output_error" if failed else "output_available",
        payload=deepcopy(raw),
        anchor=_ref("web_search_result", identity),
    )


def encode_part(
    part: PartServerToolCall | PartServerToolResult, path: str, losses: list[FieldLoss]
) -> dict[str, Any] | None:
    """Replay a complete native search block only with matching scoped evidence."""
    call = isinstance(part, PartServerToolCall)
    kind = "web_search_call" if call else "web_search_result"
    raw = part.payload
    identity_key = "id" if call else "tool_use_id"
    wire_type = "server_tool_use" if call else "web_search_tool_result"
    if (
        part.kind != "web_search"
        or not _valid_ref(part.anchor, kind, part.call_id)
        or raw.get("type") != wire_type
        or raw.get(identity_key) != part.call_id
    ):
        losses.append(_loss(path, "search replay requires a matching same-interface block anchor"))
        return None
    if call:
        if raw.get("name") != "web_search" or not is_json_object(raw.get("input")):
            losses.append(_loss(path, "search call replay requires the original input object"))
            return None
    else:
        content = raw.get("content")
        if is_json_array(content):
            for result in content:
                if (
                    not is_json_object(result)
                    or result.get("type") != "web_search_result"
                    or not isinstance(result.get("encrypted_content"), str)
                    or not result.get("encrypted_content")
                ):
                    losses.append(
                        _loss(
                            path, "search result replay requires every original encrypted_content"
                        )
                    )
                    return None
        elif not (
            is_json_object(content) and content.get("type") == "web_search_tool_result_error"
        ):
            losses.append(_loss(path, "unqualified search result payload cannot be replayed"))
            return None
    if part.extensions or part.provider_options.get(OPTIONS):
        losses.append(
            _loss(path + ".extensions", "unqualified server-part metadata is not forwarded")
        )
    caller = raw.get("caller")
    if caller is not None and caller != {"type": "direct"}:
        losses.append(
            _loss(path, "programmatic search replay is outside the qualified direct surface")
        )
        return None
    return deepcopy(raw)


def decode_citation(raw: Any, path: str, losses: list[FieldLoss]) -> Annotation:
    """Map a whole-block web citation; future forms retain their complete native record."""
    if (
        not is_json_object(raw)
        or raw.get("type") != "web_search_result_location"
        or not isinstance(raw.get("encrypted_index"), str)
        or not raw.get("encrypted_index")
    ):
        losses.append(
            FieldLoss(
                path,
                Disposition.EXTENSIONS,
                note="unqualified citation preserved as native evidence",
            )
        )
        return Annotation(extensions={CITATION: deepcopy(raw)})
    extras = {
        k: deepcopy(v)
        for k, v in raw.items()
        if k not in {"type", "url", "title", "cited_text", "encrypted_index"}
    }
    if extras:
        losses.append(
            FieldLoss(
                path,
                Disposition.EXTENSIONS,
                note="unknown citation fields preserved as native evidence",
            )
        )
    return Annotation(
        kind="url_citation",
        url=raw.get("url"),
        title=raw.get("title"),
        cited_text=raw.get("cited_text"),
        opaque=_ref("web_search_citation", raw["encrypted_index"]),
        extensions={CITATION: extras} if extras else {},
    )


def encode_citation(
    annotation: Annotation, path: str, losses: list[FieldLoss]
) -> dict[str, Any] | None:
    """Replay a qualified whole-block citation using its original encrypted index."""
    if (
        annotation.kind != "url_citation"
        or annotation.span is not None
        or not _valid_ref(annotation.opaque, "web_search_citation")
    ):
        losses.append(
            _loss(
                path + ".opaque" if annotation.opaque is not None else path,
                "search citation replay requires a whole-block same-interface opaque anchor",
            )
        )
        return None
    assert annotation.opaque is not None
    raw: dict[str, Any] = {
        "type": "web_search_result_location",
        "encrypted_index": annotation.opaque.id,
    }
    raw.update(
        {
            key: value
            for key, value in (
                ("url", annotation.url),
                ("title", annotation.title),
                ("cited_text", annotation.cited_text),
            )
            if value is not None
        }
    )
    extras = annotation.extensions.get(CITATION)
    if is_json_object(extras):
        for key, value in extras.items():
            if key not in raw:
                raw[key] = deepcopy(value)
            elif raw[key] != value:
                losses.append(_loss(path, "conflicting native citation metadata is not replayed"))
    elif CITATION in annotation.extensions:
        losses.append(_loss(path, "unqualified native citation metadata is not replayed"))
    losses.extend(
        _loss(path, "unqualified citation metadata is not replayed")
        for key in annotation.extensions
        if key != CITATION
    )
    if (
        annotation.file
        or annotation.document_index is not None
        or annotation.source_result is not None
    ):
        losses.append(
            _loss(path, "additional canonical citation references have no search replay lane")
        )
    return raw
