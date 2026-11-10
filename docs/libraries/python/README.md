---
icon: lucide/code
---

# Python

!!! note "Status"

    Implemented through milestones M1–M3 and the modernization WUs 17–20:
    unary and streaming chat on OpenAI Chat Completions and Anthropic
    Messages, cross-conversion fidelity reports, the front doors, an
    independently packaged plugin passing conformance from a wheel. The
    OpenAI Responses interface is a stub; embeddings and vector stores are
    provisional and not exercised end to end. The distributions are **not
    yet published on PyPI**; install from the repository for now.

The Python workspace lives under
[`python/`](https://github.com/ocarinow/ocai/tree/main/python) and ships
three distributions into one PEP 420 namespace:

| Distribution | Ships | Depends on |
|---|---|---|
| `ocai` | `ocai.core`, `ocai.chat`, `ocai.embedding`, `ocai.vectorstore`, `ocai.convert`, `ocai.runtime`, `ocai.wire` | nothing at runtime; `httpx` behind the `[http]` extra |
| `ocai-openai` | `ocai.openai.chat_completions`, `ocai.openai.responses` (stub) | `ocai`, `msgspec` — never an OpenAI SDK |
| `ocai-anthropic` | `ocai.anthropic.messages` | `ocai`, `msgspec` — never an Anthropic SDK |

Installing a provider distribution has exactly one structural effect: its
`CatalogFragment` becomes discoverable through the `ocai.fragments` entry
point and augments the conversion graph. Extras mirror that:
`ocai[http]`, `ocai[openai]`, `ocai[anthropic]`, `ocai[all]`.

## The front door

Build a model once; the provider and model name are one spec string, split
on the first slash. Requests are pure conversation — no `model` field.

``` python
import ocai.chat
from ocai.chat import ChatRequest
from ocai.chat import Message
from ocai.core import ApiKey

model = ocai.chat.model("openai/gpt-4o", credentials=ApiKey.from_env("OPENAI_API_KEY"))
result = model.chat(ChatRequest(messages=[Message.user("Hello!")]))

result.value.message.text   # the canonical reply
result.route                # which interface and tag served the call, and why
result.report               # FidelityReport: what the conversion cost, per field
result.usage                # consumption
```

Switching providers is a configuration change:
`ocai.chat.model(os.environ["OCAI_MODEL"], ...)`. The plugin helper is the
same machinery as sugar:

``` python
from ocai.openai import chat_model

model = chat_model("gpt-4o", credentials=ApiKey.from_env("OPENAI_API_KEY"))
```

## Streaming

One canonical chunk type; every stream ends with `StreamEnd(usage, finish,
report)`; folding the stream must equal the blocking response.

``` python
stream = model.stream(ChatRequest(messages=[Message.user("Hello!")]))
for chunk in stream:
    ...
stream.end       # StreamEnd: usage, finish, report
stream.fold()    # the ChatResponse the chunks add up to
```

Async twins (`achat`, `astream`) exist on the same model object.

## Developing

``` bash
uv sync                          # workspace + dev tools
uv run python scripts/check.py   # ruff, import contracts, pyright strict, mypy strict, pytest
uv run python examples/cross_conversion_demo.py
```

- [`python/README.md`](https://github.com/ocarinow/ocai/blob/main/python/README.md)
  — the workspace guide with the full layer table.
- [Writing a plugin](../../writing-a-plugin.md) — one subpackage per
  provider interface, pure data, certified by fixtures.
- [Providers](../../providers/README.md) — the wire research behind each
  codec and the shipped [feature matrix](../../provider-feature-matrix.md).
