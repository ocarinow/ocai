# `ocai-anthropic`

The Anthropic **plugin distribution** for [ocai](https://github.com/ocarinow/ocai).
Distribution name: **`ocai-anthropic`**; `pip install ocai[anthropic]` resolves
to the same wheel. Requires Python 3.13+ and `ocai>=0.1,<0.2`.

It ships only `ocai/anthropic/` into the shared `ocai` PEP 420 namespace,
organized one subpackage per wire interface. Today that is one:

- `ocai.anthropic.messages` — the `/v1/messages` interface: typed wire
  structs, the codec, contract-censused conversion edges, the capability
  profile, and the chat component. Unary and streaming calls are implemented
  and certified against recorded fixtures.

## What installing it does

Exactly one structural thing: the frozen `ocai.anthropic.FRAGMENT`
(a `CatalogFragment`) becomes discoverable through the `ocai.fragments`
entry-point group, so `ocai.chat.model("anthropic/<model>", ...)` can resolve
the provider and the conversion graph gains Anthropic's nodes and edges.
Importing `ocai.anthropic` is inert; there is no import-time registration.
Applications that want an explicit catalog compose it themselves with
`Catalog.of(ocai.anthropic.FRAGMENT)`.

```python
from ocai.anthropic import chat_model
from ocai.core import ApiKey

model = chat_model(
    "claude-sonnet-4-5",
    credentials=ApiKey.from_env("ANTHROPIC_API_KEY", header="x-api-key", scheme=""),
)
result = model.chat(...)   # needs ocai[http] and a real key
```

Anthropic authenticates with the `x-api-key` header, hence the explicit
`header=`/`scheme=`; the required `anthropic-version` header is injected by
the interface's declared traits. `chat_model` is sugar over
`ocai.chat.model("anthropic/<model>", ...)` on a catalog built from this
fragment, never a separate code path.

## Boundaries

- No `anthropic` SDK: ocai owns the wire through `ocai.wire`. This plugin
  depends on `ocai.core` + `ocai.convert` + `ocai.chat` only, never on
  `ocai.wire` or `httpx`, so archived traffic can be re-converted by tooling
  with no ability to make network calls.
- `msgspec` is used only at the wire-decode boundary.
- Every conversion edge declares an `EdgeContract` and ships golden fixtures
  in the repository's `spec/`.

## License

Source-available under FSL-1.1-ALv2 (converting to Apache-2.0 two years after
each release). ocai is not open source.
