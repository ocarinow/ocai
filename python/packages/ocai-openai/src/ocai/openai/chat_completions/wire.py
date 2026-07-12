"""Typed OpenAI **Chat Completions** wire models (`POST /v1/chat/completions`).

These `msgspec.Struct`s model OpenAI's chat-completions request, response, and
streaming-chunk shapes — the wire truth of the `openai/chat_completions`
interface. Its graph identity (the request / response / chunk `NodeId`s) lives
in the sibling `ocai.openai.chat_completions.codec` module; this module is the
plugin's **decode boundary** (rule 11): msgspec turns raw JSON into these typed
structs, and the codec maps them to/from the neutral canonical IR. msgspec
lives only here, never in `ocai.core`.

**Fidelity contract.** Struct and field names mirror OpenAI's OpenAPI/SDK schema
component names exactly (e.g. `ChatCompletionContentPartImageParam`, `File`,
`CompletionUsage`), and every struct carries a `Reference:` link to its schema on
https://developers.openai.com/api/reference/resources/chat so a reviewer can
diff it field-by-field against the source of truth. Names are transcribed from
the `openai-python` type stubs, not from memory.

**The `type`/`role` discriminator.** OpenAI documents `type` (and message `role`)
as required fields. We model each as a msgspec **tagged-union tag**
(`tag_field="type", tag="image_url"`) — which is what puts it on the wire and
validates it — **and** expose it as a read-only `type`/`role` property so it is
visible in the struct, accessible at runtime, and documented. (msgspec forbids a
tag field *and* a same-named declared field, so the property is how both coexist.)

**Typed but tolerant.** We model OpenAI's *documented* fields explicitly so the
mapping is precise and loss is reported. Unknown/newer wire fields are NOT an
error: `forbid_unknown_fields` is left off, so a future wire version decodes fine
and the dropped keys are recovered by the codec (which diffs the raw dict against
the known fields and sweeps the remainder into canonical `provider_options` /
`extensions`). A few deep peripheral objects (audio, logprob internals,
moderation, prediction, web-search) are typed as passthroughs and marked `# TODO`
— their sub-schemas flow losslessly through that same sweep.
"""

from __future__ import annotations

from typing import Any
from typing import Literal

import msgspec


class _Wire(msgspec.Struct, kw_only=True, omit_defaults=True):
    """Base for every wire struct: keyword-only with omit-defaults on encode.

    `omit_defaults` keeps the *encoded* request payload clean (an unset optional
    never appears on the wire as `null`). Unknown fields on *decode* are ignored,
    not rejected — see the module docstring for the version-resilience rationale.

    Wire structs carry no graph identity of their own: the interface's three
    `NodeId`s (request / response / chunk) are declared once in the sibling
    codec module and referenced by this package's edge definitions.
    """


# --- Content parts (request message content) -------------------------------


class ChatCompletionContentPartTextParam(_Wire, tag_field="type", tag="text"):
    """A text content part.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_text%20%3E%20(schema)>)

    Attributes:
        text: The text content.
        type: The content-part type discriminator; always `text`.
    """

    text: str

    @property
    def type(self) -> Literal["text"]:
        return "text"


class ImageURL(_Wire):
    """The `image_url` object nested in an image content part.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_image%20%3E%20(schema)>)

    Attributes:
        url: Either a URL of the image or a base64 `data:` URL.
        detail: Detail level of the image (`auto`, `low`, or `high`).
    """

    url: str
    detail: Literal["auto", "low", "high"] | None = None


class ChatCompletionContentPartImageParam(_Wire, tag_field="type", tag="image_url"):
    """An image content part.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_image%20%3E%20(schema)>)

    Attributes:
        image_url: The image URL and detail level.
        type: The content-part type discriminator; always `image_url`.
    """

    image_url: ImageURL

    @property
    def type(self) -> Literal["image_url"]:
        return "image_url"


class InputAudio(_Wire):
    """The `input_audio` object nested in an input-audio content part.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_input_audio%20%3E%20(schema)>)

    Attributes:
        data: Base64-encoded audio data.
        format: The format of the encoded audio data (`wav` or `mp3`).
    """

    data: str
    format: Literal["wav", "mp3"]


class ChatCompletionContentPartInputAudioParam(_Wire, tag_field="type", tag="input_audio"):
    """An audio content part.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_input_audio%20%3E%20(schema)>)

    Attributes:
        input_audio: The base64 audio payload and its format.
        type: The content-part type discriminator; always `input_audio`.
    """

    input_audio: InputAudio

    @property
    def type(self) -> Literal["input_audio"]:
        return "input_audio"


class FileFile(_Wire):
    """The `file` object nested in a file content part (SDK name `FileFile`).

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_file%20%3E%20(schema)>)

    Attributes:
        file_data: Base64-encoded file data, used when passing the file inline.
        file_id: The ID of an uploaded file to use as input.
        filename: The name of the file, used when passing the file inline.
    """

    file_data: str | None = None
    file_id: str | None = None
    filename: str | None = None


class File(_Wire, tag_field="type", tag="file"):
    """A file content part (SDK union member name `File`).

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_file%20%3E%20(schema)>)

    Attributes:
        file: The referenced or inline file.
        type: The content-part type discriminator; always `file`.
    """

    file: FileFile

    @property
    def type(self) -> Literal["file"]:
        return "file"


class ChatCompletionContentPartRefusalParam(_Wire, tag_field="type", tag="refusal"):
    """A refusal content part (assistant output).

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_content_part_refusal%20%3E%20(schema)>)

    Attributes:
        refusal: The refusal message generated by the model.
        type: The content-part type discriminator; always `refusal`.
    """

    refusal: str

    @property
    def type(self) -> Literal["refusal"]:
        return "refusal"


# `ChatCompletionContentPartParam`: the parts a user message may carry.
ChatCompletionContentPartParam = (
    ChatCompletionContentPartTextParam
    | ChatCompletionContentPartImageParam
    | ChatCompletionContentPartInputAudioParam
    | File
)

# Assistant/system/tool/developer messages carry only text (+ refusal on assistant).
ContentArrayOfContentPart = (
    ChatCompletionContentPartTextParam | ChatCompletionContentPartRefusalParam
)


# --- Tools, tool calls, tool choice ----------------------------------------


class FunctionDefinition(_Wire):
    """A function the model may call (shared `FunctionDefinition`).

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20function_definition%20%3E%20(schema)>)

    Attributes:
        name: The function name (a-z, A-Z, 0-9, underscores, dashes; max len 64).
        description: What the function does, used by the model to choose it.
        parameters: The parameters as a JSON Schema object.
        strict: Whether to enforce strict schema adherence when generating args.
    """

    name: str
    description: str | None = None
    parameters: dict[str, Any] | None = None
    strict: bool | None = None


class ChatCompletionFunctionToolParam(_Wire, tag_field="type", tag="function"):
    """A function tool the model may call (aliased by `ChatCompletionToolParam`).

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_function_tool%20%3E%20(schema)>)

    Attributes:
        function: The function definition.
        type: The tool type discriminator; always `function`.
    """

    function: FunctionDefinition

    @property
    def type(self) -> Literal["function"]:
        return "function"


class _ToolCallFunction(_Wire):
    """The `function` object inside a function tool call.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_message_function_tool_call%20%3E%20(schema)>)

    Attributes:
        arguments: The call arguments as a JSON-**encoded string** (the codec is
            responsible for `json.loads`).
        name: The name of the function to call.
    """

    arguments: str
    name: str


class ChatCompletionMessageFunctionToolCallParam(_Wire, tag_field="type", tag="function"):
    """A function tool call on a request assistant message.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_message_function_tool_call%20%3E%20(schema)>)

    Attributes:
        id: The ID of the tool call.
        function: The function the model called.
        type: The tool type discriminator; always `function`.
    """

    id: str
    function: _ToolCallFunction

    @property
    def type(self) -> Literal["function"]:
        return "function"


class _NamedToolChoiceFunction(_Wire):
    """The `function` object inside a named tool choice.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_named_tool_choice%20%3E%20(schema)>)

    Attributes:
        name: The name of the function to call.
    """

    name: str


class ChatCompletionNamedToolChoiceParam(_Wire, tag_field="type", tag="function"):
    """A `tool_choice` forcing a specific function call.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_named_tool_choice%20%3E%20(schema)>)

    Attributes:
        function: The function the model must call.
        type: The tool type discriminator; always `function`.
    """

    function: _NamedToolChoiceFunction

    @property
    def type(self) -> Literal["function"]:
        return "function"


# `tool_choice`: a string mode, or an object forcing a specific function.
ChatCompletionToolChoiceOptionParam = (
    Literal["none", "auto", "required"] | ChatCompletionNamedToolChoiceParam
)


# --- Response format --------------------------------------------------------


class ResponseFormatText(_Wire, tag_field="type", tag="text"):
    """`response_format` selecting plain-text output.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20response_format_text%20%3E%20(schema)>)

    Attributes:
        type: The response-format type discriminator; always `text`.
    """

    @property
    def type(self) -> Literal["text"]:
        return "text"


class ResponseFormatJSONObject(_Wire, tag_field="type", tag="json_object"):
    """`response_format` selecting a JSON object (legacy JSON mode).

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20response_format_json_object%20%3E%20(schema)>)

    Attributes:
        type: The response-format type discriminator; always `json_object`.
    """

    @property
    def type(self) -> Literal["json_object"]:
        return "json_object"


class JSONSchema(_Wire):
    """The `json_schema` object inside a structured-outputs response format.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20response_format_json_schema%20%3E%20(schema)>)

    Attributes:
        name: The name of the response format (a-z, A-Z, 0-9, _ or -; max len 64).
        description: What the response format is for, used by the model.
        schema: The schema for the response format, as a JSON Schema object.
        strict: Whether to enable strict schema adherence.
    """

    name: str
    description: str | None = None
    schema: dict[str, Any] | None = None
    strict: bool | None = None


class ResponseFormatJSONSchema(_Wire, tag_field="type", tag="json_schema"):
    """`response_format` selecting Structured Outputs against a JSON Schema.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20response_format_json_schema%20%3E%20(schema)>)

    Attributes:
        json_schema: The named schema the output must satisfy.
        type: The response-format type discriminator; always `json_schema`.
    """

    json_schema: JSONSchema

    @property
    def type(self) -> Literal["json_schema"]:
        return "json_schema"


ResponseFormat = ResponseFormatText | ResponseFormatJSONObject | ResponseFormatJSONSchema


# --- Request messages (tagged by role) -------------------------------------


class ChatCompletionDeveloperMessageParam(_Wire, tag_field="role", tag="developer"):
    """A `developer` message (replaces `system` for newer models).

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_developer_message_param%20%3E%20(schema)>)

    Attributes:
        content: The developer instructions, as text or an array of text parts.
        name: An optional name to differentiate participants of the same role.
        role: The author role discriminator; always `developer`.
    """

    content: str | list[ChatCompletionContentPartTextParam]
    name: str | None = None

    @property
    def role(self) -> Literal["developer"]:
        return "developer"


class ChatCompletionSystemMessageParam(_Wire, tag_field="role", tag="system"):
    """A `system` message setting model behaviour.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_system_message_param%20%3E%20(schema)>)

    Attributes:
        content: The system prompt, as text or an array of text parts.
        name: An optional name to differentiate participants of the same role.
        role: The author role discriminator; always `system`.
    """

    content: str | list[ChatCompletionContentPartTextParam]
    name: str | None = None

    @property
    def role(self) -> Literal["system"]:
        return "system"


class ChatCompletionUserMessageParam(_Wire, tag_field="role", tag="user"):
    """A `user` message — the end-user's turn, optionally multimodal.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_user_message_param%20%3E%20(schema)>)

    Attributes:
        content: Plain text or an array of multimodal content parts.
        name: An optional name to differentiate participants of the same role.
        role: The author role discriminator; always `user`.
    """

    content: str | list[ChatCompletionContentPartParam]
    name: str | None = None

    @property
    def role(self) -> Literal["user"]:
        return "user"


class _AssistantAudio(_Wire):
    """The `audio` reference on a request assistant message.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_assistant_message_param%20%3E%20(schema)>)

    Attributes:
        id: Unique identifier for a prior audio response from the model.
    """

    id: str


class _AssistantFunctionCall(_Wire):
    """Deprecated `function_call` on a request assistant message.

    Deprecated by OpenAI in favour of `tool_calls`.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_assistant_message_param%20%3E%20(schema)>)

    Attributes:
        arguments: The function-call arguments as a JSON-encoded string.
        name: The name of the function to call.
    """

    arguments: str
    name: str


class ChatCompletionAssistantMessageParam(_Wire, tag_field="role", tag="assistant"):
    """An `assistant` message — a prior model turn replayed in the request.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_assistant_message_param%20%3E%20(schema)>)

    Attributes:
        audio: Reference to a prior audio response from the model.
        content: Assistant text or an array of text/refusal parts; may be omitted
            when only `tool_calls` or `refusal` are present.
        function_call: Deprecated; superseded by `tool_calls`.
        name: An optional name to differentiate participants of the same role.
        refusal: The refusal message by the assistant.
        tool_calls: Tool calls the assistant previously requested.
        role: The author role discriminator; always `assistant`.
    """

    audio: _AssistantAudio | None = None
    content: str | list[ContentArrayOfContentPart] | None = None
    function_call: _AssistantFunctionCall | None = None
    name: str | None = None
    refusal: str | None = None
    tool_calls: list[ChatCompletionMessageFunctionToolCallParam] | None = None

    @property
    def role(self) -> Literal["assistant"]:
        return "assistant"


class ChatCompletionToolMessageParam(_Wire, tag_field="role", tag="tool"):
    """A `tool` message carrying the result of a single tool call.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_tool_message_param%20%3E%20(schema)>)

    Attributes:
        content: The tool result, as text or an array of text parts.
        tool_call_id: The `tool_calls` entry this message responds to.
        role: The author role discriminator; always `tool`.
    """

    content: str | list[ChatCompletionContentPartTextParam]
    tool_call_id: str

    @property
    def role(self) -> Literal["tool"]:
        return "tool"


# `ChatCompletionMessageParam`: the conversation turns accepted by the request.
ChatCompletionMessageParam = (
    ChatCompletionDeveloperMessageParam
    | ChatCompletionSystemMessageParam
    | ChatCompletionUserMessageParam
    | ChatCompletionAssistantMessageParam
    | ChatCompletionToolMessageParam
)


class ChatCompletionStreamOptionsParam(_Wire):
    """Options for streaming responses (`stream_options`).

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_stream_options%20%3E%20(schema)>)

    Attributes:
        include_obfuscation: When true (default), add an `obfuscation` field to
            streaming events to normalize payload sizes; disable to save bandwidth.
        include_usage: When true, stream a final chunk carrying token `usage`.
    """

    include_obfuscation: bool | None = None
    include_usage: bool | None = None


class CompletionCreateParams(_Wire):
    """A `POST /v1/chat/completions` request body (SDK `CompletionCreateParamsBase`).

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(method)%20create>)

    Attributes:
        messages: The conversation so far, as role-tagged messages.
        model: The model ID to use.
        audio: Output audio parameters (for `audio` modality). Passthrough; TODO.
        frequency_penalty: Penalize tokens by existing frequency (-2.0..2.0).
        function_call: Deprecated; superseded by `tool_choice`. Passthrough.
        functions: Deprecated; superseded by `tools`. Passthrough.
        logit_bias: Per-token-ID additive logit bias (-100..100).
        logprobs: Whether to return log probabilities of output tokens.
        max_completion_tokens: Upper bound on generated completion tokens.
        max_tokens: Deprecated cap on generated tokens; prefer
            `max_completion_tokens`.
        metadata: Up to 16 key/value string pairs attached to the request.
        modalities: Output types to generate (`text`, and/or `audio`).
        moderation: Moderation configuration. Passthrough; TODO.
        n: How many completions to generate per prompt.
        parallel_tool_calls: Whether to allow tool calls in parallel.
        prediction: Predicted-output configuration. Passthrough; TODO.
        presence_penalty: Penalize tokens by prior presence (-2.0..2.0).
        prompt_cache_key: Cache key for prompt-prefix caching.
        prompt_cache_retention: Prompt-cache retention (`in_memory` or `24h`).
        reasoning_effort: Reasoning depth (`minimal`/`low`/`medium`/`high`).
        response_format: Output format selector (text / JSON / JSON Schema).
        safety_identifier: Stable identifier used for safety/abuse monitoring.
        seed: Best-effort determinism seed.
        service_tier: Latency/throughput tier hint.
        stop: Up to four stop sequences, as a string or list.
        store: Whether to store the output for model distillation/evals.
        stream_options: Options that apply only when `stream` is true.
        temperature: Sampling temperature (0..2).
        tool_choice: Whether/which tool the model must call.
        tools: Tools the model may call.
        top_logprobs: Number of most-likely tokens to return per position.
        top_p: Nucleus-sampling probability mass (0..1).
        user: Deprecated stable end-user identifier (use `safety_identifier`).
        verbosity: Output verbosity hint (`low`/`medium`/`high`).
        web_search_options: Built-in web-search tool options. Passthrough; TODO.
        stream: Whether to stream partial chunks as server-sent events.
    """

    model: str
    messages: list[ChatCompletionMessageParam]
    audio: dict[str, Any] | None = None  # TODO: model ChatCompletionAudioParam
    frequency_penalty: float | None = None
    function_call: dict[str, Any] | str | None = None  # deprecated; passthrough
    functions: list[dict[str, Any]] | None = None  # deprecated; passthrough
    logit_bias: dict[str, int] | None = None
    logprobs: bool | None = None
    max_completion_tokens: int | None = None
    max_tokens: int | None = None
    metadata: dict[str, str] | None = None
    modalities: list[Literal["text", "audio"]] | None = None
    moderation: dict[str, Any] | None = None  # TODO: model Moderation
    n: int | None = None
    parallel_tool_calls: bool | None = None
    prediction: dict[str, Any] | None = None  # TODO: model ChatCompletionPredictionContentParam
    presence_penalty: float | None = None
    prompt_cache_key: str | None = None
    prompt_cache_retention: Literal["in_memory", "24h"] | None = None
    reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None
    response_format: ResponseFormat | None = None
    safety_identifier: str | None = None
    seed: int | None = None
    service_tier: Literal["auto", "default", "flex", "scale", "priority"] | None = None
    stop: str | list[str] | None = None
    store: bool | None = None
    stream: bool | None = None
    stream_options: ChatCompletionStreamOptionsParam | None = None
    temperature: float | None = None
    tool_choice: ChatCompletionToolChoiceOptionParam | None = None
    tools: list[ChatCompletionFunctionToolParam] | None = None
    top_logprobs: int | None = None
    top_p: float | None = None
    user: str | None = None
    verbosity: Literal["low", "medium", "high"] | None = None
    web_search_options: dict[str, Any] | None = None  # TODO: model WebSearchOptions


# --- Usage ------------------------------------------------------------------


class PromptTokensDetails(_Wire):
    """Breakdown of prompt tokens inside `usage`.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20completions%20%3E%20(model)%20completion_usage%20%3E%20(schema)>)

    Attributes:
        audio_tokens: Audio tokens present in the prompt.
        cached_tokens: Prompt tokens served from the prompt cache.
    """

    audio_tokens: int | None = None
    cached_tokens: int | None = None


class CompletionTokensDetails(_Wire):
    """Breakdown of completion tokens inside `usage`.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20completions%20%3E%20(model)%20completion_usage%20%3E%20(schema)>)

    Attributes:
        accepted_prediction_tokens: Predicted-output tokens that were accepted.
        audio_tokens: Audio tokens generated in the completion.
        reasoning_tokens: Tokens spent on internal reasoning.
        rejected_prediction_tokens: Predicted-output tokens that were rejected.
    """

    accepted_prediction_tokens: int | None = None
    audio_tokens: int | None = None
    reasoning_tokens: int | None = None
    rejected_prediction_tokens: int | None = None


class CompletionUsage(_Wire):
    """Token usage for the request (`usage` on the response and final chunk).

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20completions%20%3E%20(model)%20completion_usage%20%3E%20(schema)>)

    Attributes:
        completion_tokens: Tokens in the generated completion.
        prompt_tokens: Tokens in the prompt.
        total_tokens: Sum of prompt and completion tokens.
        completion_tokens_details: Optional completion-token breakdown.
        prompt_tokens_details: Optional prompt-token breakdown.
    """

    completion_tokens: int
    prompt_tokens: int
    total_tokens: int
    completion_tokens_details: CompletionTokensDetails | None = None
    prompt_tokens_details: PromptTokensDetails | None = None


# --- Response (non-streaming) -----------------------------------------------


class _ResponseToolCallFunction(_Wire):
    """The `function` object inside a response-message tool call.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_message_function_tool_call%20%3E%20(schema)>)

    Attributes:
        arguments: The arguments as a JSON-encoded string (codec does `json.loads`).
        name: The name of the function to call.
    """

    arguments: str
    name: str


class ChatCompletionMessageFunctionToolCall(_Wire, tag_field="type", tag="function"):
    """A function tool call on a response message.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_message_function_tool_call%20%3E%20(schema)>)

    Attributes:
        id: The ID of the tool call.
        function: The function the model called.
        type: The tool type discriminator; always `function`.
    """

    id: str
    function: _ResponseToolCallFunction

    @property
    def type(self) -> Literal["function"]:
        return "function"


class AnnotationURLCitation(_Wire):
    """A URL citation inside a message annotation.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_message%20%3E%20(schema)>)

    Attributes:
        end_index: Last index of the URL citation in the message.
        start_index: First index of the URL citation in the message.
        title: The title of the web resource.
        url: The URL of the web resource.
    """

    end_index: int
    start_index: int
    title: str
    url: str


class Annotation(_Wire, tag_field="type", tag="url_citation"):
    """A message annotation (web-search URL citation).

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_message%20%3E%20(schema)>)

    Attributes:
        url_citation: The URL citation when using web search.
        type: The annotation type discriminator; always `url_citation`.
    """

    url_citation: AnnotationURLCitation

    @property
    def type(self) -> Literal["url_citation"]:
        return "url_citation"


class ChatCompletionMessage(_Wire):
    """The assistant message generated by the model (a choice's `message`).

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_message%20%3E%20(schema)>)

    Attributes:
        role: The author role; always `assistant`.
        content: The message content, or `null` when only tools were called.
        refusal: The refusal message generated by the model.
        annotations: Web-search URL citations, when web search is used.
        audio: Audio response data. Passthrough; TODO model ChatCompletionAudio.
        function_call: Deprecated; superseded by `tool_calls`.
        tool_calls: Function tool calls the model generated.
    """

    role: Literal["assistant"] = "assistant"
    content: str | None = None
    refusal: str | None = None
    annotations: list[Annotation] | None = None
    audio: dict[str, Any] | None = None  # TODO: model ChatCompletionAudio
    function_call: _AssistantFunctionCall | None = None
    tool_calls: list[ChatCompletionMessageFunctionToolCall] | None = None


class ChoiceLogprobs(_Wire):
    """Log-probability information for a choice.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion%20%3E%20(schema)>)

    Attributes:
        content: Token log-probabilities for the message content. Passthrough; TODO.
        refusal: Token log-probabilities for the refusal. Passthrough; TODO.
    """

    content: list[dict[str, Any]] | None = None  # TODO: model ChatCompletionTokenLogprob
    refusal: list[dict[str, Any]] | None = None  # TODO: model ChatCompletionTokenLogprob


class Choice(_Wire):
    """One completion choice within a chat completion response.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion%20%3E%20(schema)>)

    Attributes:
        finish_reason: Why generation stopped.
        index: Position of this choice in the `choices` array.
        message: The generated assistant message.
        logprobs: Log-probability information, when requested.
    """

    finish_reason: Literal["stop", "length", "tool_calls", "content_filter", "function_call"]
    index: int
    message: ChatCompletionMessage
    logprobs: ChoiceLogprobs | None = None


class ChatCompletion(_Wire):
    """A `/v1/chat/completions` (non-streaming) response body.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion%20%3E%20(schema)>)

    Attributes:
        id: A unique identifier for the completion.
        choices: The generated choices (length `n`).
        created: Unix timestamp (seconds) of creation.
        model: The model used for the completion.
        object: The object type; always `chat.completion`.
        moderation: Moderation results. Passthrough; TODO model Moderation.
        service_tier: The service tier that processed the request.
        system_fingerprint: Backend configuration fingerprint.
        usage: Usage statistics for the completion request.
    """

    id: str
    choices: list[Choice]
    created: int
    model: str
    object: Literal["chat.completion"] = "chat.completion"
    moderation: dict[str, Any] | None = None  # TODO: model Moderation
    service_tier: Literal["auto", "default", "flex", "scale", "priority"] | None = None
    system_fingerprint: str | None = None
    usage: CompletionUsage | None = None


# --- Streaming chunk --------------------------------------------------------


class ChoiceDeltaFunctionCall(_Wire):
    """Incremental deprecated `function_call` fields in a streamed delta.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_chunk%20%3E%20(schema)>)

    Attributes:
        arguments: A fragment of the JSON-encoded argument string.
        name: The name of the function to call.
    """

    arguments: str | None = None
    name: str | None = None


class ChoiceDeltaToolCallFunction(_Wire):
    """Incremental `function` fields inside a streamed tool-call delta.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_chunk%20%3E%20(schema)>)

    Attributes:
        arguments: A fragment of the JSON-encoded argument string to concatenate.
        name: The name of the function to call.
    """

    arguments: str | None = None
    name: str | None = None


class ChoiceDeltaToolCall(_Wire):
    """An incremental tool-call entry within a streamed choice delta.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_chunk%20%3E%20(schema)>)

    Attributes:
        index: Position of this tool call in the assembled `tool_calls` array.
        id: The ID of the tool call (sent on the first delta for this index).
        function: Incremental name/argument fragments.
        type: The tool type; sent on the first delta; `function`.
    """

    index: int
    id: str | None = None
    function: ChoiceDeltaToolCallFunction | None = None
    type: Literal["function"] | None = None


class ChoiceDelta(_Wire):
    """The incremental `delta` carried by a streamed choice.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_chunk%20%3E%20(schema)>)

    Attributes:
        content: A fragment of generated text to concatenate.
        function_call: Deprecated; superseded by `tool_calls`.
        refusal: A fragment of a refusal message to concatenate.
        role: The author role (sent once, on the first delta).
        tool_calls: Incremental tool-call fragments.
    """

    content: str | None = None
    function_call: ChoiceDeltaFunctionCall | None = None
    refusal: str | None = None
    role: Literal["developer", "system", "user", "assistant", "tool"] | None = None
    tool_calls: list[ChoiceDeltaToolCall] | None = None


class ChunkChoice(_Wire):
    """One choice within a streamed chat completion chunk (SDK `Choice`).

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_chunk%20%3E%20(schema)>)

    Attributes:
        delta: The incremental update for this choice.
        index: Position of this choice in the `choices` array.
        finish_reason: Set on the final chunk for the choice; otherwise `null`.
        logprobs: Log-probability information, when requested.
    """

    delta: ChoiceDelta
    index: int
    finish_reason: (
        Literal["stop", "length", "tool_calls", "content_filter", "function_call"] | None
    ) = None
    logprobs: ChoiceLogprobs | None = None


class ChatCompletionChunk(_Wire):
    """A single `chat.completion.chunk` server-sent event body.

    Reference: [Reference](<https://developers.openai.com/api/reference/resources/chat#(resource)%20chat.completions%20%3E%20(model)%20chat_completion_chunk%20%3E%20(schema)>)

    Attributes:
        id: Identifier shared by every chunk of a streamed completion.
        choices: The incremental choices in this chunk.
        created: Unix timestamp (seconds) of creation.
        model: The model that produced the completion.
        object: The object type; always `chat.completion.chunk`.
        moderation: Moderation results. Passthrough; TODO model Moderation.
        service_tier: The service tier that processed the request.
        system_fingerprint: Backend configuration fingerprint.
        usage: Final token usage, present only when stream usage is included.
    """

    id: str
    choices: list[ChunkChoice]
    created: int
    model: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    moderation: dict[str, Any] | None = None  # TODO: model Moderation
    service_tier: Literal["auto", "default", "flex", "scale", "priority"] | None = None
    system_fingerprint: str | None = None
    usage: CompletionUsage | None = None
