"""The canonical `Message`: role + parts, nothing else (architecture §3.1).

Storage is **parts-only** — the old `Content = str | Part | list[Part]`
union is gone. One storage shape means every codec, edge, and accumulator
handles exactly one case; ergonomics live at the boundaries instead:
strings are constructor sugar normalized in `__post_init__`, and
`message.text` is a derived view over the text parts.

`role` is the open string code of `types/role.py`, normalized exactly once
at the codec boundary; a role core has never seen is preserved verbatim.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar
from typing import Self
from typing import overload

from ocai.chat.types.parts import Part
from ocai.chat.types.parts import PartText
from ocai.chat.types.parts import cast_part
from ocai.chat.types.role import Role
from ocai.chat.types.role import decode_role
from ocai.core.ir import IRObject
from ocai.core.ir import is_json_object


@dataclass
class Message(IRObject):
    """A single conversation turn: who spoke, and the parts they produced.

    The unit every codec encodes/decodes and every conversion edge maps.
    The constructor accepts sugar — a bare string (or strings inside the
    list, or a single `Part`) — and `__post_init__` normalizes everything
    to `list[Part]`, so downstream machinery only ever sees one shape.

    Attributes:
        role: The author's open role code; canonical constants on `Role`.
        parts: The ordered content parts making up the turn.
    """

    object: ClassVar[str] = "message"

    role: str
    parts: list[Part]

    if TYPE_CHECKING:
        # The constructor's typed face: the dataclass-generated `__init__` is
        # untouched at runtime; these declarations only admit the documented
        # sugar that `__post_init__` normalizes, so `Message(role, "hi")`
        # type-checks while the stored field stays `list[Part]`. The generic
        # overload admits any list of one part type (`list[PartToolResult]`,
        # which list invariance would otherwise reject); the second admits
        # the bare string/part forms and mixed literals.
        @overload
        def __init__[T: Part | str](
            self,
            role: str,
            parts: list[T],
            *,
            version: str = ...,
            provider_options: dict[str, Any] = ...,
            extensions: dict[str, Any] = ...,
        ) -> None: ...

        @overload
        def __init__(
            self,
            role: str,
            parts: str | Part | list[Part | str],
            *,
            version: str = ...,
            provider_options: dict[str, Any] = ...,
            extensions: dict[str, Any] = ...,
        ) -> None: ...

        def __init__(
            self,
            role: str,
            parts: Any,
            *,
            version: str = ...,
            provider_options: dict[str, Any] = ...,
            extensions: dict[str, Any] = ...,
        ) -> None: ...

    def __post_init__(self) -> None:
        """Normalize constructor sugar into the parts-only storage shape.

        A bare string becomes `[PartText(str)]`; a single `Part` is wrapped
        in a list; string items inside a list each become a `PartText`.
        After this, `parts` is always `list[Part]` — the one invariant the
        rest of the library relies on.
        """
        raw = self.parts
        if isinstance(raw, str):
            self.parts = [PartText(text=raw)]
            return
        if not isinstance(raw, list):  # pyright: ignore[reportUnnecessaryIsInstance] -- constructor sugar: a single `Part` reaches here untyped
            self.parts = [raw]
            return
        self.parts = [PartText(text=item) if isinstance(item, str) else item for item in raw]

    @classmethod
    def user(cls, parts: str | Part | list[Part | str]) -> Self:
        """Build a user-authored message.

        Args:
            parts: The content, with the same sugar the constructor accepts.

        Returns:
            A `Message` with `role == Role.USER`.
        """
        return cls(role=Role.USER, parts=parts)

    @classmethod
    def model(cls, parts: str | Part | list[Part | str]) -> Self:
        """Build a model-authored message.

        Args:
            parts: The content, with the same sugar the constructor accepts.

        Returns:
            A `Message` with `role == Role.MODEL`.
        """
        return cls(role=Role.MODEL, parts=parts)

    @classmethod
    def system(cls, parts: str | Part | list[Part | str]) -> Self:
        """Build a system-instruction message.

        Codecs relocate it per dialect (e.g. Gemini `systemInstruction`),
        recording the move as a `SemanticShift`, never silently.

        Args:
            parts: The content, with the same sugar the constructor accepts.

        Returns:
            A `Message` with `role == Role.SYSTEM`.
        """
        return cls(role=Role.SYSTEM, parts=parts)

    @classmethod
    def tool(cls, parts: str | Part | list[Part | str]) -> Self:
        """Build a tool-result message.

        Typically carries `PartToolResult` parts correlated to earlier
        `PartToolCall`s by `call_id`.

        Args:
            parts: The content, with the same sugar the constructor accepts.

        Returns:
            A `Message` with `role == Role.TOOL`.
        """
        return cls(role=Role.TOOL, parts=parts)

    @property
    def text(self) -> str:
        """Return the concatenated text of every `PartText`, in order.

        A derived view, never storage — the parts stay authoritative, so
        annotations and non-text parts are never flattened away by reading
        it.
        """
        return "".join(part.text for part in self.parts if isinstance(part, PartText))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `Message` from a serialized dict, totally.

        The role is normalized via `decode_role` (unknown roles preserved
        verbatim); parts decode through `PART_REGISTRY` (unknown tags fall
        back to `PartUnknown`); bare strings in the parts list ride the same
        sugar the constructor accepts.

        Args:
            data: A mapping with `role`, `parts`, and the common IR envelope
                keys.

        Returns:
            The decoded `Message`.
        """
        parts: list[Part] = []
        raw_parts: list[Any] = data.get("parts") or []
        for item in raw_parts:
            if isinstance(item, str):
                parts.append(PartText(text=item))
            elif is_json_object(item):
                parts.append(cast_part(item))
        return cls(
            role=decode_role(data.get("role")),
            parts=parts,
            **cls._from_dict_common(data),
        )
