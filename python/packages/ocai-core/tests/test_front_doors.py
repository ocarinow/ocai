"""The §3.4 front doors, wired end-to-end (WU-16).

Two equivalent doors, neither forced, both over the SAME machinery:

- **(a)** the architecture's five-liner — `ocai.chat.model("<provider>/<model>",
  credentials=...)` — works end-to-end over a recorded pair with **zero
  provider imports at module level**: the provider is reached exclusively
  through the entry-point-discovered default catalog and the fragment's
  registered component factory;
- **(b)** the spec string parses on the FIRST slash only (HF-style model ids
  keep their slashes), and an unmatched provider fails with a clear error
  naming the providers the catalog actually composes;
- **(c)** the plugin sugar (`ocai.openai.chat_model`) is the identical
  composition — same details, same route coordinates, same wire bytes on the
  same recorded pair — never a separate code path;
- **(d)** the `interceptors` kwarg folds a port-tier `CallInterceptor` chain
  around the facade (both faces), including short-circuits that never touch
  the wire;
- **(e)** `ocai.runtime.dual` bridges sync-only and async-only ports for
  real — thread offload one way, a portal thread's private loop the other —
  round-tripping unary calls and streams;
- **(f)** `Catalog.discover()` composes both installed plugin fragments from
  their declared entry points.

Recorded pairs replay through the real `HttpxTransport` via respx (rule 10):
no live keys, no provider-SDK mocks.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
import respx

import ocai.chat
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.core import ApiKey
from ocai.core.canonjson import semantic_equal
from ocai.core.result import CallResult
from ocai.runtime.dual import from_async
from ocai.runtime.dual import from_sync
from ocai.runtime.interceptors import Call

# The `load_http` conftest fixture: a recorded request/response pair by file name.
type LoadHttp = Callable[[str], dict[str, Any]]

# The first-party endpoint of the recorded pair — from the recording itself,
# NOT from a plugin import (this module deliberately imports no provider
# package at module level; see test (a)).
URL = "https://api.openai.com/v1/chat/completions"


def _plain_request() -> ChatRequest:
    """The canonical request the plain recording was minted from."""
    return ChatRequest(
        messages=[Message.system("You are concise."), Message.user("Hello, who are you?")]
    )


# --- (a) the §3.4 five-liner, zero provider imports ------------------------------


@respx.mock
def test_five_liner_end_to_end_with_zero_provider_imports(load_http: LoadHttp) -> None:
    pair = load_http("openai_chat_completion.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    chat = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"))
    res = chat.chat(_plain_request())

    # The canonical value decoded through the discovered catalog's edges.
    assert res.value.message.role == "model"
    assert semantic_equal(res.value.message, Message.model("I am an AI assistant."))
    # The route records the resolution: the fragment's chat_completions
    # revision, host-stamped with the first-party endpoint the Direct host
    # built from the fragment's declared traits.
    assert res.route is not None
    assert res.route.node.provider == "openai"
    assert res.route.node.interface == "chat_completions"
    assert res.route.host == URL
    assert res.route.catalog_hash  # stamped from the discovered catalog's lock
    # What went over the wire: the recorded body (bound model injected below
    # the graph) with the credential applied at the leaf.
    sent = route.calls.last.request
    assert json.loads(sent.content) == pair["request"]["json"]
    assert sent.headers["authorization"] == "Bearer sk-test"
    assert res.raw == pair["response"]["json"]
    assert res.report is not None and res.report.lossless


@respx.mock
async def test_five_liner_async_twin(load_http: LoadHttp) -> None:
    pair = load_http("openai_chat_completion.json")
    respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    chat = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"))
    res = await chat.achat(_plain_request())

    assert semantic_equal(res.value.message, Message.model("I am an AI assistant."))
    assert res.route is not None
    assert res.route.host == URL


# --- (b) spec parsing: first slash only, clear errors -----------------------------


def test_spec_splits_on_the_first_slash_only() -> None:
    # An HF-style model id keeps its own slashes — only the FIRST one splits.
    chat = ocai.chat.model("openai/meta-llama/Llama-3.3-70B", credentials=ApiKey("sk-test"))
    assert chat.details["provider"] == "openai"
    assert chat.details["model_name"] == "meta-llama/Llama-3.3-70B"


def test_unknown_provider_names_the_composed_ones() -> None:
    from ocai.convert.catalog import ResolutionError

    with pytest.raises(ResolutionError) as exc:
        ocai.chat.model("gemini/flash", credentials=ApiKey("sk-test"))
    message = str(exc.value)
    assert "gemini" in message
    # The clear error names what IS composed (both installed plugins).
    assert "openai" in message
    assert "anthropic" in message


@pytest.mark.parametrize("bad", ["gpt-4o", "openai/", "/gpt-4o", ""])
def test_slashless_or_empty_specs_are_value_errors(bad: str) -> None:
    with pytest.raises(ValueError):
        ocai.chat.model(bad, credentials=ApiKey("sk-test"))


def test_pinned_stub_interface_fails_at_the_component_lookup() -> None:
    # openai/responses is published nodes-only (no component factory): the
    # unpinned door never auto-selects it, and pinning it says why it fails.
    with pytest.raises(LookupError):
        ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"), interface="responses")


# --- (c) door 2 is the identical composition --------------------------------------


@respx.mock
def test_plugin_sugar_is_the_same_composition_on_the_same_pair(load_http: LoadHttp) -> None:
    from ocai.openai import chat_model as openai_chat_model

    pair = load_http("openai_chat_completion.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    core_door = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"))
    sugar_door = openai_chat_model("gpt-4o", credentials=ApiKey("sk-test"))

    # Identical composition, before any call.
    assert sugar_door.details == core_door.details

    core_res = core_door.chat(_plain_request())
    core_sent = json.loads(route.calls.last.request.content)
    sugar_res = sugar_door.chat(_plain_request())
    sugar_sent = json.loads(route.calls.last.request.content)

    # Same wire bytes, same route coordinates, same decoded canonical value.
    assert sugar_sent == core_sent == pair["request"]["json"]
    assert sugar_res.route is not None and core_res.route is not None
    assert sugar_res.route.node == core_res.route.node
    assert sugar_res.route.host == core_res.route.host == URL
    assert sugar_res.route.reason == core_res.route.reason
    assert semantic_equal(sugar_res.value, core_res.value)


@respx.mock
def test_anthropic_sugar_composes_the_messages_interface(load_http: LoadHttp) -> None:
    from ocai.anthropic import chat_model as anthropic_chat_model

    chat = anthropic_chat_model(
        "claude-sonnet-4-5", credentials=ApiKey("sk-ant", header="x-api-key", scheme="")
    )
    assert chat.details["provider"] == "anthropic"
    assert chat.details["interface"] == "messages"
    assert chat.details["model_name"] == "claude-sonnet-4-5"


# --- (d) the interceptors kwarg ----------------------------------------------------


class _Recorder:
    """A pass-through CallInterceptor recording what traveled the chain."""

    def __init__(self) -> None:
        self.calls: list[Call] = []
        self.acalls: list[Call] = []

    def intercept(self, call: Call, next: Any) -> CallResult[Any]:
        self.calls.append(call)
        return next(call)

    async def aintercept(self, call: Call, next: Any) -> CallResult[Any]:
        self.acalls.append(call)
        return await next(call)


class _ShortCircuit:
    """A cache-hit-style interceptor: answers without calling next."""

    def __init__(self, result: CallResult[Any]) -> None:
        self._result = result

    def intercept(self, call: Call, next: Any) -> CallResult[Any]:
        return self._result

    async def aintercept(self, call: Call, next: Any) -> CallResult[Any]:
        return self._result


@respx.mock
def test_interceptors_kwarg_applies_the_chain(load_http: LoadHttp) -> None:
    pair = load_http("openai_chat_completion.json")
    respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    recorder = _Recorder()
    chat = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"), interceptors=(recorder,))
    request = _plain_request()
    res = chat.chat(request)

    assert len(recorder.calls) == 1
    assert recorder.calls[0].request is request
    assert semantic_equal(res.value.message, Message.model("I am an AI assistant."))
    # The wrapper still satisfies the port and describes the composition.
    assert chat.details["provider"] == "openai"


@respx.mock
async def test_interceptors_kwarg_applies_the_async_face(load_http: LoadHttp) -> None:
    pair = load_http("openai_chat_completion.json")
    respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))

    recorder = _Recorder()
    chat = ocai.chat.model("openai/gpt-4o", credentials=ApiKey("sk-test"), interceptors=(recorder,))
    await chat.achat(_plain_request())

    assert len(recorder.acalls) == 1
    assert recorder.calls == []


@respx.mock
def test_short_circuit_interceptor_never_touches_the_wire() -> None:
    wire = respx.post(URL).mock(return_value=httpx.Response(500, json={}))
    cached = CallResult(value="cached-response")
    chat = ocai.chat.model(
        "openai/gpt-4o", credentials=ApiKey("sk-test"), interceptors=(_ShortCircuit(cached),)
    )

    res = chat.chat(_plain_request())

    assert res is cached
    assert wire.call_count == 0


# --- (e) dual adapters: sync <-> async round-trips ---------------------------------


class _SyncOnlyPort:
    """A blocking-only ChatModel-shaped port (no a-prefixed faces)."""

    def chat(self, request: Any, *, ctx: Any = None) -> str:
        return f"sync:{request}"

    def stream(self, request: Any, *, ctx: Any = None) -> Any:
        return iter([f"{request}-1", f"{request}-2", f"{request}-3"])

    @property
    def details(self) -> dict[str, Any]:
        return {"faces": "sync-only"}


class _AsyncOnlyPort:
    """An async-only ChatModel-shaped port (no bare-name faces)."""

    async def achat(self, request: Any, *, ctx: Any = None) -> str:
        return f"async:{request}"

    async def astream(self, request: Any, *, ctx: Any = None) -> Any:
        async def _gen() -> Any:
            for i in (1, 2, 3):
                yield f"{request}-{i}"

        return _gen()

    @property
    def details(self) -> dict[str, Any]:
        return {"faces": "async-only"}


async def test_from_sync_offloads_the_async_faces() -> None:
    port = from_sync(_SyncOnlyPort())

    # The port's own sync faces pass through unchanged.
    assert port.chat("hello") == "sync:hello"
    assert port.details == {"faces": "sync-only"}
    # The synthesized async twins run the blocking call off-loop.
    assert await port.achat("hello") == "sync:hello"
    stream = await port.astream("s")
    assert [item async for item in stream] == ["s-1", "s-2", "s-3"]


def test_wrappers_expose_every_chat_port_face() -> None:
    # Behavioral conformance: every ChatModel face is reachable on both
    # wrappers. (`isinstance` against the runtime_checkable protocol cannot
    # see dynamically synthesized faces — CPython's protocol check uses
    # `inspect.getattr_static` — so presence is asserted structurally.)
    for wrapper in (from_sync(_SyncOnlyPort()), from_async(_AsyncOnlyPort())):
        for face in ("chat", "achat", "stream", "astream"):
            assert callable(getattr(wrapper, face))
        assert isinstance(wrapper.details, dict)


def test_from_async_bridges_through_the_portal() -> None:
    port = from_async(_AsyncOnlyPort())

    # The synthesized blocking faces submit to the portal loop.
    assert port.chat("hello") == "async:hello"
    assert list(port.stream("s")) == ["s-1", "s-2", "s-3"]
    assert port.details == {"faces": "async-only"}


async def test_from_async_own_faces_pass_through() -> None:
    port = from_async(_AsyncOnlyPort())
    assert await port.achat("hi") == "async:hi"


async def test_round_trip_sync_to_async_to_sync() -> None:
    # from_async(from_sync(port)): every face reachable, both ways.
    port = from_async(from_sync(_SyncOnlyPort()))
    assert port.chat("x") == "sync:x"
    assert await port.achat("x") == "sync:x"


def test_missing_faces_raise_attribute_errors() -> None:
    name = "nonexistent"
    with pytest.raises(AttributeError):
        getattr(from_sync(_SyncOnlyPort()), name)
    with pytest.raises(AttributeError):
        getattr(from_async(_AsyncOnlyPort()), name)


# --- (f) Catalog.discover() composes both installed fragments ----------------------


def test_discover_composes_both_installed_fragments() -> None:
    from importlib.metadata import entry_points

    from ocai.convert.catalog import ENTRY_POINT_GROUP
    from ocai.convert.catalog import Catalog
    from ocai.core.identity import CHAT

    # The plugin distributions declare their fragments as entry points…
    names = {ep.name for ep in entry_points(group=ENTRY_POINT_GROUP)}
    assert {"anthropic", "openai"} <= names
    # …and discovery composes them: both providers' nodes AND their chat
    # component factories are reachable in one catalog.
    catalog = Catalog.discover()
    providers = {node.provider for node in catalog.nodes}
    assert {"anthropic", "openai"} <= providers
    assert [c.interface for c in catalog.components_for("openai", CHAT)] == ["chat_completions"]
    assert [c.interface for c in catalog.components_for("anthropic", CHAT)] == ["messages"]


def test_default_catalog_is_the_memoized_discovery() -> None:
    from ocai.convert.catalog import default_catalog

    assert default_catalog() is default_catalog()
    providers = {node.provider for node in default_catalog().nodes}
    assert {"anthropic", "openai"} <= providers
