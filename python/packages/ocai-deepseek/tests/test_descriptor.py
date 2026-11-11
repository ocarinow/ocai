"""WU-44a: installed DeepSeek identity is attributable but cannot execute yet."""

from __future__ import annotations

import json
from importlib.metadata import entry_points
from pathlib import Path

import pytest
import respx

import ocai.anthropic
import ocai.chat
import ocai.deepseek
import ocai.openai
from ocai.convert import Catalog
from ocai.convert.catalog import ENTRY_POINT_GROUP
from ocai.convert.catalog import ResolutionError
from ocai.core import ApiKey
from ocai.core.identity import CHAT
from ocai.core.profile import Support
from ocai.deepseek.chat_completions import descriptor
from ocai.deepseek.chat_completions import wire
from ocai.openai.chat_completions import wire as openai_wire


def test_installed_fragment_preserves_vendor_provenance() -> None:
    entries = list(entry_points(group=ENTRY_POINT_GROUP, name="deepseek"))
    assert len(entries) == 1
    assert entries[0].load() is ocai.deepseek.FRAGMENT
    catalog = Catalog.of(ocai.deepseek.FRAGMENT)
    route = catalog.resolve(CHAT, "deepseek", interface="chat_completions")
    assert route.node == descriptor.CHAT_COMPLETIONS_REQUEST
    lock = catalog.lock()
    assert lock.payload["fragments"][0]["origin"] == "ocai-deepseek==0.1.0"
    assert all(node.provider == "deepseek" for node in catalog.nodes)
    assert len(catalog.nodes) == 3
    assert not ocai.deepseek.FRAGMENT.edges
    assert not ocai.deepseek.FRAGMENT.components
    assert not ocai.deepseek.FRAGMENT.transducers


def test_composition_lock_is_deterministic_and_does_not_inherit_profiles() -> None:
    left = Catalog.of(ocai.openai.FRAGMENT, ocai.deepseek.FRAGMENT, ocai.anthropic.FRAGMENT)
    right = Catalog.of(ocai.anthropic.FRAGMENT, ocai.deepseek.FRAGMENT, ocai.openai.FRAGMENT)
    assert left.lock().hash == right.lock().hash
    assert left.lock().to_json() == right.lock().to_json()
    assert left.lock().hash != Catalog.of(ocai.openai.FRAGMENT, ocai.anthropic.FRAGMENT).lock().hash
    for model in descriptor.MODEL_IDS:
        profile = left.profile("deepseek", "chat_completions", model)
        assert profile and profile.features == {"chat.config.output.json_schema": Support.ABSENT}
    assert left.profile("deepseek", "chat_completions", "unknown-future-model") is None
    assert descriptor.TRAITS.first_party_base_url == "https://api.deepseek.com"
    assert descriptor.TRAITS.vendor == "deepseek"
    assert not descriptor.TRAITS.first_party_headers
    assert not descriptor.TRAITS.version_headers


@pytest.mark.parametrize("model", descriptor.MODEL_IDS)
@pytest.mark.parametrize("tag", [None, descriptor.TAG])
def test_descriptor_only_interface_cannot_reach_provider_io(model: str, tag: str | None) -> None:
    catalog = Catalog.of(ocai.openai.FRAGMENT, ocai.deepseek.FRAGMENT)
    with respx.mock as router:
        with pytest.raises(ResolutionError, match="no chat component"):
            ocai.chat.model(
                "deepseek/" + model,
                interface="chat_completions",
                tag=tag,
                credentials=ApiKey("sk-test"),
                catalog=catalog,
            )
        assert not router.calls


def test_neutral_descriptor_matches_all_nodes_and_shared_wire_types() -> None:
    spec = Path(__file__).resolve().parents[4] / "spec/interfaces/deepseek.chat_completions.json"
    document = json.loads(spec.read_text())
    assert document["provider"] == descriptor.PROVIDER
    assert document["interface"] == descriptor.INTERFACE
    assert document["shapes"] == [str(node.shape) for node in descriptor.NODES]
    for node in descriptor.NODES:
        assert node.released is not None
        assert document["tags"] == [
            {"tag": node.tag, "released": node.released.isoformat(), "status": node.status.value}
        ]
    assert wire.CompletionCreateParams is openai_wire.CompletionCreateParams
    assert wire.ChatCompletion is openai_wire.ChatCompletion
    assert wire.ChatCompletionChunk is openai_wire.ChatCompletionChunk
