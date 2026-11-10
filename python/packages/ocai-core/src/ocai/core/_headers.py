"""Pure composition of non-secret headers before credential application."""

from collections.abc import Mapping

# These conventional credential carriers must never enter hook-visible static data.
_AUTH_HEADERS = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "api-key",
        "x-api-key",
        "cookie",
        "set-cookie",
        "x-amz-security-token",
        "cf-aig-authorization",
    }
)


def merge_headers(*groups: Mapping[str, str]) -> dict[str, str]:
    """Merge non-secret groups in precedence order, without case-alias duplicates.

    Args:
        groups: Lowest to highest precedence header maps.

    Returns:
        Detached headers, retaining the winning declaration's spelling.

    Raises:
        ValueError: A group is ambiguous or contains a known credential carrier.
    """
    result: dict[str, tuple[str, str]] = {}
    for group in groups:
        normalized: dict[str, tuple[str, str]] = {}
        for name, value in group.items():
            key = name.casefold()
            if key in _AUTH_HEADERS:
                raise ValueError("static authentication headers require an explicit Credential")
            if not name or any(c in name + value for c in "\r\n"):
                raise ValueError("invalid static header")
            if key in normalized and normalized[key][1] != value:
                raise ValueError("conflicting case aliases in a static header group")
            normalized[key] = (name, value)
        result.update(normalized)
    return dict(result.values())
