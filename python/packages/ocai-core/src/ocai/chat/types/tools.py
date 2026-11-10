"""Tool definitions and tool-choice policy for chat requests (§3.1).

`Tool` is the canonical description of a callable a model may invoke — pure,
serializable data; the IR keeps only the derived `JsonSchema`, never a
callable. Three ingestion boundaries feed it:

- `Tool.from_function` — introspects a Python callable's signature, type
  hints, and docstring.
- `Tool.from_schema` — duck-types anything schema-shaped: a plain dict, a
  dataclass type, or any object exposing `model_json_schema()` (the
  pydantic bridge — served without pydantic ever becoming a dependency,
  per rule 11).
- `Tool.from_dict` — the ordinary IR decode path.

`ToolChoice` is the request-level policy for *whether/which* tool the model
must call, with an open `mode` code (`auto | none | required | named`).
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from copy import deepcopy
from dataclasses import MISSING as _DC_MISSING
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields as _dc_fields
from dataclasses import is_dataclass
from enum import Enum
from types import UnionType
from typing import Annotated
from typing import Any
from typing import ClassVar
from typing import Final
from typing import Literal
from typing import Self
from typing import Union
from typing import get_args
from typing import get_origin
from typing import get_type_hints

from ocai.core.ir import IRObject
from ocai.core.ir import is_json_object
from ocai.core.jsonschema import JsonSchema
from ocai.core.jsonschema import Schema

type AnyFunction = Callable[..., Any]

# Exact Python type -> JSON Schema primitive name. Keyed by identity so ``bool``
# and ``int`` stay distinct (``bool`` is a subclass of ``int``).
_PRIMITIVES: dict[type, str] = {
    str: "string",
    bool: "boolean",
    int: "integer",
    float: "number",
    type(None): "null",
}


def _schema_for_annotation(tp: Any) -> JsonSchema:
    """Best-effort map a Python type annotation to a `JsonSchema`.

    Covers the common cases (primitives, containers, `Optional`/unions,
    `Literal`, `Enum`, `Annotated` descriptions, and nested dataclasses). An
    unknown or missing annotation degrades to an empty schema (`{}` = anything)
    rather than raising -- callers should never lose a parameter to a type we
    cannot model.

    TODO: docstring-derived per-parameter descriptions and recursive dataclasses
    (a self-referential model would currently recurse without bound).
    """
    # Annotated[T, ...]: unwrap to T, lift the first str metadata into description.
    if get_origin(tp) is Annotated:
        args = get_args(tp)
        schema = _schema_for_annotation(args[0])
        doc = next((m for m in args[1:] if isinstance(m, str)), None)
        if doc is not None and schema.description is None:
            schema.description = doc
        return schema

    # No annotation / Any -> permissive empty schema.
    if tp is Any or tp is inspect.Parameter.empty:
        return JsonSchema()

    if isinstance(tp, type) and tp in _PRIMITIVES:
        return JsonSchema(type=_PRIMITIVES[tp])

    if isinstance(tp, type) and issubclass(tp, Enum):
        return JsonSchema(enum=[m.value for m in tp.__members__.values()])

    origin = get_origin(tp)
    args = get_args(tp)

    # Literal["a", "b"] -> enum; a single literal -> const.
    if origin is Literal:
        values = list(args)
        return JsonSchema(const=values[0]) if len(values) == 1 else JsonSchema(enum=values)

    # Optional[X] / X | Y -> anyOf (null contributes a {"type": "null"} branch).
    if origin is Union or origin is UnionType:
        non_none = [a for a in args if a is not type(None)]
        nullable = len(non_none) != len(args)
        subs = [_schema_for_annotation(a) for a in non_none]
        if nullable:
            subs.append(JsonSchema(type="null"))
        if len(subs) == 1:
            return subs[0]
        return JsonSchema(any_of=list(subs))

    # Sequences -> array.
    if origin in (list, set, frozenset) or tp in (list, set, frozenset):
        if args:
            return JsonSchema(type="array", items=_schema_for_annotation(args[0]))
        return JsonSchema(type="array")

    # Tuples -> homogeneous array (``tuple[X, ...]``) or positional ``prefixItems``.
    if origin is tuple or tp is tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            return JsonSchema(type="array", items=_schema_for_annotation(args[0]))
        if args:
            return JsonSchema(type="array", prefix_items=[_schema_for_annotation(a) for a in args])
        return JsonSchema(type="array")

    # Mappings -> object with a value schema in additionalProperties.
    if origin is dict or tp is dict:
        if len(args) == 2:
            return JsonSchema(type="object", additional_properties=_schema_for_annotation(args[1]))
        return JsonSchema(type="object")

    # Nested dataclass -> object schema built from its fields.
    if isinstance(tp, type) and is_dataclass(tp):
        try:
            hints = get_type_hints(tp, include_extras=True)
        except Exception:
            hints = {}
        props: dict[str, Schema] = {}
        required: list[str] = []
        for f in _dc_fields(tp):
            props[f.name] = _schema_for_annotation(hints.get(f.name, f.type))
            if f.default is _DC_MISSING and f.default_factory is _DC_MISSING:
                required.append(f.name)
        schema = JsonSchema(type="object", properties=props)
        if required:
            schema.required = required
        return schema

    # Unknown construct: stay lossless-friendly with a permissive schema.
    return JsonSchema()


@dataclass
class Tool(IRObject):
    """A model-invocable tool described as pure, serializable data.

    Captures a tool's name, its input parameter schema, an optional human
    description, and an optional output schema. No underlying callable is
    retained, so a `Tool` stays serializable across the IR and identical in
    every language port.

    Attributes:
        name: The tool's name, as exposed to the model.
        parameters: JSON Schema describing the tool's input parameters.
        description: Human-readable description of the tool, if any.
        output: JSON Schema describing the tool's output, if known.
    """

    object: ClassVar[str] = "tool"

    name: str
    parameters: JsonSchema
    description: str | None = None
    output: JsonSchema | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Rebuild a `Tool` from its serialized mapping, totally.

        The `parameters` schema is decoded via `JsonSchema.from_dict`;
        `output` the same way when present.

        Args:
            data: The serialized mapping to rebuild from.

        Returns:
            The reconstructed `Tool`.
        """
        parameters: dict[str, Any] = data.get("parameters") or {}
        output = data.get("output")
        return cls(
            name=data.get("name", ""),
            parameters=JsonSchema.from_dict(parameters),
            description=data.get("description"),
            output=JsonSchema.from_dict(output) if is_json_object(output) else None,
            **cls._from_dict_common(data),
        )

    @classmethod
    def from_function(cls, fn: AnyFunction) -> Self:
        """Build a `Tool` by introspecting a Python callable.

        Ingestion-boundary sugar: the function's signature + type hints become the
        tool's `parameters` JSON Schema and its docstring becomes `description`.
        The callable itself is *not* retained -- only the derived schema enters the
        IR, so a `Tool` stays pure, serializable data.
        """
        try:
            hints = get_type_hints(fn, include_extras=True)
        except Exception:
            hints = {}

        properties: dict[str, Schema] = {}
        required: list[str] = []
        for pname, param in inspect.signature(fn).parameters.items():
            # *args / **kwargs have no faithful JSON Schema form; bound receivers
            # are not model-facing parameters.
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
            if pname in ("self", "cls"):
                continue
            schema = _schema_for_annotation(hints.get(pname, param.annotation))
            if param.default is inspect.Parameter.empty:
                required.append(pname)
            else:
                schema.default = param.default
            properties[pname] = schema

        parameters = JsonSchema(type="object", properties=properties)
        if required:
            parameters.required = required

        return cls(
            name=fn.__name__,
            parameters=parameters,
            description=inspect.getdoc(fn),
        )

    @classmethod
    def from_schema(
        cls,
        obj: Any,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Self:
        """Build a `Tool` from anything schema-shaped, by duck typing.

        The pydantic bridge (rule 11): pydantic users hand their model class
        straight in and its `model_json_schema()` is consumed — without
        pydantic ever appearing in ocai's dependencies. Accepted shapes, in
        dispatch order:

        1. An object exposing `model_json_schema()` (pydantic v2 models and
           anything imitating them) — called, and the resulting dict used as
           the parameters schema.
        2. A dataclass *type* — its fields become an object schema via the
           same annotation mapping `from_function` uses.
        3. A plain dict — treated as an already-built JSON Schema for the
           parameters and decoded via `JsonSchema.from_dict` (unknown
           keywords ride `JsonSchema.extra`, lossless).

        Args:
            obj: The schema donor — a dict, a dataclass type, or anything
                exposing `model_json_schema()`.
            name: The tool name; when omitted it is derived from the
                schema's `title`, the donor's `__name__`, or left empty.
            description: The tool description; when omitted it is derived
                from the schema's `description` or the donor's docstring.

        Returns:
            The constructed `Tool`.

        Raises:
            TypeError: If `obj` matches none of the accepted shapes.
        """
        schema_getter: Callable[[], dict[str, Any]] | None = getattr(
            obj, "model_json_schema", None
        )
        if callable(schema_getter):
            raw = schema_getter()
            parameters = JsonSchema.from_dict(raw)
            title: str | None = raw.get("title")
            fallback: str = getattr(obj, "__name__", "")
            return cls(
                name=name or title or fallback,
                parameters=parameters,
                description=description or raw.get("description") or inspect.getdoc(obj),
            )

        if inspect.isclass(obj) and is_dataclass(obj):
            return cls(
                name=name or obj.__name__,
                parameters=_schema_for_annotation(obj),
                description=description or inspect.getdoc(obj),
            )

        if is_json_object(obj):
            return cls(
                name=name or obj.get("title", ""),
                parameters=JsonSchema.from_dict(obj),
                description=description or obj.get("description"),
            )

        raise TypeError(
            f"Tool.from_schema expects a dict, a dataclass type, or an object "
            f"exposing model_json_schema(); got {type(obj).__name__}"
        )


@dataclass
class ServerToolLocation(IRObject):
    """Approximate search location; not a device location or execution authority.

    Attributes:
        country: Country code supplied by the caller.
        region: Region supplied by the caller.
        city: City supplied by the caller.
        timezone: Time zone supplied by the caller.
    """

    country: str | None = None
    region: str | None = None
    city: str | None = None
    timezone: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Decode location data without interpreting or normalizing its values."""
        return cls(
            country=data.get("country"), region=data.get("region"),
            city=data.get("city"), timezone=data.get("timezone"),
            **cls._from_dict_common(data),
        )


@dataclass
class ServerTool(IRObject):
    """Provider-executed tool intent, separate from a callable function definition.

    Attributes:
        kind: Open intent code, for example `web_search`.
        allowed_domains: Explicit domain allowlist; never normalized implicitly.
        blocked_domains: Explicit domain blocklist; conflicts are provider-qualified.
        user_location: Approximate caller-supplied search location.
        type: Fixed discriminator; legacy function tools remain untagged.
    """

    kind: str
    allowed_domains: list[str] | None = None
    blocked_domains: list[str] | None = None
    user_location: ServerToolLocation | None = None
    type: str = field(default="server", init=False)

    def to_dict(self) -> dict[str, Any]:
        """Serialize intent, preserving explicitly empty domain lists."""
        data = super().to_dict()
        if self.allowed_domains is not None:
            data["allowed_domains"] = deepcopy(self.allowed_domains)
        if self.blocked_domains is not None:
            data["blocked_domains"] = deepcopy(self.blocked_domains)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Decode server intent and retain unparsed location evidence."""
        location = data.get("user_location")
        result = cls(
            kind=data.get("kind", ""),
            allowed_domains=deepcopy(data.get("allowed_domains")),
            blocked_domains=deepcopy(data.get("blocked_domains")),
            user_location=(ServerToolLocation.from_dict(location)
                           if is_json_object(location) else None),
            **cls._from_dict_common(data),
        )
        if location is not None and not is_json_object(location):
            result.extensions["ocai.server_tool_unparsed_location"] = deepcopy(location)
        return result


@dataclass
class ToolUnknown:
    """A future or malformed tool entry preserved verbatim, with no execution meaning.

    Attributes:
        data: The original JSON value, retained without interpreting its tag.
    """

    data: Any

    def to_dict(self) -> Any:
        """Return detached original data, including unknown non-object entries."""
        return deepcopy(self.data)

    @classmethod
    def from_dict(cls, data: Any) -> Self:
        """Preserve the unknown tool payload without imposing this revision's schema."""
        return cls(deepcopy(data))


type ToolDefinition = Tool | ServerTool | ToolUnknown


def decode_tool(data: Any) -> ToolDefinition:
    """Decode the open tool union; untagged mappings retain legacy function semantics."""
    if not is_json_object(data):
        return ToolUnknown.from_dict(data)
    try:
        if "type" not in data:
            return Tool.from_dict(data)
        if data.get("type") == "server":
            return ServerTool.from_dict(data)
    except (TypeError, ValueError, AttributeError):
        # Malformed known shapes retain their whole payload. G-09 tracks the
        # shared envelope reader; union decode must not lose the input meanwhile.
        return ToolUnknown.from_dict(data)
    return ToolUnknown.from_dict(data)


class ToolChoiceMode:
    """Canonical constants for the open `ToolChoice.mode` code.

    Attributes:
        AUTO: The model decides whether to call a tool (the default).
        NONE: The model must not call any tool.
        REQUIRED: The model must call at least one tool.
        NAMED: The model must call the tool named by `ToolChoice.name`.
    """

    AUTO: Final = "auto"
    NONE: Final = "none"
    REQUIRED: Final = "required"
    NAMED: Final = "named"


@dataclass
class ToolChoice(IRObject):
    """Request-level policy for whether/which tool the model must call.

    Rides `ChatRequest.tool_choice`; codecs map the open `mode` onto each
    dialect's idiom (OpenAI `tool_choice`, Anthropic `tool_choice`, Gemini
    `functionCallingConfig`).

    Attributes:
        mode: The open choice code; canonical constants on `ToolChoiceMode`
            (`auto | none | required | named`).
        name: The tool the model must call when `mode` is `named`.
    """

    mode: str = ToolChoiceMode.AUTO
    name: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `ToolChoice` from a serialized dict, totally.

        Args:
            data: A mapping with `mode`, an optional `name`, and the common
                IR envelope keys.

        Returns:
            The decoded `ToolChoice`.
        """
        return cls(
            mode=data.get("mode", ToolChoiceMode.AUTO),
            name=data.get("name"),
            **cls._from_dict_common(data),
        )
