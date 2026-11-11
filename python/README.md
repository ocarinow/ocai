# ocai — Python

The Python implementation of [ocai](../README.md), the first language port of
the language-neutral [`spec/`](../spec/README.md). This directory is a
[uv](https://docs.astral.sh/uv/) workspace; the workspace root is the
repository's top-level `pyproject.toml`.

**Requirements:** Python 3.13+ and uv.

## Distributions

The distributions share one PEP 420 namespace, `ocai`. No distribution ships
an `ocai/__init__.py`; each contributes only its own subpackages.

| Distribution | Directory | Ships | Depends on |
|---|---|---|---|
| `ocai` | [`packages/ocai-core`](packages/ocai-core/) | `ocai.core`, `ocai.chat`, `ocai.embedding`, `ocai.vectorstore`, `ocai.convert`, `ocai.runtime`, `ocai.wire` | nothing at runtime; `httpx` behind the `[http]` extra |
| `ocai-openai` | [`packages/ocai-openai`](packages/ocai-openai/) | `ocai.openai.chat_completions` (implemented), `ocai.openai.responses` (stub) | `ocai>=0.1,<0.2`, `msgspec` |
| `ocai-anthropic` | [`packages/ocai-anthropic`](packages/ocai-anthropic/) | `ocai.anthropic.messages` | `ocai>=0.1,<0.2`, `msgspec` |
| `ocai-deepseek` | [`packages/ocai-deepseek`](packages/ocai-deepseek/) | `ocai.deepseek` (interface descriptors; execution qualification pending) | `ocai>=0.1,<0.2`, `ocai-openai>=0.1,<0.2` |
| `ocai-aws` | [`packages/ocai-aws`](packages/ocai-aws/) | `ocai.aws` credentials | `ocai>=0.1,<0.2`, AWS CRT signing library |
| `ocai-bedrock` | [`packages/ocai-bedrock`](packages/ocai-bedrock/) | `ocai.bedrock` hosting | `ocai>=0.1,<0.2`; optional AWS credentials and Anthropic codec |

ocai owns the wire through `ocai.wire`. Semantic codecs depend on core/convert,
never wire/httpx. The independent cloud credential package delegates signing to
AWS-maintained code behind ocai contracts; SDK objects remain private (ADR 0016).

## Install

The `ocai` distribution declares the extras `http` (pulls `httpx`), `openai`,
`anthropic` and `deepseek` (pull the sibling plugin distribution), and `all`
(everything), so the intended install lines are:

```bash
uv add "ocai[http,openai]"        # core + HTTP transport + the OpenAI plugin
uv add "ocai[all]"                # core + httpx + both provider plugins
```

The distributions are **not yet published to PyPI** (checked November 2026),
so today they resolve only from a checkout of this repository. Inside the
checkout, `uv sync` installs all three as editable workspace members; from
another project, point uv at the package directories, for example:

```bash
uv run --isolated --no-project --python 3.13 \
  --with "./python/packages/ocai-core[http]" \
  --with ./python/packages/ocai-openai \
  python -c "import ocai.openai, httpx; print('ok')"
```

## Usage

Build a model once (the provider-specific model name is bound here, never
carried in the request), then call it with pure conversation payloads.
Credentials are explicit: constructing a model never reads the environment on
its own; only `ApiKey.from_env` / `ApiKey.from_file` do, and only when called.

```python
import ocai.chat
from ocai.chat import ChatRequest
from ocai.chat import Message
from ocai.core import ApiKey

model = ocai.chat.model(
    "openai/gpt-4o",
    credentials=ApiKey.from_env("OPENAI_API_KEY"),
)
result = model.chat(ChatRequest(messages=[Message.user("Hello!")]))
print(result.value.message.text)   # the canonical ChatResponse
print(result.route)                # provider / interface / tag + catalog fingerprint
print(result.report.lossless)      # the FidelityReport: every conversion cost, never silent
print(result.usage)
```

Running the call above needs a real `OPENAI_API_KEY` and a model your account
can use. Every port returns `CallResult(value, route, report, usage, raw)`;
the `FidelityReport` lives on the envelope only, so IR payloads stay pure.

The spec string `"<provider>/<model>"` is split on the first slash only, so
the model part may itself contain slashes. The whole provider + model choice
is one configuration value: `ocai.chat.model(os.environ["OCAI_MODEL"], ...)`
switches providers with zero code change. With no explicit `catalog=`, the
factory composes the `CatalogFragment`s of every installed plugin
(discovered through the `ocai.fragments` entry-point group).

### Streaming and the fold law

```python
from ocai.chat.types import ChunkType

stream = model.stream(ChatRequest(messages=[Message.user("Hello!")]))
for chunk in stream:
    if chunk.type == ChunkType.PART_DELTA:
        print(chunk.delta)
print(stream.end)   # StreamEnd(usage, finish, report), set once the stream is exhausted
```

The fold law is normative: `StreamAccumulator.fold(model.stream(request))`
equals `model.chat(request).value`, and `ChatStream.fold()` is the
convenience form. `achat` / `astream` are the asynchronous twins.

### Plugin helper

Each provider distribution also ships a thin helper over the same front door:

```python
from ocai.openai import chat_model
from ocai.core import ApiKey

model = chat_model("gpt-4o", credentials=ApiKey.from_env("OPENAI_API_KEY"))
```

`from ocai.anthropic import chat_model` is the Anthropic twin (Anthropic
authenticates with the `x-api-key` header: pass
`ApiKey.from_env("ANTHROPIC_API_KEY", header="x-api-key", scheme="")`).
Either helper is sugar over `ocai.chat.model("<provider>/<model>", ...)`,
never a separate code path.

## Layers

| Layer | Purpose |
|---|---|
| `ocai.core` | Standard-library contracts: identities, context, results, fidelity, credentials, references |
| `ocai.chat` / `ocai.embedding` / `ocai.vectorstore` | Capability ports and canonical IR; only chat is exercised end to end today |
| `ocai.convert` | Catalog composition, graph planning, conversion, and the conformance harness |
| `ocai.runtime` | Sans-io drivers, bindings, policy decisions, interceptor composition |
| `ocai.wire` | HTTP/SSE, hosting, and retry; the HTTP dependency is optional |
| Provider distributions | Interface-specific codecs, edges, profiles, and factories; pure data plus conversion |

The dependency arrows between layers are enforced by import-linter; an import
against them fails the build. The full contract is
[`docs/architecture.md`](../docs/architecture.md).

## Developer commands

Run from the repository root.

```bash
uv sync                                          # create the env, install the workspace
uv run python scripts/check.py                   # THE gate (path-aware; --all forces every step)
task check                                       # the same gate via Task (task lists every command)
uv run python examples/cross_conversion_demo.py  # the cross-conversion fidelity demo (offline)
```

Tests are wire-level: recorded HTTP/SSE pairs (under
`packages/ocai-core/tests/http/`) and golden fixtures from `spec/`, never
live keys, never provider-SDK mocks. A change is not done until
`scripts/check.py` exits 0.

## Writing a plugin

A provider plugin is a separate distribution that ships one subpackage per
interface into the `ocai` namespace and exposes a frozen `CatalogFragment`
through the `ocai.fragments` entry point; installing it has exactly one
structural effect, adding nodes and edges to the conversion graph. Start from
[`examples/ocai-contrib-echo`](../examples/ocai-contrib-echo/README.md), the
independently packaged template, and read
[`docs/writing-a-plugin.md`](../docs/writing-a-plugin.md) for the contracts a
plugin must honour to serve live calls.

## License

Source-available under FSL-1.1-ALv2; ocai is not open source. See
[LICENSE](../LICENSE).


## Package responsibilities

The workspace gate reads optional `[tool.ocai] role = "credential"` or `"host"`
metadata for external adapters. Existing provider packages default to `codec`;
`ocai` defaults to `kernel`. Codecs register catalog fragments and convenience
extras. Credentials and service hosts register no fake conversion fragment and
need not enter the kernel's aggregate extra; install them explicitly. They still
need release/typing/metadata wiring and a named import boundary forbidding direct
HTTP transport ownership. Credential adapters additionally stay independent of
chat, conversion and runtime modules. Unknown or misplaced roles fail the gate.
