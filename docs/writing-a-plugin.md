# Writing an ocai plugin

This guide is for **third-party authors** who want to add a provider to the
ocai ecosystem in their *own* distribution, published independently. You never
fork or vendor ocai; you depend on the published `ocai` package and plug in by
exporting one frozen value: a `CatalogFragment`.

The structural contract behind everything here is
[`docs/architecture.md`](architecture.md) — especially §7 (plugin shape),
§3.4 (the three-lane knob law), and §4 (the conversion catalog). A working
template lives at
[`examples/ocai-contrib-echo/`](../examples/ocai-contrib-echo/): copy it,
rename `echo`, publish.

> **Status: skeleton.** The plugin ABI (`CatalogFragment`) is provisional
> until v1.0; the conformance harness (`ocai.convert.conformance`) is landing.
> The names in this guide are the settled contract — write against them.

> ocai is **source-available** under FSL-1.1-ALv2, not open source. Your
> plugin is your own work under whatever license you choose.

## The namespace policy (read this first)

ocai is one **PEP 420 namespace package** (`ocai`) that many distributions
contribute subpackages into:

| Import prefix | Who owns it |
| --- | --- |
| `ocai.core`, `ocai.chat`, `ocai.convert`, `ocai.runtime`, `ocai.wire`, … | core (the `ocai` distribution) |
| `ocai.<provider>` — e.g. `ocai.openai` | **reserved** for first-party plugins |
| `ocai.contrib.<name>` — e.g. `ocai.contrib.echo` | **community plugins (you)** |

Ship under `ocai.contrib.<name>`; name the distribution
`ocai-contrib-<name>`. Two hard rules make the shared namespace work: **no
`src/ocai/__init__.py`** and **no `src/ocai/contrib/__init__.py`** — only your
leaf package gets an `__init__.py`.

## One subpackage per interface

A provider publishes **interfaces** (wire protocols), not just models.
`openai/chat_completions` and `openai/responses` are *concurrent sibling
interfaces* of the chat capability — not versions of each other — so each
gets its own subpackage. Mirror that shape even with one interface today:

```
ocai-contrib-echo/
├── pyproject.toml
├── README.md
├── src/ocai/contrib/echo/
│   ├── __init__.py          # exports FRAGMENT — nothing else happens at import
│   ├── fragment.py          # NodeIds, edges, contracts, profiles → CatalogFragment
│   ├── codec.py             # encode / decode / decode_event / map_error
│   └── py.typed
├── fixtures/                # golden edge fixtures + fold triples
└── tests/                   # runs ocai.convert.conformance over fixtures/
```

(First-party plugins put `codec.py` + wire structs inside each interface
subpackage, e.g. `ocai/openai/chat_completions/`; a single-interface plugin
can stay flat like the template.)

## Identity: declare your nodes

Everything you register is keyed by `NodeId(provider, interface, tag, shape,
released, status)` from `ocai.core.identity`. `tag` is an **opaque dated
revision** — never parsed, ordered by `released`; `status` drives resolution
(`STABLE` is auto-selected, `PREVIEW` needs an explicit pin).

```python
from datetime import date

from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import CHAT_RESPONSE
from ocai.core.identity import NodeId

ECHO_CHAT_REQUEST = NodeId(
    provider="echo", interface="chat", tag="2026-07",
    shape=CHAT_REQUEST, released=date(2026, 7, 1),
)
ECHO_CHAT_RESPONSE = NodeId(
    provider="echo", interface="chat", tag="2026-07",
    shape=CHAT_RESPONSE, released=date(2026, 7, 1),
)
```

Also add an interface descriptor to your own `spec/`-style data (and, for
listing in the shared census, to ocai's `spec/interfaces/` via PR) — see
[`spec/interfaces/README.md`](../spec/interfaces/README.md).

## The codec: four methods

A codec translates between your wire format and the canonical IR. The
signatures (architecture §7):

```python
class EchoChatCodec:
    def encode(self, request: ChatRequest) -> dict[str, Any]: ...
    def decode(self, raw: dict[str, Any]) -> ChatResponse: ...
    def decode_event(self, event: dict[str, Any]) -> ChatChunk | None: ...
    def map_error(self, status: int, body: dict[str, Any]) -> OcaiError: ...
```

Rules that keep the codec honest:

- **Decode is total.** Never raise on unknown input: unknown part tags →
  `PartUnknown`, unknown envelope keys → swept into `extensions`, unknown
  finish reasons → `reason="unknown"` with the provider's verbatim value in
  the `native` lane.
- **Three lanes only** (§3.4). Every wire field is either (1) a first-class
  canonical field, (2) a **censused extension** — namespaced
  (`"echo.mirror_mode"`) and schema-registered in `spec/extensions/` (an
  unregistered key is a CI failure), or (3) expanded from
  `provider_options["echo.chat"]` — your codec expands **only its own
  namespace** and never forwards a foreign one.
- **Never rescale, never clamp.** Out-of-range values pass verbatim with an
  `APPROXIMATED` loss record.
- **msgspec only at the wire-decode boundary**, if you want validation there.
  Never pydantic; nothing beyond stdlib in the types you return.
- `map_error` maps to the shared taxonomy in `ocai.core.errors`
  (`RateLimitError`, `AuthError`, `ContextLengthError`, `ContentFilterError`,
  `TransientError`).

You never make network calls and never import `ocai.wire` or httpx: plugins
convert meaning; the runtime moves bytes. That split is what lets an offline
audit tool re-convert archived traffic with your plugin installed and no
network capability at all.

## Edges and the EdgeContract: declare what conversion costs

Each direction of conversion is an `Edge(src, dst, fn, contract, origin)`
(`ocai.convert.graph`). The `contract` is an `EdgeContract`
(`ocai.convert.contract`): your **per-field disposition census**, using the
`Disposition` vocabulary from `ocai.core.fidelity` — `EXACT`, `RENAMED`,
`APPROXIMATED`, `EMULATED`, `EXTENSIONS`, `DROPPED`, `UNSUPPORTED`.

```python
from ocai.convert.contract import EdgeContract
from ocai.core.fidelity import Disposition

CONTRACT = EdgeContract(
    fields={
        "config.temperature": Disposition.EXACT,
        "config.top_k": Disposition.UNSUPPORTED,     # echo has no top_k — say so
        "mirror_mode": Disposition.EXTENSIONS,       # censused: echo.mirror_mode
    },
)
```

Honesty is enforced, not requested: the planner's weight is **derived** from
this census (never author-declared), and the conformance harness certifies at
build time that your edge's *runtime* `FieldLoss` never exceeds its
declaration. **An edge claiming lossless that drops a field cannot ship.** An
empty census is a lossless claim — the strongest claim you can make, so only
make it when the mapping truly is identity.

Streaming edges are `StreamEdge` transducer factories
(`feed(event) -> events`, `flush() -> (events, EdgeReport)`) so chunk-shape
conversion is planned by the same machinery.

## Declare capabilities: `CapabilityProfile`

Support varies below interface level, so profiles are keyed
`(provider, interface, model_pattern)` (`ocai.core.profile`):

```python
from ocai.core.profile import CapabilityProfile
from ocai.core.profile import Support

ECHO_PROFILE = CapabilityProfile(
    provider="echo", interface="chat", model_pattern="*",
    features={"tools": Support.ABSENT, "streaming": Support.ABSENT},
)
```

The feature gate consults this *before* payload conversion: strict mode
refuses with a typed error; annotate mode records the loss.

## The fragment: one frozen export, no import-time globals

The old pattern of registering into a process-global graph at import time is
**gone**. Your package exports a single frozen declarative value; the
*application* composes catalogs:

```python
# fragment.py
FRAGMENT = CatalogFragment(
    origin=Origin(distribution="ocai-contrib-echo", version="0.2.0"),
    nodes=(ECHO_CHAT_REQUEST, ECHO_CHAT_RESPONSE),
    edges=(ENCODE_REQUEST_EDGE, DECODE_RESPONSE_EDGE, ...),
    transducers=(),
    profiles=(ECHO_PROFILE,),
    traits=(),
)
```

```python
# the application, not you:
catalog = Catalog.of(openai.FRAGMENT, echo.FRAGMENT)   # immutable, provenance-stamped
```

`Catalog.discover()` (entry points, group `"ocai.plugins"`) is an opt-in
convenience — point your entry point at the `FRAGMENT` object. Trust is
scoped: under the default `TrustPolicy.OWNED_ENDPOINTS`, your fragment may
only register edges touching shapes **you publish or canonical** — bridging
two foreign providers requires the application's named opt-in.

## Conformance: fixtures are the contract

Every edge ships golden fixtures; every streaming edge ships **fold
triples** (wire event log → canonical chunks → folded response). Formats are
specified in [`spec/README.md`](../spec/README.md); equality is
`semantic_equal` over canonical JSON
([`spec/canonical-json.md`](../spec/canonical-json.md)) — never `==` on raw
dicts.

The harness ships in core, so your test suite stays tiny:

```python
from ocai.convert.conformance import check_edge
from ocai.convert.conformance import check_fold_triple
from ocai.convert.conformance import load_fixture

def test_edges_satisfy_golden_fixtures() -> None:
    for path in sorted(FIXTURES.glob("*.json")):
        check_edge(edge_for(path), load_fixture(path))   # output equality + loss ⊆ contract
```

Tip: generate the `expect` half of a fixture by running your codec once and
dumping the omit-absent `to_dict()` form — then *review* it; the fixture is
the contract, the codec is the implementation. When you add streaming, the
ratchet applies to you too: no new part type without its delta type, fold
law, and paired fixtures in the same change.

Wire-level tests (when your provider is real) use recorded HTTP/SSE pairs —
never live keys, never provider-SDK mocks.

## pyproject rules

```toml
[project]
name = "ocai-contrib-echo"
requires-python = ">=3.13"
# Pin a compatible core range: every wheel merges into one runtime namespace.
dependencies = ["ocai>=0.2,<0.3"]
# NO httpx, NO provider SDK, NO pydantic in your tree. msgspec is allowed
# at the wire-decode boundary only.

[project.entry-points."ocai.plugins"]
echo = "ocai.contrib.echo:FRAGMENT"    # what Catalog.discover() collects

[tool.hatch.build.targets.wheel]
packages = ["src/ocai"]                # ships only ocai/contrib/echo/
```

Ship `py.typed` inside your leaf package; full type hints; `ruff` clean.

## Checklist before you publish

- [ ] Distribution `ocai-contrib-<name>`; code under `ocai.contrib.<name>`;
      no `__init__.py` above the leaf.
- [ ] One subpackage per interface; `NodeId`s with honest `released`/`status`.
- [ ] Codec: total decode, three lanes only, own `provider_options` namespace
      only, taxonomy-mapped errors.
- [ ] Every edge has an `EdgeContract` census and golden fixtures; streaming
      edges have fold triples; extension keys schema-registered.
- [ ] A `CapabilityProfile` per interface (with `model_pattern` where support
      varies by model).
- [ ] One frozen `FRAGMENT` export; **zero** import-time side effects; entry
      point targets `FRAGMENT`.
- [ ] Depends on `ocai` core+convert only — no httpx, no wire imports, no
      provider SDK, no pydantic; `py.typed`; core pinned `>=0.x,<0.y`.
