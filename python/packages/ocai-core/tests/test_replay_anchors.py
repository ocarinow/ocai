"""WU-42: replay carriers preserve evidence and governed failures precede I/O."""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import respx

import ocai.anthropic
import ocai.chat
from ocai.chat.types import ChatChunk
from ocai.chat.types import ChatConfig
from ocai.chat.types import ChatRequest
from ocai.chat.types import ChatResponse
from ocai.chat.types import Message
from ocai.chat.types import PartReasoning
from ocai.chat.types import PartText
from ocai.chat.types import StreamAccumulator
from ocai.convert import Catalog
from ocai.core import ApiKey
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import FidelityPolicy
from ocai.core.fidelity import FidelityPolicyError
from ocai.core.refs import ProviderRef
from ocai.core.refs import Replay
from ocai.wire.transport import HttpxTransport

type LoadHttp = Callable[[str], dict[str, Any]]


def test_server_tool_transcript_and_continuation_preserve_opaque_bytes(spec_dir: Path) -> None:
    fixture = json.loads((spec_dir / "fixtures/canonical/replay_transcript.json").read_text())
    response = ChatResponse.from_dict(fixture["history"][0]["document"])
    request = ChatRequest.from_dict(fixture["document"])
    assert request.to_dict() == fixture["document"]
    assert response.to_dict() == fixture["history"][0]["document"]
    assert request.messages[0] == response.message
    assert request.anchors and request.anchors[0].replay is Replay.REQUIRED
    replayed = ChatRequest.from_dict(json.loads(json.dumps(request.to_dict())))
    assert replayed.to_dict() == request.to_dict()
    assert replayed.messages[0].parts[0].anchor == response.message.parts[0].anchor
    text = replayed.messages[0].parts[1]
    assert isinstance(text, PartText)
    assert text.annotations[0].opaque and text.annotations[0].opaque.id == "citation-test+/=="


@pytest.mark.parametrize(
    "raw",
    [
        None,
        7,
        "future",
        [],
        {"replay": "future"},
        {"provider": "p", "interface": "i", "kind": "k", "id": "v", "future": 1},
    ],
)
def test_unparsed_anchor_entries_keep_verbatim_evidence(raw: Any) -> None:
    request = ChatRequest.from_dict({"messages": [], "anchors": [raw]})
    assert request.anchors is None
    assert request.extensions["ocai.request_unparsed_anchors"] == [{"index": 0, "value": raw}]
    assert ChatRequest.from_dict(request.to_dict()).to_dict() == request.to_dict()


@pytest.mark.parametrize("mode", ["sync", "async", "stream", "astream"])
@pytest.mark.parametrize(
    "case", ["missing", "foreign", "sibling", "model", "empty", "kind", "request", "unparsed"]
)
async def test_replay_denial_prevents_all_provider_attempts(mode: str, case: str) -> None:
    transport = HttpxTransport(provider="anthropic")
    model = ocai.chat.model(
        "anthropic/claude-opus-4-6",
        credentials=ApiKey("sk-test"),
        transport=transport,
        catalog=Catalog.of(ocai.anthropic.FRAGMENT),
        conversion_policy=FidelityPolicy(
            forbidden_dispositions=frozenset({Disposition.UNSUPPORTED})
        ),
    )
    ref = ProviderRef("anthropic", "messages", "thought_signature", "opaque-test", Replay.REQUIRED)
    if case == "foreign":
        ref = replace(ref, provider="openai")
    elif case == "sibling":
        ref = replace(ref, interface="future_messages")
    elif case == "model":
        ref = replace(ref, scope="model", qualifier="other-model")
    elif case == "empty":
        ref = replace(ref, id="")
    elif case == "kind":
        ref = replace(ref, kind="file")
    request = ChatRequest(
        messages=[
            Message(
                role="model",
                parts=[
                    PartReasoning(text="thinking", signature=None if case == "missing" else ref),
                    PartText(text="Answer"),
                ],
            )
        ]
    )
    if case == "request":
        request = ChatRequest(messages=[Message.user("Continue")], anchors=[ref])
    elif case == "unparsed":
        raw = ref.to_dict()
        raw["replay"] = "future_requirement"
        request = ChatRequest.from_dict({"messages": [], "anchors": [raw]})
    before = deepcopy(request.to_dict())
    try:
        prepared = model.prepare(request, streaming="stream" in mode)
        assert prepared.inspection.request_report.edges
        with respx.mock as router:
            with pytest.raises(FidelityPolicyError) as raised:
                if mode == "sync":
                    prepared.chat()
                elif mode == "async":
                    await prepared.achat()
                elif mode == "stream":
                    with prepared.stream() as stream:
                        list(stream)
                else:
                    async with await prepared.astream() as astream:
                        async for _ in astream:
                            pass
            assert not router.calls
        assert raised.value.phase == "request"
        assert request.to_dict() == before
        assert prepared.request.to_dict() == before
    finally:
        transport.close()
        await transport.aclose()


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_recorded_thinking_transcript_replays_exactly_and_folds(
    load_http: LoadHttp,
    asynchronous: bool,
) -> None:
    seed = load_http("anthropic_thinking_seed.json")
    replay = load_http("anthropic_thinking_replay.json")
    streaming = load_http("anthropic_thinking_replay_stream.json")
    transport = HttpxTransport(provider="anthropic")
    model = ocai.chat.model(
        "anthropic/claude-opus-4-6",
        credentials=ApiKey("sk-test"),
        transport=transport,
        catalog=Catalog.of(ocai.anthropic.FRAGMENT),
        conversion_policy=FidelityPolicy(
            forbidden_dispositions=frozenset({Disposition.UNSUPPORTED})
        ),
    )
    first = ChatRequest(
        messages=[Message.user("First question")],
        config=ChatConfig(max_output_tokens=1024),
        provider_options={"anthropic.messages": {"thinking": {"type": "adaptive"}}},
    )
    try:
        with respx.mock as router:
            route = router.post(seed["request"]["url"]).respond(200, json=seed["response"]["json"])
            initial = await model.achat(first) if asynchronous else model.chat(first)
            assert json.loads(route.calls.last.request.content) == seed["request"]["json"]
            second = ChatRequest(
                messages=[first.messages[0], initial.value.message, Message.user("Continue")],
                config=first.config,
                provider_options=first.provider_options,
            )
            second = ChatRequest.from_dict(json.loads(json.dumps(second.to_dict())))
            route.respond(200, json=replay["response"]["json"])
            result = await model.achat(second) if asynchronous else model.chat(second)
            sent = json.loads(route.calls.last.request.content)
            assert sent == replay["request"]["json"]
            assert (
                sent["messages"][1]["content"][0]["signature"]
                == seed["response"]["json"]["content"][0]["signature"]
            )
            route.respond(
                200,
                headers=streaming["response"]["headers"],
                content=("\n\n".join(streaming["response"]["sse"]) + "\n\n").encode(),
            )
            chunks: list[ChatChunk]
            if asynchronous:
                async with await model.astream(second) as astream:
                    chunks = [chunk async for chunk in astream]
                end = astream.end
            else:
                with model.stream(second) as stream:
                    chunks = list(stream)
                end = stream.end
            assert json.loads(route.calls.last.request.content) == streaming["request"]["json"]
            assert end and end.report
            folded = StreamAccumulator.fold(chunks)
            assert folded.message == result.value.message
            assert folded.usage == result.value.usage
            assert folded.finish == result.value.finish
    finally:
        transport.close()
        await transport.aclose()
