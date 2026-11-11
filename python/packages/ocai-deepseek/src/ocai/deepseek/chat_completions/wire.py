"""Reuse compatible OpenAI wire DTOs without claiming complete DeepSeek decoding.

DeepSeek-specific fields remain the future dialect mapping's responsibility.
These types are not a total decoder or a registered executable codec.
"""

from ocai.openai.chat_completions.wire import ChatCompletion
from ocai.openai.chat_completions.wire import ChatCompletionChunk
from ocai.openai.chat_completions.wire import CompletionCreateParams

__all__ = ["ChatCompletion", "ChatCompletionChunk", "CompletionCreateParams"]
