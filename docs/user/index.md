# ocai

**One Common interface for AI** gives Python applications a provider-neutral chat
interface with visible conversion evidence. A call returns its response together
with the selected route, usage and a fidelity report describing conversion losses
and semantic changes.

Start with [installation and your first call](libraries/python/README.md), then
learn [streaming and async](guides/streaming.md), [tools and structured output](guides/tools.md),
and [conversion and fidelity](guides/fidelity.md). The [API reference](reference/README.md)
covers the package contracts, signatures and fields.

## Available today

| Surface | Availability |
|---|---|
| Python chat | Recorded unary/streaming qualification for OpenAI Chat Completions, Anthropic Messages and DeepSeek chat |
| AWS authentication and Bedrock hosting | Explicit SigV4 credentials; qualified Anthropic unary InvokeModel hosting |
| Conversion and governance | Catalogs, inspection/preparation, fidelity policies, interceptors and observer events |
| Platform | Foundation console and status API; no production inference or user administration workflow yet |
| Other capabilities/languages | Embedding/vector-store contracts are provisional; Responses execution, Gemini, TypeScript and Go are not implemented |

See the [support matrix](provider-feature-matrix.md) for boundaries and evidence.
These pages describe the repository revision used to build this site. Your installed
release can differ; compare its version with the [package reference](reference/README.md).
Model IDs in examples are illustrative; use a deployment your account can access.

For the service and console, start with [platform usage](platform/README.md).
For a gateway built using the Python library, use [gateway integration](gateway-integration.md).

ocai is source-available under **FSL-1.1-ALv2**, converting to Apache-2.0 two years
after each version's release. See the [license](https://github.com/ocarinow/ocai/blob/main/LICENSE).
Contributor, architecture and roadmap documents are in the
[repository documentation map](https://github.com/ocarinow/ocai/blob/main/docs/README.md).
