# ocai-contrib-echo

A working, independently packaged **conversion-only** community plugin.
Its fictional wire format is canonical ocai JSON. It demonstrates typed
request encoding/decoding, response decoding, unknown-part preservation,
catalog discovery, provenance, and conformance fixtures.

It registers no live chat component, HTTP endpoint, or streaming converter.
Installing it makes conversion nodes discoverable; it does not make
`ocai.chat.model("echo/...")` callable.

## Test the installed package

From the repository root, build and install ordinary wheels in an isolated
environment, then run the plugin's tests:

```bash
uv run --no-cache --isolated --no-project --python 3.13 \
  --with ./python/packages/ocai-core \
  --with ./examples/ocai-contrib-echo --with pytest --with jsonschema \
  python -m pytest -c /dev/null --rootdir examples/ocai-contrib-echo --import-mode=importlib \
  examples/ocai-contrib-echo/tests -q
```

CI runs this command. It checks real distribution metadata, namespace files,
entry-point discovery, all three conversion edges, an unknown-part round
trip, and schemas/fixtures loaded from the installed wheel. No source-path injection or skipped missing imports are used. Local core
is supplied explicitly because this checkout need not be published.

## Compose and convert

With both distributions installed:

```python
import ocai.contrib.echo as echo
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.convert.catalog import Catalog
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import canonical_node

catalog = Catalog.of(echo.FRAGMENT)
request = ChatRequest(messages=[Message.user("Hello!")])
wire = catalog.convert(request, canonical_node(CHAT_REQUEST), echo.ECHO_CHAT_REQUEST)
restored = catalog.convert(wire.value, echo.ECHO_CHAT_REQUEST, canonical_node(CHAT_REQUEST))
assert restored.value.messages[0].text == "Hello!"
assert restored.report.lossless

# Convenience: loads all installed ocai.fragments entry points.
discovered = Catalog.discover()
```

`EdgeContract(census={})` is a lossless declaration for the canonical-format
documents tested here. Tests check expected outputs and emitted records;
discovery does not certify arbitrary plugin code.

Copy the package into your own repository to develop a provider. Keep the
`ocai.contrib.<name>` namespace, distribution entry point, compatible core
range, and tests. See [the plugin guide](../../docs/user/writing-a-plugin.md) for
the additional contracts required to serve live calls.

The source `fixtures/` and `extensions/` directories are included as package data
under `ocai/contrib/echo/conformance/`. Tests load them via the fragment's
`ConformanceResources` manifest, not paths relative to this repository. The
synthetic `contrib.echo.trace` extension demonstrates validation with a test-only
`jsonschema` dependency; neither core nor the plugin imports it at runtime.
