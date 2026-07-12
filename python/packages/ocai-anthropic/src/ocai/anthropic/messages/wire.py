"""Typed Anthropic **Messages** wire models (`POST /v1/messages`).

These `msgspec.Struct`s model Anthropic's Messages API request, response, and
streaming-event shapes — the wire truth of the `anthropic/messages` interface.
Its graph identity (the request / response / chunk `NodeId`s) lives in the
sibling `ocai.anthropic.messages.codec` module; this module is the plugin's
**decode boundary** (rule 11): msgspec turns raw JSON into these typed structs,
and the codec maps them to/from the neutral canonical IR. msgspec lives only
here, never in `ocai.core`.

**Every struct carries a `Reference:` link** to the Anthropic Messages API
documentation (<https://platform.claude.com/docs/en/api/messages>) so a reviewer
can diff this model field-by-field against the source of truth and confirm it
stays 1-to-1. Streaming structs reference the streaming guide
(<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>).

**Typed but tolerant.** We model Anthropic's *stable, documented* fields
explicitly so the mapping is precise and loss is reported. Unknown/newer wire
fields are NOT an error: `forbid_unknown_fields` is left off, so a future wire
version decodes fine and the dropped keys are recovered by the codec (which
diffs the raw dict against the known fields and sweeps the remainder into
canonical `provider_options` / `extensions`). That keeps the dialect
version-resilient (rules 5 & 6) instead of brittle. In the same spirit,
open-ended enum-ish wire values (`stop_reason`, `error_code`, `media_type`,
tool/source `type` discriminators that the model never has to branch on) are
typed as `str`: a value the API adds tomorrow round-trips today.

Polymorphic wire shapes (content blocks, message/document sources, tool
definitions, tool choice, thinking config, streaming events and their deltas)
are msgspec **tagged unions** discriminated on their wire `type` field — the
native equivalent of the IR's hand-rolled `decode_tagged`. Request-side blocks
(`*Param`) and response-side blocks are modelled as **separate** unions even
when they share a `type` tag, because their fields differ (e.g. a request
`tool_use` carries `cache_control`; a response `tool_use` carries `caller`).
"""

from __future__ import annotations

from typing import Any

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


# --- Shared markers ---------------------------------------------------------


class CacheControlEphemeral(_Wire):
    """An `ephemeral` cache-control breakpoint attachable to most blocks.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        type: Cache-control type; always `ephemeral`.
        ttl: Cache lifetime, `5m` or `1h`; defaults server-side to `5m`.
    """

    type: str = "ephemeral"
    ttl: str | None = None


class CitationsConfig(_Wire):
    """The `citations` config attached to a document or search-result block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        enabled: Whether the model may cite from this source.
    """

    enabled: bool | None = None


# --- Sources (image / document) --------------------------------------------


class Base64Source(_Wire, tag_field="type", tag="base64"):
    """A base64-encoded binary source (image bytes or PDF bytes).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        media_type: The MIME type (e.g. `image/png`, `application/pdf`).
        data: The base64-encoded bytes.
    """

    media_type: str
    data: str


class URLSource(_Wire, tag_field="type", tag="url"):
    """A source referenced by public URL (image or PDF).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        url: The publicly fetchable URL of the resource.
    """

    url: str


class FileSource(_Wire, tag_field="type", tag="file"):
    """A source referencing a previously uploaded file by id (Files API).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        file_id: Identifier of the uploaded file to use as the source.
    """

    file_id: str


class PlainTextSource(_Wire, tag_field="type", tag="text"):
    """A plain-text document source (`media_type: text/plain`).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        data: The document text.
        media_type: The MIME type; always `text/plain`.
    """

    data: str
    media_type: str = "text/plain"


class ContentBlockSource(_Wire, tag_field="type", tag="content"):
    """A document source composed of inline content blocks.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        content: Either text, or an array of text/image content-block params.
    """

    content: str | list[TextBlockParam | ImageBlockParam]


# An image's `source`: base64 bytes, a URL, or an uploaded file id.
ImageSource = Base64Source | URLSource | FileSource

# A document's `source`: base64 PDF, plain text, a URL, an uploaded file id, or
# inline content blocks.
DocumentSource = Base64Source | PlainTextSource | URLSource | FileSource | ContentBlockSource


# --- Request content block params (tagged on `type`) ------------------------


class TextBlockParam(_Wire, tag_field="type", tag="text"):
    """A `text` content block on an input message.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        text: The text content.
        citations: Citation references attached to this text.
        cache_control: Optional cache breakpoint placed after this block.
    """

    text: str
    citations: list[dict[str, Any]] | None = None
    cache_control: CacheControlEphemeral | None = None


class ImageBlockParam(_Wire, tag_field="type", tag="image"):
    """An `image` content block on an input message.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        source: The image source (base64, URL, or uploaded file).
        cache_control: Optional cache breakpoint placed after this block.
    """

    source: ImageSource
    cache_control: CacheControlEphemeral | None = None


class DocumentBlockParam(_Wire, tag_field="type", tag="document"):
    """A `document` content block (PDF, plain text, or inline content).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        source: The document source.
        title: Optional human-readable document title.
        context: Optional extra context describing the document to the model.
        citations: Optional citation configuration for this document.
        cache_control: Optional cache breakpoint placed after this block.
    """

    source: DocumentSource
    title: str | None = None
    context: str | None = None
    citations: CitationsConfig | None = None
    cache_control: CacheControlEphemeral | None = None


class ToolUseBlockParam(_Wire, tag_field="type", tag="tool_use"):
    """A `tool_use` block replayed on an input assistant message.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        id: Identifier of this tool invocation, echoed by the matching
            `tool_result` block's `tool_use_id`.
        name: Name of the tool the model called.
        input: The tool input object the model produced.
        cache_control: Optional cache breakpoint placed after this block.
    """

    id: str
    name: str
    input: dict[str, Any]
    cache_control: CacheControlEphemeral | None = None


class ToolResultBlockParam(_Wire, tag_field="type", tag="tool_result"):
    """A `tool_result` block carrying the output of a single tool call.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        tool_use_id: Id of the `tool_use` block this result answers.
        content: The tool's output as text, or an array of content-block params
            (text/image/document/search-result).
        is_error: Whether the tool execution errored.
        cache_control: Optional cache breakpoint placed after this block.
    """

    tool_use_id: str
    content: str | list[ToolResultContent] | None = None
    is_error: bool | None = None
    cache_control: CacheControlEphemeral | None = None


class ThinkingBlockParam(_Wire, tag_field="type", tag="thinking"):
    """A `thinking` block replayed on an input assistant message.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        thinking: The internal reasoning text.
        signature: Signature verifying the block across turns.
    """

    thinking: str
    signature: str


class RedactedThinkingBlockParam(_Wire, tag_field="type", tag="redacted_thinking"):
    """A `redacted_thinking` block (opaque, server-encrypted reasoning).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        data: The redacted, encrypted reasoning payload.
    """

    data: str


class SearchResultBlockParam(_Wire, tag_field="type", tag="search_result"):
    """A `search_result` content block supplying citable retrieved content.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        title: Title of the search result.
        source: Source identifier (e.g. a URL or document id).
        content: The result body, as an array of text blocks.
        citations: Optional citation configuration for this result.
        cache_control: Optional cache breakpoint placed after this block.
    """

    title: str
    source: str
    content: list[TextBlockParam]
    citations: CitationsConfig | None = None
    cache_control: CacheControlEphemeral | None = None


class ServerToolUseBlockParam(_Wire, tag_field="type", tag="server_tool_use"):
    """A `server_tool_use` block replayed on an input message.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        id: Identifier of this server-tool invocation.
        name: Server tool name (`web_search`, `web_fetch`, `code_execution`, …).
        input: The tool input object.
        cache_control: Optional cache breakpoint placed after this block.
    """

    id: str
    name: str
    input: dict[str, Any]
    cache_control: CacheControlEphemeral | None = None


# Content-block params accepted inside a `tool_result` block's `content` array.
ToolResultContent = TextBlockParam | ImageBlockParam | SearchResultBlockParam | DocumentBlockParam

# Every content-block param a `MessageParam.content` array may carry.
ContentBlockParam = (
    TextBlockParam
    | ImageBlockParam
    | DocumentBlockParam
    | ToolUseBlockParam
    | ToolResultBlockParam
    | ThinkingBlockParam
    | RedactedThinkingBlockParam
    | SearchResultBlockParam
    | ServerToolUseBlockParam
)


# --- Input messages ---------------------------------------------------------


class MessageParam(_Wire):
    """A single input message in the `messages` array.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        role: Conversational role — `user` or `assistant`.
        content: Either a plain string, or an array of content-block params.
    """

    role: str
    content: str | list[ContentBlockParam]


# --- Tools ------------------------------------------------------------------


class Tool(_Wire, tag_field="type", tag="custom"):
    """A custom (client-side) tool the model may call.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        name: Tool name the model uses to call it.
        input_schema: JSON Schema (`type: object`) for the tool's input.
        description: Natural-language description guiding when to call it.
        cache_control: Optional cache breakpoint placed after this tool.
        strict: Whether to guarantee the model's input validates against schema.
        defer_loading: Defer loading until a `tool_reference` is returned.
        eager_input_streaming: Stream input params eagerly (fine-grained).
        input_examples: Example inputs that prime the model.
        allowed_callers: Which callers (`direct`, code-execution variants) may
            invoke this tool.
    """

    name: str
    input_schema: dict[str, Any]
    description: str | None = None
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    eager_input_streaming: bool | None = None
    input_examples: list[dict[str, Any]] | None = None
    allowed_callers: list[str] | None = None


class BashTool(_Wire, tag_field="type", tag="bash_20250124"):
    """The server-side `bash` tool (`bash_20250124`).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        name: Tool name; always `bash`.
        cache_control: Optional cache breakpoint placed after this tool.
        strict: Whether to guarantee strict schema validation.
        defer_loading: Defer loading until referenced.
        input_examples: Example inputs that prime the model.
        allowed_callers: Which callers may invoke this tool.
    """

    name: str = "bash"
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    input_examples: list[dict[str, Any]] | None = None
    allowed_callers: list[str] | None = None


class CodeExecutionTool(_Wire, tag_field="type", tag="code_execution_20250825"):
    """The server-side `code_execution` tool (`code_execution_20250825`).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        name: Tool name; always `code_execution`.
        cache_control: Optional cache breakpoint placed after this tool.
        strict: Whether to guarantee strict schema validation.
        defer_loading: Defer loading until referenced.
        allowed_callers: Which callers may invoke this tool.
    """

    name: str = "code_execution"
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    allowed_callers: list[str] | None = None


class CodeExecutionTool20260120(_Wire, tag_field="type", tag="code_execution_20260120"):
    """The `code_execution` tool with REPL state persistence (`code_execution_20260120`).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        name: Tool name; always `code_execution`.
        cache_control: Optional cache breakpoint placed after this tool.
        strict: Whether to guarantee strict schema validation.
        defer_loading: Defer loading until referenced.
        allowed_callers: Which callers may invoke this tool.
    """

    name: str = "code_execution"
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    allowed_callers: list[str] | None = None


class TextEditorTool(_Wire, tag_field="type", tag="text_editor_20250728"):
    """The server-side text-editor tool (`text_editor_20250728`).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        name: Tool name; always `str_replace_based_edit_tool`.
        max_characters: Max characters to display when viewing a file.
        cache_control: Optional cache breakpoint placed after this tool.
        strict: Whether to guarantee strict schema validation.
        defer_loading: Defer loading until referenced.
        input_examples: Example inputs that prime the model.
        allowed_callers: Which callers may invoke this tool.
    """

    name: str = "str_replace_based_edit_tool"
    max_characters: int | None = None
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    input_examples: list[dict[str, Any]] | None = None
    allowed_callers: list[str] | None = None


class MemoryTool(_Wire, tag_field="type", tag="memory_20250818"):
    """The server-side `memory` tool (`memory_20250818`).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        name: Tool name; always `memory`.
        cache_control: Optional cache breakpoint placed after this tool.
        strict: Whether to guarantee strict schema validation.
        defer_loading: Defer loading until referenced.
        input_examples: Example inputs that prime the model.
        allowed_callers: Which callers may invoke this tool.
    """

    name: str = "memory"
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    input_examples: list[dict[str, Any]] | None = None
    allowed_callers: list[str] | None = None


class UserLocation(_Wire):
    """The optional `user_location` hint on the web-search tool.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        type: Location type; always `approximate`.
        city: Approximate city.
        region: Approximate region/state.
        country: Approximate country.
        timezone: IANA timezone identifier.
    """

    type: str = "approximate"
    city: str | None = None
    region: str | None = None
    country: str | None = None
    timezone: str | None = None


class WebSearchTool(_Wire, tag_field="type", tag="web_search_20260209"):
    """The server-side `web_search` tool (`web_search_20260209`).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        name: Tool name; always `web_search`.
        allowed_domains: Only include results from these domains.
        blocked_domains: Exclude results from these domains.
        max_uses: Maximum number of searches per request.
        user_location: Approximate user location to localize results.
        cache_control: Optional cache breakpoint placed after this tool.
        strict: Whether to guarantee strict schema validation.
        defer_loading: Defer loading until referenced.
        allowed_callers: Which callers may invoke this tool.
    """

    name: str = "web_search"
    allowed_domains: list[str] | None = None
    blocked_domains: list[str] | None = None
    max_uses: int | None = None
    user_location: UserLocation | None = None
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    allowed_callers: list[str] | None = None


class WebFetchTool(_Wire, tag_field="type", tag="web_fetch_20260309"):
    """The server-side `web_fetch` tool (`web_fetch_20260309`).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        name: Tool name; always `web_fetch`.
        allowed_domains: Only fetch from these domains.
        blocked_domains: Never fetch from these domains.
        max_content_tokens: Cap on tokens of fetched page text.
        max_uses: Maximum number of fetches per request.
        citations: Optional citation configuration for fetched content.
        use_cache: Whether to allow cached content (false bypasses the cache).
        cache_control: Optional cache breakpoint placed after this tool.
        strict: Whether to guarantee strict schema validation.
        defer_loading: Defer loading until referenced.
        allowed_callers: Which callers may invoke this tool.
    """

    name: str = "web_fetch"
    allowed_domains: list[str] | None = None
    blocked_domains: list[str] | None = None
    max_content_tokens: int | None = None
    max_uses: int | None = None
    citations: CitationsConfig | None = None
    use_cache: bool | None = None
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    allowed_callers: list[str] | None = None


class ToolSearchToolBm25(_Wire, tag_field="type", tag="tool_search_tool_bm25_20251119"):
    """The BM25 tool-search tool (`tool_search_tool_bm25_20251119`).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        name: Tool name; always `tool_search_tool_bm25`.
        cache_control: Optional cache breakpoint placed after this tool.
        strict: Whether to guarantee strict schema validation.
        defer_loading: Defer loading until referenced.
        allowed_callers: Which callers may invoke this tool.
    """

    name: str = "tool_search_tool_bm25"
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    allowed_callers: list[str] | None = None


class ToolSearchToolRegex(_Wire, tag_field="type", tag="tool_search_tool_regex_20251119"):
    """The regex tool-search tool (`tool_search_tool_regex_20251119`).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        name: Tool name; always `tool_search_tool_regex`.
        cache_control: Optional cache breakpoint placed after this tool.
        strict: Whether to guarantee strict schema validation.
        defer_loading: Defer loading until referenced.
        allowed_callers: Which callers may invoke this tool.
    """

    name: str = "tool_search_tool_regex"
    cache_control: CacheControlEphemeral | None = None
    strict: bool | None = None
    defer_loading: bool | None = None
    allowed_callers: list[str] | None = None


# A `tools` array entry: a custom tool or one of the built-in server/client tools.
# Custom tools must carry `type: "custom"` so the union can discriminate them
# (the API also accepts an omitted type, but the codec writes it explicitly).
ToolUnion = (
    Tool
    | BashTool
    | CodeExecutionTool
    | CodeExecutionTool20260120
    | TextEditorTool
    | MemoryTool
    | WebSearchTool
    | WebFetchTool
    | ToolSearchToolBm25
    | ToolSearchToolRegex
)


# --- Tool choice ------------------------------------------------------------


class ToolChoiceAuto(_Wire, tag_field="type", tag="auto"):
    """`tool_choice` letting the model decide whether to call a tool.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        disable_parallel_tool_use: Cap the model to at most one tool call.
    """

    disable_parallel_tool_use: bool | None = None


class ToolChoiceAny(_Wire, tag_field="type", tag="any"):
    """`tool_choice` forcing the model to call some (any) tool.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        disable_parallel_tool_use: Force exactly one tool call.
    """

    disable_parallel_tool_use: bool | None = None


class ToolChoiceTool(_Wire, tag_field="type", tag="tool"):
    """`tool_choice` forcing a specific named tool.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        name: Name of the tool the model must call.
        disable_parallel_tool_use: Force exactly one tool call.
    """

    name: str
    disable_parallel_tool_use: bool | None = None


class ToolChoiceNone(_Wire, tag_field="type", tag="none"):
    """`tool_choice` forbidding all tool use.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)
    """


# The `tool_choice` field: auto / any / a specific tool / none.
ToolChoice = ToolChoiceAuto | ToolChoiceAny | ToolChoiceTool | ToolChoiceNone


# --- Thinking config --------------------------------------------------------


class ThinkingConfigEnabled(_Wire, tag_field="type", tag="enabled"):
    """Extended-thinking config with an explicit token budget.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        budget_tokens: Tokens reserved for internal reasoning (>=1024 and less
            than `max_tokens`).
        display: How thinking surfaces in the response (`summarized`/`omitted`).
    """

    budget_tokens: int
    display: str | None = None


class ThinkingConfigDisabled(_Wire, tag_field="type", tag="disabled"):
    """Extended-thinking config explicitly disabled.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)
    """


class ThinkingConfigAdaptive(_Wire, tag_field="type", tag="adaptive"):
    """Adaptive extended-thinking config (the model decides when to think).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        display: How thinking surfaces in the response (`summarized`/`omitted`).
    """

    display: str | None = None


# The `thinking` field: enabled (with budget), disabled, or adaptive.
ThinkingConfig = ThinkingConfigEnabled | ThinkingConfigDisabled | ThinkingConfigAdaptive


# --- Structured output config ----------------------------------------------


class JSONOutputFormat(_Wire, tag_field="type", tag="json_schema"):
    """A JSON-schema output format for structured outputs.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        schema: The JSON Schema the output must conform to.
    """

    schema: dict[str, Any]


class OutputConfig(_Wire):
    """The `output_config` controlling output format and effort.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        format: Structured-output format selector (a JSON schema).
        effort: Output-generation effort (`low`/`medium`/`high`/`xhigh`/`max`).
    """

    format: JSONOutputFormat | None = None
    effort: str | None = None


# --- Metadata ---------------------------------------------------------------


class Metadata(_Wire):
    """The request `metadata` object.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        user_id: An opaque external identifier for the end user (abuse
            detection); a uuid, hash, or other non-PII id.
    """

    user_id: str | None = None


# --- Request ----------------------------------------------------------------


class MessagesRequest(_Wire):
    """A `POST /v1/messages` request body.

    Models Anthropic's documented, stable request fields; newer/rare knobs are
    not enumerated and instead survive via the codec's extras sweep (module
    docstring).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        model: The model that will complete the prompt (e.g. `claude-opus-4-6`).
        max_tokens: Maximum tokens to generate before stopping.
        messages: The conversation so far, as alternating-role messages.
        system: System prompt — a string or an array of text blocks.
        temperature: Sampling randomness (0.0..1.0).
        top_p: Nucleus-sampling probability mass.
        top_k: Sample only from the top K tokens.
        stop_sequences: Custom sequences that stop generation.
        stream: Whether to stream the response as server-sent events.
        thinking: Extended-thinking configuration.
        tool_choice: Whether/which tool the model must use.
        tools: Tool definitions the model may use.
        metadata: Request metadata (e.g. `user_id`).
        output_config: Structured-output / effort configuration.
        service_tier: Capacity preference (`auto` or `standard_only`).
        container: Container identifier to reuse across requests.
        inference_geo: Geographic region preference for inference.
    """

    model: str
    max_tokens: int
    messages: list[MessageParam]
    system: str | list[TextBlockParam] | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    stop_sequences: list[str] | None = None
    stream: bool | None = None
    thinking: ThinkingConfig | None = None
    tool_choice: ToolChoice | None = None
    tools: list[ToolUnion] | None = None
    metadata: Metadata | None = None
    output_config: OutputConfig | None = None
    service_tier: str | None = None
    container: str | None = None
    inference_geo: str | None = None


# --- Response citations -----------------------------------------------------


class CitationCharLocation(_Wire, tag_field="type", tag="char_location"):
    """A citation referencing a character range of a document.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        cited_text: The quoted source text.
        document_index: Index of the cited document in the request.
        document_title: Title of the cited document, if any.
        start_char_index: Inclusive start character offset.
        end_char_index: Exclusive end character offset.
        file_id: Id of the cited file, if sourced from the Files API.
    """

    cited_text: str
    document_index: int
    start_char_index: int
    end_char_index: int
    document_title: str | None = None
    file_id: str | None = None


class CitationPageLocation(_Wire, tag_field="type", tag="page_location"):
    """A citation referencing a page range of a document.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        cited_text: The quoted source text.
        document_index: Index of the cited document in the request.
        document_title: Title of the cited document, if any.
        start_page_number: Inclusive start page number.
        end_page_number: Exclusive end page number.
        file_id: Id of the cited file, if sourced from the Files API.
    """

    cited_text: str
    document_index: int
    start_page_number: int
    end_page_number: int
    document_title: str | None = None
    file_id: str | None = None


class CitationContentBlockLocation(_Wire, tag_field="type", tag="content_block_location"):
    """A citation referencing a content-block range of a document.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        cited_text: The quoted source text.
        document_index: Index of the cited document in the request.
        document_title: Title of the cited document, if any.
        start_block_index: Inclusive start content-block index.
        end_block_index: Exclusive end content-block index.
        file_id: Id of the cited file, if sourced from the Files API.
    """

    cited_text: str
    document_index: int
    start_block_index: int
    end_block_index: int
    document_title: str | None = None
    file_id: str | None = None


class CitationWebSearchResultLocation(_Wire, tag_field="type", tag="web_search_result_location"):
    """A citation referencing a web-search result.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        cited_text: The quoted source text.
        url: URL of the cited web result.
        title: Title of the cited web result.
        encrypted_index: Opaque index used to resolve the cited result.
    """

    cited_text: str
    url: str
    encrypted_index: str
    title: str | None = None


class CitationSearchResultLocation(_Wire, tag_field="type", tag="search_result_location"):
    """A citation referencing a supplied `search_result` block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        cited_text: The quoted source text.
        source: Source identifier of the cited search result.
        title: Title of the cited search result, if any.
        search_result_index: Index of the cited search-result block.
        start_block_index: Inclusive start content-block index.
        end_block_index: Exclusive end content-block index.
    """

    cited_text: str
    source: str
    search_result_index: int
    start_block_index: int
    end_block_index: int
    title: str | None = None


# A citation attached to a response `text` block.
TextCitation = (
    CitationCharLocation
    | CitationPageLocation
    | CitationContentBlockLocation
    | CitationWebSearchResultLocation
    | CitationSearchResultLocation
)


# --- Response content blocks (tagged on `type`) -----------------------------


class TextBlock(_Wire, tag_field="type", tag="text"):
    """A `text` content block in a response.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        text: The generated text.
        citations: Citations supporting this text, if citation was enabled.
    """

    text: str
    citations: list[TextCitation] | None = None


class ThinkingBlock(_Wire, tag_field="type", tag="thinking"):
    """A `thinking` content block in a response.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        thinking: The internal reasoning text.
        signature: Signature verifying the block across turns.
    """

    thinking: str
    signature: str | None = None


class RedactedThinkingBlock(_Wire, tag_field="type", tag="redacted_thinking"):
    """A `redacted_thinking` content block in a response.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        data: The redacted, encrypted reasoning payload.
    """

    data: str


class ToolUseBlock(_Wire, tag_field="type", tag="tool_use"):
    """A `tool_use` content block in a response (the model's tool call).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        id: Identifier of this tool call, echoed by the `tool_result`.
        name: Name of the tool the model is calling.
        input: The tool input object the model produced.
        caller: Who invoked the tool (the model directly, or a server tool).
    """

    id: str
    name: str
    input: dict[str, Any]
    caller: Caller | None = None


class ServerToolUseBlock(_Wire, tag_field="type", tag="server_tool_use"):
    """A `server_tool_use` content block in a response.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        id: Identifier of this server-tool invocation.
        name: Server tool name (`web_search`, `web_fetch`, `code_execution`, …).
        input: The tool input object.
        caller: Who invoked the tool.
    """

    id: str
    name: str
    input: dict[str, Any]
    caller: Caller | None = None


class WebSearchResultBlock(_Wire, tag_field="type", tag="web_search_result"):
    """A single web-search result inside a `web_search_tool_result` block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        title: Result title.
        url: Result URL.
        encrypted_content: Opaque encrypted result content for follow-up.
        page_age: Approximate age of the page, if known.
    """

    title: str
    url: str
    encrypted_content: str
    page_age: str | None = None


class WebSearchToolResultError(_Wire, tag_field="type", tag="web_search_tool_result_error"):
    """An error payload inside a `web_search_tool_result` block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        error_code: Machine-readable failure code (e.g. `max_uses_exceeded`).
    """

    error_code: str


class WebSearchToolResultBlock(_Wire, tag_field="type", tag="web_search_tool_result"):
    """A `web_search_tool_result` content block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        tool_use_id: Id of the `server_tool_use` block this answers.
        content: Either the list of results, or an error payload.
        caller: Who invoked the originating tool.
    """

    tool_use_id: str
    content: list[WebSearchResultBlock] | WebSearchToolResultError
    caller: Caller | None = None


class WebFetchBlock(_Wire, tag_field="type", tag="web_fetch_result"):
    """The fetched-content payload inside a `web_fetch_tool_result` block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        url: The URL that was fetched.
        retrieved_at: When the content was retrieved.
        content: The fetched content as a document block.
    """

    url: str
    content: DocumentBlock
    retrieved_at: str | None = None


class WebFetchToolResultError(_Wire, tag_field="type", tag="web_fetch_tool_result_error"):
    """An error payload inside a `web_fetch_tool_result` block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        error_code: Machine-readable failure code (e.g. `url_not_allowed`).
    """

    error_code: str


class WebFetchToolResultBlock(_Wire, tag_field="type", tag="web_fetch_tool_result"):
    """A `web_fetch_tool_result` content block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        tool_use_id: Id of the `server_tool_use` block this answers.
        content: Either the fetched content, or an error payload.
        caller: Who invoked the originating tool.
    """

    tool_use_id: str
    content: WebFetchBlock | WebFetchToolResultError
    caller: Caller | None = None


class CodeExecutionOutputBlock(_Wire, tag_field="type", tag="code_execution_output"):
    """A file output emitted by a code-execution run.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        file_id: Id of the produced output file.
    """

    file_id: str


class CodeExecutionResultBlock(_Wire, tag_field="type", tag="code_execution_result"):
    """A successful `code_execution` result payload.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        stdout: Captured standard output.
        stderr: Captured standard error.
        return_code: Process exit code.
        content: Output file blocks produced by the run.
    """

    stdout: str
    stderr: str
    return_code: int
    content: list[CodeExecutionOutputBlock] | None = None


class CodeExecutionToolResultError(_Wire, tag_field="type", tag="code_execution_tool_result_error"):
    """An error payload inside a `code_execution_tool_result` block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        error_code: Machine-readable failure code (e.g. `execution_time_exceeded`).
    """

    error_code: str


class CodeExecutionToolResultBlock(_Wire, tag_field="type", tag="code_execution_tool_result"):
    """A `code_execution_tool_result` content block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        tool_use_id: Id of the `server_tool_use` block this answers.
        content: Either the execution result, or an error payload.
    """

    tool_use_id: str
    content: CodeExecutionResultBlock | CodeExecutionToolResultError


class BashCodeExecutionResultBlock(_Wire, tag_field="type", tag="bash_code_execution_result"):
    """A successful `bash_code_execution` result payload.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        stdout: Captured standard output.
        stderr: Captured standard error.
        return_code: Process exit code.
        content: Output file blocks produced by the run.
    """

    stdout: str
    stderr: str
    return_code: int
    content: list[CodeExecutionOutputBlock] | None = None


class BashCodeExecutionToolResultError(
    _Wire, tag_field="type", tag="bash_code_execution_tool_result_error"
):
    """An error payload inside a `bash_code_execution_tool_result` block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        error_code: Machine-readable failure code (e.g. `output_file_too_large`).
    """

    error_code: str


class BashCodeExecutionToolResultBlock(
    _Wire, tag_field="type", tag="bash_code_execution_tool_result"
):
    """A `bash_code_execution_tool_result` content block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        tool_use_id: Id of the `server_tool_use` block this answers.
        content: Either the execution result, or an error payload.
    """

    tool_use_id: str
    content: BashCodeExecutionResultBlock | BashCodeExecutionToolResultError


class TextEditorViewResultBlock(
    _Wire, tag_field="type", tag="text_editor_code_execution_view_result"
):
    """A text-editor `view` result.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        content: The viewed file content.
        file_type: Kind of file viewed (`text`, `image`, or `pdf`).
        start_line: First line shown, if a range was requested.
        num_lines: Number of lines shown.
        total_lines: Total lines in the file.
    """

    content: str
    file_type: str
    start_line: int | None = None
    num_lines: int | None = None
    total_lines: int | None = None


class TextEditorCreateResultBlock(
    _Wire, tag_field="type", tag="text_editor_code_execution_create_result"
):
    """A text-editor `create` result.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        is_file_update: Whether the create overwrote an existing file.
    """

    is_file_update: bool


class TextEditorStrReplaceResultBlock(
    _Wire, tag_field="type", tag="text_editor_code_execution_str_replace_result"
):
    """A text-editor `str_replace` result (the applied diff hunk).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        old_start: Start line of the replaced region.
        old_lines: Number of lines replaced.
        new_start: Start line of the inserted region.
        new_lines: Number of lines inserted.
        lines: The resulting line context.
    """

    old_start: int | None = None
    old_lines: int | None = None
    new_start: int | None = None
    new_lines: int | None = None
    lines: list[str] | None = None


class TextEditorToolResultError(
    _Wire, tag_field="type", tag="text_editor_code_execution_tool_result_error"
):
    """An error payload inside a `text_editor_code_execution_tool_result` block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        error_code: Machine-readable failure code (e.g. `file_not_found`).
        error_message: Human-readable error message.
    """

    error_code: str
    error_message: str | None = None


class TextEditorToolResultBlock(
    _Wire, tag_field="type", tag="text_editor_code_execution_tool_result"
):
    """A `text_editor_code_execution_tool_result` content block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        tool_use_id: Id of the `server_tool_use` block this answers.
        content: A view/create/str_replace result, or an error payload.
    """

    tool_use_id: str
    content: (
        TextEditorViewResultBlock
        | TextEditorCreateResultBlock
        | TextEditorStrReplaceResultBlock
        | TextEditorToolResultError
    )


class ToolReferenceBlock(_Wire, tag_field="type", tag="tool_reference"):
    """A tool reference surfaced by tool-search.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        name: Name of the referenced tool.
    """

    name: str


class ToolSearchToolSearchResultBlock(
    _Wire, tag_field="type", tag="tool_search_tool_search_result"
):
    """A successful tool-search result payload.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        tool_references: The tools the search surfaced.
    """

    tool_references: list[ToolReferenceBlock]


class ToolSearchToolResultError(_Wire, tag_field="type", tag="tool_search_tool_result_error"):
    """An error payload inside a `tool_search_tool_result` block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        error_code: Machine-readable failure code.
        error_message: Human-readable error message.
    """

    error_code: str
    error_message: str | None = None


class ToolSearchToolResultBlock(_Wire, tag_field="type", tag="tool_search_tool_result"):
    """A `tool_search_tool_result` content block.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        tool_use_id: Id of the `server_tool_use` block this answers.
        content: Either the surfaced tool references, or an error payload.
    """

    tool_use_id: str
    content: ToolSearchToolSearchResultBlock | ToolSearchToolResultError


class ContainerUploadBlock(_Wire, tag_field="type", tag="container_upload"):
    """A `container_upload` content block referencing an uploaded file.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        file_id: Id of the uploaded file in the container.
    """

    file_id: str


class DocumentBlock(_Wire, tag_field="type", tag="document"):
    """A `document` content block returned inside a web-fetch result.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        source: The document source.
        title: Optional document title.
        citations: Optional citation configuration.
    """

    source: DocumentSource
    title: str | None = None
    citations: CitationsConfig | None = None


# Every content block a response `Message.content` array may carry.
ContentBlock = (
    TextBlock
    | ThinkingBlock
    | RedactedThinkingBlock
    | ToolUseBlock
    | ServerToolUseBlock
    | WebSearchToolResultBlock
    | WebFetchToolResultBlock
    | CodeExecutionToolResultBlock
    | BashCodeExecutionToolResultBlock
    | TextEditorToolResultBlock
    | ToolSearchToolResultBlock
    | ContainerUploadBlock
)


# --- Callers ----------------------------------------------------------------


class DirectCaller(_Wire, tag_field="type", tag="direct"):
    """A tool invoked directly by the model.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)
    """


class ServerToolCaller(_Wire, tag_field="type", tag="code_execution_20250825"):
    """A tool invoked from server-side code execution (`code_execution_20250825`).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        tool_id: Id of the server tool that invoked this call.
    """

    tool_id: str


class ServerToolCaller20260120(_Wire, tag_field="type", tag="code_execution_20260120"):
    """A tool invoked from server-side code execution (`code_execution_20260120`).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        tool_id: Id of the server tool that invoked this call.
    """

    tool_id: str


# A tool-call `caller`: the model directly, or a server-side code-execution tool.
Caller = DirectCaller | ServerToolCaller | ServerToolCaller20260120


# --- Usage & response metadata ----------------------------------------------


class CacheCreation(_Wire):
    """Breakdown of cache-creation input tokens by TTL.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        ephemeral_5m_input_tokens: Tokens written to the 5-minute cache.
        ephemeral_1h_input_tokens: Tokens written to the 1-hour cache.
    """

    ephemeral_5m_input_tokens: int | None = None
    ephemeral_1h_input_tokens: int | None = None


class OutputTokensDetails(_Wire):
    """Breakdown of output tokens by category.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        thinking_tokens: Output tokens spent on extended thinking.
    """

    thinking_tokens: int | None = None


class ServerToolUsage(_Wire):
    """Counts of server-tool requests billed on the response.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        web_search_requests: Number of web-search requests issued.
        web_fetch_requests: Number of web-fetch requests issued.
    """

    web_search_requests: int | None = None
    web_fetch_requests: int | None = None


class Usage(_Wire):
    """Token usage and billing detail on the response (and `message_delta`).

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        input_tokens: Input tokens consumed.
        output_tokens: Output tokens generated.
        cache_creation_input_tokens: Input tokens written to the prompt cache.
        cache_read_input_tokens: Input tokens served from the prompt cache.
        cache_creation: Per-TTL cache-creation breakdown.
        output_tokens_details: Per-category output-token breakdown.
        server_tool_use: Server-tool request counts.
        service_tier: Tier that served the request (`standard`/`priority`/`batch`).
        inference_geo: Region where inference ran.
    """

    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    cache_creation: CacheCreation | None = None
    output_tokens_details: OutputTokensDetails | None = None
    server_tool_use: ServerToolUsage | None = None
    service_tier: str | None = None
    inference_geo: str | None = None


class RefusalStopDetails(_Wire, tag_field="type", tag="refusal"):
    """Structured refusal information on a response.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        category: Policy category that triggered the refusal (`cyber`/`bio`/
            `reasoning_extraction`).
        explanation: Human-readable explanation of the refusal.
    """

    category: str | None = None
    explanation: str | None = None


class Container(_Wire):
    """Container info attached to a response when a container was used.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        id: Container identifier.
        expires_at: ISO-8601 timestamp when the container expires.
    """

    id: str
    expires_at: str | None = None


# --- Response ---------------------------------------------------------------


class Message(_Wire):
    """A `POST /v1/messages` (non-streaming) response body.

    Reference: [Messages API](<https://platform.claude.com/docs/en/api/messages>)

    Attributes:
        id: Unique message identifier.
        type: Object type discriminator; always `message`.
        role: Author role; always `assistant`.
        model: Model that produced the message.
        content: The generated content blocks.
        stop_reason: Why generation stopped (`end_turn`, `max_tokens`,
            `stop_sequence`, `tool_use`, `pause_turn`, `refusal`).
        stop_sequence: The custom stop sequence that was hit, if any.
        stop_details: Structured stop detail (e.g. refusal information).
        usage: Token usage and billing detail.
        container: Container info, when a container was used.
    """

    id: str
    role: str
    model: str
    content: list[ContentBlock]
    type: str = "message"
    stop_reason: str | None = None
    stop_sequence: str | None = None
    stop_details: RefusalStopDetails | None = None
    usage: Usage | None = None
    container: Container | None = None


# --- Streaming events -------------------------------------------------------


class ContentBlockDeltaText(_Wire, tag_field="type", tag="text_delta"):
    """A `text_delta` inside a `content_block_delta` event.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

    Attributes:
        text: A fragment of generated text to concatenate.
    """

    text: str


class ContentBlockDeltaInputJson(_Wire, tag_field="type", tag="input_json_delta"):
    """An `input_json_delta` inside a `content_block_delta` event.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

    Attributes:
        partial_json: A partial JSON string fragment of the tool `input` to
            accumulate; the final `input` is always an object.
    """

    partial_json: str


class ContentBlockDeltaThinking(_Wire, tag_field="type", tag="thinking_delta"):
    """A `thinking_delta` inside a `content_block_delta` event.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

    Attributes:
        thinking: A fragment of extended-thinking text to concatenate.
    """

    thinking: str


class ContentBlockDeltaSignature(_Wire, tag_field="type", tag="signature_delta"):
    """A `signature_delta` inside a `content_block_delta` event.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

    Attributes:
        signature: The thinking-block signature (sent just before stop).
    """

    signature: str


class ContentBlockDeltaCitations(_Wire, tag_field="type", tag="citations_delta"):
    """A `citations_delta` inside a `content_block_delta` event.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

    Attributes:
        citation: A single citation appended to the text block.
    """

    citation: TextCitation


# The `delta` carried by a `content_block_delta` event.
ContentBlockDelta = (
    ContentBlockDeltaText
    | ContentBlockDeltaInputJson
    | ContentBlockDeltaThinking
    | ContentBlockDeltaSignature
    | ContentBlockDeltaCitations
)


class MessageStartEvent(_Wire, tag_field="type", tag="message_start"):
    """The `message_start` event opening a stream.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

    Attributes:
        message: The initial `Message` with empty `content`.
    """

    message: Message


class ContentBlockStartEvent(_Wire, tag_field="type", tag="content_block_start"):
    """A `content_block_start` event opening a content block.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

    Attributes:
        index: Index of the block in the final `content` array.
        content_block: The initial (empty) content block being opened.
    """

    index: int
    content_block: ContentBlock


class ContentBlockDeltaEvent(_Wire, tag_field="type", tag="content_block_delta"):
    """A `content_block_delta` event updating a content block.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

    Attributes:
        index: Index of the block being updated.
        delta: The incremental update (text/json/thinking/signature/citation).
    """

    index: int
    delta: ContentBlockDelta


class ContentBlockStopEvent(_Wire, tag_field="type", tag="content_block_stop"):
    """A `content_block_stop` event closing a content block.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

    Attributes:
        index: Index of the block being closed.
    """

    index: int


class MessageDeltaInfo(_Wire):
    """The top-level `delta` carried by a `message_delta` event.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

    Attributes:
        stop_reason: Final stop reason, set as the message completes.
        stop_sequence: Custom stop sequence that was hit, if any.
    """

    stop_reason: str | None = None
    stop_sequence: str | None = None


class MessageDeltaEvent(_Wire, tag_field="type", tag="message_delta"):
    """A `message_delta` event carrying top-level Message changes.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

    Attributes:
        delta: The top-level field updates (`stop_reason`, `stop_sequence`).
        usage: Cumulative token usage for the message so far.
    """

    delta: MessageDeltaInfo
    usage: Usage | None = None


class MessageStopEvent(_Wire, tag_field="type", tag="message_stop"):
    """The `message_stop` event ending a stream.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)
    """


class PingEvent(_Wire, tag_field="type", tag="ping"):
    """A `ping` keep-alive event, dispersed throughout a stream.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)
    """


class StreamError(_Wire):
    """The `error` object inside an `error` stream event.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

    Attributes:
        type: Error type (e.g. `overloaded_error`).
        message: Human-readable error message.
    """

    type: str
    message: str | None = None


class ErrorEvent(_Wire, tag_field="type", tag="error"):
    """An `error` event the API may emit mid-stream.

    Reference: [Streaming](<https://platform.claude.com/docs/en/docs/build-with-claude/streaming>)

    Attributes:
        error: The error payload.
    """

    error: StreamError


# Every server-sent event a Messages stream may emit, discriminated on `type`.
# New event types may appear; unknown ones should be handled gracefully (the
# codec falls back to the raw dict rather than failing the stream).
StreamEvent = (
    MessageStartEvent
    | ContentBlockStartEvent
    | ContentBlockDeltaEvent
    | ContentBlockStopEvent
    | MessageDeltaEvent
    | MessageStopEvent
    | PingEvent
    | ErrorEvent
)
