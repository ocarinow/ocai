"""Error mapping: neutral status layer + dialect body layer.

Pins the two-layer design: `error_from_response` classifies by HTTP status
alone (neutral — what the wire layer raises, so retry policies can branch on
`TransientError`), and a codec's `map_error` refines from the provider's error
*body* into precise taxonomy that status can't express
(`context_length_exceeded`, content-filter blocks). Returning `None` from
layer 2 defers to layer 1 — no false precision.
"""

from __future__ import annotations

from ocai.anthropic.messages.codec import MessagesCodec
from ocai.core import AuthError
from ocai.core import ContentFilterError
from ocai.core import ContextLengthError
from ocai.core import OcaiError
from ocai.core import RateLimitError
from ocai.core import TransientError
from ocai.core import error_from_response
from ocai.openai.chat_completions.codec import ChatCompletionsCodec

# --- Layer 1: the neutral status mapper ------------------------------------


def test_neutral_mapper_classifies_by_status() -> None:
    assert isinstance(error_from_response(429, None), RateLimitError)
    assert isinstance(error_from_response(503, None), TransientError)
    assert isinstance(error_from_response(401, None), AuthError)
    # An unrecognized 4xx stays a generic OcaiError (no false precision).
    assert type(error_from_response(400, {"error": "bad"})) is OcaiError


def test_neutral_mapper_parses_retry_after() -> None:
    err = error_from_response(429, None, retry_after="2.5")
    assert isinstance(err, RateLimitError) and err.retry_after == 2.5


# --- Layer 2: dialect body refinement --------------------------------------


def test_openai_map_error_refines_context_length_from_body() -> None:
    # A 400 whose body code says context_length_exceeded → ContextLengthError,
    # which status alone (400) could never reach.
    body = {
        "error": {
            "type": "invalid_request_error",
            "code": "context_length_exceeded",
            "message": "too long",
        }
    }
    err = ChatCompletionsCodec().map_error(400, body)
    assert isinstance(err, ContextLengthError)
    assert err.code == "context_length_exceeded"
    assert err.status == 400


def test_openai_map_error_refines_content_filter() -> None:
    body = {"error": {"code": "content_filter", "message": "blocked"}}
    assert isinstance(ChatCompletionsCodec().map_error(400, body), ContentFilterError)


def test_openai_map_error_defers_when_unrecognized() -> None:
    assert ChatCompletionsCodec().map_error(400, {"error": {"code": "teapot"}}) is None
    # A non-dict error body (some 4xx/5xx shapes) defers rather than crashing.
    assert ChatCompletionsCodec().map_error(429, {"error": "slow down"}) is None


def test_anthropic_map_error_maps_type_and_sets_code() -> None:
    body = {"type": "error", "error": {"type": "rate_limit_error", "message": "slow"}}
    err = MessagesCodec().map_error(429, body)
    assert isinstance(err, RateLimitError) and err.code == "rate_limit_error"
    assert MessagesCodec().map_error(400, {"error": {"type": "weird"}}) is None
