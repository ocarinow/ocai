"""Message roles: who authored a message (architecture §3.1).

`Role` is an **open string code**, not a closed enum: the canonical constants
(`user | model | system | tool`) cover every first-party interface today, but
an unknown wire role is *preserved verbatim* rather than coerced to a sentinel
— total decode (rule 6) applies to roles like everything else.

Normalization happens **exactly once**, at the codec boundary, through the
two named helpers:

- `decode_role` — wire value → canonical code (case-normalizing known values,
  preserving unknown ones verbatim).
- `encode_role` — canonical code → wire value (identity; the single named
  hook a codec overrides per dialect, e.g. canonical `model` → OpenAI
  `assistant`).

The old `serialize_role`/`deserialize_role` pair (whose names inverted their
meaning) is gone.
"""

from __future__ import annotations

from typing import Final


class Role:
    """Canonical constants for the open message-role code.

    `Message.role` is a plain `str`; these constants name the values core
    itself understands. Codecs map provider wire roles onto them (OpenAI
    `assistant` → `MODEL`) and preserve anything unmapped verbatim, so a
    role this revision has never seen survives a round trip untouched.

    Attributes:
        USER: The end user speaking to the model.
        MODEL: The model / assistant. Canonical name is `model`, not
            `assistant` — codecs translate.
        SYSTEM: System-level instructions.
        TOOL: A tool returning a result into the conversation.
    """

    USER: Final = "user"
    MODEL: Final = "model"
    SYSTEM: Final = "system"
    TOOL: Final = "tool"


# The roles core recognizes for case-normalization in `decode_role`.
_CANONICAL_ROLES: Final = frozenset({Role.USER, Role.MODEL, Role.SYSTEM, Role.TOOL})


def decode_role(value: str | None) -> str:
    """Normalize a wire role into the canonical open code — totally.

    Known values are case-normalized to their canonical constant; unknown
    values are preserved verbatim (never coerced, never raised on); a missing
    role decodes to the empty string so the caller — the codec, which knows
    its wire context — decides what an absent role means.

    Args:
        value: The role read off the wire, or None when the wire carried
            none.

    Returns:
        The canonical role constant, the verbatim unknown value, or `""`
        when `value` is None.
    """
    if value is None:
        return ""
    normalized = value.strip().lower()
    if normalized in _CANONICAL_ROLES:
        return normalized
    return value


def encode_role(role: str) -> str:
    """Render a canonical role as its wire value.

    The canonical constants are already wire-ready strings, so this is the
    identity — it exists as the named inverse of `decode_role` so codecs
    have exactly one hook to specialize per dialect (e.g. emitting
    `assistant` for `Role.MODEL` on OpenAI wires).

    Args:
        role: The canonical (or preserved-verbatim) role code.

    Returns:
        The role, verbatim.
    """
    return role
