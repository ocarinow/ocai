# `ocai` (core)

The core meta-package. Distribution name: **`ocai`**. Public API: `ocai.core`.

```python
from ocai.core import ConversionGraph, ChatRequest, Message, get_component
```

Ships the `ocai/core/` subpackage into the shared `ocai` PEP 420 namespace.
There is **no** `src/ocai/__init__.py` here — that is deliberate, so plugin
distributions (`ocai-openai`, ...) can add their own subpackages to the same
namespace.

## What's here

- `core/types.py` — canonical IR dataclasses + `Report`.
- `core/ports.py` — `ChatModel`, `EmbeddingModel`, `VectorStore`, `Tracer` protocols.
- `core/graph.py` — the conversion graph (registry + Dijkstra-over-loss + caching).
- `core/middleware.py` — middleware base + `RetryMiddleware`.
- `core/plugins.py` — entry-point discovery + `get_component()`.

## Extras

- `pip install ocai[openai]` → pulls the `ocai-openai` plugin distribution.
- `pip install ocai[anthropic]` → pulls the `anthropic` SDK directly.
- `pip install ocai[all]` → everything.
