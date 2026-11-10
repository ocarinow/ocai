---
name: record-wire-pair
description: Author or update a recorded HTTP/SSE request+response pair under python/packages/*/tests/http/ for facade and transport tests — the rule-10 format (no live keys, no SDK mocks), naming, redaction, streaming pairs, error pairs, and how tests mount them with respx. Use whenever a test needs provider wire traffic.
---

# Record a wire pair

Rule 10: tests are wire-level, recorded HTTP/SSE pairs replayed with respx,
never live keys, never provider-SDK mocks. A pair is a hand-authored or
captured JSON file that pins exactly what went over the wire. This skill is
the format and the discipline. (Promoting the format into `spec/` is gap
G-02; until then this file is the convention.)

## 1. Where and what to name it

`python/packages/ocai-core/tests/http/<provider>_<interface-short>_<behavior>.json`

Examples already there: `openai_chat_completion.json`,
`openai_chat_completion_tool_call.json`, `openai_chat_completion_auth_error.json`,
`openai_chat_completion_stream.json` + `openai_chat_completion_stream_paired.json`,
`anthropic_messages_overloaded_error.json`. One behavior per file; the name
says which.

## 2. The shape

```jsonc
{
  "description": "One paragraph: what the exchange exercises, which WU/rule it serves, whether it is captured or synthetic, and what it PAIRS with if anything.",
  "request": {
    "method": "POST",
    "url": "https://api.openai.com/v1/chat/completions",
    "json": { /* the exact wire body the codec emits, INCLUDING the model the facade injects */ }
  },
  "response": {
    "status": 200,
    "json": { /* verbatim provider body */ }
  }
}
```

Streaming pairs replace `response.json` with:

```jsonc
  "response": {
    "status": 200,
    "headers": {"content-type": "text/event-stream"},
    "sse": ["data: {...}", "data: {...}", "data: [DONE]"]   // verbatim event lines, in order
  }
```

Error pairs are the same shape with the provider's real error envelope and
status (401, 429, 400 context-length, 529 overloaded, …); they exist to prove
the error mapping (rule 8), so the envelope must be wire-accurate.

## 3. Rules

- **Wire-accurate or nothing.** Captured from a real call (preferred) or
  hand-authored against the provider research in `docs/providers/` and the
  plugin's wire structs. A body a provider would never send is a lie the
  tests will defend. Say which in `description`.
- **Redact before committing.** No API key, organization id, account email,
  real user content, or real request ids that could identify a tenant.
  Replace keys with the provider's documented placeholder shape
  (`sk-XXXX`), ids with obviously synthetic ones (`chatcmpl-tool123`). The
  CI must pass with zero secrets, and the archive is public.
- **The request body is the codec's output.** It carries the injected
  `model`, the stream markers (`stream`, `stream_options`), and nothing the
  canonical request did not express. Tests may assert on the request the
  route received, so keep it exact.
- **Streaming pairs come in twos.** A stream recording is PAIRED with a
  blocking recording of the same logical request (`*_stream.json` +
  `*_stream_paired.json`) so the fold law can be asserted at the port
  (rule 7). The SSE log should also exist as the fold triple's
  `wire_events` under `spec/fixtures/<provider>/<interface>/streams/`;
  the description names that fixture.
- **Mid-stream errors are recordings too.** An error event inside an SSE
  log (`*_stream_error.json`) proves the wire shape of a mid-stream error,
  not just the exception.
- **Never edit a recording to make a test pass.** If the codec disagrees
  with the wire, the codec is wrong or the recording is; find out which
  against `docs/providers/`.

## 4. Mount it in a test

```python
@respx.mock
def test_chat_tool_call_pair(load_http: LoadHttp) -> None:
    pair = load_http("openai_chat_completion_tool_call.json")
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=pair["response"]["json"]))
    ...
    assert route.called
    sent = json.loads(route.calls.last.request.content)
    assert sent == pair["request"]["json"]          # the wire body is part of the contract
```

Streaming:

```python
body = ("\n\n".join(pair["response"]["sse"]) + "\n\n").encode()
respx.post(URL).mock(return_value=httpx.Response(200, headers=pair["response"]["headers"], content=body))
```

`load_http` is the conftest fixture; `LoadHttp` is the per-file alias
`Callable[[str], dict[str, Any]]`. Credentials in tests are literal dummies
(`ApiKey("sk-test")`), never read from the environment.

## 5. Checklist before the PR

- [ ] `description` says captured vs synthetic, the WU/rule, and the pair/triple it relates to
- [ ] zero secrets or identifying ids (grep for `sk-`, `@`, `org-`)
- [ ] request body equals what the codec emits for the canonical request in the test
- [ ] a stream recording has its blocking twin and its fold triple
- [ ] `uv run python scripts/check.py` passes
