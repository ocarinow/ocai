"""Typed OpenAI **Responses** wire models (`POST /v1/responses`) — [stub].

Structure only: this module will hold the msgspec decode-boundary structs for
the `/responses` interface, mirroring how
`ocai.openai.chat_completions.wire` models the chat-completions wire. The
interface's graph identity lives in `ocai.openai.responses.codec`.

The load-bearing difference from chat_completions is the **item model**: a
`/responses` request/response is a flat list of typed, id-carrying *items*
rather than role-nested messages — the wire design the canonical part
taxonomy's `id`/`anchor` fields were shaped by (§3.1). The structs to model,
each mirroring OpenAI's schema component names exactly with a `Reference:`
link:

- `message` items (role + content parts: `input_text`, `output_text`,
  `input_image`, `input_file`, `refusal`, …),
- `function_call` items (`call_id`, `name`, `arguments` string) and their
  paired `function_call_output` items — call and result are *sibling items*
  correlated by `call_id`, exactly like `PartToolCall`/`PartToolResult`,
- `reasoning` items (`summary` parts + `encrypted_content`) — decoded as ONE
  `PartReasoning` with an `opaque` `ProviderRef`, never two correlated parts,
- built-in tool call items (`web_search_call`, `code_interpreter_call`,
  `mcp_call`, …) → `PartServerToolCall`/`Result` with byte-faithful payloads,
- the request envelope (`model`, `input`, `instructions`,
  `previous_response_id` — a `ProviderRef` anchor, `store`, `include`,
  `text.format`, `reasoning`, …) and the response envelope (`id`, `status`,
  `output`, `usage`, `incomplete_details`, …),
- the semantic streaming events (`response.output_text.delta`,
  `response.output_item.added`, `response.completed`, …).
"""

from __future__ import annotations

import msgspec

# TODO: model the item structs listed in the module docstring (message /
# function_call / function_call_output / reasoning / built-in tool items) as
# tagged unions on `type`, transcribed from the openai-python type stubs.


# Stub base with no subclasses until the /responses item structs land (see the
# TODO above); unused-by-construction, not dead code.
class _Wire(msgspec.Struct, kw_only=True, omit_defaults=True):  # pyright: ignore[reportUnusedClass]
    """Base for every Responses wire struct: keyword-only, omit-defaults.

    Same tolerant-decode posture as the chat_completions wire base: unknown
    fields are ignored on decode and recovered by the codec's extensions
    sweep, never an error (rule 6).
    """
