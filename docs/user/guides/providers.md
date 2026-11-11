# Providers, credentials and hosts

Install the provider codec before constructing a model. Credentials are explicit
and are applied at the transport leaf on every attempt. Never put a key in
`provider_options`, context, logs or saved request JSON.

| Provider | Model prefix | Credential |
|---|---|---|
| OpenAI Chat Completions | `openai/` | `ApiKey.from_env("OPENAI_API_KEY")` |
| Anthropic Messages | `anthropic/` | `ApiKey.from_env("ANTHROPIC_API_KEY", header="x-api-key", scheme="")` |
| DeepSeek chat | `deepseek/` | `ApiKey.from_env("DEEPSEEK_API_KEY")` |

The prefix selects an installed codec; it does not grant access to a model or
certify every feature of that model. Responses is a declared stub, so pinning
`interface="responses"` does not provide working Responses execution.

Provider helpers such as `ocai.openai.chat_model` and
`ocai.anthropic.chat_model` compose the same core front door. A caller-supplied
credential retains its header/scheme: the Anthropic helper does not fix an
incorrect bearer credential for you.

## Bedrock unary hosting

Install `ocai[http]` and `ocai-bedrock[anthropic,aws]`. Construct a `Bedrock` host
and `SigV4Credential`, passing access key, secret key, region and optional session
token explicitly. Pass both as `host=` and `credentials=` to `ocai.chat.model`,
using an `anthropic/<model-or-profile-id>` spec. See the
[Bedrock API](../reference/ocai-bedrock.md) and [AWS credentials](../reference/ocai-aws.md).

This release qualifies Anthropic **unary InvokeModel** only. The EventStream parser
exists, but that does not qualify Bedrock streaming or Converse. There is no IMDS,
profile, STS or automatic credential refresh. Supply replacement credentials through
your own explicit lifecycle. `ocai-aws` uses AWS-maintained signing code; it does not
replace ocai's execution, conversion or fidelity contracts with an SDK client.

## Custom endpoints and trust

Use an explicit `Custom` host for a compatible endpoint and a catalog/trust policy
appropriate to that endpoint. A base URL does not establish dialect compatibility,
residency, model availability or data-retention policy. Endpoint/host declarations
and conversion qualification are distinct. Never send a provider key to an
unreviewed custom endpoint. See [`ocai.wire`](../reference/ocai-wire.md) and the
[support matrix](../provider-feature-matrix.md).
