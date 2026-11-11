"""WU-38: explicit host data and approved execution over recorded HTTP/SSE."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from typing import Any
from urllib.parse import quote

import httpx
import pytest
import respx

import ocai.chat
import ocai.openai
from ocai.chat.facade import StalePreparationError
from ocai.chat.facade import WireChatModel
from ocai.chat.types import ChatConfig
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import Message
from ocai.chat.types import StreamAccumulator
from ocai.convert import AdmissionError
from ocai.convert import Catalog
from ocai.convert import CatalogBuilder
from ocai.convert import CatalogFragment
from ocai.convert import HostDescriptor
from ocai.convert import ResolutionError
from ocai.core import ApiKey
from ocai.core import NoCredential
from ocai.core.canonjson import semantic_equal
from ocai.core.credentials import Credential
from ocai.core.credentials import CredentialError
from ocai.core.credentials import require_credential
from ocai.core.errors import UnsupportedFeatureError
from ocai.core.identity import Origin
from ocai.core.ir import is_json_array
from ocai.core.ir import is_json_object
from ocai.core.profile import CapabilityProfile
from ocai.core.profile import Support
from ocai.core.traits import DialectTraits
from ocai.openai.chat_completions.codec import CHAT_COMPLETIONS_REQUEST
from ocai.openai.chat_completions.codec import ChatCompletionsCodec
from ocai.runtime.binding import Binding
from ocai.runtime.decisions import Decision
from ocai.runtime.decisions import Outcome
from ocai.runtime.decisions import Proceed
from ocai.runtime.observe import ObserveEvent
from ocai.wire.hosting import Custom
from ocai.wire.hosting import EndpointSpec
from ocai.wire.hosting import Operation
from ocai.wire.http import HttpRequest
from ocai.wire.transport import HttpxTransport

LoadHttp = Callable[[str], dict[str, Any]]
RESOURCE = "vendor/model:fast"


def _semantic(value: Any) -> Any:
    """Apply the existing fold fixture's raw/stream-identity exclusions."""
    if is_json_object(value):
        return {
            key: _semantic(item)
            for key, item in value.items()
            if key not in {"raw", "raw_event", "info"}
        }
    if is_json_array(value):
        return [_semantic(item) for item in value]
    return value


def _host() -> Custom:
    return Custom(
        "https://gateway.example.test",
        {"generative": "/models/{resource}/chat"},
        path_prefix="/proxy",
        streaming_paths={"generative": "/models/{resource}/stream"},
        static_headers={"X-Attribution": "host", "X-Version": "host-version"},
        query={"api-version": "preview", "region": "test region"},
        profile_suffixes=(":fast",),
    )


def _spec(resource: str = RESOURCE, streaming: bool = False) -> EndpointSpec:
    return EndpointSpec(
        CHAT_COMPLETIONS_REQUEST,
        DialectTraits("openai"),
        Operation("chat", "generative", streaming=streaming),
        resource,
        "/v1/chat/completions",
    )


@pytest.mark.parametrize("mode", ["sync", "async", "stream", "astream"])
@pytest.mark.parametrize("auth", ["none", "bearer", "api-key"])
@respx.mock
async def test_recorded_host_matrix(load_http: LoadHttp, mode: str, auth: str) -> None:
    streaming = "stream" in mode
    pair = load_http("custom_host_stream.json" if streaming else "custom_host_unary.json")
    response = pair["response"]
    if streaming:
        wire_response = httpx.Response(
            200,
            headers=response["headers"],
            content=("\n\n".join(response["sse"]) + "\n\n").encode(),
        )
    else:
        wire_response = httpx.Response(200, json=response["json"])
    route = respx.post(pair["request"]["url"]).mock(return_value=wire_response)
    credentials: Credential = (
        NoCredential()
        if auth == "none"
        else ApiKey("test-secret", header="api-key", scheme="")
        if auth == "api-key"
        else ApiKey("test-secret")
    )
    retained: list[HttpRequest] = []
    observations: list[ObserveEvent] = []

    class Record:
        def on_request(self, request: HttpRequest) -> Decision:
            retained.append(request)
            return Proceed()

        def on_outcome(self, outcome: Outcome) -> Decision:
            retained.append(outcome.request)
            return Proceed()

    class Observe:
        def on_event(self, event: ObserveEvent) -> None:
            observations.append(event)

    transport = HttpxTransport(provider="openai")
    model = WireChatModel(
        ChatCompletionsCodec(),
        Binding(
            _host(),
            credentials,
            transport,
            extra_headers={"x-attribution": "binding"},
        ),
        Catalog.of(ocai.openai.FRAGMENT),
        model_name=RESOURCE,
        policies=[Record()],
        attempt_observers=[Observe()],
    )
    request = ChatRequest(messages=[Message.user("Hello!")])
    try:
        if mode == "sync":
            value = model.chat(request).value
        elif mode == "async":
            value = (await model.achat(request)).value
        elif mode == "stream":
            with model.stream(request) as stream:
                value = StreamAccumulator.fold(list(stream))
                assert stream.end and stream.end.usage
        else:
            async with await model.astream(request) as astream:
                value = StreamAccumulator.fold([chunk async for chunk in astream])
                assert astream.end and astream.end.usage
        assert value.message.text == "Hello! How can I help you today?"
        assert value.usage and value.usage.output_tokens == 9
        expected = (
            ChatCompletionsCodec()
            .decode_response(load_http("custom_host_unary.json")["response"]["json"])
            .value
        )
        assert isinstance(expected, ChatResponse)
        assert semantic_equal(_semantic(value.to_dict()), _semantic(expected.to_dict()))
        sent = route.calls.last.request
        assert json.loads(sent.content) == pair["request"]["json"]
        assert sent.headers["x-attribution"] == "binding"
        assert sent.headers["x-version"] == "host-version"
        assert sent.headers.get("authorization") == (
            "Bearer test-secret" if auth == "bearer" else None
        )
        assert sent.headers.get("api-key") == ("test-secret" if auth == "api-key" else None)
        assert retained and observations
        assert "test-secret" not in repr(retained) + repr(observations)
        assert all(
            "authorization" not in {key.lower() for key in req.headers}
            and "api-key" not in {key.lower() for key in req.headers}
            for req in retained
        )
    finally:
        transport.close()
        await transport.aclose()


@respx.mock
async def test_recorded_arn_stays_one_segment_and_body_is_verbatim(load_http: LoadHttp) -> None:
    pair = load_http("custom_host_arn.json")
    resource = pair["request"]["json"]["model"]
    route = respx.post(pair["request"]["url"]).mock(
        return_value=httpx.Response(
            200,
            json=pair["response"]["json"],
        )
    )
    transport = HttpxTransport(provider="openai")
    model = WireChatModel(
        ChatCompletionsCodec(),
        Binding(_host(), NoCredential(), transport),
        Catalog.of(ocai.openai.FRAGMENT),
        model_name=resource,
    )
    try:
        await model.achat(ChatRequest(messages=[Message.user("Hello!")]))
        sent = route.calls.last.request
        assert json.loads(sent.content)["model"] == resource
        assert quote(resource, safe="").encode() in sent.url.raw_path
    finally:
        await transport.aclose()


def test_legacy_defaults_and_non_interpreted_resource() -> None:
    assert Custom("https://example.test").endpoint(_spec()) == (
        "https://example.test/v1/chat/completions"
    )
    assert Custom("https://example.test/base/", {"generative": "/chat/"}).endpoint(_spec()) == (
        "https://example.test/base/chat/"
    )
    host = _host()
    for resource in ("..", "a/b?x=y#z", "x%2Fy", "a{resource}"):
        endpoint = host.endpoint(_spec(resource))
        assert endpoint.startswith("https://gateway.example.test/proxy/models/")
        assert endpoint.count("?") == 1
        assert "#" not in endpoint
    assert "%2E%2E/chat" in host.endpoint(_spec(".."))
    assert host.profile_key(RESOURCE) == "vendor/model"
    assert host.profile_key("vendor/model:unknown") == "vendor/model:unknown"
    assert replace(host, profile_aliases={RESOURCE: "explicit"}).profile_key(RESOURCE) == "explicit"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"base_url": "https://user:secret@example.test"},
        {"base_url": "https://example.test?key=secret"},
        {"path_prefix": "//evil.test"},
        {"paths": {"generative": "/model/{resource.__class__}"}},
        {"paths": {"generative": "/model/{resource!r}"}},
        {"paths": {"generative": "/../path"}},
        {"query": {"api_key": "secret"}},
        {"static_headers": {"Authorization": "secret"}},
        {"static_headers": {"x-id": "one", "X-ID": "two"}},
    ],
)
def test_invalid_host_declarations_fail_before_io(kwargs: dict[str, Any]) -> None:
    options: dict[str, Any] = {"base_url": "https://example.test"}
    options.update(kwargs)
    with pytest.raises(ValueError):
        Custom(**options)


def test_catalog_hosts_are_detached_locked_and_conflict_checked() -> None:
    descriptor = HostDescriptor("https://example.test", path_prefix="/proxy", query={"v": "1"})
    fragment = CatalogFragment(Origin("test-host", "1"), hosts={"test": descriptor})
    builder = CatalogBuilder().add(fragment)
    assert isinstance(descriptor.query, dict)
    descriptor.query["v"] = "changed"
    catalog = builder.build()
    before = catalog.lock()
    detached = catalog.host("test")
    assert detached.query == {"v": "1"}
    assert isinstance(detached.query, dict)
    detached.query.clear()
    assert catalog.host("test").query == {"v": "1"}
    assert catalog.lock() == before
    assert before.hash != Catalog.of(fragment).lock().hash
    with pytest.raises(AdmissionError, match="conflicting host"):
        builder.add(fragment)
    assert builder.build().lock() == before
    with pytest.raises(ResolutionError):
        catalog.host("missing")
    empty = Catalog.of(CatalogFragment(Origin("test-host", "1"))).lock().payload
    assert "hosts" not in empty["fragments"][0]


async def test_named_catalog_host_and_profile_coverage() -> None:
    fragment = CatalogFragment(
        Origin("test-host", "1"),
        hosts={"local": _host()},
        profiles=(
            CapabilityProfile(
                "openai",
                "chat_completions",
                "vendor/model",
                {"chat.config.temperature": Support.ABSENT},
            ),
        ),
    )
    catalog = Catalog.of(ocai.openai.FRAGMENT, fragment)
    transport = HttpxTransport(provider="openai")
    model = ocai.chat.model(
        f"openai/{RESOURCE}",
        credentials=NoCredential(),
        host="local",
        catalog=catalog,
        transport=transport,
    )
    try:
        request = ChatRequest(messages=[], config=ChatConfig(temperature=0.2))
        inspected_absent = model.prepare(request)
        assert inspected_absent.inspection.coverage[0].support == Support.ABSENT
        strict_model = WireChatModel(
            ChatCompletionsCodec(),
            Binding(Custom.from_descriptor(catalog.host("local")), NoCredential(), transport),
            catalog,
            model_name=RESOURCE,
            strict=True,
        )
        with pytest.raises(UnsupportedFeatureError):
            strict_model.prepare(request)
        unknown = ocai.chat.model(
            "openai/unknown",
            credentials=NoCredential(),
            host="local",
            catalog=catalog,
            transport=transport,
        )
        inspected = unknown.prepare(
            ChatRequest(messages=[], config=ChatConfig(max_output_tokens=10))
        )
        assert not inspected.inspection.coverage_complete
        assert inspected.inspection.coverage[0].support is None
    finally:
        await transport.aclose()


@pytest.mark.parametrize("field", ["query", "static_headers", "paths", "profile_aliases"])
async def test_mutated_host_configuration_requires_new_approval(field: str) -> None:
    host = _host()
    transport = HttpxTransport(provider="openai")
    model = WireChatModel(
        ChatCompletionsCodec(),
        Binding(host, NoCredential(), transport),
        Catalog.of(ocai.openai.FRAGMENT),
        model_name=RESOURCE,
    )
    prepared = model.prepare(ChatRequest(messages=[]))
    changes = {
        "query": ("api-version", "changed"),
        "static_headers": ("X-Version", "changed"),
        "paths": ("generative", "/changed"),
        "profile_aliases": (RESOURCE, "other"),
    }
    data = getattr(host, field)
    data[changes[field][0]] = changes[field][1]
    try:
        with respx.mock as router:
            with pytest.raises(StalePreparationError):
                await prepared.achat()
            assert not router.calls
    finally:
        await transport.aclose()


def test_caller_maps_are_snapshots_and_missing_credentials_still_fail() -> None:
    paths = {"generative": "/old"}
    headers = {"X-Attribution": "old"}
    host = Custom("https://example.test", paths, static_headers=headers)
    transport = HttpxTransport(provider="openai")
    binding = Binding(host, NoCredential(), transport, extra_headers=headers)
    paths.clear()
    headers.clear()
    assert host.paths == {"generative": "/old"}
    assert host.static_headers == binding.extra_headers == {"X-Attribution": "old"}
    request = HttpRequest.from_json("POST", "https://example.test", {})
    before = dict(request.headers)
    NoCredential().apply(request)
    assert request.headers == before
    with pytest.raises(CredentialError):
        require_credential(None)
    with pytest.raises(ValueError, match="Credential"):
        Binding(host, NoCredential(), transport, extra_headers={"api-key": "secret"})
    transport.close()
