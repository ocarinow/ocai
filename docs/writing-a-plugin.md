# Writing an ocai plugin

Third-party plugins ship as independent distributions. They depend on `ocai`
and export a `CatalogFragment`; they do not fork the graph engine or mutate
a global registry. The ABI remains provisional until the modernization release
gates are met. ocai is source-available under FSL-1.1-ALv2.

The working [echo example](https://github.com/ocarinow/ocai/tree/main/examples/ocai-contrib-echo) demonstrates
**offline conversion**. The first-party Chat Completions and Messages adapters
demonstrate the larger live-serving contract. Conversion registration and
endpoint execution are separate capabilities.

## Package and discovery

Use distribution `ocai-contrib-<name>` and import namespace
`ocai.contrib.<name>`. Ship no `ocai/__init__.py` or
`ocai/contrib/__init__.py`; only the leaf package has one. Include `py.typed`.

```toml
[project]
name = "ocai-contrib-example"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["ocai>=0.1,<0.2"]

[project.entry-points."ocai.fragments"]
example = "ocai.contrib.example:FRAGMENT"

[tool.hatch.build.targets.wheel]
packages = ["src/ocai"]
```

The range above matches the current checkout, not a promise about publication
or future ABI compatibility. Test each supported core version. The old
`ocai.plugins` entry-point group is not discovered.

A fragment contains nodes, payload edges, streaming transducers, profiles,
traits, and component factories. Omit components for conversion-only packages.
Use the installed distribution version in `Origin`, as the echo example does.

## Nodes, converters and contracts

A node identifies `(provider, interface, tag, shape, released, status)`.
Use a node per payload shape and interface revision. Import canonical nodes
from the capability; do not invent a competing canonical revision. Tags,
canonical revisions, and distribution versions are distinct.

An edge function takes the source representation and returns `EdgeOutput`:

```python
from ocai.convert.graph import EdgeOutput

def encode_request(request):
    return EdgeOutput(value=request.to_dict(), losses=(), shifts=())
```

The graph assembles `EdgeReport` and `FidelityReport`; an individual edge
does not return `Converted`. Real converters emit `FieldLoss` and
`SemanticShift` records whenever their mappings require them.

```python
from ocai.convert.contract import DeclaredDisposition
from ocai.convert.contract import EdgeContract
from ocai.core.fidelity import Disposition

contract = EdgeContract(census={
    "config.top_k": DeclaredDisposition(Disposition.UNSUPPORTED),
})
```

This is a declaration, not automatic behavior: the converter must report an
unsupported `top_k` when present. Unlisted fields are implicitly declared
exact. The planner uses the static declared grade, not a per-payload prediction.
Golden fixtures and `certify_edge` check output/records and declared bounds.
They cannot detect every omitted record outside tested cases.

Register directed edges explicitly; reverse mappings often have different
contracts. Request encoding uses typed canonical requests; request decoding
returns typed canonical requests. Provider output normally decodes to a typed
canonical response. Preserve unknown tags/data and report unsupported mappings.
Use destination-scoped `provider_options` only for the matching interface.

First-party extension schemas live in `spec/extensions/`. External plugins
package their own schemas and fixtures, declaring their locations on the fragment:

```python
from ocai.convert import ConformanceResources

resources = ConformanceResources(
    package="ocai.contrib.example",
    fixtures="conformance/fixtures",
    extensions="conformance/extensions",  # omit when no schemas are needed
)
# Pass conformance=resources when constructing CatalogFragment.
```

Use the census annotations: namespaced `title`, `description`, `x-ocai-origin`
matching the distribution, and `x-ocai-promotion`. The echo package demonstrates
Hatch `force-include`; no monorepo change or online registry is required.

```python
from ocai.convert.resources import load_conformance_resources
from ocai.convert.conformance import check_fragment

bundle = load_conformance_resources(FRAGMENT)
check_fragment(FRAGMENT, bundle.fixtures.values(), decode_inputs=typed_decoders)
bundle.check_extension_bag(canonical_object.extensions, validate=validate_schema)
```

`typed_decoders` maps source nodes to decoders. Your test suite supplies
`validate_schema(schema, value)`, which must raise for invalid values, for
example with `jsonschema` and a local reference registry. Validate each schema
itself too. The helper validates the supplied bag; tests must select every
canonical bag exercised, rather than recursively treating arbitrary raw JSON
as canonical data. Missing resources, conflicting schemas, uncovered payload
edges, and incorrect output/reports fail. Streaming edges still require fold
triples. Catalog discovery records locations but never runs conformance tests.

## Application-owned composition

```python
catalog = Catalog.of(openai.FRAGMENT, example.FRAGMENT)
# Or discover all installed ocai.fragments entry points:
catalog = Catalog.discover()
```

Under `OWNED_ENDPOINTS`, edge endpoints must be canonical or belong to an
interface the fragment publishes. Allow-listed packages can bridge foreign
interfaces. A converting interface needs at least one canonical connection;
the current check does not guarantee every direction/shape is reachable.

Ownership is self-declared. Admission does not authenticate a publisher, verify
artifact hashes, or sandbox imports. Entry-point loading executes Python.
Applications with governance requirements should explicitly compose reviewed
packages. The default model factory otherwise uses a cached discovered catalog.

Composition rejects competing directed edges, contradictory node metadata,
same-pattern profile conflicts, and conflicting component factories. Identical
registrations remain idempotent. Multiple eligible sibling interfaces require
`interface=`; dates are not an API preference. Equal-specificity profile patterns
sort lexically. Lock format 2 fingerprints full declarations and resource
locations; it does not hash executable code, package artifacts, or resource contents.

## Serving live calls

To be selected by `ocai.chat.model()`, register a `Component` factory for the
provider/interface/capability. Its codec must structurally satisfy
[`ChatCodec`](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/chat/facade.py), including:

- Interface labels and request/response/chunk nodes.
- `encode_request` and `decode_response` returning `EdgeOutput`.
- `native_path`, `dialect_traits`, `bind_resource`, and `bind_stream`.
- SSE decoding and error refinement, with the current protocol signatures.

Do not subclass or import the facade protocol in plugins. Implement the shape
and register graph edges over the same mappings. The facade owns execution;
plugins do not import runtime/wire/httpx or provider SDKs. The bound model name
is inserted after graph conversion.

Profiles use the current namespaced feature vocabulary, such as
`chat.tools`, `chat.tools.parallel`, and `chat.config.output.json_schema`.
Check `_request_features` in the facade and first-party profiles before adding
a feature. A profile is a declaration, not an implementation.

Streaming requires `StreamEdge` factories creating fresh state per stream.
Use the current `StreamConverter` protocol and first-party transducers as the
reference. Fold fixtures must prove accumulated output and final accounting.
Do not copy the obsolete four-method codec sketch.

## Conformance and installation checks

Use the installed echo test suite as the executable recipe. Fixture objects are
plain dictionaries, not objects with `.src` attributes. Canonical-source
fixtures need `decode_input=ChatRequest.from_dict` when the edge expects a
typed request.

```python
fixture = load_fixture(path)
out = check_edge(edge, fixture, decode_input=decode_input)
payload = decode_input(fixture["input"]) if decode_input else fixture["input"]
assert certify_edge(edge, [payload]) == []
```

`check_edge` checks expected output and exact loss/shift records;
`certify_edge` separately checks declared bounds. Use
`assert_fold_triple` / `check_fold_triples` for streaming. Author expected
outputs independently and record fixture provenance. Synthetic cases are not
live recordings. Add unknown-input and downgrade cases.

Test ordinary wheel installation in an isolated environment as well as direct
imports: this catches namespace files, missing package data, entry-point errors,
and dependency mistakes. Missing imports must fail rather than skip. The
example's CI invocation installs core and plugin from local paths without
vendoring core or injecting source paths.
