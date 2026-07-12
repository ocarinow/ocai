# `ocai-openai`

Example **plugin distribution** for `ocai`. Distribution name: **`ocai-openai`**.

Ships only `ocai/openai/` into the shared `ocai` PEP 420 namespace. Because
`pip install ocai[openai]` depends on this distribution, the two install the
**same wheel** — the extra and the standalone package are interchangeable.

```bash
pip install ocai-openai      # or:  pip install ocai[openai]
```

```python
import ocai.openai                      # registers OpenAI<->canonical graph edges
from ocai.core import get_component

handle = get_component("openai")        # discovered via the ocai.plugins entry point
model = handle["chat_model"]()          # stub ChatModel (no network yet)
```

## Status

- `adapter.py` — **stub** `OpenAIChatModel` (canned response, no network) +
  lossless `to_canonical` / `from_canonical` codec and graph-edge registration.
- Pins core to `ocai>=0.1,<0.2` (compatible API range).

`# TODO`: real HTTP client, auth, streaming SSE, tool calls.
