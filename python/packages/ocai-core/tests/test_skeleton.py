"""The skeleton's structural contracts, pinned.

Imports every public module of the re-architecture (so a broken import
anywhere fails loudly here), re-asserts the PEP 420 invariant for the new
packages, and pins the load-bearing basics the blueprint freezes:
`CallResult` as the uniform port envelope, `NodeId` as the hashable graph
identity, and the total-decode / omit-absent laws of the IR envelope
(`PART_REGISTRY` falling back to `PartUnknown`, `to_dict` skipping absent
fields, `from_dict` sweeping unknown keys into `extensions`).
"""

from __future__ import annotations

import importlib

import pytest

# Every public module of the rewrite, per architecture §1–§7. A module that
# fails to import is a skeleton regression regardless of its stub status.
MODULES = (
    # ocai.core — the contract layer
    "ocai.core",
    "ocai.core.canonjson",
    "ocai.core.credentials",
    "ocai.core.errors",
    "ocai.core.fidelity",
    "ocai.core.identity",
    "ocai.core.ir",
    "ocai.core.jsonschema",
    "ocai.core.primitives",
    "ocai.core.profile",
    "ocai.core.refs",
    "ocai.core.result",
    "ocai.core.sources",
    # capability contracts
    "ocai.chat",
    "ocai.chat.canonical",
    "ocai.chat.model",
    "ocai.chat.protocol",
    "ocai.chat.types",
    "ocai.embedding",
    "ocai.embedding.protocol",
    "ocai.vectorstore",
    "ocai.vectorstore.protocol",
    # ocai.convert — meaning
    "ocai.convert",
    "ocai.convert.catalog",
    "ocai.convert.conformance",
    "ocai.convert.contract",
    "ocai.convert.graph",
    "ocai.convert.migrate",
    # ocai.runtime — movement
    "ocai.runtime",
    "ocai.runtime.binding",
    "ocai.runtime.decisions",
    "ocai.runtime.drivers",
    "ocai.runtime.dual",
    "ocai.runtime.interceptors",
    "ocai.runtime.observe",
    # ocai.wire — remote transport
    "ocai.wire",
    "ocai.wire.hosting",
    "ocai.wire.http",
    "ocai.wire.policies",
    "ocai.wire.sse",
    "ocai.wire.transport",
    # plugins — one subpackage per interface
    "ocai.openai",
    "ocai.openai.chat_completions",
    "ocai.openai.responses",
    "ocai.anthropic",
    "ocai.anthropic.messages",
)


@pytest.mark.parametrize("module", MODULES)
def test_public_module_imports(module: str) -> None:
    importlib.import_module(module)


def test_new_packages_keep_the_namespace_open() -> None:
    import ocai

    # The root stays a PEP 420 namespace package even with all the new
    # subpackages imported — no distribution collapsed it.
    for module in MODULES:
        importlib.import_module(module)
    assert getattr(ocai, "__file__", None) is None


# --- CallResult: the uniform port envelope (§2.3) ---------------------------


def test_callresult_carries_value_route_report_usage_raw() -> None:
    from ocai.core import CallResult

    result = CallResult(value=42)
    assert result.value == 42
    assert result.route is None  # local in-process adapters resolve nothing
    assert result.report is None
    assert result.usage is None
    assert result.raw is None


# --- NodeId: the graph identity (§2.1) ---------------------------------------


def test_nodeid_is_hashable_identity_with_a_stable_label() -> None:
    from ocai.core import CHAT_REQUEST
    from ocai.core import canonical_node

    node = canonical_node(CHAT_REQUEST)
    assert str(node) == "ocai/ocai@2026-07#chat.request"
    assert node.capability.name == "chat"
    assert {node: "ok"}[canonical_node(CHAT_REQUEST)] == "ok"  # value identity


# --- The IR envelope laws (§2.6, §3.1) ----------------------------------------


def test_message_constructor_sugar_normalizes_to_parts() -> None:
    from ocai.chat.types import Message
    from ocai.chat.types import PartText

    message = Message(role="user", parts="hello")
    assert message.parts == [PartText(text="hello")]
    assert message.text == "hello"  # derived view, never storage


def test_unknown_part_tag_decodes_to_part_unknown() -> None:
    from ocai.chat.types import PART_REGISTRY
    from ocai.chat.types import PartUnknown

    payload = {"type": "holo_message", "hologram": {"px": 7}}
    part = PART_REGISTRY.decode(payload)
    assert isinstance(part, PartUnknown)  # total decode: never raises
    assert part.to_dict() == payload  # preserved verbatim, byte-faithful


def test_to_dict_is_omit_absent() -> None:
    from ocai.chat.types import Message

    data = Message(role="user", parts="hi").to_dict()
    # None-valued and default-empty fields are not emitted...
    assert "extensions" not in data
    assert "provider_options" not in data
    part = data["parts"][0]
    assert "id" not in part and "anchor" not in part and "annotations" not in part
    # ...while set fields are.
    assert part["type"] == "text"
    assert part["text"] == "hi"


def test_from_dict_sweeps_unknown_keys_into_extensions() -> None:
    from ocai.chat.types import Message

    decoded = Message.from_dict(
        {"role": "user", "parts": [{"type": "text", "text": "hi"}], "from_the_future": 1}
    )
    assert decoded.extensions["from_the_future"] == 1  # tolerant, never raises
    assert decoded.text == "hi"
