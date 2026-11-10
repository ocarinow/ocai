# `ocai-openai`

The OpenAI **plugin distribution** for [ocai](https://github.com/ocarinow/ocai).
Distribution name: **`ocai-openai`**; `pip install ocai[openai]` resolves to the
same wheel. Requires Python 3.13+ and `ocai>=0.1,<0.2`.

It ships only `ocai/openai/` into the shared `ocai` PEP 420 namespace,
organized one subpackage per wire interface:

- `ocai.openai.chat_completions` — the `/v1/chat/completions` interface:
  typed wire structs, the codec, contract-censused conversion edges, the
  capability profile, and the chat component. Unary and streaming calls are
  implemented and certified against recorded fixtures.
- `ocai.openai.responses` — the `/v1/responses` interface. A **stub**: its
  nodes are declared so the interface exists in the graph, but it has no
  edges, codec, or chat component yet. The front door never auto-selects it,
  and pinning `interface="responses"` raises `LookupError` until it lands.

The two are sibling interfaces of the one chat capability, not versions of
each other.

## What installing it does

Exactly one structural thing: the frozen `ocai.openai.FRAGMENT`
(a `CatalogFragment`) becomes discoverable through the `ocai.fragments`
entry-point group, so `ocai.chat.model("openai/<model>", ...)` can resolve the
provider and the conversion graph gains OpenAI's nodes and edges. Importing
`ocai.openai` is inert; there is no import-time registration. Applications
that want an explicit catalog compose it themselves with
`Catalog.of(ocai.openai.FRAGMENT)`.

```python
from ocai.openai import chat_model
from ocai.core import ApiKey

model = chat_model("gpt-4o", credentials=ApiKey.from_env("OPENAI_API_KEY"))
result = model.chat(...)   # needs ocai[http] and a real key
```

`chat_model` is sugar over `ocai.chat.model("openai/<model>", ...)` on a
catalog built from this fragment, never a separate code path.

## Boundaries

- No `openai` SDK: ocai owns the wire through `ocai.wire`. This plugin depends
  on `ocai.core` + `ocai.convert` + `ocai.chat` only, never on `ocai.wire` or
  `httpx`, so archived traffic can be re-converted by tooling with no ability
  to make network calls.
- `msgspec` is used only at the wire-decode boundary.
- Every conversion edge declares an `EdgeContract` and ships golden fixtures
  in the repository's `spec/`.

## License

Source-available under FSL-1.1-ALv2 (converting to Apache-2.0 two years after
each release). ocai is not open source.
