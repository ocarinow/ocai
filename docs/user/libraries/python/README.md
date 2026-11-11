# Python: installation and first call

Requires Python 3.13 or newer. In your application environment:

```bash
uv add "ocai[http,openai]"
# Or: python -m pip install "ocai[http,openai]"
```

For Anthropic or DeepSeek, choose `ocai[http,anthropic]` or
`ocai[http,deepseek]`. `ocai[all]` includes HTTP and these three codec packages;
it does not install the separate AWS credential or Bedrock host packages.
For Bedrock use `ocai[http]` plus `ocai-bedrock[anthropic,aws]`.

Published releases are listed on [PyPI](https://pypi.org/project/ocai/).
Use matching supported package releases and lock your application's dependencies.
The [reference](../../reference/README.md) shows versions from this checkout,
which may be newer than your installed release.

To try the source revision instead, clone the repository and run `uv sync` at its
root. This installs its six workspace distributions. Run examples with `uv run`.
A source checkout is not required for normal package installation.

## Make a call

Set `OPENAI_API_KEY` explicitly in your process environment. The example reads it
only because you call `ApiKey.from_env`; there is no automatic credential discovery.
Never commit the value. Select a model available to your account.

<!-- test: recorded -->
```python
import ocai.chat
from ocai.chat import ChatRequest, Message
from ocai.core import ApiKey
from ocai.wire import HttpxTransport

with HttpxTransport() as transport:
    model = ocai.chat.model(
        "openai/gpt-4o",
        credentials=ApiKey.from_env("OPENAI_API_KEY"),
        transport=transport,
    )
    result = model.chat(ChatRequest(messages=[Message.user("Hello!")]))
    print(result.value.message.text)
    print(result.route)
    print(result.report)
    print(result.usage)
```

The application owns an explicitly supplied transport; the context manager closes
its connections. Reuse the model/transport across calls inside that lifetime.
For async calls use the transport's async context manager.

The model string binds provider/model selection. Requests contain conversation and
configuration, not a model name. The factory splits on the first slash; the model
part may itself contain slashes. Pin `interface=` or `tag=` only when your installed
catalog has an executable implementation of that interface/revision.

## Read the result

| Field | Meaning |
|---|---|
| `value` | Canonical `ChatResponse` |
| `route` | Selected interface/revision and catalog identity |
| `report` | Conversion and host-effect evidence; inspect losses and semantic shifts |
| `usage` | Known consumption with provenance; missing usage is not zero |
| `raw` | Optional raw response evidence; treat provider content as sensitive |

Continue with [streaming](../../guides/streaming.md), [tools](../../guides/tools.md),
[fidelity](../../guides/fidelity.md), [provider setup](../../guides/providers.md)
and [error handling](../../guides/errors.md).
