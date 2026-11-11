# ocai-deepseek

DeepSeek's separately attributable Chat Completions interface for ocai.
This source-available package uses FSL-1.1-ALv2.

WU-44a publishes descriptor nodes, hosting facts and conservative profiles only.
There is no registered codec factory or conversion edge, so public chat execution
fails before provider I/O. Wire DTOs reuse ocai-openai; that dependency does not
make DeepSeek an OpenAI host or inherit OpenAI conversion qualification.

```python
from ocai.convert import Catalog
from ocai.deepseek import FRAGMENT

catalog = Catalog.of(FRAGMENT)
lock = catalog.lock()
```

`deepseek/chat_completions@2026-11` names ocai's documented-wire observation
snapshot dated 2026-11-11. It is neither a vendor version header nor a model
release. Model facts and exclusions are recorded in `docs/providers/deepseek.md`.
WU-44b qualifies conversion edges; WU-45 enables public unary execution.
