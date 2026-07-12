"""Tagged primitive values for the canonical IR.

This module models JSON-shaped scalar and container values in a self-describing
way: a `Value` pairs a piece of data with a `ValueType` tag, and can validate
that the data actually matches its declared type. The `Primitive` type alias
enumerates the Python types these values may hold.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Self


class ValueType(str, Enum):
    """Enumeration of the JSON value categories a `Value` can carry.

    Members mirror the JSON type system; each maps to a concrete Python type
    via the module-level `_VALUE_TYPE_MAPPER`.

    Attributes:
        NULL: The JSON null value (`None` in Python).
        NUMBER: A floating-point number.
        INTEGER: An integer.
        STRING: A text string.
        BOOLEAN: A boolean.
        OBJECT: A JSON object (a `dict`).
        ARRAY: A JSON array (a `list`).
    """

    NULL = "NULL"
    NUMBER = "NUMBER"
    INTEGER = "INTEGER"
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    OBJECT = "OBJECT"
    ARRAY = "ARRAY"


_VALUE_TYPE_MAPPER: dict[ValueType, type] = {
    ValueType.NULL: type(None),
    ValueType.NUMBER: float,
    ValueType.INTEGER: int,
    ValueType.STRING: str,
    ValueType.BOOLEAN: bool,
    ValueType.ARRAY: list,
    ValueType.OBJECT: dict,
}

type Primitive = int | float | bool | str | dict[str, Any] | list[Any] | None


@dataclass
class Value[T: Primitive = Primitive]:
    """A primitive value paired with its declared `ValueType` tag.

    The generic parameter `T` records the Python type of the carried value; it
    defaults to the full `Primitive` union.

    Attributes:
        type: The declared `ValueType` describing the value's category.
        value: The carried primitive data.
    """

    type: ValueType
    value: T

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict with the tag's string value.

        Returns:
            A dict with `type` (the enum's string value) and the raw `value`.
        """
        return {
            "type": self.type.value,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a `Value` from a serialized dict.

        Args:
            data: A mapping with `type` (a `ValueType` string) and `value`.

        Returns:
            A new `Value` with the parsed type tag and carried value.
        """
        return cls(
            type=ValueType(data["type"]),
            value=data["value"],
        )

    def is_valid(self, *, error: bool = False) -> bool:
        """Check that the carried value matches its declared `type`.

        Args:
            error: If true, raise instead of returning False on a mismatch.

        Returns:
            True if `value` is an instance of the Python type mapped from
            `type`, otherwise False.

        Raises:
            TypeError: If the value does not match its declared type and
                `error` is true.
        """
        if isinstance(self.value, _VALUE_TYPE_MAPPER[self.type]):
            return True

        if error:
            raise TypeError(f"Value `{self.value}` is not of type <{self.type}>")

        return False
