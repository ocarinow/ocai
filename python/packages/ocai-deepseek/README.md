# ocai-deepseek

DeepSeek's separately attributable Chat Completions interface for ocai.
This source-available package uses FSL-1.1-ALv2.

The catalog publishes independently censused unary request encode, request audit
and response decode edges. Text, function tools, JSON-object output, reasoning
replay, native finish state and measured usage are qualified by golden fixtures.
Unknown native data remains recoverable in registered extension banks.

Public sync/async unary calls use the standard chat facade. Compatible mapping
code and wire DTOs reuse ocai-openai, while DeepSeek retains its own identity,
profiles and contracts. Streaming preparation currently fails before provider I/O;
WU-46 owns that qualification.

```python
import ocai.chat
from ocai.chat.types import ChatRequest, Message
from ocai.convert import Catalog
from ocai.core import ApiKey
from ocai.core.fidelity import Disposition, FidelityPolicy
from ocai.deepseek import FRAGMENT

model = ocai.chat.model(
    "deepseek/deepseek-flash",
    credentials=ApiKey.from_env("DEEPSEEK_API_KEY"),
    catalog=Catalog.of(FRAGMENT),  # may be omitted to use installed plugin discovery
    conversion_policy=FidelityPolicy(
        forbidden_dispositions=frozenset({Disposition.UNSUPPORTED}),
    ),
)
prepared = model.prepare(ChatRequest(messages=[Message.user("Say hello.")]))
inspection = prepared.inspection  # routing, paths, coverage and request findings
result = prepared.chat()          # or: await prepared.achat()
```

`deepseek/chat_completions@2026-11` names ocai's documented-wire observation
snapshot dated 2026-11-11. It is neither a vendor version header nor a model
release. Model facts and exclusions are recorded in `docs/providers/deepseek.md`.
No provider SDK or ambient credential discovery is used.

Tool histories require original reasoning text for every assistant turn. Missing
reasoning and unqualified model-dependent top_p are reported UNSUPPORTED. The
explicit policy above rejects those findings before sending; without a caller
policy the facade retains its ordinary permissive/reporting behavior. Media,
beta strict tools, FIM, prefix completion, JSON-schema output, Responses and
Anthropic-compatible endpoints are outside this initial surface.
