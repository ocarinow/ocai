# Changelog — ocai-deepseek

All notable changes to the `ocai-deepseek` distribution. Generated from the change files in
`.changeset/` by the release workflow (ADR 0010); do not edit released sections by hand.
## 0.1.2 (2026-11-11)

### Features

#### Execute DeepSeek through the public chat facade

Enable sync and async unary calls through explicit catalogs or plugin discovery,
with public preparation, conversion policies, context and credential isolation,
reasoning replay and measured usage. Streaming remains unqualified. (WU-45, #99)

#### Qualify DeepSeek streaming through public chat execution

Add a censused DeepSeek stream edge with reasoning, tools, response metadata and
final-choice usage, plus explicit incomplete-stream evidence. Allow compatible
stream transducers to use an explicitly configured codec. (WU-46, #100)

## 0.1.1 (2026-11-11)

### Features

#### Declare the independently attributable DeepSeek interface package

Declare the independently attributable DeepSeek interface package. (WU-44a, #89)

#### Qualify independent DeepSeek unary conversion

Share compatible mapping through explicit variant configuration while preserving
DeepSeek identity, mandatory reasoning replay, honest parameter effects and
measured usage. Add independently censused request encode/audit and response
decode edges with recoverable unknown-field evidence. (WU-44b, #91)

### Fixes

#### Package metadata points at the real repository and the DeepSeek plugin has an extra

Homepage, Source, Documentation and Changelog URLs now point at `github.com/ocarinow/ocai` and the docs site. `ocai[deepseek]` installs the DeepSeek plugin and `ocai[all]` includes it. No runtime behavior changed.
