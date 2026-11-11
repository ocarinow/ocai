"""Declarative host configuration for catalog fragments; no wire imports or I/O."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from urllib.parse import urlsplit

from ocai.core._headers import merge_headers


@dataclass(frozen=True)
class HostDescriptor:
    """Pure host data, explicitly selected by a caller rather than auto-routed.

    Attributes:
        base_url: Explicit HTTP(S) origin, optionally including a base path.
        paths: Unary operation-kind path templates; only `{resource}` is supported.
        path_prefix: Path prepended to the selected native or remapped path.
        streaming_paths: Stream-specific templates, falling back to `paths`.
        static_headers: Non-secret host headers, overriding dialect defaults.
        query: Explicit query values, independent of path and version headers.
        profile_aliases: Exact resource-to-profile-key aliases; wire names stay intact.
        profile_suffixes: Explicit suffixes to remove once for profile lookup only.
    """

    base_url: str
    paths: Mapping[str, str] = field(default_factory=dict[str, str])
    path_prefix: str = ""
    streaming_paths: Mapping[str, str] = field(default_factory=dict[str, str])
    static_headers: Mapping[str, str] = field(default_factory=dict[str, str])
    query: Mapping[str, str] = field(default_factory=dict[str, str])
    profile_aliases: Mapping[str, str] = field(default_factory=dict[str, str])
    profile_suffixes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Detach caller-owned maps and canonicalize unordered suffix declarations."""
        for name in ("paths", "streaming_paths", "static_headers", "query", "profile_aliases"):
            object.__setattr__(self, name, dict(getattr(self, name)))
        merge_headers(self.static_headers)
        base = urlsplit(self.base_url)
        if (
            base.scheme not in {"http", "https"}
            or not base.netloc
            or base.username is not None
            or base.password is not None
            or base.query
            or base.fragment
            or any(c in self.base_url for c in "\r\n")
        ):
            raise ValueError("host base_url requires HTTP(S), without credentials/query/fragment")
        if any(
            key.casefold().replace("_", "-")
            in {
                "api-key",
                "access-token",
                "token",
                "authorization",
                "key",
                "signature",
            }
            for key in self.query
        ):
            raise ValueError("credentials do not belong in host query configuration")
        if any(not alias for alias in self.profile_aliases.values()):
            raise ValueError("profile aliases must be nonempty")
        if any(not suffix for suffix in self.profile_suffixes):
            raise ValueError("profile suffixes must be nonempty")
        object.__setattr__(self, "profile_suffixes", tuple(sorted(set(self.profile_suffixes))))
