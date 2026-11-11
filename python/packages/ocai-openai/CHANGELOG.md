# Changelog — ocai-openai

All notable changes to the `ocai-openai` distribution. Generated from the change files in
`.changeset/` by the release workflow (ADR 0010); do not edit released sections by hand.
## 0.1.1 (2026-11-11)

### Features

#### Admit provider-executed server-tool definitions with honest support reports

Admit provider-executed server-tool definitions with honest support reports. (WU-41, #80)

#### Preserve scoped request and replay anchors

Preserve scoped request and replay anchors. (WU-42, #83)

#### Qualify independent DeepSeek unary conversion

Share compatible mapping through explicit variant configuration while preserving
DeepSeek identity, mandatory reasoning replay, honest parameter effects and
measured usage. Add independently censused request encode/audit and response
decode edges with recoverable unknown-field evidence. (WU-44b, #91)

### Fixes

#### Package metadata points at the real repository and the DeepSeek plugin has an extra

Homepage, Source, Documentation and Changelog URLs now point at `github.com/ocarinow/ocai` and the docs site. `ocai[deepseek]` installs the DeepSeek plugin and `ocai[all]` includes it. No runtime behavior changed.
