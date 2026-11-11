# API reference

These pages describe this repository revision. Installed releases may differ;
check your installed distribution versions before relying on a newer symbol.
Public declarations in non-private modules are included; re-export tables identify
where imported symbols are defined. Internal underscore-prefixed modules are excluded.
Examples and task-oriented explanations live in the [Python guide](../libraries/python/README.md).
Embedding/vector-store contracts and Responses declarations are provisional and do
not imply an executable provider implementation.

## Packages at this revision

| Distribution | Version | Python | Runtime dependencies |
|---|---|---|---|
| `ocai-anthropic` | `0.1.2` | `>=3.13` | `ocai>=0.1,<0.2`, `msgspec>=0.18` |
| `ocai-aws` | `0.1.1` | `>=3.13` | `ocai>=0.1,<0.2`, `awscrt>=0.38.1,<0.39` |
| `ocai-bedrock` | `0.1.1` | `>=3.13` | `ocai>=0.1,<0.2` |
| `ocai` | `0.1.2` | `>=3.13` | None |
| `ocai-deepseek` | `0.1.2` | `>=3.13` | `ocai>=0.1,<0.2`, `ocai-openai>=0.1,<0.2` |
| `ocai-openai` | `0.1.2` | `>=3.13` | `ocai>=0.1,<0.2`, `msgspec>=0.18` |

## Python namespaces

- [ocai.anthropic](ocai-anthropic.md)
- [ocai.aws](ocai-aws.md)
- [ocai.bedrock](ocai-bedrock.md)
- [ocai.chat](ocai-chat.md)
- [ocai.convert](ocai-convert.md)
- [ocai.core](ocai-core.md)
- [ocai.deepseek](ocai-deepseek.md)
- [ocai.embedding](ocai-embedding.md)
- [ocai.openai](ocai-openai.md)
- [ocai.runtime](ocai-runtime.md)
- [ocai.vectorstore](ocai-vectorstore.md)
- [ocai.wire](ocai-wire.md)

## Platform

- [Management HTTP API](management.md)
- [Management TypeScript client](../platform/client.md)
