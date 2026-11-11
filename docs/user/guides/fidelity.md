# Conversion, inspection and fidelity

Every call's `report` describes conversion losses and semantic shifts. Inspect it
when changing a provider, interface or revision. `lossless` is an evidence summary,
not a statement about answer quality or model equivalence. Host effects such as
filtering are recorded separately from conversion edges in the same report.

## Compose a catalog and convert offline

<!-- test: offline -->
```python
import ocai.openai
from ocai.chat import CANONICAL_CHAT_REQUEST
from ocai.convert import Catalog
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_REQUEST

catalog = Catalog.of(ocai.openai.FRAGMENT)
converted = catalog.convert(
    {"messages": [{"role": "user", "content": "Hello!"}]},
    CHAT_COMPLETIONS_REQUEST,
    CANONICAL_CHAT_REQUEST,
)
print(converted.value)
print(converted.report)
print(catalog.lock())
```

An explicit catalog makes the admitted fragments visible. The default factory
catalog discovers installed fragment entry points under its trust policy.
A catalog lock identifies the composed conversion configuration; it does not prove
live endpoint availability. `catalog.inspect(...)` exposes declarations and evidence
locations without running provider traffic or certifying them again.

## Enforce acceptance

<!-- test: offline -->
```python
from ocai.core.fidelity import Disposition, FidelityPolicy

policy = FidelityPolicy(
    forbidden_dispositions=frozenset({Disposition.DROPPED, Disposition.UNSUPPORTED}),
)
```

Pass `conversion_policy=policy` when constructing a model. `model.prepare(request)`
returns a prepared call with inspection data; inspect its request report before
execution. A prepared snapshot is rejected if its governed configuration becomes
stale. Response findings become known after execution, so a response-policy failure
can occur after billable provider work. Preserve its usage/evidence rather than
reporting zero cost. See [errors](errors.md) and [gateway integration](../gateway-integration.md).

Provider references remain scoped to their provider/interface. Replaying a foreign
ID as a native continuation is unsupported; use explicit history or a qualified
migration path and preserve the reported conversion findings.
