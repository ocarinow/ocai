"""WU-37: independent host declarations, snapshot integrity and real wire composition."""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from typing import Any

import httpx
import pytest
import respx

import ocai.anthropic
from ocai.anthropic.messages import MESSAGES_REQUEST
from ocai.anthropic.messages import MessagesCodec
from ocai.anthropic.messages.codec import dialect_traits
from ocai.chat import WireChatModel
from ocai.chat.types import ChatRequest
from ocai.chat.types import Message
from ocai.convert import Catalog
from ocai.convert import CatalogBuilder
from ocai.convert import CatalogFragment
from ocai.core.credentials import ApiKey
from ocai.core.identity import Origin
from ocai.core.traits import DialectTraits
from ocai.core.traits import HeaderBodyMapping
from ocai.runtime.binding import Binding
from ocai.wire.hosting import Custom
from ocai.wire.hosting import Direct
from ocai.wire.hosting import EndpointSpec
from ocai.wire.hosting import Operation
from ocai.wire.hosting import Vertex
from ocai.wire.transport import HttpxTransport

LoadHttp = Callable[[str], dict[str, Any]]


def _spec(traits: DialectTraits) -> EndpointSpec:
    return EndpointSpec(
        MESSAGES_REQUEST, traits, Operation("chat", "generative"), "claude-opus-4-6", "/v1/messages"
    )


def _catalog(traits: DialectTraits) -> Catalog:
    return Catalog.of(CatalogFragment(Origin("test-host-traits", "1"), traits=(traits,)))


def test_same_dialect_resolves_independent_host_versions_and_features() -> None:
    traits = replace(dialect_traits(), feature_headers={"Anthropic-Beta": "one, two"})
    spec = _spec(traits)
    original = {"model": "model", "stream": True, "messages": [{"role": "user"}]}
    before = deepcopy(original)
    assert traits.body_fields("bedrock") == {
        "anthropic_version": "bedrock-2023-05-31",
        "anthropic_beta": ["one", "two"],
    }
    assert traits.body_fields("vertex") == {"anthropic_version": "vertex-2023-10-16"}
    assert Vertex("test-project", "us-east5").envelope(spec).wrap(original) == {
        "messages": [{"role": "user"}],
        "anthropic_version": "vertex-2023-10-16",
    }
    assert Vertex("test-project", "us-east5").headers(spec) == {"anthropic-beta": "one, two"}
    expected = {"anthropic-version": "2023-06-01", "anthropic-beta": "one, two"}
    assert Direct("https://example.test").headers(spec) == expected
    assert Custom("https://example.test").headers(spec) == expected
    fields = traits.body_fields("bedrock")
    beta = fields["anthropic_beta"]
    assert isinstance(beta, list)
    beta.append("changed")
    assert traits.body_fields("bedrock")["anthropic_beta"] == ["one", "two"]
    assert original == before
    assert dialect_traits().feature_headers == {}  # No implicit feature opt-in.


def test_legacy_headers_versions_and_vertex_payload_are_preserved() -> None:
    legacy = DialectTraits("test", {"X-Version": "old"}, ("api_version", "legacy"))
    assert legacy.request_headers() == {"X-Version": "old"}
    envelope = Vertex("test-project", "region").envelope(_spec(legacy))
    assert envelope.wrap({"model": "m", "stream": True, "nested": {"x": 1}}) == {
        "api_version": "legacy",
        "nested": {"x": 1},
    }
    assert envelope.wrap({"api_version": "payload"}) == {"api_version": "payload"}
    explicit = replace(
        legacy,
        version_headers={"x-version": "new"},
        host_body_versions={"vertex": ("api_version", "new"), "none": None},
    )
    assert explicit.request_headers() == {"x-version": "new"}
    assert explicit.body_fields("vertex") == {"api_version": "new"}
    assert explicit.body_fields("other") == {"api_version": "legacy"}
    assert explicit.body_fields("none") == {}
    with pytest.raises(ValueError, match="payload conflicts"):
        Vertex("test-project", "region").envelope(_spec(explicit)).wrap({"api_version": "bad"})


def test_vertex_consumes_explicit_feature_body_mapping() -> None:
    traits = DialectTraits(
        "test",
        version_headers={"x-version": "v1"},
        feature_headers={"x-feature": "a,b"},
        host_body_versions={"vertex": ("version", "v2")},
        host_feature_body_mappings={"vertex": (HeaderBodyMapping("x-feature", "flags", ","),)},
    )
    spec = _spec(traits)
    host = Vertex("test-project", "region")
    assert host.envelope(spec).wrap({"model": "m"}) == {"version": "v2", "flags": ["a", "b"]}
    assert host.headers(spec) == {}
    assert replace(traits, feature_headers={}).body_fields("vertex") == {"version": "v2"}
    scalar = replace(
        traits,
        host_feature_body_mappings={
            "vertex": (HeaderBodyMapping("x-feature", "flags"),),
        },
    )
    assert scalar.body_fields("vertex")["flags"] == "a,b"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"feature_headers": {"X-Flag": "a", "x-flag": "b"}},
        {"version_headers": {"X-Flag": "a"}, "feature_headers": {"x-flag": "a"}},
        {
            "version_headers": {"x-version": "v1"},
            "host_feature_body_mappings": {
                "vertex": (HeaderBodyMapping("x-version", "flags"),),
            },
        },
        {
            "host_body_versions": {"vertex": ("version", "v1")},
            "host_feature_body_mappings": {
                "vertex": (HeaderBodyMapping("x-flag", "version"),),
            },
        },
        {
            "host_feature_body_mappings": {
                "vertex": (
                    HeaderBodyMapping("x-flag", "flags"),
                    HeaderBodyMapping("X-Flag", "other"),
                )
            }
        },
        {
            "host_feature_body_mappings": {
                "vertex": (
                    HeaderBodyMapping("x-flag", "flags"),
                    HeaderBodyMapping("x-other", "flags"),
                )
            }
        },
    ],
)
def test_conflicting_declarations_fail_before_io(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        DialectTraits("test", **kwargs)


def test_malformed_feature_lists_are_not_silently_repaired() -> None:
    with pytest.raises(ValueError, match="empty feature item"):
        replace(dialect_traits(), feature_headers={"anthropic-beta": "a,,b"}).body_fields("bedrock")
    with pytest.raises(ValueError, match="separator"):
        HeaderBodyMapping("x-flag", "flags", "")


def test_all_declarations_change_lock_and_order_does_not() -> None:
    base = DialectTraits("test")
    variants = [
        base,
        replace(base, version_headers={"x-version": "v1"}),
        replace(base, feature_headers={"x-flag": "a"}),
        replace(base, host_body_versions={"vertex": ("version", "v1")}),
        replace(base, host_body_versions={"vertex": None}),
        replace(base, host_feature_body_mappings={"vertex": (HeaderBodyMapping("x", "flags"),)}),
        replace(
            base,
            host_feature_body_mappings={
                "vertex": (HeaderBodyMapping("x", "flags", ","),),
            },
        ),
    ]
    assert len({_catalog(traits).lock().hash for traits in variants}) == len(variants)
    first = replace(
        base,
        host_feature_body_mappings={
            "vertex": (
                HeaderBodyMapping("x-b", "b"),
                HeaderBodyMapping("x-a", "a"),
            )
        },
        host_body_versions={"vertex": ("v", "1"), "bedrock": ("v", "2")},
    )
    second = replace(
        first,
        host_feature_body_mappings={
            "vertex": tuple(reversed(first.host_feature_body_mappings["vertex"]))
        },
        host_body_versions={
            "bedrock": ("v", "2"),
            "vertex": ("v", "1"),
        },
    )
    assert _catalog(first).lock().hash == _catalog(second).lock().hash
    # Empty additions do not alter the legacy lock representation.
    assert _catalog(base).lock().payload["fragments"][0]["traits"] == [
        {
            "vendor": "test",
            "first_party_headers": {},
            "cloud_body_version": None,
            "first_party_base_url": None,
        }
    ]


def test_catalog_snapshots_every_trait_mapping_before_and_after_lock() -> None:
    versions: dict[str, tuple[str, str] | None] = {"vertex": ("version", "v1")}
    features = {"x-feature": "original"}
    mappings = {"vertex": (HeaderBodyMapping("x-feature", "flags"),)}
    traits = DialectTraits(
        "test",
        first_party_headers={"legacy": "value"},
        version_headers={"x-version": "v1"},
        feature_headers=features,
        host_body_versions=versions,
        host_feature_body_mappings=mappings,
    )
    fragment = CatalogFragment(Origin("test-host-traits", "1"), traits=(traits,))
    builder = CatalogBuilder().add(fragment)
    versions.clear()
    features.clear()
    mappings.clear()
    assert traits.body_fields("vertex") == {"version": "v1", "flags": "original"}
    assert isinstance(traits.host_body_versions, dict)
    traits.host_body_versions.clear()
    catalog = builder.build()
    assert catalog.fragments[0].traits[0].body_fields("vertex") == {
        "version": "v1",
        "flags": "original",
    }
    before = catalog.lock()
    detached = catalog.fragments[0].traits[0]
    for mapping in (
        detached.first_party_headers,
        detached.version_headers,
        detached.feature_headers,
        detached.host_body_versions,
        detached.host_feature_body_mappings,
    ):
        assert isinstance(mapping, dict)
        mapping.clear()
    assert catalog.lock() == before
    assert catalog.fragments[0].traits[0].body_fields("vertex")["flags"] == "original"
    assert catalog.fragments[0].traits[0].request_headers() == {
        "legacy": "value",
        "x-version": "v1",
        "x-feature": "original",
    }


@pytest.mark.parametrize("async_mode", [False, True])
@respx.mock
async def test_recorded_vertex_version_through_public_facade(
    load_http: LoadHttp,
    async_mode: bool,
) -> None:
    pair = load_http("anthropic_vertex_version.json")
    route = respx.post(pair["request"]["url"]).mock(
        return_value=httpx.Response(
            pair["response"]["status"],
            json=pair["response"]["json"],
        )
    )
    transport = HttpxTransport(provider="anthropic")
    model = WireChatModel(
        MessagesCodec(),
        Binding(
            host=Vertex("test-project", "us-east5"),
            credentials=ApiKey("test-token"),
            transport=transport,
        ),
        Catalog.of(ocai.anthropic.FRAGMENT),
        model_name="claude-opus-4-6",
    )
    request = ChatRequest(
        messages=[
            Message.system("You are concise."),
            Message.user("Hello, who are you?"),
        ]
    )
    try:
        result = await model.achat(request) if async_mode else model.chat(request)
        assert result.value.message.text == "I am Claude, an AI assistant."
        assert route.call_count == 1
        sent = route.calls.last.request
        assert json.loads(sent.content) == pair["request"]["json"]
        assert sent.headers["authorization"] == "Bearer test-token"
        assert "anthropic-version" not in sent.headers
        assert "anthropic-beta" not in sent.headers
    finally:
        await transport.aclose()
        transport.close()
