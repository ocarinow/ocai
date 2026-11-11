# Supported features

Checked against the repository's November 2026 implementation. **Represented** means
a canonical type exists; **converted** means a mapping exists; **qualified** means
recorded execution/conformance tests exercise the stated scope. None of these proves
current live model access, commercial availability or every vendor feature.
The canonical IR revision is `2026-07`; package semver is independent.

| Surface | Current qualified scope | Boundary |
|---|---|---|
| OpenAI Chat Completions | Unary/streaming chat, function-tool conversions and client compatibility mappings | Explicit fixture census; not the entire evolving OpenAI API |
| Anthropic Messages | Unary/streaming chat, tools, basic hosted search accounting and URL citation handling | Feature-specific tests; no universal hosted-tool or media support |
| DeepSeek chat | Unary/streaming, reasoning replay and usage/identity evidence | Compatible dialect with independent censuses, not arbitrary OpenAI equivalence |
| Anthropic on Bedrock | Unary InvokeModel, signing, host errors and successful response effects | No Bedrock streaming or Converse qualification yet |
| OpenAI Responses | Interface declarations and placeholder codec | No executable facade component or completed conversion path |
| Gemini | No executable provider package | Research only |
| Embeddings/vector stores | Provisional port/type contracts | No qualified provider execution |
| Streaming middleware | Unary and streaming interception, lifecycle/ownership and metadata observer events | Not a durable audit database or delivered OTel satellite |
| Citations/replay | URL citations, scoped provider references, response identity in stream folding | Provider-specific references cannot silently cross interface scope |
| Media | Canonical source/part types and selected mappings | No general media-generation capability or multimodal gateway qualification |
| Platform | Status console/API plus internal identity, storage and authorization foundation | No user-facing inference gateway yet |
| TypeScript/Go | Placeholder library ports | Platform TypeScript client is a separate private package |

## Qualification evidence

- [Core qualification tests](https://github.com/ocarinow/ocai/tree/main/python/packages/ocai-core/tests): gateway integration, stream ownership/middleware, fidelity policy, citations, host adaptation and EventStream framing.
- [OpenAI tests](https://github.com/ocarinow/ocai/tree/main/python/packages/ocai-openai/tests): provider conversion and inbound compatibility fixtures.
- [Anthropic tests](https://github.com/ocarinow/ocai/tree/main/python/packages/ocai-anthropic/tests): conversion and search/accounting cases.
- [DeepSeek tests](https://github.com/ocarinow/ocai/tree/main/python/packages/ocai-deepseek/tests): unary/streaming and reasoning replay.
- [AWS tests](https://github.com/ocarinow/ocai/tree/main/python/packages/ocai-aws/tests) and [Bedrock tests](https://github.com/ocarinow/ocai/tree/main/python/packages/ocai-bedrock/tests): signing and unary host qualification.
- [Platform contract](https://github.com/ocarinow/ocai/blob/main/platform/spec/management.openapi.json): available HTTP operations.

Use inspection and fidelity reports for the selected request. A declared capability
profile or a passing canonical schema check alone is not a qualification verdict.
