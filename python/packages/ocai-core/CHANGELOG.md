# Changelog — ocai

All notable changes to the `ocai` distribution. Generated from the change files in
`.changeset/` by the release workflow (ADR 0010); do not edit released sections by hand.
## 0.1.1 (2026-11-11)

### Features

#### Compose explicit host endpoints and profile aliases

Compose explicit host endpoints and profile aliases. (WU-38, #35)

#### Select stream framing independently of semantic conversion

Select stream framing independently of semantic conversion. (WU-39, #69)

#### Validate and preserve canonical URL citations

Validate and preserve canonical URL citations. (WU-40, #77)

#### Admit provider-executed server-tool definitions with honest support reports

Admit provider-executed server-tool definitions with honest support reports. (WU-41, #80)

#### Preserve scoped request and replay anchors

Preserve scoped request and replay anchors. (WU-42, #83)

#### Qualify basic Anthropic web search with replay and measured accounting

Qualify basic Anthropic web search with replay and measured accounting. (WU-43, #87)

### Fixes

#### Package metadata points at the real repository and the DeepSeek plugin has an extra

Homepage, Source, Documentation and Changelog URLs now point at `github.com/ocarinow/ocai` and the docs site. `ocai[deepseek]` installs the DeepSeek plugin and `ocai[all]` includes it. No runtime behavior changed.
