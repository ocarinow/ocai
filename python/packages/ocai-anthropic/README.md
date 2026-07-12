# `ocai-anthropic`

Anthropic **plugin distribution** for `ocai`. Distribution name: **`ocai-anthropic`**.

Ships only `ocai/anthropic/` into the shared `ocai` PEP 420 namespace. Because
`pip install ocai[anthropic]` depends on this distribution, the two install the
**same wheel** — the extra and the standalone package are interchangeable.

```bash
pip install ocai-anthropic      # or:  pip install ocai[anthropic]
```

```python
import ocai.anthropic                    # registers Anthropic<->canonical graph edges
from ocai.core import get_component

handle = get_component("anthropic")      # discovered via the ocai.plugins entry point
model = handle["chat_model"](            # stub ChatModel (no network yet)
    credentials=ApiKey("sk-ant-...", header="x-api-key", scheme=""),
)
```

## What's here

- `chat/dialect.py` — the **typed Anthropic Messages wire dialect**: msgspec
  structs modelling the full [`POST /v1/messages`](https://platform.claude.com/docs/en/api/messages)
  request, the `Message` response, every content block (text, image, document,
  tool_use, tool_result, thinking, search_result, server-tool results, …), tools,
  tool choice, extended-thinking config, structured-output config, usage, and the
  SSE streaming events. This is the plugin's **decode boundary** (rule 11).
- `adapter.py` — the `anthropic` chat `DialectCodec`, the composed
  `AnthropicChatModel`, and the Anthropic<->canonical graph-edge registration.

## Status

- `dialect.py` — complete wire model of the Messages API (typed but tolerant).
- `adapter.py` — **stub** codec + `AnthropicChatModel`; the canonical mapping is
  lossless at the fixture level. `# TODO`: full content-block conversion, tool
  calls, streaming `ChatChunk`, fidelity loss accounting.
- Pins core to `ocai>=0.1,<0.2` (compatible API range).

`ocai` owns the wire: this adapter imports **no** `anthropic` SDK (rule 12).
Anthropic auth is the `x-api-key` header plus the required `anthropic-version`
header — supply the key explicitly via `ApiKey(..., header="x-api-key", scheme="")`.
