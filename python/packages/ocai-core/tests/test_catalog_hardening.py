"""Composition failures, reproducible plans, and declaration fingerprints."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from functools import partial
from itertools import permutations
from typing import Any

import pytest

from ocai.chat import model
from ocai.convert import AdmissionError
from ocai.convert import Catalog
from ocai.convert import CatalogBuilder
from ocai.convert import CatalogFragment
from ocai.convert import Component
from ocai.convert import ConformanceResources
from ocai.convert import ConversionGraph
from ocai.convert import DeclaredDisposition
from ocai.convert import Edge
from ocai.convert import EdgeContract
from ocai.convert import EdgeOutput
from ocai.convert import ResolutionError
from ocai.convert import StreamEdge
from ocai.core import ApiKey
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import EdgeReport
from ocai.core.fidelity import SemanticShift
from ocai.core.identity import CHAT
from ocai.core.identity import CHAT_CHUNK
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import NodeId
from ocai.core.identity import Origin
from ocai.core.identity import canonical_node
from ocai.core.profile import CapabilityProfile
from ocai.core.profile import Support
from ocai.core.traits import DialectTraits

ORIGIN = Origin("ocai-test", "1")
HUB = canonical_node(CHAT_REQUEST)
A = NodeId("test", "chat", "a", CHAT_REQUEST, date(2026, 1, 1))
B = replace(A, tag="b")
C = replace(A, tag="c")


def identity(payload: Any) -> EdgeOutput:
    return EdgeOutput(payload)


def edge(src: NodeId = A, dst: NodeId = HUB) -> Edge:
    return Edge(src, dst, identity, EdgeContract(), ORIGIN)


def fragment(*edges: Edge, **kwargs: Any) -> CatalogFragment:
    return CatalogFragment(origin=ORIGIN, nodes=(A, B, C), edges=edges or (edge(),), **kwargs)


class PassThrough:
    def __init__(self, src: NodeId, dst: NodeId) -> None:
        self.src, self.dst = src, dst

    def feed(self, event: Any) -> list[Any]:
        return [event]

    def flush(self) -> tuple[list[Any], EdgeReport]:
        return [], EdgeReport(self.src, self.dst)


def stream_edge(src: NodeId, dst: NodeId) -> StreamEdge:
    return StreamEdge(src, dst, partial(PassThrough, src, dst), EdgeContract(), ORIGIN)


def _register(graph: ConversionGraph, conversion: Edge | StreamEdge) -> None:
    if isinstance(conversion, StreamEdge):
        graph.register_stream(conversion)
    else:
        graph.register(conversion)


def changed(payload: Any) -> EdgeOutput:
    return EdgeOutput({"changed": payload})


@pytest.mark.parametrize("stream", [False, True])
def test_conflicting_edges_fail_without_poisoning_an_existing_graph(stream: bool) -> None:
    graph = ConversionGraph()
    original = stream_edge(A, HUB) if stream else edge()
    _register(graph, original)
    _register(graph, original)
    with pytest.raises(ValueError, match="conflicting"):
        _register(graph, replace(original, note="competing declaration"))
    if stream:
        assert graph.stream_converter(A, HUB).feed("kept") == ["kept"]
    else:
        assert graph.convert("kept", A, HUB).value == "kept"


@pytest.mark.parametrize("stream", [False, True])
def test_same_endpoints_with_different_callable_are_not_idempotent(stream: bool) -> None:
    original = stream_edge(A, HUB) if stream else edge()
    other = (
        replace(original, factory=lambda: PassThrough(A, HUB))
        if stream
        else replace(original, fn=changed)
    )
    graph = ConversionGraph()
    _register(graph, original)
    with pytest.raises(ValueError, match="conflicting"):
        _register(graph, other)


def test_graph_and_catalog_reject_conflicting_node_metadata() -> None:
    changed = replace(A, released=date(2026, 2, 1))
    graph = ConversionGraph()
    graph.register(edge())
    with pytest.raises(ValueError, match="node metadata"):
        graph.register(edge(changed))
    with pytest.raises(AdmissionError, match="node metadata"):
        Catalog.of(fragment(), CatalogFragment(ORIGIN, nodes=(changed,)))


def test_graph_enforces_one_shape_even_for_disjoint_pairs() -> None:
    graph = ConversionGraph()
    graph.register(edge())
    with pytest.raises(ValueError, match="shapes"):
        graph.register_stream(stream_edge(replace(A, shape=CHAT_CHUNK), canonical_node(CHAT_CHUNK)))


def test_builder_rejects_competing_edge_and_remains_reusable() -> None:
    builder = CatalogBuilder().add(fragment())
    with pytest.raises(AdmissionError, match="conflicting conversion edge"):
        builder.add(fragment(replace(edge(), fn=changed)))
    assert builder.build().convert("kept", A, HUB).value == "kept"


def test_canonical_privilege_requires_the_canonical_interface() -> None:
    spoof = replace(HUB, interface="foreign")
    with pytest.raises(AdmissionError):
        Catalog.of(fragment(edge(A, spoof)))


@pytest.mark.parametrize("stream", [False, True])
def test_equal_cost_diamond_is_independent_of_registration_order(stream: bool) -> None:
    edges = (
        [stream_edge(A, B), stream_edge(B, HUB), stream_edge(A, C), stream_edge(C, HUB)]
        if stream
        else [edge(A, B), edge(B, HUB), edge(A, C), edge(C, HUB)]
    )
    for order in permutations(edges):
        graph = ConversionGraph()
        for item in order:
            _register(graph, item)
        if stream:
            assert [e.dst for e in graph.stream_converter(A, HUB).edges] == [B, HUB]
        else:
            assert graph.convert({}, A, HUB).report.path == [A, B, HUB]


def test_catalog_order_does_not_change_plan_or_lock() -> None:
    one = fragment(edge(A, B), edge(B, HUB))
    two = fragment(edge(A, C), edge(C, HUB))
    forward, reverse = Catalog.of(one, two), Catalog.of(two, one)
    assert forward.lock().hash == reverse.lock().hash
    assert forward.convert({}, A, HUB).report.path == reverse.convert({}, A, HUB).report.path


def test_unpinned_sibling_interfaces_are_ambiguous_even_with_matching_tag() -> None:
    newer = replace(A, interface="responses", released=date(2026, 9, 1))
    catalog = Catalog.of(CatalogFragment(ORIGIN, nodes=(A, newer)))
    for tag in (None, A.tag):
        with pytest.raises(ResolutionError, match="pass interface="):
            catalog.resolve(CHAT, "test", tag=tag)
    assert catalog.resolve(CHAT, "test", interface="chat").node == A
    assert catalog.resolve(CHAT, "test", interface="responses").node == newer


def test_front_door_uses_the_same_explicit_interface_rule() -> None:
    newer = replace(A, interface="responses", released=date(2026, 9, 1))

    def must_not_run() -> Any:
        raise AssertionError("ambiguity must fail before codec construction")

    catalog = Catalog.of(
        CatalogFragment(
            ORIGIN,
            nodes=(A, newer),
            components=(
                Component("test", "chat", CHAT, must_not_run),
                Component("test", "responses", CHAT, must_not_run),
            ),
        )
    )
    with pytest.raises(ResolutionError, match="ambiguous serveable"):
        model("test/model", credentials=ApiKey("test"), catalog=catalog)


def test_profile_conflicts_fail_and_equal_specificity_ties_are_stable() -> None:
    first = CapabilityProfile("test", "chat", "m*", {"feature": Support.NATIVE})
    second = CapabilityProfile("test", "chat", "m?", {"feature": Support.ABSENT})
    a, b = fragment(profiles=(first,)), fragment(profiles=(second,))
    assert Catalog.of(a, b).profile("test", "chat", "m1") == Catalog.of(b, a).profile(
        "test", "chat", "m1"
    )
    with pytest.raises(AdmissionError, match="conflicting capability profile"):
        Catalog.of(a, fragment(profiles=(replace(first, features={"feature": Support.ABSENT}),)))


def test_lock_tracks_full_declarations_but_not_callable_implementation() -> None:
    loss = DeclaredDisposition(Disposition.DROPPED)
    first = replace(edge(), contract=EdgeContract(census={"x": loss}))
    second = replace(first, contract=EdgeContract(census={"y": loss}))
    assert first.contract.loss_grade() == second.contract.loss_grade()
    assert Catalog.of(fragment(first)).lock().hash != Catalog.of(fragment(second)).lock().hash
    third = replace(
        first,
        contract=replace(first.contract, semantic_shifts=(SemanticShift("test.relocation", "x"),)),
    )
    assert Catalog.of(fragment(first)).lock().hash != Catalog.of(fragment(third)).lock().hash
    altered_code = replace(first, fn=changed)
    assert Catalog.of(fragment(first)).lock().hash == Catalog.of(fragment(altered_code)).lock().hash


def test_lock_includes_traits_and_conformance_manifest() -> None:
    plain = fragment()
    with_traits = replace(
        plain, traits=(DialectTraits("test", first_party_base_url="https://example.com"),)
    )
    with_resources = replace(plain, conformance=ConformanceResources("test.resources"))
    assert len({Catalog.of(f).lock().hash for f in (plain, with_traits, with_resources)}) == 3


def test_caller_mutation_cannot_change_catalog_or_cached_fingerprint() -> None:
    census: dict[str, DeclaredDisposition] = {}
    features = {"feature": Support.NATIVE}
    original = fragment(
        replace(edge(), contract=EdgeContract(census=census)),
        profiles=(CapabilityProfile("test", "chat", "*", features),),
    )
    builder = CatalogBuilder().add(original)
    census["x"] = DeclaredDisposition(Disposition.DROPPED)
    features["feature"] = Support.ABSENT
    catalog = builder.build()
    before = catalog.lock().hash
    profile = catalog.profile("test", "chat", "model")
    assert profile is not None
    assert profile.features["feature"] is Support.NATIVE
    profile.features.clear()
    detached_census = catalog.fragments[0].edges[0].contract.census
    assert isinstance(detached_census, dict)
    detached_census.clear()
    catalog.lock().payload.clear()
    assert catalog.lock().hash == before
    assert catalog.lock().payload["format"] == "ocai.catalog-lock/2"
    preserved = catalog.profile("test", "chat", "model")
    assert preserved is not None
    assert preserved.features["feature"] is Support.NATIVE


def test_node_profile_and_component_keys_keep_their_distinct_domains() -> None:
    profile = CapabilityProfile("test", "chat", "*", {"feature": Support.NATIVE})
    component = Component("test", "chat", CHAT, identity)
    definition = fragment(profiles=(profile,), components=(component,))
    catalog = Catalog.of(definition, definition)
    assert catalog.nodes == (A, B, C)
    assert catalog.profile("test", "chat", "model") == profile
    assert catalog.component("test", "chat", CHAT) is identity
    conflicting = replace(definition, components=(replace(component, factory=changed),))
    with pytest.raises(AdmissionError, match="component"):
        Catalog.of(definition, conflicting)
