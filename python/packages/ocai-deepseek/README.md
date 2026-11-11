# ocai-deepseek

DeepSeek's separately attributable Chat Completions interface for ocai.
This source-available package uses FSL-1.1-ALv2.

The catalog publishes independently censused unary request encode, request audit
and response decode edges. Text, function tools, JSON-object output, reasoning
replay, native finish state and measured usage are qualified by golden fixtures.
Unknown native data remains recoverable in registered extension banks.

There is no registered serving component or streaming edge yet: public chat
execution fails before provider I/O. Compatible mapping code and wire DTOs reuse
ocai-openai, while DeepSeek retains its own identity, profiles and contracts.

```python
from ocai.convert import Catalog
from ocai.deepseek import FRAGMENT

catalog = Catalog.of(FRAGMENT)
lock = catalog.lock()
```

`deepseek/chat_completions@2026-11` names ocai's documented-wire observation
snapshot dated 2026-11-11. It is neither a vendor version header nor a model
release. Model facts and exclusions are recorded in `docs/providers/deepseek.md`.
WU-45 enables public unary execution; WU-46 qualifies streaming.

Tool histories require original reasoning text for every assistant turn. Missing
reasoning and unqualified model-dependent top_p are reported UNSUPPORTED. Media,
beta strict tools, FIM, prefix completion, JSON-schema output, Responses and
Anthropic-compatible endpoints are outside this initial surface.
