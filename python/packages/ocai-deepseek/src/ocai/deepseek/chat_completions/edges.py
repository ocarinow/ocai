"""Independently censused DeepSeek unary edges; no serving or stream registration."""

from ocai.convert.contract import DeclaredDisposition
from ocai.convert.contract import EdgeContract
from ocai.convert.graph import Edge
from ocai.convert.graph import StreamEdge
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import SemanticShift
from ocai.core.identity import CHAT_CHUNK
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import CHAT_RESPONSE
from ocai.core.identity import canonical_node
from ocai.deepseek.chat_completions.codec import DeepSeekCodec
from ocai.deepseek.chat_completions.descriptor import CHAT_COMPLETIONS_CHUNK
from ocai.deepseek.chat_completions.descriptor import CHAT_COMPLETIONS_REQUEST
from ocai.deepseek.chat_completions.descriptor import CHAT_COMPLETIONS_RESPONSE
from ocai.deepseek.chat_completions.descriptor import ORIGIN
from ocai.deepseek.chat_completions.streaming import DeepSeekStreamTransducer

_CODEC = DeepSeekCodec()

ENCODE_REQUEST_CONTRACT = EdgeContract(
    census={
        **{
            f"{path}.{lane}": DeclaredDisposition(Disposition.UNSUPPORTED)
            for path in (
                "config",
                "config.reasoning",
                "config.output",
                "config.audio",
                "config.cache",
                "messages[]",
                "messages[].parts[]",
                "messages[].parts[].parts[]",
                "messages[].parts[].annotations[]",
                "tools[]",
                "tool_choice",
            )
            for lane in ("extensions[]", "provider_options[deepseek.chat_completions]")
        },
        "messages[].role": DeclaredDisposition(Disposition.EXACT),
        "messages[].parts[text]": DeclaredDisposition(Disposition.EXACT),
        "messages[].parts[tool_call]": DeclaredDisposition(Disposition.EXACT),
        "messages[].parts[reasoning]": DeclaredDisposition(
            Disposition.UNSUPPORTED,
            "required history must be present; plain text replay otherwise maps exactly",
        ),
        "messages[].parts[]": DeclaredDisposition(
            Disposition.DROPPED, "media, server tools and unqualified parts have no mapped lane"
        ),
        "config.stop_sequences": DeclaredDisposition(Disposition.RENAMED),
        "messages[].parts[].text": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].parts[].annotations": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].parts[].anchor": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].parts[].signature": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].parts[].opaque": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].parts[].source": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].parts[].annotations[].opaque": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].parts[].is_error": DeclaredDisposition(Disposition.DROPPED),
        "messages[].parts[].parts[]": DeclaredDisposition(Disposition.DROPPED),
        "messages": DeclaredDisposition(Disposition.UNSUPPORTED),
        "tools": DeclaredDisposition(Disposition.EXACT),
        "tools[]": DeclaredDisposition(Disposition.UNSUPPORTED),
        "tool_choice": DeclaredDisposition(Disposition.UNSUPPORTED),
        "anchors[]": DeclaredDisposition(Disposition.UNSUPPORTED),
        "extensions[]": DeclaredDisposition(Disposition.DROPPED),
        "extensions[ocai.request_unparsed_anchors]": DeclaredDisposition(Disposition.UNSUPPORTED),
        "config.temperature": DeclaredDisposition(Disposition.APPROXIMATED),
        "config.top_p": DeclaredDisposition(Disposition.UNSUPPORTED),
        "config.seed": DeclaredDisposition(Disposition.UNSUPPORTED),
        "config.frequency_penalty": DeclaredDisposition(Disposition.EXACT),
        "config.presence_penalty": DeclaredDisposition(Disposition.EXACT),
        "config.parallel_tool_calls": DeclaredDisposition(Disposition.UNSUPPORTED),
        "config.max_output_tokens": DeclaredDisposition(Disposition.APPROXIMATED),
        "config.reasoning.budget_tokens": DeclaredDisposition(Disposition.UNSUPPORTED),
        "config.reasoning.include_thoughts": DeclaredDisposition(Disposition.UNSUPPORTED),
        "messages[].parts[refusal]": DeclaredDisposition(Disposition.UNSUPPORTED),
        "provider_options[deepseek.chat_completions].tools": DeclaredDisposition(
            Disposition.UNSUPPORTED
        ),
        "config.reasoning.effort": DeclaredDisposition(Disposition.UNSUPPORTED),
        "config.output": DeclaredDisposition(Disposition.UNSUPPORTED),
        "config.top_k": DeclaredDisposition(Disposition.UNSUPPORTED),
        "config.logprobs": DeclaredDisposition(Disposition.EXACT),
        "config.modalities": DeclaredDisposition(Disposition.DROPPED),
        "config.audio": DeclaredDisposition(Disposition.DROPPED),
        "config.cache": DeclaredDisposition(Disposition.DROPPED),
        **{
            f"provider_options[deepseek.chat_completions].{key}": DeclaredDisposition(
                Disposition.UNSUPPORTED
            )
            for key in (
                "thinking",
                "reasoning_effort",
                "top_p",
                "seed",
                "parallel_tool_calls",
                "max_completion_tokens",
                "n",
                "tool_choice",
                "response_format",
            )
        },
        "provider_options[deepseek.chat_completions].max_tokens": DeclaredDisposition(
            Disposition.APPROXIMATED
        ),
        (
            "provider_options[deepseek.chat_completions].messages[].reasoning_content"
        ): DeclaredDisposition(Disposition.UNSUPPORTED),
    },
    semantic_shifts=(
        *(
            SemanticShift(
                kind="deepseek.thinking_override",
                path=path,
                note="thinking selector overrides effort",
            )
            for path in (
                "config.reasoning.effort",
                "provider_options[deepseek.chat_completions].reasoning_effort",
            )
        ),
        SemanticShift(
            kind="relocation",
            path="messages[].parts[]",
            note="tool results relocate into sibling tool messages",
        ),
        *(
            SemanticShift(
                kind="deepseek.ignored_parameter",
                path=path,
                note="provider accepts but ignores the supplied parameter",
            )
            for key in ("temperature", "frequency_penalty", "presence_penalty")
            for path in (f"config.{key}", f"provider_options[deepseek.chat_completions].{key}")
        ),
        *(
            SemanticShift(
                kind="deepseek.effort_alias",
                path=path,
                note="provider interprets an effort alias; supplied value stays verbatim",
            )
            for path in (
                "config.reasoning.effort",
                "provider_options[deepseek.chat_completions].reasoning_effort",
            )
        ),
        SemanticShift(
            kind="deepseek.reasoning_ignored",
            path="messages[].parts[reasoning]",
            note="provider ignores reasoning replay without tools",
        ),
        SemanticShift(
            kind="deepseek.reasoning_ignored",
            path="provider_options[deepseek.chat_completions].messages[].reasoning_content",
            note="provider ignores reasoning replay without tools",
        ),
        SemanticShift(
            kind="deepseek.reasoning_concatenated",
            path="messages[].parts[reasoning]",
            note="multiple reasoning parts concatenate into the native text lane",
        ),
    ),
    note="canonical request to independently qualified DeepSeek compatible wire",
)
DECODE_REQUEST_CONTRACT = EdgeContract(
    census={
        "model": DeclaredDisposition(Disposition.EXTENSIONS),
        "unmapped": DeclaredDisposition(Disposition.EXTENSIONS),
        "tools[]": DeclaredDisposition(Disposition.EXTENSIONS),
        "tool_choice": DeclaredDisposition(Disposition.EXTENSIONS),
        "response_format": DeclaredDisposition(Disposition.EXTENSIONS),
        "messages[].content[]": DeclaredDisposition(Disposition.EXTENSIONS),
        "n": DeclaredDisposition(Disposition.UNSUPPORTED),
    },
    semantic_shifts=(
        SemanticShift(
            kind="relocation",
            path="messages[]",
            note="native tool message rethreads into a canonical tool turn",
        ),
    ),
    note="DeepSeek request audit with exact native reasoning and unknown evidence",
)
DECODE_RESPONSE_CONTRACT = EdgeContract(
    census={
        "system_fingerprint": DeclaredDisposition(Disposition.EXTENSIONS),
        "choices[0].message.content": DeclaredDisposition(Disposition.EXACT),
        "choices[0].message.reasoning_content": DeclaredDisposition(Disposition.EXACT),
        "choices[0].message.tool_calls[]": DeclaredDisposition(Disposition.EXACT),
        "choices[0].finish_reason": DeclaredDisposition(Disposition.EXACT),
        "choices[0].logprobs": DeclaredDisposition(Disposition.EXTENSIONS),
        "unmapped": DeclaredDisposition(Disposition.EXTENSIONS),
        "usage": DeclaredDisposition(
            Disposition.EXTENSIONS,
            "known disjoint counters map exactly; uncertain measurements remain evidence",
        ),
        "id": DeclaredDisposition(Disposition.EXACT),
        "model": DeclaredDisposition(Disposition.EXACT),
        "created": DeclaredDisposition(Disposition.RENAMED),
    },
    note="DeepSeek response to canonical text, reasoning, tools and measured usage",
)
EDGES = (
    Edge(
        canonical_node(CHAT_REQUEST),
        CHAT_COMPLETIONS_REQUEST,
        _CODEC.encode_request,
        ENCODE_REQUEST_CONTRACT,
        ORIGIN,
    ),
    Edge(
        CHAT_COMPLETIONS_REQUEST,
        canonical_node(CHAT_REQUEST),
        _CODEC.decode_request,
        DECODE_REQUEST_CONTRACT,
        ORIGIN,
    ),
    Edge(
        CHAT_COMPLETIONS_RESPONSE,
        canonical_node(CHAT_RESPONSE),
        _CODEC.decode_response,
        DECODE_RESPONSE_CONTRACT,
        ORIGIN,
    ),
)


DECODE_CHUNK_CONTRACT = EdgeContract(
    census={
        "id": DeclaredDisposition(Disposition.EXACT),
        "model": DeclaredDisposition(Disposition.EXACT),
        "created": DeclaredDisposition(Disposition.RENAMED),
        "system_fingerprint": DeclaredDisposition(Disposition.EXTENSIONS),
        "response_info": DeclaredDisposition(Disposition.EXTENSIONS),
        "choices[0].delta.reasoning_content": DeclaredDisposition(Disposition.EXACT),
        "choices[0].delta.content": DeclaredDisposition(Disposition.EXACT),
        "choices[0].delta.tool_calls[]": DeclaredDisposition(Disposition.EXACT),
        "choices[0].finish_reason": DeclaredDisposition(Disposition.EXACT),
        "usage": DeclaredDisposition(Disposition.EXTENSIONS),
        "unmapped": DeclaredDisposition(Disposition.EXTENSIONS),
        "frame": DeclaredDisposition(Disposition.EXTENSIONS),
        "termination": DeclaredDisposition(Disposition.UNSUPPORTED),
        "tool_order": DeclaredDisposition(Disposition.UNSUPPORTED),
    },
    note="DeepSeek reasoning, tools and final-choice usage with incomplete evidence",
)
TRANSDUCERS = (StreamEdge(CHAT_COMPLETIONS_CHUNK, canonical_node(CHAT_CHUNK),
                          DeepSeekStreamTransducer, DECODE_CHUNK_CONTRACT, ORIGIN),)
