# `ocai` (core)

The core distribution of [ocai](https://github.com/ocarinow/ocai), One Common
interface for AI. Distribution name: **`ocai`**. Requires Python 3.13+.

It ships the shared layers into the `ocai` PEP 420 namespace:

- `ocai.core` — pure-stdlib data contracts: identity, fidelity, errors,
  `CallResult`, credentials, provider references, the IR envelope, canonical
  JSON.
- `ocai.chat`, `ocai.embedding`, `ocai.vectorstore` — capability ports and
  canonical IR types; chat is the one exercised end to end today, the other
  two are provisional contracts.
- `ocai.convert` — governed conversion catalogs, graph planning, edge
  contracts, the conformance harness.
- `ocai.runtime` — sans-io drivers, bindings, policy decisions, interceptors.
- `ocai.wire` — HTTP/SSE transport, hosting, wire policies.

There is deliberately **no** `ocai/__init__.py` in this distribution, so
provider distributions (`ocai-openai`, `ocai-anthropic`, community
`ocai-contrib-*` packages) can add their own subpackages to the same
namespace. Importing `ocai.core` or `ocai.convert` needs no third-party
package at all.

## Extras

- `ocai[http]` — `httpx`, used only by `ocai.wire.transport.HttpxTransport`
  and imported lazily there. Required for live calls.
- `ocai[openai]`, `ocai[anthropic]`, `ocai[deepseek]` — the sibling codec distributions
  (`ocai-openai`, `ocai-anthropic`, `ocai-deepseek`); the extra and the standalone package
  resolve to the same wheel.
- `ocai[all]` — HTTP plus those three codecs; AWS credentials and Bedrock
  hosting are separate distributions.

## Usage

```python
import ocai.chat
from ocai.chat import ChatRequest
from ocai.chat import Message
from ocai.core import ApiKey

model = ocai.chat.model("openai/gpt-4o", credentials=ApiKey.from_env("OPENAI_API_KEY"))
result = model.chat(ChatRequest(messages=[Message.user("Hello!")]))
print(result.value.message.text, result.report.lossless)
```

A live call needs `ocai[http]`, an installed provider plugin, and a real key;
credentials are explicit and never discovered from the environment unless
`ApiKey.from_env` is called. Every port returns
`CallResult(value, route, report, usage, raw)`. The full guide is the
[Python README](https://github.com/ocarinow/ocai/blob/main/python/README.md).

## License

Source-available under FSL-1.1-ALv2 (converting to Apache-2.0 two years after
each release). ocai is not open source.
