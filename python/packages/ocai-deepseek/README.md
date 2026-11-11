# ocai-deepseek

DeepSeek's separately attributable Chat Completions interface for ocai.
This source-available package uses FSL-1.1-ALv2.

The catalog publishes independently censused unary request encode, request audit
and response decode edges. Text, function tools, JSON-object output, reasoning
replay, native finish state and measured usage are qualified by golden fixtures.
Unknown native data remains recoverable in registered extension banks.

Public sync/async unary calls use the standard chat facade. Compatible mapping
code and wire DTOs reuse ocai-openai, while DeepSeek retains its own identity,
profiles and contracts. Sync/async streaming uses its own censused graph edge over
shared compatible framing machinery, with reasoning, text, indexed tools, native
finish values, full response identity and usage on the final choice qualified.
`model.prepare(request, streaming=True)` supports the same public inspection
before `.stream()` or `await .astream()`. Own streams with `with` / `async with`,
or call `.close()` / `await .aclose()` when stopping consumption early.

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

The provider backend fingerprint is retained in `ResponseInfo.extensions` under
`deepseek.system_fingerprint`, with an EXTENSIONS finding in both directions of
execution. Unknown native fields remain available on canonical event extensions
(`deepseek.stream_unmapped`) and raw events with findings; they are not advertised
as portable first-class features. Full response fold parity is qualified for the
recorded supported surface; unknown-event extension folding is tracked as G-12.

A successful stream requires both a finish signal and `[DONE]`. An aborted finish,
malformed frame, missing tool identity, missing finish or missing sentinel cannot
produce successful StreamEnd. Available usage and reports remain in the execution
outcome. No generation is retried after partial delivery. Undocumented native
in-stream error codes remain `unknown` with verbatim evidence; no stable vendor
error schema is claimed.
