"""[PROVISIONAL] The `QueryFilter` type alias.

A `QueryFilter` is the metadata-filter shape vector store operations accept
— always under the one parameter name `filters` (the old `where`-vs-
`filters` split is dead). It is currently a free-form `dict[str, Any]`; a
narrower canonical filter schema may replace it before this package
freezes.
"""

from __future__ import annotations

from typing import Any

type QueryFilter = dict[str, Any]
