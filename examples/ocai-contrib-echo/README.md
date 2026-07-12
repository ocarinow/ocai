# `ocai-contrib-echo` — example third-party ocai plugin

A **template** for a community ocai plugin under the July 2026 architecture
([`docs/architecture.md`](../../docs/architecture.md) §7). `echo` is a
fictional provider; copy this directory, rename `echo` to your provider, and
publish independently — nothing here lives in the ocai monorepo.

> **TEMPLATE STATUS: pending harness completion.** The structure and names
> below are the settled contract; the `ocai.convert` layer (catalog +
> conformance harness) is still landing, so the fragment does not import yet
> and the test suite skips gracefully until it does.

Full walkthrough: [`docs/writing-a-plugin.md`](../../docs/writing-a-plugin.md).

## What it demonstrates

- **Namespace policy** — community plugins ship into `ocai.contrib.<name>`
  (PEP 420: no `__init__.py` above the leaf package), leaving
  `ocai.<provider>` for first-party plugins.
- **One frozen export, zero import-time side effects** — the whole
  integration surface is `FRAGMENT`, a declarative `CatalogFragment` (nodes,
  edges, profiles). Applications compose `Catalog.of(echo.FRAGMENT)`; the
  old import-time global-graph registration pattern is gone.
- **Four-level identity** — echo publishes one interface (`echo/chat`) at one
  dated tag as `NodeId`s; the canonical IR is just the interface named
  `ocai`.
- **Honest contracts** — the identity edges carry an *empty* `EdgeContract`,
  which is a lossless **claim** the conformance harness certifies against
  runtime loss. A real provider declares real per-field dispositions.
- **The codec shape** — `codec.py` shows the four-method surface
  (`encode` / `decode` / `decode_event` / `map_error`) and documents the
  total-decode and three-lane rules each must honor.
- **Conformance** — `fixtures/` holds a golden edge fixture in the
  `spec/README.md` format; `tests/` runs it through
  `ocai.convert.conformance` (`load_fixture` / `check_edge`).

## Layout

```
ocai-contrib-echo/
├── pyproject.toml                    # core pin, ocai.plugins entry point → FRAGMENT
├── src/ocai/contrib/echo/
│   ├── __init__.py                   # exports FRAGMENT — nothing else happens
│   ├── fragment.py                   # NodeIds + edges + EdgeContract + profile
│   ├── codec.py                      # encode/decode/decode_event/map_error
│   └── py.typed
├── fixtures/echo_chat_request.json   # golden edge fixture (input/expect/losses)
└── tests/test_conformance.py         # harness-driven; skips until convert lands
```

## Develop & test

```bash
pip install -e .          # resolves `ocai>=0.2,<0.3`
pytest                    # conformance suite (skips while the harness is pending)
```

Once installed, an application can discover the plugin without importing it
by name:

```python
from ocai.convert.catalog import Catalog

catalog = Catalog.discover()          # collects ocai.plugins entry points
# or, explicit and audit-friendly:
import ocai.contrib.echo as echo
catalog = Catalog.of(echo.FRAGMENT)
```
